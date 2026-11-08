'''Тести GUARD. Запуск з папки backend:  python -m pytest tests -q
Мережеві перевірки (Google Safe Browsing, перенаправлення) підмінено заглушками,
щоб тести були швидкими й не витрачали ліміт API'''

import os
import sys

import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import check_isPhishing
from app import app
from check_rules import check_rules
from check_ssl_and_redirects import check_redirects
from ml.extract_features import extract_features, normalize_url, N_FEATURES

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(check_isPhishing, "check_google_safe_browsing", lambda url: False)
    monkeypatch.setattr(check_isPhishing, "check_redirects", lambda url: {"final_url": url, "redirect_count": 0, "error": None})


# --- Ознаки ---

def test_features_count():
    assert len(extract_features("https://www.bbc.com/news")) == N_FEATURES == 47


def test_scheme_and_www_do_not_change_features():
    # головна причина старої поломки моделі: схема і www "видавали" клас
    assert extract_features("https://www.bbc.com/news") == extract_features("bbc.com/news")
    assert extract_features("http://bbc.com/news#top") == extract_features("bbc.com/news")


def test_normalize_url():
    assert normalize_url("HTTPS://www.Example.com/") == "Example.com"
    assert normalize_url("http://site.com/a?x=1#frag") == "site.com/a?x=1"


def test_broken_url_does_not_crash():
    assert len(extract_features("http://[broken.com/a")) == N_FEATURES


# --- Правила ---

@pytest.mark.parametrize("url", [
    "http://paypal-login-verify.xyz/signin",
    "https://privat24-ua.online/login",
    "https://amazon.co.jp.lcmgo.com/",
    "http://paypal.com@evil.ru/",
    "http://45.95.168.245/x.exe",
])
def test_rules_catch_obvious_phishing(url):
    assert check_rules(url)["score"] >= check_isPhishing.THRESHOLD


@pytest.mark.parametrize("url", [
    "https://www.bbc.com/news",
    "https://accounts.google.com/signin",
    "https://www.amazon.de/",
    "https://groups.io/login",          # "groups" містить "ups", але це не бренд UPS
    "https://pineapple-shop.xyz/",      # "pineapple" містить "apple"
    "http://192.168.0.1/admin",         # локальна адреса (роутер)
])
def test_rules_do_not_block_normal_sites(url):
    assert check_rules(url)["score"] < check_isPhishing.THRESHOLD


def test_brand_alone_is_only_a_reason():
    result = check_rules("https://www.amazongames.com/")
    assert 0 < result["score"] < check_isPhishing.THRESHOLD
    assert result["reasons"]


# --- Перенаправлення: захист від SSRF (без мережі - адреси відсіюються до запиту) ---

@pytest.mark.parametrize("url", [
    "http://127.0.0.1:5000/",
    "http://localhost/",
    "http://169.254.169.254/latest/meta-data/",
    "http://10.0.0.1/",
    "ftp://example.com/",
])
def test_redirects_block_private_addresses(url):
    assert check_redirects(url)["error"] == "not public host"


# --- Підсумкова перевірка ---

def test_check_url_normal_site():
    result = check_isPhishing.check_url("https://www.bbc.com/news")
    assert result["is_phishing"] is False


def test_check_url_phishing():
    result = check_isPhishing.check_url("http://paypal-login-verify.xyz/signin")
    assert result["is_phishing"] is True
    assert result["threat_type"] == "phishing"


def test_safe_browsing_match_gives_max_probability(monkeypatch):
    monkeypatch.setattr(check_isPhishing, "check_google_safe_browsing", lambda url: True)
    result = check_isPhishing.check_url("https://www.bbc.com/news")
    assert result["probability"] == 1.0
    assert "є в базі Google Safe Browsing" in result["reasons"]


def test_safe_browsing_skipped_when_already_blocked(monkeypatch):
    calls = []
    monkeypatch.setattr(check_isPhishing, "check_google_safe_browsing", lambda url: calls.append(url) or False)
    check_isPhishing.check_url("http://paypal-login-verify.xyz/signin")
    assert calls == []


def test_short_link_to_phishing_is_blocked(monkeypatch):
    monkeypatch.setattr(check_isPhishing, "check_redirects",
                        lambda url: {"final_url": "http://paypal-login-verify.xyz/signin", "redirect_count": 1, "error": None})
    result = check_isPhishing.check_url("https://bit.ly/abc123")
    assert result["is_phishing"] is True
    assert result["reasons"][0] == "перенаправляє на paypal-login-verify.xyz"


# --- API ---

def test_api_missing_url():
    response = app.test_client().post("/guardai/api/scan", json={})
    assert response.status_code == 400


def test_api_scan():
    response = app.test_client().post("/guardai/api/scan", json={"url": "https://www.bbc.com/news"})
    data = response.get_json()
    assert response.status_code == 200
    assert set(data) == {"status", "url", "is_phishing", "probability", "threat_type", "reasons"}


def test_api_rate_limit():
    client = app.test_client()
    # окрема IP, щоб ліміт не зачепив інші тести
    headers = {"X-Forwarded-For": "203.0.113.7"}
    codes = [client.post("/guardai/api/scan", json={"url": "https://bbc.com"}, headers=headers).status_code
             for _ in range(61)]
    assert codes[:60] == [200] * 60
    assert codes[60] == 429

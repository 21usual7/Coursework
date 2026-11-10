'''Правила поверх моделі для очевидних ознак фішингу.

Модель пропускає випадки на кшталт "paypal-login-verify.xyz", бо в датасеті мало
таких прикладів. Правила перевіряють кілька сильних ознак і повертають оцінку
небезпеки (0..1) та список причин. Підсумкова ймовірність = max(модель, правила).'''

import os
import re
import csv
import ipaddress
from urllib.parse import urlparse

from ml.extract_features import EXTRACTOR, normalize_url, TRIGGERS, SUSPICIOUS_TLDS, PLATFORMS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Бренди, які найчастіше підробляють. Довгі назви шукаємо як підрядок ("paypallogin"),
# короткі - лише як окреме слово, бо інакше "groups" містить "ups", а "pineapple" - "apple"
BRANDS_SUBSTRING = {
    "paypal", "google", "microsoft", "amazon", "facebook", "instagram", "netflix",
    "spotify", "dropbox", "wellsfargo", "bankofamerica", "barclays",
    "outlook", "office365", "binance", "coinbase", "metamask", "whatsapp", "telegram",
    "privatbank", "privat24", "monobank", "linkedin", "twitter",
}
BRANDS_TOKEN = {"apple", "appleid", "icloud", "adobe", "chase", "citi", "hsbc", "dhl", "fedex", "ups", "irs", "steam", "ebay"}

# Оцінка для "підозрілих" ознак, яких самих по собі замало для блокування:
# вони потрапляють у список причин, але нижчі за поріг 0.6
INFO_SCORE = 0.5

# Офіційні домени брендів, яких немає у списку популярних сайтів
OFFICIAL_DOMAINS = {
    "google.com", "googleapis.com", "googleusercontent.com", "googlegroups.com", "gstatic.com", "youtube.com",
    "amazonaws.com", "facebook.com", "fb.com", "microsoft.com", "microsoftonline.com",
    "office.com", "live.com", "outlook.com", "sharepoint.com", "windows.net",
    "twitter.com", "adobe.com", "dropbox.com", "whatsapp.com", "apple.com", "icloud.com",
    "paypal.com", "privatbank.ua", "privat24.ua", "monobank.ua",
}


def _load_popular_domains():
    '''Популярні домени з tranco_benign.csv. Хостинги (blogspot, github.io, wixsite...)
    туди не потрапили, бо мають шкідливі мітки в датасеті - і це правильно,
    бо фішингові сторінки часто розміщують саме на них'''
    path = os.path.join(BASE_DIR, "ml", "tranco_benign.csv")
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        return {EXTRACTOR(row["url"]).top_domain_under_public_suffix for row in csv.DictReader(f)}


POPULAR_DOMAINS = _load_popular_domains() | OFFICIAL_DOMAINS


def _tokens(text):
    return set(t for t in re.split(r"[-_./?=&:%#@]", text.lower()) if t)


def _find_brand(hostname):
    host_tokens = _tokens(hostname)
    for brand in BRANDS_SUBSTRING:
        if brand in hostname:
            return brand
    for brand in BRANDS_TOKEN:
        if brand in host_tokens:
            return brand
    return None


def check_rules(url: str) -> dict:
    '''Повертає {"score": 0..1, "reasons": [...]}. score = 0, якщо жодне правило не спрацювало'''

    status = {"score": 0.0, "reasons": []}

    url = url.strip()
    if not url:
        return status

    # "@" у частині з адресою: http://paypal.com@evil.com відкриває evil.com.
    # Перевіряємо до нормалізації, поки є схема
    try:
        raw = url if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url) else "http://" + url
        if urlparse(raw).username:
            status["reasons"].append("у адресі є '@': браузер відкриє інший сайт, ніж видно")
            status["score"] = max(status["score"], 0.85)
    except ValueError:
        pass

    norm = normalize_url(url)
    try:
        parsed = urlparse("http://" + norm)
        hostname = (parsed.hostname or "").lower()
    except ValueError:
        return status

    ext = EXTRACTOR(norm)
    registered = ext.top_domain_under_public_suffix.lower()
    suffix = ext.suffix.lower()
    path_and_query = (parsed.path or "") + "?" + (parsed.query or "")

    # 1. IP-адреса замість домену
    try:
        ipaddress.ip_address(hostname)
        is_ip = True
    except ValueError:
        is_ip = False

    if is_ip:
        # локальні адреси (роутер, локальний сервер) не вважаємо небезпечними
        if not ipaddress.ip_address(hostname).is_private:
            status["reasons"].append("IP-адреса замість доменного імені")
            status["score"] = max(status["score"], 0.75)
        return status

    # популярні та офіційні домени далі не перевіряємо
    if registered in POPULAR_DOMAINS:
        return status

    # тригери в самому домені ("secure-login.xyz") - сильна ознака,
    # а "/login" у шляху є майже на кожному сайті
    host_triggers = _tokens(hostname) & TRIGGERS
    triggers = host_triggers | (_tokens(path_and_query) & TRIGGERS)
    bad_tld = suffix.split(".")[-1] in SUSPICIOUS_TLDS

    # 2. Назва бренду в домені, який бренду не належить
    brand = _find_brand(hostname)
    if brand and ext.domain.lower() != brand and suffix != brand:
        # бренд у піддомені чужого сайту: "paypal.com.evil.ru". На хостингах піддомен - ім'я
        # акаунта (microsoft.github.io - офіційна сторінка), тому там потрібне ще й слово-тригер
        brand_in_subdomain = brand in ext.subdomain.lower() and registered not in PLATFORMS
        if brand_in_subdomain or host_triggers or bad_tld:
            status["reasons"].append(f"назва бренду '{brand}' на чужому домені {registered}")
            status["score"] = max(status["score"], 0.9)
        else:
            # "amazongames.com", "microsoftazure.us" - може бути як фішинг, так і звичайний сайт
            status["reasons"].append(f"домен {hostname} містить назву бренду '{brand}'")
            status["score"] = max(status["score"], INFO_SCORE)

    # 3. Підозріла доменна зона + слово-тригер у домені (login, verify, account...)
    if bad_tld and host_triggers:
        status["reasons"].append(f"підозріла зона .{suffix} і слова {sorted(host_triggers)} у домені")
        status["score"] = max(status["score"], 0.7)

    # 4. Punycode (xn--) - домен може імітувати інший схожими літерами (аpple з кириличною "а").
    # Але так записуються і звичайні домени кирилицею чи тайською, тому лише як підозра
    if "xn--" in hostname:
        status["reasons"].append("punycode-домен (можлива підміна літер)")
        status["score"] = max(status["score"], INFO_SCORE)

    # 5. Багато піддоменів + тригер: "secure.login.paypal.com.verify.example.tk"
    subdomain_levels = len(ext.subdomain.split(".")) if ext.subdomain else 0
    if subdomain_levels >= 3 and triggers:
        status["reasons"].append(f"забагато піддоменів ({subdomain_levels}) і слова-тригери")
        status["score"] = max(status["score"], 0.65)

    return status

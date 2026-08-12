import time
import re
import math
import socket
import requests
import tldextract
import whois
from urllib.parse import urlparse
import ssl
from collections import Counter


TRIGGERS = ["login", "signin", "verify", "verification", "authenticate", "account", "security", "secure", "password", "reset", "recover", "unlock", "confirm", "confirmation", "validate", "wallet", "payment", "billing", "invoice", "support", "alert", "warning", "suspended", "blocked", "update", "activate", "authorization", "2fa", "mfa", "credential"]


def extract_features(url: str) -> list:
    '''Функція яка достає головні ознаки фішонгової URL та стандартизує їх'''
    features = []
    domain = urlparse(url).netloc
    
    assert type(url) is str, "URL is not string type"
    
    #Перевірка на https
    features.append(len(url))
    features.append(1) if "https:" in url else features.append(0)
    features.append(is_ip(url))
    cerificate_val = check_for_certificate(url)
    
    features.append(cerificate_val) if cerificate_val is not None else f"Error, exiting {exit(-1)}"
    redirects_count = count_redirects(url)
    
    if redirects_count == -1: 
        raise ValueError("Redirect count check failed ")
    features.append(redirects_count)
    
    features.extend(extract_specific_symbols(url=url, domain=domain))
    features.extend(extract_entropy_features(url=url))
    features.extend(extract_trigger_features(url))
    return features
    
    
def is_ip(url: str) -> int:
    '''Функція яка перевіряє чи є в URL IP адреса'''
    pattern = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    match = re.findall(pattern, url)
    return 1 if match else 0     


def check_for_certificate(url: str) -> int:
    '''Функія яка перевіряє чи має URL SSL/TLS сертіфікати'''
    parsed_url = urlparse(url)
    host = parsed_url.hostname
    port = parsed_url.port or 443
    context = ssl.create_default_context()
    
    try:
        with socket.create_connection((host, port), timeout=5) as s: 
            with context.wrap_socket(s, server_hostname=host) as ssock:
                certificate = ssock.getpeercert()
                return 1 

    except ssl.SSLError as e:
        return 0
    except Exception as e:
        print(f"Помилка підключення {e}")
        return None


def count_redirects(url: str) -> int:
    '''Функція яка рахує кількість редіректів'''
    try:
        r = requests.get(url)
        redirect_count = len(r.history)
        return redirect_count
    
    except Exception as e:
        print(f"Помилка: {e}")
        return -1
    

def extract_specific_symbols(url: str, domain: str) -> list:
    """Функція яка приймає аргументи (url: str, domain: str) и повертає symbols_features list"""
    symbols_features = []
    
    symbols_features.append(1 if "@" in url else 0 )
    symbols_features.append(domain.count("-"))
    symbols_features.append(url.rfind("//"))
    symbols_features.append(url.rfind("%"))
    symbols_features.append(url.rfind("="))

    clean_url = re.sub(r'[a-zA-Z0-9.:/]', '', url)
    total_special_chars = len(clean_url)
    symbols_features.append(total_special_chars)
    
    special_ratio = total_special_chars / len(url) if len(url) > 0 else 0
    symbols_features.append(round(special_ratio, 4))
    
    return symbols_features


def calc_shannon_entropy(text: str) -> float:
    if not text:
        return 0.0

    length = len(text)
    entropy = 0
    counts = Counter(text)
    
    entropy = -sum((count / length) * math.log2(count / length) for count in counts.values())
    return round(entropy, 4)


def extract_entropy_features(url: str) -> list:
    ext = tldextract.extract(url)
    
    domain_part = f"{ext.subdomain}.{ext.domain}" if ext.subdomain else ext.domain
    domain_entropy = calc_shannon_entropy(domain_part)
    full_url_entropy = calc_shannon_entropy(url)
    
    return [domain_entropy, full_url_entropy]


def extract_trigger_features(url: str) -> list[int]:
    url_lower = url.lower()
    tokens = set(re.split(r'[-_./?=&:%#]', url_lower))
    matched_words = tokens.intersection(TRIGGERS)
    
    trigger_count = len(matched_words)
    has_trigger = 1 if trigger_count > 0 else 0
    
    return [trigger_count, has_trigger]


print(extract_features("https://google.com"))
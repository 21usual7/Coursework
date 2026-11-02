import re
import math
import tldextract
from urllib.parse import urlparse
from collections import Counter
import ipaddress


TRIGGERS = ["login", "signin", "verify", "verification", "authenticate", "account", "security", "secure", "password", "reset", "recover", "unlock", "confirm", "confirmation", "validate", "wallet", "payment", "billing", "invoice", "support", "alert", "warning", "suspended", "blocked", "update", "activate", "authorization", "2fa", "mfa", "credential"]


def extract_features(url: str) -> list:
    '''Функція яка достає головні ознаки фішонгової URL та стандартизує їх'''
    assert isinstance(url, str), "URL is not string type"

    features = []
    domain = urlparse(url).netloc
    
    
    parsed = urlparse(url)

    # Перевірка довжини субдомена
    ext = tldextract.extract(url)
    subdomaim_length = len(ext.subdomain)
    features.append(subdomaim_length)

    #Перевірка на https
    features.append(int(parsed.scheme.lower() == "https"))
    features.append(is_ip(url))

    # Мережеві ознаки

    # Інші ознаки
    features.extend(extract_specific_symbols(url=url, domain=domain))
    features.extend(extract_entropy_features(url=url))
    features.extend(extract_trigger_features(url))
    features.extend(extract_domain_features(url))
    features.extend(extract_structure_features(url))
    features.extend(extract_character_features(url))

    return features
    

def is_ip(url: str) -> int:
    hostname = urlparse(url).hostname

    try:
        ipaddress.ip_address(hostname)
        return 1
    except (ValueError, TypeError):
        return 0


def extract_specific_symbols(url: str, domain: str) -> list:
    """Функція яка приймає аргументи (url: str, domain: str) и повертає symbols_features list"""
    symbols_features = []
    
    symbols_features.append(domain.count("-"))
    symbols_features.append(url.count("//"))
    symbols_features.append(url.count("%"))
    symbols_features.append(url.count("="))

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


def extract_domain_features(url: str) -> list:
    ext = tldextract.extract(url) 

    domain = ext.domain
    subdomain = ext.subdomain
    suffix = ext.suffix

    return [
        len(domain),
        len(subdomain.split(".")) if subdomain else 0,
        len(suffix),
        sum(c.isdigit() for c in domain),
        sum(c.isalpha() for c in domain),
        int(any(c.isdigit() for c in domain))
    ]


def extract_structure_features(url: str) -> list:
    parsed = urlparse(url)

    return [
        url.count("/"),
        url.count("?"),
        url.count("="),
        url.count("&"),
        url.count("@"),
        url.count("#"),
        len(parsed.params),
        int(parsed.port is not None),
    ]


def extract_character_features(url: str) -> list:
    length = max(len(url), 1)

    digits = sum(c.isdigit() for c in url)
    letters = sum(c.isalpha() for c in url)
    uppercase = sum(c.isupper() for c in url)

    return [
        round(digits / length, 4),
        round(letters / length, 4),
        round(uppercase / length, 4),
        int("--" in url),
        int(".." in url),
        int("%%" in url),
    ]

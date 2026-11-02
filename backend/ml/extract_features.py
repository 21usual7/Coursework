import re
import math
import tldextract
from urllib.parse import urlparse
from collections import Counter
import ipaddress

TRIGGERS = [
    "login", "signin", "verify", "verification", "authenticate", "account",
    "security", "secure", "password", "reset", "recover", "unlock", "confirm",
    "confirmation", "validate", "wallet", "payment", "billing", "invoice",
    "support", "alert", "warning", "suspended", "blocked", "update", "activate",
    "authorization", "2fa", "mfa", "credential", "signin", "logon", "auth"
]

SUSPICIOUS_TLDS = {
    "tk", "ml", "ga", "cf", "gq", "xyz", "top", "icu", "work", "click",
    "link", "online", "site", "website", "space", "fun", "live", "club",
    "pw", "cc", "ws", "info", "biz", "name", "pro"
}

BRAND_KEYWORDS = {
    "paypal", "apple", "google", "microsoft", "amazon", "facebook", "instagram",
    "netflix", "spotify", "dropbox", "adobe", "chase", "wellsfargo", "bankofamerica",
    "citi", "hsbc", "barclays", "dhl", "fedex", "ups", "irs", "gov", "secure"
}


def extract_features(url: str) -> list:
    """Сильний набір ознак для детекції фішингу. Стійкий до довгих легітимних URL."""
    assert isinstance(url, str), "URL must be a string"
    
    url = url.strip()
    if not url:
        return [0.0] * 35

    parsed = urlparse(url)
    ext = tldextract.extract(url)
    length = max(len(url), 1)
    hostname = parsed.hostname or ""

    features = []

    # === 1. Базові ===
    features.append(len(ext.subdomain))                         
    features.append(int(parsed.scheme.lower() == "https")) 
    features.append(_is_ip(hostname))                     

    # === 2. Символьні ratios ===
    features.extend(_symbol_ratios(url, length, hostname))

    # === 3. Ентропія ===
    features.extend(_entropy_features(url, ext))

    # === 4. Тригери ===
    features.extend(_trigger_features(url))

    # === 5. Доменні ознаки ===
    features.extend(_domain_features(ext, hostname))

    # === 6. Структурні ratios + порт ===
    features.extend(_structure_features(url, parsed, length))

    # === 7. Символьні ratios + підозрілі послідовності ===
    features.extend(_character_features(url, length))

    # === 8. Нові сильні ознаки ===
    features.extend(_advanced_features(url, parsed, ext, hostname, length))

    return features


def _is_ip(hostname: str) -> int:
    if not hostname:
        return 0
    try:
        ipaddress.ip_address(hostname)
        return 1
    except (ValueError, TypeError):
        return 0


def _symbol_ratios(url: str, length: int, hostname: str) -> list:
    special = len(re.sub(r'[a-zA-Z0-9.:/\-]', '', url))
    return [
        hostname.count("-"),                
        url.count("//") / length,
        url.count("%") / length,
        url.count("=") / length,
        special / length,
        round(special / length, 4)
    ]


def _calc_shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    length = len(text)
    counts = Counter(text)
    return round(-sum((c / length) * math.log2(c / length) for c in counts.values()), 4)


def _entropy_features(url: str, ext) -> list:
    domain_part = f"{ext.subdomain}.{ext.domain}" if ext.subdomain else (ext.domain or "")
    return [
        _calc_shannon_entropy(domain_part),
        _calc_shannon_entropy(url)
    ]


def _trigger_features(url: str) -> list:
    tokens = set(re.split(r'[-_./?=&:%#@]', url.lower()))
    matched = tokens.intersection(TRIGGERS)
    count = len(matched)
    return [count, int(count > 0)]


def _domain_features(ext, hostname: str) -> list:
    domain = ext.domain or ""
    subdomain = ext.subdomain or ""
    suffix = ext.suffix or ""

    return [
        len(domain),
        len(subdomain.split(".")) if subdomain else 0,   
        len(suffix),
        sum(c.isdigit() for c in domain),
        sum(c.isalpha() for c in domain),
        int(any(c.isdigit() for c in domain)),
        int(any(c.isdigit() for c in subdomain)),
    ]


def _structure_features(url: str, parsed, length: int) -> list:
    try:
        has_port = int(parsed.port is not None)
    except ValueError:
        has_port = 0

    path_len = len(parsed.path or "")
    return [
        url.count("/") / length,
        url.count("?") / length,
        url.count("=") / length,
        url.count("&") / length,
        url.count("@") / length,
        url.count("#") / length,
        has_port,
        path_len / length,    
    ]


def _character_features(url: str, length: int) -> list:
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


def _advanced_features(url: str, parsed, ext, hostname: str, length: int) -> list:
    subdomain = (ext.subdomain or "").lower()
    domain = (ext.domain or "").lower()
    suffix = (ext.suffix or "").lower()
    full_host = hostname.lower()

    # 1. Підозрілий TLD
    is_suspicious_tld = int(suffix in SUSPICIOUS_TLDS)

    # 2. Багато рівнів субдомену (≥ 3)
    subdomain_levels = len(subdomain.split(".")) if subdomain else 0
    many_subdomains = int(subdomain_levels >= 3)

    # 3. Наявність @ (дуже підозріло)
    has_at = int("@" in url)

    # 4. Brand keyword у субдомені (класичний фішинг)
    has_brand_in_subdomain = int(any(brand in subdomain for brand in BRAND_KEYWORDS))

    # 5. Brand keyword у домені, але TLD підозрілий
    has_brand_suspicious_tld = int(
        any(brand in domain for brand in BRAND_KEYWORDS) and suffix in SUSPICIOUS_TLDS
    )

    # 6. Довгий hostname (але відносно)
    hostname_len_ratio = len(hostname) / length if hostname else 0

    # 7. Чи є цифри + літери впереміш у домені (часто в згенерованих)
    mixed_alnum_domain = int(
        bool(re.search(r'[a-zA-Z]', domain)) and bool(re.search(r'\d', domain))
    )

    return [
        is_suspicious_tld,
        many_subdomains,
        has_at,
        has_brand_in_subdomain,
        has_brand_suspicious_tld,
        round(hostname_len_ratio, 4),
        mixed_alnum_domain,
    ]

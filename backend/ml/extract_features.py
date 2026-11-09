import re
import math
import ipaddress
from collections import Counter
from urllib.parse import urlparse

import tldextract


TRIGGERS = {
    "login", "signin", "verify", "verification", "authenticate",
    "account", "security", "secure", "password", "reset", "recover",
    "unlock", "confirm", "confirmation", "validate", "wallet",
    "payment", "billing", "invoice", "support", "alert", "warning",
    "suspended", "blocked", "update", "activate", "authorization",
    "2fa", "mfa", "credential", "logon", "auth"
}

SUSPICIOUS_TLDS = {
    "tk", "ml", "ga", "cf", "gq", "xyz", "top", "icu", "work",
    "click", "link", "online", "site", "website", "space", "fun",
    "live", "club", "pw", "cc", "ws", "info", "biz", "name", "pro"
}

BRAND_KEYWORDS = {
    "paypal", "apple", "google", "microsoft", "amazon", "facebook",
    "instagram", "netflix", "spotify", "dropbox", "adobe", "chase",
    "wellsfargo", "bankofamerica", "citi", "hsbc", "barclays",
    "dhl", "fedex", "ups", "irs"
}

SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "is.gd", "t.ly",
    "tiny.cc", "ow.ly", "buff.ly", "cutt.ly", "rb.gy",
    "rebrand.ly", "short.io", "lnkd.in", "soo.gd"
}

EXTRACTOR = tldextract.TLDExtract(suffix_list_urls=None)


_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")
_WWW_RE = re.compile(r"^www\d?\.", re.IGNORECASE)


def normalize_url(url: str) -> str:
    '''Приводить URL до єдиного вигляду: без схеми, "www." та #фрагмента.
    '''
    url = url.strip()
    url = _SCHEME_RE.sub("", url)
    url = _WWW_RE.sub("", url)
    url = url.split("#", 1)[0]
    # прибираємо лише кінцевий "/" у корені ("site.com/" == "site.com")
    if url.endswith("/") and url.count("/") == 1:
        url = url[:-1]
    return url


def extract_features(url: str) -> list:
    if not isinstance(url, str):
        raise TypeError("URL must be a string")

    url = normalize_url(url)

    if not url:
        raise ValueError("URL cannot be empty")

    # схема потрібна лише для коректного розбору hostname
    try:
        parsed = urlparse("http://" + url)
    except ValueError:
        # напр. "Invalid IPv6 URL" для сміттєвих URL з "[" у хості
        parsed = urlparse("http://" + url.replace("[", "").replace("]", ""))
    hostname = (parsed.hostname or "").lower()

    ext = EXTRACTOR(url)

    domain = (ext.domain or "").lower()
    subdomain = (ext.subdomain or "").lower()
    suffix = (ext.suffix or "").lower()

    length = max(len(url), 1)

    features = []

    # 1. Basic features (2)
    # is_https прибрано: у датасеті схема — це "витік" мітки класу
    features.extend([
        len(subdomain),
        _is_ip(hostname)
    ])

    # 2. Symbol features (5)
    features.extend(
        _symbol_features(url, hostname, length)
    )

    # 3. Entropy (2)
    domain_part = (
        f"{subdomain}.{domain}" if subdomain else domain
    )

    features.extend([
        _entropy(domain_part),
        _entropy(url)
    ])

    # 4. Trigger words (6)
    features.extend(
        _trigger_features(parsed)
    )

    # 5. Domain features (7)
    features.extend(
        _domain_features(domain, subdomain, suffix)
    )

    # 6. URL structure (8)
    features.extend(
        _structure_features(url, parsed, length)
    )

    # 7. Character features (6)
    features.extend(
        _character_features(url, length)
    )

    # 8. Advanced features (7)
    features.extend(
        _advanced_features(
            url, hostname, domain, subdomain, suffix, length
        )
    )

    # 9. Additional features (4)
    features.extend(
        _additional_features(url, parsed, hostname)
    )

    assert len(features) == N_FEATURES, (
        f"Expected {N_FEATURES} features, got {len(features)}"
    )

    return features


def _is_ip(hostname: str) -> int:
    if not hostname:
        return 0

    try:
        ipaddress.ip_address(hostname)
        return 1
    except ValueError:
        return 0


def _entropy(text: str) -> float:
    if not text:
        return 0.0

    length = len(text)
    counts = Counter(text)

    return round(
        -sum(
            (count / length) * math.log2(count / length)
            for count in counts.values()
        ),
        4
    )


def _symbol_features(url: str, hostname: str, length: int) -> list:
    special = len(re.sub(r"[a-zA-Z0-9.:/\-]", "", url))

    return [
        hostname.count("-"),
        url.count("//") / length,
        url.count("%") / length,
        url.count("=") / length,
        round(special / length, 4)
    ]


def _count_triggers(text: str) -> int:
    tokens = set(re.split(r"[-_./?=&:%#@]", text.lower()))
    return len(tokens.intersection(TRIGGERS))


def _trigger_features(parsed) -> list:
    hostname = parsed.hostname or ""
    path = parsed.path or ""
    query = parsed.query or ""

    host_count = _count_triggers(hostname)
    path_count = _count_triggers(path)
    query_count = _count_triggers(query)

    return [
        host_count,
        path_count,
        query_count,
        int(host_count > 0),
        int(path_count > 0),
        int(query_count > 0)
    ]


def _domain_features(domain: str, subdomain: str, suffix: str) -> list:
    return [
        len(domain),
        len(subdomain.split(".")) if subdomain else 0,
        len(suffix),
        sum(c.isdigit() for c in domain),
        sum(c.isalpha() for c in domain),
        int(any(c.isdigit() for c in domain)),
        int(any(c.isdigit() for c in subdomain))
    ]


def _structure_features(url: str, parsed, length: int) -> list:
    try:
        has_port = int(parsed.port is not None)
    except ValueError:
        has_port = 0

    path = parsed.path or ""

    return [
        url.count("/") / length,
        url.count("?") / length,
        url.count("=") / length,
        url.count("&") / length,
        url.count("@") / length,
        url.count("#") / length,
        has_port,
        len(path) / length
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
        int("%%" in url)
    ]


def _advanced_features(
    url: str,
    hostname: str,
    domain: str,
    subdomain: str,
    suffix: str,
    length: int
) -> list:

    subdomain_levels = len(subdomain.split(".")) if subdomain else 0

    has_brand_in_subdomain = int(
        any(brand in subdomain.split(".") for brand in BRAND_KEYWORDS)
    )

    has_brand_suspicious_tld = int(
        any(brand in domain for brand in BRAND_KEYWORDS)
        and suffix in SUSPICIOUS_TLDS
    )

    mixed_alnum_domain = int(
        bool(re.search(r"[a-zA-Z]", domain))
        and bool(re.search(r"\d", domain))
    )

    return [
        int(suffix in SUSPICIOUS_TLDS),
        int(subdomain_levels >= 3),
        int("@" in url),
        has_brand_in_subdomain,
        has_brand_suspicious_tld,
        round(len(hostname) / length, 4) if hostname else 0,
        mixed_alnum_domain
    ]


def _additional_features(
    url: str,
    parsed,
    hostname: str
) -> list:

    normalized_host = hostname.removeprefix("www.")

    return [
        len(url),
        url.count("."),
        int("//" in (parsed.path or "")),
        int(normalized_host in SHORTENERS)
    ]


def get_feature_names() -> list:
    return [
        # Basic
        "subdomain_length",
        "is_ip",

        # Symbols
        "hostname_hyphens",
        "double_slash_ratio",
        "percent_ratio",
        "equals_ratio",
        "special_char_ratio",

        # Entropy
        "domain_entropy",
        "url_entropy",

        # Triggers
        "host_trigger_count",
        "path_trigger_count",
        "query_trigger_count",
        "host_has_trigger",
        "path_has_trigger",
        "query_has_trigger",

        # Domain
        "domain_length",
        "subdomain_levels",
        "suffix_length",
        "domain_digit_count",
        "domain_letter_count",
        "domain_has_digits",
        "subdomain_has_digits",

        # Structure
        "slash_ratio",
        "question_ratio",
        "equals_structure_ratio",
        "ampersand_ratio",
        "at_ratio",
        "hash_ratio",
        "has_port",
        "path_length_ratio",

        # Characters
        "digit_ratio",
        "letter_ratio",
        "uppercase_ratio",
        "has_double_hyphen",
        "has_double_dot",
        "has_double_percent",

        # Advanced
        "is_suspicious_tld",
        "many_subdomains",
        "has_at",
        "has_brand_in_subdomain",
        "has_brand_suspicious_tld",
        "hostname_length_ratio",
        "mixed_alnum_domain",

        # Additional
        "url_length",
        "dot_count",
        "path_has_double_slash",
        "is_shortened_url"
    ]


N_FEATURES = len(get_feature_names())

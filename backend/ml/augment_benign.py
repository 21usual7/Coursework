'''Генерує додаткові "чисті" (benign) URL з рейтингу популярних сайтів Tranco.

Навіщо: у malicious_phish.csv benign-клас — це переважно довгі глибокі посилання
з кількох сайтів (youtube, amazon...), а phishing — короткі домени. Модель вчиться
правилу "короткий URL = фішинг" і блокує звичайні сайти (bbc.com/news, github.com).
Домашні сторінки популярних сайтів виправляють цей перекіс.

Використання:
    1. Завантажити https://tranco-list.eu/top-1m.csv.zip і розпакувати top-1m.csv
    2. python ml/augment_benign.py шлях/до/top-1m.csv
    -> створює ml/tranco_benign.csv (url,type)
'''
import random
import sys
from pathlib import Path

import pandas as pd
import tldextract

ml_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(ml_dir.parent))
from ml.extract_features import normalize_url

TOP_N = 50_000          # нижче в рейтингу трапляються спамні / шкідливі домени
OUT_PATH = ml_dir / "tranco_benign.csv"
DATASET = ml_dir / "malicious_phish_cleaned.csv"

# типові шляхи реальних сайтів; навмисно є й "login"/"account" —
# саме слово в шляху ще не означає фішинг
COMMON_PATHS = [
    "", "", "", "",  # частіше — просто домен
    "/news", "/about", "/contact", "/login", "/account", "/search?q=test",
    "/help", "/blog", "/products", "/en/", "/support", "/signin",
    "/index.html", "/category/sport", "/watch?v=dQw4w9WgXcQ",
    "/2024/05/article-title", "/user/profile", "/docs/getting-started",
]
SUBDOMAINS = ["", "", "", "", "", "en.", "m.", "mail.", "app.", "docs."]

EXTRACTOR = tldextract.TLDExtract(suffix_list_urls=None)


def main(tranco_csv: str):
    rnd = random.Random(42)
    top = pd.read_csv(tranco_csv, header=None, names=["rank", "domain"], nrows=TOP_N)

    # домени, що вже мають шкідливі мітки в датасеті (хостинги, зламані сайти) — пропускаємо
    data = pd.read_csv(DATASET)
    bad = data[data["type"] != "benign"]["url"].astype(str).map(normalize_url)
    bad_domains = set(bad.map(lambda u: EXTRACTOR(u).top_domain_under_public_suffix))

    rows = []
    for domain in top["domain"]:
        if domain in bad_domains:
            continue
        url = rnd.choice(SUBDOMAINS) + domain + rnd.choice(COMMON_PATHS)
        rows.append({"url": url, "type": "benign"})

    pd.DataFrame(rows).to_csv(OUT_PATH, index=False)
    print(f"збережено {len(rows)} URL (пропущено {TOP_N - len(rows)}) у {OUT_PATH}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])

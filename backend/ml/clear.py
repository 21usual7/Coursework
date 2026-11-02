import pandas as pd
import tldextract
from urllib.parse import urlparse
from collections import Counter

# === Налаштування ===
INPUT_FILE = "malicious_phish.csv"
OUTPUT_FILE = "malicious_phish_cleaned.csv"

# Домени, які майже напевно не є фішингом (додавай сюди)
LEGIT_DOMAINS = {
    # Ігрові сайти (найбільше сміття)
    "ign.com", "gamespot.com", "gamefaqs.com", "gamepro.com", "gamespy.com",
    "1up.com", "teamxbox.com", "gametrailers.com", "gamesradar.com", "eurogamer.net",
    "gameinformer.com", "kotaku.com", "polygon.com", "destructoid.com", "rockpapershotgun.com",
    "pcgamer.com", "gamespot.com", "metacritic.com", "mobygames.com", "giantbomb.com",
    "neoseeker.com", "cheatcc.com", "gamefaqs.gamespot.com",

    # Великі легітимні
    "wikipedia.org", "wikia.com", "fandom.com", "youtube.com", "youtu.be",
    "reddit.com", "twitter.com", "x.com", "facebook.com", "instagram.com",
    "linkedin.com", "github.com", "stackoverflow.com", "stackexchange.com",
    "medium.com", "blogspot.com", "wordpress.com", "tumblr.com",
    "amazon.com", "ebay.com", "etsy.com", "walmart.com", "target.com",
    "nytimes.com", "bbc.com", "bbc.co.uk", "cnn.com", "theguardian.com",
    "forbes.com", "bloomberg.com", "reuters.com", "washingtonpost.com",
    "imdb.com", "rottentomatoes.com", "metacritic.com",
    "apple.com", "microsoft.com", "google.com", "yahoo.com", "bing.com",
    "netflix.com", "spotify.com", "twitch.tv", "discord.com", "steamcommunity.com",
    "steampowered.com", "roblox.com",
    "nih.gov", "edu", "gov", "ac.uk", "edu.au",

    # Українські / локальні
    "prom.ua", "rozetka.ua", "olx.ua", "allo.ua", "comfy.ua", "epicentrk.ua",
    "ukr.net", "i.ua", "meta.ua", "sinoptik.ua",
}

# Домени, які часто зустрічаються в шумі (можна розширювати)
SUSPICIOUS_LEGIT_PATTERNS = [
    "ign.com", "gamespot", "gamefaqs", "gamepro", "gamespy", "1up.com",
    "teamxbox", "gametrailers", "gamesradar", "eurogamer", "neoseeker",
    "cheatcc", "mobygames", "giantbomb"
]


def get_registered_domain(url: str) -> str:
    """Повертає registered domain (domain + suffix)"""
    try:
        if not url.startswith(("http://", "https://")):
            url = "http://" + url
        ext = tldextract.extract(url)
        if ext.domain and ext.suffix:
            return f"{ext.domain}.{ext.suffix}".lower()
        return ""
    except Exception:
        return ""


def is_likely_legit(url: str, label: str) -> bool:
    """Перевіряє, чи URL майже напевно легітимний (і його треба прибрати з phishing)"""
    if label.lower() not in ("phishing", "malicious"):
        return False

    domain = get_registered_domain(url)
    if not domain:
        return False

    # Пряме попадання в білий список
    if domain in LEGIT_DOMAINS:
        return True

    # Перевірка по патернах
    domain_lower = domain.lower()
    for pattern in SUSPICIOUS_LEGIT_PATTERNS:
        if pattern in domain_lower:
            return True

    # Додатково: якщо домен закінчується на .edu / .gov / .ac.uk тощо
    if domain.endswith((".edu", ".gov", ".ac.uk", ".edu.au", ".gov.uk")):
        return True

    return False


def main():
    print("Завантаження датасету...")
    df = pd.read_csv(INPUT_FILE)

    print(f"Всього записів: {len(df)}")
    print("Розподіл до очищення:")
    print(df["type"].value_counts())
    print()

    # Знаходимо рядки, які потрібно видалити
    mask_to_remove = df.apply(
        lambda row: is_likely_legit(str(row["url"]), str(row["type"])),
        axis=1
    )

    removed_count = mask_to_remove.sum()
    print(f"Знайдено підозрілих (ймовірно помилкових) phishing/malicious: {removed_count}")

    if removed_count > 0:
        # Показуємо приклади того, що прибираємо
        print("\nПриклади того, що буде видалено:")
        examples = df[mask_to_remove][["url", "type"]].head(15)
        print(examples.to_string())

        # Видаляємо
        df_cleaned = df[~mask_to_remove].copy()
    else:
        df_cleaned = df.copy()

    print(f"\nЗаписів після очищення: {len(df_cleaned)}")
    print("Розподіл після очищення:")
    print(df_cleaned["type"].value_counts())

    # Зберігаємо
    df_cleaned.to_csv(OUTPUT_FILE, index=False)
    print(f"\nОчищений датасет збережено в: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

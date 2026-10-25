import requests
import os
from dotenv import load_dotenv

load_dotenv()

SAFE_BROWSING_API_KEY = os.getenv("GSB_API_KEY") # Треба зробити локальний .env файл з api ключем google safe browsing і додати його в .gitignore

def check_google_safe_browsing(url: str) -> bool:
    '''Перевіряє URL через Google Safe Browsing API. Повертає True якщо сайт знайдено в базі небезпечних посилань. False - якщо не знайдено або виникла помилка'''

    if not SAFE_BROWSING_API_KEY:
        return False

    api_url = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={SAFE_BROWSING_API_KEY}"

    payload = {
        "client": {
            "clientId": "phishing-detector-coursework",
            "clientVersion": "1.0"
        },
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [
                {"url": url}
            ]
        }
    }

    try:
        response = requests.post(api_url, json=payload, timeout=2)

        if response.status_code == 200:
            data = response.json()
            if "matches" in data and len(data["matches"]) > 0:
                return True
            return False
    except Exception:
        return False
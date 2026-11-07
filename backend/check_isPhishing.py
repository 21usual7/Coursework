import joblib
import os
import numpy as np
from ml.extract_features import extract_features, EXTRACTOR, SHORTENERS
from check_rules import check_rules
from check_ssl_and_redirects import check_redirects
from safebrowsing import check_google_safe_browsing

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(BASE_DIR, "ml", "coursework.pkl")

# Поріг обрано за training_metrics.txt: при 0.6 precision ≈ 0.95, recall ≈ 0.65, FPR ≈ 1.6%
THRESHOLD = 0.6

# "Сіра зона": модель не впевнена, тому варто подивитися, куди веде посилання
GRAY_ZONE = 0.3

model = joblib.load(MODEL_PATH)

def check_url(url, follow_redirects=True):
    if model is None:
        raise RuntimeError("Модель не завантажена")

    features = extract_features(url)
    features_array = np.array(features).reshape(1, -1)

    phishing_prob = 0.0
    probabilities = model.predict_proba(features_array)[0]
    classes = list(model.classes_)

    # У моделі 4 класи (benign / defacement / malware / phishing), класу 'malicious' немає.
    # Небезпечний = будь-який клас, крім benign, тому ймовірність = 1 - P(benign)
    benign_idx = classes.index('benign')
    phishing_prob = float(1 - probabilities[benign_idx])

    threat_type = str(classes[probabilities.argmax()])

    # правила ловлять очевидний фішинг, який модель пропускає (paypal-login-verify.xyz),
    # тому беремо більшу з двох оцінок
    rules = check_rules(url)
    if rules["score"] > phishing_prob:
        phishing_prob = rules["score"]
        threat_type = "phishing"

    reasons = rules["reasons"]

    # Мережева перевірка (повільна, до кількох секунд) - лише для коротких посилань
    # і "сірої зони". Якщо посилання веде на інший домен, перевіряємо кінцеву адресу
    # тією ж моделлю й правилами і беремо більшу оцінку
    domain = EXTRACTOR(url).top_domain_under_public_suffix
    if follow_redirects and (domain in SHORTENERS or GRAY_ZONE <= phishing_prob < THRESHOLD):
        final_url = check_redirects(url)["final_url"]
        final_domain = EXTRACTOR(final_url).top_domain_under_public_suffix

        if final_domain and final_domain != domain:
            final = check_url(final_url, follow_redirects=False)
            if final["probability"] > phishing_prob:
                phishing_prob = final["probability"]
                threat_type = final["threat_type"]
                reasons = [f"перенаправляє на {final_domain}"] + final["reasons"]

    # База відомих загроз Google: ловить те, що за виглядом URL не визначити
    # (зламані сайти, фішинг зі "звичайною" адресою). Модель і правила - для нових загроз
    if check_google_safe_browsing(url):
        phishing_prob = 1.0
        threat_type = "phishing"
        reasons = ["є в базі Google Safe Browsing"] + reasons

    is_phishing = bool(phishing_prob >= THRESHOLD)

    return {"is_phishing": is_phishing, "probability": round(phishing_prob, 4), "threat_type": threat_type, "reasons": reasons}

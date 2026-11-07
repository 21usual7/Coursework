import joblib
import os
import numpy as np
from ml.extract_features import extract_features

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(BASE_DIR, "ml", "coursework.pkl")

# Поріг обрано за training_metrics.txt: при 0.6 precision ≈ 0.95, recall ≈ 0.65, FPR ≈ 1.6%
THRESHOLD = 0.6

model = joblib.load(MODEL_PATH)

def check_url(url):
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

    is_phishing = bool(phishing_prob >= THRESHOLD)

    return {"is_phishing": is_phishing, "probability": round(phishing_prob, 4), "threat_type": threat_type}

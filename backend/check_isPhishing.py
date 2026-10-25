import joblib
import os
import numpy as np
from flask import request
from ml.extract_features import extract_features
from safebrowsing import check_google_safe_browsing

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "ml", "coursework.pkl")

model = joblib.load(MODEL_PATH)

def check_url(url):
    if model is None:
        raise RuntimeError("Модель не завантажена")

    is_known_phishing = check_google_safe_browsing(url)
    if is_known_phishing:
        return {
            "is_phishing": True, 
            "probability": 1.0,
            "source": "Google Safe Browsing (Database)",
            "ssl_valid": 0,
            "redirects_count": 0
        }
    
    features = extract_features(url)
    features_array = np.array(features).reshape(1, -1)

    prediction = model.predict(features_array)[0]

    phishing_prob = 0.0
    probabilities = model.predict_proba(features_array)[0]
    classes = list(model.classes_)

    malicious_idx = classes.index('malicious') if 'malicious' in classes else 1
    phishing_prob = probabilities[malicious_idx]

    is_phishing = bool(phishing_prob > 0.5)

    return {
        "is_phishing": is_phishing, 
        "probability": phishing_prob,
        "source": "Machine Learning Model",
        "ssl_valid": features[2] if len(features) > 2 else 0,
        "redirects_count": features[4] if len(features) > 4 else 0
    }


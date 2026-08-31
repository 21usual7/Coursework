import joblib
from flask import request
from ml.extract_features import extract_features

model = joblib.load("ml/coursework.pkl")


def check_url(url):
    if model is None:
        raise RuntimeError("Модель не завантажена")

    features = extract_features(url)
    prediction = model.predict(features)[0]  

    phishing_prob = 0.0
    probabilities = model.predict_proba(features)[0]
    classes = list(model.classes_)

    malicious_idx = classes.index('malicious') if 'malicious' in classes else 1
    phishing_prob = probabilities[malicious_idx]

    is_phishing = bool(prediction == 1)

    return {"is_phishing": is_phishing, "probability": phishing_prob}

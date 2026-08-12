from flask import Flask
import joblib
import pandas as pd
from extract_features import extract_features
from GUARD_PROJECT.ml.train_GUARD import NAMES

app = Flask(name)
@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"
mod = joblib.load("coursework.pkl")

def check_url(url):
    features = extract_features(url)
    X_new = pd.DataFrame([features], columns=NAMES)

    prediction = mod.predict(X_new)[0]
    probability = mod.proba(X_new)[0][1]

    return prediction, probability

if __name__ == "__main__":
    test_url = input("Введіть URL: ")
    is_phishing, prob = check_url(test_url)

    print(f"Фішинг з ймовірністю {prob * 100:.1f}%") if is_phishing == 1 else print(f"Безпечно з ймовірністю {prob * 100:.1f}%")
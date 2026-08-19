import sys
from pathlib import Path
from database import close_db, get_all_users
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import joblib
import pandas as pd
from flask import Flask
from ml.extract_features import extract_features


app = Flask(__name__)


app.teardown_appcontext(close_db)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


mod = joblib.load(BASE_DIR / "coursework.pkl")


def check_url(url):
    features = extract_features(url)
    X_new = pd.DataFrame([features])

    prediction = mod.predict(X_new)[0]  

    classes = list(mod.classes_)
    malicious_idx = classes.index('malicious') if 'malicious' in classes else 1

    probabilities = mod.predict_proba(X_new)[0]
    phishing_prob = probabilities[malicious_idx]

    return prediction, phishing_prob


@app.route('/register', ['GET', 'POST'])
def register():
    pass


@app.route('login', ['GET', 'POST'])


    

if __name__ == "__main__":
    test_url = input("Введіть URL: ")
    verdict, prob = check_url(test_url)

    if verdict in ['malicious', 1]:
        print(f"🚨 Фішинг з ймовірністю {prob * 100:.1f}%")
    else:
        print(f"✅ Безпечно з ймовірністю {(1 - prob) * 100:.1f}%")
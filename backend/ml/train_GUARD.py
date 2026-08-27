import os
import sys
import joblib
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix

ML_DIR = Path(__file__).resolve().parent
PROJECT_DIR = ML_DIR.parent

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from ml.extract_features import extract_features

NAMES = [
    "url_length",
    "has_https",
    "is_ip",
    "is_specific_symbols",
    "shannon_entropy",
    "trigger_features",
]

def train():
    csv_in_project = PROJECT_DIR / "balanced_urls.csv"
    csv_in_ml = ML_DIR / "balanced_urls.csv"

    if csv_in_project.exists():
        csv_path = csv_in_project
    elif csv_in_ml.exists():
        csv_path = csv_in_ml
    else:
        print(f"❌ ОШИБКА: Файл balanced_urls.csv не найден!")
        print(f"Содержимое {PROJECT_DIR}: {os.listdir(PROJECT_DIR)}")
        return

    print(f"Загрузка датасета из: {csv_path}")
    data = pd.read_csv(csv_path)

    print("Извлечение признаков...")
    X_raw = [extract_features(str(url)) for url in data["url"]]
    X = pd.DataFrame(X_raw)
    y = data["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print("Обучение модели...")
    mod = RandomForestClassifier(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1)
    mod.fit(X_train, y_train)

    y_pred = mod.predict(X_test)

    print("\n--- Отчет о качестве ---")
    print(classification_report(y_test, y_pred))
    print("Матрица ошибок:")
    print(confusion_matrix(y_test, y_pred))

    model_save_path = PROJECT_DIR / "coursework.pkl"
    joblib.dump(mod, model_save_path)
    print(f"\nМодель успешно сохранена в: {model_save_path}")

if __name__ == "__main__":
    train()
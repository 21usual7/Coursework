import os
import sys
import joblib
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from tqdm import tqdm

ML_DIR = Path(__file__).resolve().parent
PROJECT_DIR = ML_DIR.parent

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from ml.extract_features import extract_features


def train():
    csv_in_project = PROJECT_DIR / "malicious_phish_cleaned.csv"
    csv_in_ml = ML_DIR / "malicious_phish_cleaned.csv"

    if csv_in_project.exists():
        csv_path = csv_in_project
    elif csv_in_ml.exists():
        csv_path = csv_in_ml
    else:
        print(f"ПОМИЛКА: Файл balanced_urls.csv не знайдено")
        print(f"Вміст {PROJECT_DIR}: {os.listdir(PROJECT_DIR)}")
        return

    print(f"Завантаження датасета з: {csv_path}")
    data = pd.read_csv(csv_path)

    print("Вилучення ознак...")
    urls = [str(url) for url in data["url"]]

    # Послідовний обхід через простий цикл з прогрес-баром
    X_raw = [extract_features(url) for url in tqdm(urls, desc="Екстракція фіч")]

    X = pd.DataFrame(X_raw)
    y = data["type"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print("Навчання моделі...")
    mod = RandomForestClassifier(n_estimators=100, max_depth=12, class_weight='balanced', random_state=42, n_jobs=-1)
    mod.fit(X_train, y_train)

    y_pred = mod.predict(X_test)

    # Генерація результатів
    report_str = classification_report(y_test, y_pred)
    conf_matrix = confusion_matrix(y_test, y_pred)
    acc = accuracy_score(y_test, y_pred)

    print("\n--- Звіт про якість ---")
    print(report_str)
    print("Матриця помилок:")
    print(conf_matrix)

    # Збереження результатів у файл для звіту
    metrics_path = PROJECT_DIR / "training_metrics.txt"
    with open(metrics_path, "w", encoding="utf-8") as f:
        f.write("=== REZULTATI NAVCHANNYA MODELI GUARD ===\n\n")
        f.write(f"Всього рядків у датасеті: {len(data)}\n")
        f.write(f"Test Accuracy: {acc:.4f}\n\n")
        f.write("Classification Report:\n")
        f.write(report_str + "\n\n")
        f.write("Confusion Matrix:\n")
        f.write(str(conf_matrix) + "\n")

    print(f"\nМетрики успішно збережено у файл: {metrics_path}")

    model_save_path = PROJECT_DIR / "coursework.pkl"
    joblib.dump(mod, model_save_path)
    print(f"Модель успішно збережена в: {model_save_path}")

if __name__ == "__main__":
    train()

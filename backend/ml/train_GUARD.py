import os
import sys
import joblib
import pandas as pd
from pathlib import path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import randomforestclassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from tqdm import tqdm

ml_dir = path(__file__).resolve().parent
project_dir = ml_dir.parent

if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

from ml.extract_features import extract_features


def train():
    csv_in_project = project_dir / "malicious_phish_cleaned.csv"
    csv_in_ml = ml_dir / "malicious_phish_cleaned.csv"

    if csv_in_project.exists():
        csv_path = csv_in_project
    elif csv_in_ml.exists():
        csv_path = csv_in_ml
    else:
        print(f"помилка: файл .csv не знайдено")
        print(f"вміст {project_dir}: {os.listdir(project_dir)}")
        return

    print(f"завантаження датасета з: {csv_path}")
    data = pd.read_csv(csv_path)

    print("вилучення ознак...")
    urls = [str(url) for url in data["url"]]

    # послідовний обхід через простий цикл з прогрес-баром
    x_raw = [extract_features(url) for url in tqdm(urls, desc="екстракція фіч")]

    x = pd.dataframe(x_raw)
    y = data["type"]

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=42, stratify=y
    )

    print("навчання моделі...")
    mod = randomforestclassifier(n_estimators=100, max_depth=12, class_weight='balanced', random_state=42, n_jobs=-1)
    mod.fit(x_train, y_train)

    y_pred = mod.predict(x_test)

    # генерація результатів
    report_str = classification_report(y_test, y_pred)
    conf_matrix = confusion_matrix(y_test, y_pred)
    acc = accuracy_score(y_test, y_pred)

    print("\n--- звіт про якість ---")
    print(report_str)
    print("матриця помилок:")
    print(conf_matrix)

    # збереження результатів у файл для звіту
    metrics_path = project_dir / "training_metrics.txt"
    with open(metrics_path, "w", encoding="utf-8") as f:
        f.write("=== rezultati navchannya modeli guard ===\n\n")
        f.write(f"всього рядків у датасеті: {len(data)}\n")
        f.write(f"test accuracy: {acc:.4f}\n\n")
        f.write("classification report:\n")
        f.write(report_str + "\n\n")
        f.write("confusion matrix:\n")
        f.write(str(conf_matrix) + "\n")

    print(f"\nметрики успішно збережено у файл: {metrics_path}")

    model_save_path = project_dir / "coursework.pkl"
    joblib.dump(mod, model_save_path)
    print(f"модель успішно збережена в: {model_save_path}")

if __name__ == "__main__":
    train()

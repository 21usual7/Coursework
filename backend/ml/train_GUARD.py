import os
import sys
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, roc_auc_score, precision_recall_fscore_support
from tqdm import tqdm

ml_dir = Path(__file__).resolve().parent
project_dir = ml_dir.parent

if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

from ml.extract_features import extract_features, normalize_url, get_feature_names

SANITY_URLS = [
    "https://www.bbc.com/news",
    "http://www.bbc.com/news",
    "https://example.com/",
    "https://github.com/user/repo",
    "https://www.amazon.com/dp/B08N5WRWNW",
    "http://paypal-login-verify.xyz/signin",
    "http://secure-appleid.apple.com.verify-account.tk/login.php",
    "http://192.168.10.5/bank/update/index.php?acc=1",
]


def binary_metrics(y_true, proba, classes, threshold):
    '''Розширенню потрібна лише відповідь "небезпечно / ні", тому рахуємо метрики для P(не benign)'''
    p_bad = 1 - proba[:, list(classes).index("benign")]
    y_bad = (np.asarray(y_true) != "benign").astype(int)
    pred = (p_bad >= threshold).astype(int)
    p, r, f, _ = precision_recall_fscore_support(y_bad, pred, average="binary")
    fpr = ((pred == 1) & (y_bad == 0)).sum() / (y_bad == 0).sum()
    return {"auc": roc_auc_score(y_bad, p_bad), "precision": p, "recall": r, "f1": f, "fpr": fpr}


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
    data["source"] = "original"
    rows_raw = len(data)

    # додаткові benign-URL популярних сайтів (створюються augment_benign.py)
    extra_path = ml_dir / "tranco_benign.csv"
    if extra_path.exists():
        extra = pd.read_csv(extra_path)
        extra["source"] = "tranco"
        data = pd.concat([data, extra], ignore_index=True)
        print(f"додано {len(extra)} benign URL з {extra_path.name}")
    else:
        print("увага: tranco_benign.csv не знайдено, модель помилятиметься на звичайних сайтах")

    # дублікати рахуємо після нормалізації: "http://www.a.com" == "a.com"
    data["url"] = data["url"].astype(str)
    data["norm"] = data["url"].map(normalize_url)
    data = data[data["norm"] != ""]

    # URL-и з різними мітками - це шум, викидаємо
    n_labels = data.groupby("norm")["type"].nunique()
    conflicting = set(n_labels[n_labels > 1].index)
    data = data[~data["norm"].isin(conflicting)]
    data = data.drop_duplicates("norm").reset_index(drop=True)
    print(f"рядків після очистки: {len(data)} (конфліктних URL: {len(conflicting)})")

    print("вилучення ознак...")
    urls = [str(url) for url in data["url"]]

    # послідовний обхід через простий цикл з прогрес-баром
    x_raw = [extract_features(url) for url in tqdm(urls, desc="екстракція фіч")]

    x = pd.DataFrame(x_raw)
    y = data["type"]

    x_train, x_test, y_train, y_test, src_train, src_test = train_test_split(
        x, y, data["source"], test_size=0.2, random_state=42, stratify=y
    )

    print("навчання моделі...")
    mod = RandomForestClassifier(n_estimators=30, min_samples_leaf=3, random_state=42, n_jobs=-1)
    mod.fit(x_train.values, y_train)

    y_pred = mod.predict(x_test.values)
    proba = mod.predict_proba(x_test.values)

    # генерація результатів
    report_str = classification_report(y_test, y_pred, digits=4)
    conf_matrix = confusion_matrix(y_test, y_pred, labels=mod.classes_)
    acc = accuracy_score(y_test, y_pred)
    auc = binary_metrics(y_test, proba, mod.classes_, 0.5)["auc"]

    orig = (src_test == "original").values
    orig_acc = accuracy_score(y_test[orig], y_pred[orig])
    orig_m = binary_metrics(y_test[orig], proba[orig], mod.classes_, 0.6)
    tranco_fpr = (1 - proba[~orig][:, list(mod.classes_).index("benign")] >= 0.6).mean()

    importances = sorted(zip(get_feature_names(), mod.feature_importances_), key=lambda kv: -kv[1])[:15]

    print("\n--- звіт про якість ---")
    print(report_str)
    print("матриця помилок:")
    print(conf_matrix)
    print(f"ROC-AUC (benign vs небезпечний): {auc:.4f}")

    # збереження результатів у файл для звіту
    metrics_path = project_dir / "training_metrics.txt"
    with open(metrics_path, "w", encoding="utf-8") as f:
        f.write("=== rezultati navchannya modeli guard ===\n\n")
        f.write(f"всього рядків у датасеті: {rows_raw}, після очистки: {len(data)}\n")
        f.write(f"кількість ознак: {x.shape[1]}\n")
        f.write(f"test accuracy: {acc:.4f}\n\n")
        f.write("classification report:\n")
        f.write(report_str + "\n\n")
        f.write(f"confusion matrix ({list(mod.classes_)}):\n")
        f.write(str(conf_matrix) + "\n\n")

        f.write(f"бінарна задача (benign vs небезпечний), ROC-AUC = {auc:.4f}\n")
        for t in (0.4, 0.5, 0.6, 0.7, 0.8):
            m = binary_metrics(y_test, proba, mod.classes_, t)
            f.write(f"  поріг {t}: precision={m['precision']:.4f} recall={m['recall']:.4f} "
                    f"f1={m['f1']:.4f} FPR={m['fpr']:.4f}\n")

        f.write(f"\nлише оригінальний датасет: accuracy={orig_acc:.4f} ROC-AUC={orig_m['auc']:.4f} "
                f"(поріг 0.6: precision={orig_m['precision']:.4f} recall={orig_m['recall']:.4f})\n")
        f.write(f"хибні тривоги на популярних сайтах (Tranco, поріг 0.6): {tranco_fpr:.4f}\n")

        f.write("\nтоп-15 важливих ознак:\n")
        for name, imp in importances:
            f.write(f"  {name:<26} {imp:.4f}\n")

        f.write("\nперевірка на реальних URL (P(небезпечний), клас):\n")
        for url in SANITY_URLS:
            p = mod.predict_proba(np.array(extract_features(url)).reshape(1, -1))[0]
            p_bad = 1 - p[list(mod.classes_).index("benign")]
            f.write(f"  {p_bad:.2f}  {mod.classes_[p.argmax()]:<11} {url}\n")

    print(f"\nметрики успішно збережено у файл: {metrics_path}")

    # модель зберігаємо в ml/, бо саме звідси її читає check_isPhishing.py
    model_save_path = ml_dir / "coursework.pkl"
    joblib.dump(mod, model_save_path, compress=3)
    print(f"модель успішно збережена в: {model_save_path}")

if __name__ == "__main__":
    train()

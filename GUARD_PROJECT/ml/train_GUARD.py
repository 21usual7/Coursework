import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from extract_features import extract_features

NAMES = [
    "url_length",
    "has_https",
    "is_ip",
    "has_ssl_certificate",
    "count_redirects",
    "is_specific_symbols",
    "shannon_entropy",
    "trigger_features",
]

data = pd.read_csv("balanced_urls.csv")

X_raw = [extract_features(url) for url in data["url"]]
X = pd.DataFrame(X_raw)
y = data["label"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

mod = RandomForestClassifier(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1)
mod.fit(X_train, y_train)

y_pred = mod.predict(X_test)

class_rep = classification_report(y_test, y_pred)
conf_matrix = confusion_matrix(y_test, y_pred)

print(class_rep, conf_matrix)

joblib.dump(mod, "coursework.pkl")

print("Модель збережена")
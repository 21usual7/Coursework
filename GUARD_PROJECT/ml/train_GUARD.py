import pandas as pd
from matplotlib import pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from GUARD_PROJECT.Coursework.GUARD_PROJECT.extract_features import extract_features
data = pd.read_csv("balanced_urls.csv")

X = [extract_features(url) for url in data["url"]]
y = data["label"]
print(len(X))
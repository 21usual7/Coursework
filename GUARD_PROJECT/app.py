import sys
from pathlib import Path
from database import close_db, add_user, get_user, check_username, delete_user_from_db
from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import joblib
import pandas as pd
from flask import Flask, redirect, request, url_for, session
from ml.extract_features import extract_features

mod = joblib.load(BASE_DIR / "coursework.pkl")



#Ініцілізація FLASK
app = Flask(__name__)

app.teardown_appcontext(close_db)
app.secret_key = open('key').read()


@app.route("/")
def index():
    user = session.get('username')    
    return f"""<p>Hello, {user}
    You have loggin in your profile 
    </p>"""


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return f"""INFORMATION"""
    
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    
    session['username'] = username
    res = check_username()
    
    if res is None:
        return f"User arleady exists!"
    
    elif all([username, password, email]):
        hashed_password = generate_password_hash(password=password)
        add_user(username=username, password=hashed_password, email=email)
        return redirect(url_for("/"))
    
    return "Заполните все поля!", 400


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return f"""RENDER Template"""
    
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    
    hashed_password = generate_password_hash(password=password)
    user = get_user(email=email, password=hashed_password)

    if user:
        session['username'] = username
        session['user_id'] = user['user_id']
        
        return redirect(url_for("/"))

    return "Неверное имя пользователя или пароль", 401


@app.route("/delete/usr", methods=['GET', 'POST'])
def deelt() -> int: 
    if request.methods == "GET":
        return f"some_string"
    username = request.form.get('username')
    if session.get('username') == username:
        return delete_user_from_db(username=username)
    return f"U haven't login as {username}" 
    
    
@app.route("/api/scan", methods=['GET', 'POST']) #TODO
async def check_url(data: str):
    features = extract_features(data.url)
    X_new = pd.DataFrame([features])

    prediction = mod.predict(X_new)[0]  

    classes = list(mod.classes_)
    malicious_idx = classes.index('malicious') if 'malicious' in classes else 1

    probabilities = mod.predict_proba(X_new)[0]
    phishing_prob = probabilities[malicious_idx]

    return prediction, phishing_prob
    

if __name__ == "__main__":
    app.run(debug=True)
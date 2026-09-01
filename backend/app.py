import joblib
from flask import Flask, jsonify, request
from flask_cors import CORS
from check_isPhishing import check_url
from database import get_db, add_link, change_status
# сервер, который запущениый, обрабатывае т и принмает запросы от сервер воркер. 
# достает из них юрл ссылку, вызвает спец функцию, которая запускает можель и возвращает ответ
 
app = Flask(__name__)
CORS(app)

@app.route("/api/check_url", methods = ["POST"])
def api_scan():
    data = request.get_json()

    url = data["url"]

    try:
        result = check_url(url)

        add_link(1, url, 0)
        return jsonify({"status": "succes", "url": url, "is_phishing": result["is_phisging"], "probability": result["probability"]}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500



@app.route('/api/change/status')
def change_status():
    data = request.get_json()
    user_id, status = data.get['user_id'], data.get['status']
    try:  
        res = change_status(user_id, status)
        return jsonify({"response" : res})
    except Exception as e:
        return jsonify({"response" : "error"})
    

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=80)

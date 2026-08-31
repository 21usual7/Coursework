# сервер, который запущениый, обрабатывае т и принмает запросы от сервер воркер. 
# достает из них юрл ссылку, вызвает спец функцию, которая запускает можель и возвращает ответ

import joblib
from flask import Flask, jsonify, request
from flask_cors import CORS
from backend.check_isPhishing import check_url
 
app = Flask(__name__)
CORS(app)

@app.route("/api/check_url", methods = ["POST"])
def api_scan():
    data = request.get_json()

    url = data["url"]

    try:
        result = check_url(url)
        return jsonify({"status": "succes", "url": url, "is_phishing": result["is_phisging"], "probability": result["probability"]}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=80)
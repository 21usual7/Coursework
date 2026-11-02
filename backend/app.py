import joblib
from flask import Flask, jsonify, request
from flask_cors import CORS
from check_isPhishing import check_url
from database import get_db, add_link, change_status

'''Сервер, що приймає й оброблює запити від server_worker, дістає з них URL-посилання, викликає функцію, що запускає модель та повертає відповідь'''

app = Flask(__name__)
CORS(app)


@app.route("/", methods=["GET"])
def index():
    return "Welcome, to the backend server of GUARDI! Please, authorize!", 200


@app.route("/guardai/api/scan", methods = ["POST"])
def api_scan():
    data = request.get_json()

    url = data["url"]

    try:
        result = check_url(url)

        add_link(1, url, 0)
        return jsonify({"status": "succes", "url": url, "is_phishing": result["is_phisging"], "probability": result["probability"]}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=1337)

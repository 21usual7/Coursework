import joblib
from flask import Flask, jsonify, request
from flask_cors import CORS
from check_isPhishing import check_url
import os

'''Сервер, що приймає й оброблює запити від server_worker, дістає з них URL-посилання, викликає функцію, що запускає модель та повертає відповідь'''

app = Flask(__name__)
CORS(app)


@app.route("/", methods=["GET"])
def index():
    return "Welcome, to the backend server of GUARDI! Please, authorize!", 200


@app.route("/guardai/api/scan", methods=["POST"])
def api_scan():
    data = request.get_json()

    if not data or "url" not in data:
        return jsonify({"status": "error", "message": "Missing 'url' in request body"}), 400

    url = data["url"]

    try:
        result = check_url(url)

        # Безпечно отримуємо значення незалежно від того, як названо ключ в результаті
        is_phishing = result.get("is_phishing", result.get("is_phisging", False))
        probability = result.get("probability", 0.0)

        return jsonify({
            "status": "success", 
            "url": url, 
            "is_phishing": is_phishing, 
            "probability": probability
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()  
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
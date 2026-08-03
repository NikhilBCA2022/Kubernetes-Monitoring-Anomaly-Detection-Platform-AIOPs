from flask import Flask, request, jsonify
from predict import predictor

app = Flask(__name__)

# =====================================================
# Health Check
# =====================================================

@app.route("/health", methods=["GET"])
def health():

    return jsonify({
        "status": "healthy",
        "model_loaded": True
    })

# =====================================================
# Prediction Endpoint
# =====================================================

@app.route("/predict", methods=["POST"])
def predict():

    try:

        data = request.get_json()

        if data is None:
            return jsonify({
                "error":"Invalid JSON payload"
            }),400


        result = predictor.predict_metrics(data)

        return jsonify(result)


    except Exception as e:

        return jsonify({
            "error":str(e)
        }),500

# =====================================================
# Home
# =====================================================

@app.route("/")
def home():

    return jsonify({
        "project": "AIOps Platform",
        "model": "LSTM Autoencoder",
        "status": "Running"
    })   
    
@app.route("/info", methods=["GET"])
def info():

    return jsonify({

        "application":"AIOps Kubernetes Monitoring Platform",
        "model":"LSTM Autoencoder",
        "sequence_length":20,
        "features":8,
        "purpose":"Kubernetes anomaly detection"

    }) 

# =====================================================
# Run
# =====================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )

import os

from flask import (
    Flask,
    request,
    jsonify,
    render_template
)

from prometheus_client import (
    generate_latest,
    CONTENT_TYPE_LATEST
)

from predict import predictor
from prometheus_collector import PrometheusCollector


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)


# ============================================================
# PROMETHEUS COLLECTOR
# ============================================================

PROMETHEUS_URL = os.environ.get(
    "PROMETHEUS_URL",
    "http://localhost:9090"
)

collector = PrometheusCollector(
    PROMETHEUS_URL
)


# ============================================================
# REQUIRED ML FEATURES
# ============================================================

REQUIRED_FEATURES = [
    "cpu_usage",
    "memory_usage",
    "disk_usage",
    "network_latency",
    "request_rate",
    "pod_restarts",
    "error_rate",
    "response_time"
]


# ============================================================
# HOME
# ============================================================

@app.route("/", methods=["GET"])
def home():

    return render_template(
        "index.html"
    )


# ============================================================
# HEALTH PAGE
# ============================================================

@app.route("/health", methods=["GET"])
def health():

    return render_template(
        "health.html",
        status="Healthy",
        model_loaded=True,
        model_name="LSTM Autoencoder",
        model_stage="Production",
        api_status="Running"
    )


# ============================================================
# PROMETHEUS METRICS
# ============================================================

@app.route("/metrics", methods=["GET"])
def metrics():

    return generate_latest(), 200, {
        "Content-Type": CONTENT_TYPE_LATEST
    }


# ============================================================
# MANUAL PREDICTION
# ============================================================

@app.route("/predict", methods=["GET", "POST"])
def predict():

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    if request.method == "GET":

        return render_template(
            "predict.html",
            result=None
        )

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    try:

        # ----------------------------------------------------
        # JSON REQUEST
        # ----------------------------------------------------

        if request.is_json:

            data = request.get_json(
                silent=True
            ) or {}

        # ----------------------------------------------------
        # HTML FORM REQUEST
        # ----------------------------------------------------

        else:

            data = request.form.to_dict()

        # ----------------------------------------------------
        # CHECK REQUIRED FEATURES
        # ----------------------------------------------------

        missing = [
            field
            for field in REQUIRED_FEATURES
            if (
                field not in data
                or data[field] is None
                or str(data[field]).strip() == ""
            )
        ]

        if missing:

            error = {
                "status": "error",
                "message": "Missing required metrics",
                "missing_fields": missing
            }

            if request.is_json:

                return jsonify(error), 400

            return render_template(
                "predict.html",
                result=error
            )

        # ----------------------------------------------------
        # CONVERT FEATURES TO FLOAT
        # ----------------------------------------------------

        for field in REQUIRED_FEATURES:

            try:

                data[field] = float(
                    data[field]
                )

            except (
                ValueError,
                TypeError
            ):

                error = {
                    "status": "error",
                    "message": (
                        f"Invalid numeric value "
                        f"for {field}"
                    )
                }

                if request.is_json:

                    return jsonify(error), 400

                return render_template(
                    "predict.html",
                    result=error
                )

        # ----------------------------------------------------
        # RUN PREDICTION
        # ----------------------------------------------------

        result = predictor.predict_metrics(
            data
        )

        # ----------------------------------------------------
        # JSON RESPONSE
        # ----------------------------------------------------

        if request.is_json:

            return jsonify(result)

        # ----------------------------------------------------
        # BROWSER RESPONSE
        # ----------------------------------------------------

        return render_template(
            "predict.html",
            result=result
        )

    except Exception as exc:

        print(
            "Prediction error:",
            exc
        )

        error = {
            "status": "error",
            "message": str(exc)
        }

        if request.is_json:

            return jsonify(
                error
            ), 500

        return render_template(
            "predict.html",
            result=error
        )


# ============================================================
# LIVE PROMETHEUS PREDICTION
# ============================================================

@app.route(
    "/api/predict-live",
    methods=["GET"]
)
def predict_live():

    try:

        # ----------------------------------------------------
        # COLLECT PROMETHEUS METRICS
        # ----------------------------------------------------

        metrics = collector.collect_pod_metrics()

        # ----------------------------------------------------
        # BUILD DATA FOR ML MODEL
        # ----------------------------------------------------

        data = {}

        missing = []

        for metric_name in REQUIRED_FEATURES:

            values = metrics.get(
                metric_name,
                []
            )

            # ------------------------------------------------
            # No value returned
            # ------------------------------------------------

            if not values:

                missing.append(
                    metric_name
                )

                continue

            # ------------------------------------------------
            # Convert Prometheus value
            # ------------------------------------------------

            try:

                data[metric_name] = float(
                    values[0]["value"]
                )

            except (
                KeyError,
                TypeError,
                ValueError
            ):

                missing.append(
                    metric_name
                )

        # ----------------------------------------------------
        # DO NOT RUN MODEL WITH INCOMPLETE DATA
        # ----------------------------------------------------

        if missing:

            return jsonify({

                "status": "error",

                "message": (
                    "Prometheus returned "
                    "incomplete metric data"
                ),

                "missing_metrics": missing,

                "metrics": data

            }), 503

        # ----------------------------------------------------
        # RUN LSTM PREDICTION
        # ----------------------------------------------------

        result = predictor.predict_metrics(
            data
        )

        # ----------------------------------------------------
        # RETURN METRICS + PREDICTION
        # ----------------------------------------------------

        return jsonify({

            "status": "success",

            "metrics": data,

            "prediction": result

        })

    except Exception as exc:

        print(
            "Live prediction error:",
            exc
        )

        return jsonify({

            "status": "error",

            "message": str(exc)

        }), 500


# ============================================================
# RESET PREDICTION SEQUENCE
# ============================================================

@app.route(
    "/api/predict-reset",
    methods=["POST"]
)
def predict_reset():

    try:

        # ----------------------------------------------------
        # CLEAR LSTM SEQUENCE
        # ----------------------------------------------------

        predictor.sequence.clear()

        return jsonify({

            "status": "success",

            "message": (
                "Prediction sequence reset"
            ),

            "samples_collected": 0,

            "samples_required": 20

        })

    except Exception as exc:

        print(
            "Prediction reset error:",
            exc
        )

        return jsonify({

            "status": "error",

            "message": str(exc)

        }), 500


# ============================================================
# INFORMATION PAGE
# ============================================================

@app.route(
    "/info",
    methods=["GET"]
)
def info():

    return render_template(
        "info.html",

        application=(
            "AIOps Kubernetes Monitoring Platform"
        ),

        model="LSTM Autoencoder",

        sequence_length=20,

        features=8,

        purpose=(
            "Kubernetes anomaly detection"
        )
    )


# ============================================================
# API INFORMATION
# ============================================================

@app.route(
    "/api/info",
    methods=["GET"]
)
def api_info():

    return jsonify({

        "application": (
            "AIOps Kubernetes Monitoring Platform"
        ),

        "model": "LSTM Autoencoder",

        "model_stage": "Production",

        "sequence_length": 20,

        "features": 8,

        "metrics": REQUIRED_FEATURES

    })


# ============================================================
# API HEALTH
# ============================================================

@app.route(
    "/api/health",
    methods=["GET"]
)
def api_health():

    return jsonify({

        "status": "Healthy",

        "model_loaded": True,

        "model_name": (
            "LSTM Autoencoder"
        ),

        "model_stage": "Production",

        "api_status": "Running"

    })


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("AIOps Kubernetes Monitoring Platform")
    print("=" * 60)
    print(
        f"Prometheus: {PROMETHEUS_URL}"
    )
    print(
        "Flask API: http://localhost:5000"
    )
    print(
        "Dashboard: http://localhost:5000/predict"
    )
    print("=" * 60)
    print()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )

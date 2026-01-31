import os
import time
from flask import Flask, jsonify, render_template, request, session
from qkd_backend.qkd_runner import exp1, exp2, exp3, exp4
from qkd_backend.backend_config import get_backend_service, validate_ibm_token
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, static_folder="static")
# Configure caching based on environment
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 3600 if os.getenv('FLASK_ENV') == 'production' else 0
# Use environment variable for secret key, fallback for development only
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
last_exp1_result = {}
last_exp2_result = {}
last_exp3_result = {}
last_exp4_result = {}

# Store experiment results for state management
experiment_states = {}
last_circuit = {}

# ---- Serve index.html at root ----
@app.route("/")
def home():
    return render_template("index.html", static_version=int(time.time()))  # Looks in templates/index.html

@app.route("/keyrate")
def keyrate():
    return render_template("keyrate.html")

@app.route("/KeyrateVsDistance")
def KeyrateVsDistance():
    return render_template("KeyrateVsDistance.html")
@app.route("/QuantumVsClassicalSimulator")
def QuantumVsClassicalSimulator():
    return render_template("QuantumVsClassicalSimulator.html")

# ---- Experiment routes ----
@app.route("/run/exp1", methods=["POST"])
def exp1_route():
    global last_exp1_result
    data = request.get_json()
    message = data.get("message") if data else None
    if message is None:
        # Run experiment, store result (no message yet)
        backend_type = data.get('backend', 'local')
        # Get API token from session if using IBM backend
        api_token = session.get('ibm_api_token') if backend_type == 'ibm' else None
        # Use simple experiment for testing
        from qkd_backend.qkd_runner.exp_simple import run_simple_exp
        result = run_simple_exp(backend_type=backend_type, api_token=api_token)
        last_exp1_result = result
        return jsonify(result)
    else:
        # Use previous key to encrypt/decrypt
        if not last_exp1_result:
            return jsonify({"error": "Run the experiment first!"}), 400
        from qkd_backend.qkd_runner.exp_simple import encrypt_with_existing_key
        result = encrypt_with_existing_key(last_exp1_result, message)
        return jsonify(result)

@app.route("/run/exp2", methods=["POST"])
def exp2_route():
    global last_exp2_result
    data = request.get_json()
    message = data.get("message") if data else None
    if message is None:
        backend_type = data.get('backend', 'local')
        # Get API token from session if using IBM backend
        api_token = session.get('ibm_api_token') if backend_type == 'ibm' else None
        result = exp2.run_exp2(backend_type=backend_type, api_token=api_token)
        last_exp2_result = result
        return jsonify(result)
    else:
        if not last_exp2_result:
            return jsonify({"error": "Run the experiment first!"}), 400
        result = exp2.encrypt_with_existing_key(last_exp2_result, message)
        return jsonify(result)

@app.route("/run/exp3", methods=["POST"])
def exp3_route():
    data = request.get_json()
    backend_type = data.get('backend', 'local') if data else 'local'
    # Get API token from session if using IBM backend
    api_token = session.get('ibm_api_token') if backend_type == 'ibm' else None
    result = exp3.run_exp3(backend_type=backend_type, api_token=api_token)
    return jsonify(result)

@app.route("/run/exp4", methods=["POST"])
def exp4_route():
    data = request.get_json()
    backend_type = data.get('backend', 'local') if data else 'local'
    # Get API token from session if using IBM backend
    api_token = session.get('ibm_api_token') if backend_type == 'ibm' else None
    result = exp4.run_exp4(backend_type=backend_type, api_token=api_token)
    return jsonify(result)
@app.route("/run/<exp>", methods=["POST"])
def run_exp(exp):
    pass  # Placeholder route to be removed
    # After getting the result:
    global last_circuit
    last_circuit = result
    return jsonify(result)

@app.route("/circut")
def circuit():
    return render_template("circuit.html")
@app.route("/shors")
def shors():
    return render_template("shors.html")


@app.route("/get_last_circuit")
def get_last_circuit():
    global last_circuit
    return jsonify(last_circuit)

# ---- IBM API Token Management Routes ----
@app.route("/api/ibm/validate", methods=["POST"])
def validate_token():
    """Validate an IBM API token"""
    data = request.get_json()
    token = data.get('token', '').strip() if data else ''
    
    if not token:
        return jsonify({"valid": False, "error": "Token cannot be empty"}), 400
    
    is_valid, error_msg, backend_name = validate_ibm_token(token)
    
    if is_valid:
        return jsonify({
            "valid": True,
            "backend_name": backend_name,
            "message": f"Token is valid. Connected to {backend_name}"
        })
    else:
        return jsonify({
            "valid": False,
            "error": error_msg or "Invalid token"
        }), 400

@app.route("/api/ibm/save", methods=["POST"])
def save_token():
    """Save IBM API token to session"""
    data = request.get_json()
    token = data.get('token', '').strip() if data else ''
    
    if not token:
        return jsonify({"success": False, "error": "Token cannot be empty"}), 400
    
    # Validate token before saving
    is_valid, error_msg, backend_name = validate_ibm_token(token)
    
    if not is_valid:
        return jsonify({
            "success": False,
            "error": error_msg or "Invalid token"
        }), 400
    
    # Save to session
    session['ibm_api_token'] = token
    return jsonify({
        "success": True,
        "message": f"Token saved successfully. Connected to {backend_name}"
    })

@app.route("/api/ibm/delete", methods=["POST"])
def delete_token():
    """Delete IBM API token from session"""
    session.pop('ibm_api_token', None)
    return jsonify({"success": True, "message": "Token deleted successfully"})

@app.route("/api/ibm/status", methods=["GET"])
def token_status():
    """Check if a token is saved in session"""
    token = session.get('ibm_api_token')
    if token:
        # Validate the saved token
        is_valid, error_msg, backend_name = validate_ibm_token(token)
        if is_valid:
            return jsonify({
                "has_token": True,
                "valid": True,
                "backend_name": backend_name
            })
        else:
            # Token is saved but invalid, clear it
            session.pop('ibm_api_token', None)
            return jsonify({
                "has_token": False,
                "valid": False,
                "error": "Saved token is invalid"
            })
    return jsonify({"has_token": False, "valid": False})

if __name__ == "__main__":
    port = int(os.getenv('PORT', 5505))
    debug = os.getenv('FLASK_ENV') != 'production'
    app.run(host="0.0.0.0", port=port, debug=debug)

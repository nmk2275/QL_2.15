# Backend Configuration for QKD Experiments
import os
import json
from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime.fake_provider import FakeBrisbane
from qiskit_aer import AerSimulator

def _get_ibm_token():
    """Get IBM token from multiple sources"""
    # Method 1: Environment variable
    token = os.getenv('IBM_QUANTUM_TOKEN')
    if token:
        return token.strip().strip('"').strip("'")
    
    # Method 2: Direct JSON file read (your apikey file)
    try:
        json_path = os.path.join(os.path.expanduser('~'), 'Downloads', 'apikey (1).json')
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                data = json.load(f)
                return data.get('apikey', '').strip()
    except Exception:
        pass
    
    # Method 3: token.env in project root
    try:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        token_env_path = os.path.join(base_dir, 'token.env')
        if os.path.exists(token_env_path):
            with open(token_env_path, 'r') as f:
                for line in f:
                    if line.strip().startswith('IBM_QUANTUM_TOKEN'):
                        parts = line.split('=', 1)
                        if len(parts) == 2:
                            raw = parts[1].strip()
                            if raw and raw[0] in ('"', "'") and raw[-1] == raw[0]:
                                raw = raw[1:-1]
                            return raw.strip()
    except Exception:
        pass
    
    return None

def validate_ibm_token(token):
    """
    Validate an IBM API token by attempting to connect.
    
    Args:
        token (str): IBM API token to validate
        
    Returns:
        tuple: (is_valid: bool, error_message: str or None, backend_name: str or None)
    """
    if not token or not token.strip():
        return False, "Token cannot be empty", None
    
    token = token.strip()
    
    # Try ibm_quantum_platform channel first (public IBM Quantum Experience)
    try:
        service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token)
        backend = service.least_busy(operational=True, simulator=False)
        return True, None, backend.name
    except Exception as e1:
        # Try ibm_cloud channel as fallback
        try:
            service = QiskitRuntimeService(channel="ibm_cloud", token=token)
            backend = service.least_busy(operational=True, simulator=False)
            return True, None, backend.name
        except Exception as e2:
            error_msg = str(e1) if "ibm_quantum_platform" in str(e1) else str(e2)
            return False, error_msg, None

def get_backend_service(backend_type="local", api_token=None):
    """
    Get the appropriate backend service based on the backend type.
    
    Args:
        backend_type (str): Either "local" or "ibm"
        api_token (str, optional): IBM API token. If provided, this will be used.
                                  If None and backend_type is "ibm", falls back to
                                  environment/file sources for backward compatibility.
        
    Returns:
        Backend service for quantum experiments
    """
    if backend_type == "ibm":
        # Use IBM Quantum backend
        try:
            # Use provided token first, then fall back to old methods for backward compatibility
            token = api_token
            if not token:
                token = _get_ibm_token()
            
            if not token:
                print("IBM token not found, falling back to local backend")
                return get_local_backend()
            
            print(f"Using IBM token: {token[:10]}...")
            
            # Try ibm_quantum_platform channel first (public IBM Quantum Experience)
            try:
                service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token)
                backend = service.least_busy(operational=True, simulator=False)
                print(f"Using IBM Quantum backend: {backend.name}")
                return backend
            except Exception as e1:
                print(f"IBM Quantum channel failed: {e1}")
                
                # Try ibm_cloud channel as fallback
                try:
                    service = QiskitRuntimeService(channel="ibm_cloud", token=token)
                    backend = service.least_busy(operational=True, simulator=False)
                    print(f"Using IBM Cloud backend: {backend.name}")
                    return backend
                except Exception as e2:
                    print(f"IBM Cloud channel also failed: {e2}")
                    raise e1  # Raise the original error
            
        except Exception as e:
            print(f"IBM backend initialization failed: {e}")
            print("Falling back to local backend")
            return get_local_backend()
    else:
        # Use local simulation
        return get_local_backend()

def get_local_backend():
    """Get local simulation backend"""
    backend = FakeBrisbane()
    print(f"Using local backend: {backend.name}")
    return backend

def get_aer_simulator():
    """Get Aer simulator backend"""
    backend = AerSimulator()
    print("Using Aer simulator backend")
    return backend
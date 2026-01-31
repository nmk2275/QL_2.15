# Simple QKD experiment for testing
import numpy as np
import hashlib

def run_simple_exp(backend_type="local", api_token=None):
    """
    Simple QKD experiment for testing the web interface
    """
    # Simulate a simple BB84 protocol without heavy quantum computation
    rng = np.random.default_rng()
    bit_num = 10  # Reduced from 20 for faster execution
    
    # Step 1: Alice's random bits and bases
    abits = np.round(rng.random(bit_num)).astype(int)
    abase = np.round(rng.random(bit_num)).astype(int)
    
    # Step 2: Bob's random measurement bases
    bbase = np.round(rng.random(bit_num)).astype(int)
    
    # Step 3: Simulate measurements (without quantum circuit for now)
    bbits = []
    for i in range(bit_num):
        if abase[i] == bbase[i]:  # Same basis
            bbits.append(abits[i])  # Perfect measurement
        else:  # Different basis
            bbits.append(rng.integers(0, 2))  # Random result
    
    # Step 4: Sifting - keep only bits where bases match
    agoodbits = []
    bgoodbits = []
    for i in range(bit_num):
        if abase[i] == bbase[i]:
            agoodbits.append(abits[i])
            bgoodbits.append(bbits[i])
    
    # Calculate fidelity
    if len(agoodbits) > 0:
        matches = sum(1 for a, b in zip(agoodbits, bgoodbits) if a == b)
        fidelity = matches / len(agoodbits)
    else:
        fidelity = 0.0
    
    # Generate a simple key hash
    key_string = ''.join(map(str, agoodbits))
    key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]
    
    return {
        "abits": [int(x) for x in abits],
        "abase": [int(x) for x in abase],
        "bbase": [int(x) for x in bbase],
        "bbits": [int(x) for x in bbits],
        "agoodbits": [int(x) for x in agoodbits],
        "bgoodbits": [int(x) for x in bgoodbits],
        "fidelity": float(fidelity),
        "qber": float(1.0 - fidelity),
        "final_secret_key": key_hash,
        "backend_used": backend_type,
        "message": f"Simple QKD test completed with {len(agoodbits)} good bits"
    }

def encrypt_with_existing_key(exp_result, message):
    """
    Simple XOR encryption with the generated key
    """
    if not exp_result or "final_secret_key" not in exp_result:
        return {"error": "No experiment result available"}
    
    key = exp_result["final_secret_key"]
    message_bytes = message.encode('utf-8')
    
    # Simple XOR encryption
    encrypted = []
    for i, byte in enumerate(message_bytes):
        key_byte = ord(key[i % len(key)])
        encrypted.append(byte ^ key_byte)
    
    encrypted_hex = ''.join(f'{b:02x}' for b in encrypted)
    
    # Decrypt to verify
    decrypted = []
    for i, byte in enumerate(encrypted):
        key_byte = ord(key[i % len(key)])
        decrypted.append(byte ^ key_byte)
    
    decrypted_message = bytes(decrypted).decode('utf-8')
    
    return {
        "original_message": message,
        "encrypted_message_hex": encrypted_hex,
        "decrypted_message": decrypted_message,
        "key_used": key,
        "success": decrypted_message == message
    }
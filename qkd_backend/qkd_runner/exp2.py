"""
BB84 protocol without Eve.

Supports user-selectable backend:
- local: AerSimulator + BackendSamplerV2 (fast, no transpile)
- ibm: IBM Runtime backend + SamplerV2 (with transpile)
"""

import numpy as np
from qiskit import QuantumCircuit
try:
    from qiskit_ibm_runtime import SamplerV2 as Sampler
except Exception:
    try:
        from qiskit_ibm_runtime import Sampler as Sampler
    except Exception:
        Sampler = None
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
import os
import hashlib
from qiskit.visualization import circuit_drawer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
try:
    from qiskit_aer import AerSimulator
    HAS_AER = True
except ImportError:
    HAS_AER = False
try:
    from qiskit.primitives import BackendSamplerV2
except Exception:
    try:
        from qiskit.primitives import BackendSampler as BackendSamplerV2
    except Exception:
        BackendSamplerV2 = None
from qkd_backend.backend_config import get_backend_service
from qkd_backend.qkd_runner.qrng import generate_qrng_bits
from qkd_backend.qkd_runner.cascade_error_correction import cascade_error_correction

def xor_encrypt_decrypt(message_bytes, key_bits):
    # message_bytes: bytes
    # key_bits: list of 0/1
    msg_bits = []
    for byte in message_bytes:
        for i in range(8):
            msg_bits.append((byte >> (7-i)) & 1)
    # Pad or trim key to message length
    if len(key_bits) < len(msg_bits):
        key = (key_bits * ((len(msg_bits)//len(key_bits))+1))[:len(msg_bits)]
    else:
        key = key_bits[:len(msg_bits)]
    # XOR
    cipher_bits = [m ^ k for m, k in zip(msg_bits, key)]
    # Convert bits back to bytes
    cipher_bytes = bytearray()
    for i in range(0, len(cipher_bits), 8):
        byte = 0
        for j in range(8):
            if i+j < len(cipher_bits):
                byte = (byte << 1) | cipher_bits[i+j]
            else:
                byte = (byte << 1)
        cipher_bytes.append(byte)
    return bytes(cipher_bytes)

def run_exp2(message=None, bit_num=20, shots=1024, rng_seed=None, backend_type="local", api_token=None):
    rng = np.random.default_rng(rng_seed)

    # Generate random bits: use QRNG if IBM backend, otherwise NumPy
    if backend_type == "ibm":
        # Get IBM backend first for QRNG
        backend = get_backend_service("ibm", api_token=api_token)
        # Generate random bits using QRNG
        abits = np.array(generate_qrng_bits(bit_num, backend, shots=1))
        abase = np.array(generate_qrng_bits(bit_num, backend, shots=1))
        bbase = np.array(generate_qrng_bits(bit_num, backend, shots=1))
    else:
        # Use NumPy random for local backend
        abits = np.round(rng.random(bit_num))
        abase = np.round(rng.random(bit_num))
        bbase = np.round(rng.random(bit_num))

    # Step 1: Sender's random bits and bases
    # Step 2: Receiver's random measurement bases

    # Sender prepares and sends qubits
    qc = QuantumCircuit(bit_num, bit_num)
    for n in range(bit_num):
        if abits[n] == 0:
            if abase[n] == 1:
                qc.h(n)
        if abits[n] == 1:
            if abase[n] == 0:
                qc.x(n)
            if abase[n] == 1:
                qc.x(n)
                qc.h(n)

    # Receiver's measurement
    for m in range(bit_num):
        if bbase[m] == 1:
            qc.h(m)
        qc.measure(m, m)

    # Backend & Sampler selection
    if backend_type == "local":
        if HAS_AER:
            aer_backend = AerSimulator()
            qc_isa = qc
            if BackendSamplerV2 is None:
                raise RuntimeError("BackendSamplerV2 not available: install qiskit or qiskit-aer")
            sampler = BackendSamplerV2(backend=aer_backend)
        else:
            # Fallback to FakeBrisbane if AerSimulator is not available
            backend = get_backend_service("local")
            qc_isa = qc
            if BackendSamplerV2 is None:
                raise RuntimeError("BackendSamplerV2 not available: install qiskit or qiskit-aer")
            sampler = BackendSamplerV2(backend=backend)
    else:
        # Backend already obtained for QRNG, reuse it
        target = backend.target
        pm = generate_preset_pass_manager(target=target, optimization_level=3)
        qc_isa = pm.run(qc)
        if Sampler is None:
            raise RuntimeError("Sampler not available: install qiskit-ibm-runtime")
        sampler = Sampler(mode=backend)

    # Draw circuit once
    os.makedirs("static", exist_ok=True)
    diagram_path = "static/circuit_exp2.png"
    fig = circuit_drawer(qc_isa, output='mpl')
    fig.savefig(diagram_path)
    plt.close(fig)

    # Run using selected sampler
    job = sampler.run([qc_isa], shots=shots)
    result = job.result()
    
    # Handle different Qiskit API versions for accessing counts
    counts = None
    
    # Debug: log what we're working with
    print(f"DEBUG: result type = {type(result)}")
    print(f"DEBUG: result dir = {[x for x in dir(result) if not x.startswith('_')]}")
    
    # Try multiple methods to extract counts
    try:
        # Method 1: Iterate over result (new API)
        for quasi_dist in result:
            print(f"DEBUG: quasi_dist type = {type(quasi_dist)}")
            if hasattr(quasi_dist, 'data'):
                if hasattr(quasi_dist.data, 'c'):
                    counts = quasi_dist.data.c.get_counts()
                else:
                    counts = quasi_dist.data.get_counts()
            break
    except (TypeError, AttributeError, IndexError) as e:
        print(f"DEBUG: Method 1 failed: {e}")
        pass
    
    if counts is None:
        try:
            # Method 2: Access via indexing
            print(f"DEBUG: Trying indexing method")
            quasi_dist = result[0]
            print(f"DEBUG: result[0] type = {type(quasi_dist)}")
            if hasattr(quasi_dist, 'data'):
                if hasattr(quasi_dist.data, 'c'):
                    counts = quasi_dist.data.c.get_counts()
                else:
                    counts = quasi_dist.data.get_counts()
        except (TypeError, AttributeError, IndexError) as e:
            print(f"DEBUG: Method 2 failed: {e}")
            pass
    
    if counts is None:
        try:
            # Method 3: Direct call on result
            print(f"DEBUG: Trying direct call on result")
            if hasattr(result, 'get_counts'):
                counts = result.get_counts()
            elif hasattr(result, '__iter__'):
                # Try iterating again with more debug info
                items = list(result)
                print(f"DEBUG: Found {len(items)} items in result")
                if items:
                    counts = items[0].data.c.get_counts() if hasattr(items[0].data, 'c') else items[0].data.get_counts()
        except (TypeError, AttributeError, Exception) as e:
            print(f"DEBUG: Method 3 failed: {e}")
            pass
    
    if counts is None:
        print(f"DEBUG: All methods failed. result object: {result}")
        raise RuntimeError("Failed to extract counts from sampler result. Try using AerSimulator or check qiskit version.")
    
    key = list(counts.keys())[0]
    bmeas = list(key)
    bbits = [int(x) for x in bmeas][::-1]

    # Sifting: keep only positions where Sender & Receiver used same basis
    agoodbits = []
    bgoodbits = []
    match_count = 0
    for i in range(bit_num):
        if abase[i] == bbase[i]:
            agoodbits.append(int(abits[i]))
            bgoodbits.append(int(bbits[i]))
            if int(abits[i]) == int(bbits[i]):
                match_count += 1

    fidelity = match_count / len(agoodbits) if agoodbits else 0
    loss = 1 - fidelity if agoodbits else 1

    # --- Error Correction (Cascade Protocol) ---
    corrected_bbits = cascade_error_correction(agoodbits, bgoodbits, num_rounds=4, initial_block_size=8)

    # Display key after error correction
    error_corrected_key = ''.join(map(str, corrected_bbits))
    print("Key after Error Correction:", error_corrected_key)

    # --- Privacy Amplification ---
    secret_key = hashlib.sha256(error_corrected_key.encode()).hexdigest()
    secret_key = secret_key[:64]  # shorten for demonstration

    print("Final Secret Key:", secret_key)

    # --- Message encryption/decryption ---
    if message is None:
        message = "QKD demo"
    message_bytes = message.encode('utf-8')
    if agoodbits and len(agoodbits) >= 8:
        # Encrypt
        encrypted_bytes = xor_encrypt_decrypt(message_bytes, agoodbits)
        # Decrypt using Bob's key
        decrypted_bytes = xor_encrypt_decrypt(encrypted_bytes, bgoodbits)
        try:
            decrypted_message = decrypted_bytes.decode('utf-8')
        except Exception:
            decrypted_message = "<decryption failed>"
        encrypted_hex = encrypted_bytes.hex()
    else:
        encrypted_hex = ""
        decrypted_message = ""
    return {
        "Sender_bits": abits.tolist(),
        "Sender_bases": abase.tolist(),
        "Receiver_bases": bbase.tolist(),
        "Receiver_bits": bbits,
        "agoodbits": agoodbits,
        "bgoodbits": bgoodbits,
        "fidelity": fidelity,
        "loss": loss,
        "error_corrected_key": error_corrected_key,
        "final_secret_key": secret_key,
        "original_message": message,
        "encrypted_message_hex": encrypted_hex,
        "decrypted_message": decrypted_message,
        "circuit_diagram_url": "/static/circuit_exp2.png",
        "counts": counts # <-- add this line,
        
        
    }

def encrypt_with_existing_key(exp_result, message):
    # Use error-corrected key if available, else fallback to agoodbits
    corrected_bbits = exp_result.get("error_corrected_key")
    if corrected_bbits:
        # Convert string to list of ints
        key_bits = [int(b) for b in corrected_bbits]
    else:
        key_bits = exp_result["agoodbits"]

    message_bytes = message.encode('utf-8')
    if key_bits and len(key_bits) >= 8:
        encrypted_bytes = xor_encrypt_decrypt(message_bytes, key_bits)
        decrypted_bytes = xor_encrypt_decrypt(encrypted_bytes, key_bits)
        try:
            decrypted_message = decrypted_bytes.decode('utf-8')
        except Exception:
            decrypted_message = "<decryption failed>"
        encrypted_hex = encrypted_bytes.hex()
    else:
        encrypted_hex = ""
        decrypted_message = ""
    return {
        "original_message": message,
        "encrypted_message_hex": encrypted_hex,
        "decrypted_message": decrypted_message,
        "error_corrected_key": exp_result.get("error_corrected_key"),
        "final_secret_key": exp_result.get("final_secret_key"),
    }

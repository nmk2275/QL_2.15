# qkd_backend/qkd_runner/exp1.py
"""
BB84 (no Eve) with selectable backend.

Backends:
- local: AerSimulator + BackendSamplerV2
- ibm: IBM Runtime backend + SamplerV2 (with transpilation)
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
from qiskit.visualization import circuit_drawer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import hashlib
import os
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


def xor_encrypt_decrypt(message_bytes, key_bits):
    # Repeat key_bits to match the length of message_bytes
    key = (key_bits * ((len(message_bytes) // len(key_bits)) + 1))[:len(message_bytes)]
    key_bytes = bytes([int(b) for b in key])
    return bytes([mb ^ kb for mb, kb in zip(message_bytes, key_bytes)])


def run_exp1(message=None, backend_type="local", error_mitigation=False, bit_num=20, shots=1024, rng_seed=None, api_token=None):
    # Map problem to quantum circuit
    rng = np.random.default_rng(rng_seed)
    qc = QuantumCircuit(bit_num, bit_num)

    # QKD step 1: Random bits and bases for Sender
    abits = np.round(rng.random(bit_num))
    abase = np.round(rng.random(bit_num))

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

    qc.barrier()

    # QKD step 2: Random bases for Receiver
    bbase = np.round(rng.random(bit_num))

    for m in range(bit_num):
        if bbase[m] == 1:
            qc.h(m)
        qc.measure(m, m)

    # Backend & sampler selection
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
        backend = get_backend_service("ibm", api_token=api_token)
        target = backend.target
        pm = generate_preset_pass_manager(target=target, optimization_level=3)
        qc_isa = pm.run(qc)
        if Sampler is None:
            raise RuntimeError("Sampler not available: install qiskit-ibm-runtime")
        sampler = Sampler(mode=backend)

    # Draw circuit
    os.makedirs("static", exist_ok=True)
    diagram_path = "static/circuit_exp1.png"
    fig = circuit_drawer(qc_isa, output='mpl')
    fig.savefig(diagram_path)
    plt.close(fig)

    # Run
    job = sampler.run([qc_isa], shots=shots)

    counts = job.result()[0].data.c.get_counts()
    countsint = job.result()[0].data.c.get_int_counts()

    keys = counts.keys()
    key = list(keys)[0]
    bmeas = list(key)
    bmeas_ints = []
    for n in range(bit_num):
        bmeas_ints.append(int(bmeas[n]))
    bbits = bmeas_ints[::-1]

    print(bbits)

    # QKD step 3: Public discussion of bases
    agoodbits = []
    bgoodbits = []
    match_count = 0
    for n in range(bit_num):
        if abase[n] == bbase[n]:
            agoodbits.append(int(abits[n]))
            bgoodbits.append(bbits[n])
            if int(abits[n]) == bbits[n]:
                match_count += 1
    # --- Error Correction (Simple Parity) ---
    block_size = 4
    corrected_bbits = []

    for i in range(0, len(agoodbits), block_size):
        a_block = agoodbits[i:i+block_size]
        b_block = bgoodbits[i:i+block_size]
        a_parity = sum(a_block) % 2
        b_parity = sum(b_block) % 2
        if a_parity != b_parity and len(b_block) > 0:
            b_block[-1] ^= 1
        corrected_bbits.extend(b_block)

    print(agoodbits)
    print(bgoodbits)
    print("fidelity = ", match_count / len(agoodbits))
    print("loss = ", 1 - match_count / len(agoodbits))
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

    # Return results for UI
    return {
        "Sender_bits": abits.tolist(),
        "Sender_bases": abase.tolist(),
        "Receiver_bases": bbase.tolist(),
        "Receiver_bits": bbits,
        "agoodbits": agoodbits,
        "bgoodbits": bgoodbits,
        "fidelity": match_count / len(agoodbits) if agoodbits else 0,
        "loss": 1 - (match_count / len(agoodbits)) if agoodbits else 1,
        "error_corrected_key": error_corrected_key,
        "final_secret_key": secret_key,
        "original_message": message,
        "encrypted_message_hex": encrypted_hex,
        "decrypted_message": decrypted_message,
        "circuit_diagram_url": "/static/circuit_exp1.png",
        "counts": counts
    }
def encrypt_with_existing_key(exp_result, message):
    agoodbits = exp_result["agoodbits"]
    bgoodbits = exp_result["bgoodbits"]
    # Use the same error correction and privacy amplification as before if needed
    message_bytes = message.encode('utf-8')
    if agoodbits and len(agoodbits) >= 8:
        encrypted_bytes = xor_encrypt_decrypt(message_bytes, agoodbits)
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
        "original_message": message,
        "encrypted_message_hex": encrypted_hex,
        "decrypted_message": decrypted_message,
        "error_corrected_key": exp_result.get("error_corrected_key"),
        "final_secret_key": exp_result.get("final_secret_key"),
        # Optionally, include other fields you want to show
    }

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.visualization import circuit_drawer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

# Robust imports for deployment compatibility
try:
    from backend.backend_config import get_backend_service
    from backend.qrng import generate_qrng_bits
    from backend.cascade_error_correction import cascade_error_correction
    from backend.privacy_amplification import privacy_amplify
except ImportError:
    # Fallback for when backend/ is at root or we're in backend directory
    from backend_config import get_backend_service
    from qrng import generate_qrng_bits
    from cascade_error_correction import cascade_error_correction
    from privacy_amplification import privacy_amplify

try:
    from qiskit_ibm_runtime import SamplerV2 as Sampler
except ImportError:
    from qiskit_ibm_runtime import Sampler

from qiskit_aer import AerSimulator
try:
    from qiskit.primitives import BackendSamplerV2 as BackendSampler
except ImportError:
    try:
        from qiskit.primitives import BackendSampler
    except ImportError:
        BackendSampler = None


def run_exp2(message=None, backend_type="local",
             bit_num=20, shots=1024,
             rng_seed=None, api_token=None):

    rng = np.random.default_rng(rng_seed)

    if backend_type == "ibm":
        backend = get_backend_service("ibm", api_token=api_token)
        abits = np.array(generate_qrng_bits(bit_num, backend, shots=1))
        abase = np.array(generate_qrng_bits(bit_num, backend, shots=1))
        bbase = np.array(generate_qrng_bits(bit_num, backend, shots=1))
    else:
        abits = rng.integers(0, 2, bit_num)
        abase = rng.integers(0, 2, bit_num)
        bbase = rng.integers(0, 2, bit_num)

    qc = QuantumCircuit(bit_num, bit_num)

    # Alice encodes
    for n in range(bit_num):
        if abits[n] == 1:
            qc.x(n)
        if abase[n] == 1:
            qc.h(n)

    qc.barrier()

    # Bob measures
    for n in range(bit_num):
        if bbase[n] == 1:
            qc.h(n)
        qc.measure(n, n)

    # Run backend
    if backend_type == "local":
        backend = AerSimulator()
        tqc = transpile(qc, backend)
        sampler = BackendSampler(backend=backend)
        result = sampler.run([tqc], shots=shots).result()
    else:
        tqc = transpile(qc, backend)
        sampler = Sampler(mode=backend)
        result = sampler.run([tqc], shots=shots).result()

    # --- Robust counts extraction (copied from exp1) ---
    counts = None
    if hasattr(result, "quasi_dists"):
        counts = {}
        bit_num = tqc.num_qubits
        for dist in result.quasi_dists:
            for int_key, prob in dist.items():
                bitstring = format(int_key, f'0{bit_num}b')
                counts[bitstring] = prob
            break
    if counts is None or not counts:
        try:
            for quasi_dist in result:
                if hasattr(quasi_dist, 'data'):
                    if hasattr(quasi_dist.data, 'c'):
                        counts = quasi_dist.data.c.get_counts()
                    else:
                        counts = quasi_dist.data.get_counts()
                break
        except (TypeError, AttributeError, IndexError):
            pass
        if counts is None:
            try:
                quasi_dist = result[0]
                if hasattr(quasi_dist, 'data'):
                    if hasattr(quasi_dist.data, 'c'):
                        counts = quasi_dist.data.c.get_counts()
                    else:
                        counts = quasi_dist.data.get_counts()
            except (TypeError, AttributeError, IndexError):
                pass
        if counts is None:
            try:
                if hasattr(result, 'get_counts'):
                    counts = result.get_counts()
                elif hasattr(result, '__iter__'):
                    items = list(result)
                    if items:
                        counts = items[0].data.c.get_counts() if hasattr(items[0].data, 'c') else items[0].data.get_counts()
            except (TypeError, AttributeError, Exception):
                pass
    if counts is None or not counts:
        raise RuntimeError("Failed to extract counts from sampler result. Try using AerSimulator or check qiskit version.")
    # --- End robust counts extraction ---

    # Convert quasi-dist to bitstrings
    # counts = {
    #     format(k, f"0{bit_num}b"): float(v)
    #     for k, v in dist.items()
    # }

    # ✅ Sample ONE real backend outcome (authentic BB84)
    bitstrings = list(counts.keys())
    weights = np.array(list(counts.values()), dtype=float)
    weights = weights.astype(float)
    weights /= weights.sum()

    sampled = rng.choice(bitstrings, p=weights)
    bbits = list(map(int, reversed(sampled)))

    # Sifting
    agoodbits = []
    bgoodbits = []
    for i in range(bit_num):
        if abase[i] == bbase[i]:
            agoodbits.append(int(abits[i]))
            bgoodbits.append(bbits[i])

    # QBER (true BB84 definition)
    mismatches = sum(a != b for a, b in zip(agoodbits, bgoodbits))
    qber = mismatches / len(agoodbits) if agoodbits else 0.0

    corrected = cascade_error_correction(agoodbits, bgoodbits)
    final_key = privacy_amplify("".join(map(str, corrected)), qber=qber)

    # Calculate fidelity and loss as percentages
    match_count = len(agoodbits) - mismatches
    fidelity = match_count / len(agoodbits) if agoodbits else 0
    loss = 1 - fidelity if agoodbits else 1
    fidelity_percent = fidelity * 100
    loss_percent = loss * 100
    qber_percent = qber * 100

    # Save circuit
    # Get absolute path to static folder (backend/static)
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_dir = os.path.join(backend_dir, "static")
    os.makedirs(static_dir, exist_ok=True)
    circuit_path = os.path.join(static_dir, "circuit_exp2.png")
    fig = circuit_drawer(qc, output="mpl", style='clifford')
    fig.savefig(circuit_path)
    plt.close(fig)

    return {
        "Sender_bits": abits.tolist(),
        "Sender_bases": abase.tolist(),
        "Receiver_bases": bbase.tolist(),
        "Receiver_bits": bbits,
        "agoodbits": agoodbits,
        "bgoodbits": bgoodbits,
        "fidelity": fidelity_percent,
        "loss": loss_percent,
        "qber": qber_percent,
        "final_secret_key": final_key,
        "circuit_diagram_url": "/static/circuit_exp2.png",
        "counts": counts
    }

def encrypt_with_existing_key(exp2_result, message):
    """
    Encrypts and decrypts a message using the final_secret_key from exp2, using the same XOR method as exp1.
    Returns a dict with original, encrypted, and decrypted message.
    """
    key_bits = exp2_result.get("final_secret_key", "")
    if not key_bits or not message:
        return {
            "original_message": message,
            "encrypted_message_hex": None,
            "decrypted_message": None,
            "error": "Missing key or message."
        }
    # Convert key_bits string to list of ints, ignoring non-binary chars
    key_bits_list = [int(b) for b in key_bits if b in ('0', '1')]
    if not key_bits_list:
        return {
            "original_message": message,
            "encrypted_message_hex": None,
            "decrypted_message": None,
            "error": "Key is not a valid binary string."
        }
    message_bytes = message.encode('utf-8')
    # XOR encrypt
    encrypted_bytes = xor_encrypt_decrypt(message_bytes, key_bits_list)
    encrypted_hex = encrypted_bytes.hex()
    # XOR decrypt
    decrypted_bytes = xor_encrypt_decrypt(encrypted_bytes, key_bits_list)
    try:
        decrypted_message = decrypted_bytes.decode('utf-8')
    except Exception:
        decrypted_message = "<decryption failed>"
    return {
        "original_message": message,
        "encrypted_message_hex": encrypted_hex,
        "decrypted_message": decrypted_message
    }

def xor_encrypt_decrypt(data, key_bits):
    """
    Encrypt or decrypt data using XOR with the given key_bits.
    """
    key_length = len(key_bits)
    # Repeat the key_bits to match the data length
    extended_key_bits = (key_bits * (len(data) // key_length + 1))[:len(data)]
    # XOR each byte of data with the corresponding key_bit
    encrypted_decrypted = bytes([b ^ k for b, k in zip(data, extended_key_bits)])
    return encrypted_decrypted

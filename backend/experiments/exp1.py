import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.visualization import circuit_drawer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

from qkd_backend.backend_config import get_backend_service
from qkd_backend.qrng import generate_qrng_bits
from qkd_backend.cascade_error_correction import cascade_error_correction
from qkd_backend.privacy_amplification import privacy_amplify

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

def xor_encrypt_decrypt(message_bytes, key_bits):
    key = (key_bits * ((len(message_bytes) // len(key_bits)) + 1))[:len(message_bytes)]
    key_bytes = bytes([int(b) for b in key])
    return bytes([mb ^ kb for mb, kb in zip(message_bytes, key_bytes)])

def run_exp1(message=None, backend_type="local", noise_mitigation=True, bit_num=20, shots=1024, rng_seed=None, api_token=None):
    rng = np.random.default_rng(rng_seed)
    if backend_type == "ibm":
        backend = get_backend_service("ibm", api_token=api_token)
        abits = np.array(generate_qrng_bits(bit_num, backend, shots=1))
        abase = np.array(generate_qrng_bits(bit_num, backend, shots=1))
        bbase = np.array(generate_qrng_bits(bit_num, backend, shots=1))
    else:
        abits = np.round(rng.random(bit_num)).astype(int)
        abase = np.round(rng.random(bit_num)).astype(int)
        bbase = np.round(rng.random(bit_num)).astype(int)

    qc = QuantumCircuit(bit_num, bit_num)
    for n in range(bit_num):
        if abits[n] == 0:
            if abase[n] == 1:
                qc.h(n)
        else:
            if abase[n] == 0:
                qc.x(n)
            else:
                qc.x(n)
                qc.h(n)
    qc.barrier()
    for m in range(bit_num):
        if bbase[m] == 1:
            qc.h(m)
        qc.measure(m, m)

    if backend_type == "local":
        backend = AerSimulator()
        tqc = transpile(qc, backend)
        sampler = BackendSampler(backend=backend)
        result = sampler.run([tqc], shots=shots).result()
        # Handle different Qiskit API versions for accessing counts
        counts = None
        if hasattr(result, "quasi_dists"):
            counts = {}
            bit_num = tqc.num_qubits
            for dist in result.quasi_dists:
                for int_key, prob in dist.items():
                    bitstring = format(int_key, f'0{bit_num}b')
                    counts[bitstring] = prob
                break  # Only use the first quasi_dist
        if counts is None or not counts:
            try:
                for quasi_dist in result:
                    if hasattr(quasi_dist, 'data'):
                        if hasattr(quasi_dist.data, 'c'):
                            counts = quasi_dist.data.c.get_counts()
                        else:
                            counts = quasi_dist.data.get_counts()
                    break
            except (TypeError, AttributeError, IndexError) as e:
                pass
            if counts is None:
                try:
                    quasi_dist = result[0]
                    if hasattr(quasi_dist, 'data'):
                        if hasattr(quasi_dist.data, 'c'):
                            counts = quasi_dist.data.c.get_counts()
                        else:
                            counts = quasi_dist.data.get_counts()
                except (TypeError, AttributeError, IndexError) as e:
                    pass
            if counts is None:
                try:
                    if hasattr(result, 'get_counts'):
                        counts = result.get_counts()
                    elif hasattr(result, '__iter__'):
                        items = list(result)
                        if items:
                            counts = items[0].data.c.get_counts() if hasattr(items[0].data, 'c') else items[0].data.get_counts()
                except (TypeError, AttributeError, Exception) as e:
                    pass
        if counts is None or not counts:
            raise RuntimeError("Failed to extract counts from sampler result. Try using AerSimulator or check qiskit version.")
    else:
        tqc = transpile(qc, backend)
        sampler = Sampler(mode=backend)
        if noise_mitigation:
            try:
                sampler.options.resilience_level = 2
                sampler.options.resilience.zne_mitigation = True
                sampler.options.resilience.zne.noise_factors = [1, 3, 5]
                sampler.options.dynamical_decoupling.enable = True
                sampler.options.dynamical_decoupling.sequence_type = "XpXm"
            except Exception:
                pass
        result = sampler.run([tqc], shots=shots).result()
        # Handle different Qiskit API versions for accessing counts
        counts = None
        if hasattr(result, "quasi_dists"):
            counts = {}
            bit_num = tqc.num_qubits
            for dist in result.quasi_dists:
                for int_key, prob in dist.items():
                    bitstring = format(int_key, f'0{bit_num}b')
                    counts[bitstring] = prob
                break  # Only use the first quasi_dist
        if counts is None or not counts:
            try:
                for quasi_dist in result:
                    if hasattr(quasi_dist, 'data'):
                        if hasattr(quasi_dist.data, 'c'):
                            counts = quasi_dist.data.c.get_counts()
                        else:
                            counts = quasi_dist.data.get_counts()
                    break
            except (TypeError, AttributeError, IndexError) as e:
                pass
            if counts is None:
                try:
                    quasi_dist = result[0]
                    if hasattr(quasi_dist, 'data'):
                        if hasattr(quasi_dist.data, 'c'):
                            counts = quasi_dist.data.c.get_counts()
                        else:
                            counts = quasi_dist.data.get_counts()
                except (TypeError, AttributeError, IndexError) as e:
                    pass
            if counts is None:
                try:
                    if hasattr(result, 'get_counts'):
                        counts = result.get_counts()
                    elif hasattr(result, '__iter__'):
                        items = list(result)
                        if items:
                            counts = items[0].data.c.get_counts() if hasattr(items[0].data, 'c') else items[0].data.get_counts()
                except (TypeError, AttributeError, Exception) as e:
                    pass
        if counts is None or not counts:
            raise RuntimeError("Failed to extract counts from sampler result. Try using AerSimulator or check qiskit version.")

    os.makedirs("static", exist_ok=True)
    fig = circuit_drawer(qc, output='mpl')
    fig.savefig("static/circuit_exp1.png")
    plt.close(fig)

    if not counts:
        raise RuntimeError("Counts not available")

    # Find the most likely outcome string
    max_key = max(counts, key=counts.get)
    bbits = list(map(int, reversed(list(max_key))))

    agoodbits = []
    bgoodbits = []
    match_count = 0
    for n in range(bit_num):
        if abase[n] == bbase[n]:
            ab = int(abits[n])
            bb = bbits[n]
            agoodbits.append(ab)
            bgoodbits.append(bb)
            if ab == bb:
                match_count += 1

    corrected_bbits = cascade_error_correction(agoodbits, bgoodbits, num_rounds=4, initial_block_size=8)
    fidelity = match_count / len(agoodbits) if agoodbits else 0
    loss = 1 - fidelity if agoodbits else 1
    fidelity_percent = fidelity * 100
    loss_percent = loss * 100
    qber = loss  # QBER is still a fraction; multiply by 100 if you want percent
    error_corrected_key = ''.join(map(str, corrected_bbits))
    secret_key = privacy_amplify(error_corrected_key, qber=qber)

    if message is None:
        message = "QKD demo"
    message_bytes = message.encode('utf-8')
    encrypted_hex = ""
    decrypted_message = ""
    if agoodbits and len(agoodbits) >= 8:
        encrypted_bytes = xor_encrypt_decrypt(message_bytes, agoodbits)
        decrypted_bytes = xor_encrypt_decrypt(encrypted_bytes, bgoodbits)
        try:
            decrypted_message = decrypted_bytes.decode('utf-8')
        except Exception:
            decrypted_message = "<decryption failed>"
        encrypted_hex = encrypted_bytes.hex()

    def tolist_safe(x):
        if hasattr(x, 'tolist'):
            return x.tolist()
        return list(x) if isinstance(x, (np.ndarray,)) else x

    fidelity = match_count / len(agoodbits) if agoodbits else 0
    loss = 1 - fidelity if agoodbits else 1

    return {
        "Sender_bits": tolist_safe(abits),
        "Sender_bases": tolist_safe(abase),
        "Receiver_bases": tolist_safe(bbase),
        "Receiver_bits": bbits,
        "agoodbits": agoodbits,
        "bgoodbits": bgoodbits,
        "fidelity": fidelity_percent,
        "loss": loss_percent,
        "qber": qber * 100,  # QBER as percent for consistency
        "error_corrected_key": error_corrected_key,
        "final_secret_key": secret_key,
        "original_message": message,
        "encrypted_message_hex": encrypted_hex,
        "decrypted_message": decrypted_message,
        "circuit_diagram_url": "/static/circuit_exp1.png",
        "counts": dict(counts) if not isinstance(counts, dict) else counts
    }

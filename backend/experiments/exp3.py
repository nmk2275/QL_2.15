# backend/qkd_runner/exp3.py
# BB84 with Eve intercept-resend, executed on IBM Quantum backend using SamplerV2.

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
try:
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
except Exception:
    try:
        from qiskit_ibm_runtime import QiskitRuntimeService, Sampler as Sampler
    except Exception:
        try:
            from qiskit_ibm_runtime import QiskitRuntimeService
        except Exception:
            QiskitRuntimeService = None
        Sampler = None
try:
    from qiskit_aer import AerSimulator
    from qiskit_aer.noise import NoiseModel
    HAS_AER = True
except ImportError:
    HAS_AER = False
    NoiseModel = None
try:
    from qiskit.primitives import BackendSamplerV2
except Exception:
    try:
        from qiskit.primitives import BackendSampler as BackendSamplerV2
    except Exception:
        BackendSamplerV2 = None
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Robust imports for deployment compatibility
from backend_config import get_backend_service
from qrng import generate_qrng_bits
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
import os
from qiskit.visualization import circuit_drawer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


"""
exp3: BB84 with Eve intercept-resend

Changes:
- Avoid initializing IBM Runtime at import time.
- Respect backend_type ("local" | "ibm").
- Use AerSimulator + BackendSamplerV2 for local fast runs.
- Safely extract a single bitstring from counts (sampling when shots>1).
"""

def extract_bitstring(counts, n):
    """Extract a deterministic bitstring from counts dict (single-shot)."""
    if not counts:
        raise RuntimeError("Empty measurement counts.")
    bitstring = max(counts, key=counts.get)
    return bitstring.zfill(n)

def run_exp3(message=None, bit_num=20, backend_type="local", api_token=None, shots=1024):
    # Use multiple shots for counts visualization, but extract single bitstring for protocol
    rng = np.random.default_rng()

    # Generate random bits: use QRNG if IBM backend, otherwise NumPy
    if backend_type == "ibm":
        # Get IBM backend first for QRNG
        backend = get_backend_service("ibm", api_token=api_token)
        # Generate random bits using QRNG
        abits = np.array(generate_qrng_bits(bit_num, backend, shots=1)).astype(int)
        abase = np.array(generate_qrng_bits(bit_num, backend, shots=1)).astype(int)
        ebase = np.array(generate_qrng_bits(bit_num, backend, shots=1)).astype(int)
        bbase = np.array(generate_qrng_bits(bit_num, backend, shots=1)).astype(int)
    else:
        # Use NumPy random for local backend
        abits = rng.integers(0, 2, bit_num)
        abase = rng.integers(0, 2, bit_num)
        ebase = rng.integers(0, 2, bit_num)
        bbase = rng.integers(0, 2, bit_num)

    # --- Sender prepares and sends qubits ---
    qr = QuantumRegister(bit_num, "q")
    cr = ClassicalRegister(bit_num, "c")
    qc = QuantumCircuit(qr, cr)
    for i in range(bit_num):
        if abits[i] == 1:
            qc.x(i)
        if abase[i] == 1:
            qc.h(i)
    for i in range(bit_num):
        if ebase[i] == 1:
            qc.h(i)
        qc.measure(i, i)
    # Backend execution (Eve)
    if backend_type == "local":
        if not HAS_AER:
            raise RuntimeError("AerSimulator not available.")
        backend = AerSimulator()
        sampler = BackendSamplerV2(backend=backend)
        qc_isa = qc
    else:
        pm = generate_preset_pass_manager(target=backend.target, optimization_level=1)
        qc_isa = pm.run(qc)
        sampler = Sampler(mode=backend)
    result = sampler.run([qc_isa], shots=shots).result()
    # --- Robust counts extraction for Eve ---
    counts = None
    if hasattr(result, "quasi_dists"):
        counts = {}
        bit_num_circuit = qc_isa.num_qubits
        for dist in result.quasi_dists:
            for k, v in dist.items():
                counts[format(k, f"0{bit_num_circuit}b")] = v
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
    eve_key = extract_bitstring(counts, bit_num)
    ebits = [int(b) for b in eve_key][::-1]
    # Eve → Bob
    qr2 = QuantumRegister(bit_num, "q")
    cr2 = ClassicalRegister(bit_num, "c")
    qc2 = QuantumCircuit(qr2, cr2)
    for i in range(bit_num):
        if ebits[i] == 1:
            qc2.x(i)
        if ebase[i] == 1:
            qc2.h(i)
    for i in range(bit_num):
        if bbase[i] == 1:
            qc2.h(i)
        qc2.measure(i, i)
    qc2_isa = qc2 if backend_type == "local" else pm.run(qc2)
    result2 = sampler.run([qc2_isa], shots=shots).result()
    # --- Robust counts extraction for Bob ---
    counts2 = None
    if hasattr(result2, "quasi_dists"):
        counts2 = {}
        bit_num_circuit2 = qc2_isa.num_qubits
        for dist in result2.quasi_dists:
            for k, v in dist.items():
                counts2[format(k, f"0{bit_num_circuit2}b")] = v
            break
    if counts2 is None or not counts2:
        try:
            for quasi_dist in result2:
                if hasattr(quasi_dist, 'data'):
                    if hasattr(quasi_dist.data, 'c'):
                        counts2 = quasi_dist.data.c.get_counts()
                    else:
                        counts2 = quasi_dist.data.get_counts()
                break
        except (TypeError, AttributeError, IndexError):
            pass
        if counts2 is None:
            try:
                quasi_dist = result2[0]
                if hasattr(quasi_dist, 'data'):
                    if hasattr(quasi_dist.data, 'c'):
                        counts2 = quasi_dist.data.c.get_counts()
                    else:
                        counts2 = quasi_dist.data.get_counts()
            except (TypeError, AttributeError, IndexError):
                pass
        if counts2 is None:
            try:
                if hasattr(result2, 'get_counts'):
                    counts2 = result2.get_counts()
                elif hasattr(result2, '__iter__'):
                    items = list(result2)
                    if items:
                        counts2 = items[0].data.c.get_counts() if hasattr(items[0].data, 'c') else items[0].data.get_counts()
            except (TypeError, AttributeError, Exception):
                pass
    if counts2 is None or not counts2:
        raise RuntimeError("Failed to extract counts from sampler result. Try using AerSimulator or check qiskit version.")
    bob_key = extract_bitstring(counts2, bit_num)
    bbits = [int(b) for b in bob_key][::-1]

    # --- Sifting: Alice and Bob compare bases over public channel ---
    agood, bgood = [], []
    for i in range(bit_num):
        if abase[i] == bbase[i]:
            agood.append(int(abits[i]))
            bgood.append(int(bbits[i]))
    sifted_key_len = len(agood)

    # --- Key length limitation for testing ---
    max_key_len = None
    if max_key_len is not None and sifted_key_len > max_key_len:
        sifted_key_len = max_key_len
        agood = agood[:sifted_key_len]
        bgood = bgood[:sifted_key_len]

    # --- Compute fidelity: compare Alice and Bob's sifted keys ---
    matches = sum(1 for a, b in zip(agood, bgood) if a == b)
    mismatches = sum(1 for a, b in zip(agood, bgood) if a != b)
    sifted_len = len(agood)
    fidelity = matches / sifted_len if sifted_len > 0 else 0.0
    loss = 1 - fidelity if sifted_len > 0 else 1.0
    qber = mismatches / sifted_len if sifted_len > 0 else 0.0

    # --- Abort reason: authentic BB84 security threshold ---
    abort_reason = None
    if qber > 0.11:
        abort_reason = (
            "QBER exceeds 11% — BB84 security bound violated. "
            "Secret key cannot be distilled."
        )

    # --- Circuit diagram URL ---
    circuit_diagram_url = "/static/circuit_exp3.png"

    # --- Return results ---
    return {
        "message": message,
        "bit_num": bit_num,
        "backend_type": backend_type,
        "sifted_key_len": sifted_key_len,
        "Sender_bits": abits.tolist() if isinstance(abits, np.ndarray) else list(abits),
        "Sender_bases": abase.tolist() if isinstance(abase, np.ndarray) else list(abase),
        "Receiver_bases": bbase.tolist() if isinstance(bbase, np.ndarray) else list(bbase),
        "Receiver_bits": bbits,
        "eve_bases": ebase.tolist() if isinstance(ebase, np.ndarray) else list(ebase),
        "agoodbits": agood,
        "bgoodbits": bgood,
        "eve_key": eve_key,
        "bob_key": bob_key,
        "counts": counts,
        "counts2": counts2,
        "fidelity": fidelity,
        "qber": qber,
        "loss": loss,
        "abort_reason": abort_reason,
        "circuit_diagram_url": circuit_diagram_url,
    }

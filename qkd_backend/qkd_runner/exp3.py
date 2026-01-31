# qkd_backend/qkd_runner/exp3.py
# BB84 with Eve intercept-resend, executed on IBM Quantum backend using SamplerV2.

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel
from qiskit.primitives import BackendSamplerV2
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qkd_backend.backend_config import get_backend_service
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

def _extract_bitstring_from_counts(counts, rng, shots):
    """Extract a random bitstring sample from counts dict."""
    if not counts:
        raise ValueError("Empty counts dictionary from sampler result.")
    outcomes, freqs = zip(*counts.items())
    probs = np.array(freqs) / shots
    choice = rng.choice(len(outcomes), p=probs)
    return outcomes[choice]

def run_exp3(message=None, bit_num=20, shots=1024, rng_seed=None, backend_type="local", api_token=None):
    rng = np.random.default_rng(rng_seed)

    # Step 1: Sender's random bits and bases
    abits = np.round(rng.random(bit_num)).astype(int)
    abase = np.round(rng.random(bit_num)).astype(int)

    # Step 2: Eve's random measurement bases
    ebase = np.round(rng.random(bit_num)).astype(int)

    # Step 3: Receiver's random measurement bases
    bbase = np.round(rng.random(bit_num)).astype(int)

    # --- Sender prepares and sends qubits ---
    qr = QuantumRegister(bit_num, "q")
    cr = ClassicalRegister(bit_num, "c")
    qc = QuantumCircuit(qr, cr)
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

    # --- Eve intercepts and measures ---
    for m in range(bit_num):
        if ebase[m] == 1:
            qc.h(m)
        qc.measure(qr[m], cr[m])

    # Backend & Sampler selection
    if backend_type == "local":
        # Fast local path: AerSimulator without heavy transpilation
        aer_backend = AerSimulator()
        qc_isa = qc
        sampler = BackendSamplerV2(backend=aer_backend)
    else:
        # IBM runtime backend
        backend = get_backend_service("ibm", api_token=api_token)
        target = backend.target
        pm = generate_preset_pass_manager(target=target, optimization_level=3)
        qc_isa = pm.run(qc)
        # SamplerV2 alias imported as Sampler
        sampler = Sampler(mode=backend)

    # Eve’s measurement
    job = sampler.run([qc_isa], shots=shots)
    res = job.result()
    try:
        counts = res[0].data.c.get_counts()
    except Exception:
        counts = res[0].data.get_counts()
    key = _extract_bitstring_from_counts(counts, rng, shots)
    emeas = list(key)
    ebits = [int(x) for x in emeas][::-1]

    # --- Eve resends to Receiver ---
    qr2 = QuantumRegister(bit_num, "q")
    cr2 = ClassicalRegister(bit_num, "c")
    qc2 = QuantumCircuit(qr2, cr2)
    for n in range(bit_num):
        if ebits[n] == 0:
            if ebase[n] == 1:
                qc2.h(n)
        if ebits[n] == 1:
            if ebase[n] == 0:
                qc2.x(n)
            if ebase[n] == 1:
                qc2.x(n)
                qc2.h(n)

    # Receiver's measurement
    for m in range(bit_num):
        if bbase[m] == 1:
            qc2.h(m)
        qc2.measure(qr2[m], cr2[m])

    if backend_type == "local":
        qc2_isa = qc2
    else:
        qc2_isa = pm.run(qc2)

    job2 = sampler.run([qc2_isa], shots=shots)
    res2 = job2.result()
    try:
        counts2 = res2[0].data.c.get_counts()
    except Exception:
        counts2 = res2[0].data.get_counts()
    key2 = _extract_bitstring_from_counts(counts2, rng, shots)
    bmeas = list(key2)
    bbits = [int(x) for x in bmeas][::-1]

    # Save circuit diagram
    diagram_path = "static/circuit_exp3.png"
    try:
        fig = circuit_drawer(qc2_isa, output='mpl')
        fig.savefig(diagram_path)
        plt.close(fig)
    except Exception:
        # Don't fail if drawing isn't supported in the environment
        diagram_path = None

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

    # After sifting and before returning the result:
    fidelity = match_count / len(agoodbits) if agoodbits else 0
    loss = 1 - fidelity if agoodbits else 1

    # Define abort reason first
    abort_reason = None
    if loss > 0.15:
        abort_reason = "Error too high! Key generation aborted."

    return {
        "Sender_bits": abits.tolist(),
        "Sender_bases": abase.tolist(),
        "Receiver_bases": bbase.tolist(),
        "Receiver_bits": bbits,
        "Eve_bases": ebase.tolist(),  # Add Eve's bases
        "Eve_bits": ebits,            # Add Eve's bits
        "agoodbits": agoodbits,
        "bgoodbits": bgoodbits,
        "fidelity": fidelity,
        "loss": loss,
        "circuit_diagram_url": f"/{diagram_path}" if diagram_path else None,
        "counts_eve": counts,
        "counts_bob": counts2,
        "abort_reason": abort_reason
    }

def run(message=None):
    return run_exp3(message)


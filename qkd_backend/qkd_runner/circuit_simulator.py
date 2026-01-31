# qkd_backend/qkd_runner/circuit_simulator.py
import random
import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

def text_to_bits(text):
    return [int(b) for c in text for b in bin(ord(c))[2:].zfill(8)]

def random_bases(n):
    return [random.choice(['+', 'x']) for _ in range(n)]

def run_circuit_simulator(message, shots=1024):
    bits = text_to_bits(message)
    n = len(bits)
    Sender_bases = random_bases(n)
    Receiver_bases = random_bases(n)

    qc = QuantumCircuit(n, n)
    for i in range(n):
        if bits[i] == 1:
            qc.x(i)
        if Sender_bases[i] == 'x':
            qc.h(i)
    for i in range(n):
        if Receiver_bases[i] == 'x':
            qc.h(i)
        qc.measure(i, i)

    try:
        qasm_str = qc.qasm()
    except Exception:
        qasm_str = ""

    sim = AerSimulator()
    job = sim.run(qc, shots=shots)
    result = job.result()
    counts = result.get_counts()
    counts_int = {str(k): int(v) for k, v in counts.items()}

    matched_positions = [i for i in range(n) if Sender_bases[i] == Receiver_bases[i]]
    total = 0
    errors = 0
    step_details = []
    for bitstring, freq in counts_int.items():
        Receiver_bits = [int(b) for b in bitstring[::-1]]
        for i in matched_positions:
            Sender_bit = bits[i]
            Receiver_bit = Receiver_bits[i] if i < len(Receiver_bits) else None
            mismatch = (Receiver_bit is None) or (Receiver_bit != Sender_bit)
            total += freq
            if mismatch:
                errors += freq
            step_details.append({
                "bitstring": bitstring,
                "freq": int(freq),
                "qubit": i,
                "Sender_bit": int(Sender_bit),
                "Receiver_bit": (int(Receiver_bit) if Receiver_bit is not None else None),
                "basis": Sender_bases[i],
                "mismatch": bool(mismatch)
            })
    qber = (errors / total * 100) if total > 0 else 0.0

    return {
        "qasm": qasm_str,
        "counts": counts_int,
        "qber": round(qber, 2),
        "steps": step_details
    }

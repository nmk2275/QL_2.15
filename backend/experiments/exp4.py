# exp4.py
import random
import numpy as np
import os
from qkd_backend.backend_config import get_backend_service
from qkd_backend.qrng import generate_qrng_bits
try:
    from qiskit_ibm_runtime import SamplerV2 as Sampler
except Exception:
    try:
        from qiskit_ibm_runtime import Sampler as Sampler
    except Exception:
        Sampler = None
try:
    from qiskit_aer import AerSimulator
    HAS_AER = True
except ImportError:
    HAS_AER = False
try:
    from qiskit.primitives import BackendSamplerV2 as BackendSampler
except ImportError:
    try:
        from qiskit.primitives import BackendSampler as BackendSampler
    except ImportError:
        BackendSampler = None
from qiskit import QuantumCircuit, transpile
from qiskit.visualization import circuit_drawer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def run_exp4(num_bits=30, backend_type=None, api_token=None):
    QBER_THRESHOLD = 0.11  # 11%
    channel_loss_prob = 0.15      # 15% extra loss due to Eve tapping
    side_channel_error = 0.03     # 3% disturbance (VERY IMPORTANT: < 11%)
    if backend_type == "ibm":
        backend = get_backend_service("ibm", api_token=api_token)
        sender_bits = generate_qrng_bits(num_bits, backend, shots=1)
        sender_bases = generate_qrng_bits(num_bits, backend, shots=1)
        receiver_bases = generate_qrng_bits(num_bits, backend, shots=1)
        # Quantum circuit: Alice encodes, Bob measures
        qc = QuantumCircuit(num_bits, num_bits)
        for i in range(num_bits):
            if sender_bits[i] == 1:
                qc.x(i)
            if sender_bases[i] == 1:
                qc.h(i)
        qc.barrier()
        for i in range(num_bits):
            if receiver_bases[i] == 1:
                qc.h(i)
            qc.measure(i, i)
        tqc = transpile(qc, backend)
        sampler = Sampler(mode=backend)
        result = sampler.run([tqc], shots=1).result()
        # Robust counts extraction (as in exp1/exp2/exp3)
        counts = None
        if hasattr(result, "quasi_dists"):
            counts = {}
            for dist in result.quasi_dists:
                for int_key, prob in dist.items():
                    bitstring = format(int_key, f"0{num_bits}b")
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
        # Get Bob's measured bits (reverse order)
        measured_key = max(counts, key=counts.get)
        receiver_bits = [int(b) for b in measured_key][::-1]
        # Simulate loss and side-channel error after measurement
        received_mask = []
        noisy_bits = []
        for i in range(num_bits):
            if np.random.random() < channel_loss_prob:
                received_mask.append(False)
                noisy_bits.append(None)
            else:
                received_mask.append(True)
                bit = receiver_bits[i]
                if np.random.random() < side_channel_error:
                    bit ^= 1
                noisy_bits.append(bit)
        receiver_bits = noisy_bits
    else:
        sender_bits = [random.randint(0, 1) for _ in range(num_bits)]
        sender_bases = [random.randint(0, 1) for _ in range(num_bits)]
        receiver_bases = []
        receiver_bits = []
        received_mask = []
        for i in range(num_bits):
            if random.random() < channel_loss_prob:
                received_mask.append(False)
                receiver_bases.append(None)
                receiver_bits.append(None)
                continue
            received_mask.append(True)
            r_basis = random.randint(0, 1)
            receiver_bases.append(r_basis)
            if r_basis == sender_bases[i]:
                bit = sender_bits[i]
            else:
                bit = random.randint(0, 1)
            if random.random() < side_channel_error:
                bit ^= 1
            receiver_bits.append(bit)
        counts = None  # No quantum counts in classical mode
    # -----------------------------
    # Step 3: Sifting
    # -----------------------------
    sender_sifted = []
    receiver_sifted = []
    errors = 0

    for i in range(num_bits):
        if not received_mask[i]:
            continue
        if sender_bases[i] == receiver_bases[i]:
            sender_sifted.append(sender_bits[i])
            receiver_sifted.append(receiver_bits[i])
            if sender_bits[i] != receiver_bits[i]:
                errors += 1

    sift_len = len(sender_sifted)
    qber = errors / sift_len if sift_len > 0 else 0.0

    # -----------------------------
    # Step 4: Metrics
    # -----------------------------
    fidelity = 1 - qber
    loss = 1 - (sum(received_mask) / num_bits)

    encryption_allowed = qber < QBER_THRESHOLD

    # Save circuit diagram if quantum
    diagram_url = None
    if backend_type == "ibm":
        os.makedirs("static", exist_ok=True)
        fig = circuit_drawer(qc, output="mpl")
        fig.savefig("static/circuit_exp4.png")
        plt.close(fig)
        diagram_url = "/static/circuit_exp4.png"
    # -----------------------------
    # Return format (MATCHES exp3)
    # -----------------------------
    return {
        "Sender_bits": sender_bits,
        "Sender_bases": sender_bases,
        "Receiver_bases": receiver_bases,
        "Receiver_bits": receiver_bits,
        "agoodbits": sender_sifted,
        "bgoodbits": receiver_sifted,
        "fidelity": fidelity,
        "loss": loss,
        "qber": qber * 100,  # frontend shows %
        "encryption_allowed": encryption_allowed,
        "counts": counts,
        "diagram": diagram_url,
        "backend_type": backend_type
    }

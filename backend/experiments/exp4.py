# exp4.py
import random
import numpy as np
import os
from backend.backend_config import get_backend_service
from backend.qrng import generate_qrng_bits
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

def run_exp4(num_bits=30, backend_type=None, api_token=None, shots=1024):
    QBER_THRESHOLD = 0.11  # 11%
    channel_loss_prob = 0.15      # 15% extra loss due to Eve tapping
    side_channel_error = 0.03     # 3% disturbance (VERY IMPORTANT: < 11%)
    if backend_type == "ibm":
        backend = get_backend_service("ibm", api_token=api_token)
        sender_bits = generate_qrng_bits(num_bits, backend, shots=1)
        sender_bases = generate_qrng_bits(num_bits, backend, shots=1)
        receiver_bases = generate_qrng_bits(num_bits, backend, shots=1)
        # Quantum circuit: Pure BB84 protocol (preparation and measurement only)
        # Alice prepares qubits: X gates encode bits, H gates encode basis choice
        # Bob measures: H gates for basis choice, then measurement
        # Note: Channel loss and passive Eve effects are classical post-processing (not in circuit)
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
        # Use multiple shots for counts visualization, but extract single bitstring for protocol
        result = sampler.run([tqc], shots=shots).result()
        # Extract raw quantum measurement counts (pre-channel: before loss/noise simulation)
        # These are the direct measurement results from the quantum circuit
        raw_counts = None
        if hasattr(result, "quasi_dists"):
            raw_counts = {}
            bit_num_circuit = tqc.num_qubits
            for dist in result.quasi_dists:
                for int_key, prob in dist.items():
                    bitstring = format(int_key, f"0{bit_num_circuit}b")
                    raw_counts[bitstring] = prob
                break
        if raw_counts is None or not raw_counts:
            try:
                for quasi_dist in result:
                    if hasattr(quasi_dist, 'data'):
                        if hasattr(quasi_dist.data, 'c'):
                            raw_counts = quasi_dist.data.c.get_counts()
                        else:
                            raw_counts = quasi_dist.data.get_counts()
                    break
            except (TypeError, AttributeError, IndexError):
                pass
            if raw_counts is None:
                try:
                    quasi_dist = result[0]
                    if hasattr(quasi_dist, 'data'):
                        if hasattr(quasi_dist.data, 'c'):
                            raw_counts = quasi_dist.data.c.get_counts()
                        else:
                            raw_counts = quasi_dist.data.get_counts()
                except (TypeError, AttributeError, IndexError):
                    pass
            if raw_counts is None:
                try:
                    if hasattr(result, 'get_counts'):
                        raw_counts = result.get_counts()
                    elif hasattr(result, '__iter__'):
                        items = list(result)
                        if items:
                            raw_counts = items[0].data.c.get_counts() if hasattr(items[0].data, 'c') else items[0].data.get_counts()
                except (TypeError, AttributeError, Exception):
                    pass
        if raw_counts is None or not raw_counts:
            raise RuntimeError("Failed to extract counts from sampler result. Try using AerSimulator or check qiskit version.")
        # Get Bob's measured bits (reverse order) from raw_counts
        measured_key = max(raw_counts, key=raw_counts.get)
        receiver_bits = [int(b) for b in measured_key][::-1]
        # Simulate loss and side-channel error after measurement (channel effects applied here)
        received_mask = []
        noisy_bits = []
        for i in range(num_bits):
            if np.random.random() < channel_loss_prob:
                received_mask.append(False)
                noisy_bits.append(None)
                receiver_bases[i] = None  # Loss implies no basis
            else:
                received_mask.append(True)
                bit = receiver_bits[i]
                if np.random.random() < side_channel_error:
                    bit ^= 1
                noisy_bits.append(bit)
        receiver_bits = noisy_bits
    else:
        # Local mode: Use AerSimulator with BackendSamplerV2 (same as exp3)
        sender_bits = [random.randint(0, 1) for _ in range(num_bits)]
        sender_bases = [random.randint(0, 1) for _ in range(num_bits)]
        receiver_bases = [random.randint(0, 1) for _ in range(num_bits)]
        # Quantum circuit: Pure BB84 protocol (preparation and measurement only)
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
        # Backend execution (same method as exp3)
        if not HAS_AER:
            raise RuntimeError("AerSimulator not available.")
        backend = AerSimulator()
        sampler = BackendSampler(backend=backend)
        qc_isa = qc
        result = sampler.run([qc_isa], shots=shots).result()
        # Extract raw quantum measurement counts (same method as exp3)
        raw_counts = None
        if hasattr(result, "quasi_dists"):
            raw_counts = {}
            bit_num_circuit = qc_isa.num_qubits
            for dist in result.quasi_dists:
                for int_key, prob in dist.items():
                    bitstring = format(int_key, f"0{bit_num_circuit}b")
                    raw_counts[bitstring] = prob
                break
        if raw_counts is None or not raw_counts:
            try:
                for quasi_dist in result:
                    if hasattr(quasi_dist, 'data'):
                        if hasattr(quasi_dist.data, 'c'):
                            raw_counts = quasi_dist.data.c.get_counts()
                        else:
                            raw_counts = quasi_dist.data.get_counts()
                    break
            except (TypeError, AttributeError, IndexError):
                pass
            if raw_counts is None:
                try:
                    quasi_dist = result[0]
                    if hasattr(quasi_dist, 'data'):
                        if hasattr(quasi_dist.data, 'c'):
                            raw_counts = quasi_dist.data.c.get_counts()
                        else:
                            raw_counts = quasi_dist.data.get_counts()
                except (TypeError, AttributeError, IndexError):
                    pass
            if raw_counts is None:
                try:
                    if hasattr(result, 'get_counts'):
                        raw_counts = result.get_counts()
                    elif hasattr(result, '__iter__'):
                        items = list(result)
                        if items:
                            raw_counts = items[0].data.c.get_counts() if hasattr(items[0].data, 'c') else items[0].data.get_counts()
                except (TypeError, AttributeError, Exception):
                    pass
        if raw_counts is None or not raw_counts:
            raise RuntimeError("Failed to extract counts from sampler result. Try using AerSimulator or check qiskit version.")
        # Get Bob's measured bits (reverse order) from raw_counts
        measured_key = max(raw_counts, key=raw_counts.get)
        receiver_bits_quantum = [int(b) for b in measured_key][::-1]
        # Simulate loss and side-channel error after measurement (channel effects applied here)
        receiver_bits = []
        received_mask = []
        for i in range(num_bits):
            if random.random() < channel_loss_prob:
                received_mask.append(False)
                receiver_bases[i] = None  # Loss implies no basis
                receiver_bits.append(None)
            else:
                received_mask.append(True)
                bit = receiver_bits_quantum[i]
                if random.random() < side_channel_error:
                    bit ^= 1
                receiver_bits.append(bit)
    # -----------------------------
    # Step 3: Sifting
    # -----------------------------
    # Sift positions where bases match and both bits are valid (not None)
    sender_sifted = []
    receiver_sifted = []
    errors = 0

    for i in range(num_bits):
        # Skip positions that were lost (not received)
        if not received_mask[i]:
            continue
        # Skip positions with None basis or None bit (invalid measurements)
        if receiver_bases[i] is None or receiver_bits[i] is None:
            continue
        # Sift: keep only positions where bases match
        if sender_bases[i] == receiver_bases[i]:
            sender_sifted.append(sender_bits[i])
            receiver_sifted.append(receiver_bits[i])
            # Count errors in sifted positions only
            if sender_bits[i] != receiver_bits[i]:
                errors += 1

    # QBER computed only from sifted bits
    sift_len = len(sender_sifted)
    qber = errors / sift_len if sift_len > 0 else 0.0

    # -----------------------------
    # Step 4: Metrics
    # -----------------------------
    # Fidelity is defined as (1 - QBER), computed only from sifted bits
    fidelity = 1 - qber
    loss = 1 - (sum(received_mask) / num_bits)

    encryption_allowed = qber < QBER_THRESHOLD

    # Circuit diagram URL - always return static file (like exp1/exp2/exp3)
    # Optionally generate new diagram for IBM backend
    circuit_diagram_url = "/static/circuit_exp4.png"
    if backend_type == "ibm":
        # Optionally generate a new circuit diagram for IBM backend
        try:
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            static_dir = os.path.join(backend_dir, "static")
            os.makedirs(static_dir, exist_ok=True)
            circuit_path = os.path.join(static_dir, "circuit_exp4.png")
            fig = circuit_drawer(qc, output="mpl", style='clifford')
            fig.savefig(circuit_path)
            plt.close(fig)
        except Exception as e:
            # If diagram generation fails, use static file
            pass
    
    # -----------------------------
    # Return format (matches exp1/exp2/exp3)
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
        "raw_counts": raw_counts,  # Raw quantum measurements (pre-channel, before loss/noise)
        "counts": raw_counts,  # Alias for frontend compatibility (same as raw_counts)
        "circuit_diagram_url": circuit_diagram_url,
        "backend_type": backend_type
    }

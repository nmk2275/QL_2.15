"""
Quantum Random Number Generator (QRNG)

Provides true quantum randomness using IBM Quantum hardware.
Falls back to NumPy ONLY if real hardware is not available.

Designed as a drop-in replacement for NumPy randomness
across all BB84 experiments (exp1–exp4).
"""

import warnings
import numpy as np
from qiskit import QuantumCircuit

try:
    from qiskit_ibm_runtime import SamplerV2 as Sampler
except Exception:
    try:
        from qiskit_ibm_runtime import Sampler as Sampler
    except Exception:
        Sampler = None

# Track last randomness source (for debugging / UI display)
_last_rng_source = None


# -------------------------------------------------------------------
# Helper: Detect real IBM quantum hardware (NOT simulator)
# -------------------------------------------------------------------
def _is_real_ibm_hardware(backend):
    if backend is None:
        return False
    try:
        name = backend.name()
    except Exception:
        return False
    name = str(name).lower()
    return name.startswith("ibm_") and "sim" not in name and "aer" not in name


# -------------------------------------------------------------------
# Main QRNG API
# -------------------------------------------------------------------
def generate_qrng_bits(n, backend, shots=1, return_source=False):
    """
    Generate n random bits.

    If backend is real IBM hardware:
        → Uses quantum measurement randomness
    Else:
        → Falls back to NumPy PRNG with warning

    Args:
        n (int): Number of bits
        backend: IBM backend instance
        shots (int): Shots for QRNG circuit (default = 1)
        return_source (bool): Return (bits, source) if True

    Returns:
        list[int] OR (list[int], str)
    """
    global _last_rng_source

    if n <= 0:
        raise ValueError("Number of bits must be positive")

    # ----------------------------------------------------------------
    # Fallback path (no IBM hardware)
    # ----------------------------------------------------------------
    if backend is None or not _is_real_ibm_hardware(backend):
        warnings.warn(
            "IBM quantum hardware not detected — using NumPy PRNG",
            UserWarning,
        )
        bits = np.random.randint(0, 2, size=n).tolist()
        _last_rng_source = "numpy_fallback"
        return (bits, _last_rng_source) if return_source else bits

    # ----------------------------------------------------------------
    # Quantum RNG path (REAL hardware)
    # ----------------------------------------------------------------
    if Sampler is None:
        raise RuntimeError("qiskit-ibm-runtime is not installed")

    try:
        # Create QRNG circuit
        qc = QuantumCircuit(n, n)
        for i in range(n):
            qc.h(i)
            qc.measure(i, i)

        # Transpile for backend (safe, no backend.target)
        from qiskit import transpile

        qc_isa = transpile(qc, backend)

        # Run job
        sampler = Sampler(mode=backend)
        job = sampler.run([qc_isa], shots=shots)
        result = job.result()

        # Extract counts (SamplerV2-compatible)
        quasi = result.quasi_dists[0]
        counts = quasi.binary_probabilities()

        # Pick most probable bitstring
        bitstring = max(counts, key=counts.get)

        # Convert to list of ints (little-endian fix)
        bits = [int(b) for b in bitstring][::-1]

        # Ensure exact length
        bits = bits[:n] if len(bits) >= n else bits + [0] * (n - len(bits))

        _last_rng_source = "ibm_quantum"
        return (bits, _last_rng_source) if return_source else bits

    except Exception as e:
        warnings.warn(
            f"IBM QRNG failed — falling back to NumPy ({e})",
            UserWarning,
        )
        bits = np.random.randint(0, 2, size=n).tolist()
        _last_rng_source = "numpy_fallback"
        return (bits, _last_rng_source) if return_source else bits


# -------------------------------------------------------------------
# Optional helper (for UI / debugging)
# -------------------------------------------------------------------
def get_last_rng_source():
    """
    Returns:
        "ibm_quantum" | "numpy_fallback" | None
    """
    return _last_rng_source

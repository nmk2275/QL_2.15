import streamlit as st
import math
from math import gcd
import matplotlib.pyplot as plt
from collections import Counter

st.set_page_config(page_title="Shor’s Algorithm Visualized", layout="centered")

st.title("🔓 Shor’s Algorithm — Visual & Beginner Friendly")

st.markdown("""
This app **visually explains how Shor’s algorithm breaks RSA**  
by finding a **repeating pattern**, not by guessing factors directly.
""")

st.divider()

# -------------------------
# PANEL 1: RSA LOCK
# -------------------------
st.header("🟦 Panel 1: RSA Lock")

N = st.number_input(
    "Choose a public number (N)",
    min_value=4,
    step=1,
    value=15,
    help="Choose a small composite number like 15, 21, 33"
)

if N <= 3:
    st.error("Choose a composite number greater than 3.")
    st.stop()

st.markdown(f"""
**Public number (N):** `{N}`  
**Hidden inside:** `? × ?`
""")

st.info(
    "RSA security depends on the fact that "
    "finding the hidden factors of N is hard for classical computers."
)

st.divider()

# -------------------------
# PANEL 2: BRUTE FORCE
# -------------------------
st.header("🟦 Panel 2: Why brute force is slow")

with st.expander("Try brute-force factorization"):
    found = False
    for i in range(2, int(math.sqrt(N)) + 1):
        if N % i == 0:
            st.write(f"✅ Found factor: {i}")
            found = True
            break
        else:
            st.write(f"❌ {i} does not divide {N}")
    if not found:
        st.write("❌ No small factors found")

st.warning(
    "This works only for small N. "
    "For large RSA numbers, brute force is impossible."
)

st.divider()

# -------------------------
# PANEL 3: PATTERN GENERATION
# -------------------------
st.header("🟦 Panel 3: Creating a repeating pattern")

a = st.number_input(
    "Choose a number (a) such that gcd(a, N) = 1",
    min_value=2,
    step=1,
    value=2
)

if gcd(a, N) != 1:
    st.error("gcd(a, N) must be 1. Choose another a.")
    st.stop()

st.markdown(f"""
We compute the values:

`f(x) = a^x mod N`

This function **always repeats** when N has hidden factors.
""")

values = []
for x in range(0, 10):
    values.append(pow(a, x, N))

# Display table
st.subheader("Pattern Table")

st.table({
    "x": list(range(10)),
    f"{a}^x mod {N}": values
})

# Detect period
period = None
for r in range(1, len(values)):
    if values[r] == values[0]:
        period = r
        break

if period:
    st.success(f"🔁 Pattern detected! Period (r) = {period}")
else:
    st.warning("No clear period detected (try another a).")

st.divider()

# -------------------------
# PANEL 4: QUANTUM IDEA (VISUAL)
# -------------------------
st.header("🟦 Panel 4: How a quantum computer helps")

st.markdown("""
A **classical computer** checks values one by one:

`x = 0 → 1 → 2 → 3 → ...`

A **quantum computer** evaluates **all x values at once**,  
then highlights the **repeating pattern**.

This is why Shor’s algorithm is fast.
""")

st.divider()

# -------------------------
# PANEL 5: MEASUREMENT HISTOGRAM (SIMULATED)
# -------------------------
st.header("🟦 Panel 5: Measurement result (visual)")

# Fake quantum-like measurement emphasizing multiples of period
samples = []
for i in range(100):
    samples.append((i * period) % (2 * period))

counts = Counter(samples)

fig, ax = plt.subplots()
ax.bar(counts.keys(), counts.values())
ax.set_xlabel("Measured values")
ax.set_ylabel("Frequency")
ax.set_title("Histogram showing repeating structure")

st.pyplot(fig)

st.info(
    "The equal spacing between peaks reveals the period."
)

st.divider()

# -------------------------
# PANEL 6: PATTERN → FACTORS
# -------------------------
st.header("🟦 Panel 6: Turning the pattern into factors")

if period and period % 2 == 0:
    x = pow(a, period // 2, N)

    f1 = gcd(x - 1, N)
    f2 = gcd(x + 1, N)

    if f1 > 1 and f2 > 1:
        st.success("🔓 RSA Broken!")
        st.markdown(f"""
**Period (r):** `{period}`  
**Computed value:** `a^(r/2) = {x}`  

### ✅ Hidden factors found:
- `{f1}`
- `{f2}`

So:
{N} = {f1} × {f2}

""")
    else:
        st.warning("Pattern found, but factors did not emerge (try another a).")
else:
    st.warning("Period must be even to extract factors.")

st.divider()

# -------------------------
# FINAL TAKEAWAY
# -------------------------
st.header("🧠 Final Takeaway")

st.markdown("""
- RSA hides **two numbers inside one**
- Shor **does not guess** those numbers
- It finds a **repeating pattern**
- That pattern **mathematically exposes** the hidden factor
            s

This is why **RSA is not safe** against quantum computers.
""")
import streamlit as st
import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
import networkx as nx

# --- Streamlit App ---
st.set_page_config(page_title="Multi-user QKD BB84 Simulator", layout="wide")
st.title("Multi-User QKD BB84 Simulator with Trusted Nodes")

# --- 1. User-set (Input) Parameters ---
st.sidebar.header("Input Parameters")

total_distance = st.sidebar.number_input("Total distance (km)", min_value=1, value=500)
link_length = st.sidebar.number_input("Link length per trusted node (km)", min_value=1, value=100)
n_users = st.sidebar.number_input("Number of receivers (N_users)", min_value=1, value=3)
session_key_length = st.sidebar.selectbox("K_session length (bits)", [128, 256, 512, 1024])
distribution_mode = st.sidebar.selectbox("Distribution mode", ["Sequential", "Parallel"])
detector_efficiency = st.sidebar.slider("Detector efficiency (%)", 0, 100, 90)
dark_count_prob = st.sidebar.number_input("Dark count probability", 0.0, 0.01, 0.001)
channel_attenuation = st.sidebar.number_input("Channel attenuation (dB/km)", 0.0, 1.0, 0.2)
misalignment_error = st.sidebar.slider("Misalignment error (%)", 0, 10, 2)
key_relay_latency = st.sidebar.number_input("Key relay latency per hop (ms)", min_value=0, value=5)

# Optional: allow per-user distances
user_distances = []
for i in range(1, n_users + 1):
    d = st.sidebar.number_input(f"Distance to Bob{i} (km)", min_value=1, value=int(total_distance*i/n_users))
    user_distances.append(d)

# --- 2. Derived Parameters Calculation Functions ---
def calculate_trusted_nodes(distance, link_length):
    return math.ceil(distance / link_length)

def calculate_per_link_qber(detector_eff, dark_count, attenuation, misalignment):
    # Simplified QBER formula
    qber = (100 - detector_eff) * 0.01 + dark_count*100 + misalignment
    return round(qber, 2)

def calculate_end_to_end_qber(per_link_qber, n_hops):
    # Approximate: Q_total = 1 - (1 - qber_per_link)^n
    q_total = 1 - ((1 - per_link_qber/100) ** n_hops)
    return round(q_total * 100, 2)

def calculate_key_rate(end_to_end_qber, base_rate=50):
    # Simplified formula: key rate decreases with QBER
    rate = base_rate * (1 - end_to_end_qber/100)
    return round(rate, 2)

def calculate_time_to_form_key(session_length, key_rate, n_hops, latency):
    # Total time = session_length / key_rate + hop latencies
    t = session_length / key_rate + n_hops * latency / 1000.0  # convert ms to s
    return round(t, 2)

# --- 3. Simulate per-user ---
data = []
for i, dist in enumerate(user_distances):
    user_name = f"Bob{i+1}"
    n_hops = calculate_trusted_nodes(dist, link_length)
    per_link_qber = calculate_per_link_qber(detector_efficiency, dark_count_prob, channel_attenuation, misalignment_error)
    end_to_end_qber = calculate_end_to_end_qber(per_link_qber, n_hops)
    key_rate = calculate_key_rate(end_to_end_qber)
    time_to_form = calculate_time_to_form_key(session_key_length, key_rate, n_hops, key_relay_latency)
    success_flag = "✔" if key_rate > 0 else "✖"
    data.append([user_name, dist, n_hops, per_link_qber, end_to_end_qber, key_rate, success_flag, time_to_form, session_key_length])

# --- 4. Output Table ---
df = pd.DataFrame(data, columns=[
    "Receiver", "Distance (km)", "Trusted Nodes", "Per-link QBER (%)",
    "End-to-end QBER (%)", "End-to-end Key Rate (kbps)", "K_session formed?", 
    "Time to Form Key (s)", "Final Key Length (bits)"
])
st.subheader("Per-Receiver Output Table")
st.dataframe(df)

# --- 5. Summary Statistics ---
avg_qber = round(df["End-to-end QBER (%)"].mean(),2)
total_key_rate = round(df["End-to-end Key Rate (kbps)"].sum(),2)
success_count = df["K_session formed?"].value_counts().get("✔",0)
failure_count = df["K_session formed?"].value_counts().get("✖",0)
total_time = round(df["Time to Form Key (s)"].sum(),2)

st.subheader("Summary Statistics")
st.markdown(f"- **Average end-to-end QBER across all users:** {avg_qber}%")
st.markdown(f"- **Total key generation rate for all users:** {total_key_rate} kbps")
st.markdown(f"- **Number of successful sessions:** {success_count}")
st.markdown(f"- **Number of failed sessions:** {failure_count}")
st.markdown(f"- **Total time to form all session keys:** {total_time} s")

# --- 6. Visualizations ---
st.subheader("Visualizations")

# Bar chart: Key Rate per User
st.markdown("**Key Rate per User**")
plt.figure(figsize=(8,4))
plt.bar(df["Receiver"], df["End-to-end Key Rate (kbps)"], color='skyblue')
plt.ylabel("Key Rate (kbps)")
plt.xlabel("Receiver")
st.pyplot(plt)

# Line graph: Per-link QBER (simplified example for first user)
st.markdown("**Per-link QBER Along the Path (Example: Bob1)**")
plt.figure(figsize=(8,4))
per_link_qbers = [calculate_per_link_qber(detector_efficiency, dark_count_prob, channel_attenuation, misalignment_error)]*calculate_trusted_nodes(user_distances[0], link_length)
plt.plot(range(1,len(per_link_qbers)+1), per_link_qbers, marker='o', linestyle='-', color='orange')
plt.ylabel("Per-link QBER (%)")
plt.xlabel("Hop Number")
plt.title("Bob1 QBER per Hop")
st.pyplot(plt)

# 6c. Network Diagram with color-coded session success/failure
st.markdown("**Network Diagram (Alice → Trusted Nodes → Bobs)**")
G = nx.Graph()
G.add_node("Alice")
node_colors = []

for i, dist in enumerate(user_distances):
    prev = "Alice"
    n_hops = calculate_trusted_nodes(dist, link_length)
    # add hops
    for h in range(1, n_hops+1):
        node_name = f"Node{i+1}_{h}"
        G.add_node(node_name)
        G.add_edge(prev, node_name)
        prev = node_name
        node_colors.append('lightgreen')  # trusted nodes always green
    # connect final hop to Bob
    bob_name = f"Bob{i+1}"
    G.add_node(bob_name)
    G.add_edge(prev, bob_name)
    # color-code Bob by session success/failure
    color = 'green' if df.loc[i, "K_session formed?"] == "✔" else 'red'
    node_colors.append(color)

plt.figure(figsize=(10,6))
pos = nx.spring_layout(G, seed=42)
# Generate node color list for all nodes: Alice + trusted nodes + Bobs
all_nodes = list(G.nodes())
colors_final = ['skyblue']  # Alice
for node in all_nodes[1:]:
    if "Bob" in node:
        idx = int(node.replace("Bob","")) - 1
        colors_final.append('green' if df.loc[idx,"K_session formed?"]=="✔" else 'red')
    else:
        colors_final.append('lightgreen')  # trusted node

nx.draw(G, pos, with_labels=True, node_color=colors_final, node_size=1200, font_size=10, font_weight='bold', edge_color='gray')
st.pyplot(plt)
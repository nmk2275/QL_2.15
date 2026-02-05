Quantum Key Distribution (BB84) Simulator 🔐⚛️

A lightweight, interactive simulator that demonstrates Quantum Key Distribution (QKD) using the BB84 protocol.
Built with Python and Flask, this project visualizes how two parties (Alice & Bob) can securely exchange cryptographic keys using quantum mechanics — and how eavesdropping can be detected through QBER.

This project is designed for demos, academic use, and hands-on understanding of quantum cryptography principles.

⭐ Features

⚛️ BB84 Protocol Simulation

Implements the full workflow of BB84:

Qubit generation

Random basis selection

Measurement

Sifting

Key reconciliation

QBER (Quantum Bit Error Rate) calculation

🧪 Eavesdropper Simulation (Eve)

Enable/disable Eve to visualize:

How qubit interception alters measurement

How eavesdropping increases QBER

Why BB84 guarantees secure communication

🌐 Clean Web Interface

Built using Flask + HTML/CSS/JS, the interface lets users:

Start a round of key distribution

View each stage visually

See generated bits, bases, sifted keys, and QBER

Download or view the final secure key

📸 UI Screenshot

<img width="1470" height="798" alt="image" src="https://github.com/user-attachments/assets/ee5efe91-73a4-4143-8fa6-28aa79708441" />
<img width="1465" height="805" alt="image" src="https://github.com/user-attachments/assets/3666799f-cdf8-484a-a744-ea577051f4d8" />


🧠 Backend Engine

The backend/ module contains:

Core BB84 logic

Random qubit preparation

Measurement & basis matching

QBER computation

Secure key extraction

🚀 How It Works

1️⃣ Qubit Generation

Alice generates:

A random bit string

A random basis string (+ or ×)

2️⃣ Transmission

Each bit is encoded into a qubit using Alice’s basis selection.

3️⃣ Bob’s Measurement

Bob measures each qubit in a randomly chosen basis.

4️⃣ Sifting

Alice and Bob compare bases publicly and keep only matching positions.

5️⃣ QBER Calculation

QBER is computed to detect eavesdropping:

QBER = (# mismatched bits due to noise/interception) / total bits

6️⃣ Secure Key Extraction

If QBER is acceptable → final key is generated.
If QBER is high → communication is considered compromised.

🛠️ Tech Stack

Python

Flask

HTML / CSS / JavaScript

Custom BB84 implementation

💻 Run Locally
1. Install dependencies
pip install -r requirements.txt

2. Run Flask server
python app.py

3. Open in browser
http://127.0.0.1:5000

📈 Future Enhancements

Support for E91 & B92 QKD protocols

Exportable experiment logs

Real-time qubit animation

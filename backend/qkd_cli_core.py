import random
import numpy as np
from itertools import product
from flask import Flask, request, jsonify

app = Flask(__name__)


class QKDCLI:
    """
    EXACT logic copy of Tkinter QKDCLI.
    Only UI (tkinter) removed.
    """

    def __init__(self):
        # ---- SAME STATE ----
        self.current_mode = "user"

        # -------- SYSTEM (REAL HARDWARE) --------
        self.system = {
            "nodes": {},
            "link": {"loss": 0.2, "noise": 0.01, "distance": 10},
            "receiver": {"dark_count": 0.0005}
        }

        # -------- EXPERIMENT (SWEEP SETTINGS) --------
        self.sweep = {
            "mode": None,
            "parameters": {}
        }

        self.results = []

        # ---- UI REPLACEMENT BUFFER ----
        self._output_buffer = []

    # ---------------- PROMPT ----------------
    def get_prompt(self):
        prompts = {
            "user": "QKD-Sim> ",
            "privileged": "QKD-Sim# ",
            "config": "QKD-Sim(config)# ",
            "experiment": "QKD-Sim(experiment)# "
        }
        return prompts[self.current_mode]

    def write(self, text, newline=True):
        # Append each line separately to _output_buffer, ignore newline argument
        for line in str(text).splitlines():
            self._output_buffer.append(line)

    # ---------------- COMMAND ENTRY ----------------
    def execute(self, cmd):
        """
        Replaces Tkinter <Return> handler.
        """
        self._output_buffer = []
        self.process_command(cmd.strip())
        return self._output_buffer

    # ---------------- COMMAND HANDLER ----------------
    def process_command(self, cmd):
        cmd = cmd.lower()

        if self.current_mode == "user":
            if cmd == "enable":
                self.current_mode = "privileged"
            else:
                self.write("Unknown command")

        elif self.current_mode == "privileged":
            if cmd == "configure terminal":
                self.current_mode = "config"
            elif cmd == "experiment configure":
                self.current_mode = "experiment"
            elif cmd.startswith("run bb84"):
                eve_on = "eve" in cmd
                self.run_bb84_experiment(eve_on)
            elif cmd == "show results summary":
                self.show_results_summary()
            elif cmd == "show system":
                self.show_system()
            elif cmd == "exit":
                # Tkinter used root.quit()
                # In core logic we return to user mode
                self.current_mode = "user"
            else:
                self.write("Unknown command")

        elif self.current_mode == "config":
            if cmd.startswith("create node"):
                parts = cmd.split()
                self.system["nodes"][parts[2]] = parts[4]
                self.write(f"Node {parts[2]} created as {parts[4]}")

            elif cmd.startswith("create link"):
                parts = cmd.split()
                a, b, dist = parts[2], parts[3], float(parts[4])
                self.system["link"]["nodes"] = (a, b)
                self.system["link"]["distance"] = dist
                self.write(f"Link {a}-{b} set with distance {dist} km")

            elif cmd.startswith("set loss"):
                self.system["link"]["loss"] = float(cmd.split()[2])
                self.write("Loss set")

            elif cmd.startswith("set channel-noise"):
                self.system["link"]["noise"] = float(cmd.split()[2])
                self.write("Channel noise set")

            elif cmd.startswith("set dark-count"):
                self.system["receiver"]["dark_count"] = float(cmd.split()[2])
                self.write("Dark count set")

            elif cmd == "exit":
                self.current_mode = "privileged"

        elif self.current_mode == "experiment":
            if cmd.startswith("sweep mode"):
                self.sweep["mode"] = cmd.split()[2]
                self.write(f"Sweep mode set to {self.sweep['mode']}")

            elif cmd.startswith("sweep parameter"):
                parts = cmd.split()
                param = parts[2]
                start, end, step = float(parts[3]), float(parts[4]), float(parts[6])
                self.sweep["parameters"][param] = (start, end, step)
                self.write(f"Sweep set for {param}")

            elif cmd == "show sweep-plan":
                self.show_sweep_plan()

            elif cmd == "exit":
                self.current_mode = "privileged"

    # ---------------- DISPLAY ----------------
    def show_system(self):
        self.write("System Configuration:")
        for n, r in self.system["nodes"].items():
            self.write(f"  Node: {n} ({r})")
        self.write(f"  Distance: {self.system['link']['distance']} km")
        self.write(f"  Loss: {self.system['link']['loss']} dB/km")
        self.write(f"  Noise: {self.system['link']['noise']}")
        self.write(f"  Dark Count: {self.system['receiver']['dark_count']}")

    def show_sweep_plan(self):
        if not self.sweep["mode"]:
            self.write("No sweep configured")
            return
        self.write(f"Sweep Mode: {self.sweep['mode']}")
        for p, (s, e, st) in self.sweep["parameters"].items():
            self.write(f"  {p}: {s} → {e} (step {st})")

    # ---------------- BB84 ENGINE ----------------
    def run_bb84_experiment(self, eve_on):
        if not self.sweep["mode"]:
            self.write("Configure experiment first.")
            return

        self.results.clear()
        run_number = 1

        def generate_values(start, end, step):
            vals, v = [], start
            while v <= end + 1e-9:
                vals.append(round(v, 5))
                v += step
            return vals

        names, value_lists = [], []
        for p, (s, e, st) in self.sweep["parameters"].items():
            names.append(p)
            value_lists.append(generate_values(s, e, st))

        combos = product(*value_lists) if self.sweep["mode"] == "combo" else zip(*value_lists)

        for combo in combos:
            self.simulate_bb84_run(run_number, dict(zip(names, combo)), eve_on)
            run_number += 1

        self.write("Experiment completed.")

    def simulate_bb84_run(self, run_number, param_values, eve_on):
        # -------- Hardware baseline (non-ideal reality) --------
        BASE_LOSS = 0.2
        BASE_NOISE = 0.005
        BASE_DARK = 0.0005
        INTRINSIC_QBER = 0.01

        user_loss = param_values.get("loss", self.system["link"]["loss"])
        user_noise = param_values.get("channel-noise", self.system["link"]["noise"])
        user_dark = param_values.get("dark-count", self.system["receiver"]["dark_count"])

        loss = max(user_loss, BASE_LOSS)
        noise = max(user_noise, BASE_NOISE)
        dark = max(user_dark, BASE_DARK)

        distance = self.system["link"]["distance"]
        transmission_prob = 10 ** (-(loss * distance) / 10)

        detector_eff = 0.15
        photons = 5000
        sifted, errors = 0, 0

        for _ in range(photons):
            alice_bit = random.randint(0, 1)
            alice_basis = random.choice(["Z", "X"])

            if random.random() > transmission_prob:
                continue

            if eve_on:
                eve_basis = random.choice(["Z", "X"])
                photon_bit = alice_bit if eve_basis == alice_basis else random.randint(0, 1)
                photon_basis = eve_basis
            else:
                photon_bit = alice_bit
                photon_basis = alice_basis

            bob_basis = random.choice(["Z", "X"])
            detected = np.random.poisson(detector_eff) > 0 or np.random.poisson(dark) > 0
            if not detected:
                continue

            bob_bit = photon_bit if bob_basis == photon_basis else random.randint(0, 1)

            if random.random() < noise:
                bob_bit ^= 1

            if bob_basis == alice_basis:
                sifted += 1
                if bob_bit != alice_bit:
                    errors += 1

        if sifted > 0:
            intrinsic_errors = max(1, int(INTRINSIC_QBER * sifted))
            errors = max(errors, intrinsic_errors)

        qber = errors / sifted if sifted else 0
        final_key = int(sifted * (1 - 2 * qber)) if qber < 0.11 else 0
        secure = qber < 0.11

        self.results.append({
            "run": run_number,
            "params": param_values,
            "qber": qber,
            "sifted": sifted,
            "final": final_key,
            "secure": secure
        })

        self.write(f"Run {run_number}: QBER={qber*100:.2f}% Secure={secure}")

    # ---------------- RESULTS TABLE ----------------
    def show_results_summary(self):
        if not self.results:
            self.write("No results available.")
            return

        self.write("Loss     Channel-Noise   Sifted Key   QBER(%)   Final Key   Secure")
        self.write("---------------------------------------------------------------------")

        for r in self.results:
            loss = r["params"].get("loss", self.system["link"]["loss"])
            noise = r["params"].get("channel-noise", self.system["link"]["noise"])
            sifted = r["sifted"]
            qber = r["qber"] * 100
            final = r["final"]
            secure = r["secure"]

            self.write(f"{loss:<8} {noise:<15} {sifted:<12} {qber:<8.2f} {final:<11} {secure}")

cli_instance = QKDCLI()

@app.route("/cli/command", methods=["POST"])
def cli_command():
    data = request.get_json()
    command = data.get("command", "")
    output = cli_instance.execute(command)
    # TEMP DEBUG LOG - REMOVE IN PRODUCTION
    print(f"[DEBUG] /cli/command received: '{command}' | Output lines: {len(output)}")
    return jsonify({
        "prompt": cli_instance.get_prompt(),
        "output": output
    })
import random
from itertools import product

class QKDCLI:
    def __init__(self):
        self.current_mode = "user"
        self.system = {
            "nodes": {},
            "link": {"loss": 0.0, "noise": 0.0},
            "receiver": {"dark_count": 0.0}
        }
        self.sweep = {
            "mode": None,
            "parameters": {}
        }
        self.results = []
        self.command_history = []
        self.history_index = -1
        self.output_buffer = []

    def print_prompt(self):
        prompts = {
            "user": "QKD-Sim> ",
            "privileged": "QKD-Sim# ",
            "config": "QKD-Sim(config)# "
        }
        self.output_buffer.append(prompts[self.current_mode])

    def write(self, text, newline=True):
        if newline:
            self.output_buffer.append(text)
        else:
            if self.output_buffer:
                self.output_buffer[-1] += text
            else:
                self.output_buffer.append(text)

    def process_command(self, cmd):
        cmd = cmd.strip()
        self.output_buffer = []
        if cmd:
            self.command_history.append(cmd)
            self.history_index = len(self.command_history)
        cmd_l = ' '.join(cmd.lower().split())  # Normalize whitespace
        if self.current_mode == "user":
            if cmd_l == "enable":
                self.current_mode = "privileged"
            else:
                self.write("Unknown command")
        elif self.current_mode == "privileged":
            if cmd_l == "configure terminal":
                self.current_mode = "config"
            elif cmd_l == "show system":
                self.show_system()
            elif cmd_l.startswith("run bb84"):
                eve_on = cmd_l.strip() == "run bb84 eve"
                self.run_bb84_experiment(eve_on)
            elif cmd_l == "show results summary":
                self.show_results_summary()
            elif cmd_l == "exit":
                self.write("Exiting...")
            else:
                self.write("Unknown command")
        elif self.current_mode == "config":
            if cmd_l.startswith("create node"):
                self.create_node(cmd)
            elif cmd_l.startswith("create link"):
                self.create_link(cmd)
            elif cmd_l.startswith("set loss"):
                self.system["link"]["loss"] = float(cmd.split()[2])
                self.write("Link loss set")
            elif cmd_l.startswith("set channel-noise"):
                self.system["link"]["noise"] = float(cmd.split()[2])
                self.write("Channel noise set")
            elif cmd_l.startswith("set dark-count"):
                self.system["receiver"]["dark_count"] = float(cmd.split()[2])
                self.write("Dark count set")
            elif cmd_l.startswith("sweep mode"):
                mode = cmd.split()[2]
                if mode in ["single", "paired", "combo"]:
                    self.sweep["mode"] = mode
                    self.write(f"Sweep mode set to {mode}")
                else:
                    self.write("Invalid sweep mode")
            elif cmd_l.startswith("sweep parameter"):
                parts = cmd.split()
                try:
                    param = parts[2]
                    start = float(parts[3])
                    end = float(parts[4])
                    step = float(parts[6])
                    self.sweep["parameters"][param] = (start, end, step)
                    self.write(f"Sweep set for {param}")
                except:
                    self.write("Usage: sweep parameter <name> <start> <end> step <value>")
            elif cmd_l == "show sweep-plan":
                self.show_sweep_plan()
            elif cmd_l == "exit":
                self.current_mode = "privileged"
            else:
                self.write("Unknown command")
        self.print_prompt()
        return self.output_buffer

    def create_node(self, cmd):
        parts = cmd.split()
        if len(parts) >= 5:
            name = parts[2]
            role = parts[4]
            self.system["nodes"][name] = role
            self.write(f"Node {name} created as {role}")
        else:
            self.write("Usage: create node <name> role <transmitter/receiver>")

    def create_link(self, cmd):
        parts = cmd.split()
        if len(parts) == 4:
            a, b = parts[2], parts[3]
            if a in self.system["nodes"] and b in self.system["nodes"]:
                self.write(f"Link created between {a} and {b}")
            else:
                self.write("Both nodes must exist first")
        else:
            self.write("Usage: create link Alice Bob")

    def show_system(self):
        self.write("System Configuration:")
        for n, r in self.system["nodes"].items():
            self.write(f"  Node: {n} ({r})")
        self.write(f"  Link Loss: {self.system['link']['loss']}")
        self.write(f"  Channel Noise: {self.system['link']['noise']}")
        self.write(f"  Dark Count: {self.system['receiver']['dark_count']}")

    def show_sweep_plan(self):
        if not self.sweep["mode"] or not self.sweep["parameters"]:
            self.write("No sweep configured")
            return
        self.write(f"Sweep Mode: {self.sweep['mode']}")
        total_runs = 1
        for p, (start, end, step) in self.sweep["parameters"].items():
            values = int((end - start) / step) + 1
            total_runs *= values
            self.write(f"  {p}: {start} → {end} (step {step})")
        self.write(f"Total Runs: {total_runs}")

    # -------- REAL BB84 ENGINE --------
    def run_bb84_experiment(self, eve_on):
        if not self.sweep["mode"] or not self.sweep["parameters"]:
            self.write("Sweep not configured.")
            return
        self.results.clear()
        self.write("Starting BB84 experiment (photon-level simulation)...")
        def generate_values(start, end, step):
            vals = []
            v = start
            while v <= end + 1e-9:
                vals.append(round(v, 5))
                v += step
            return vals
        run_number = 1
        mode = self.sweep["mode"]
        params = self.sweep["parameters"]
        if mode == "single":
            p, (s, e, st) = list(params.items())[0]
            for val in generate_values(s, e, st):
                self.simulate_bb84_run(run_number, {p: val}, eve_on)
                run_number += 1
        elif mode == "paired":
            items = list(params.items())
            p1, (s1, e1, st1) = items[0]
            p2, (s2, e2, st2) = items[1]
            vals1 = generate_values(s1, e1, st1)
            vals2 = generate_values(s2, e2, st2)
            for v1, v2 in zip(vals1, vals2):
                self.simulate_bb84_run(run_number, {p1: v1, p2: v2}, eve_on)
                run_number += 1
        elif mode == "combo":
            names = []
            value_lists = []
            for p, (s, e, st) in params.items():
                names.append(p)
                value_lists.append(generate_values(s, e, st))
            for combo in product(*value_lists):
                self.simulate_bb84_run(run_number, dict(zip(names, combo)), eve_on)
                run_number += 1
        self.write("Experiment completed.")

    def simulate_bb84_run(self, run_number, param_values, eve_on):
        loss = param_values.get("loss", self.system["link"]["loss"])
        noise = param_values.get("channel-noise", self.system["link"]["noise"])
        dark = param_values.get("dark-count", self.system["receiver"]["dark_count"])
        photons = 1000
        sifted_len = 0
        errors = 0
        for _ in range(photons):
            alice_bit = random.randint(0, 1)
            alice_basis = random.choice(["Z", "X"])
            if random.random() < loss:
                continue
            if eve_on:
                eve_basis = random.choice(["Z", "X"])
                if eve_basis == alice_basis:
                    eve_bit = alice_bit
                else:
                    eve_bit = random.randint(0, 1)
                alice_bit, alice_basis = eve_bit, eve_basis
            bob_basis = random.choice(["Z", "X"])
            if bob_basis == alice_basis:
                bob_bit = alice_bit
            else:
                bob_bit = random.randint(0, 1)
            if random.random() < (noise + dark):
                bob_bit ^= 1
            if bob_basis == alice_basis:
                sifted_len += 1
                if alice_bit != bob_bit:
                    errors += 1
        qber = errors / sifted_len if sifted_len else 0
        final_key = int(sifted_len * (1 - 2 * qber))
        secure = qber < 0.11
        self.results.append({
            "run": run_number,
            "params": param_values,
            "qber": qber,
            "sifted_key": sifted_len,
            "final_key": max(final_key, 0),
            "secure": secure
        })
        self.write(f"Run {run_number} done → {param_values}")

    def show_results_summary(self):
        if not self.results:
            self.write("No results available.")
            return
        self.write("Run | Params | QBER | Sifted Key | Final Key | Secure")
        for r in self.results:
            status = "Yes" if r["secure"] else "No"
            self.write(f"{r['run']} | {r['params']} | {r['qber']*100:.2f}% | {r['sifted_key']} | {r['final_key']} | {status}")

    def get_prompt(self):
        prompts = {
            "user": "QKD-Sim> ",
            "privileged": "QKD-Sim# ",
            "config": "QKD-Sim(config)# "
        }
        return prompts[self.current_mode]

# Test block for local testing
if __name__ == "__main__":
    cli = QKDCLI()
    cmds = ["enable", "configure terminal", "set loss 0.1", "exit"]
    for cmd in cmds:
        output = cli.process_command(cmd)
        print(f"Command: {cmd}")
        for line in output:
            print(line)
        print("-"*30)
// Enhanced QKD Simulator JavaScript
// Message Encryption and Animation Functionality

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    
    // Enhanced Message Encryption Handler
    const encryptBtn = document.getElementById("encryptBtn");
    if (encryptBtn) {
        encryptBtn.onclick = async function() {
            const message = document.getElementById("userMessage").value;
            if (!message.trim()) {
                alert("Please enter a message to encrypt");
                return;
            }
            
            if (!window.lastExpData) {
                alert("Please run an experiment first to generate a quantum key");
                return;
            }
            
            const cryptoOutput = document.getElementById("cryptoOutput");
            cryptoOutput.innerHTML = "Encrypting message with quantum key...";
            
            try {
                const res = await fetch("/run/" + window.lastExpType, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message: message })
                });
                const data = await res.json();
                
                if (data.error) {
                    cryptoOutput.innerHTML = 
                        `<div style="color:#ef4444;"><b>Error:</b> ${data.error}</div>`;
                } else {
                    cryptoOutput.innerHTML = 
                        `<div><b>Original Message:</b> ${data.original_message}</div>
                         <div style="margin-top:8px;"><b>Encrypted (hex):</b><br><span style="font-family:monospace; word-break:break-all; background:rgba(255,255,255,0.1); padding:4px; border-radius:4px;">${data.encrypted_message_hex}</span></div>
                         <div style="margin-top:8px;"><b>Decrypted:</b> <span style="color:var(--text);">${data.decrypted_message}</span></div>
                         <div style="margin-top:8px; font-size:12px; color:var(--accent1);"><b>✅ Success:</b> Message encrypted and decrypted using quantum key!</div>`;
                }
            } catch (error) {
                cryptoOutput.innerHTML = 
                    `<div style="color:#ef4444;"><b>Error:</b> ${error.message}</div>`;
            }
        };
    }
    
    // Capture experiment data when experiments are run
    const runExpButtons = document.querySelectorAll('button[onclick*="runExp"]');
    runExpButtons.forEach(button => {
        const originalOnClick = button.onclick;
        button.onclick = async function() {
            try {
                const result = await originalOnClick.call(this);
                // Store experiment data globally
                if (result && typeof result === 'object') {
                    window.lastExpData = result;
                    window.lastExpType = this.textContent.includes('1') ? 'exp1' : 
                                        this.textContent.includes('2') ? 'exp2' :
                                        this.textContent.includes('3') ? 'exp3' : 'exp4';
                }
            } catch (error) {
                console.log('Error capturing experiment data:', error);
            }
        };
    });

    // Simulation Animation Handler
    const simulationBtn = document.getElementById("simulationBtn");
    if (simulationBtn) {
        simulationBtn.onclick = function() {
            const Sender = nodes.find(n => n.type === 'Sender');
            const Receiver = nodes.find(n => n.type === 'Receiver');
            
            if (!Sender || !Receiver) {
                alert('Please place Sender and Receiver nodes on the canvas first');
                return;
            }
            
            const route = findRoute(Sender, Receiver);
            if (!route) {
                alert('Please connect Sender and Receiver with fiber (drag Fiber tool, then click Sender → Receiver)');
                return;
            }
            
            // Check if we have experiment data to use
            if (!window.lastExpData) {
                alert('Please run an experiment first to generate quantum data for simulation');
                return;
            }
            
            // Create side panel with logs and Bloch sphere
            createSidePanel();
            
            // Start simulation using actual experiment data
            startQuantumSimulation(route, window.lastExpData);
        };
    }
});

// Create side panel with tabs for logs and Bloch sphere
function createSidePanel() {
    let sidePanel = document.getElementById('sidePanel');

    // compute a responsive panel width
    const DEFAULT_WIDTH = 520;
    const vw = window.innerWidth || document.documentElement.clientWidth;
    const PANEL_WIDTH = vw < 1000 ? Math.max(360, Math.floor(vw * 0.40)) : DEFAULT_WIDTH;

    const appEl = document.querySelector('.app');
    const canvasWrap = document.querySelector('.canvas-wrap');

    // If there's already a panel, just ensure it's visible and sized
    if (sidePanel) {
        sidePanel.style.flex = `0 0 ${PANEL_WIDTH}px`;
        sidePanel.style.width = PANEL_WIDTH + 'px';
        sidePanel.style.opacity = '1';
        sidePanel.style.display = 'flex';
        // ensure canvasWrap shrinks
        if (canvasWrap) canvasWrap.style.flex = '1 1 auto';
        
        // Re-initialize or render if panel exists
        setTimeout(() => {
            initializeBlochSphere();
        }, 50);
        return;
    }

    // create semantic aside that participates in layout
    sidePanel = document.createElement('aside');
    sidePanel.id = 'sidePanel';
    sidePanel.setAttribute('role', 'complementary');
    sidePanel.setAttribute('aria-label', 'Quantum Analysis');

    // initial collapsed state (zero width) so animation expands it
    sidePanel.style.cssText = `
        flex: 0 0 0;
        width: 0px;
        height: 100vh;
        overflow-y: auto;
        background: linear-gradient(180deg, var(--bg2), rgba(0,0,0,0.36));
        border-left: 1px solid rgba(255,255,255,0.03);
        padding: 18px 14px;
        box-sizing: border-box;
        box-shadow: -12px 0 40px rgba(0,0,0,0.55);
        transition: width 300ms cubic-bezier(.2,.9,.2,1), opacity 220ms ease;
        opacity: 0;
        display: flex;
        flex-direction: column;
        z-index: 1100;
    `;

    // Stacked layout: Logs on top (full width) and Bloch Sphere below (replaces experiment results)
    sidePanel.innerHTML = `
        <style>
            /* Scoped styles for the side panel stacked layout */
            #sidePanel .side-panel-body { display: flex; flex-direction: column; gap: 12px; align-items: stretch; }
            #sidePanel .side-panel-body > div { box-sizing: border-box; }
            #sidePanel #logsColumn { width: 100%; }
            #sidePanel #blochBottom { width: 100%; }
            /* Bloch sphere: use full available width (maximize) */
            #sidePanel #blochSphere { height: 200px; min-height: 120px; max-height: 520px; width: 100%; max-width: none; margin: 0; }
             @media (max-width: 800px) {
                 #sidePanel { padding: 12px; }
                 #sidePanel #blochSphere { height: 140px !important; width: 100% !important; max-width: none; }
             }
         </style>
        <div class="side-panel-header" style="flex:0 0 auto;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                <h3 style="margin:0;color:var(--e9f7ff, #e9f7ff);font-size:15px;">Quantum Analysis</h3>
                <button id="closeSidePanel" aria-label="Close" style="background:rgba(255,255,255,0.06);border:none;color:var(--e9f7ff, #fff);border-radius:6px;padding:6px 8px;cursor:pointer;font-size:14px;">✕</button>
            </div>
        </div>

        <div class="side-panel-body" style="flex:1 1 auto; min-height:220px;">
            <div id="logsColumn" style="background:rgba(0,0,0,0.02); padding:8px; border-radius:8px; display:flex; flex-direction:column;">
                <h4 style="margin:0 0 8px 0;color:var(--accent2);font-size:13px;">⚛️ Quantum Measurement Logs</h4>
                <div id="measurementLogs" style="flex:1 1 auto; background:rgba(0,0,0,0.18); border-radius:8px; padding:10px; overflow-y:auto; font-family:monospace; font-size:12px; color:var(--accent2);"></div>
            </div>

            <!-- Bloch sphere moved to bottom replacing the experiment results area -->
            <div id="blochBottom" style="background:transparent; padding:6px 0 0 0; margin-top:8px;">
                <h4 style="margin:6px 0 8px 0;color:var(--accent2);font-size:13px;">🌀 Bloch Sphere</h4>
                <div id="blochSphere" style="background:rgba(0,0,0,0.12); border-radius:8px; display:flex; align-items:center; justify-content:center; color:var(--accent2); overflow:hidden;"></div>
            </div>
        </div>

        <!-- Experiment results removed; Bloch sphere now occupies that space -->
    `;

    // Insert the panel as the last child of .app so flex layout places it to the right
    if (appEl) {
        appEl.appendChild(sidePanel);
        // ensure app is flex (template already sets .app display:flex)
        appEl.style.display = appEl.style.display || 'flex';
        // make canvas shrink to allow panel space
        if (canvasWrap) {
            canvasWrap.dataset._origFlex = canvasWrap.style.flex || '';
            canvasWrap.style.flex = '1 1 auto';
            canvasWrap.style.minWidth = '0'; // important to allow shrinking
        }
    } else {
        document.body.appendChild(sidePanel);
    }

    // prevent horizontal scrollbar while panel is visible
    document.documentElement.style.overflowX = 'hidden';

    // Show panel: expand width and set opacity
    requestAnimationFrame(() => {
        sidePanel.style.width = PANEL_WIDTH + 'px';
        sidePanel.style.flex = `0 0 ${PANEL_WIDTH}px`;
        sidePanel.style.opacity = '1';
    });

    // Close button: collapse and cleanup
    const closeBtn = sidePanel.querySelector('#closeSidePanel');
    closeBtn.addEventListener('click', () => {
        sidePanel.style.width = '0px';
        sidePanel.style.flex = '0 0 0';
        sidePanel.style.opacity = '0';

        const onEnd = () => {
            // restore canvas styles
            if (canvasWrap && canvasWrap.dataset._origFlex !== undefined) {
                canvasWrap.style.flex = canvasWrap.dataset._origFlex;
                delete canvasWrap.dataset._origFlex;
            }
            // remove panel element
            if (sidePanel && sidePanel.parentNode) sidePanel.parentNode.removeChild(sidePanel);
            // reset bloch sphere instance so it re-initializes with new canvas
            window.blochSphere = null;
            blochSphere = null;
            // restore overflow
            document.documentElement.style.overflowX = '';
            sidePanel.removeEventListener('transitionend', onEnd);

            // stop any ongoing animation
            if (window.animationInProgress) {
                window.animationInProgress = false;
            }
        };
        sidePanel.addEventListener('transitionend', onEnd);
    });

    // ensure logs area scroll styling
    const measurementLogs = document.getElementById('measurementLogs');
    if (measurementLogs) {
        measurementLogs.style.overflowY = 'auto';
        measurementLogs.style.maxHeight = 'calc(100vh - 340px)';
    }

    // Initialize Bloch sphere shortly after showing
    setTimeout(() => {
        initializeBlochSphere();
        if (window.blochSphere) {
            if (typeof window.blochSphere.resizeToContainer === 'function') window.blochSphere.resizeToContainer();
            addMeasurementLog('🌀 Bloch sphere initialized (bottom view) - ready for quantum state visualization!', 'info');
        }
    }, 140);
}

// Add measurement log entry
function addMeasurementLog(message, type = 'info') {
    const logsEl = document.getElementById('measurementLogs');
    if (logsEl) {
        // Use theme-aware CSS variables so colors follow the page theme
        const colors = {
            'info': 'var(--muted)',          // informational — muted text
            'alice': 'var(--text)',          // Alice messages — normal text
            'bob': 'var(--text)',            // Bob messages — normal text
            'eve': 'var(--accent1)',         // Eve / warnings — red accent
            'success': 'var(--accent1)'      // success/important — red accent (matches Streamlit style)
        };
        const timestamp = new Date().toLocaleTimeString();
        // Make timestamp muted and message body the chosen color
        const logEntry = `
          <div style="margin-bottom:6px; line-height:1.25;">
            <span style="color:var(--muted); font-family:monospace; margin-right:6px;">[${timestamp}]</span>
            <span style="color:${colors[type] || colors.info};">${message}</span>
          </div>`;
        logsEl.innerHTML += logEntry;
        logsEl.scrollTop = logsEl.scrollHeight;
    }
}

// Tab switching removed — provide a no-op for backward compatibility
function switchTab() {
    // Tabs removed: logs and Bloch sphere are shown side-by-side. No action required.
}

// Start quantum simulation with animation using real experiment data
function startQuantumSimulation(route, expData) {
    // Display experiment summary
    updateExperimentSummary(expData);
    
    addMeasurementLog("🔬 Initializing BB84 Protocol Simulation with Real Quantum Data", "info");
    addMeasurementLog(`📡 Route: ${route.map(n => n.type).join(' → ')}`, "info");
    
    // Use actual experiment data instead of random generation
    const abits = expData.abits || expData.Sender_bits || [];
    const abase = expData.abase || expData.Sender_bases || [];
    const bbase = expData.bbase || expData.Receiver_bases || [];
    const bbits = expData.bbits || expData.Receiver_bits || [];
    
    // Eve detection - check multiple possible field names and structures
    let ebase = [];
    let ebits = [];
    
    // For exp3 (intercept-resend Eve)
    if (expData.Eve_bases) {
        ebase = expData.Eve_bases;
        ebits = expData.Eve_bits || [];
    }
    // For exp4 (partial Eve)
    else if (expData.eve_bases) {
        ebase = expData.eve_bases;
        ebits = expData.eve_bits || [];
    }
    // Legacy field names
    else if (expData.ebase) {
        ebase = expData.ebase;
        ebits = expData.ebits || [];
    }
    
    // Additional Eve detection based on QBER threshold
    const qber = expData.qber || (expData.loss * 100) || 0;
    const highQber = qber > 11; // Security threshold
    
    const numQubits = abits.length;
    let currentQubit = 0;
    
    addMeasurementLog(`🎯 Using ${numQubits} qubits from experiment data`, "info");
    
    // Enhanced Eve detection
    const evePresent = ebase.length > 0 || highQber;
    if (evePresent) {
        if (ebase.length > 0) {
            addMeasurementLog("⚠️ Eve detected in experiment data - will show interception", "eve");
        } else if (highQber) {
            addMeasurementLog(`🚨 High QBER (${qber.toFixed(1)}%) suggests Eve interference - simulating interception`, "eve");
            // Generate Eve data for simulation when QBER is high but no explicit Eve data
            ebase = Array(numQubits).fill(0).map(() => Math.random() < 0.5 ? 0 : 1);
            ebits = Array(numQubits).fill(0).map(() => Math.random() < 0.5 ? 0 : 1);
        }
    } else {
        addMeasurementLog("✅ No Eve detected - secure communication", "success");
    }
    
    // Convert bases to consistent format if needed
    const formatBase = (base) => {
        if (typeof base === 'number') return base === 0 ? '+' : 'x';
        return base;
    };
    
    const aliceBits = abits;
    const aliceBases = abase.map(formatBase);
    const bobBases = bbase.map(formatBase);
    const bobBits = bbits;
    const eveBases = ebase.map(formatBase);
    const eveBits = ebits;
    
    addMeasurementLog(`👩‍💻 Alice's bits: [${aliceBits.join(', ')}]`, "alice");
    addMeasurementLog(`👩‍💻 Alice's bases: [${aliceBases.join(', ')}]`, "alice");
    addMeasurementLog(`👨‍💻 Bob's bases: [${bobBases.join(', ')}]`, "bob");
    
    // Step-by-step simulation controls and helpers
    function injectStepControls() {
        const sidePanel = document.getElementById('sidePanel');
        if (!sidePanel) return;
        if (document.getElementById('stepControls')) return; // already injected

        const header = sidePanel.querySelector('.side-panel-header');
        const ctrl = document.createElement('div');
        ctrl.id = 'stepControls';
        ctrl.style.cssText = 'display:flex;gap:8px;align-items:center;justify-content:flex-start;margin:8px 0;flex:0 0 auto;';

        ctrl.innerHTML = `
            <div style="display:flex;gap:6px;align-items:center;">
                <button id="stepPrev" class="btn btn.secondary" title="Previous step">Prev</button>
                <button id="stepPlay" class="btn" title="Play">Play</button>
                <button id="stepPause" class="btn" title="Pause" style="display:none;">Pause</button>
                <button id="stepNext" class="btn btn.secondary" title="Next step">Next</button>
                <button id="stepRestart" class="btn btn.secondary" title="Restart">Restart</button>
            </div>
            <div id="stepIndicator" style="margin-left:12px;color:var(--muted);font-size:13px;">Step 0 / 0</div>
        `;

        // insert after header
        if (header && header.parentNode) {
            header.parentNode.insertBefore(ctrl, header.nextSibling);
        } else {
            sidePanel.insertBefore(ctrl, sidePanel.firstChild);
        }

        // wire events
        document.getElementById('stepPrev').addEventListener('click', () => { prevStep(); });
        document.getElementById('stepNext').addEventListener('click', () => { nextStep(); });
        document.getElementById('stepPlay').addEventListener('click', () => { startPlay(); });
        document.getElementById('stepPause').addEventListener('click', () => { pausePlay(); });
        document.getElementById('stepRestart').addEventListener('click', () => { restartSimulation(); });
    }

    function buildSimulationStepsFromExpData(expData) {
        // normalize fields
        const abits = expData.abits || expData.Sender_bits || expData.agoodbits || expData.Sender_bits || [];
        const abase = expData.abase || expData.Sender_bases || expData.Alice_bases || [];
        const bbase = expData.bbase || expData.Receiver_bases || expData.Receiver_bases || [];
        const bbits = expData.bbits || expData.Receiver_bits || [];

        // Eve detection
        let ebase = [];
        let ebits = [];
        if (expData.Eve_bases) { ebase = expData.Eve_bases; ebits = expData.Eve_bits || []; }
        else if (expData.eve_bases) { ebase = expData.eve_bases; ebits = expData.eve_bits || []; }
        else if (expData.ebase) { ebase = expData.ebase; ebits = expData.ebits || []; }

        // ensure arrays lengths
        const n = Math.max(abits.length, bbits.length, abase.length, bbase.length);
        const steps = [];
        const fmt = (base) => (typeof base === 'number' ? (base === 0 ? '+' : 'x') : base || '+');

        for (let i = 0; i < n; i++) {
            steps.push({
                aliceBit: (abits[i] !== undefined ? abits[i] : (expData.agoodbits && expData.agoodbits[i] !== undefined ? expData.agoodbits[i] : 0)),
                aliceBase: fmt(abase[i]),
                bobBit: (bbits[i] !== undefined ? bbits[i] : 0),
                bobBase: fmt(bbase[i]),
                eveBase: ebase[i] !== undefined ? fmt(ebase[i]) : null,
                eveBit: ebits[i] !== undefined ? ebits[i] : null,
                index: i
            });
        }

        window.simulationSteps = steps;
        // set default control state
        window.currentStepIndex = -1;
        window.simulationPlaying = false;
        updateStepInfo();
    }

    function updateStepInfo() {
        const ind = document.getElementById('stepIndicator');
        const total = (window.simulationSteps && window.simulationSteps.length) ? window.simulationSteps.length : 0;
        const idx = (typeof window.currentStepIndex === 'number' && window.currentStepIndex >= 0) ? window.currentStepIndex + 1 : 0;
        if (ind) ind.textContent = `Step ${idx} / ${total}`;
    }

    function animateQubitOnCanvasPromise(route, bit, basis) {
        return new Promise((resolve) => {
            // guard: if no route, fallback to center-left -> center-right animation
            const vw = window.innerWidth || document.documentElement.clientWidth;
            const vh = window.innerHeight || document.documentElement.clientHeight;

            const createFallbackRect = (xFrac = 0.15, yFrac = 0.5) => ({
                left: Math.floor(vw * xFrac),
                top: Math.floor(vh * yFrac),
                width: 0,
                height: 0
            });

            let startRect = null;
            let endRect = null;

            if (route && route.length >= 2) {
                const startNode = route[0];
                const endNode = route[route.length - 1];
                try {
                    if (startNode && startNode.el) startRect = startNode.el.getBoundingClientRect();
                    if (endNode && endNode.el) endRect = endNode.el.getBoundingClientRect();
                } catch (e) {
                    startRect = null; endRect = null;
                }
            }

            // Try to find DOM nodes by common selectors if route nodes didn't provide elements
            if (!startRect) {
                const el = document.querySelector('#node-sender, .node-sender, [data-node-type="Sender"]');
                if (el) startRect = el.getBoundingClientRect();
            }
            if (!endRect) {
                const el = document.querySelector('#node-receiver, .node-receiver, [data-node-type="Receiver"]');
                if (el) endRect = el.getBoundingClientRect();
            }

            // final fallback to viewport positions
            if (!startRect) startRect = createFallbackRect(0.12, 0.5);
            if (!endRect) endRect = createFallbackRect(0.88, 0.5);

            const qubit = document.createElement('div');
            qubit.className = 'quantum-bit';
            qubit.textContent = `${bit}${basis}`;
            qubit.style.cssText = [
                'position:fixed',
                'width:40px',
                'height:40px',
                'border-radius:50%',
                'background:linear-gradient(45deg, var(--accent1), var(--accent2))',
                'display:flex',
                'align-items:center',
                'justify-content:center',
                'color:white',
                'font-weight:bold',
                'font-size:14px',
                'z-index:20000',
                'box-shadow:0 6px 30px rgba(0,0,0,0.6), 0 0 30px rgba(255,75,75,0.18)',
                'transition: transform 0.85s cubic-bezier(.2,.9,.2,1), opacity 0.3s ease',
                'pointer-events:none',
                'will-change: transform, left, top'
            ].join(';');

            // place at start
            const startLeft = startRect.left + (startRect.width || 0) / 2 - 20;
            const startTop = startRect.top + (startRect.height || 0) / 2 - 20;
            const endLeft = endRect.left + (endRect.width || 0) / 2 - 20;
            const endTop = endRect.top + (endRect.height || 0) / 2 - 20;

            qubit.style.transform = `translate3d(${startLeft}px, ${startTop}px, 0)`;
            qubit.style.opacity = '1';
            document.body.appendChild(qubit);

            // Force a reflow then animate to end position using translate3d delta
            requestAnimationFrame(() => {
                const dx = endLeft - startLeft;
                const dy = endTop - startTop;
                qubit.style.transform = `translate3d(${startLeft + dx}px, ${startTop + dy}px, 0)`;

                // cleanup after transition
                const onEnd = () => {
                    if (qubit && qubit.parentNode) qubit.parentNode.removeChild(qubit);
                    qubit.removeEventListener('transitionend', onEnd);
                    resolve();
                };

                // safety timeout
                const to = setTimeout(() => { if (qubit && qubit.parentNode) qubit.parentNode.removeChild(qubit); resolve(); }, 1200);
                qubit.addEventListener('transitionend', () => { clearTimeout(to); onEnd(); });
            });
        });
    }

    async function performStep(stepIndex) {
        const steps = window.simulationSteps || [];
        if (!steps[stepIndex]) return;
        const s = steps[stepIndex];
        const route = window._lastRouteForSteps;

        // Alice sends
        addMeasurementLog(`📡 Qubit ${stepIndex + 1}: Alice sends |${s.aliceBit}⟩ in ${s.aliceBase} basis`, 'alice');
        if (window.blochSphere) {
            const aliceState = window.blochSphere.mapBasisBitToVector(s.aliceBase, s.aliceBit);
            window.blochSphere.animateToVector(aliceState, 300);
        }

        // animate qubit on canvas
        if (route) await animateQubitOnCanvasPromise(route, s.aliceBit, s.aliceBase);

        // Eve (if any)
        if (s.eveBase) {
            addMeasurementLog(`🔴 Eve intercepts and measures in ${s.eveBase} basis → ${s.eveBit}`, 'eve');
            if (window.blochSphere) {
                const eveState = window.blochSphere.mapBasisBitToVector(s.eveBase, s.eveBit || 0);
                window.blochSphere.animateToVector(eveState, 220);
            }
            // small pause for visualization
            await new Promise(r => setTimeout(r, 180));
        }

        // Bob measures
        addMeasurementLog(`👨‍💻 Bob measures in ${s.bobBase} basis → ${s.bobBit}`, 'bob');
        if (window.blochSphere) {
            const bobState = window.blochSphere.mapBasisBitToVector(s.bobBase, s.bobBit || 0);
            window.blochSphere.animateToVector(bobState, 220);
        }

        // Sifting
        if (s.aliceBase === s.bobBase) {
            const match = (s.aliceBit === s.bobBit);
            const matchText = match ? '✅ Match' : '❌ Mismatch';
            const color = match ? 'success' : 'eve';
            addMeasurementLog(`🎯 Bases match (${s.aliceBase}): ${matchText}`, color);
        } else {
            addMeasurementLog(`🔄 Bases differ (${s.aliceBase} vs ${s.bobBase}): Discarded`, 'info');
        }

        // small settle delay
        await new Promise(r => setTimeout(r, 220));
    }

    async function replayUpTo(targetIndex) {
        const steps = window.simulationSteps || [];
        const logsEl = document.getElementById('measurementLogs');
        if (logsEl) logsEl.innerHTML = '';
        if (window.blochSphere) {
            const zero = { x: 0, y: 0, z: 1, label: '|0⟩' };
            window.blochSphere.animateToVector(zero, 80);
        }

        // replay quickly (no canvas animations) to build deterministic state
        for (let i = 0; i <= targetIndex; i++) {
            const s = steps[i];
            if (!s) continue;
            addMeasurementLog(`📡 Qubit ${i + 1}: Alice sends |${s.aliceBit}⟩ in ${s.aliceBase} basis`, 'alice');
            if (window.blochSphere) window.blochSphere.animateToVector(window.blochSphere.mapBasisBitToVector(s.aliceBase, s.aliceBit), 80);
            if (s.eveBase) {
                addMeasurementLog(`🔴 Eve intercepts and measures in ${s.eveBase} basis → ${s.eveBit}`, 'eve');
                if (window.blochSphere) window.blochSphere.animateToVector(window.blochSphere.mapBasisBitToVector(s.eveBase, s.eveBit || 0), 60);
            }
            addMeasurementLog(`👨‍💻 Bob measures in ${s.bobBase} basis → ${s.bobBit}`, 'bob');
            if (window.blochSphere) window.blochSphere.animateToVector(window.blochSphere.mapBasisBitToVector(s.bobBase, s.bobBit || 0), 80);
            if (s.aliceBase === s.bobBase) {
                const match = (s.aliceBit === s.bobBit);
                const matchText = match ? '✅ Match' : '❌ Mismatch';
                const color = match ? 'success' : 'eve';
                addMeasurementLog(`🎯 Bases match (${s.aliceBase}): ${matchText}`, color);
            } else {
                addMeasurementLog(`🔄 Bases differ (${s.aliceBase} vs ${s.bobBase}): Discarded`, 'info');
            }
        }
    }

    async function nextStep() {
        const steps = window.simulationSteps || [];
        if (!steps.length) return;
        if (window.simulationPlaying) return; // avoid manual next during play
        if (window.currentStepIndex >= steps.length - 1) return;
        window.currentStepIndex++;
        updateStepInfo();
        await performStep(window.currentStepIndex);
    }

    async function prevStep() {
        if (!window.simulationSteps || !window.simulationSteps.length) return;
        if (window.currentStepIndex <= 0) {
            // reset to zero
            window.currentStepIndex = -1;
            const logsEl = document.getElementById('measurementLogs'); if (logsEl) logsEl.innerHTML = '';
            if (window.blochSphere) window.blochSphere.animateToVector({ x:0,y:0,z:1, label: '|0⟩' }, 120);
            updateStepInfo();
            return;
        }
        window.currentStepIndex--;
        // fast rebuild up to currentStepIndex
        await replayUpTo(window.currentStepIndex);
        updateStepInfo();
    }

    async function startPlay() {
        if (!window.simulationSteps || !window.simulationSteps.length) return;
        window.simulationPlaying = true;
        const playBtn = document.getElementById('stepPlay');
        const pauseBtn = document.getElementById('stepPause');
        if (playBtn) playBtn.style.display = 'none';
        if (pauseBtn) pauseBtn.style.display = '';

        while (window.simulationPlaying && window.currentStepIndex < window.simulationSteps.length - 1) {
            window.currentStepIndex++;
            updateStepInfo();
            await performStep(window.currentStepIndex);
            // allow exit early
            if (!window.simulationPlaying) break;
        }

        window.simulationPlaying = false;
        if (playBtn) playBtn.style.display = '';
        if (pauseBtn) pauseBtn.style.display = 'none';
    }

    function pausePlay() {
        window.simulationPlaying = false;
        const playBtn = document.getElementById('stepPlay');
        const pauseBtn = document.getElementById('stepPause');
        if (playBtn) playBtn.style.display = '';
        if (pauseBtn) pauseBtn.style.display = 'none';
    }

    function restartSimulation() {
        window.simulationPlaying = false;
        const playBtn = document.getElementById('stepPlay');
        const pauseBtn = document.getElementById('stepPause');
        if (playBtn) playBtn.style.display = '';
        if (pauseBtn) pauseBtn.style.display = 'none';
        window.currentStepIndex = -1;
        const logsEl = document.getElementById('measurementLogs'); if (logsEl) logsEl.innerHTML = '';
        if (window.blochSphere) window.blochSphere.animateToVector({ x:0,y:0,z:1, label: '|0⟩' }, 200);
        updateStepInfo();
    }

    // Hook into startQuantumSimulation: place the hook lines after steps arrays are constructed
    // Create step controls after ensuring side panel is created
    injectStepControls();
    // Build simulation steps from experiment data
    buildSimulationStepsFromExpData(expData);
    
    // Start qubit-by-qubit animation
    animateQuantumProtocol(route, aliceBits, aliceBases, bobBases, bobBits, eveBases, eveBits, 0);
}

// Update experiment summary display
function updateExperimentSummary(expData) {
    const summaryEl = document.getElementById('experimentSummary');
    if (summaryEl && expData) {
        let fidelity = expData.fidelity || 0;
        let qber = expData.qber || 0;
        
        // Handle both percentage and decimal formats
        if (fidelity > 1) {
            // Already in percentage format
            fidelity = fidelity;
        } else {
            // Convert decimal to percentage
            fidelity = fidelity * 100;
        }
        
        if (qber === 0 && expData.loss !== undefined) {
            // Use loss as QBER if QBER not provided
            qber = expData.loss > 1 ? expData.loss : expData.loss * 100;
        }
        
        // Enhanced Eve detection for summary
        let evePresent = false;
        if (expData.Eve_bases && expData.Eve_bases.length > 0) {
            evePresent = true;
        } else if (expData.eve_bases && expData.eve_bases.length > 0) {
            evePresent = true;
        } else if (expData.ebase && expData.ebase.length > 0) {
            evePresent = true;
        } else if (qber > 11) {
            evePresent = true; // High QBER suggests Eve
        }
        
        summaryEl.innerHTML = `
            <div style="color:var(--accent1); margin-bottom:8px;"><strong>Experiment Results</strong></div>
            <div style="color:var(--text);">Fidelity: ${fidelity.toFixed(1)}%</div>
            <div style="color:var(--accent1);">QBER: ${qber.toFixed(1)}%</div>
            <div style="color:${evePresent ? 'var(--accent1)' : 'var(--text)'};">
                Eve: ${evePresent ? 'Detected ⚠️' : 'Not Present ✅'}
            </div>
            <div style="color:var(--text); margin-top:8px; font-size:11px;">
                Key Length: ${expData.agoodbits ? expData.agoodbits.length : 'N/A'} bits
            </div>
        `;
    }
}

// Animate quantum protocol step by step
function animateQuantumProtocol(route, aliceBits, aliceBases, bobBases, bobBits, eveBases, eveBits, qubitIndex) {
    // Set a flag to track if animation is in progress
    window.animationInProgress = true;
    
    if (qubitIndex >= aliceBits.length || !window.animationInProgress) {
        addMeasurementLog("✅ Quantum protocol simulation complete!", "success");
        window.animationInProgress = false;
        return;
    }
    
    const bit = aliceBits[qubitIndex];
    const aliceBase = aliceBases[qubitIndex];
    const bobBase = bobBases[qubitIndex];
    const bobBit = bobBits[qubitIndex];
    const evePresent = eveBases.length > 0;
    const eveBase = evePresent ? eveBases[qubitIndex] : null;
    const eveBit = evePresent ? eveBits[qubitIndex] : null;
    
    // Alice prepares and sends the qubit
    addMeasurementLog(`📡 Qubit ${qubitIndex + 1}: Alice sends |${bit}⟩ in ${aliceBase} basis`, "alice");
    
    // Update Bloch sphere to show Alice's prepared state
    if (blochSphere) {
        const aliceState = blochSphere.mapBasisBitToVector(aliceBase, bit);
        blochSphere.animateToVector(aliceState, 400);
    }
    
    // Create and animate the qubit on the canvas
    animateQubitOnCanvas(route, bit, aliceBase);
    
    // Show Eve interception if present
    if (evePresent) {
        setTimeout(() => {
            if (!window.animationInProgress) return;
            
            addMeasurementLog(`🔴 Eve intercepts and measures in ${eveBase} basis → ${eveBit}`, "eve");
            
            // Update Bloch sphere to show Eve's measurement result
            if (blochSphere) {
                const eveState = blochSphere.mapBasisBitToVector(eveBase, eveBit);
                blochSphere.animateToVector(eveState, 300);
            }
            
            // Visual indicator for Eve interception
            const eveNode = document.getElementById('node-eve');
            if (eveNode) {
                eveNode.style.boxShadow = '0 0 20px #ef4444';
                setTimeout(() => {
                    if (eveNode) eveNode.style.boxShadow = '0 10px 30px rgba(0,0,0,0.45)';
                }, 500);
            }
        }, 500);
    }
    
    // Bob's measurement
    setTimeout(() => {
        if (!window.animationInProgress) return;
        
        addMeasurementLog(`👨‍💻 Bob measures in ${bobBase} basis → ${bobBit}`, "bob");
        
        // Update Bloch sphere to show Bob's measurement result
        if (blochSphere) {
            const bobState = blochSphere.mapBasisBitToVector(bobBase, bobBit);
            blochSphere.animateToVector(bobState, 300);
        }
        
        // Check if bases match and show sifting result
        if (aliceBase === bobBase) {
            const match = bit === bobBit;
            const matchText = match ? "✅ Match" : "❌ Mismatch";
            const color = match ? "success" : "eve";
            addMeasurementLog(`🎯 Bases match (${aliceBase}): ${matchText}`, color);
        } else {
            addMeasurementLog(`🔄 Bases differ (${aliceBase} vs ${bobBase}): Discarded`, "info");
        }
        
        // Continue with next qubit - use a shorter delay for better performance
        setTimeout(() => {
            if (window.animationInProgress) {
                animateQuantumProtocol(route, aliceBits, aliceBases, bobBases, bobBits, eveBases, eveBits, qubitIndex + 1);
            }
        }, 200);
    }, evePresent ? 800 : 400);
}

// Animate a qubit on the canvas between nodes
function animateQubitOnCanvas(route, bit, basis) {
    if (!route || route.length < 2 || !window.animationInProgress) return;
    
    // Create animated qubit element
    const qubit = document.createElement('div');
    qubit.className = 'quantum-bit';
    qubit.style.cssText = 'position:absolute; width:40px; height:40px; border-radius:50%; background:linear-gradient(45deg, var(--accent1), var(--accent2)); display:flex; align-items:center; justify-content:center; color:white; font-weight:bold; font-size:14px; z-index:1000; box-shadow:0 0 20px rgba(255,75,75,0.25); transition: all 0.5s ease-in-out;';
    qubit.textContent = `${bit}${basis}`;
    
    document.body.appendChild(qubit);
    
    // Get start and end positions
    const startNode = route[0]; // Sender
    const endNode = route[route.length - 1]; // Receiver
    
    // Check if nodes have elements
    if (!startNode.el || !endNode.el) {
        qubit.remove();
        return;
    }
    
    const startRect = startNode.el.getBoundingClientRect();
    const endRect = endNode.el.getBoundingClientRect();
    
    // Set initial position
    qubit.style.left = (startRect.left + startRect.width / 2 - 25) + 'px';
    qubit.style.top = (startRect.top + startRect.height / 2 - 25) + 'px';
    
    // Animate to end position
    setTimeout(() => {
        if (!window.animationInProgress) {
            qubit.remove();
            return;
        }
        
        qubit.style.transition = 'all 1s ease-in-out';
        qubit.style.left = (endRect.left + endRect.width / 2 - 25) + 'px';
        qubit.style.top = (endRect.top + endRect.height / 2 - 25) + 'px';
        
        // Remove after animation completes
        setTimeout(() => {
            if (qubit.parentNode) qubit.remove();
        }, 1200);
    }, 100);
}

// Legacy function - kept for compatibility
function animateQuantumBit(index, route, bit, aliceBase, bobBase, isEvePresent, onComplete) {
    // Create animated qubit element
    const qubit = document.createElement('div');
    qubit.style.cssText = 'position:absolute; width:50px; height:50px; border-radius:50%; background:linear-gradient(45deg, var(--accent1), var(--accent2)); display:flex; align-items:center; justify-content:center; color:white; font-weight:bold; font-size:14px; z-index:1000; box-shadow:0 0 20px rgba(255,75,75,0.25);';
    qubit.textContent = `${bit}${aliceBase}`;
    
    document.body.appendChild(qubit);
    
    // Calculate path for animation
    const startNode = route[0];
    const startRect = startNode.el.getBoundingClientRect();
    
    // Set initial position
    qubit.style.left = (startRect.left + startRect.width / 2 - 25) + 'px';
    qubit.style.top = (startRect.top + startRect.height / 2 - 25) + 'px';
    
    // Animate along the route
    let currentRouteIndex = 0;
    
    function animateToNextNode() {
        if (currentRouteIndex >= route.length - 1) {
            // Reached Bob - perform measurement
            const measured = (aliceBase === bobBase) ? bit : Math.random() < 0.5 ? 0 : 1;
            const match = aliceBase === bobBase;
            
            addMeasurementLog(`📥 Qubit ${index + 1}: Bob measures with ${bobBase} → ${measured} ${match ? '✓' : '✗'}`, "bob");
            
            setTimeout(() => {
                if (qubit.parentNode) qubit.remove();
                onComplete();
            }, 500);
            return;
        }
        
        const nextNode = route[currentRouteIndex + 1];
        const nextRect = nextNode.el.getBoundingClientRect();
        
        // Handle Eve interception
        if (nextNode.type === 'eve' && isEvePresent) {
            const eveBase = Math.random() < 0.5 ? '+' : 'x';
            const eveMeasured = (aliceBase === eveBase) ? bit : Math.random() < 0.5 ? 0 : 1;
            
            addMeasurementLog(`🕵️ Eve intercepts Qubit ${index + 1}: measures with ${eveBase} → ${eveMeasured}`, "eve");
            
            // Change qubit appearance to show Eve's interference
            qubit.style.background = 'linear-gradient(45deg, #ef4444, #fb923c)';
            qubit.textContent = `${eveMeasured}${eveBase}`;
        } else if (nextNode.type === 'passive_eve') {
            addMeasurementLog(`👁️ Passive Eve observes Qubit ${index + 1}`, "eve");
        }
        
        // Animate to next node
        qubit.style.transition = 'all 0.8s ease-in-out';
        qubit.style.left = (nextRect.left + nextRect.width / 2 - 25) + 'px';
        qubit.style.top = (nextRect.top + nextRect.height / 2 - 25) + 'px';
        
        currentRouteIndex++;
        setTimeout(animateToNextNode, 900);
    }
    
    setTimeout(animateToNextNode, 200);
}

// ================== BLOCH SPHERE VISUALIZATION ==================

class BlochSphere {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.canvas = document.createElement('canvas');
        this.ctx = null;
        this.labelElement = null;
        this.currentVector = { x: 0, y: 0, z: 1 }; // Start at |0⟩
        this.targetVector = { x: 0, y: 0, z: 1 };
        this.animationProgress = 1;
        this.label = '|0⟩';
        this.rotationY = 0.3;
        this.rotationX = 0.2;
        // horizontal offset applied to rendered state (negative moves left)
        // allow override via options; default moderate left offset to avoid clipping
        this.stateOffsetX = (typeof options.stateOffsetX !== 'undefined') ? options.stateOffsetX : -0.24;

        this.setupCanvas();
        this.resizeToContainer();
        this.render();
        this.startAutoRotation();
    }

    setupCanvas() {
        if (!this.container) return;
        this.container.innerHTML = '';
        this.canvas.width = 300;
        this.canvas.height = 300;
        // brighter, larger canvas with subtle glow to improve visibility
        this.canvas.style.cssText = 'border-radius: 10px; background: radial-gradient(120px 60px at 30% 20%, rgba(255,75,75,0.02), rgba(0,0,0,0.18)); display:block; margin:0 auto; box-shadow: 0 8px 28px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.02);';
        this.container.appendChild(this.canvas);
        this.ctx = this.canvas.getContext('2d');
        
        // Add controls
        const controlDiv = document.createElement('div');
        controlDiv.style.cssText = 'margin-top: 10px; text-align: center; font-size: 13px;';
        const labelEl = document.createElement('div');
        labelEl.id = 'blochLabel';
        labelEl.style.cssText = 'color: var(--accent1); font-weight: 700; font-size:14px; margin-bottom: 6px; text-shadow: 0 1px 0 rgba(0,0,0,0.6);';
        labelEl.textContent = this.label;
        controlDiv.appendChild(labelEl);
        const subtitle = document.createElement('div');
        subtitle.style.cssText = 'color: var(--muted); opacity: 0.95; font-size:12px;';
        controlDiv.appendChild(subtitle);
        this.container.appendChild(controlDiv);

        this.labelElement = labelEl;
    }
    
    // Resize canvas to fit the container element
    resizeToContainer() {
        if (!this.container || !this.canvas) return;
        const rect = this.container.getBoundingClientRect();
        // reserve a bit less space for controls so the canvas can be larger
        const reserved = 40;
        const targetWidth = Math.max(240, Math.floor(rect.width - 12));
        const targetHeight = Math.max(220, Math.floor(rect.height - reserved));
        // account for device pixel ratio for crisp canvas
        const ratio = window.devicePixelRatio || 1;
        this.canvas.width = Math.floor(targetWidth * ratio);
        this.canvas.height = Math.floor(targetHeight * ratio);
        this.canvas.style.width = targetWidth + 'px';
        this.canvas.style.height = targetHeight + 'px';
        this.ctx = this.canvas.getContext('2d');
        // redraw after resize
        this.render();
    }

    // Map BB84 basis and bit to Bloch vector
    mapBasisBitToVector(basis, bit) {
        const numericBasis = typeof basis === 'number' ? basis : (basis === '+' ? 0 : 1);
        
        if (numericBasis === 0) { // Z-basis (+ basis)
            return bit === 0 ? 
                { x: 0, y: 0, z: 1, label: '|0⟩' } :   // |0⟩ state
                { x: 0, y: 0, z: -1, label: '|1⟩' };   // |1⟩ state
        } else { // X-basis (x basis)
            return bit === 0 ? 
                { x: 1, y: 0, z: 0, label: '|+⟩' } :   // |+⟩ state
                { x: -1, y: 0, z: 0, label: '|-⟩' };   // |-⟩ state
        }
    }
    
    // Animate to a new quantum state
    animateToVector(targetState, duration = 500) {
        this.targetVector = { x: targetState.x, y: targetState.y, z: targetState.z };
        this.label = targetState.label;
        this.animationProgress = 0;
        
        const startTime = Date.now();
        const startVector = { ...this.currentVector };
        
        const animate = () => {
            const elapsed = Date.now() - startTime;
            this.animationProgress = Math.min(elapsed / duration, 1);
            
            // Smooth interpolation with easing
            const t = this.easeInOutCubic(this.animationProgress);
            
            this.currentVector.x = startVector.x + (this.targetVector.x - startVector.x) * t;
            this.currentVector.y = startVector.y + (this.targetVector.y - startVector.y) * t;
            this.currentVector.z = startVector.z + (this.targetVector.z - startVector.z) * t;
            
            this.render();
            
            if (this.animationProgress < 1) {
                requestAnimationFrame(animate);
            } else {
                this.labelElement.textContent = this.label;
            }
        };
        
        requestAnimationFrame(animate);
    }
    
    easeInOutCubic(t) {
        return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }
    
    startAutoRotation() {
        let lastTime = Date.now();
        
        const rotate = () => {
            const currentTime = Date.now();
            const deltaTime = currentTime - lastTime;
            lastTime = currentTime;
            
            // Slow auto-rotation for better 3D visualization
            this.rotationY += deltaTime * 0.0002;
            this.render();
            
            requestAnimationFrame(rotate);
        };
        
        requestAnimationFrame(rotate);
    }
    
    render() {
        if (!this.ctx) return;
        const ctx = this.ctx;
        const width = this.canvas.width;
        const height = this.canvas.height;
        // when using devicePixelRatio scaling, adjust center/radius accordingly
        const ratio = window.devicePixelRatio || 1;
        // Add right-side breathing room so the rendered sphere and state labels don't get clipped
        // No extra horizontal padding when using full-width Bloch sphere so it can maximize available space
        const horizontalPadding = Math.max(8, Math.floor(width * 0.12));
        const centerX = width / 2 - horizontalPadding; // shift center left
        const centerY = height / 2;
        // slightly reduce radius so vector arrow and label stay inside canvas
        const radius = Math.min((width - horizontalPadding * 2), height) * 0.32; // scale sphere to available canvas

        // Clear canvas
        ctx.clearRect(0, 0, width, height);

        // Convert rotation and projection to work with high-DPI canvas
        const cosY = Math.cos(this.rotationY);
        const sinY = Math.sin(this.rotationY);
        const cosX = Math.cos(this.rotationX);
        const sinX = Math.sin(this.rotationX);

        const project = (x, y, z) => {
            const x1 = x * cosY - z * sinY;
            const z1 = x * sinY + z * cosY;
            const y2 = y * cosX - z1 * sinX;
            const z2 = y * sinX + z1 * cosX;
            return {
                x: centerX + x1 * radius,
                y: centerY - y2 * radius,
                z: z2
            };
        };

        // Draw sphere wireframe with a neutral color that contrasts on dark background
        ctx.strokeStyle = 'rgba(255,75,75,0.06)';
        ctx.lineWidth = Math.max(1.2, 1.6 * ratio);
        for (let i = 0; i < 8; i++) {
            ctx.beginPath();
            const angle = (i * Math.PI) / 4;
            for (let t = 0; t <= Math.PI * 2; t += 0.12) {
                const x = Math.cos(t) * Math.cos(angle);
                const y = Math.cos(t) * Math.sin(angle);
                const z = Math.sin(t);
                const p = project(x, y, z);
                if (t === 0) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y);
            }
            ctx.stroke();
        }

        // Draw axes and state vector using themed colors
        this.drawAxis(project, ctx, centerX, centerY, radius);
        this.drawStateVector(project, ctx, centerX, centerY, radius);
    }

    // enhance axis drawing with brighter colors and glow
    drawAxis(project, ctx, centerX, centerY, radius) {
        // X axis (bright red)
        ctx.save();
        ctx.shadowColor = 'rgba(255,75,75,0.35)';
        ctx.shadowBlur = 12;
        ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--accent1') || '#ff4b4b';
        ctx.lineWidth = Math.max(2, 2 * (window.devicePixelRatio || 1));
        ctx.beginPath();
        const xStart = project(-1.2, 0, 0);
        const xEnd = project(1.2, 0, 0);
        ctx.moveTo(xStart.x, xStart.y);
        ctx.lineTo(xEnd.x, xEnd.y);
        ctx.stroke();
        ctx.restore();

        // Y axis (make more visible and give depth cue)
        ctx.save();
        // subtle bluish glow so it contrasts with wireframe and background
        ctx.shadowColor = 'rgba(120,160,255,0.22)';
        ctx.shadowBlur = 10;
        // pick a brighter color than the default muted so it shows on dark backgrounds
        const yColor = getComputedStyle(document.documentElement).getPropertyValue('--muted') || '#94a3b8';
        ctx.strokeStyle = yColor || '#7fb3ff';
        ctx.lineWidth = Math.max(1.8, 1.8 * (window.devicePixelRatio || 1));
        // dashed line gives a depth cue so it's easier to distinguish
        if (typeof ctx.setLineDash === 'function') ctx.setLineDash([6, 4]);
        ctx.beginPath();
        const yStart = project(0, -1.2, 0);
        const yEnd = project(0, 1.2, 0);
        ctx.moveTo(yStart.x, yStart.y);
        ctx.lineTo(yEnd.x, yEnd.y);
        ctx.stroke();
        // draw small end caps for visibility
        ctx.setLineDash([]);
        ctx.fillStyle = ctx.strokeStyle;
        ctx.beginPath(); ctx.arc(yStart.x, yStart.y, Math.max(2.2, 2 * (window.devicePixelRatio || 1)), 0, Math.PI * 2); ctx.fill();
        ctx.beginPath(); ctx.arc(yEnd.x, yEnd.y, Math.max(2.2, 2 * (window.devicePixelRatio || 1)), 0, Math.PI * 2); ctx.fill();
        ctx.restore();

        // Z axis (darker red with subtle glow)
        ctx.save();
        ctx.shadowColor = 'rgba(155,43,43,0.28)';
        ctx.shadowBlur = 8;
        ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--accent2') || '#7f1d1d';
        ctx.lineWidth = Math.max(1.6, 1.8 * (window.devicePixelRatio || 1));
        ctx.beginPath();
        const zStart = project(0, 0, -1.2);
        const zEnd = project(0, 0, 1.2);
        ctx.moveTo(zStart.x, zStart.y);
        ctx.lineTo(zEnd.x, zEnd.y);
        ctx.stroke();
        ctx.restore();

        // Axis labels (bolder) — offset slightly to avoid overlap with endpoints
        ctx.fillStyle = 'rgba(230,246,255,0.95)';
        ctx.font = `${12 * (window.devicePixelRatio || 1)}px Arial`;
        ctx.fillText('X', xEnd.x + 8, xEnd.y + 2);
        ctx.fillText('Y', yEnd.x + 8, yEnd.y + 2);
        ctx.fillText('Z', zEnd.x + 8, zEnd.y + 2);
    }
    
    drawStateVector(project, ctx, centerX, centerY, radius) {
        // Project current vector; apply horizontal offset so state appears more to the left
        const offsetX = this.stateOffsetX || 0;
        const vectorEnd = project(this.currentVector.x + offsetX, this.currentVector.y, this.currentVector.z);
        const vectorStart = project(0, 0, 0);
        
        // Draw glowing vector line
        ctx.save();
        ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--accent2') || '#7f1d1d';
        ctx.lineWidth = Math.max(3, 3 * (window.devicePixelRatio || 1));
        ctx.shadowColor = getComputedStyle(document.documentElement).getPropertyValue('--accent1') || '#ff4b4b';
        ctx.shadowBlur = 16;
        ctx.beginPath();
        ctx.moveTo(vectorStart.x, vectorStart.y);
        ctx.lineTo(vectorEnd.x, vectorEnd.y);
        ctx.stroke();

        // Arrow head
        const angle = Math.atan2(vectorEnd.y - vectorStart.y, vectorEnd.x - vectorStart.x);
        const arrowLength = 10 * (window.devicePixelRatio || 1);
        ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--accent1') || '#ff4b4b';
        ctx.beginPath();
        ctx.moveTo(vectorEnd.x, vectorEnd.y);
        ctx.lineTo(
            vectorEnd.x - arrowLength * Math.cos(angle - Math.PI / 6),
            vectorEnd.y - arrowLength * Math.sin(angle - Math.PI / 6)
        );
        ctx.lineTo(
            vectorEnd.x - arrowLength * Math.cos(angle + Math.PI / 6),
            vectorEnd.y - arrowLength * Math.sin(angle + Math.PI / 6)
        );
        ctx.closePath();
        ctx.fill();
        ctx.restore();

        // State point (bigger)
        ctx.beginPath();
        ctx.arc(vectorEnd.x, vectorEnd.y, Math.max(4, 4 * (window.devicePixelRatio || 1)), 0, Math.PI * 2);
        ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--accent1') || '#ff4b4b';
        ctx.fill();
    }

    // Replace or add the function that converts a 3D state to screen coords / draws the vector.
    // If your implementation already draws directly in `render()` or `draw()`, apply the same offset there.
    _projectAndDrawState(vec3) {
        // ...existing code that sets up center/scale/radius ...
        const cx = this.cx;
        const cy = this.cy;
        const r = this.radius * (this.scale || 1);

        // apply horizontal offset so the state appears moved to the left
        const x3 = (vec3.x || 0) + this.stateOffsetX;
        const y3 = (vec3.y || 0);
        const z3 = (vec3.z || 0);

        // simple orthographic-style projection used by the existing renderer
        const sx = cx + x3 * r;
        const sy = cy - y3 * r;

        // ...existing drawing code to render the vector/point using sx, sy ...
        // e.g. draw line from center to (sx,sy) and draw end-cap
        const ctx = this.ctx;
        ctx.save();
        ctx.lineWidth = 3;
        ctx.strokeStyle = this.vectorColor || 'rgba(255,80,80,0.95)';
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(sx, sy);
        ctx.stroke();

        ctx.fillStyle = this.vectorColor || 'rgba(255,80,80,0.95)';
        ctx.beginPath();
        ctx.arc(sx, sy, Math.max(4, Math.round(r * 0.04)), 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
    }
}

// Global Bloch sphere instance
let blochSphere = null;

// Initialize Bloch sphere when side panel is created
function initializeBlochSphere() {
    if (!document.getElementById('blochSphere')) return;
    if (!blochSphere) {
        // pass a small left offset so the state is visible but not clipped
        blochSphere = new BlochSphere('blochSphere', { stateOffsetX: -0.06 });
        window.blochSphere = blochSphere; // For debugging
    } else {
        // already exists — ensure it fits the container
        if (typeof blochSphere.resizeToContainer === 'function') blochSphere.resizeToContainer();
        blochSphere.render();
    }
}
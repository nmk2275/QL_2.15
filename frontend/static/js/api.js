// frontend/static/js/api.js
// Helper functions for calling  experiment endpoints

const _URL = ""; // Set to "" for same-origin, or override as needed

async function runExp1(data) {
    const res = await fetch(`${_URL}/run/exp1`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    });
    return res.json();
}

async function runExp2(data) {
    const res = await fetch(`${_URL}/run/exp2`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    });
    return res.json();
}

async function runExp3(data) {
    const res = await fetch(`${_URL}/run/exp3`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    });
    return res.json();
}

async function runExp4(data) {
    const res = await fetch(`${_URL}/run/exp4`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    });
    return res.json();
}

// Export functions if using modules
// export { runExp1, runExp2, runExp3, runExp4, _URL };

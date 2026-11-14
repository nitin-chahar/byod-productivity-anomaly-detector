// API Base
const isLocalStatic = window.location.protocol === "file:" || 
    ((window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") && window.location.port !== "5000");

const API_BASE = isLocalStatic ? "http://127.0.0.1:5000" : "";

let activeFilter = "all";
let cachedLogs = [];
let cachedAnomalies = [];

// Elements
const logForm = document.getElementById("logForm");
const submitBtn = document.getElementById("submitBtn");
const btnText = document.getElementById("btnText");
const btnSpinner = document.getElementById("btnSpinner");
const responseBox = document.getElementById("responseMessage");

const kpiTotalVisits = document.getElementById("kpiTotalVisits");
const kpiProductivityRatio = document.getElementById("kpiProductivityRatio");
const productivityRing = document.getElementById("productivityRing");
const alertRing = document.getElementById("alertRing");
const kpiTotalAlerts = document.getElementById("kpiTotalAlerts");
const logsTableBody = document.getElementById("logsTableBody");
const logsCountText = document.getElementById("logsCountText");

const btnQuickSimulate = document.getElementById("btnQuickSimulate");
const btnRefreshLogs = document.getElementById("btnRefreshLogs");
const toastContainer = document.getElementById("toastContainer");

// Theme Toggle
const themeToggle = document.getElementById("themeToggle");
const themeIcon = document.getElementById("themeIcon");

function initTheme() {
    const saved = localStorage.getItem("byod_theme") || "dark";
    document.documentElement.setAttribute("data-theme", saved);
    themeIcon.textContent = saved === "dark" ? "☀️" : "🌙";
}

themeToggle.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme") || "dark";
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("byod_theme", next);
    themeIcon.textContent = next === "dark" ? "☀️" : "🌙";
});

// Escape values before putting them in innerHTML
function esc(v) {
    return String(v ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// Toast
function showToast(message) {
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 250);
    }, 3500);
}

// Data Fetching
async function fetchStats() {
    try {
        const res = await fetch(`${API_BASE}/api/stats`);
        if (!res.ok) return;
        const stats = await res.json();

        kpiTotalVisits.textContent = stats.total_visits;
        kpiTotalAlerts.textContent = stats.alerts_triggered;

        const total = stats.productive_count + stats.non_productive_count;
        const ratio = total > 0 ? Math.round((stats.productive_count / total) * 100) : 0;
        kpiProductivityRatio.textContent = `${ratio}%`;
        productivityRing.style.setProperty("--p", ratio);
        const alertPct = stats.total_visits > 0 ? Math.min(100, Math.round((stats.alerts_triggered / stats.total_visits) * 100)) : 0;
        alertRing.style.setProperty("--p", alertPct);
    } catch (e) {
        // silent fail for telemetry
    }
}

async function fetchLogs() {
    try {
        const res = await fetch(`${API_BASE}/api/logs?limit=40`);
        if (!res.ok) return;
        const data = await res.json();
        cachedLogs = data.logs || [];
        renderTable();
    } catch (e) {}
}

async function fetchAnomalies() {
    try {
        const res = await fetch(`${API_BASE}/api/anomalies`);
        if (!res.ok) return;
        const data = await res.json();
        cachedAnomalies = data.anomalies || [];
    } catch (e) {}
}

function renderTable() {
    if (activeFilter === "anomalies") {
        renderAnomalies();
        return;
    }

    let filtered = cachedLogs;
    if (activeFilter === "alerts") {
        filtered = cachedLogs.filter(l => l.alert === "YES");
    } else if (activeFilter === "productive") {
        filtered = cachedLogs.filter(l => l.category === "Productive");
    }

    logsCountText.textContent = `${filtered.length} entries`;

    if (!filtered.length) {
        logsTableBody.innerHTML = `<tr><td colspan="5" class="table-empty">No activity logs recorded.</td></tr>`;
        return;
    }

    logsTableBody.innerHTML = filtered.map(row => {
        const isProd = row.category === "Productive";
        const hasAlert = row.alert === "YES";
        const cleanUrl = row.url ? esc(row.url.replace(/^https?:\/\//, '')) : 'N/A';
        const safeUrl = esc(row.url);

        return `
            <tr>
                <td><span class="user-badge">#${row.user_id || '?'}</span></td>
                <td class="url-cell" title="${safeUrl}">
                    <a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${cleanUrl}</a>
                </td>
                <td>
                    <span class="tag ${isProd ? 'tag-prod' : 'tag-danger'}">
                        ${row.category || 'Unknown'}
                    </span>
                </td>
                <td>
                    ${row.time_spent || 0}s
                    ${hasAlert ? `<span style="font-size:11px;color:var(--danger)"> (+${row.excess_time}s)</span>` : ''}
                </td>
                <td>
                    ${hasAlert ? `<span class="badge-alert">ALERT</span>` : `<span class="badge-normal">OK</span>`}
                </td>
            </tr>
        `;
    }).join("");
}

function renderAnomalies() {
    logsCountText.textContent = `${cachedAnomalies.length} anomaly records`;

    if (!cachedAnomalies.length) {
        logsTableBody.innerHTML = `<tr><td colspan="5" class="table-empty">No anomaly records found.</td></tr>`;
        return;
    }

    logsTableBody.innerHTML = cachedAnomalies.map(row => {
        const isAnomaly = String(row.Anomaly) === "1" || String(row.Z_Anomaly) === "1";
        return `
            <tr>
                <td><span class="user-badge">#${row.User_Id || '?'}</span></td>
                <td>${esc(row.E_mail || 'N/A')}</td>
                <td>Switches: ${row.Switches || 0}</td>
                <td>${row.Session_Duration || 0}s</td>
                <td>
                    ${isAnomaly ? `<span class="badge-alert">ANOMALY</span>` : `<span class="badge-normal">STABLE</span>`}
                </td>
            </tr>
        `;
    }).join("");
}

// Preset chips
document.querySelectorAll(".preset-chip").forEach(chip => {
    chip.addEventListener("click", () => {
        document.getElementById("user_id").value = chip.dataset.user;
        document.getElementById("url").value = chip.dataset.url;
        document.getElementById("time_spent").value = chip.dataset.time;
        document.getElementById("email").value = chip.dataset.email;
        showToast("Preset loaded");
    });
});

// Form submit
logForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    responseBox.style.display = "none";
    submitBtn.disabled = true;
    btnText.textContent = "Processing...";
    btnSpinner.style.display = "inline-block";

    const userId = parseInt(document.getElementById("user_id").value, 10);
    const url = document.getElementById("url").value.trim();
    const timeSpent = parseInt(document.getElementById("time_spent").value, 10);
    const email = document.getElementById("email").value.trim();

    try {
        const res = await fetch(`${API_BASE}/log-visit`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: userId, url, time_spent: timeSpent, email })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "HTTP " + res.status);

        const details = data.data || {};
        const isProd = details.category === "Productive";
        const hasAlert = details.alert === "YES";

        responseBox.innerHTML = `
            <strong>${details.category}</strong> &bull; 
            ${hasAlert ? `<span style="color:var(--danger)">Alert: Exceeded limit (+${details.excess_time}s)</span>` : 'Normal duration'}
        `;
        responseBox.style.background = isProd ? "var(--success-subtle)" : "var(--danger-subtle)";
        responseBox.style.color = isProd ? "var(--success)" : "var(--danger)";
        responseBox.style.display = "block";

        showToast(hasAlert ? "Visit logged with policy alert" : "Visit logged");

        await Promise.all([fetchStats(), fetchLogs(), fetchAnomalies()]);
    } catch (err) {
        responseBox.textContent = `Error: ${err.message}`;
        responseBox.style.background = "var(--danger-subtle)";
        responseBox.style.color = "var(--danger)";
        responseBox.style.display = "block";
    } finally {
        submitBtn.disabled = false;
        btnText.textContent = "Log Visit";
        btnSpinner.style.display = "none";
    }
});

// Tabs
document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        activeFilter = btn.dataset.filter;
        renderTable();
    });
});

btnRefreshLogs.addEventListener("click", async () => {
    await Promise.all([fetchStats(), fetchLogs(), fetchAnomalies()]);
    showToast("Refreshed");
});

const btnClearLogs = document.getElementById("btnClearLogs");
if (btnClearLogs) {
    btnClearLogs.addEventListener("click", async () => {
        if (!confirm("Are you sure you want to clear all activity logs?")) return;
        try {
            const res = await fetch(`${API_BASE}/api/clear-logs`, { method: "POST" });
            const data = await res.json();
            showToast(data.message || "All activity logs cleared");
            await Promise.all([fetchStats(), fetchLogs(), fetchAnomalies()]);
        } catch (e) {
            showToast("Failed to clear logs");
        }
    });
}

btnQuickSimulate.addEventListener("click", async () => {
    try {
        const res = await fetch(`${API_BASE}/api/simulate`, { method: "POST" });
        await Promise.all([fetchStats(), fetchLogs(), fetchAnomalies()]);
        showToast("Simulation visits added");
    } catch (e) {
        showToast("Simulation failed");
    }
});

// Init
initTheme();
fetchStats();
fetchLogs();
fetchAnomalies();
setInterval(() => {
    fetchStats();
    if (activeFilter === "anomalies") fetchAnomalies();
    else fetchLogs();
}, 5000);
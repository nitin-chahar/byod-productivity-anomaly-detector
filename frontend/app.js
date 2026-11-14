/**
 * BYOD Sentinel - Production Dashboard Application
 * Handles live telemetry, activity ingestion, asynchronous alerts,
 * and real-time anomaly log visualizers.
 */

// Dynamic API Endpoint Resolver
const isLocalStatic = window.location.protocol === "file:" || 
    ((window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") && window.location.port !== "5000");

const API_BASE = isLocalStatic ? "http://127.0.0.1:5000" : "";

// Application State
let activeFilter = "all";
let cachedLogs = [];
let cachedAnomalies = [];
let isServerOnline = false;

// DOM Elements
const logForm = document.getElementById("logForm");
const submitBtn = document.getElementById("submitBtn");
const btnText = document.getElementById("btnText");
const btnSpinner = document.getElementById("btnSpinner");
const responseBox = document.getElementById("responseMessage");

const apiStatusPill = document.getElementById("apiStatusPill");
const apiStatusText = document.getElementById("apiStatusText");
const smtpStatusPill = document.getElementById("smtpStatusPill");
const smtpStatusText = document.getElementById("smtpStatusText");

const kpiTotalVisits = document.getElementById("kpiTotalVisits");
const kpiProductivityRatio = document.getElementById("kpiProductivityRatio");
const kpiRatioSubtext = document.getElementById("kpiRatioSubtext");
const productivityProgressBar = document.getElementById("productivityProgressBar");
const kpiTotalAlerts = document.getElementById("kpiTotalAlerts");
const kpiPolicyThreshold = document.getElementById("kpiPolicyThreshold");
const logsTableBody = document.getElementById("logsTableBody");
const logsCountText = document.getElementById("logsCountText");

// Email Modal Elements
const emailModal = document.getElementById("emailModal");
const btnOpenTestEmail = document.getElementById("btnOpenTestEmail");
const btnCloseEmailModal = document.getElementById("btnCloseEmailModal");
const btnCancelEmailModal = document.getElementById("btnCancelEmailModal");
const btnExecuteTestEmail = document.getElementById("btnExecuteTestEmail");
const testEmailRecipient = document.getElementById("testEmailRecipient");
const testEmailFeedback = document.getElementById("testEmailFeedback");
const testEmailSpinner = document.getElementById("testEmailSpinner");
const testEmailBtnText = document.getElementById("testEmailBtnText");

const btnQuickSimulate = document.getElementById("btnQuickSimulate");
const btnRefreshLogs = document.getElementById("btnRefreshLogs");
const toastContainer = document.getElementById("toastContainer");

/* ==========================================================================
   Toast Notification Utility
   ========================================================================== */

function showToast(message, type = "success") {
    const toast = document.createElement("div");
    toast.className = `toast ${type === "success" ? "toast-success" : "toast-error"}`;
    const icon = type === "success" ? "✅" : "⚠️";
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(20px)";
        setTimeout(() => toast.remove(), 300);
    }, 4500);
}

/* ==========================================================================
   Data Fetching & Telemetry
   ========================================================================== */

async function checkSystemHealth() {
    try {
        const res = await fetch(`${API_BASE}/health`);
        if (!res.ok) throw new Error("Server status " + res.status);
        const data = await res.json();

        isServerOnline = true;
        apiStatusPill.className = "status-pill online";
        apiStatusText.textContent = "Server Online";

        if (data.smtp_configured) {
            smtpStatusPill.className = "status-pill online";
            smtpStatusText.textContent = `SMTP Ready (${data.sender_email || "Active"})`;
        } else {
            smtpStatusPill.className = "status-pill warning";
            smtpStatusText.textContent = "SMTP Not Configured";
        }

        if (data.alert_threshold_seconds) {
            kpiPolicyThreshold.textContent = `${data.alert_threshold_seconds}s`;
        }
    } catch (err) {
        isServerOnline = false;
        apiStatusPill.className = "status-pill offline";
        apiStatusText.textContent = "Server Offline";
        smtpStatusPill.className = "status-pill offline";
        smtpStatusText.textContent = "SMTP Offline";
    }
}

async function fetchStats() {
    try {
        const res = await fetch(`${API_BASE}/api/stats`);
        if (!res.ok) return;
        const stats = await res.json();

        kpiTotalVisits.textContent = stats.total_visits;
        kpiTotalAlerts.textContent = stats.alerts_triggered;

        const totalClassified = stats.productive_count + stats.non_productive_count;
        const prodPercentage = totalClassified > 0 
            ? Math.round((stats.productive_count / totalClassified) * 100) 
            : 0;

        kpiProductivityRatio.textContent = `${prodPercentage}%`;
        productivityProgressBar.style.width = `${prodPercentage}%`;
        kpiRatioSubtext.textContent = `${stats.productive_count} Productive / ${stats.non_productive_count} Distraction`;
        document.getElementById("kpiVisitsSubtext").textContent = `${totalClassified} sessions evaluated`;
    } catch (err) {
        console.warn("Could not fetch stats:", err);
    }
}

async function fetchLogs() {
    try {
        const res = await fetch(`${API_BASE}/api/logs?limit=40`);
        if (!res.ok) return;
        const data = await res.json();
        cachedLogs = data.logs || [];
        renderTable();
    } catch (err) {
        console.warn("Could not fetch logs:", err);
    }
}

async function fetchAnomalies() {
    try {
        const res = await fetch(`${API_BASE}/api/anomalies`);
        if (!res.ok) return;
        const data = await res.json();
        cachedAnomalies = data.anomalies || [];
    } catch (err) {
        console.warn("Could not fetch anomalies:", err);
    }
}

/* ==========================================================================
   Table Rendering & Filtering
   ========================================================================== */

function renderTable() {
    if (activeFilter === "anomalies") {
        renderAnomaliesTable();
        return;
    }

    let filtered = cachedLogs;
    if (activeFilter === "alerts") {
        filtered = cachedLogs.filter(l => l.alert === "YES");
    } else if (activeFilter === "productive") {
        filtered = cachedLogs.filter(l => l.category === "Productive");
    }

    logsCountText.textContent = `Showing ${filtered.length} of ${cachedLogs.length} entries`;

    if (filtered.length === 0) {
        logsTableBody.innerHTML = `
            <tr>
                <td colspan="5" class="table-empty">
                    ${cachedLogs.length === 0 
                        ? 'No activity logs found. Use the form on the left or click "Run Simulation".' 
                        : 'No entries match the selected filter.'}
                </td>
            </tr>
        `;
        return;
    }

    logsTableBody.innerHTML = filtered.map(row => {
        const isProd = row.category === "Productive";
        const hasAlert = row.alert === "YES";
        const cleanUrl = row.url ? row.url.replace(/^https?:\/\//, '') : 'N/A';

        return `
            <tr>
                <td>
                    <span class="user-badge">#${row.user_id || '?'}</span>
                </td>
                <td class="url-cell" title="${row.url}">
                    <a href="${row.url}" target="_blank" rel="noopener noreferrer">${cleanUrl}</a>
                </td>
                <td>
                    <span class="tag ${isProd ? 'tag-prod' : 'tag-danger'}">
                        ${row.category || 'Unknown'}
                    </span>
                </td>
                <td>
                    <strong style="color: #F8FAFC;">${row.time_spent || 0}s</strong>
                    ${hasAlert ? `<span style="font-size: 11px; color: #F43F5E;"> (+${row.excess_time}s)</span>` : ''}
                </td>
                <td>
                    ${hasAlert 
                        ? `<span class="badge-alert">⚠️ ALERT</span>` 
                        : `<span class="badge-normal">NORMAL</span>`}
                </td>
            </tr>
        `;
    }).join("");
}

function renderAnomaliesTable() {
    logsCountText.textContent = `Showing ${cachedAnomalies.length} anomaly evaluation records`;

    if (cachedAnomalies.length === 0) {
        logsTableBody.innerHTML = `
            <tr>
                <td colspan="5" class="table-empty">
                    No anomaly records generated yet. Ensure <code>python backend/anomaly.py</code> is running.
                </td>
            </tr>
        `;
        return;
    }

    logsTableBody.innerHTML = cachedAnomalies.map(row => {
        const isAnomaly = String(row.Anomaly) === "1" || String(row.Z_Anomaly) === "1";
        return `
            <tr>
                <td><span class="user-badge">#${row.User_Id || '?'}</span></td>
                <td>
                    <span style="font-size: 12px; color: #CBD5E1;">${row.E_mail || 'N/A'}</span>
                </td>
                <td>
                    <span style="font-size: 11px; color: #94A3B8;">Switches: <strong>${row.Switches || 0}</strong></span>
                </td>
                <td>
                    <span style="font-size: 12px; color: #CBD5E1;">${row.Session_Duration || 0}s</span>
                </td>
                <td>
                    ${isAnomaly 
                        ? `<span class="badge-alert">🧠 ANOMALOUS</span>` 
                        : `<span class="badge-normal">STABLE</span>`}
                </td>
            </tr>
        `;
    }).join("");
}

/* ==========================================================================
   Event Listeners: Form Submission & Presets
   ========================================================================== */

// Handle Quick Preset Chips
document.querySelectorAll(".preset-chip").forEach(chip => {
    chip.addEventListener("click", () => {
        document.getElementById("user_id").value = chip.dataset.user;
        document.getElementById("url").value = chip.dataset.url;
        document.getElementById("time_spent").value = chip.dataset.time;
        document.getElementById("email").value = chip.dataset.email;

        // Subtle highlight
        document.getElementById("url").focus();
        showToast(`Loaded preset: ${chip.textContent.trim()}`);
    });
});

// Handle Log Form Submission
logForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    responseBox.style.display = "none";
    submitBtn.disabled = true;
    btnText.textContent = "Classifying & Evaluating...";
    btnSpinner.style.display = "inline-block";

    const userId = parseInt(document.getElementById("user_id").value, 10);
    const url = document.getElementById("url").value.trim();
    const timeSpent = parseInt(document.getElementById("time_spent").value, 10);
    const email = document.getElementById("email").value.trim();

    const requestData = {
        user_id: userId,
        url: url,
        time_spent: timeSpent,
        email: email
    };

    try {
        const response = await fetch(`${API_BASE}/log-visit`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(requestData)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || ("Server HTTP " + response.status));
        }

        const details = data.data || {};
        const isProd = details.category === "Productive";
        const hasAlert = details.alert === "YES";

        let alertNotice = "";
        if (hasAlert) {
            alertNotice = `
                <div style="margin-top: 10px; font-size: 12px; color: #FCA5A5; background: rgba(244, 63, 94, 0.15); padding: 8px 12px; border-radius: 6px; border: 1px solid rgba(244, 63, 94, 0.3);">
                    ⚠️ <strong>Policy Alert Dispatched:</strong> Non-productive duration exceeded threshold by <strong>${details.excess_time}s</strong>. 
                    An alert email has been dispatched to <code>${email}</code>.
                </div>
            `;
        }

        responseBox.innerHTML = `
            <div style="font-weight: 700; color: #F8FAFC; margin-bottom: 6px;">
                ✔ ${data.message || "Visit Logged Successfully!"}
            </div>
            <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px;">
                <span class="tag ${isProd ? 'tag-prod' : 'tag-danger'}">
                    ${details.category}
                </span>
                <span class="${hasAlert ? 'badge-alert' : 'badge-normal'}">
                    ${hasAlert ? `⚠️ EXCEEDED LIMIT (+${details.excess_time}s)` : 'NORMAL DURATION'}
                </span>
            </div>
            ${alertNotice}
        `;

        responseBox.style.backgroundColor = isProd ? "rgba(16, 185, 129, 0.1)" : "rgba(244, 63, 94, 0.1)";
        responseBox.style.border = `1px solid ${isProd ? "rgba(16, 185, 129, 0.3)" : "rgba(244, 63, 94, 0.3)"}`;
        responseBox.style.display = "block";

        showToast(hasAlert ? `Alert Triggered! Email dispatched to ${email}` : `Visit recorded: ${details.category}`);

        // Refresh stats and logs immediately
        await Promise.all([fetchStats(), fetchLogs(), fetchAnomalies()]);

    } catch (err) {
        responseBox.innerHTML = `
            <div style="font-weight: 700; color: #F87171;">Connection Failed</div>
            <div style="margin-top: 4px; font-size: 12px; color: #FECDD3;">
                ${err.message}. Ensure <code>python backend/server.py</code> is running.
            </div>
        `;
        responseBox.style.backgroundColor = "rgba(244, 63, 94, 0.12)";
        responseBox.style.border = "1px solid rgba(244, 63, 94, 0.35)";
        responseBox.style.display = "block";
        showToast("Error connecting to backend", "error");
    } finally {
        submitBtn.disabled = false;
        btnText.textContent = "Log Activity & Run Detection";
        btnSpinner.style.display = "none";
    }
});

// Tab Filters
document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        activeFilter = btn.dataset.filter;
        renderTable();
    });
});

// Refresh Feed Button
btnRefreshLogs.addEventListener("click", async () => {
    btnRefreshLogs.disabled = true;
    btnRefreshLogs.textContent = "Refreshing...";
    await Promise.all([fetchStats(), fetchLogs(), fetchAnomalies()]);
    btnRefreshLogs.disabled = false;
    btnRefreshLogs.textContent = "↻ Refresh Feed";
    showToast("Feed refreshed!");
});

// Quick Simulation Button
btnQuickSimulate.addEventListener("click", async () => {
    btnQuickSimulate.disabled = true;
    btnQuickSimulate.innerHTML = `<span>⚡</span> Simulating...`;
    try {
        const res = await fetch(`${API_BASE}/api/simulate`, { method: "POST" });
        const data = await res.json();
        showToast(data.message || "Simulation visits logged!");
        await Promise.all([fetchStats(), fetchLogs(), fetchAnomalies()]);
    } catch (err) {
        showToast("Simulation failed: " + err.message, "error");
    } finally {
        btnQuickSimulate.disabled = false;
        btnQuickSimulate.innerHTML = `<span>⚡</span> Run Simulation`;
    }
});

/* ==========================================================================
   SMTP Test Email Modal Handlers
   ========================================================================== */

btnOpenTestEmail.addEventListener("click", () => {
    emailModal.style.display = "flex";
    testEmailFeedback.style.display = "none";
});

btnCloseEmailModal.addEventListener("click", () => emailModal.style.display = "none");
btnCancelEmailModal.addEventListener("click", () => emailModal.style.display = "none");
emailModal.addEventListener("click", (e) => {
    if (e.target === emailModal) emailModal.style.display = "none";
});

btnExecuteTestEmail.addEventListener("click", async () => {
    const recipient = testEmailRecipient.value.trim();
    if (!recipient) {
        alert("Please enter a valid recipient email.");
        return;
    }

    btnExecuteTestEmail.disabled = true;
    testEmailBtnText.textContent = "Sending Test...";
    testEmailSpinner.style.display = "inline-block";
    testEmailFeedback.style.display = "none";

    try {
        const res = await fetch(`${API_BASE}/api/test-email`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: recipient })
        });

        const data = await res.json();

        testEmailFeedback.style.display = "block";
        if (data.success) {
            testEmailFeedback.style.background = "rgba(16, 185, 129, 0.15)";
            testEmailFeedback.style.color = "#34D399";
            testEmailFeedback.style.border = "1px solid rgba(16, 185, 129, 0.3)";
            testEmailFeedback.innerHTML = `<strong>✔ Success!</strong> ${data.message}`;
            showToast(`Test email delivered to ${recipient}`);
        } else {
            testEmailFeedback.style.background = "rgba(244, 63, 94, 0.15)";
            testEmailFeedback.style.color = "#FDA4AF";
            testEmailFeedback.style.border = "1px solid rgba(244, 63, 94, 0.3)";
            testEmailFeedback.innerHTML = `<strong>❌ Error:</strong> ${data.message}`;
            showToast("SMTP test failed. Check feedback modal.", "error");
        }
    } catch (err) {
        testEmailFeedback.style.display = "block";
        testEmailFeedback.style.background = "rgba(244, 63, 94, 0.15)";
        testEmailFeedback.style.color = "#FDA4AF";
        testEmailFeedback.style.border = "1px solid rgba(244, 63, 94, 0.3)";
        testEmailFeedback.innerHTML = `<strong>❌ Request Failed:</strong> ${err.message}. Is backend running?`;
    } finally {
        btnExecuteTestEmail.disabled = false;
        testEmailBtnText.textContent = "Send Test Email";
        testEmailSpinner.style.display = "none";
    }
});

/* ==========================================================================
   Initialization & Polling Cycle
   ========================================================================== */

async function initializeApp() {
    await checkSystemHealth();
    await Promise.all([fetchStats(), fetchLogs(), fetchAnomalies()]);

    // Polling every 5 seconds for live telemetry
    setInterval(async () => {
        await checkSystemHealth();
        await fetchStats();
        if (activeFilter !== "anomalies") {
            await fetchLogs();
        } else {
            await fetchAnomalies();
        }
    }, 5000);
}

document.addEventListener("DOMContentLoaded", initializeApp);

document.getElementById("logForm").addEventListener("submit", async function (event) {
    event.preventDefault();

    const responseEl = document.getElementById("responseMessage");
    const submitBtn = document.getElementById("submitBtn");
    const btnText = document.getElementById("btnText");
    const btnSpinner = document.getElementById("btnSpinner");

    responseEl.style.display = "none";
    submitBtn.disabled = true;
    btnText.textContent = "Analyzing & Logging...";
    if (btnSpinner) btnSpinner.style.display = "inline-block";

    const userId = document.getElementById("user_id").value.trim();
    const url = document.getElementById("url").value.trim();
    const timeSpent = document.getElementById("time_spent").value.trim();
    const email = document.getElementById("email").value.trim();

    const requestData = {
        user_id: parseInt(userId, 10),
        url: url,
        time_spent: parseInt(timeSpent, 10),
        email: email
    };

    try {
        const isLocalFileOrDev = window.location.protocol === "file:" ||
            (window.location.hostname === "localhost" && window.location.port !== "5000") ||
            (window.location.hostname === "127.0.0.1" && window.location.port !== "5000");
        const endpoint = isLocalFileOrDev ? "http://127.0.0.1:5000/log-visit" : "/log-visit";

        const response = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(requestData)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || ("Server returned HTTP " + response.status));
        }

        const details = data.data || {};
        const isProductive = details.category === "Productive";
        const hasAlert = details.alert === "YES";

        let html = `
            <div style="font-weight: 600; margin-bottom: 8px;">
                ✔ ${data.message || "Visit logged successfully!"}
            </div>
            <div style="display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; margin-top: 10px;">
                <span style="background: ${isProductive ? 'rgba(16, 185, 129, 0.25)' : 'rgba(239, 68, 68, 0.25)'}; 
                             color: ${isProductive ? '#34D399' : '#F87171'}; 
                             padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 600;">
                    ${details.category || "Unknown"}
                </span>
                <span style="background: ${hasAlert ? 'rgba(245, 158, 11, 0.25)' : 'rgba(59, 130, 246, 0.25)'}; 
                             color: ${hasAlert ? '#FBBF24' : '#60A5FA'}; 
                             padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 600;">
                    ${hasAlert ? `⚠️ Alert: Exceeded (+${details.excess_time}s)` : 'Normal (Within limits)'}
                </span>
            </div>
        `;

        responseEl.innerHTML = html;
        responseEl.style.backgroundColor = "rgba(16, 185, 129, 0.12)";
        responseEl.style.color = "#E2E8F0";
        responseEl.style.border = "1px solid rgba(16, 185, 129, 0.3)";
        responseEl.style.display = "block";

        document.getElementById("logForm").reset();

    } catch (error) {
        console.error("Submission Error:", error);
        responseEl.innerHTML = `
            <div style="font-weight: 600;">Connection Error</div>
            <div style="font-size: 13px; margin-top: 4px; opacity: 0.9;">
                ${error.message}. Ensure backend API server is running on port 5000.
            </div>
        `;
        responseEl.style.backgroundColor = "rgba(239, 68, 68, 0.15)";
        responseEl.style.color = "#FCA5A5";
        responseEl.style.border = "1px solid rgba(239, 68, 68, 0.3)";
        responseEl.style.display = "block";
    } finally {
        submitBtn.disabled = false;
        btnText.textContent = "Log Activity Visit";
        if (btnSpinner) btnSpinner.style.display = "none";
    }
});

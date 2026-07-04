document.getElementById("logForm").addEventListener("submit", function (event) {
    event.preventDefault(); // Prevent default form submission

    const responseEl = document.getElementById("responseMessage");
    responseEl.style.display = "none";

    let user_id = document.getElementById("user_id").value;
    let url = document.getElementById("url").value;
    let time_spent = document.getElementById("time_spent").value;
    let email = document.getElementById("email").value;

    let requestData = {
        user_id: user_id,
        url: url,
        time_spent: time_spent,
        email: email
    };

    fetch("http://127.0.0.1:5000/log-visit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestData)
    })
        .then(response => {
            if (!response.ok) {
                throw new Error("HTTP error " + response.status);
            }
            return response.json();
        })
        .then(data => {
            responseEl.textContent = data.message || "Visit logged successfully!";
            responseEl.style.backgroundColor = "rgba(16, 185, 129, 0.15)";
            responseEl.style.color = "#10B981";
            responseEl.style.border = "1px solid rgba(16, 185, 129, 0.3)";
            responseEl.style.display = "block";
            document.getElementById("logForm").reset();
        })
        .catch(error => {
            console.error("Error:", error);
            responseEl.textContent = "Could not connect to the backend server. Make sure server.py is running!";
            responseEl.style.backgroundColor = "rgba(239, 68, 68, 0.15)";
            responseEl.style.color = "#EF4444";
            responseEl.style.border = "1px solid rgba(239, 68, 68, 0.3)";
            responseEl.style.display = "block";
        });
});

# 🛡️ BYOD Productivity Logger & Real-Time Anomaly Detection System

A machine learning-powered security and productivity monitoring platform designed for educational institutions and enterprise **Bring Your Own Device (BYOD)** environments.

The system automatically logs student browsing sessions, classifies visited websites into **Productive** or **Non-Productive** categories using an NLP pipeline (**TF-IDF + LinearSVC**, 94% accuracy), enforces time-spent limits, detects behavioral anomalies using **Isolation Forest** and **Statistical Z-Scores**, and sends automated **email alerts** via SMTP.

---

## 🌟 Key Features

- **🌐 Automated Web Content Classification**: Scrapes live page meta-descriptions/titles using `BeautifulSoup` or cleans domain URLs via RegEx to classify sites across 16 categories.
- **⚡ Real-Time Threshold Alerts**: Flags visits exceeding **300 seconds (5 minutes)** on non-productive websites.
- **🔍 Dual-Engine Anomaly Detection**:
  - **Isolation Forest**: Unsupervised ML model detecting multi-variable session anomalies (`contamination=0.05`).
  - **Statistical Z-Score**: Identifies rapid task-switching outliers ($Z > 3.0$).
- **👁️ Event-Driven File Observer**: Built with Python `watchdog` to monitor session logs reactively without database polling overhead.
- **📧 Automated Email Security Dispatcher**: Sends TLS-encrypted email notifications to users/administrators when anomalous behavior is detected.
- **🎨 Glassmorphism Web UI**: Modern, dark-mode frontend built with HTML5, CSS3 tokens (Outfit typography), and asynchronous JavaScript (`fetch` API).
- **🔒 Thread-Safe Logging**: Uses `threading.Lock()` to prevent race conditions during concurrent API writes.

---

## 🏗️ System Architecture

```
+------------------+         HTTP POST         +------------------+
|  Frontend UI /   |  -----------------------> |   Flask Server   |
|  Simulated Batch |  (/log-visit @ port 5000) |   (server.py)    |
+------------------+                           +------------------+
                                                        |
                                                        v
                                              +--------------------+
                                              |  logging_handler   |
                                              | (Scraping + Model) |
                                              +--------------------+
                                                        |
                                                        v
                                              +--------------------+
                                              | student_activity   |
                                              |      (.csv)        |
                                              +--------------------+
                                                        |
                                               watchdog listener
                                                        v
                                              +--------------------+
                                              |     anomaly.py     |
                                              | (Isolation Forest  |
                                              |    + Z-score)      |
                                              +--------------------+
                                                        |
                                                        v
                                              +--------------------+
                                              | real_time_anomalies|
                                              |      (.csv)        |
                                              +--------------------+
                                                        |
                                                        v
                                              +--------------------+
                                              |   send_alert.py    |
                                              |    (SMTP Email)    |
                                              +--------------------+
```

---

## 📏 Core Rules & Thresholds

| Parameter | Value | Module / File | Description |
| :--- | :--- | :--- | :--- |
| **Alert Time Limit** | `300 seconds` (5 mins) | `BYOD/backend/logging_handler.py` | Triggers alert (`Alert="YES"`) if time spent on a **Non-Productive** site exceeds 300s. |
| **Switch Duration Baseline** | `120 seconds` (2 mins) | `BYOD/backend/logging_handler.py` | Baseline metric for task-switching analysis. |
| **Isolation Forest Contamination** | `0.05` (5%) | `BYOD/backend/anomaly.py` | Expected anomaly rate in student browsing population. |
| **Z-Score Outlier Threshold** | $Z > 3.0$ | `BYOD/backend/anomaly.py` | Flags users exceeding 3 standard deviations above the mean in category switching frequency. |
| **Productive Class Set** | `{1, 2, 4, 9, 10}` | `BYOD/backend/logging_handler.py` | Class indices corresponding to Educational, Business, News, Tech, and Reference domains. |

---

## 📊 Machine Learning & Evaluation Metrics

- **Classification Model**: `LinearSVC` with `TfidfVectorizer` (scikit-learn pipeline).
- **Dataset Size**: **1,409 websites** across 16 categories (`website_classification.csv`).
- **Train-Test Split**: 80% Training (**1,127 samples**) / 20% Testing (**282 samples**).
- **Performance**:
  - **Accuracy**: **93.97% (~94%)**
  - **Weighted Precision**: **94%**
  - **Weighted Recall**: **94%**
  - **Weighted F1-Score**: **94%**
  - **Confusion Matrix**: Evaluated across a $16 \times 16$ category matrix.

---

## 📂 Project Structure

```
BYOD/
├── README.md                  # Main Git repository documentation
├── website_classification.csv # Training dataset
├── url_list.py                # Sample URL batch script
└── BYOD/
    ├── backend/
    │   ├── anomaly.py             # Watchdog file observer + Isolation Forest & Z-Score engine
    │   ├── byod_notebook.ipynb    # Jupyter notebook for model training, EDA & evaluation
    │   ├── logging_handler.py     # Content scraper, SVM predictor & thread-safe CSV logger
    │   ├── main.py                # Simulation script for batch URL visit logging
    │   ├── real_time_anomalies.csv# Real-time anomaly outputs
    │   ├── requirements.txt       # Python dependencies
    │   ├── send_alert.py          # SMTP email alert dispatcher
    │   ├── server.py              # Flask REST API backend server (/log-visit)
    │   ├── student_activity.csv   # Raw activity logs
    │   ├── svm_stem(3,3).sav      # Serialized LinearSVC + TF-IDF model (pickle)
    │   └── utils.py               # BeautifulSoup HTML scraper & RegEx text cleaner
    └── frontend/
        ├── app.js                 # Async JavaScript fetch handler
        ├── index.html             # Responsive Web UI form
        └── styles.css             # Modern glassmorphism CSS design system
```

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.8+**
- **pip** package manager

### 1. Installation
Clone the repository and install the backend dependencies:

```bash
cd BYOD/BYOD/backend
pip install -r requirements.txt
```

### 2. Start the Backend API Server
Run the Flask server:

```bash
python server.py
```
*The server will start at `http://127.0.0.1:5000`.*

### 3. Launch the Anomaly Detection Observer
In a separate terminal, start the real-time file watcher:

```bash
cd BYOD/BYOD/backend
python anomaly.py
```

### 4. Launch the Frontend UI
Open `BYOD/BYOD/frontend/index.html` in any modern web browser.

---

## 🔌 API Reference

### Log Visit Endpoint

- **URL**: `/log-visit`
- **Method**: `POST`
- **Content-Type**: `application/json`

#### Request Body
```json
{
  "user_id": 101,
  "url": "https://www.youtube.com/wwe",
  "time_spent": 600,
  "email": "student@school.edu"
}
```

#### Success Response (`200 OK`)
```json
{
  "message": "Visit logged successfully!"
}
```

---

## 🛠️ Tech Stack

- **Backend**: Python 3, Flask, Flask-CORS, Watchdog, SMTP
- **Machine Learning & NLP**: Scikit-Learn (LinearSVC, TfidfVectorizer, Isolation Forest), SciPy (Z-score), Pandas, NumPy
- **Web Scraping**: BeautifulSoup4, Requests
- **Frontend**: HTML5, Vanilla CSS3 (Glassmorphism, Outfit font), Vanilla JavaScript (Fetch API)

---

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.

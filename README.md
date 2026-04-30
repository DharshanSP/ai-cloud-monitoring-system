# 🚀 AI Cloud Sentinel - Hybrid AIOps Monitoring Platform

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-Flask-lightgrey.svg)](https://flask.palletsprojects.com/)
[![AI](https://img.shields.io/badge/AI-Gemini%201.5%20Flash-orange.svg)](https://deepmind.google/technologies/gemini/)
[![ML](https://img.shields.io/badge/ML-Isolation%20Forest-green.svg)](https://scikit-learn.org/)

**AI Cloud Sentinel** is a state-of-the-art AIOps monitoring platform designed for real-time system telemetry, intelligent anomaly detection, and automated root-cause analysis. By combining traditional statistical thresholds with Machine Learning (Isolation Forest) and Generative AI (Google Gemini), it provides actionable insights and predictive maintenance for modern cloud infrastructures.

---

## ✨ Key Features

### 🧠 Intelligent Anomaly Detection
*   **Isolation Forest ML:** Identifies complex, multi-dimensional anomalies that traditional rules miss.
*   **Statistical Z-Score Analysis:** Detects sudden spikes in CPU, Memory, Disk, and Network I/O.
*   **Trend Analysis:** Recognizes gradual "slow-burn" issues like memory leaks or process bloat.

### 🤖 AI-Powered Reasoning
*   **Gemini 1.5 Flash Integration:** Automatically analyzes anomaly contexts to provide:
    *   **Root Cause Analysis:** Technical explanation of what triggered the event.
    *   **Fix Suggestions:** Immediate step-by-step resolution actions.
    *   **Prevention Strategies:** Best practices to avoid recurrence.

### 🔮 Predictive Forecasting
*   **Time-to-Incident (TTI):** Uses Linear Regression and EMA (Exponential Moving Averages) to predict when system resources (CPU/Memory) will hit critical thresholds.
*   **Risk Level Assessment:** Categorizes potential failures as Low, Medium, or High risk based on trend slopes.

### 🌐 Multi-Server Architecture
*   **Dynamic Agent Deployment:** Easily add remote servers to your monitoring cluster with a single command.
*   **Real-time Ingestion:** High-frequency metric collection (every 2 seconds) with minimal latency.
*   **Centralized Dashboard:** Monitor your entire fleet from a single, unified interface.

### 🛠 Operational Tools
*   **Live Task Manager:** Real-time process monitoring and sorting by resource consumption.
*   **Smart Alerting:** Integrated with **Resend** for beautiful, data-rich email alerts.
*   **Incident History:** Persistent storage of anomalies in **MongoDB** for long-term auditing.
*   **Load Simulation:** Built-in tools to trigger CPU spikes and memory leaks for testing detection accuracy.

---

## 🚀 Getting Started

### 1. Prerequisites
*   **Python 3.10+**
*   **MongoDB** (Local or Atlas)
*   **API Keys:**
    *   [Google AI Studio](https://aistudio.google.com/) (Gemini API)
    *   [Resend](https://resend.com/) (Email Alerts)

### 2. Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/DharshanSP/ai-cloud-monitoring-system.git
cd ai-cloud-monitoring-system
pip install -r requirements.txt
```

### 3. Configuration

Create a `.env` file in the root directory:

```env
GEMINI_API_KEY=your_gemini_api_key
RESEND_API_KEY=your_resend_api_key
MONGO_URI=your_mongodb_uri
EMAIL_TO=your_alert_recipient@example.com
```

### 4. Running the Platform

Start the main monitoring hub:

```bash
python app.py
```

Access the dashboard at: `http://localhost:5000`

---

## 📡 Connecting Remote Nodes

1.  **Open Dashboard:** Navigate to the main dashboard from any computer on the network.
2.  **Add Server:** Click the **"+ Add Server"** button.
3.  **Run Agent:** Copy the generated command and run it on the target server. 
    *   *Note: The agent is a lightweight script that requires `psutil` and `requests`.*

---

## 🛠 Tech Stack

*   **Backend:** Python, Flask
*   **AI/ML:** Google Gemini 1.5 Flash, Scikit-learn (Isolation Forest)
*   **Monitoring:** Psutil
*   **Database:** MongoDB
*   **Alerting:** Resend API
*   **Frontend:** Vanilla JS, TailwindCSS (for some components), Chart.js (for visualization)

---

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

---
*Built with ❤️ for High-Performance AIOps.*

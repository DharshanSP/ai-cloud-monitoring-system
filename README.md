AI-Based Cloud Monitoring System

## 📌 Overview
This project is a hybrid AI-based cloud monitoring system that automatically monitors system performance, detects anomalies, and provides intelligent explanations using both local machine learning and cloud AI.

---

## 🎯 Problem Statement
Cloud applications generate massive performance logs and metrics that require manual analysis, leading to delayed fault detection and increased downtime. This project addresses the problem by automating monitoring using AI-based anomaly detection and alerting.

---

## ⚙️ Key Features
- 📊 Real-time CPU & Memory Monitoring  
- 🧠 Hybrid AI (Local + Gemini AI)  
- 🤖 AI Explanation for anomalies  
- 🚨 Automated Email Alerts (Resend API)  
- 🎨 Interactive Dashboard with animations  
- 🔁 AI Mode Toggle (Local / Gemini)  
- 📜 Logging system  

---

## 🧠 Technologies Used

| Category | Technology |
|--------|-----------|
| Backend | Flask |
| Monitoring | psutil |
| Local AI | Isolation Forest |
| Cloud AI | Gemini API |
| Alerts | Resend API |
| Frontend | HTML, CSS, Chart.js |

---

## 🧩 System Architecture


System → psutil → Local AI → Gemini AI → Alert → Dashboard


---

## 🔄 Workflow

1. System generates performance data  
2. psutil collects CPU & memory metrics  
3. Local AI detects anomalies  
4. Gemini AI provides explanation  
5. Resend API sends alert  
6. Dashboard displays results  

---

## 🧠 AI Approach

### 🔹 Local AI
- Uses Isolation Forest  
- Detects anomalies based on learned patterns  

### 🔹 Gemini AI
- Provides reasoning and explanation  
- Enhances decision-making  

### 🔹 Hybrid AI
Combines both for:
- Faster detection  
- Better accuracy  
- Intelligent explanation  

---

## 🚀 How to Run

### 1️⃣ Install dependencies

pip install -r requirements.txt


### 2️⃣ Run application

python app.py


### 3️⃣ Open browser

http://localhost:5000


---

## 🔑 Setup Required

Update API keys in `app.py`:

- Gemini API Key  
- Resend API Key  

---

## 🧪 Demo Steps

1. Open dashboard  
2. Click **Generate Load**  
3. Observe:
   - CPU spike  
   - Anomaly detection  
   - AI explanation  
   - Email alert  

---

## 🌍 SDG Alignment
This project aligns with **SDG 9 (Industry, Innovation, and Infrastructure)** by improving system reliability and enabling intelligent automation.

---

## ⚠️ Limitations
- Requires internet for Gemini AI  
- Limited API usage (free tier)  
- Currently monitors a single system  

---

## 🔮 Future Scope
- Docker deployment  
- Cloud hosting (AWS/Render)  
- Multi-server monitoring  
- Database integration (MongoDB)  
- Predictive analytics  

---

## 🏆 Conclusion
This project demonstrates how AI can enhance traditional monitoring systems by adding automation, intelligence, and real-time insights.

---
## 📌 Guide

Mayank Kumar

-- 
## 👨‍💻 Team Members

Dharshan S p

--
Gautam 

--

abhishek

--
abhiram

---


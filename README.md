# 🏦 BankEase AI
### *Banking, but smarter — secure access, faster support, and AI-powered assistance in one place.*

---

## 📌 Overview

BankEase AI is a full-stack smart banking web application built to make daily banking **simpler, safer, and more digital**. Instead of depending on branch visits for every task, users can log in securely, transfer money, chat with an AI assistant, raise support tickets, and schedule manager meetings — all from one platform.

> 💡 Most banking apps handle transactions well, but they fail when a user needs **real help** — loan guidance, dispute resolution, or account issues. BankEase fills that gap.

---

## 🚀 Features at a Glance

🔐 **Secure Login** — OTP sent to registered email, verified before access is granted

💸 **Money Transfer** — PIN-protected transfers with optional camera capture for proof

🤖 **AI Chatbot** — Gemini-powered, replies in your language (Hindi, English, Hinglish)

🎫 **Support & Escalation** — Raise tickets for loans, disputes, KYC, account problems

📅 **Manager Appointment** — User describes issue, manager schedules a meeting from the app

🛡️ Fraud Detection — Flags suspicious transactions based on amount, timing, and behavior

🧑‍💼 **Manager Panel** — User management, fund addition, account freeze, fraud review
---

## 🆚 Why BankEase even when apps already exist?

Most banking apps already exist in the market — but many users still visit branches for loan questions, KYC issues, account problems, and dispute follow-up. BankEase focuses on that missing support layer.

With BankEase, a user can:
1. Raise a support ticket describing any issue (loan, freeze, dispute, account problem)
2. Continue the conversation through ticket messages + share files
3. Get a meeting scheduled by the manager — **no branch visit needed**

> 📉 This kind of digital support flow can help reduce unnecessary branch visits for basic to moderate issues by an estimated **15–20%** — consistent with digital banking industry trends.

---

## 🛠️ Tech Stack

- **Backend** — Python, Flask, Flask-CORS
- **Database** — MySQL
- **AI Integration** — Google Gemini API (`gemini-2.5-flash`)
- **Authentication** — Session-based login, OTP via email, PIN verification
- **Email** — Gmail SMTP
- **Config** — `python-dotenv` (.env file)
- **Frontend** — HTML, CSS, JavaScript
---

## 📁 Project Structure

```bash
BankEase/
├── app.py              ← Main Flask backend (all APIs)
├── index.html          ← Landing page
├── login.html          ← Login + OTP flow
├── dashboard.html      ← User dashboard
├── profile.html        ← Profile management
├── chatbot.html        ← AI Banking Assistant
├── statement.html      ← Transaction history
├── support.html        ← Support tickets + manager chat
├── manager.html        ← Manager admin panel
├── static/
│   ├── transactionphotos/   ← Transfer verification images
│   └── supportuploads/      ← Support ticket attachments
└── .env
```

> 📝 **Why HTML + CSS + JS are kept together per module?**  
> Each page is self-contained — its structure, styling, and interactions stay in one file. This kept development fast, reduced setup complexity, made Flask serving simple, and made each screen easier to debug independently. No build tools, no separate frontend server needed.

---

## 🔄 Application Flow

```text
Register
   ↓
Login → OTP Verification
   ↓
Dashboard
   ├── 💸 Transfer Money (PIN + Camera)
   ├── 📊 View Transactions
   ├── 🤖 Chat with AI Assistant
   ├── 🎫 Raise Support Ticket / Schedule Meeting
   └── 👤 Manage Profile

Manager
   ├── 👥 View All Users
   ├── 🔒 Freeze / Unfreeze Accounts
   ├── ➕ Add Money to Accounts
   ├── 🚨 Review Fraud Alerts
   └── 📅 Schedule + Resolve Support Tickets
```

---

## ⚙️ Setup & Run

```bash
# 1. Install dependencies
pip install flask flask-cors mysql-connector-python python-dotenv google-genai

# 2. Create .env file
SECRET_KEY=your_secret_key
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=bankease
GEMINI_API_KEY=your_gemini_api_key
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password

# 3. Run the app
python app.py
```

App runs at → `http://localhost:5000`

---

## 🎨 Frontend Note

The frontend UI (HTML, CSS, JavaScript) was **prototyped using AI tools** during the design stage. Each module has its own self-contained file combining structure, styles, and logic — this kept all screens consistent and made iteration fast.

All frontend files were then **manually reviewed, customized, and wired** to the Flask backend APIs. The backend logic, authentication, database integration, AI chatbot system, support + meeting flow, and fraud detection were all **written and implemented manually**.

> Using AI to accelerate frontend layout is similar to using a UI library or template — the real engineering is in the backend architecture, API design, and system integration.

---

## 💡 What Makes This Project Strong

- Not just CRUD — real banking flows with multiple security layers
- AI chatbot with **multilingual support** and live UI action triggers
- Support system doubles as a **manager escalation + meeting scheduler**
- Rule-based **fraud detection** with risk scoring
- Role-based access with separate user and manager flows
- Full backend manually built with Flask + MySQL + Gemini API

---

*Built as a final year BSc IT college project — 2026*

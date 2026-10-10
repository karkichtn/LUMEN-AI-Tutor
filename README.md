# LUMEN — Conversational AI Tutor, Authentication & Paid Plus System

A minimal, professional conversational AI tutor and assistant inspired by ChatGPT's dark layout, built with **Python**, **FastAPI**, **SQLite**, and **Google Gemini API**.

[![Live Demo](https://img.shields.io/badge/🚀%20Live%20App-lumen--ai--tutor.onrender.com-00C781?style=for-the-badge&logo=render&logoColor=white)](https://lumen-ai-tutor.onrender.com)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/AI-Google%20Gemini-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)

---

## 🌐 Live Application

- **Live URL**: [https://lumen-ai-tutor.onrender.com](https://lumen-ai-tutor.onrender.com)
- **Localhost**: [http://127.0.0.1:8000](http://127.0.0.1:8000)

> *Note: Hosted live on Render cloud. Free tier services spin down on inactivity and automatically spin back up in ~30–50 seconds on initial visit.*

---

## ✦ Overview & Key Features

1. **ChatGPT-Inspired Conversational Interface**
   - Near-black palette (`#0B0B0B` main area, `#080808` sidebar, `#1C1C1C` composer, `#252525` borders).
   - Fixed left sidebar (260px) with conversations grouped into **Today**, **Yesterday**, **Previous 7 Days**, and **Older**.
   - Clean central empty state: **"Ready when you are."** with concise starter prompts.
   - Pinned bottom composer with multi-line auto-resize, Enter to send, Shift+Enter for new line, Web Speech dictation, and subtle typing indicators.
   - Collapsible **Raw JSON Inspector** drawer for viewing and copying the structured RFC 8259 backend responses.

2. **Real Authentication & User Accounts**
   - Secure PBKDF2-HMAC-SHA256 password hashing (600,000 iterations with random salts).
   - Sign up, Log in, Log out with 30-day persistent session tokens stored in `localStorage`.
   - Multi-tenant isolation: every conversation, message, and payment request belongs strictly to the authenticated user ID.

3. **Persistent SQLite Chat History (`lumen.db`)**
   - Database models for Users, Sessions, Conversations, Messages, Payment Requests, and Usage Logs.
   - Auto-generated conversation titles from first prompt.
   - In-app **Rename** and **Delete** conversation management with confirmation.
   - Full history reload when reopening past conversations.

4. **LUMEN Free vs. LUMEN Plus (₹699 One-Time Lifetime Payment)**
   - **LUMEN Free**: Standard models, 35 messages per 3 hours, 8-turn conversation memory.
   - **LUMEN Plus (₹699)**: Unlimited messaging, 24-turn deep memory, priority model routing, and permanent lifetime entitlement.
   - Rate limits and plan restrictions enforced strictly on the server side.

5. **UPI QR Payment & Manual Admin Verification Flow**
   - Integrates the exact supplied UPI QR image (`frontend/assets/upi_qr.jpg` for Ishani K. / `ishanikarki.9889-1@oksbi`).
   - Clean, scannable QR display with ₹699 amount and clear UPI instructions.
   - User submits transaction reference (UTR) and optional payment screenshot. Status defaults to **Pending Verification**.
   - Protected **Admin Verification Portal** (`admin@lumen.ai`): review requests, view screenshots, and approve/reject with notes. Approval immediately activates permanent Plus access.

6. **Preserved AI Capabilities**
   - Multilingual support (English, Hindi, Hinglish, Spanish, French, etc.).
   - Educational explanations across programming, mathematics, science, and general knowledge.
   - Progressive conversational health survey (one targeted question at a time with clickable options).
   - Immediate emergency medical triage warning for critical symptoms (e.g., chest pain, respiratory distress).

---

## 🏛️ Project Structure

```
tikka2/
├── backend/
│   ├── config.py                 # Application settings, plan limits & credentials
│   ├── main.py                   # FastAPI application with DB lifespan
│   ├── models/                   # Pydantic schemas (Chat, Survey, Conversation)
│   ├── prompts/                  # System prompts for Gemini
│   ├── routes/
│   │   ├── auth.py               # Register, Login, Logout, /me, Profile
│   │   ├── billing.py            # Plan status, UPI payment submission, Admin reviews
│   │   ├── chat.py               # Chat endpoint & conversation CRUD
│   │   └── health.py             # Server health endpoint
│   ├── services/
│   │   ├── conversation_service.py # In-memory session manager
│   │   ├── db_service.py         # SQLite database operations & PBKDF2 hashing
│   │   └── gemini_service.py     # Gemini API integration & model cascade
│   └── utils/
│       └── json_repair.py        # Robust JSON parser for LLM responses
├── frontend/
│   ├── assets/
│   │   └── upi_qr.jpg            # Exact UPI QR code image asset
│   ├── index.html                # ChatGPT-style minimal layout & modals
│   ├── scripts/
│   │   ├── app.js                # Frontend client controller
│   │   └── audio.js              # Tactile UI sound synthesizer
│   └── styles/
│       └── main.css              # Minimal dark theme stylesheet
├── lumen.db                      # Persistent SQLite database
├── uploads/screenshots/          # Stored payment screenshot files
├── .env                          # Local environment variables
├── .env.example                  # Environment configuration template
├── .gitignore                    # Excludes secrets, databases, and uploads
├── Procfile                      # Web process configuration for cloud hosting
├── render.yaml                   # 1-click Render blueprint configuration
├── test_full_system.py           # End-to-end integration test suite
└── test_scenarios.py             # 8 core AI tutor regression tests
```

---

## 🚀 Getting Started

### 1. Installation

Ensure Python 3.10+ is installed:

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy `.env.example` to `.env` and configure your API keys:

```bash
cp .env.example .env
```

Ensure your `.env` contains:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
HOST=127.0.0.1
PORT=8000
ADMIN_EMAIL=admin@lumen.ai
ADMIN_PASSWORD=Admin@Lumen2026!
```

### 3. Running Locally

```bash
python -m backend.main
```

Open your browser and navigate to:
**`http://127.0.0.1:8000`**

---

## ☁️ 1-Click Cloud Deployment

Deploy your own live cloud instance for free on **Render**:

1. Click the button below:
   [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/karkichtn/LUMEN-AI-Tutor)
2. Enter your `GEMINI_API_KEY`.
3. Click **Apply** — your application will be live on an HTTPS domain within minutes.

---

## 🔑 Administrator Access

A default administrator account is automatically provisioned on first launch:

- **Email**: `admin@lumen.ai`
- **Password**: `Admin@Lumen2026!`

To review and approve pending UPI Plus payments:
1. Click **Log In** and enter the administrator credentials.
2. Click the user profile card at the bottom of the sidebar.
3. Select **Admin Verifications** from the popup menu.
4. Review pending UTRs and screenshot attachments.
5. Click **Approve (Grant Plus)** to activate permanent Plus access for the user.

---

## 🧪 Testing

Run the full end-to-end system test suite:
```bash
python test_full_system.py
```

Run the 8 core AI tutor regression scenarios:
```bash
python test_scenarios.py
```

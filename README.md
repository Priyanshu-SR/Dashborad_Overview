# LeadQ — Lead Qualification Dashboard

A real-time analytics dashboard for monitoring WhatsApp-based lead qualification powered by an AI agent. Built with **FastAPI**, **MongoDB**, and **Chart.js**, secured with **Google Sign-In** authentication.

---

## Overview

LeadQ connects to your MongoDB database where an n8n workflow stores WhatsApp conversations and AI-generated lead analysis. The dashboard provides instant visibility into your sales funnel — from template messages sent, to conversations started, to AI-qualified leads ready for follow-up.

### Key Features

- **Real-time funnel visualization** — Track leads from initial outreach through qualification
- **AI analysis insights** — View intent distribution, confidence scores, and qualification rates
- **Click-through stat cards** — Click any metric to drill into the underlying phone numbers
- **Lead detail drawer** — Inspect full chat history, AI summary, signals, and confidence per lead
- **Google Sign-In authentication** — Only authorized emails can access the dashboard
- **Admin user management** — Add or remove authorized users directly from the UI
- **Fully responsive** — Optimized for phones, tablets, desktops, and ultrawide screens
- **Glassmorphism UI** — Animated backgrounds, stagger animations, count-up effects, and glow interactions

---

## Architecture

```
WhatsApp → n8n Workflow → MongoDB ← FastAPI Dashboard
                ↓
        AI Lead Qualification
        (GPT via n8n Agent)
```

| Component | Role |
|-----------|------|
| **WhatsApp Bot** | Receives and sends messages via WhatsApp Business API |
| **n8n Workflow** | Orchestrates message storage, triggers AI analysis on a schedule |
| **MongoDB** | Stores all conversations, templates, and AI analysis output |
| **FastAPI + Dashboard** | Serves the frontend and API, authenticates users, reads from MongoDB |

---

## Project Structure

```
Lead-Qualification-Agent-Dashboard/
├── main.py                     # FastAPI backend (API + auth + middleware)
├── requirements.txt            # Python dependencies
├── AUTH_SETUP.md               # Step-by-step Google OAuth setup guide
├── README.md                   # This file
└── templates/
    ├── dashboard.html          # Main dashboard (single-file HTML/CSS/JS)
    └── login.html              # Google Sign-In page
```

---

## Prerequisites

- **Python 3.10+**
- **MongoDB Atlas** cluster (or any MongoDB instance)
- **Google Cloud** project with OAuth 2.0 credentials
- **n8n** instance running the Lead Qualification Agent workflow

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/your-org/Lead-Qualification-Agent-Dashboard.git
cd Lead-Qualification-Agent-Dashboard
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Dependencies:
- `fastapi` — Web framework
- `uvicorn[standard]` — ASGI server
- `motor` — Async MongoDB driver
- `pymongo[srv]` — MongoDB SRV connection support
- `google-auth` — Google ID token verification
- `PyJWT` — JWT session tokens

### 3. Configure credentials

Open `main.py` and update the config section:

```python
# MongoDB
MONGO_USERNAME = "your_username"
MONGO_PASSWORD = "your_password"
MONGO_CLUSTER  = "cluster0.xxxxx.mongodb.net"
DB_NAME        = "YourDatabase"
COLLECTION     = "customerChats"

# Google OAuth (see AUTH_SETUP.md for detailed steps)
GOOGLE_CLIENT_ID = "your-client-id.apps.googleusercontent.com"

# JWT Secret (any random string — keep it consistent across restarts)
JWT_SECRET = "your-random-secret-string"

# Access control
ALLOWED_EMAILS = ["you@gmail.com"]
ADMIN_EMAILS   = ["you@gmail.com"]
```

Also update the Google Client ID in `templates/login.html`:

```javascript
const GOOGLE_CLIENT_ID = 'your-client-id.apps.googleusercontent.com';
```

### 4. Run the server

```bash
python main.py
```

Open **http://localhost:8000** → Sign in with Google → Dashboard loads.

---

## Authentication

The dashboard uses **Google Sign-In** with a server-side email allowlist.

### How It Works

1. User clicks "Sign in with Google" on the login page
2. Google returns a signed ID token to the browser
3. Browser sends the token to `/api/auth/google`
4. Backend verifies the token with Google's servers
5. Backend checks if the email is in the allowed list
6. If allowed, a JWT session cookie is set (valid for 24 hours)
7. All subsequent requests are authenticated via this cookie

### User Tiers

| Tier | Access | Managed via |
|------|--------|-------------|
| **Config users** | Full dashboard access | `ALLOWED_EMAILS` in `main.py` |
| **Dashboard users** | Full dashboard access | Admin panel in the UI |
| **Admins** | Dashboard + user management | `ADMIN_EMAILS` in `main.py` |

- Config users cannot be removed from the UI (edit `main.py` to remove them)
- Admins can add/remove dashboard users from the "Manage Users" section
- Admin emails are hidden from the user management list for security
- All logins and user changes are logged in the `authLogs` MongoDB collection

For detailed setup instructions, see **[AUTH_SETUP.md](AUTH_SETUP.md)**.

---

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/google` | Verify Google token and create session |
| `POST` | `/api/auth/logout` | Clear session cookie |
| `GET` | `/api/auth/me` | Get current user info |

### Dashboard Data

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/stats` | Overview statistics (totals, distributions) |
| `GET` | `/api/leads` | Paginated lead list with filters |
| `GET` | `/api/lead/{session_id}` | Full detail for a single lead |
| `GET` | `/api/stat-leads/{category}` | Phone numbers for a stat card category |
| `GET` | `/api/export/qualified` | Export all qualified leads as JSON |
| `GET` | `/api/ping` | Health check and MongoDB diagnostics |

### Admin

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/admin/users` | List all authorized users |
| `POST` | `/api/admin/users` | Add a user (`{"email": "..."}`) |
| `DELETE` | `/api/admin/users/{email}` | Remove a user |

### Query Parameters for `/api/leads`

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | int | Page number (default: 1) |
| `limit` | int | Results per page (default: 25, max: 100) |
| `doc_type` | string | Filter: `template`, `chat`, or `analysed` |
| `intent` | string | Filter by intent: `INTERESTED`, `QUERY`, `NOT_INTERESTED`, `JUNK`, `FAILED` |
| `qualified` | string | Filter: `true` or `false` |
| `search` | string | Search by phone/session ID |
| `min_confidence` | float | Minimum confidence score (0–1) |
| `max_confidence` | float | Maximum confidence score (0–1) |
| `sort_by` | string | Sort field (default: `_id`) |
| `sort_dir` | int | Sort direction: `-1` (desc) or `1` (asc) |

---

## MongoDB Schema

The dashboard reads from the `customerChats` collection. Each document represents one lead/session:

```javascript
{
  "_id": ObjectId,
  "sessionId": "919876543210",           // Phone number
  "template": "KW Delhi 6",              // Template campaign name (if sent)
  "messages": [                           // Chat messages array
    {
      "type": "human",                    // or "ai"
      "data": { "content": "..." }
    }
  ],
  "leadAnalysed": true,                   // Set by n8n after AI analysis
  "analysedAt": "2026-02-20T...",
  "output": {                             // AI analysis result
    "summary": ["Asked about price", "Inquired about location"],
    "intent": "INTERESTED",               // INTERESTED | QUERY | NOT_INTERESTED | JUNK | FAILED
    "qualified": true,
    "signals": ["price", "location"],
    "confidence": 0.85                    // 0.0 to 1.0
  }
}
```

### Collections Created by Dashboard

| Collection | Purpose |
|------------|---------|
| `allowedUsers` | Email allowlist for authentication |
| `authLogs` | Audit trail for logins and user management actions |

---

## n8n Workflow

The Lead Qualification Agent workflow (`Lead_Qualification_Agent.json`) runs on a schedule and:

1. **Triggers** every N minutes (configurable)
2. **Fetches** unanalysed documents from MongoDB (chats with messages that haven't been processed)
3. **Extracts** only human messages from the conversation
4. **Filters** out empty or very short chats
5. **Sends** the chat text to an AI agent (GPT) with a structured prompt
6. **Parses** the AI response into structured output (summary, intent, qualified, signals, confidence)
7. **Updates** the MongoDB document with the analysis result

### Qualification Rules

The AI marks a lead as **QUALIFIED** if the user asks about:
- Price, cost, or ROI
- Location or directions
- Site visit or property tour
- Possession date or timeline
- Loan, EMI, or financing

### Intent Tags

| Tag | Meaning |
|-----|---------|
| `INTERESTED` | Actively asking about the property |
| `QUERY` | General questions, not yet committed |
| `NOT_INTERESTED` | Explicitly declined |
| `JUNK` | Spam, greetings only, or irrelevant |
| `FAILED` | AI could not determine intent |

---

## Deployment

### VPS / Production

```bash
# Install dependencies
pip install -r requirements.txt

# Run with uvicorn (production)
uvicorn main:app --host 0.0.0.0 --port 8001 --workers 2

# Or use systemd service
sudo systemctl start dashboard.service
```

Example systemd service file (`/etc/systemd/system/dashboard.service`):

```ini
[Unit]
Description=LeadQ Dashboard
After=network.target

[Service]
User=root
WorkingDirectory=/var/www/Lead-Qualification-Agent-Dashboard
ExecStart=/usr/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-party.target
```

### Important Notes

- Ensure your Google OAuth Client ID has your production domain in **Authorized JavaScript Origins**
- Set a fixed `JWT_SECRET` in production so sessions survive restarts
- The dashboard uses HTTP-only secure cookies — HTTPS is recommended for production
- No `.limit()` is applied to stat queries to ensure accurate counts

---

## Dashboard Sections

### Overview
Six stat cards showing the full funnel: Total Leads → Templates Sent → With Chats → Analysed → Qualified → Not Qualified. Three charts: Intent Distribution (doughnut), Confidence Spread (bar), and Template Campaigns (horizontal bar). Plus a Qualification Funnel showing conversion at each stage.

### All Leads
Paginated table of all leads with filters by type, intent, qualification status, and confidence range. Click any row to open the detail drawer with full chat history and AI analysis.

### Analysis
Deeper analytics with qualification rate doughnut, intent vs. confidence bar chart, signal frequency analysis, and per-lead analysis cards.

### Manage Users (Admin only)
Add or remove authorized email addresses. Config-level users (from `main.py`) are shown with a "Config" badge and cannot be removed from the UI. Dashboard-added users can be removed by any admin.

---

## Responsive Breakpoints

| Screen | Width | Layout |
|--------|-------|--------|
| TV / Ultrawide | >1920px | 6-col stats, 3-col charts, 17px base |
| Desktop | 1280–1920px | 6-col stats, 3-col charts (default) |
| Small Desktop | 1024–1280px | 3-col stats, sidebar visible |
| Tablet | 768–1024px | 3-col stats, hamburger menu |
| Large Phone | 600–768px | 2-col stats, 1-col charts |
| Phone | 480–600px | 2-col stats, compact spacing |
| Small Phone | <480px | 2-col stats, 13px base font |

---

## License

Private / Internal use.

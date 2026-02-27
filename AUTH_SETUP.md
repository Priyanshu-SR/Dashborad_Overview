# Authentication Setup Guide

## Files Overview

```
D:\Dashboard\
├── main.py                    ← Updated with auth (replace your old one)
├── requirements.txt           ← Updated with new dependencies
└── templates\
    ├── dashboard.html         ← Updated with user profile + admin panel
    └── login.html             ← NEW — Google Sign-In page
```

## Step 1: Install New Dependencies

```bash
pip install google-auth PyJWT --break-system-packages
```

## Step 2: Create Google OAuth Client ID

1. Go to **[Google Cloud Console](https://console.cloud.google.com/)**
2. Create a new project (or select existing one)
3. Go to **APIs & Services → Credentials**
4. Click **+ CREATE CREDENTIALS → OAuth 2.0 Client ID**
5. If prompted, configure the **OAuth consent screen** first:
   - Choose "External"
   - App name: "LeadQ Dashboard"
   - Add your email as test user
   - No scopes needed
6. Back in Credentials, create **OAuth 2.0 Client ID**:
   - Application type: **Web application**
   - Name: "LeadQ Dashboard"
   - Authorized JavaScript origins: Add ALL URLs you'll access the dashboard from:
     - `http://localhost:8000`
     - `http://localhost:8001`
     - `https://leadq.co.in`
     - `http://72.62.288.194:8001`
   - Click **CREATE**
7. Copy the **Client ID** (looks like: `123456789-xxxx.apps.googleusercontent.com`)

## Step 3: Update main.py

Open `main.py` and update these values:

```python
# MongoDB (your existing credentials)
MONGO_USERNAME = "dashboardUser"
MONGO_PASSWORD = "your_password"
MONGO_CLUSTER  = "whatsappbot.qn3amlt.mongodb.net"

# Google OAuth
GOOGLE_CLIENT_ID = "YOUR_CLIENT_ID_FROM_STEP_2.apps.googleusercontent.com"

# JWT Secret (any random string, keep it secret)
JWT_SECRET = "some-random-secret-string-change-this"

# Allowed emails
ALLOWED_EMAILS = [
    "your.email@gmail.com",
    "colleague@gmail.com",
]

# Admin emails (subset of allowed — can add/remove users)
ADMIN_EMAILS = [
    "your.email@gmail.com",
]
```

## Step 4: Update login.html

Open `templates/login.html` and replace the placeholder:

Find: `const GOOGLE_CLIENT_ID = '%%GOOGLE_CLIENT_ID%%';`
Replace with your actual client ID:
```javascript
const GOOGLE_CLIENT_ID = 'YOUR_CLIENT_ID_FROM_STEP_2.apps.googleusercontent.com';
```

## Step 5: Run

```bash
python main.py
```

Open `http://localhost:8000` → You'll see the login page → Sign in with Google → Only allowed emails get through.

## How It Works

- **Login flow**: User clicks "Sign in with Google" → Google returns an ID token → Backend verifies it with Google → Checks if email is in the allowed list → Creates a JWT session cookie → Redirects to dashboard
- **Session**: Stored as an HTTP-only cookie, expires in 24 hours
- **Config users** (`ALLOWED_EMAILS`): Always allowed, cannot be removed from the dashboard UI
- **Dashboard users**: Added/removed by admins through the "Manage Users" panel
- **Admins** (`ADMIN_EMAILS`): Can see the "Manage Users" section in the sidebar
- **Auth logs**: All logins and user changes are logged in the `authLogs` MongoDB collection

## MongoDB Collections Created

- `allowedUsers` — email whitelist (config + dashboard-added users)
- `authLogs` — login and user management audit trail

## For VPS Deployment

When deploying to your VPS (leadq.co.in), make sure:
1. The new dependencies are installed: `pip install google-auth PyJWT`
2. The Google OAuth Client ID has `https://leadq.co.in` in authorized JavaScript origins
3. Update both `main.py` and `templates/login.html` with the same Client ID
4. Set `secure=True` stays in the cookie settings (already set — works with HTTPS)

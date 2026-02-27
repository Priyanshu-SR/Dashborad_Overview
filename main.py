"""
Lead Qualification Dashboard - FastAPI Backend
With Google Sign-In authentication and admin user management.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus
from datetime import datetime, timedelta, timezone
import json, traceback
from bson import ObjectId

# ── Auth imports ────────────────────────────────────────
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import jwt  # PyJWT


# ══════════════════════════════════════════════════════════
# CONFIG — UPDATE THESE VALUES
# ══════════════════════════════════════════════════════════

# MongoDB
MONGO_URI = "mongodb+srv://dashboardUser:dashboardUser12345@whatsappbot.qn3amlt.mongodb.net/"
DB_NAME    = "Yamini"
COLLECTION = "customerChats"

# Google OAuth  ← GET THIS FROM Google Cloud Console → Credentials → OAuth 2.0 Client ID
GOOGLE_CLIENT_ID = "143664148202-bn068parcggqumu3stkn00r32fsrom0r.apps.googleusercontent.com"

# JWT Session — set a fixed secret so sessions survive server restarts
JWT_SECRET = "kw-leadq-dashboard-2026-xR9mP4qL7nZ2wK5v"
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

# Allowed emails (baseline — always allowed even if removed from DB)
ALLOWED_EMAILS = [
    "priyanshusr8920@gmail.com",
    "mdo27@kwgroup.in",
    "mm8@kwgroup.in"
    # Add more emails here
]

# Admin emails (can add/remove users from the dashboard)
ADMIN_EMAILS = [
    "priyanshusr8920@gmail.com",
    "mdo27@kwgroup.in",
    "mm8@kwgroup.in"
    # Add more admin emails here
]


# ══════════════════════════════════════════════════════════
# AUTH HELPERS
# ══════════════════════════════════════════════════════════

def create_jwt_token(email: str, name: str, picture: str, is_admin: bool) -> str:
    payload = {
        "email": email,
        "name": name,
        "picture": picture,
        "is_admin": is_admin,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


async def is_email_allowed(db, email: str) -> bool:
    email_lower = email.lower()
    if email_lower in [e.lower() for e in ALLOWED_EMAILS]:
        return True
    coll = db["allowedUsers"]
    doc = await coll.find_one({"email": email_lower})
    return doc is not None


def check_admin(email: str) -> bool:
    return email.lower() in [e.lower() for e in ADMIN_EMAILS]


async def get_current_user(request: Request) -> dict | None:
    token = request.cookies.get("session")
    if not token:
        return None
    return verify_jwt_token(token)


# ══════════════════════════════════════════════════════════
# LIFESPAN
# ══════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app):
    app.state.mongo_client = AsyncIOMotorClient(MONGO_URI)
    app.state.db = app.state.mongo_client[DB_NAME]
    app.state.collection = app.state.db[COLLECTION]

    # Ensure allowedUsers collection with unique email index
    users_coll = app.state.db["allowedUsers"]
    await users_coll.create_index("email", unique=True)

    # Seed config emails into DB
    for email in ALLOWED_EMAILS:
        try:
            await users_coll.update_one(
                {"email": email.lower()},
                {"$setOnInsert": {
                    "email": email.lower(),
                    "addedBy": "config",
                    "addedAt": datetime.now(timezone.utc).isoformat(),
                    "source": "config"
                }},
                upsert=True
            )
        except Exception:
            pass

    print(f"✅ Connected to MongoDB: {DB_NAME}/{COLLECTION}")
    print(f"🔐 Auth: {len(ALLOWED_EMAILS)} config users, admins: {ADMIN_EMAILS}")
    yield
    app.state.mongo_client.close()


app = FastAPI(title="Lead Qualification Dashboard", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth Middleware ──────────────────────────────────────
PUBLIC_PATHS = {"/api/auth/google", "/api/auth/logout", "/login", "/api/health"}

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path

    # Public paths
    if path in PUBLIC_PATHS:
        return await call_next(request)

    # Static assets
    if path.endswith(('.css', '.js', '.ico', '.png', '.svg', '.woff2')):
        return await call_next(request)

    user = await get_current_user(request)

    # Unauthenticated — serve login page for HTML requests
    if user is None:
        if path.startswith("/api/"):
            return JSONResponse({"error": "Not authenticated"}, status_code=401)
        # Serve login page
        login_path = Path(__file__).resolve().parent / "templates" / "login.html"
        if login_path.exists():
            return HTMLResponse(content=login_path.read_text(encoding="utf-8"))
        return HTMLResponse(content="<h1>Login required</h1>", status_code=401)

    # Attach user to request state
    request.state.user = user
    return await call_next(request)


# ══════════════════════════════════════════════════════════
# AUTH ENDPOINTS
# ══════════════════════════════════════════════════════════

@app.post("/api/auth/google")
async def google_login(request: Request):
    try:
        body = await request.json()
        token = body.get("credential")
        if not token:
            raise HTTPException(400, "Missing credential")

        # Verify with Google
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), GOOGLE_CLIENT_ID
        )

        email = idinfo.get("email", "").lower()
        name = idinfo.get("name", "")
        picture = idinfo.get("picture", "")

        # Check allowlist
        allowed = await is_email_allowed(app.state.db, email)
        if not allowed:
            return JSONResponse(
                {"error": "Access denied", "message": f"{email} is not authorized to access this dashboard."},
                status_code=403
            )

        # Create session
        admin = check_admin(email)
        session_token = create_jwt_token(email, name, picture, admin)

        # Log login
        await app.state.db["authLogs"].insert_one({
            "email": email, "name": name, "action": "login",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ip": request.client.host if request.client else "unknown",
        })

        resp = JSONResponse({
            "success": True, "email": email, "name": name,
            "picture": picture, "is_admin": admin,
        })
        resp.set_cookie(
            key="session", value=session_token,
            httponly=True, secure=True, samesite="lax",
            max_age=JWT_EXPIRY_HOURS * 3600, path="/",
        )
        return resp

    except ValueError as e:
        return JSONResponse({"error": "Invalid Google token", "detail": str(e)}, status_code=401)
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"error": "Login failed", "detail": str(e)}, status_code=500)


@app.post("/api/auth/logout")
async def logout():
    resp = JSONResponse({"success": True})
    resp.delete_cookie("session", path="/")
    return resp


@app.get("/api/auth/me")
async def get_me(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")
    return {
        "email": user["email"], "name": user["name"],
        "picture": user["picture"], "is_admin": user.get("is_admin", False),
    }


# ══════════════════════════════════════════════════════════
# ADMIN: USER MANAGEMENT
# ══════════════════════════════════════════════════════════

@app.get("/api/admin/users")
async def list_users(request: Request):
    user = await get_current_user(request)
    if not user or not user.get("is_admin"):
        raise HTTPException(403, "Admin access required")

    coll = app.state.db["allowedUsers"]
    admin_lower = [e.lower() for e in ADMIN_EMAILS]
    users = []
    async for doc in coll.find({}).sort("addedAt", -1):
        # Hide admin emails from the list
        if doc["email"].lower() in admin_lower:
            continue
        users.append({
            "email": doc["email"],
            "addedBy": doc.get("addedBy", "unknown"),
            "addedAt": doc.get("addedAt"),
            "source": doc.get("source", "db"),
            "isConfigUser": doc["email"].lower() in [e.lower() for e in ALLOWED_EMAILS],
        })
    return {"users": users, "total": len(users)}


@app.post("/api/admin/users")
async def add_user(request: Request):
    user = await get_current_user(request)
    if not user or not user.get("is_admin"):
        raise HTTPException(403, "Admin access required")

    body = await request.json()
    email = body.get("email", "").strip().lower()
    if not email or "@" not in email:
        raise HTTPException(400, "Invalid email address")

    coll = app.state.db["allowedUsers"]
    try:
        await coll.insert_one({
            "email": email,
            "addedBy": user["email"],
            "addedAt": datetime.now(timezone.utc).isoformat(),
            "source": "dashboard",
        })
    except Exception:
        raise HTTPException(409, f"{email} is already in the allowed list")

    await app.state.db["authLogs"].insert_one({
        "email": user["email"], "action": "add_user", "targetEmail": email,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return {"success": True, "email": email}


@app.delete("/api/admin/users/{email}")
async def remove_user(email: str, request: Request):
    user = await get_current_user(request)
    if not user or not user.get("is_admin"):
        raise HTTPException(403, "Admin access required")

    email = email.lower()
    if email in [e.lower() for e in ALLOWED_EMAILS]:
        raise HTTPException(400, f"{email} is a config-level user. Remove from ALLOWED_EMAILS in main.py instead.")
    if email == user["email"].lower():
        raise HTTPException(400, "Cannot remove yourself")

    coll = app.state.db["allowedUsers"]
    result = await coll.delete_one({"email": email})
    if result.deleted_count == 0:
        raise HTTPException(404, "User not found")

    await app.state.db["authLogs"].insert_one({
        "email": user["email"], "action": "remove_user", "targetEmail": email,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return {"success": True, "removed": email}


# ══════════════════════════════════════════════════════════
# EXISTING DASHBOARD & API ROUTES
# ══════════════════════════════════════════════════════════

def serialize(doc):
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])
    return doc


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    html_path = Path(__file__).resolve().parent / "templates" / "dashboard.html"
    if not html_path.exists():
        return HTMLResponse(content="<h1>Dashboard not found</h1>", status_code=404)
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/api/ping")
async def ping():
    try:
        coll = app.state.collection
        count = await coll.count_documents({})
        sample = await coll.find_one()
        return {"status": "ok", "database": DB_NAME, "collection": COLLECTION, "documentCount": count, "sampleDocKeys": list(sample.keys()) if sample else []}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/stats")
async def get_stats():
    try:
        coll = app.state.collection
        total = await coll.count_documents({})
        template_only = await coll.count_documents({"template": {"$exists": True}, "messages": {"$exists": False}})
        with_messages = await coll.count_documents({"messages.0": {"$exists": True}})
        analysed = await coll.count_documents({"leadAnalysed": True})
        qualified = await coll.count_documents({"output.qualified": True})
        not_qualified = await coll.count_documents({"output.qualified": False})

        intent_dist = {}
        async for doc in coll.aggregate([
            {"$match": {"output.intent": {"$exists": True}}},
            {"$group": {"_id": "$output.intent", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]):
            intent_dist[doc["_id"]] = doc["count"]

        conf_dist = []
        async for doc in coll.aggregate([
            {"$match": {"output.confidence": {"$exists": True}}},
            {"$bucket": {"groupBy": "$output.confidence", "boundaries": [0, 0.2, 0.4, 0.6, 0.8, 1.01], "default": "other", "output": {"count": {"$sum": 1}}}}
        ]):
            label = f"{doc['_id']:.1f}-{doc['_id'] + 0.2:.1f}" if isinstance(doc["_id"], (int, float)) else "other"
            conf_dist.append({"range": label, "count": doc["count"]})

        tmpl_dist = {}
        async for doc in coll.aggregate([
            {"$match": {"template": {"$exists": True}}},
            {"$group": {"_id": "$template", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]):
            tmpl_dist[doc["_id"]] = doc["count"]

        return {
            "total": total, "templateOnly": template_only, "withMessages": with_messages,
            "analysed": analysed, "qualified": qualified, "notQualified": not_qualified,
            "intentDistribution": intent_dist, "confidenceDistribution": conf_dist,
            "templateDistribution": tmpl_dist,
        }
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}


@app.get("/api/stat-leads/{category}")
async def get_stat_leads(category: str, page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=200), search: Optional[str] = Query(None)):
    coll = app.state.collection
    query = {}
    if category == "template": query = {"template": {"$exists": True}, "messages": {"$exists": False}}
    elif category == "chats": query = {"messages.0": {"$exists": True}}
    elif category == "analysed": query = {"leadAnalysed": True}
    elif category == "qualified": query = {"output.qualified": True}
    elif category == "not_qualified": query = {"output.qualified": False}
    if search: query["sessionId"] = {"$regex": search, "$options": "i"}

    total = await coll.count_documents(query)
    skip = (page - 1) * limit
    cursor = coll.find(query, {"sessionId": 1, "template": 1, "leadAnalysed": 1, "output.intent": 1, "output.qualified": 1, "output.confidence": 1, "messages": {"$slice": 1}, "analysedAt": 1}).sort("_id", -1).skip(skip).limit(limit)

    docs = []
    async for doc in cursor:
        d = serialize(doc)
        has_messages = bool(d.get("messages"))
        is_analysed = d.get("leadAnalysed", False)
        output = d.get("output", {})
        docs.append({"sessionId": d.get("sessionId"), "type": "analysed" if is_analysed else ("chat" if has_messages else "template"), "template": d.get("template"), "intent": output.get("intent"), "qualified": output.get("qualified"), "confidence": output.get("confidence"), "analysedAt": d.get("analysedAt")})

    return {"category": category, "total": total, "page": page, "limit": limit, "totalPages": (total + limit - 1) // limit, "data": json.loads(json.dumps(docs, default=str))}


@app.get("/api/leads")
async def get_leads(page: int = Query(1, ge=1), limit: int = Query(25, ge=1, le=100), doc_type: Optional[str] = Query(None), intent: Optional[str] = Query(None), qualified: Optional[str] = Query(None), search: Optional[str] = Query(None), sort_by: Optional[str] = Query("_id"), sort_dir: Optional[int] = Query(-1), min_confidence: Optional[float] = Query(None), max_confidence: Optional[float] = Query(None)):
    coll = app.state.collection
    query = {}
    if doc_type == "template": query["template"] = {"$exists": True}; query["messages"] = {"$exists": False}
    elif doc_type == "chat": query["messages.0"] = {"$exists": True}; query["leadAnalysed"] = {"$ne": True}
    elif doc_type == "analysed": query["leadAnalysed"] = True
    if intent: query["output.intent"] = intent
    if qualified == "true": query["output.qualified"] = True
    elif qualified == "false": query["output.qualified"] = False
    if search: query["sessionId"] = {"$regex": search, "$options": "i"}
    if min_confidence is not None or max_confidence is not None:
        conf_q = {}
        if min_confidence is not None: conf_q["$gte"] = min_confidence
        if max_confidence is not None: conf_q["$lte"] = max_confidence
        query["output.confidence"] = conf_q
    skip = (page - 1) * limit
    total = await coll.count_documents(query)
    cursor = coll.find(query).sort(sort_by, sort_dir).skip(skip).limit(limit)
    docs = []
    async for doc in cursor: docs.append(serialize(doc))
    return {"total": total, "page": page, "limit": limit, "totalPages": (total + limit - 1) // limit, "data": json.loads(json.dumps(docs, default=str))}


@app.get("/api/lead/{session_id}")
async def get_lead(session_id: str):
    coll = app.state.collection
    cursor = coll.find({"sessionId": session_id})
    docs = []
    async for doc in cursor: docs.append(serialize(doc))
    if not docs: return {"error": "Not found"}
    template_docs, chat_doc, analysis = [], None, None
    for doc in docs:
        if "messages" in doc and doc.get("leadAnalysed"): analysis = doc; chat_doc = doc
        elif "messages" in doc: chat_doc = doc
        elif "template" in doc: template_docs.append(doc)
    return {"sessionId": session_id, "templates": json.loads(json.dumps(template_docs, default=str)), "chat": json.loads(json.dumps(chat_doc, default=str)) if chat_doc else None, "analysis": json.loads(json.dumps(analysis, default=str)) if analysis else None}


@app.get("/api/export/qualified")
async def export_qualified():
    coll = app.state.collection
    cursor = coll.find({"output.qualified": True}).sort("output.confidence", -1)
    docs = []
    async for doc in cursor:
        d = serialize(doc)
        docs.append({"sessionId": d.get("sessionId"), "intent": d.get("output", {}).get("intent"), "confidence": d.get("output", {}).get("confidence"), "summary": d.get("output", {}).get("summary"), "signals": d.get("output", {}).get("signals"), "analysedAt": d.get("analysedAt")})
    return json.loads(json.dumps(docs, default=str))


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    html_path = Path(__file__).resolve().parent / "templates" / "login.html"
    if not html_path.exists():
        return HTMLResponse(content="<h1>Login page not found</h1>", status_code=500)
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)

# LeadQ — Lead Qualification Dashboard

Interactive dashboard for your WhatsApp Bot lead qualification data.

## Quick Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure MongoDB connection
Open `main.py` and update line 10 with your MongoDB connection string:
```python
MONGO_URI = "mongodb+srv://<username>:<password>@<cluster>.mongodb.net/"
```

Also verify the database and collection names match yours:
```python
DB_NAME = "WhatsAppBot"       # Your database name
COLLECTION = "customerChats"  # Your collection name
```

### 3. Run the server
```bash
python main.py
```
Or:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Open the dashboard
Visit **http://localhost:8000** in your browser.

---

## Features

### Overview Page
- **Stats cards**: Total leads, templates sent, chats, analysed, qualified/not qualified
- **Intent distribution** doughnut chart
- **Confidence spread** bar chart (bucketed 0–1)
- **Template campaigns** horizontal bar chart
- **Qualification funnel** (Total → Templates → Chats → Analysed → Qualified)

### All Leads Page
- Paginated table (25 per page) with sorting
- **Filter by type**: Template / Chat / Analysed
- **Filter by intent**: Interested, Query, Not Interested, Junk, Failed
- **Filter by qualification**: Qualified / Not Qualified
- **Search** by phone number (sessionId)
- Click any row to open the **detail drawer**

### Detail Drawer (per lead)
- Shows all templates sent to that phone number
- Full chat conversation with human/AI bubbles
- AI analysis: intent, qualification, confidence, summary, signals

### Analysis Page
- Qualification rate donut chart
- Intent distribution bar chart
- Top qualified leads table with signals and summaries

## API Endpoints

| Endpoint                  | Description                          |
|---------------------------|--------------------------------------|
| `GET /`                   | Dashboard HTML                       |
| `GET /api/stats`          | Overview statistics                  |
| `GET /api/leads`          | Paginated leads list (with filters)  |
| `GET /api/lead/{session}` | Single lead detail (all doc types)   |
| `GET /api/export/qualified` | Export all qualified leads          |

### Query Parameters for `/api/leads`
- `page`, `limit` — Pagination
- `doc_type` — `template` | `chat` | `analysed`
- `intent` — `INTERESTED` | `QUERY` | `NOT_INTERESTED` | `JUNK` | `FAILED`
- `qualified` — `true` | `false`
- `search` — Partial match on sessionId
- `min_confidence`, `max_confidence` — Filter by confidence range

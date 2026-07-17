# Hostel Complaint Management System (HCMS)

Three separable layers — each can be zipped/downloaded and run independently.

```
hcms/
├── frontend/    index.html, style.css, script.js   (plain HTML/CSS/JS)
├── backend/     app.py, requirements.txt           (Flask REST API)
└── database/    schema.sql                         (SQLite schema, auto-loaded by app.py)
```

## 1. Database
`database/schema.sql` defines all tables (users, categories, complaints, complaint_logs,
feedback, notifications). You don't need to run it manually — `backend/app.py` executes
it automatically on first launch and creates `backend/hcms.db`.

## 2. Backend
```bash
cd backend
pip install -r requirements.txt
python app.py
```
Runs on **http://127.0.0.1:5000**. Default admin login: `admin@hcms.com` / `admin123`.

Key endpoints: `/api/register`, `/api/login`, `/api/complaints` (GET/POST),
`/api/complaints/<id>/status` (PUT), `/api/feedback`, `/api/reports/summary`, `/api/staff`.

## 3. Frontend
Just open `frontend/index.html` in a browser (or serve it with any static server).
It talks to the backend at `http://127.0.0.1:5000/api` — edit `API_BASE` at the top of
`script.js` if you deploy the backend elsewhere.

## Roles
- **Student** — registers, submits complaints, tracks their own status, leaves feedback.
- **Admin** — sees all complaints, updates status/assigns, views reports.
- **Staff** — created via `/api/staff`, can be assigned to complaints (extend the frontend
  as needed for a dedicated staff view).

## Notes
- Change `app.secret` / add proper session tokens before any real deployment — this build
  keeps auth simple (password hashing only, no session/JWT layer) to stay easy to read.
- CORS is open (`flask-cors`) for local development; restrict allowed origins in production.

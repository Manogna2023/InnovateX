# 🛡 GigShield AI — Phase 2 Enhanced: Automation & Protection

> **Guidewire DEVTrails 2026** · Team InnovateX  
> *Parametric Income Insurance for India's Gig Economy*

---

## 🆕 What's New in This Enhanced Build

### 1. Separate Worker & Admin Login Portals
- **Portal Selection Screen** — first screen lets you choose your portal
- **Worker Portal** — login/register for delivery partners
- **Admin Portal** — separate secured login page for insurers/administrators
  - Role-validated: non-admin accounts are rejected
  - Visual distinction (blue accent vs amber for workers)

### 2. Multilingual AI Chatbot
- Floating chat assistant powered by Claude AI
- Supports **8 Indian languages**: English, Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali, Marathi
- Context-aware: knows the logged-in worker's name, platform, city, and zone
- Quick-chip shortcuts for common queries
- Appears after login (bottom-right corner)

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run (SQLite auto-created on first run)
uvicorn app.main:app --reload --port 8000

# 3. Open browser
# → http://localhost:8000
```

> `.env` is pre-configured for local SQLite demo — no edits needed.

---

## 🔐 Demo Credentials

| Portal | Role | Phone | Password |
|--------|------|-------|----------|
| Admin Portal | Admin | `0000000000` | `Admin@1234` |
| Admin Portal | Admin | `1111111111` | `Admin@123` |
| Worker Portal | Worker | `9876543210` | `Demo@1234` |
| Worker Portal | Worker | `9876543211` | `Demo@1234` |
| Worker Portal | Worker | `9876543212` | `Demo@1234` |

---

## 📌 Problem Statement

India's platform-based delivery partners (Zomato, Swiggy, Zepto, Amazon, Dunzo) lose **20–30% of monthly income** due to uncontrollable external disruptions — extreme weather, flooding, severe AQI, local curfews, and platform outages. They have **no financial safety net**.

**GigShield AI** is a parametric insurance platform that provides automated, zero-touch income protection with instant UPI payouts triggered by real-world sensor data.

---

## 🏗 Architecture

```
gigshield/
├── app/
│   ├── core/
│   │   ├── config.py          # Pydantic settings (env-driven)
│   │   ├── security.py        # bcrypt + JWT (access + refresh tokens)
│   │   ├── deps.py            # FastAPI dependency injection (RBAC)
│   │   └── limiter.py         # Rate limiting (slowapi)
│   ├── models/
│   │   ├── database.py        # SQLAlchemy engine (SQLite / PostgreSQL)
│   │   └── models.py          # ORM: User, Policy, Claim, Payout, RiskLog, LocationLog
│   ├── routes/
│   │   ├── auth.py            # POST /auth/register, /login, /refresh
│   │   ├── policy.py          # POST /policy/create, GET /policy/{user_id}
│   │   ├── claims.py          # POST /claims/initiate, GET /claims/{user_id}
│   │   ├── monitor.py         # POST /monitor/check-zone
│   │   ├── location.py        # POST /location/update, GET /location/latest
│   │   ├── dashboard.py       # GET /dashboard/worker/{id}, /dashboard/admin
│   │   ├── admin.py           # GET /admin/users, /admin/claims, /admin/analytics
│   │   ├── websocket_routes.py# WS /ws/alerts/{user_id}, /ws/admin/alerts
│   │   ├── health.py          # GET /health
│   │   └── frontend.py        # GET / → serves gigshield_phase2.html
│   ├── schemas/               # Pydantic request/response models
│   ├── services/
│   │   ├── ml_sim.py          # LightGBM premium model + Prophet risk forecast
│   │   ├── fraud_service.py   # GPS check + duplicate gate + velocity + anomaly
│   │   ├── claim_service.py   # Full claim lifecycle (fraud→payout→DB→Razorpay)
│   │   ├── trigger_service.py # Open-Meteo live weather + mock social triggers
│   │   ├── analytics_service.py # Admin KPIs, loss ratio, sparklines
│   │   ├── auth_service.py    # Registration + JWT pair
│   │   ├── scheduler_service.py # Background auto-claim thread (5 min cycle)
│   │   ├── websocket_manager.py # Async WS push to workers and admins
│   │   └── seed.py            # Demo data seeder
│   └── main.py                # FastAPI app factory + lifespan
├── gigshield_phase2.html      # Enhanced single-page frontend (portal select + chatbot)
├── requirements.txt
├── .env                       # Ready-to-use local config
├── .env.example
└── README.md
```

---

## 💡 Weekly Premium Model

| Tier | Base Premium | AI-Adjusted Range | Max Payout | Coverage Hours |
|------|-------------|-------------------|------------|----------------|
| Basic | ₹49/week | ₹34–₹69 | ₹500 | 4 hrs |
| Standard | ₹89/week | ₹62–₹125 | ₹1,200 | 8 hrs |
| Pro | ₹149/week | ₹104–₹209 | ₹2,500 | 12 hrs |

---

## ⚡ Parametric Triggers

| Trigger | Threshold | Data Source |
|---------|-----------|-------------|
| Heavy Rain | > 10 mm/hr | Open-Meteo live hourly |
| Extreme Heat | > 40 °C | Open-Meteo current weather |
| High Wind | > 60 km/h | Open-Meteo current weather |
| Thunderstorm | WMO code ≥ 80 | Open-Meteo weather code |
| Curfew / Platform Outage | Detected | Mock (govt API / webhook simulation) |

---

## 🌐 API Endpoints

```
Auth
  POST  /auth/register          Register a new worker
  POST  /auth/login             Get JWT access + refresh tokens
  POST  /auth/refresh           Refresh access token
  GET   /auth/me                Current user profile

Policy
  POST  /policy/calculate-premium  AI premium preview
  POST  /policy/create             Activate weekly policy
  GET   /policy/{user_id}          Get active policy

Monitor
  POST  /monitor/check-zone        Live disruption check (Open-Meteo + mock)

Claims
  POST  /claims/initiate           File parametric claim
  GET   /claims/{user_id}          Claim history

Location
  POST  /location/update           Push GPS coordinates
  GET   /location/latest/{user_id} Latest GPS ping

Dashboard
  GET   /dashboard/worker/{user_id} Worker KPIs
  GET   /dashboard/admin            Admin analytics

Admin (admin role required)
  GET   /admin/users               All workers
  GET   /admin/claims              All claims
  GET   /admin/analytics           Full KPI analytics

WebSocket
  WS    /ws/alerts/{user_id}       Worker live disruption push
  WS    /ws/admin/alerts           Admin live feed
```

---

## 👥 Team InnovateX

Built for **Guidewire DEVTrails 2026** University Hackathon.

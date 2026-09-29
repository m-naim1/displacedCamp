# 🏕️ Displaced Camp Manager

Full-stack application for managing displaced families and individuals across humanitarian shelter centers — family registration, member tracking, shelter assignments, role-based staff access, family self-service, reports, and an admin dashboard.

> **Status:** Backend API complete · Frontend (SolidJS SPA) in development

---

## 📌 What This Project Does

- **Family registration** with full demographic data, shelter assignments, and residency status
- **Member tracking** per family, including vulnerability flags (disability, injury, pregnancy, chronic illness, breastfeeding)
- **Dual authentication** — staff log in with username/password; families identify themselves using their national ID (Luhn-validated) and date of birth
- **Role-based access control** — SUPERADMIN / MANAGER / BLOCK_HEAD families each see and modify only what they need (block- and shelter-scoped reads)
- **Family update requests** — families propose changes (new member, changed phone, change of head); staff approve or reject
- **Reports** — family and member reports with CSV/JSON export
- **Live dashboard stats** — family/member totals, block occupancy, shelter center breakdowns
- **Admin dashboard** (starlette-admin) plus a SolidJS SPA frontend
- **Soft delete** — families are archived, not permanently erased

---

## 🏗️ Architecture

```
app/
├── api/
│   ├── deps.py             # DI + require_role() auth guards
│   └── v1/
│       ├── router.py
│       └── endpoints/      # auth, families, users, lookups, reports, dashboard
├── core/
│   ├── config.py           # Settings (env-driven)
│   ├── security.py         # JWT signing, bcrypt hashing
│   ├── errors.py           # Custom exception classes
│   └── scoping.py          # Block/shelter scope enforcement
├── db/session.py           # Async engine + session
├── models/                 # SQLAlchemy 2.0 ORM models
├── schemas/                # Pydantic v2 request/response schemas
├── repositories/           # Data-access layer
├── services/               # Business logic (router → service → repository → model)
├── admin.py                # starlette-admin dashboard + auth
├── seed.py                 # Table bootstrap + Gaza seed data + first superadmin
└── main.py                 # FastAPI app, middleware, error handlers
frontend/                   # SolidJS SPA (Vite, TanStack Router/Query, UnoCSS)
alembic/                    # Database migrations
templates/index.html        # Admin dashboard template
tests/                      # pytest suite (43 tests, async)
```

The backend follows a strict **router → service → repository → model** pattern. Endpoints never query the database directly; all business logic lives in the service layer.

---

## ⚙️ Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | FastAPI |
| ORM | SQLAlchemy 2.0 (async, `mapped_column` style) |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Authentication | JWT (`python-jose`) + bcrypt (`passlib`) |
| Admin panel | starlette-admin |
| Database | SQLite (dev, aiosqlite) · PostgreSQL-ready |
| Logging / observability | structlog, Prometheus `/metrics`, correlation IDs |
| Backend runtime | Python 3.14 · uvicorn · uv |
| Frontend | SolidJS · Vite · TanStack Router · TanStack Query · UnoCSS · zod |
| Linting / testing | ruff · pytest (pytest-asyncio) |

---

## 🔐 Authentication & Authorization

Two separate authentication flows by design:

**System staff** (SUPERADMIN, MANAGER, BLOCK_HEAD):
```
POST /api/v1/auth/login
Body: username + password (OAuth2 form)
Returns: JWT Bearer token
```

**Families** authenticate using their existing registration data — no account needed:
```
POST /api/v1/auth/family-login
Body: national_id + date_of_birth
Returns: JWT Bearer token scoped to their family record
```

### Role permission matrix

| Operation | SUPERADMIN | MANAGER | BLOCK_HEAD | FAMILY |
|---|:---:|:---:|:---:|:---:|
| Read families & members | ✅ | ✅ | ✅ (own block only) | ❌ |
| Register / update / archive family | ✅ | ✅ | ❌ | ❌ |
| Add / update / remove members | ✅ | ✅ | ❌ | ❌ |
| Manage system users | ✅ | ❌ | ❌ | ❌ |
| Admin panel (`/admin`) | ✅ | ❌ | ❌ | ❌ |
| View own family record / submit update request | ❌ | ❌ | ❌ | ✅ |

Authorization is enforced via `require_role()` FastAPI dependencies injected at the route level. MANAGER reads are scoped to their shelter center; BLOCK_HEAD reads are scoped to their block (see `app/core/scoping.py`).

---

## 🗂️ Data Model

- **Family** — the core entity: head/spouse, residency status, housing type, shelter quality, phone numbers, original city, current shelter center + block, female-/child-headed flags, soft-delete (`is_active`, `archived_at`).
- **Member** — belongs to a family: name, gender, date of birth, marital status, relationship to head, and vulnerability flags (`disabled`, `injured`, `pregnant`, `breastfeeding`, `has_chronic_disease`). National ID is the PK and is Luhn-validated.
- **FamilyUpdateRequest** — family-submitted change proposals (`ADD_MEMBER`, `CHANGE_HEAD`, `UPDATE_FAMILY_INFO`, `UPDATE_MEMBER_INFO`) with a JSON payload and `PENDING`/`APPROVED`/`REJECTED` status.
- **Lookup tables** — `Governor`, `City`, `ShelterCenter`, `ShelterBlock`, `ShelterQuality`, `RelationshipToHead`.
- **User** — system operators only; carries optional `shelter_id` (MANAGER) / `block_id` (BLOCK_HEAD) scope. Families are never stored here.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)
- Node.js 20+ and npm (frontend only)

### Backend

```bash
git clone https://github.com/m-naim1/displacedCamp
cd displacedCamp

# Create virtual environment and install dependencies
uv sync

# Copy and edit environment config
cp .env.example .env
# - Generate a strong SECRET_KEY:  python -c "import secrets; print(secrets.token_hex(32))"
# - Set ADMIN_USERNAME / ADMIN_PASSWORD / ADMIN_EMAIL (used to create the first superadmin)
# - Pick a database (SQLite default; PostgreSQL-ready)

# Bootstrap the database and seed lookups + superadmin
uv run python -m app.seed

# Run the API server
uv run uvicorn app.main:app --reload
```

| URL | Description |
|---|---|
| http://localhost:8000 | API root |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/redoc | ReDoc |
| http://localhost:8000/admin | starlette-admin dashboard (SUPERADMIN only) |
| http://localhost:8000/health | Health check (DB ping) |
| http://localhost:8000/metrics | Prometheus metrics |

> **Setup, not auto-create:** the API does **not** create an admin on first run. Run `uv run python -m app.seed` (or `uv run alembic upgrade head` for a schema-only setup) and use the credentials from your `ADMIN_USERNAME` / `ADMIN_PASSWORD` env vars. Change them via the API after first login.

### Frontend (SolidJS SPA)

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server runs at http://localhost:5173 and proxies `/api` requests to the backend at `http://localhost:8000`.

### Example: login and make an authenticated request

```bash
# Get a token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=<ADMIN_USERNAME>&password=<ADMIN_PASSWORD>"

# Use the token
curl http://localhost:8000/api/v1/families/ \
  -H "Authorization: Bearer <your_token>"
```

### Environment variables

```env
SECRET_KEY=your-secret-key-here        # Required — signs JWT tokens and admin sessions
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
SQLALCHEMY_DATABASE_URI=sqlite+aiosqlite:///./camp_manager.db   # or postgresql+asyncpg://...
ADMIN_USERNAME=admin                   # First superadmin (used by `python -m app.seed`)
ADMIN_PASSWORD=change-me
ADMIN_EMAIL=admin@example.com
CORS_ORIGINS=["http://localhost:5173"] # Allowed SPA origins (JSON list)
```

---

## 📡 API Endpoints

> All paths under `/api/v1`. "Staff" = SUPERADMIN, MANAGER, BLOCK_HEAD.

### Auth (`/auth`)
| Method | Endpoint | Description | Access |
|---|---|---|---|
| POST | `/auth/login` | Staff login → JWT | Public |
| POST | `/auth/family-login` | Family login by national ID + DOB | Public |
| GET | `/auth/me` | Current user profile | Authenticated |
| POST | `/auth/register` | Create system user | SUPERADMIN |

### Families (`/families`)
| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/families/` | List families (filtering, pagination) | Staff (scoped) |
| POST | `/families/` | Register a new family with members | SUPERADMIN, MANAGER |
| GET | `/families/{id}` | Family details + computed stats | Staff (scoped) |
| PUT | `/families/{id}` | Update family record | SUPERADMIN, MANAGER |
| PATCH | `/families/{id}/archive` | Soft-delete a family | SUPERADMIN, MANAGER |
| PATCH | `/families/{id}/restore` | Restore archived family | SUPERADMIN, MANAGER |
| GET | `/families/me` | Family's own record | FAMILY |
| GET | `/families/members` | List members (filtering, pagination) | Staff (scoped) |
| POST | `/families/{family_id}/members` | Add member to family | SUPERADMIN, MANAGER |
| PUT | `/families/members/{member_id}` | Update member | SUPERADMIN, MANAGER |
| DELETE | `/families/members/{member_id}` | Remove member | SUPERADMIN, MANAGER |

### Update requests (family self-service)
| Method | Endpoint | Description | Access |
|---|---|---|---|
| POST | `/families/me/update-requests` | Propose a change (add member, phone, etc.) | FAMILY |
| GET | `/families/update-requests` | List pending requests | Staff (scoped) |
| PATCH | `/families/{request_id}/approve` | Approve and apply a request | Staff |
| PATCH | `/families/{request_id}/reject` | Reject a request | Staff |

### Users (`/users`)
| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/users/` | List system users | SUPERADMIN |
| GET | `/users/{user_id}` | User details | SUPERADMIN |
| PATCH | `/users/{user_id}` | Update user (role, shelter, block, password) | SUPERADMIN |
| DELETE | `/users/{user_id}` | Deactivate user | SUPERADMIN |

### Lookups (`/lookups`) — governors, cities, shelter-centers, shelter-blocks, shelter-qualities, relationships
| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/lookups/{resource}` | List active entries | Staff + FAMILY (read-only) |
| POST | `/lookups/{resource}` | Create entry | SUPERADMIN |
| PUT | `/lookups/{resource}/{item_id}` | Update entry | SUPERADMIN |
| DELETE | `/lookups/{resource}/{item_id}` | Delete entry | SUPERADMIN |

### Reports (`/reports`)
| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/reports/families` | Family report | SUPERADMIN, MANAGER, BLOCK_HEAD |
| GET | `/reports/families/export` | CSV/JSON export | SUPERADMIN, MANAGER, BLOCK_HEAD |
| GET | `/reports/members` | Member report (+ `special_only` flag) | SUPERADMIN, MANAGER, BLOCK_HEAD |
| GET | `/reports/members/export` | CSV/JSON export | SUPERADMIN, MANAGER, BLOCK_HEAD |

### Dashboard (`/dashboard`)
| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/dashboard/stats` | Family/member totals, block & center occupancy | Staff |

---

## 🛠️ Skills Demonstrated

- **REST API design** — resource-oriented endpoints, correct HTTP methods/status codes, consistent error responses
- **FastAPI** — dependency injection, OAuth2 password bearer, Pydantic v2 schemas, scoped auth dependencies
- **SQLAlchemy 2.0** — typed `Mapped` columns, relationships with `foreign_keys`, soft delete, JSON payloads (JSON/JSONB)
- **Authentication** — JWT HS256, bcrypt hashing, token expiry, two separate auth flows in one API
- **Authorization** — role-based access via `require_role()` factory + MANAGER/BLOCK_HEAD scope guard
- **Validation** — Palestine national ID validation (format + Luhn checksum), startup settings validation
- **Admin dashboard** — starlette-admin with custom `AuthProvider`, overridden dashboard view, live DB statistics
- **Observability** — structured logging (structlog + correlation IDs), Prometheus metrics, health checks
- **Layered architecture** — router → service → repository → model, easily testable
- **Testing** — 43 async pytest tests across services and scoping
- **Frontend** — SolidJS SPA with TanStack Router/Query, bilingual UI (English/Arabic)

---

## 🔮 Roadmap

### API
- [ ] Audit log — track who changed what and when
- [ ] Advanced pagination/search (member name, national ID, phone)
- [ ] PostgreSQL production deployment (migrations lag the models — needs a revision for `family_update_requests` and user scope columns)
- [ ] Rate limiting on auth endpoints
- [ ] `.env` validation on startup

### Frontend
- [ ] Complete family self-service flows
- [ ] Camp map showing block occupancy
- [ ] Full Arabic localization pass

### Infrastructure
- [ ] Docker + docker-compose setup
- [ ] GitHub Actions CI (lint, test, migrate)

---

## 📁 Project Structure

```
displacedCamp/
├── app/
│   ├── main.py
│   ├── admin.py
│   ├── seed.py
│   ├── api/
│   │   ├── deps.py
│   │   └── v1/
│   │       ├── router.py
│   │       └── endpoints/        # auth, families, users, lookups, reports, dashboard
│   ├── core/                     # config, security, errors, scoping
│   ├── db/                       # session.py
│   ├── models/                   # enums, lookups, family, user
│   ├── schemas/                  # family, user, lookups, report, filters, dashboard, update_request
│   ├── repositories/             # data access layer
│   └── services/                 # family, user, lookup, report, update_request
├── frontend/                     # SolidJS SPA
│   └── src/
│       ├── api/                  # client + endpoint definitions
│       ├── auth/                 # auth store
│       ├── components/           # FamilyForm, MemberForm, UI kit
│       ├── i18n/                 # English / Arabic
│       ├── routes/               # staff + family routes (TanStack Router)
│       └── schemas/              # zod schemas
├── alembic/                      # migrations
├── templates/index.html          # admin dashboard template
├── tests/                        # 43 async pytest tests
├── .env.example
├── pyproject.toml
└── README.md
```

---

## 👤 Author

**Mohammed Naim**
Backend Developer · Python · FastAPI · SQLAlchemy

[GitHub](https://github.com/m-naim1)

---

*Built as a portfolio project demonstrating production-grade full-stack development with Python and SolidJS — designed around a real humanitarian need: tracking and supporting displaced families in camp settings.*
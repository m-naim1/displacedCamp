# 🏕️ Displaced Camp Manager

Full-stack application for managing displaced families and individuals across humanitarian shelter centers — family registration, member tracking, shelter assignments, role-based staff access, family self-service, reports, and a SolidJS SPA frontend.

> **Status:** Backend API complete (67 tests passing) · Frontend SolidJS SPA implemented (decoupled REST client — safe to extract to its own repo)

---

## 📌 What This Project Does

- **Family registration** with full demographic data, shelter assignments, and residency status
- **Member tracking** per family, including vulnerability flags (disability, injury, pregnancy, chronic illness, breastfeeding)
- **Dual authentication** — staff log in with username/password; families identify themselves using their national ID (Luhn-validated) and date of birth
- **Role-based access control** — SUPERADMIN / MANAGER / BLOCK_HEAD families each see and modify only what they need (block- and shelter-scoped reads)
- **Family update requests** — families propose changes (new member, changed phone, change of head); staff approve or reject (SUPERADMIN / MANAGER / BLOCK_HEAD, scoped)
- **Reports** — family and member reports with filtering, pagination, and CSV/JSON export
- **XLSX export** — `GET /export/families` and `GET /export/members` workbooks with column selection
- **CSV bulk import** — `POST /families/import` registers many families at once (one row per member, grouped by `family_code`); per-family errors are reported, not fatal
- **Audit log** — append-only `audit_logs` trail of who changed what and when (`GET /audit/`, SUPERADMIN only)
- **Live dashboard stats** — family/member totals, age bands, vulnerability counts, block occupancy, shelter center breakdowns, pending-request count (role-scoped)
- **SolidJS SPA frontend** — role-gated staff pages (dashboard, families, members, reports, lookups, users, audit) plus family self-service
- **Soft delete** — families are archived, not permanently erased

---

## 🏗️ Architecture

```
app/
├── api/
│   ├── deps.py             # DI + require_role() auth guards + service providers
│   └── v1/
│       ├── router.py       # mounts families, auth, users, audit, lookups, reports, export, dashboard
│       └── endpoints/      # auth, families, users, audit, lookups, reports, export, dashboard
├── core/
│   ├── config.py           # Settings (env-driven, .env)
│   ├── security.py         # JWT signing, bcrypt hashing (async via asyncio.to_thread)
│   ├── errors.py           # Custom exception classes
│   └── scoping.py          # Block/shelter scope enforcement
├── db/session.py           # Async engine + session
├── models/                 # SQLAlchemy 2.0 ORM models (incl. AuditLog)
├── schemas/                # Pydantic v2 request/response schemas
├── repositories/           # Data-access layer
├── services/               # Business logic (router → service → repository → model)
│                           # family, user, lookup, report, update_request, audit, export, import
├── seed.py                 # Table bootstrap + Gaza seed data + first superadmin
└── main.py                 # FastAPI app, middleware, error handlers
frontend/                   # Standalone SolidJS SPA (Vite, TanStack Router/Query, UnoCSS)
│                           # talks to the backend only via /api/v1 + JWT — can be moved to its own repo
├── alembic/                # Database migrations (head: 9999_restore_trgm)
├── scripts/                # generate_large_dataset.py (load testing)
└── tests/                  # pytest suite (67 tests, async)
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
| Authentication | JWT (`python-jose`) + `bcrypt` (async, via `asyncio.to_thread`) |
| Rate limiting | `slowapi` (auth endpoints, `AUTH_RATE_LIMIT`, default `10/minute` → 429) |
| XLSX export | `openpyxl` |
| Database | SQLite (dev, aiosqlite) · PostgreSQL-ready (asyncpg, JSONB, pg_trgm) |
| Logging / observability | structlog, Prometheus `/metrics`, correlation IDs |
| Backend runtime | Python 3.14 · uvicorn · uv |
| Frontend | SolidJS · Vite · TanStack Router · TanStack Query · UnoCSS · zod |
| Linting / testing | ruff · pytest (pytest-asyncio) · ty · httpx |

---

## 🔐 Authentication & Authorization

Two separate authentication flows by design:

**System staff** (SUPERADMIN, MANAGER, BLOCK_HEAD):
```
POST /api/v1/auth/login
Body: username + password (OAuth2 form)
Returns: JWT Bearer token
```

**Families** authenticate using their existing registration data — no account needed.
Only the **head of family** can log in (the member record must equal the family's `head_id`):
```
POST /api/v1/auth/family-login
Body: national_id + date_of_birth
Returns: JWT Bearer token scoped to their family record
```

Auth endpoints are rate-limited per client IP (`AUTH_RATE_LIMIT`, default `10/minute` → HTTP 429).

### Role permission matrix

| Operation | SUPERADMIN | MANAGER | BLOCK_HEAD | FAMILY |
|---|:---:|:---:|:---:|:---:|
| Read families & members | ✅ | ✅ (own shelter) | ✅ (own block only) | ❌ |
| Register / update / archive family | ✅ | ✅ (own shelter) | ❌ | ❌ |
| Bulk CSV import (`POST /families/import`) | ✅ | ✅ | ❌ | ❌ |
| Add / update / remove members | ✅ | ✅ | ❌ | ❌ |
| Manage system users (`GET/PATCH/DELETE /users`) | ✅ | ❌ | ❌ | ❌ |
| Create users (`POST /auth/register`) | ✅ (any role) | ✅ (BLOCK_HEAD in own shelter only) | ❌ | ❌ |
| Create shelter blocks | ✅ | ✅ (own shelter only) | ❌ | ❌ |
| Other lookups (create/update/delete) | ✅ | ❌ | ❌ | ❌ |
| Review update requests (approve/reject) | ✅ | ✅ | ✅ (scoped) | ❌ |
| Reports + CSV/JSON/XLSX export | ✅ | ✅ | ✅ (scoped) | ❌ |
| Audit log (`GET /audit/`) | ✅ | ❌ | ❌ | ❌ |
| Dashboard stats (scoped) | ✅ | ✅ | ✅ | ❌ |
| View own family record / submit update request / list own requests | ❌ | ❌ | ❌ | ✅ |

`GET /auth/me` returns the staff profile; family tokens get HTTP 403 there (families use `GET /families/me` instead).

Authorization is enforced via `require_role()` FastAPI dependencies injected at the route level. MANAGER reads are scoped to their shelter center; BLOCK_HEAD reads are scoped to their block (see `app/core/scoping.py`).

---

## 🗂️ Data Model

- **Family** — the core entity: head/spouse, residency status, housing type, shelter quality, phone numbers, original city, current shelter center + block, female-/child-headed flags, soft-delete (`is_active`, `archived_at`, `created_at`).
- **Member** — belongs to a family: name, gender, date of birth, marital status, relationship to head, and vulnerability flags (`disabled`, `injured`, `pregnant`, `breastfeeding`, `has_chronic_disease`). `id` is the national ID (integer PK, exactly 9 digits starting with 4/7/8/9, Luhn-validated on input).
- **FamilyUpdateRequest** — family-submitted change proposals (`ADD_MEMBER`, `CHANGE_HEAD`, `UPDATE_FAMILY_INFO`, `UPDATE_MEMBER_INFO`) with a JSON payload and `PENDING`/`APPROVED`/`REJECTED` status plus reviewer/timestamps.
- **AuditLog** — append-only trail (`actor_username`, `actor_role`, `action`, `entity_type`, `entity_id`, `details`, `created_at`); `user_id` is NULL for family-performed actions.
- **Lookup tables** — `Governor`, `City`, `ShelterCenter`, `ShelterBlock`, `ShelterQuality`, `RelationshipToHead` (all with `code`, `name_en`, `name_ar`, `is_active`).
- **User** — system operators only; carries optional `shelter_id` (MANAGER) / `block_id` (BLOCK_HEAD) scope. Families are never stored here. Scope is strictly validated: MANAGER must have `shelter_id` and no `block_id`; BLOCK_HEAD must have `block_id` and no `shelter_id`; SUPERADMIN must have neither.

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
| http://localhost:8000 | API root (`{"name": ...}`) |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/redoc | ReDoc |
| http://localhost:8000/health | Health check (DB ping, 503 when disconnected) |
| http://localhost:8000/metrics | Prometheus metrics |

> **Setup, not auto-create:** the API does **not** create an admin on first run. Run `uv run python -m app.seed` (or `uv run alembic upgrade head` for a schema-only setup) and use the credentials from your `ADMIN_USERNAME` / `ADMIN_PASSWORD` env vars. Change them via the API after first login.

### Frontend (SolidJS SPA)

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server runs at http://localhost:5173 and proxies `/api` requests to the backend at `http://localhost:8000`. The SPA talks to the backend only through `/api/v1` + JWT (`localStorage` token, role-based route guards in `_staff.tsx` / `_family.tsx`), so it can be moved to its own repo without backend changes.

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
PROJECT_NAME=Displaced Camp Manager
SECRET_KEY=your-secret-key-here        # Required — signs JWT tokens and admin sessions
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
SQLALCHEMY_DATABASE_URI=sqlite+aiosqlite:///./camp_manager.db   # or postgresql+asyncpg://...
ADMIN_USERNAME=admin                   # First superadmin (used by `python -m app.seed`)
ADMIN_PASSWORD=change-me
ADMIN_EMAIL=admin@example.com          # First superadmin email (used by `python -m app.seed`)
CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"] # Allowed SPA origins (JSON list)
AUTH_RATE_LIMIT=10/minute              # Rate limit for POST /auth/login + /auth/family-login
```

---

## 📡 API Endpoints

> All paths under `/api/v1`. "Staff" = SUPERADMIN, MANAGER, BLOCK_HEAD.

### Auth (`/auth`)
| Method | Endpoint | Description | Access |
|---|---|---|---|
| POST | `/auth/login` | Staff login → JWT (rate-limited) | Public |
| POST | `/auth/family-login` | Family login by head national ID + DOB (rate-limited) | Public |
| GET | `/auth/me` | Current staff profile (403 for family tokens) | Staff |
| POST | `/auth/register` | Create system user (MANAGERs: BLOCK_HEAD in own shelter only) | SUPERADMIN, MANAGER |

### Families (`/families`)
| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/families/?page&limit&...filters` | List families (filtering, sorting, pagination) | Staff (scoped) |
| POST | `/families/` | Register a new family with members | SUPERADMIN, MANAGER |
| POST | `/families/import` | Bulk CSV import (multipart `.csv`, per-family error report + audit) | SUPERADMIN, MANAGER |
| GET | `/families/{id}` | Family details + computed stats | Staff (scoped) |
| PUT | `/families/{id}` | Update family record | SUPERADMIN, MANAGER |
| PATCH | `/families/{id}/archive` | Soft-delete a family | SUPERADMIN, MANAGER |
| PATCH | `/families/{id}/restore` | Restore archived family | SUPERADMIN, MANAGER |
| GET | `/families/me` | Family's own record | FAMILY |
| GET | `/families/members?page&limit&...filters` | List members (filtering incl. national-ID prefix search, pagination) | Staff (scoped) |
| POST | `/families/{family_id}/members` | Add member to family | SUPERADMIN, MANAGER |
| PUT | `/families/members/{member_id}` | Update member | SUPERADMIN, MANAGER |
| DELETE | `/families/members/{member_id}` | Remove member (204) | SUPERADMIN, MANAGER |

### Update requests (family self-service)
| Method | Endpoint | Description | Access |
|---|---|---|---|
| POST | `/families/me/update-requests` | Propose a change (add member, phone, etc.) | FAMILY |
| GET | `/families/me/update-requests` | List own requests (any status) | FAMILY |
| GET | `/families/update-requests` | List scoped pending requests | SUPERADMIN, MANAGER, BLOCK_HEAD |
| PATCH | `/families/{request_id}/approve` | Approve and apply a request | SUPERADMIN, MANAGER, BLOCK_HEAD |
| PATCH | `/families/{request_id}/reject` | Reject a request | SUPERADMIN, MANAGER, BLOCK_HEAD |

### Users (`/users`)
| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/users/` | List system users | SUPERADMIN |
| GET | `/users/{user_id}` | User details | SUPERADMIN |
| PATCH | `/users/{user_id}` | Update user (role, shelter, block, password) | SUPERADMIN |
| DELETE | `/users/{user_id}` | Deactivate user | SUPERADMIN |

### Lookups (`/lookups`) — `governors`, `cities`, `shelter-centers`, `shelter-blocks`, `shelter-qualities`, `relationships`
| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/lookups/{resource}?skip&limit&is_active` | List entries (read-only for UI dropdowns) | Staff + FAMILY |
| POST | `/lookups/{resource}` | Create entry (`shelter-blocks`: MANAGER allowed in own center) | SUPERADMIN (+ MANAGER for blocks) |
| PUT | `/lookups/{resource}/{item_id}` | Update entry | SUPERADMIN |
| DELETE | `/lookups/{resource}/{item_id}` | Delete entry (204) | SUPERADMIN |

### Reports (`/reports`) — all role-scoped (MANAGER → shelter, BLOCK_HEAD → block)
| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/reports/families?page&limit&block_ids` | Family report (paginated) | SUPERADMIN, MANAGER, BLOCK_HEAD |
| GET | `/reports/families/export?block_ids&selected_ids&columns&format=csv\|json` | CSV/JSON export | SUPERADMIN, MANAGER, BLOCK_HEAD |
| GET | `/reports/members?page&limit&block_ids&special_only` | Member report (+ `special_only` vulnerability flag) | SUPERADMIN, MANAGER, BLOCK_HEAD |
| GET | `/reports/members/export?block_ids&special_only&selected_ids&columns&format=csv\|json` | CSV/JSON export | SUPERADMIN, MANAGER, BLOCK_HEAD |

### Export (`/export`) — XLSX workbooks via the same scoped report pipeline
| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/export/families?block_ids&selected_ids&columns` | `families_export.xlsx` download | SUPERADMIN, MANAGER, BLOCK_HEAD |
| GET | `/export/members?block_ids&special_only&selected_ids&columns` | `members_export.xlsx` download | SUPERADMIN, MANAGER, BLOCK_HEAD |

### Audit (`/audit`)
| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/audit/?action&entity_type&entity_id&user_id&page&limit` | Query audit trail (newest first) | SUPERADMIN |

### Dashboard (`/dashboard`)
| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/dashboard/stats` | Family/member totals, age bands, vulnerability counts, block & center occupancy, pending requests (scoped) | SUPERADMIN, MANAGER, BLOCK_HEAD |

---

## 🛠️ Skills Demonstrated

- **REST API design** — resource-oriented endpoints, correct HTTP methods/status codes, consistent error responses
- **FastAPI** — dependency injection, OAuth2 password bearer, Pydantic v2 schemas, scoped auth dependencies
- **SQLAlchemy 2.0** — typed `Mapped` columns, relationships with `foreign_keys`, soft delete, JSON payloads (JSON/JSONB)
- **Authentication** — JWT HS256, bcrypt hashing, token expiry, two separate auth flows in one API
- **Authorization** — role-based access via `require_role()` factory + MANAGER/BLOCK_HEAD scope guard
- **Validation** — Palestine national ID validation (9 digits, leading 4/7/8/9, Luhn checksum, mirrored in frontend zod schemas), startup `SECRET_KEY` warning
- **Observability** — structured logging (structlog + correlation IDs), Prometheus metrics, health checks
- **Layered architecture** — router → service → repository → model, easily testable
- **Testing** — 67 async pytest tests (services, auth endpoints, scoping, dashboard, export, CSV import, audit, rate limiting)
- **Frontend** — SolidJS SPA with TanStack Router/Query, JWT store with role guards, bilingual UI (English/Arabic, RTL), zod schemas, CSV/JSON/XLSX export helpers

---

## 🔮 Roadmap

### API
- [ ] PostgreSQL production deployment
- [ ] `.env` strict validation on startup (currently only a `SECRET_KEY` default warning)
- [ ] `AUTH_RATE_LIMIT` missing from `.env.example` (present in config) — add it

### Frontend
- [ ] Camp map showing block occupancy
- [ ] Full Arabic localization pass (dictionary exists in `src/i18n`, needs completion)
- [ ] Extract to its own repo (backend is already decoupled via `/api/v1` + JWT; no backend changes needed)

### Infrastructure
- [ ] Docker + docker-compose setup
- [ ] GitHub Actions CI (lint, test, migrate)

---

## 📁 Project Structure

```
displacedCamp/
├── app/
│   ├── main.py
│   ├── seed.py
│   ├── api/
│   │   ├── deps.py
│   │   └── v1/
│   │       ├── router.py
│   │       └── endpoints/        # auth, families, users, audit, lookups, reports, export, dashboard
│   ├── core/                     # config, security, errors, scoping
│   ├── db/                       # session.py
│   ├── models/                   # enums, lookups, family, user, audit
│   ├── schemas/                  # family, user, lookups, report, filters, dashboard, audit
│   ├── repositories/             # data access layer (incl. auditRepository)
│   └── services/                 # family, user, lookup, report, update_request, audit, export, import
├── frontend/                     # Standalone SolidJS SPA (extractable)
│   └── src/
│       ├── api/                  # client.ts (JWT fetch wrapper) + endpoints.ts
│       ├── auth/store.ts         # token persistence + role guards
│       ├── components/           # FamilyForm, MemberForm, ui, toast
│       ├── i18n/                 # English / Arabic (RTL)
│       ├── routes/               # login, family-login, _staff/*, _family/me
│       ├── schemas/              # zod schemas (incl. Luhn national ID)
│       ├── queries.ts            # TanStack Query helpers
│       └── exportColumns.ts      # report column selection
├── alembic/                      # migrations (head: 9999_restore_trgm)
├── scripts/generate_large_dataset.py
├── tests/                        # 67 async pytest tests
├── .env.example
├── pyproject.toml
└── README.md
```

---

## 👤 Author

**Mohammed Naim**
Software Engineer · Python · FastAPI · SQLAlchemy

[GitHub](https://github.com/m-naim1)

---

*Built as a portfolio project demonstrating production-grade full-stack development with Python and SolidJS — designed around a real humanitarian need: tracking and supporting displaced families in camp settings.*

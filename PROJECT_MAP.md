# PROJECT_MAP — Displaced Families Camp Manager

> Living document. If this file disagrees with the code, the code wins — update this file.

## TECH_STACK

| Layer | Technology | Version |
|-------|-----------|---------|
| Runtime | Python | >= 3.14 |
| Backend framework | FastAPI | >= 0.124.0 |
| ORM | SQLAlchemy 2.0 (async) | >= 2.0.45 |
| Validation | Pydantic v2 | >= 2.12.5 |
| Auth | JWT (python-jose) + bcrypt (passlib) | 3.5.0 / 1.7.4 |
| Admin panel | starlette-admin | >= 0.16.0 |
| Migrations | Alembic | >= 1.18.4 |
| DB | SQLite (aiosqlite) — dev · PostgreSQL-ready (JSONB, asyncpg) | 0.22.1 |
| Logging | structlog (structured, correlation IDs) | >= 26.1.0 |
| Metrics | prometheus-fastapi-instrumentator (`/metrics`) | >= 7.1.0 |
| Server | uvicorn | >= 0.38.0 |
| Package manager (backend) | uv | — |
| Frontend | SolidJS · Vite · TanStack Router · TanStack Query · UnoCSS · zod | — |
| Lint / tests | ruff · pytest (pytest-asyncio, `asyncio_mode=auto`) | — |

---

## SYSTEM_FLOW

```
                ┌───────────────────────────────────────────┐
                │              FastAPI (uvicorn)            │
                │              app/main.py:app              │
                └──────┬──────────────────────────────┬─────┘
                       │                              │
              ┌────────▼────────┐          ┌──────────▼──────────┐
              │    REST API     │          │   starlette-admin    │
              │    /api/v1/*    │          │       /admin         │
              │   (stateless)   │          │  (SUPERADMIN only)   │
              └────────┬────────┘          └──────────┬──────────┘
                       │                              │
                       └───────────────┬──────────────┘
                                       │
                        ┌──────────────▼──────────────┐
                        │  Frontend: SolidJS SPA       │
                        │  frontend/ (Vite dev server) │
                        │  proxies /api → :8000        │
                        └──────────────┬───────────────┘
                                       │
                        ┌──────────────▼──────────────┐
                        │  api/deps.py  require_role() │
                        │  + scoping (core/scoping.py) │
                        └──────────────┬───────────────┘
                                       │
                        ┌──────────────▼──────────────┐
                        │        SERVICES (logic)      │
                        └──────────────┬───────────────┘
                                       │
                        ┌──────────────▼──────────────┐
                        │     REPOSITORIES (data)      │
                        └──────────────┬───────────────┘
                                       │
                        ┌──────────────▼───────────────┐
                        │   SQLAlchemy MODELS → SQLite │
                        └──────────────────────────────┘
```

### Auth flows
```
Staff:      POST /api/v1/auth/login  → JWT (sub=username, role)
            → require_role(...) guard → scoped controllers

Family:     POST /api/v1/auth/family-login  → JWT (sub=national_id,
            role=FAMILY, family_id) — national ID validated (format + Luhn)

Admin:      Session-based starlette-admin AuthProvider — SUPERADMIN only
```

### Role permission matrix
| Operation | SUPERADMIN | MANAGER | BLOCK_HEAD | FAMILY |
|---|:---:|:---:|:---:|:---:|
| Read families & members | ✅ | ✅ | ✅ (own block) | ❌ |
| Register / update / archive family | ✅ | ✅ | ❌ | ❌ |
| Add / update / remove members | ✅ | ✅ | ❌ | ❌ |
| Manage system users | ✅ | ❌ | ❌ | ❌ |
| Admin panel `/admin` | ✅ | ❌ | ❌ | ❌ |
| Own record + update requests | ❌ | ❌ | ❌ | ✅ |

Reads for MANAGER are scoped to their shelter center, and for BLOCK_HEAD to their block (`app/core/scoping.py`; enforced in tests by `tests/test_block_head_scope.py`).

---

## ARCHITECTURE

### Directory layout (current)
```
app/
├── main.py                  # FastAPI app, middleware (CORS/session/access-log/correlation),
│                            #   exception handlers, admin panel mount, /health, /metrics
├── admin.py                 # AdminAuthProvider, DashboardView (live stats), UserAdminView (hashes pwd)
├── seed.py                  # create_all + Gaza lookups (5 gov | 20 cities | 11 rel | 3 qualities
│                            #   | 3 centers | 4 blocks) + first superadmin (from env ADMIN_*)
├── api/
│   ├── deps.py              # DI providers + require_role(*roles) factory (+ FAMILY token handling)
│   └── v1/
│       ├── router.py        # mounts families, auth, users, lookups, reports, dashboard
│       └── endpoints/       # auth.py, families.py, users.py, lookups.py, reports.py, dashboard.py
├── core/
│   ├── config.py            # pydantic-settings (env .env)
│   ├── security.py          # create_access_token / get_password_hash / verify_password (async)
│   ├── errors.py            # NotFoundError, ConflictError, DomainError, ValidationError
│   └── scoping.py           # require_block_head_scope(), manager/block-head family scope guard
├── db/session.py            # Base, async engine, AsyncSessionLocal
├── models/
│   ├── enums.py             # UserRole, ResidencyStatus, Gender, MaritalStatus,
│   │                        #   HousingType, UpdateRequestType, UpdateRequestStatus
│   ├── lookups.py           # Governor, City, ShelterCenter, ShelterBlock, ShelterQuality,
│   │                        #   RelationshipToHead
│   ├── family.py            # Family, Member, FamilyUpdateRequest (payload JSON/JSONB variant)
│   └── user.py              # User (block_id, shelter_id; flush-time role/scope validation)
├── schemas/
│   ├── family.py            # FamilyCreate/Response/Update, Member*, validate_palestine_id (Luhn)
│   ├── user.py              # UserCreate/Update/Response, Token, FamilyLoginSchema (Luhn)
│   ├── lookups.py           # generic + Shelter*/City schemas
│   ├── report.py            # FamilyReportRow, MemberReportRow
│   ├── filters.py           # FamilyFilterParams, MemberFilterParams (dataclasses w/ Query())
│   ├── dashboard.py         # DashboardStats, BlockCount, CenterCount
│   └── update_request.py    # UpdateRequestCreate (+ sub-request payload models)
├── repositories/            # base.py + family/Member/lookup/updateRequest/user repositories
└── services/                # family_service, user_service, lookup_service, report_service,
                             #   update_request_service (all async)

frontend/                    # SolidJS SPA
├── src/
│   ├── api/                 # client.ts, endpoints.ts  (proxied via Vite → :8000)
│   ├── auth/store.ts        # token persistence
│   ├── components/          # FamilyForm.tsx, MemberForm.tsx, ui.tsx, toast.tsx
│   ├── i18n/index.ts        # English + Arabic
│   ├── routes/              # __root, login, family-login, _staff/* (dashboard, families/[index|new|$id],
│   │                        #   members, reports, update-requests, users, lookups), _family/me
│   └── schemas/             # index.ts (zod)

templates/index.html         # admin dashboard template
tests/                       # 43 async tests: family, user, update_request, block_head scope
alembic/                     # migrations (see KNOWN GAPS)
.env.example
```

### Data model (abridged)
- **Family** — `head_id`, `spouse_id`, `residency_status`, `female_headed`, `child_headed`, phones, `original_city_id`, `current_shelter_center_id`, `shelter_block_id`, `housing_type`, `shelter_quality_id`, `is_active`, `archived_at`.
- **Member** — PK = national ID (`id`), `family_id`, `full_name`, `gender`, `marital_status`, `date_of_birth`, `relationship_to_head_id`, health flags (`has_chronic_disease`, `injured`, `disabled`, `pregnant`, `breastfeeding`).
- **FamilyUpdateRequest** — `family_id`, `request_type` (`ADD_MEMBER | CHANGE_HEAD | UPDATE_FAMILY_INFO | UPDATE_MEMBER_INFO`), `payload` (JSON/JSONB), `status` (`PENDING | APPROVED | REJECTED`), `reviewed_by_id`, `reviewed_at`, `created_at`.
- **User** — username (unique), email, `hashed_password`, `full_name`, `role`, `is_active`, `shelter_id` (MANAGER), `block_id` (BLOCK_HEAD). Role consistency validated at flush time (`before_insert`/`before_update`) — ordering of kwargs irrelevant.

### Request flow
`endpoint → deps.require_role() → service ctor(repository(db)) → repository → model`
Errors: `NotFoundError` → 404, `ConflictError` → 409, `DomainError`/`ValidationError` → 400, unhandled → 500 (all logged with correlation ID).

---

## SEED DATA (`python -m app.seed`)

Idempotent (Postgres `on_conflict_do_nothing`; works on SQLite too):

- 5 governors (Gaza strip), 20 cities, 11 relationships-to-head, 3 shelter qualities
- 3 shelter centers + 4 blocks
- SUPERADMIN created from `ADMIN_USERNAME` / `ADMIN_PASSWORD` / `ADMIN_EMAIL` env vars
- Rules: `require_role` respects FAMILY tokens as a dict (`family_id`); `require_block_head_scope` drives block-level reads.

---

## TESTS

`uv run pytest` — 43 passing (async, in-memory SQLite):

| Module | Covers |
|---|---|
| `test_family_service.py` | CRUD, duplicate head, filters, manager scoping, archive/restore, members, dashboard stats |
| `test_user_service.py` | create roles, duplicate/chars validation, auth, update, deactivate |
| `test_update_request_service.py` | create/approve/reject flows, validation failures, member application |
| `test_block_head_scope.py` | BLOCK_HEAD create scoping, own-block reads, cross-block 403 |

---

## KNOWN GAPS & PENDING

| Item | Status | Notes |
|---|---|---|
| Alembic migrations lag models | ⚠️ PENDING | No revision for `family_update_requests` table or `users.shelter_id`/`block_id`; fresh DB should use `python -m app.seed` (create_all) until a revision is added |
| `.env` default DB | ⚠️ LOCAL | Repo `.env` points at `postgresql+asyncpg://localhost:5432` (not running); switch to `sqlite+aiosqlite:///./camp_manager.db` for local dev |
| Lint clean across repo | ⚠️ PARTIAL | `ruff check` passes on touched files + tests; pre-existing `E501`/`F841`/`B904` remain in untouched files (`app/main.py`, `app/admin.py`, services, etc.) |
| `ruff` installed? | ⚠️ NOTE | Not in dev deps in `pyproject.toml` — run via `uvx ruff` or install manually |
| Password change via admin panel | ✅ OK | `UserAdminView.before_create/edit` hashes plaintext |
| Health endpoint | ✅ OK | `/health` pings DB (sync-safe, 503 when disconnected) |
| Admin panel role gate | ✅ OK | `AdminAuthProvider` rejects non-SUPERADMIN |
| Backend not creating admin on run | ✅ FIXED | README previously claimed auto-creation; admin is created only by `seed.py` (and that username bug is fixed) |
| `test_block_head_service.py` removed | ✅ OK | Feature (`BlockHeadPermission`, portals) deleted earlier; replaced by `test_block_head_scope.py` |
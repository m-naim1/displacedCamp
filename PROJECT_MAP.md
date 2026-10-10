# PROJECT_MAP — Displaced Families Camp Manager

> Living document. If this file disagrees with the code, the code wins — update this file.

## TECH_STACK

| Layer | Technology | Version |
|-------|-----------|---------|
| Runtime | Python | >= 3.14 |
| Backend framework | FastAPI | >= 0.124.0 |
| ORM | SQLAlchemy 2.0 (async) | >= 2.0.45 |
| Validation | Pydantic v2 | >= 2.12.5 |
| Auth | JWT (python-jose) + bcrypt (async via `asyncio.to_thread`) | 3.5.0 / 5.0.0 |
| Rate limiting | slowapi (`AUTH_RATE_LIMIT`, default `10/minute` on `/auth/*`) | >= 0.1.10 |
| XLSX export | openpyxl | >= 3.1.5 |
| Migrations | Alembic | >= 1.18.4 |
| DB drivers | aiosqlite (dev) · asyncpg (Postgres, JSONB, pg_trgm) | 0.22.1 / >= 0.32.0 |
| DB | SQLite (aiosqlite) — dev · PostgreSQL-ready (JSONB, asyncpg) | 0.22.1 |
| Logging | structlog (structured, correlation IDs) | >= 26.1.0 |
| Metrics | prometheus-fastapi-instrumentator (`/metrics`) | >= 7.1.0 |
| Server | uvicorn | >= 0.38.0 |
| Package manager (backend) | uv | — |
| Frontend | SolidJS · Vite · TanStack Router · TanStack Query · UnoCSS · zod (standalone SPA, extractable) | 1.9.9 / 7.1.9 / 1.170 / 5.101 / 66.5 / 4.1 |
| Lint / tests | ruff · pytest (pytest-asyncio, `asyncio_mode=auto`) · ty · httpx | — |

---

## SYSTEM_FLOW

```
                ┌───────────────────────────────────────────┐
                │              FastAPI (uvicorn)            │
                │              app/main.py:app              │
                └─────────────────────┬─────────────────────┘
                                      │
              ┌───────────────────────▼─────────────────────┐
              │                 REST API                    │
              │                 /api/v1/*                   │
              │                (stateless)                  │
              └───────────────────────┬─────────────────────┘
                                      │
                        ┌──────────────▼──────────────┐
                        │  Frontend: SolidJS SPA       │
                        │  frontend/ (Vite dev server) │
                        │  proxies /api → :8000        │
                        │  standalone — only /api/v1   │
                        │  + JWT; safe to move to its  │
                        │  own repo                    │
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
Staff:      POST /api/v1/auth/login  → JWT (sub=username, role, shelter_id)
            → require_role(...) guard → scoped controllers
            Rate-limited per IP (AUTH_RATE_LIMIT, default 10/minute → 429)

Family:     POST /api/v1/auth/family-login  → JWT (sub=national_id,
            role=FAMILY, family_id) — head national ID validated (9 digits,
            leading 4/7/8/9 + Luhn); member must be the family head.
            Rate-limited per IP.
```

### Role permission matrix
| Operation | SUPERADMIN | MANAGER | BLOCK_HEAD | FAMILY |
|---|:---:|:---:|:---:|:---:|
| Read families & members | ✅ | ✅ (own shelter) | ✅ (own block) | ❌ |
| Register / update / archive family | ✅ | ✅ | ❌ | ❌ |
| Bulk CSV import | ✅ | ✅ | ❌ | ❌ |
| Add / update / remove members | ✅ | ✅ | ❌ | ❌ |
| Manage system users | ✅ | ❌ | ❌ | ❌ |
| Create users (`POST /auth/register`) | ✅ (any) | ✅ (BLOCK_HEAD, own shelter) | ❌ | ❌ |
| Create shelter-blocks | ✅ | ✅ (own shelter) | ❌ | ❌ |
| Other lookup writes | ✅ | ❌ | ❌ | ❌ |
| Review update requests | ✅ | ✅ | ✅ (scoped) | ❌ |
| Reports + CSV/JSON/XLSX export | ✅ | ✅ | ✅ (scoped) | ❌ |
| Audit log | ✅ | ❌ | ❌ | ❌ |
| Own record + update requests | ❌ | ❌ | ❌ | ✅ |

Reads for MANAGER are scoped to their shelter center, and for BLOCK_HEAD to their block (`app/core/scoping.py`; enforced in tests by `tests/test_block_head_scope.py`).

---

## ARCHITECTURE

### Directory layout (current)
```
app/
├── main.py                  # FastAPI app, middleware (CORS/access-log/correlation),
│                            #   exception handlers, /health, /metrics
├── seed.py                  # create_all + Gaza lookups (5 gov | 20 cities | 11 rel | 3 qualities
│                            #   | 3 centers | 4 blocks) + first superadmin (from env ADMIN_*)
├── api/
│   ├── deps.py              # DI providers + require_role(*roles) factory (+ FAMILY token handling)
│   └── v1/
│       ├── router.py        # mounts families, auth, users, audit, lookups, reports, export, dashboard
│       └── endpoints/       # auth.py, families.py (incl. CSV import), users.py,
│                            #   audit.py, lookups.py, reports.py, export.py (XLSX), dashboard.py
├── core/
│   ├── config.py            # pydantic-settings (env .env; AUTH_RATE_LIMIT, CORS_ORIGINS, ADMIN_*)
│   ├── security.py          # create_access_token / decode / bcrypt hash+verify (async via to_thread)
│   ├── errors.py            # NotFoundError, ConflictError, DomainError, ValidationError
│   └── scoping.py           # require_manager_shelter_id(), require_block_head_scope(),
│                            #   verify_family_scope() (manager→shelter, block-head→block)
├── db/session.py            # Base, async engine, AsyncSessionLocal
├── models/
│   ├── enums.py             # UserRole, ResidencyStatus, Gender, MaritalStatus,
│   │                        #   HousingType, UpdateRequestType, UpdateRequestStatus, AuditAction
│   ├── lookups.py           # Governor, City, ShelterCenter, ShelterBlock, ShelterQuality,
│   │                        #   RelationshipToHead
│   ├── family.py            # Family, Member (PK = national ID int), FamilyUpdateRequest
│   │                        #   (payload JSON/JSONB variant)
│   ├── audit.py             # AuditLog (append-only; user_id NULL for family actions)
│   └── user.py              # User (block_id, shelter_id; flush-time role/scope validation)
├── schemas/
│   ├── family.py            # FamilyCreate/Response/Update, Member*, validate_palestine_id
│   │                        #   (9 digits, leading 4/7/8/9 + Luhn)
│   ├── user.py              # UserCreate/Update/Response, Token, FamilyLoginSchema (Luhn)
│   ├── lookups.py           # generic + Shelter*/City schemas
│   ├── report.py            # FamilyReportRow, MemberReportRow
│   ├── filters.py           # FamilyFilterParams, MemberFilterParams (dataclasses w/ Query();
│   │                        #   multi-select lists, national-ID prefix search, sorting)
│   ├── dashboard.py         # DashboardStats, BlockCount, CenterCount
│   └── audit.py             # AuditLogResponse
├── repositories/            # base.py + family/Member/lookup/updateRequest/user/audit repositories
└── services/                # family_service, user_service, lookup_service, report_service,
                             #   update_request_service, audit_service, export_service (XLSX),
                             #   import_service (CSV parsing) — all async

frontend/                    # Standalone SolidJS SPA (Vite; extractable to own repo)
├── src/
│   ├── api/                 # client.ts (JWT fetch wrapper, 401 handling) + endpoints.ts
│   ├── auth/store.ts        # token persistence (localStorage), JWT claims, role guards
│   ├── components/          # FamilyForm.tsx, MemberForm.tsx, ui.tsx, toast.tsx
│   ├── i18n/index.ts        # English + Arabic (RTL toggle, localStorage)
│   ├── routes/              # __root, login, family-login, _staff/* (dashboard, families/[index|new|$id],
│   │                        #   members, reports, update-requests, users, lookups, audit), _family/me
│   ├── schemas/             # index.ts + enums.ts (zod; Luhn national ID, report/audit/dashboard rows)
│   ├── queries.ts           # TanStack Query helpers
│   └── exportColumns.ts     # report column selection
├── vite.config.ts           # /api → http://localhost:8000 proxy, '@' alias
└── package.json             # solid-js, @tanstack/solid-router, @tanstack/solid-query, zod

scripts/generate_large_dataset.py  # load-test data generator (run seed first)
tests/                       # 67 async tests (see TESTS)
alembic/                     # migrations, head = 9999_restore_trgm (see KNOWN GAPS)
.env.example                 # NOTE: missing AUTH_RATE_LIMIT (in config.py)
```

### Data model (abridged)
- **Family** — `head_id`, `spouse_id`, `residency_status`, `female_headed`, `child_headed`, phones, `original_city_id`, `current_shelter_center_id`, `shelter_block_id`, `housing_type`, `shelter_quality_id`, `is_active`, `archived_at`, `created_at`.
- **Member** — PK = national ID int (`id`, 9 digits / leading 4/7/8/9 / Luhn on input), `family_id`, `full_name`, `gender`, `marital_status`, `date_of_birth`, `relationship_to_head_id`, health flags (`has_chronic_disease`, `injured`, `disabled`, `pregnant`, `breastfeeding`).
- **FamilyUpdateRequest** — `family_id`, `request_type` (`ADD_MEMBER | CHANGE_HEAD | UPDATE_FAMILY_INFO | UPDATE_MEMBER_INFO`), `payload` (JSON/JSONB), `status` (`PENDING | APPROVED | REJECTED`), `reviewed_by_id`, `reviewed_at`, `created_at`.
- **AuditLog** — `user_id` (NULL for family actions), `actor_username`, `actor_role`, `action` (AuditAction constants), `entity_type`, `entity_id`, `details` (JSON/JSONB), `created_at`.
- **User** — username/email (unique), `hashed_password`, `full_name`, `role`, `is_active`, `shelter_id` (MANAGER only, required), `block_id` (BLOCK_HEAD only, required). Strict: SUPERADMIN has neither; violations raise at flush time (`before_insert`/`before_update`).

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

`uv run pytest` — 67 passing (async, in-memory SQLite):

| Module | Count | Covers |
|---|---|---|
| `test_auth_endpoints.py` | 3 | staff/family login success+failure, family-login rate limit |
| `test_block_head_scope.py` | 3 | BLOCK_HEAD create scoping, own-block reads, cross-block 403 |
| `test_dashboard_scoping.py` | 4 | superadmin/manager/block-head scoping, manager-without-shelter guard |
| `test_export.py` | 5 | XLSX families/members, column selection, endpoint auth + content |
| `test_family_service.py` | 16 | CRUD, duplicate head, filters, manager scoping, archive/restore, members, pregnancy rule, dashboard stats |
| `test_new_features.py` | 12 | audit lifecycle + filters, auth rate limiting, CSV import (valid/errors/missing cols/endpoint), dashboard age bands + pending count, report CSV output + column filtering, lookup duplicate-code conflict, national-ID prefix search |
| `test_update_request_service.py` | 10 | create/approve/reject flows, validation failures, scoped pending list, already-reviewed + not-found |
| `test_user_service.py` | 14 | create roles (incl. manager-without-shelter guard), duplicate validation, auth, update (+password), deactivate |

---

## KNOWN GAPS & PENDING

| Item | Status | Notes |
|---|---|---|
| Alembic chain | ✅ OK (head `9999_restore_trgm`) | Revisions cover initial schema, member-ID fixes, nullable head, `family_update_requests` + `audit_logs` (`b3e8f7a2c1d4`), pg_trgm + index, performance indexes (`e1f9c4d8a2b3`), trgm restore (`9999`). Fresh DB can use `python -m app.seed` (create_all) or `alembic upgrade head` |
| `.env` vs `.env.example` | ⚠️ DRIFT | `.env.example` lacks `AUTH_RATE_LIMIT` (real in `config.py`); copy + add it manually |
| `.env` default DB | ⚠️ LOCAL | Repo `.env` points at `postgresql+asyncpg://localhost:5432` (not running); switch to `sqlite+aiosqlite:///./camp_manager.db` for local dev |
| Startup env validation | ⚠️ PARTIAL | Only a `SECRET_KEY == "change-me"` warning in `main.py`; no strict fail-fast |
| Audit log | ✅ DONE | `audit_logs` + `GET /audit/` (SUPERADMIN) + service-layer writes incl. `BULK_IMPORT` |
| Auth rate limiting | ✅ DONE | `slowapi`, `AUTH_RATE_LIMIT=10/minute` on login + family-login (covered by tests) |
| Pagination / search | ✅ MOSTLY DONE | `page`/`limit` + `FamilyFilterParams`/`MemberFilterParams` (multi-select, sorting, national-ID prefix); reports add `block_ids`/`selected_ids`/`columns`/`special_only` |
| CSV import / XLSX export | ✅ DONE | `POST /families/import`, `GET /reports/*/export` (csv/json), `GET /export/*` (xlsx); frontend `exportReport`/`exportXlsx` helpers |
| Health endpoint | ✅ OK | `/health` pings DB (503 when disconnected); access log also skips `/health/liveness`, `/health/readiness`, `/metrics` |
| Backend not creating admin on run | ✅ OK | Admin is created only by `seed.py` from `ADMIN_*` env |
| Frontend extraction | 🔜 PLANNED | SPA is already decoupled (only `/api/v1` + JWT); moving `frontend/` to its own repo needs no backend changes |
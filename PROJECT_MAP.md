# PROJECT_MAP — Displaced Families Camp Manager

## TECH_STACK

| Layer | Technology | Version |
|-------|-----------|---------|
| Runtime | Python | 3.14.2 |
| Framework | FastAPI | 0.124.0 |
| ORM | SQLAlchemy 2.0 (async) | 2.0.45 |
| Validation | Pydantic v2 | 2.12.5 |
| Auth | JWT (python-jose) + bcrypt | 3.5.0 |
| Admin Panel | starlette-admin | 0.16.0 |
| Migrations | Alembic | 1.18.4 |
| DB | SQLite (aiosqlite) | 0.22.1 |
| Server | uvicorn | 0.38.0 |
| Frontend | Jinja2 + HTMX | server-rendered |
| Package mgr | uv | 0.11.8 |

---

## SYSTEM_FLOW

```
                    ┌──────────────────────────┐
                    │     FastAPI (uvicorn)     │
                    │   app/main.py:app         │
                    └──────────┬───────────────┘
                               │
              ┌────────────────┼────────────────────┐
              │                │                    │
     ┌────────▼──────┐  ┌─────▼──────┐   ┌─────────▼────────┐
     │  REST API     │  │ starlette- │   │   PORTALS        │
     │  /api/v1/*    │  │ admin      │   │   (Jinja2+HTMX)  │
     │  (stateless)  │  │ /admin     │   │   /portal/*      │
     └────────┬──────┘  └─────┬──────┘   └─────────┬────────┘
              │               │                    │
              └───────┬───────┴────────────────────┘
                      │
              ┌───────▼───────┐
              │  DEPENDENCIES │
              │  deps.py      │
              │  (auth guard) │
              └───────┬───────┘
                      │
              ┌───────▼───────┐
              │   SERVICES    │
              │  (business    │
              │   logic)      │
              └───────┬───────┘
                      │
              ┌───────▼───────┐
              │   MODELS      │
              │  (SQLAlchemy) │
              └───────┬───────┘
                      │
              ┌───────▼───────┐
              │   SQLite DB   │
              └───────────────┘
```

### Auth flow
```
Login → JWT → require_role(ROLE) → guarded route/portal
Admin session → starlette-admin AuthProvider (SUPERADMIN → /admin)
Family login → national_id + DOB → JWT with family_id scope
Portal staff login → session-based → role-based redirect (SUPERADMIN→/admin, MANAGER→/portal/manager, etc.)
```

### Portal routing per role
| Role | Portal path | Access |
|------|------------|--------|
| SUPERADMIN | /admin | starlette-admin (full CRUD + user mgmt) |
| MANAGER | /portal/manager | Camp-scoped mgmt |
| BLOCK_HEAD | /portal/block | Block-scoped (permission-gated) |
| FAMILY | /portal/family | Self-service view + request |
| Unauthed | /portal/login | Login redirect |

---

## ARCHITECTURE

### Directory (post-refactor)
```
app/
├── api/v1/endpoints/   # REST — untouched
├── core/               # config, security, errors — untouched
├── models/             # ORM
├── schemas/            # Pydantic
├── services/           # Logic (all wired with logger)
├── db/session.py       # untouched
├── admin.py            # enhanced role-gating + logger
├── portals/            # Jinja2+HTMX dashboards
│   ├── common.py       # shared templates + auth deps + load_lookups() + logger
│   ├── router.py       # auth routes + sub-router mounting + SUPERADMIN→/admin
│   ├── admin_portal.py # [REMOVED] redirects to /admin
│   ├── manager_portal.py
│   ├── blockhead_portal.py
│   └── family_portal.py
├── logging.py          # sync structured logger (stdout)
├── static/             # CSS
│   └── style.css
└── main.py             # lifespan + portal mount
templates/portals/      # per-role templates (admin templates removed)
tests/                  # [NEW] unit tests for all services
├── conftest.py
├── test_family_service.py
├── test_user_service.py
├── test_update_request_service.py
└── test_block_head_service.py
```

### New Models
```python
class BlockHeadPermission(Base):
    """MANAGER-controlled permissions per BLOCK_HEAD user"""
    __tablename__ = "block_head_permissions"
    id: int
    user_id: int  # FK → users.id (must be BLOCK_HEAD role)
    can_edit: bool = False
    can_add: bool = False
    can_delete: bool = False

class UpdateRequest(Base):
    """Family-submitted change requests — reviewed by MANAGER"""
    __tablename__ = "update_requests"
    id: int
    family_id: int  # FK → families.id
    requested_changes: dict  # JSON: which fields changed
    status: str  # pending / approved / rejected
    created_at: datetime
    reviewed_at: datetime | None
    reviewed_by: int | None  # FK → users.id
```

---

## ACTION PLAN — Milestones

| M | Verifiable Goal | Status |
|---|----------------|--------|
| M1 | Enhanced starlette-admin with role-gated views per portal | ✅ DONE |
| M2 | Manager portal: camp-scoped family CRUD + block-head permission toggle + UpdateRequest review UI | ✅ DONE |
| M3 | Block head portal: block-scoped read-only view, configurable edit/add/delete via BlockHeadPermission | ✅ DONE |
| M4 | Family portal: self-service view + UpdateRequest submission (stored as pending in DB) | ✅ DONE |
| M5 | Async logger (INFO/WARN/ERROR) integrated + PROJECT_MAP.md finalized | ✅ DONE |
| M6 | Smoke test all 4 portals end-to-end + fix orphans | ✅ DONE |
| **S1** | Gaza seed data (governors + cities, Ar/En, consistent IDs) | ✅ DONE |
| **S2** | Family CRUD forms in admin portal (not reliant on starlette-admin) | ✅ DONE |
| **S3** | Structured family update request (JSON object, not text) | ✅ DONE |
| **S4** | Manager CRUD scoped to families in their shelter | ✅ DONE |
| **S5** | User management in admin portal | ✅ DONE |
| **R1** | Portal refactor: admin removed → starlette-admin, logger wired, shared utils, unit tests | ✅ DONE |

**Total delivered:** 12 milestones

---

## ORPHANS & PENDING

| Item | Status | Notes |
|------|--------|-------|
| Python 3.14.2 vs pyproject `>=3.14` | ✅ OK | venv confirmed 3.14.2 |
| `read_family` sync→async fix | ✅ DONE | Changed `def` to `async def` in families.py |
| `shelter_type_id` inconsistency | ✅ DONE | Removed from schema (no model field or table) |
| Portal login (staff + family) | ✅ DONE | Session-based, role-redirect; SUPERADMIN→/admin |
| Admin dashboard | ✅ DONE → MOVED | Portal admin removed; SUPERADMIN redirected to starlette-admin (/admin) |
| Manager dashboard | ✅ DONE | /portal/manager — family list + stats |
| BlockHeadPermission UI | ✅ DONE | /portal/manager/block-heads — toggle per block head |
| UpdateRequest model + review UI | ✅ DONE | /portal/manager/requests — approve/reject |
| Block head portal | ✅ DONE | /portal/block — block-scoped family list, permission-gated |
| Family portal | ✅ DONE | /portal/family — view record + submit UpdateRequest |
| Async logger | ✅ DONE | app/logging.py — stdout, INFO/WARN/ERROR |
| starlette-admin customizes password | ✅ OK | UserAdminView handles hash on create/edit |
| health endpoint is sync | ✅ OK | No DB call, fine |
| `require_role` doesn't scope BLOCK_HEAD to their block (API) | ⚠️ PENDING | Portal block-head route handles scope; API still unscoped |
| Gaza governors + cities seed | ✅ DONE | app/seed.py — 5 governors, 20 cities, 11 relationships, 3 qualities, consistent IDs |
| Family CRUD in manager portal | ✅ DONE | Create/edit/view/archive/restore + add/remove members |
| Family CRUD in admin portal | ✅ DONE | Same CRUD + user management (create/deactivate/activate) |
| Family structured update request | ✅ DONE | JSON object (phone, housing, residency) instead of raw text |
| Sidebar nav updated with CRUD links | ✅ DONE | Both admin and manager portals |
| Alembic migration for new models | ⚠️ PENDING | BlockHeadPermission + UpdateRequest tables exist via create_all but no migration revision |
| Logging not wired into all services | ✅ DONE | Logger imported and used in all services, admin.py, and portals |
| Member schema missing relationship_to_head_id | ✅ DONE | Added to MemberBase (fix pre-existing bug) |
| Family service model_dump bug | ✅ DONE | Excluded members from Family constructor (fix pre-existing bug) |
| Unit tests for all services | ✅ DONE | 33 tests across 4 modules (family, user, update_request, block_head), all passing |
| Shared `load_lookups` in common.py | ✅ DONE | Extracted from admin_portal + manager_portal to portals/common.py |

Build a full frontend for the displaced-camp management app in a new `frontend/` directory using **SolidJS + TanStack Router (file-based) + TanStack Query + Zod + UnoCSS**, on Vite + TypeScript.

## Setup

- `frontend/` package with: `solid-js`, `@tanstack/react-router` → solid equivalents (`@tanstack/router-plugin`, `@tanstack/solid-router`), `@tanstack/solid-query`, `zod`, `unocss`, `vite`, `typescript`.
- Vite dev proxy: `/api` → `http://localhost:8000` (avoids CORS in dev).
- Small backend change: add `CORSMiddleware` to `app/main.py` allowing the dev origin (needed if not proxying in prod).
- UnoCSS preset (`presetUno` + `presetAttributify` off for speed; `presetIcons` with a few iconify icons) — atomic CSS keeps the bundle tiny. Minimal custom theme (colors, fonts).

## Architecture

```
frontend/src/
  api/            # typed fetch client + per-resource functions (thin, returns parsed data)
  schemas/        # Zod schemas mirroring app/schemas/* (Family, Member, User, Lookups, Reports, enums, filters)
  queries/        # TanStack Query keys + hooks per resource (families, members, lookups, users, reports, update-requests, auth)
  i18n/           # lightweight custom dictionary (EN/AR JSON) + locale signal, no i18n lib
  auth/           # token store (signal + localStorage), JWT decode for role/family_id, route guards
  routes/         # TanStack Router file routes (see below)
  components/     # DataTable, Pagination, FilterBar, Modal, Drawer, FormField, Select (lookup-backed), Toast, StatusBadge, ConfirmDialog, LangToggle
  layouts/        # StaffLayout (sidebar nav), FamilyLayout, AuthLayout
```

- **Auth**: staff login (form-encoded `POST /auth/login`) and family login (national_id + DOB). Token in localStorage; a `beforeLoad` guard on route trees checks role from decoded JWT; redirect to login on 401 via a Query `onError` global handler. 30-min expiry — decode `exp` and auto-logout with a toast.
- **i18n/RTL**: locale signal (`en` | `ar`) persisted in localStorage, `document.dir` toggled, all labels from dictionaries; lookup names rendered via `name_en`/`name_ar` based on locale. Custom tiny t() — no dependency.
- **Zod**: every API response parsed through schemas; enums (Gender, MaritalStatus, HousingType, ResidencyStatus, UpdateRequestType, UserRole) defined once and reused for selects, filters, and display labels.
- **Lookups** (governors → cities → centers → blocks cascade, qualities, relationships) loaded via one query each, cached staleTime ∞, with dependent cascading selects (city filtered by governor, center by city, block by center).
- Forms: hand-rolled Solid forms with Zod validation (no form library) — keeps bundle small.

## Routes / features (staff portal — SUPERADMIN/MANAGER/BLOCK_HEAD see nav by role)

- `/login` — dual-mode staff login (username/password) + link to family login
- `/family-login` — national ID + date of birth
- `/` → redirect by role
- `/families` — paginated/filterable/sortable table: filters (residency, housing multi, centers, blocks, cities, female/child-headed, active, head name, phone), row → detail
- `/families/$id` — full detail: head/spouse, members table with health flags, family stats; edit (role-gated), archive/restore, add member, edit/delete member; national-ID client-side Luhn + first-digit validation
- `/families/new` — create family with nested members builder (head required, optional spouse)
- `/members` — global member search: all member filters (gender, marital multi, relation, DOB range, name, health flags), pagination, sorting; row links to family
- `/update-requests` — pending requests list; view payload JSON, approve / reject with confirm (BLOCK_HEAD/above)
- `/lookups` — SUPERADMIN: tabs for 6 lookup resources, CRUD with parent linkage
- `/reports` — families & members report tables with block filter, special-only toggle, column selection, CSV/JSON export (download link with auth header → fetch blob)
- `/users` — SUPERADMIN: list, create, edit, deactivate
- Family portal (`/me`, role FAMILY): view own family + members, submit update requests via typed forms — ADD_MEMBER (member form), CHANGE_HEAD (pick member), UPDATE_FAMILY_INFO, UPDATE_MEMBER_INFO — success shows request ID

## Implementation order

1. Scaffold (vite, packages, UnoCSS, router, query client, proxy)
2. Zod schemas + API client + auth store/guards
3. i18n + layouts + core components
4. Families list/detail/create/edit + members management
5. Update requests review + family portal
6. Lookups admin, users admin, reports + export
7. Polish: loading/error states, empty states, toasts, responsive + RTL verification

## Verification

`npm run build` clean (tsc + vite), dev server against the running FastAPI backend; smoke-test login, family list/detail, create family, update-request flow in both EN and RTL.

Fast/lightweight measures: no UI component library (hand-rolled UnoCSS-styled components), no form/i18n libraries, Zod schemas shared across query parsing + forms, code-split routes via TanStack Router file-based routing.
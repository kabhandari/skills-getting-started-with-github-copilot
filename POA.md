# Plan of Action — AHJ Configuration Worksheet V1 (Final)

**Project**: AHJ Config → Symbium Configs Worksheet
**Timeline**: 3 working days (Day 0 = this POA)
**Primary Users**: Symbium developers
**Secondary Users (near-term)**: Symbium product team

---

## Confirmed Assumptions

| # | Assumption |
|---|-----------|
| 1 | Schemas + validation + build logic packaged as `@symbium/config-engine` monorepo workspace. Both `Generate-Projects` scripts and `AHJ-Worksheet` consume the same package. Docker pulls required files from `Generate-Projects/` |
| 2 | Schema fields support a `hidden: true` key. Hidden fields are developer-only. V1 implements the "All Fields / Public Fields" toggle backed by this key |
| 3 | **MySQL** for persistence |
| 4 | Output is the **specifications folder** structure. Downstream `build-configs.js` and `generate` are separate steps |
| 5 | **S3** for document uploads in V1 |
| 6 | **Server-side validation** using existing `SchemaManager`. Client-side limited to basic UX hints |
| 7 | **Configuration states**: draft and published. Only published configs trigger a GitHub branch/push |
| 8 | **Unsaved changes** persist in localStorage until explicitly saved as draft or published |
| 9 | **JSON preview** restricted to Dev users only in V1 |
| 10 | **User access levels** (Dev, Product, City Official) designed into the data model now, enforced in V2 |
| 11 | No authentication for V1 — user selects their role manually. Auth enforced in V2 |

---

## Pipeline Context

```
                       ┌──────────────────────┐
                       │   AHJ Worksheet V1    │  ◄── THIS PROJECT
                       │  (replaces Airtable   │
                       │   + manual JSON)       │
                       └──────────┬─────────────┘
                                  │
                    User edits → saves as DRAFT (DB only)
                                  │
                    User PUBLISHES → branch created + pushed to GitHub
                                  │
                                  ▼
                    specifications/state_XX/city_XXXXXXX/
                    ├── city_XXXXXXX.json
                    ├── projects.json
                    ├── projects/*.json
                    └── scopes/*.json
                                  │
                                  │ consumed by (SEPARATE STEP)
                                  ▼
                    build-configs.js → built-configurations/
                                  │
                                  ▼
                    generate script → downstream repos
```

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              Data-Scripting (monorepo)               │
│                                                     │
│  ┌────────────────────────────────────────────────┐ │
│  │        @symbium/config-engine (workspace)      │ │
│  │  schema definitions + SchemaManager +          │ │
│  │  config-builder + config-validator             │ │
│  └──────────┬──────────────────────┬──────────────┘ │
│             │ require()            │ require()       │
│  ┌──────────▼──────────┐  ┌───────▼──────────────┐ │
│  │  Generate-Projects  │  │  AHJ-Worksheet       │ │
│  │  (existing scripts) │  │  (new app) ◄── V1    │ │
│  └─────────────────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│    AHJ-Worksheet (Docker container in production)    │
│                                                      │
│  ┌──────────────────────────────────────────────┐    │
│  │            React SPA (Frontend)               │    │
│  │  - Dynamic form from schema metadata          │    │
│  │  - localStorage for unsaved changes           │    │
│  │  - Draft / Publish workflow                   │    │
│  │  - Role selector (Dev / Product / City)       │    │
│  │  - JSON preview (Dev only)                    │    │
│  │  - Public / All Fields toggle (hidden key)    │    │
│  │  - Inline validation display                  │    │
│  │  - PDF upload to S3                           │    │
│  │  - AI rewrite suggest/accept/reject           │    │
│  └──────────────────┬───────────────────────────┘    │
│                     │ REST API                        │
│  ┌──────────────────▼───────────────────────────┐    │
│  │         Node.js / Express (Backend)           │    │
│  │  - @symbium/config-engine loaded at startup   │    │
│  │  - Serves serialized schema definitions       │    │
│  │  - Server-side validation (SchemaManager)     │    │
│  │  - CRUD with draft/published states (MySQL)   │    │
│  │  - Role-aware response filtering              │    │
│  │  - S3 upload for documents                    │    │
│  │  - Git branch + push on publish               │    │
│  │  - AI rewrite endpoint (OpenAI)               │    │
│  └──────────┬──────────┬───────────┬────────────┘    │
└─────────────│──────────│───────────│─────────────────┘
        ┌─────▼──┐  ┌────▼────┐ ┌───▼────┐
        │ MySQL  │  │  AWS S3  │ │ GitHub │
        │  (DB)  │  │  (docs)  │ │(branch)│
        └────────┘  └─────────┘ └────────┘
```

---

## Monorepo & Config Engine Package

### Why a shared package

The schema definitions, `SchemaManager`, `config-builder`, and `config-validator` are tightly coupled — a new field comes with its validator, calculator, and dependencies. They must be versioned as a single unit. Both the existing `Generate-Projects` scripts and the new `AHJ-Worksheet` app need them.

Packaging them as a **monorepo workspace** (`@symbium/config-engine`) means both consumers resolve to the same local code — no publishing, no duplication, always in sync.

### Package boundary

**Inside `@symbium/config-engine`** (everything needed to define, validate, and build a configuration):

```
Generate-Projects/config-engine/           ← workspace package
├── package.json                           ← name: @symbium/config-engine
├── schema-classes.js                      ← SchemaManager, ValidationError, TypeValidators
├── lib/
│   └── utilities.js                       ← load_json, discover_json_files
├── schema/
│   ├── index.js                           ← main entry point (re-exports all)
│   ├── schema-manager-instance.js         ← builds SchemaManager, loads specs
│   ├── config-builder.js                  ← buildFromInputs, buildFromDirectory
│   ├── config-validator.js                ← validateFromInputs, validateFromDirectory
│   ├── utils.js                           ← shared helpers
│   └── specifications/                    ← schema definitions
│       ├── state.js
│       ├── jurisdiction.js
│       ├── projects/*.js
│       └── scopes/*.js
└── CHANGELOG.md
```

**Outside the package** (consumers / pipeline-specific):

```
Generate-Projects/
├── validators/          ← downstream pipeline validators (ahj.js, pv_ess.js)
├── builders/            ← downstream pipeline builders (symbium.js, api.js)
├── specifications/      ← actual jurisdiction config data files
├── built-configurations/← generated output
└── lib/specification_compiler.js
```

### Monorepo workspace setup

```
Data-Scripting/                          ← repo root
├── package.json                         ← workspaces: ["Generate-Projects/config-engine", "AHJ-Worksheet"]
├── Generate-Projects/
│   ├── config-engine/                   ← @symbium/config-engine workspace
│   │   └── (schema + validation + build logic)
│   ├── validators/
│   ├── builders/
│   ├── specifications/
│   └── (existing scripts reference @symbium/config-engine)
└── AHJ-Worksheet/                       ← worksheet app workspace
    ├── package.json                     ← depends on @symbium/config-engine
    ├── server/
    └── client/
```

Root `package.json`:

```json
{
  "private": true,
  "workspaces": [
    "Generate-Projects/config-engine",
    "AHJ-Worksheet"
  ]
}
```

`Generate-Projects/config-engine/package.json`:

```json
{
  "name": "@symbium/config-engine",
  "version": "1.0.0",
  "main": "schema/index.js",
  "dependencies": {
    "lodash": "^4.17.21",
    "glob": "^10.0.0"
  }
}
```

`AHJ-Worksheet/package.json`:

```json
{
  "dependencies": {
    "@symbium/config-engine": "*"
  }
}
```

Both consumers use the exact same import:

```javascript
const {
    schemaManager, schemaList,
    validateFromInputs, buildFromInputs,
    SchemaManager, ValidationError,
} = require('@symbium/config-engine');
```

### Docker deployment

The AHJ-Worksheet Dockerfile pulls only what it needs from the repo:

```dockerfile
FROM node:20-alpine

WORKDIR /app

# Copy root workspace config
COPY package.json package-lock.json ./

# Copy the config-engine package
COPY Generate-Projects/config-engine/ ./Generate-Projects/config-engine/

# Copy the worksheet app
COPY AHJ-Worksheet/ ./AHJ-Worksheet/

# Install all workspaces
RUN npm ci --workspaces

WORKDIR /app/AHJ-Worksheet

EXPOSE 3000
CMD ["node", "server/index.js"]
```

The image contains only `config-engine/` and `AHJ-Worksheet/` — not the full `Generate-Projects/` tree (no `validators/`, `builders/`, `specifications/`, `built-configurations/`).

### Schema version tracking

`schema_version` in the DB maps to the `version` field in `config-engine/package.json`. When schemas change:

1. Dev modifies schema files inside `config-engine/`
2. Bumps `version` in `config-engine/package.json` (patch = constraints, minor = new fields, major = renames)
3. Both `Generate-Projects` and `AHJ-Worksheet` immediately see the change (monorepo)
4. New configurations saved in the DB record `schema_version: "1.1.0"`
5. V2 migration tooling can compare schema versions to detect field additions/renames

---

## Schema Visibility — Hidden Fields

### Design

Schema fields can declare `hidden: true` to indicate they are developer-only (computed, internal, or not relevant to product/city workflows):

```javascript
// In jurisdiction.js
"jurisdiction_keyword": {
    "required": true,
    "type": "string",
    "hidden": true,
    "dependencies": ["symbium_config.jurisdiction_name_short"],
    "calculator": function(config,_) {
        return config.symbium_config.jurisdiction_name_short.toLowerCase().replace(/[^a-z]+/g,"_")
    },
    "explanation": "calculated from jurisdiction_name_short"
},
```

Fields without `hidden` or with `hidden: false` are public.

### Frontend behavior

A toggle in the worksheet header switches between two views:

| View | Fields shown | Default for role |
|------|-------------|-----------------|
| **Public Fields** | Only fields where `hidden !== true` | Product, City Official |
| **All Fields** | Every field in the schema | Dev |

The toggle is available to all roles but the **default view** is role-dependent. Devs default to "All Fields", others default to "Public Fields".

### Serialization

The `GET /api/schemas` endpoint includes the `hidden` flag in serialized output:

```javascript
serialized[path] = {
    type: def.type,
    required: ...,
    hidden: def.hidden || false,   // ◄── included
    explanation: def.explanation || null,
    // ...
};
```

The frontend filters fields based on the toggle state:

```javascript
const visibleFields = Object.entries(schema.fields).filter(
    ([key, def]) => showAllFields || !def.hidden
);
```

### Hidden fields still validate and compute

Hidden fields are excluded from the **UI** only, not from validation or building. Server-side, `SchemaManager` processes all fields regardless of `hidden`. Calculators and validators for hidden fields run normally — the user just doesn't see or edit them.

---

## Configuration Lifecycle

```
┌───────────┐      ┌───────────┐      ┌───────────────┐
│ UNSAVED   │      │  DRAFT    │      │  PUBLISHED    │
│ (browser  │─────►│ (MySQL,   │─────►│ (MySQL +      │
│ localStorage)│   │  not on   │      │  GitHub       │
│           │      │  GitHub)  │      │  branch)      │
└───────────┘      └───────────┘      └───────────────┘
     │                  │                    │
  User edits       Save Draft            Publish
  form fields      (POST/PUT)         (PUT status)
                                           │
                                    Creates branch:
                              config/{jurisdiction_id}/{YYYYMMDD}
                                    Pushes spec files
                                    Returns branch URL
```

**Key rules:**
- Unsaved edits live in **localStorage** only — survives page refresh, lost on clear
- **Save as Draft** → persists to MySQL with `status: "draft"`. No GitHub action.
- **Publish** → updates status to `"published"` in MySQL. Creates a git branch with predefined naming convention and pushes specification files. Only published configurations exist on GitHub.
- User can go back to draft (edit a published config → save as draft → re-publish later)
- **Version history**: each publish creates a new version record, so prior published states are preserved

---

## User Access Levels

Designed into the data model and API now. V1 uses a manual role selector (no auth). V2 enforces via authentication.

| Role | V1 Capabilities | V2 Additions |
|------|----------------|-------------|
| **Dev** | All fields visible, JSON preview, validate, save draft, publish, create branch, see all configs | Full admin |
| **Product** | All fields visible (public-keys view as default, can toggle), validate, save draft. No JSON preview, no publish, no branch creation | Auth-gated, limited publish |
| **City Official** | Public-keys view only, edit instructional text + upload docs, save draft only | Auth (magic link / Cognito), own jurisdiction only |

### V1 Implementation
- Frontend has a **role selector** in the header (dropdown: Dev / Product Team)
- City Official role not active in V1 but exists in the DB schema
- API responses include a `role` parameter; backend filters capabilities:
  - `GET /api/configurations/:id/preview` → returns generated JSON → **404 unless role=dev**
  - `POST /api/configurations/:id/publish` → **403 unless role=dev**
- Role is passed as a header (`X-User-Role`) in V1. Replaced by auth token in V2.

### DB Design for Access Levels

```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) UNIQUE,
    name VARCHAR(255) NOT NULL,
    role ENUM('dev', 'product', 'city_official') NOT NULL DEFAULT 'product',
    jurisdiction_id VARCHAR(20) NULL,     -- only for city_official, restricts access
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

V1: No auth. The role selector sets `X-User-Role` header. The `users` table exists but isn't actively enforced.
V2: Auth middleware reads the token, looks up the user, enforces role-based access.

---

## Persistence Model (MySQL)

```sql
CREATE TABLE configurations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    jurisdiction_id VARCHAR(20) NOT NULL,
    state_id VARCHAR(10) NOT NULL DEFAULT 'state_06',
    schema_version VARCHAR(20) NOT NULL DEFAULT '1.0.0',  -- matches @symbium/config-engine version
    status ENUM('draft', 'published') NOT NULL DEFAULT 'draft',
    version INT NOT NULL DEFAULT 1,
    jurisdiction_data JSON NOT NULL,
    projects_list JSON NOT NULL,
    published_at TIMESTAMP NULL,
    published_by VARCHAR(255) NULL,
    branch_name VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_jurisdiction_version (jurisdiction_id, version)
);

CREATE TABLE project_configs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    configuration_id INT NOT NULL,
    project_type VARCHAR(50) NOT NULL,
    project_data JSON NOT NULL,
    UNIQUE KEY uq_config_project (configuration_id, project_type),
    FOREIGN KEY (configuration_id) REFERENCES configurations(id) ON DELETE CASCADE
);

CREATE TABLE scope_configs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    configuration_id INT NOT NULL,
    scope_type VARCHAR(50) NOT NULL,
    scope_data JSON NOT NULL,
    UNIQUE KEY uq_config_scope (configuration_id, scope_type),
    FOREIGN KEY (configuration_id) REFERENCES configurations(id) ON DELETE CASCADE
);

CREATE TABLE documents (
    id INT PRIMARY KEY AUTO_INCREMENT,
    configuration_id INT NOT NULL,
    field_key VARCHAR(100) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    s3_key VARCHAR(500) NOT NULL,
    s3_url VARCHAR(500) NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (configuration_id) REFERENCES configurations(id) ON DELETE CASCADE
);

CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) UNIQUE,
    name VARCHAR(255) NOT NULL,
    role ENUM('dev', 'product', 'city_official') NOT NULL DEFAULT 'product',
    jurisdiction_id VARCHAR(20) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Version History

When a user publishes, the current config is frozen as a version:
- `version` increments (1, 2, 3...)
- `status` set to `"published"`, `published_at` timestamped, `branch_name` recorded
- If user wants to edit after publish → a new row is created with `version+1`, `status: "draft"`, copying the data

This preserves every published snapshot.

---

## localStorage Strategy

**What is stored**: The current in-progress form state for each jurisdiction being edited.

```javascript
// Key format
`worksheet_draft_{jurisdiction_id}`

// Value format
{
  "jurisdiction_data": { ... },
  "projects_list": ["pv_ess"],
  "project_configs": { "pv_ess": { ... } },
  "scope_configs": { "pv_ess": { ... } },
  "lastModified": "2026-03-10T14:30:00Z"
}
```

**Lifecycle:**
1. User opens a config (new or existing) → form populated from DB (or empty)
2. Every form edit → **auto-saved to localStorage** (debounced, ~500ms)
3. User navigates away / refreshes → form state restored from localStorage
4. User clicks **Save Draft** → POST to backend → saved to MySQL → localStorage cleared
5. User clicks **Publish** → PUT to backend → saved to MySQL as published → branch created → localStorage cleared
6. If user opens a config that has localStorage data newer than DB data → prompt: "You have unsaved changes. Resume editing or discard?"

---

## GitHub Branch Strategy

### Branch Naming Convention

```
config/{jurisdiction_id}/{YYYYMMDD}
```

Examples:
- `config/city_0656938/20260310`
- `config/city_0665000/20260312`

If a branch for the same jurisdiction + date already exists, append a sequence number:
- `config/city_0656938/20260310-2`

### Publish Flow

1. User clicks **Publish** (Dev role only)
2. Backend validates the configuration (blocks if errors)
3. Status updated to `"published"` in MySQL
4. New branch created from `main`: `config/{jurisdiction_id}/{YYYYMMDD}`
5. Specification files written:
   ```
   Generate-Projects/specifications/{state_id}/{jurisdiction_id}/
   ├── {jurisdiction_id}.json
   ├── projects.json
   ├── projects/{type}.json
   └── scopes/{type}.json
   ```
6. Commit message: `config: update {jurisdiction_id} specifications`
7. Branch pushed to origin
8. `branch_name` stored in the configuration record
9. Branch URL returned to frontend and displayed

**No PR is auto-created** — the dev reviews the branch and creates a PR when ready. (This avoids noise from multiple publishes.)

---

## API Endpoints

| Method | Endpoint | Purpose | Role |
|--------|---------|---------|------|
| `GET` | `/api/schemas` | Serialized schema metadata | All |
| `GET` | `/api/schemas/:name` | Single schema definition | All |
| `GET` | `/api/configurations` | List all configs (with status filter) | All |
| `POST` | `/api/configurations` | Create new config (draft) | All |
| `GET` | `/api/configurations/:id` | Get config with projects/scopes | All |
| `PUT` | `/api/configurations/:id` | Update config (save draft) | All |
| `DELETE` | `/api/configurations/:id` | Delete config | Dev |
| `POST` | `/api/validate` | Server-side validation | All |
| `GET` | `/api/configurations/:id/preview` | Preview generated JSON output | **Dev only** |
| `POST` | `/api/configurations/:id/publish` | Publish → MySQL + GitHub branch | **Dev only** |
| `GET` | `/api/configurations/:id/versions` | Version history | All |
| `POST` | `/api/upload` | Upload PDF to S3 | All |
| `POST` | `/api/ai/rewrite` | AI rewrite suggestion | All |

---

## Schema → UI Component Mapping

| Schema `type` | UI Component |
|--------------|-------------|
| `string` | Text input; multiline for HTML content fields |
| `string` + `subtype: "url"` | URL input with format hint |
| `string` + `subtype: "email"` | Email input with format hint |
| `number` / `integer` | Number input |
| `boolean` | Toggle switch |
| `domain` (static array) | Select dropdown |
| `domain` (dynamic function) | Select dropdown, options resolved server-side |
| `array` + `subtype: "string"` | Tag/chip input |
| `array` + `subtype: "domain"` | Multi-select checkboxes |
| `array` + `subtype: "object"` | Repeatable nested form group |
| `object` with `properties` | Collapsible nested form section |
| Fields with `calculator` | Read-only computed field |

---

## Validation Strategy

| Layer | Responsibility |
|-------|---------------|
| **Client-side** (UX hints) | Instant: empty required fields, wrong input type, static domain, URL/email format |
| **Server-side** (real validation) | Full: `SchemaManager.validateConfigs()` with custom validators, cross-field deps, cross-schema refs, calculators |

Validation required before publish. Draft can be saved with validation errors.

---

## Day-by-Day Timeline

### Day 1 — Foundation: Monorepo + Backend + Schema API + DB + Validation

| Task | Description | Est. |
|------|------------|------|
| 1.1 | **Monorepo & config-engine setup** — Create root `package.json` with workspaces. Extract `config-engine/` package from existing `schema/`, `schema-classes.js`, and `lib/utilities.js`. Update `require()` paths in existing Generate-Projects scripts. Verify existing scripts still work. Dockerfile for AHJ-Worksheet | 1.5h |
| 1.2 | **Project scaffolding** — Express backend + React/Vite frontend under `AHJ-Worksheet/`, depends on `@symbium/config-engine`, dev scripts, MySQL connection setup | 1h |
| 1.3 | **Schema serialization API** — `GET /api/schemas` loads `@symbium/config-engine`, serializes to JSON metadata (types, static defaults, domains, explanations, `hidden` flag; marks dynamic fields). `GET /api/schemas/:name` for individual. Filters hidden fields based on role/toggle | 1.5h |
| 1.4 | **MySQL setup + CRUD** — migration scripts for all tables (configurations, project_configs, scope_configs, documents, users), CRUD endpoints with `status` (draft/published), `version`, and `schema_version` (from config-engine package version) | 2h |
| 1.5 | **Validation endpoint** — `POST /api/validate` calls `buildFromInputs()` + `validateConfigs()` from `@symbium/config-engine`, returns structured errors. Role-aware JSON preview endpoint `GET /api/configurations/:id/preview` (Dev only) | 1.5h |
| 1.6 | **Export/Publish endpoint** — `POST /api/configurations/:id/publish` validates → updates status → creates branch `config/{jurisdiction_id}/{YYYYMMDD}` → pushes spec files → returns branch URL | 1.5h |

**Day 1 Deliverable**: Monorepo with `@symbium/config-engine` workspace. Working backend — serves schemas (with hidden flag), persists to MySQL with draft/published states and schema versioning, validates via SchemaManager, publishes to GitHub branch. Dockerfile ready.

---

### Day 2 — Frontend: Form + Lifecycle + Document Upload

| Task | Description | Est. |
|------|------------|------|
| 2.1 | **Dashboard page** — list all jurisdictions (filterable by status: draft/published), search, "Create New" button, role selector in header | 1.5h |
| 2.2 | **Dynamic form renderer** — schema-driven form fields, grouped by section, help text from `explanation`, localStorage auto-save on every edit (debounced), restore prompt on load | 3h |
| 2.3 | **Project/scope management** — multi-select project types, auto-resolve default scopes, tabs for project/scope config forms | 1h |
| 2.4 | **Draft/Publish workflow** — "Save Draft" button (always available), "Publish" button (Dev only, requires passing validation), status badge on dashboard, version history panel | 1.5h |
| 2.5 | **S3 document upload** — drag-and-drop PDF upload, backend upload to S3, display uploaded doc links in form, wire into config fields | 1h |

**Day 2 Deliverable**: Functional worksheet UI — role-aware, localStorage persistence, draft/publish workflow, document uploads.

---

### Day 3 — Integration, Polish, Seed Data

| Task | Description | Est. |
|------|------------|------|
| 3.1 | **Validation UI** — validate button, inline errors per field, summary panel, must-pass gate before publish | 1h |
| 3.2 | **JSON preview** — Dev-only panel showing generated specification JSON, toggle to view/hide | 0.5h |
| 3.3 | **AI rewrite integration** — endpoint + UI for instructional text fields, suggest/accept/reject | 1.5h |
| 3.4 | **Schema visibility toggle** — "All Fields" / "Public Fields" toggle. Filters fields by `hidden` key from schema. Default view is role-dependent: Dev → All Fields, Product → Public Fields. Toggle available to all roles | 1h |
| 3.5 | **Seed existing configs** — script to import existing `specifications/` folder data into MySQL so all current jurisdictions are browsable | 1h |
| 3.6 | **End-to-end testing** — create jurisdiction, add projects/scopes, upload docs, validate, save draft, publish, verify branch on GitHub | 1.5h |
| 3.7 | **Polish** — error handling, loading states, toast notifications, responsive layout, README with setup instructions | 2h |

**Day 3 Deliverable**: Complete V1 — developer opens worksheet, configures jurisdiction, saves drafts, publishes, and specification files land on a GitHub branch.

---

## Success Criteria Verification

| # | Criteria | How Met |
|---|---------|---------|
| 1 | Open the worksheet | React SPA, dashboard lists all jurisdictions with status badges |
| 2 | Toggle between public-key and full-schema view | UI toggle filters by `hidden` key in schema. Dev defaults to All Fields, Product defaults to Public Fields |
| 3 | Create or edit jurisdiction configuration | Dynamic form, MySQL persistence, draft/publish states, localStorage for unsaved edits |
| 4 | Upload required jurisdiction document templates (PDFs) | S3 upload, URL stored in config |
| 5 | Run schema validation | Server-side `SchemaManager.validateConfigs()`, errors inline + summary |
| 6 | Build valid configurations | Dev-only JSON preview of generated specification files |
| 7 | Generate deployments using automation workflow | Publish creates branch `config/{jurisdiction_id}/{YYYYMMDD}`, pushes spec files; downstream scripts consume unchanged |

---

## Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Monorepo | npm workspaces | `@symbium/config-engine` shared between Generate-Projects and AHJ-Worksheet |
| Frontend | React + Vite + Tailwind CSS | Fast dev, dynamic forms, clean UI |
| Backend | Node.js + Express | Same runtime as schema code, `require('@symbium/config-engine')` |
| Database | **MySQL** | Per requirement, supports version history, role-based queries |
| Container | Docker | Dockerfile copies only `config-engine/` + `AHJ-Worksheet/` from repo for standalone deployment |
| File Storage | AWS S3 | Documents in S3 from V1 |
| Validation | Server-side SchemaManager | `@symbium/config-engine` reused, no duplication |
| Git | `gh` CLI or `@octokit/rest` | Branch creation + push on publish |
| AI Rewrite | OpenAI API | Instructional text rewriting |
| Client Storage | localStorage | Unsaved form edits persist across refresh |

---

## Out of Scope for V1

- Authentication / authorization enforcement (V2 — designed into DB now)
- City Official role active usage (V2)
- Schema migration tooling (storing `schema_version` from `@symbium/config-engine` package version; migration logic is V2)
- Publishing `@symbium/config-engine` to npm registry (monorepo workspace is sufficient for V1; publish to GitHub Packages in V2 if the worksheet is extracted to its own repo)
- Auto-creating PRs (dev creates PR manually from the pushed branch)
- Running `build-configs.js` or `generate` from the worksheet

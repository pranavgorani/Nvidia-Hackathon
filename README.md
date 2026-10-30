# DocuFlow AI Agent OS — SaaS2Agent Hackathon Project (PS 2)

**DocuFlow AI Agent OS** is an enterprise AI SaaS agent operating system that converts business documents and user instructions into verified business operations through AI agents, CRM tools, workflow automation, human approvals, and immutable audit logs.

---

## 🏆 Hackathon Technology & Provider Disclosure

> [!IMPORTANT]
> **AI Inference Provider:** This application is integrated with the official **Google Gemini API** (`google_gemini`) using the official **Google Gen AI Python SDK** (`google-genai`).
>
> Legacy inference endpoints (e.g., NVIDIA Nemotron via Nebius Token Factory) have been replaced with the Google Gemini API architecture.
> All API credentials are kept strictly server-side in backend environment variables and are **never** exposed to the frontend or browser.

---

## 🏗 Architecture Overview

```
DocuFlow AI Agent OS/
├── backend/
│   ├── app/
│   │   ├── api/            # REST API endpoints (Auth, CRM, Documents, Agent, Approvals, Skills, Audit)
│   │   ├── core/           # Security (JWT, bcrypt, SHA-256 payload hashing), Database, Configuration
│   │   ├── db/             # SQLAlchemy ORM models & database seeding
│   │   ├── providers/      # Google Gemini AI Provider (google-genai SDK, structured output, tool calls)
│   │   ├── services/       # CRM, Document Intelligence (pypdf text & OCR), Approvals, Audit
│   │   ├── tools/          # Registered typed business tools (Strict allowlist & Pydantic schemas)
│   │   ├── skills/         # Property Intake Agent (11-step signature skill) & skills registry
│   │   ├── agent/          # State machine orchestrator & turn-based execution
│   │   └── main.py         # FastAPI application entrypoint with CORS & lifespan handlers
│   ├── tests/              # Pytest test suite (13 automated unit, integration, and security tests)
│   └── pyproject.toml      # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── app/            # Next.js App Router (Dashboard, Workspace, CRM, Documents, Approvals, Skills, etc.)
│   │   ├── components/     # UI components (Sidebar, Header)
│   │   └── lib/            # Type-safe API client
│   └── package.json        # Next.js, React, Tailwind CSS, Lucide icons
├── storage/uploads/        # Secure opaque storage for uploaded inquiry files
├── .env.example            # Environment configuration template
└── README.md
```

---

## 🚀 Key Features

1. **Google Gemini Integration (`google-genai`):**
   - Configurable model identifier (e.g. `gemini-2.5-flash`).
   - Strict server-side credential isolation (`GEMINI_API_KEY`).
   - Zero-trust tool execution: `automatic_function_calling(disable=True)`. Model proposals are intercepted, validated against a strict backend allowlist, and executed by authorized backend services.
   - Pydantic structured output validation for schema extraction.

2. **Signature Skill: Property Intake Agent (v1.0.0):**
   - **Step 1:** Resolve document & verify permissions.
   - **Step 2-3:** Ingest PDF/Image and extract text & structured fields with source snippets and confidence heuristics.
   - **Step 4:** Review extraction quality and flag missing required fields.
   - **Step 5:** Multi-criteria CRM contact and lead deduplication (exact email, normalized phone, fuzzy name).
   - **Step 6:** Propose verified CRM mutation (`create_lead` or `update_lead`).
   - **Step 7-8:** Enforce policy and bind proposal to human approval with cryptographic SHA-256 payload hash.
   - **Step 9:** Execute approved action atomically via CRM services with idempotency protection.
   - **Step 10-11:** Verify database persistence and record append-only audit trail.

3. **Human Approval Center:**
   - Cryptographically binds approvals to exact proposed actions and payload hashes.
   - Detects and rejects payload tampering or replayed approvals.
   - Role-based permissions (Manager, Admin, Owner).

4. **Multi-Tenant SaaS Foundation:**
   - Role-based access control (Owner, Admin, Manager, Agent, Viewer).
   - Strict organization-scoped database queries (`organization_id`).

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env`:

```env
# AI Provider Configuration
AI_PROVIDER=google_gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# Backend Configuration
APP_ENV=development
APP_SECRET_KEY=docuflow_super_secret_enterprise_agent_os_key_2026_safe
ACCESS_TOKEN_EXPIRE_MINUTES=1440
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Database & Storage
DATABASE_URL=sqlite+aiosqlite:///./docuflow.db
STORAGE_PATH=./storage/uploads
MAX_UPLOAD_SIZE_MB=25

# Agent Policies
MAX_AGENT_TURNS=15
TOOL_EXECUTION_TIMEOUT_SECONDS=45
REQUIRE_APPROVAL_FOR_WRITES=true
APPROVAL_EXPIRY_HOURS=24
```

---

## 💻 Local Setup & Running Instructions

### Prerequisites
- Python 3.11+ (or `uv`)
- Node.js 18+ and `npm`

### 1. Start the FastAPI Backend
```bash
cd backend

# Using uv
$env:UV_LINK_MODE="copy" # (For Windows/OneDrive)
uv run --link-mode=copy uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The backend API is now running at `http://localhost:8000` (Interactive Swagger Docs at `http://localhost:8000/docs`).

### 2. Start the Next.js Frontend
```bash
cd frontend
npm.cmd install
npm.cmd run dev
```
Open `http://localhost:3000` to access the DocuFlow SaaS dashboard.

---

## 🧪 Running Automated Tests

Run the full pytest suite (covering Gemini integration, authentication, multi-tenant isolation, CRM operations, tool allowlist enforcement, approval tamper detection, and the end-to-end Property Intake workflow):

```bash
cd backend
$env:UV_LINK_MODE="copy"
uv run --link-mode=copy --extra dev pytest tests -v
```

All 13 tests execute with 100% pass rate.

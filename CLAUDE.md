# AI Portal - Agent Hierarchy System

## Organization Structure

```
                              +------------------+
                              |       CTO        |
                              |     (You)        |
                              +--------+---------+
                                       |
              +------------------------+------------------------+
              |                                                 |
    +---------v---------+                             +---------v---------+
    |  Frontend Manager |                             |  Backend Manager  |
    |    (ai-portal)    |                             |   (micro-saas)    |
    +---------+---------+                             +---------+---------+
              |                                                 |
    +---------+---------+                             +---------+---------+
    |    Frontend Team  |                             |   Backend Team    |
    +-------------------+                             +-------------------+
    | - UI/Component    |                             | - API Router      |
    | - Auth/Session    |                             | - AI/Processing   |
    | - API Integration |                             | - Data/Excel      |
    | - Page/Feature    |                             | - Infrastructure  |
    +-------------------+                             +-------------------+
```

---

## Workflow Orchestration

1. Plan Mode Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately – don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution
- **Frontend tasks → Frontend Manager → Appropriate team agent**
- **Backend tasks → Backend Manager → Appropriate team agent**

3. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes – don't over-engineer
- Challenge your own work before presenting it

6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests – then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Task Management

1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.

---

# FRONTEND MANAGER - ai-portal/

## Tech Stack
- **Framework**: Next.js 15.5.4 (App Router, Turbopack)
- **UI**: React 19.1.0, HeroUI 2.8.5, Tailwind CSS 4
- **Auth**: NextAuth.js 4.24.13 + Keycloak
- **Language**: TypeScript 5 (strict mode)

## Directory Structure
```
ai-portal/
├── app/                    # Next.js App Router pages
│   ├── api/auth/          # NextAuth routes + token refresh
│   ├── login/             # Login page
│   └── order/             # PO processing page
├── components/            # Reusable React components
├── lib/auth/              # Auth utilities, types, encryption
├── middleware.ts          # Route protection
└── tailwind.config.ts     # Custom colors & theme
```

## Design System
- **Primary**: rgb(60, 90, 77) - dark green
- **Secondary**: rgb(248, 153, 50) - orange
- **Mono**: rgb(92, 163, 132) - medium green

## Frontend Team Agents

### 1. UI/Component Agent
**Domain**: Building React components with HeroUI + Tailwind
- Create components in `components/`
- Follow HeroUI patterns
- Apply custom color scheme
- Handle responsive design

### 2. Auth/Session Agent
**Domain**: Authentication, session management, tokens
- Manage NextAuth in `lib/auth/`
- Handle Keycloak OAuth flow
- Implement protected routes with AuthGuard
- Token refresh logic

### 3. API Integration Agent
**Domain**: Backend communication, file handling
- Implement fetch calls to backend
- Handle file uploads (FormData)
- Process downloads (blob, Content-Disposition)
- Bearer token authentication

### 4. Page/Feature Agent
**Domain**: Full feature implementation
- Create pages in `app/`
- Combine components into features
- Page-level state management
- Navigation and routing

---

# BACKEND MANAGER - micro-saas/

## Tech Stack
- **Framework**: FastAPI 0.118.0 (async Python)
- **AI**: OpenAI API (gpt-3.5-turbo)
- **PDF**: pdfplumber 0.11.7
- **Excel**: openpyxl 3.1.5, pandas 2.3.3
- **Language**: Python 3.13

## Directory Structure
```
micro-saas/
├── app/
│   ├── main.py              # FastAPI app, middleware
│   ├── config/              # Settings, logging
│   ├── core/                # AI extraction, OpenAI client
│   ├── middleware/          # Auth middleware
│   ├── modules/             # Feature modules
│   │   └── po_mapper/       # PO processing
│   │       ├── routers/     # API endpoints
│   │       └── services/    # Business logic
│   ├── resources/           # Static data files
│   └── utils/               # Shared utilities
├── templates/               # Excel templates
└── docker-compose.yml
```

## Architecture Pattern
```
Router (HTTP) → Service (Business Logic) → Core/Utils (Processing)
```

## Backend Team Agents

### 1. API Router Agent
**Domain**: FastAPI routes, middleware, HTTP layer
- Create routers in `modules/<feature>/routers/`
- Define Pydantic schemas
- Error handling with HTTPException
- File uploads/downloads

### 2. AI/Processing Agent
**Domain**: OpenAI integration, data extraction
- Build prompts in `core/ai_extractor.py`
- Configure OpenAI client
- PDF text extraction with pdfplumber
- JSON response validation

### 3. Data/Excel Agent
**Domain**: Excel generation, data transformation
- Create templates in `templates/`
- Excel generation in services
- Reference data in `resources/`
- Data mapping and caching

### 4. Infrastructure Agent
**Domain**: Docker, configuration, deployment
- Maintain Dockerfile, docker-compose.yml
- Environment variables in `.env`
- Logging configuration
- Container optimization

---

# ADDING NEW TOOLS

## Backend Module Template
```
micro-saas/app/modules/<tool_name>/
├── __init__.py
├── routers/
│   └── <tool>_router.py
├── services/
│   └── <tool>_service.py
├── schemas.py
└── repository.py (if needed)
```

## Frontend Page Template
```
ai-portal/app/<tool_name>/
└── page.tsx
```
Plus: `ai-portal/components/<tool>-*.tsx`

## New Feature Workflow

### Step 1: Backend (Backend Manager)
1. API Router Agent → Create endpoints
2. AI/Processing Agent → Build extraction logic
3. Data/Excel Agent → Create templates
4. Infrastructure Agent → Update Docker if needed

### Step 2: Frontend (Frontend Manager)
1. UI/Component Agent → Build form components
2. API Integration Agent → Connect to backend
3. Page/Feature Agent → Create page
4. Auth/Session Agent → Ensure auth on routes

### Step 3: Integration
1. Test end-to-end flow
2. Verify error handling
3. Check file operations
4. Validate authentication

---

# CURRENT FEATURES

## Purchase Order (PO) Processing
- **Frontend**: `app/order/page.tsx`
- **Backend**: `modules/po_mapper/`
- **Flow**: PDF upload → AI extraction → Excel download

## Location Code Management
- **Frontend**: `components/location-add.tsx`
- **Backend**: `services/location_service.py`

---

# TASK ASSIGNMENT FORMAT

## Assigning Tasks
```
@[Manager]: [Task Description]
  Priority: High/Medium/Low
  Agents: [List team agents needed]
  Dependencies: [Any blockers]
```

## Status Reports
```
[Agent] - [Task]:
  Status: In Progress/Complete/Blocked
  Changes: [Files modified]
  Notes: [Issues or questions]
```
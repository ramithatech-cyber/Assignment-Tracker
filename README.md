# Student Assignment Tracker

Students submit a GitHub repository link and get back an AI-assisted code review. The backend downloads the repo, runs real static-analysis tools on it, gives the measured facts plus the key source files to OpenAI, and returns a structured report:

- **what's good**
- **what needs improvement**
- a **score out of 100** across a seven-part rubric

Teachers create assignments, see every submission with its score, and follow each student's progress through a 45-day daily activity programme.

## Features

- **Repository review:** download the repo, run static analysis and an OpenAI structured-output review, then score it
- **Evidence-capped scoring:** deterministic caps (no tests, no README, committed secrets, weak git history…) that the model cannot override, each shown to the student with its reason
- **45-day activity programme:** students log one entry per day; days are date-locked and enforced server-side, with an automatic weekly rollup
- **Teacher dashboard:**
  - Class overview and per-student performance levels
  - Per-student review pages with an on-demand AI "overall remark", cached and flagged when out of date
- **Role-based access:**
  - A student can only see their own submissions; a teacher can only see submissions on their own assignments
  - Admin accounts can only be created with the staff signup code (`ADMIN_SIGNUP_CODE`), checked on the server

## Tech stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, React Router |
| Backend | FastAPI, SQLModel (SQLite locally, Postgres in production), JWT auth, slowapi rate limiting |
| Analysis | ruff, radon, ESLint (when available), GitHub REST API |
| AI review | OpenAI structured outputs |
| Tests | pytest (LLM and network calls stubbed) |

## Getting started

### Prerequisites

- Python 3.10+
- Node.js 18+
- An OpenAI API key

### 1. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

copy .env.example .env              # macOS/Linux: cp .env.example .env
# edit .env and set OPENAI_API_KEY, JWT_SECRET and ADMIN_SIGNUP_CODE

python -m uvicorn app.main:app --reload
```

- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/health

### 2. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api` to port 8000, so you don't need any CORS setup for local development.

## Configuration

Backend settings are read from `backend/.env` (see `backend/.env.example`):

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `OPENAI_API_KEY` | **yes** | none | Submissions fail without it |
| `JWT_SECRET` | **yes** in production | insecure dev value | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ADMIN_SIGNUP_CODE` | **yes** for admin accounts | empty (admin signup disabled) | Shared secret staff must enter to create an admin account. Share it only with staff |
| `OPENAI_MODEL` | no | `gpt-4.1` | Any model that supports structured outputs |
| `GITHUB_TOKEN` | no | none | Raises the GitHub API limit from 60/hr to 5000/hr; a no-scope classic token is enough |
| `DATABASE_URL` | no | `sqlite:///./assignment_tracker.db` | Use `postgresql+psycopg://…` in production |
| `CORS_ORIGINS` | no | `http://localhost:5173,…` | Comma-separated |
| `MAX_REPO_SIZE_KB` | no | `50000` | Larger repositories are rejected up front |
| `MAX_FILES` | no | `2000` | |
| `PROGRAM_DAYS` | no | `45` | Length of the daily activity programme |
| `PROGRAM_TIMEZONE` | no | `UTC` | IANA zone such as `Asia/Kolkata`; days unlock on their calendar date in this zone |

The frontend reads `VITE_API_URL` from `frontend/.env`. Leave it blank for local development and set it to the deployed backend URL for production builds.

## How the score is built

The model supplies judgement; static analysis supplies the facts. `backend/app/services/scoring.py` applies **evidence caps**, so the same commit always gets the same limits:

| Evidence | Effect |
|----------|--------|
| No test files | Testing capped at 2/10 |
| No README, or under 200 characters | Documentation capped at 3–4/15 |
| Credentials committed outside test fixtures | Security scored 0/10 |
| Fewer than 3 commits | Git Hygiene capped at 3/10 |
| Mostly generic commit messages | Git Hygiene capped at 5/10 |
| No `.gitignore` / build output committed | Git Hygiene −2 / −3 |
| More than 80 lint issues per 1000 lines | Code Quality capped at 8/20 |

**Rubric (100 points):**

| Category | Points |
|----------|--------|
| Code Quality | 20 |
| Structure | 15 |
| Correctness | 20 |
| Documentation | 15 |
| Testing | 10 |
| Git Hygiene | 10 |
| Security | 10 |

`GET /api/rubric` returns the rubric.

## Testing

```powershell
cd backend
python -m pytest -q
```

The suite makes no network calls and costs nothing in OpenAI usage, because the LLM boundary is stubbed. It covers:

- URL validation
- the repository inspector against synthetic repos
- every scoring cap
- the activity programme
- the API's auth and ownership rules

## Project structure

```
Assignment-Tracker/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app, CORS, rate limiting
│   │   ├── config.py        # settings from environment / .env
│   │   ├── models.py        # SQLModel tables
│   │   ├── auth.py          # bcrypt + JWT, role dependencies
│   │   ├── routers/         # auth, assignments, submissions, activities, admin
│   │   └── services/        # github, inspector, linters, git_hygiene, collector,
│   │                        # llm, scoring, pipeline, program, performance, remark
│   ├── prompts/reviewer.md  # system prompt for the reviewer model
│   ├── tests/               # pytest suite
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/           # student and teacher screens
│   │   ├── components/      # shared UI
│   │   ├── api/client.ts    # typed API client
│   │   └── contexts/        # auth context
│   ├── package.json
│   └── .env.example
├── LICENSE
└── README.md
```

## Deployment note

`POST /api/submissions` runs the whole analysis inline, so the request stays open for 30–120 seconds. That's fine locally. But most hosting proxies close idle requests after 30–60 seconds, so move the analysis to a background job (e.g. FastAPI `BackgroundTasks` plus polling `GET /api/submissions/{id}`) before deploying publicly. `Submission.status` and the framework-free `run_analysis()` pipeline are already in place for this.

## License

[MIT](LICENSE)

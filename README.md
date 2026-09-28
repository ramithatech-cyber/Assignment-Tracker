# Student Assignment Tracker

Students submit a GitHub repository link. The backend downloads the repo, runs real
static-analysis tooling over it, hands the measured facts plus the important source files to
OpenAI, and returns a structured review: **what's good**, **what needs improvement**, and a
**score out of 100** broken down across a seven-part rubric.

Teachers create assignments and see every submission with its score.

- **Frontend** — React 18 + TypeScript (Vite, Tailwind)
- **Backend** — FastAPI + SQLModel (SQLite locally, Postgres in production)
- **Review** — OpenAI structured outputs, constrained by deterministic static analysis

---

## Quick start

### 1. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env      # then set OPENAI_API_KEY
python -m uvicorn app.main:app --reload
```

API docs: <http://localhost:8000/docs> · health: <http://localhost:8000/api/health>

### 2. Frontend

Requires **Node.js 18+** ([nodejs.org](https://nodejs.org)).

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The Vite dev server proxies `/api` to port 8000, so there is no
CORS setup for local development.

### 3. Use it

The landing page at `/` is student-facing. Admin (staff) sign-in lives at an unlinked URL:

| Who | URL |
|---|---|
| Student | <http://localhost:5173/> |
| Admin | <http://localhost:5173/login/admin> — **bookmark this** |

1. Go to `/login/admin`, register an admin account, create an assignment, and write real
   requirements — that text is what the "Correctness & Completeness" score is measured against.
2. Register a **student** account from the landing page, open the assignment, paste a public
   GitHub URL, submit.
3. Wait 30–120 seconds for the report.

> **"Admin" is the UI name for the `teacher` role.** The API contract is unchanged.
>
> ⚠️ **The admin portal is hidden, not protected.** `/login/admin` and `/register/admin` are
> simply not linked from the student pages — both still work for anyone who types them, and
> `POST /api/auth/register` still accepts `"role": "teacher"` from any client. Before real
> students use this, gate admin signup server-side (a shared signup code checked in
> `routers/auth.py`, or closing admin self-registration entirely).
>
> What *is* enforced server-side: a student can never read another student's submission, and a
> teacher can only see submissions on assignments they own.

---

## Configuration

| Variable | Required | Default | Notes |
|---|---|---|---|
| `OPENAI_API_KEY` | **yes** | — | Submissions fail without it |
| `JWT_SECRET` | **yes** in prod | insecure dev value | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `OPENAI_MODEL` | no | `gpt-4.1` | Any model supporting structured outputs |
| `GITHUB_TOKEN` | no | — | Lifts the GitHub API limit from 60/hr to 5000/hr. A no-scope classic token is enough |
| `DATABASE_URL` | no | `sqlite:///./assignment_tracker.db` | `postgresql+psycopg://…` in production |
| `MAX_REPO_SIZE_KB` | no | `50000` | Repositories above this are rejected up front |
| `PROGRAM_DAYS` | no | `45` | Length of the daily activity programme |
| `PROGRAM_TIMEZONE` | no | `UTC` | **Set this.** Days unlock on their calendar date in this IANA zone, e.g. `Asia/Kolkata`. Left at UTC, a student's day rolls over at 05:30 local |

---

## The 45-day activity programme

Students log one entry per day for 45 days: status (completed / partial / skipped), what they
worked on, hours, and an optional link. The **Weekly** page is a read-only rollup of the same
entries grouped into seven weeks — nothing extra to fill in, one source of truth.

**Days are date-locked.** Day 1 is the student's enrolment date (their registration date by
default). Only *today's* day is editable: future days are not yet open, and a day closes when
its date passes. That rule lives in `routers/activities.py`, not the UI — the API returns 403
with an explanatory message either way, so hiding the button is not what enforces it.

| Endpoint | Purpose |
|---|---|
| `GET /api/activities/days` | All 45 days with state (`upcoming`/`open`/`submitted`/`missed`) |
| `GET /api/activities/weeks` | The seven-week rollup |
| `PUT /api/activities/days/{n}` | Create or update day *n* (today only) |

## Admin dashboard

`GET /api/admin/overview`, `/students`, `/students/{id}` — teacher-only. Each student gets a
**performance level** blended from two signals:

```
index = 0.6 x average assignment score  +  0.4 x daily completion rate
```

A student with no graded submissions is judged on consistency alone rather than being scored
zero. Bands: Excellent 85+, Strong 70+, On track 55+, Needs support 40+, At risk below.

### Reviewing one student

Clicking a student anywhere in the admin UI opens `/admin/students/{id}`: every submission they
have made (expandable to its category breakdown and top issues), their weekly consistency, their
recent daily entries, and an **overall remark** at the end.

The remark is a single verdict across their whole body of work — the patterns that recur, not a
restatement of any one report. `POST /api/admin/students/{id}/remark` writes it; it reads the
reports already stored for each submission, so it is **one cheap call (~1,500 tokens) regardless
of how many submissions the student has** and never re-analyses a repository.

It is cached in `student_remarks` and **only ever generated from an explicit button** — an admin
scrolling a class of thirty must not spend thirty OpenAI calls. When new work arrives after a
remark was written, the API returns a `stale_reason` (`"2 new submissions and 1 new daily
entry"`) and the UI shows an out-of-date banner with a Regenerate button.

---

## How the score is built

The model supplies judgement; static analysis supplies the facts. `app/services/scoring.py`
enforces **evidence caps** the model cannot argue past, so the same commit always produces the
same limits:

| Evidence | Effect |
|---|---|
| No test files anywhere | Testing capped at 2/10 |
| No README, or under 200 chars | Documentation capped at 3–4/15 |
| Credentials committed outside test fixtures | Security scored 0/10 |
| Fewer than 3 commits | Git Hygiene capped at 3/10 |
| Mostly generic commit messages | Git Hygiene capped at 5/10 |
| No `.gitignore` / build output committed | Git Hygiene −2 / −3 |
| >80 lint issues per 1000 lines | Code Quality capped at 8/20 |

Every cap that fires is shown to the student with its reason, which is what makes a disputed
grade answerable.

Rubric (100 points): Code Quality 20 · Structure 15 · Correctness 20 · Documentation 15 ·
Testing 10 · Git Hygiene 10 · Security 10. `GET /api/rubric` returns it.

### Notable behaviours

- **No `git` required.** Repositories are fetched through GitHub's tarball API over HTTPS and
  extracted with path-traversal and symlink guards. A shallow `git clone` is used as a fallback
  only if a git binary happens to be present.
- **Test fixtures are not treated as leaks.** A private key under `tests/` or `certs/` is
  reported to the student but never zeroes the Security score. (The first live run against
  `psf/requests` failed this way; `tests/test_secret_fixtures.py` pins the behaviour.)
- **Cited paths are verified.** Every `file:line` the model returns is checked against the real
  file list. Unverified citations are shown without a link rather than linking somewhere broken.
- **Linters degrade gracefully.** A missing `npx`, or a repo with no ESLint config, marks that
  tool unavailable rather than failing the submission.
- **Consistent ruleset.** ruff runs with `--isolated` and an explicit rule selection, so a
  student cannot raise their score by committing a config that disables the linter.

---

## Testing

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

49 tests, no network calls and no OpenAI spend — the LLM boundary is stubbed. They cover URL
validation (SSH, `file://`, other hosts, lookalike domains), the inspector against synthetic
repositories, every scoring cap, and the API's auth and ownership rules.

---

## Architecture

```
backend/app/
├─ main.py            FastAPI app, CORS, rate limiting
├─ models.py          User · Assignment · Submission · AnalysisReport
├─ auth.py            bcrypt + JWT, role dependencies
├─ routers/           auth · assignments · submissions
└─ services/
   ├─ github.py       URL allowlist, metadata, commits, tarball download
   ├─ inspector.py    file tree, LOC, tests, README, secrets, junk
   ├─ linters.py      ruff, radon, eslint
   ├─ git_hygiene.py  commit count, cadence, message quality
   ├─ collector.py    picks the files worth reviewing, builds the bundle
   ├─ llm.py          OpenAI structured-output call
   ├─ scoring.py      rubric + evidence caps
   └─ pipeline.py     orchestration (no FastAPI types — worker-ready)
```

### A note on the synchronous design

`POST /api/submissions` runs the whole pipeline inline, so the request stays open for 30–120
seconds. That is fine locally, but most hosting proxies (Render, Railway, Heroku, nginx) close
idle responses at 30–60 seconds, so **this will need to move to a background job before it is
deployed publicly**.

The groundwork is already in place: `Submission.status` and `error_message` exist, and
`run_analysis()` takes plain values and returns a plain result with no request state in it.
Switching to `BackgroundTasks` plus polling on `GET /api/submissions/{id}` is a change to
`routers/submissions.py` alone — no schema migration, no pipeline changes  .


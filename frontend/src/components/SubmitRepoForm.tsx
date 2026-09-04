import { useEffect, useRef, useState } from 'react'

import { ApiError, api } from '../api/client'
import type { Submission } from '../types'
import { ErrorBanner, Icons } from './common'

// Same shape the server enforces -- catching it here saves a 60-second round
// trip to be told the URL was wrong.
const GITHUB_URL =
  /^https?:\/\/(www\.)?github\.com\/[A-Za-z0-9][A-Za-z0-9-]{0,38}\/[A-Za-z0-9._-]{1,100}(\.git)?(\/.*)?$/

const STAGES = [
  { at: 0, label: 'Validating the repository URL', hint: 'Checking it points at a public GitHub repo' },
  { at: 2, label: 'Downloading from GitHub', hint: 'Pulling the full repository archive' },
  { at: 8, label: 'Reading the file tree', hint: 'Counting lines, finding tests and docs' },
  { at: 16, label: 'Running static analysis', hint: 'ruff, radon, complexity and secret scanning' },
  { at: 26, label: 'Reading the commit history', hint: 'Commit cadence and message quality' },
  { at: 34, label: 'AI review in progress', hint: 'This is the slow part — hang tight' },
  { at: 75, label: 'Still reviewing', hint: 'Large repositories take a little longer' },
]

/**
 * The analysis runs inline in the POST, so this request stays open for 30-120
 * seconds. Staged copy plus an elapsed counter is what stops that reading as a
 * hung page.
 */
function Progress() {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    const timer = window.setInterval(() => setElapsed((value) => value + 1), 1000)
    return () => window.clearInterval(timer)
  }, [])

  const index = STAGES.reduce((found, stage, i) => (elapsed >= stage.at ? i : found), 0)
  const stage = STAGES[index]
  const minutes = Math.floor(elapsed / 60)
  const seconds = String(elapsed % 60).padStart(2, '0')

  return (
    <div className="card card-accent animate-scale-in overflow-hidden p-6">
      <div className="flex items-center gap-4">
        <span className="relative flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-brand-gradient text-white shadow-lift">
          <Icons.Sparkle className="h-6 w-6 animate-pulse" />
          <span className="absolute inset-0 animate-ping rounded-2xl bg-brand-400 opacity-20" />
        </span>
        <div className="flex-1">
          <p className="text-base font-bold text-ink">{stage.label}</p>
          <p className="mt-0.5 text-sm text-muted">{stage.hint}</p>
        </div>
        <span className="chip border-brand-200 bg-brand-50 tabular-nums text-brand-700">
          <Icons.Clock className="h-3 w-3" />
          {minutes}:{seconds}
        </span>
      </div>

      <div className="mt-5 h-2 w-full overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-brand-gradient"
          style={{
            // Asymptotic: approaches but never reaches 100%, because the real
            // duration is unknown.
            width: `${Math.min(95, (1 - Math.exp(-elapsed / 45)) * 100)}%`,
            transition: 'width 1s linear',
          }}
        />
      </div>

      <ol className="mt-5 grid gap-1.5">
        {STAGES.slice(0, 6).map((item, i) => (
          <li
            key={item.at}
            className={`flex items-center gap-2 text-xs transition ${
              i < index ? 'text-emerald-600' : i === index ? 'font-semibold text-brand-700' : 'text-slate-300'
            }`}
          >
            {i < index ? (
              <Icons.Check className="h-3.5 w-3.5" />
            ) : (
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  i === index ? 'animate-pulse bg-brand-500' : 'bg-slate-300'
                }`}
              />
            )}
            {item.label}
          </li>
        ))}
      </ol>

      <p className="mt-4 text-center text-xs text-slate-400">Please keep this tab open.</p>
    </div>
  )
}

interface Props {
  assignmentId: number
  onComplete: (submission: Submission) => void
}

export function SubmitRepoForm({ assignmentId, onComplete }: Props) {
  const [url, setUrl] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => () => abortRef.current?.abort(), [])

  const trimmed = url.trim()
  const invalid = trimmed.length > 0 && !GITHUB_URL.test(trimmed)
  const valid = trimmed.length > 0 && !invalid

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!GITHUB_URL.test(trimmed)) {
      setError('Enter a public GitHub repository URL, e.g. https://github.com/owner/repository')
      return
    }

    setError(null)
    setSubmitting(true)
    abortRef.current = new AbortController()
    try {
      const submission = await api.submit(assignmentId, trimmed, abortRef.current.signal)
      onComplete(submission)
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : 'Something went wrong. Please try again.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  if (submitting) return <Progress />

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="label" htmlFor="repo-url">
          GitHub repository URL
        </label>
        <div className="relative">
          <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400">
            <Icons.Github className="h-4 w-4" />
          </span>
          <input
            id="repo-url"
            className={`input pl-10 font-mono ${invalid ? 'input-error' : ''} ${
              valid ? 'border-emerald-400 focus:border-emerald-500 focus:ring-emerald-500/10' : ''
            }`}
            placeholder="https://github.com/your-username/your-project"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            autoComplete="off"
            spellCheck={false}
          />
          {valid && (
            <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-emerald-500">
              <Icons.Check className="h-4 w-4" />
            </span>
          )}
        </div>
        {invalid && (
          <p className="mt-1.5 text-xs font-medium text-rose-600">
            That isn&apos;t a GitHub repository URL — it should look like
            https://github.com/owner/repository
          </p>
        )}
      </div>

      <ErrorBanner message={error} />

      <div className="flex flex-wrap items-center gap-3">
        <button type="submit" className="btn-primary" disabled={!valid}>
          <Icons.Sparkle className="h-4 w-4" />
          Analyse and submit
        </button>
        <span className="text-xs text-muted">
          Must be public · usually takes 30–120 seconds
        </span>
      </div>
    </form>
  )
}

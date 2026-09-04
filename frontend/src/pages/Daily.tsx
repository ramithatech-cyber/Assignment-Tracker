import { useEffect, useMemo, useState } from 'react'

import { ApiError, api } from '../api/client'
import {
  EmptyState,
  ErrorBanner,
  Icons,
  LoadingBlock,
  PageHeader,
  Spinner,
} from '../components/common'
import { useAsync } from '../hooks/useAsync'
import type { ActivityStatus, ProgramDay, ProgramSummary } from '../types'

const STATE_STYLES: Record<string, string> = {
  submitted: 'border-emerald-300 bg-emerald-50 text-emerald-800 hover:border-emerald-400',
  open: 'border-brand-500 bg-brand-gradient text-white shadow-lift ring-4 ring-brand-500/15',
  missed: 'border-brand-200 bg-brand-50/60 text-brand-500 hover:border-brand-300',
  upcoming: 'border-stone-200 bg-stone-50 text-stone-300 cursor-not-allowed',
}

const STATUS_OPTIONS: { value: ActivityStatus; label: string; hint: string }[] = [
  { value: 'completed', label: 'Completed', hint: 'Finished the day fully' },
  { value: 'partial', label: 'Partial', hint: 'Made some progress' },
  { value: 'skipped', label: 'Skipped', hint: "Couldn't work today" },
]

function shortDate(iso: string): string {
  const d = new Date(`${iso}T00:00:00`)
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

function StatCard({
  label,
  value,
  Icon,
  tone = 'brand',
}: {
  label: string
  value: string | number
  Icon: (p: { className?: string }) => JSX.Element
  tone?: 'brand' | 'emerald' | 'amber'
}) {
  const tones = {
    brand: 'bg-brand-gradient',
    emerald: 'bg-gradient-to-br from-emerald-500 to-teal-600',
    amber: 'bg-gradient-to-br from-amber-500 to-orange-600',
  }
  return (
    <div className="card flex items-center gap-3.5 p-4">
      <span
        className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${tones[tone]} text-white shadow-lift`}
      >
        <Icon className="h-5 w-5" />
      </span>
      <div className="min-w-0">
        <p className="text-xl font-extrabold tabular-nums leading-tight text-ink">{value}</p>
        <p className="truncate text-[11px] font-semibold uppercase tracking-wide text-stone-400">
          {label}
        </p>
      </div>
    </div>
  )
}

/** The form for one day. Only rendered for the day the server says is open. */
function DayForm({
  day,
  onSaved,
}: {
  day: ProgramDay
  onSaved: (day: ProgramDay, summary: ProgramSummary) => void
}) {
  const [status, setStatus] = useState<ActivityStatus>(day.entry?.status ?? 'completed')
  const [notes, setNotes] = useState(day.entry?.notes ?? '')
  const [hours, setHours] = useState(String(day.entry?.hours ?? ''))
  const [link, setLink] = useState(day.entry?.link ?? '')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [saved, setSaved] = useState(false)

  // Switching days must reset the form, or you'd edit day 6 with day 5's text.
  useEffect(() => {
    setStatus(day.entry?.status ?? 'completed')
    setNotes(day.entry?.notes ?? '')
    setHours(String(day.entry?.hours ?? ''))
    setLink(day.entry?.link ?? '')
    setSaved(false)
    setError(null)
  }, [day.day_number, day.entry])

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const result = await api.saveDay(day.day_number, {
        status,
        notes: notes.trim(),
        hours: Number(hours) || 0,
        link: link.trim() || null,
      })
      setSaved(true)
      onSaved(result.day, result.summary)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Could not save.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <span className="label">How did today go?</span>
        <div className="grid grid-cols-3 gap-2">
          {STATUS_OPTIONS.map((option) => {
            const active = status === option.value
            return (
              <button
                key={option.value}
                type="button"
                onClick={() => setStatus(option.value)}
                className={`rounded-xl border-2 p-2.5 text-left transition ${
                  active
                    ? 'border-brand-600 bg-brand-50 shadow-glow'
                    : 'border-stone-200 bg-white hover:border-brand-300'
                }`}
              >
                <span
                  className={`block text-sm font-bold ${active ? 'text-brand-700' : 'text-stone-700'}`}
                >
                  {option.label}
                </span>
                <span className="mt-0.5 block text-[11px] leading-tight text-stone-400">
                  {option.hint}
                </span>
              </button>
            )
          })}
        </div>
      </div>

      <div>
        <label className="label" htmlFor="notes">
          What did you work on?
        </label>
        <textarea
          id="notes"
          className="input min-h-[120px] resize-y"
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          placeholder="Built the login form, fixed the token refresh bug, read up on FastAPI dependencies..."
          maxLength={4000}
        />
        <p className="mt-1 text-right text-xs text-stone-400">{notes.length}/4000</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="label" htmlFor="hours">
            Hours spent
          </label>
          <input
            id="hours"
            type="number"
            step="0.5"
            min="0"
            max="24"
            className="input"
            value={hours}
            onChange={(event) => setHours(event.target.value)}
            placeholder="3.5"
          />
        </div>
        <div>
          <label className="label" htmlFor="link">
            Link (optional)
          </label>
          <input
            id="link"
            className="input font-mono text-xs"
            value={link}
            onChange={(event) => setLink(event.target.value)}
            placeholder="https://github.com/..."
          />
        </div>
      </div>

      <ErrorBanner message={error} />

      <div className="flex flex-wrap items-center gap-3">
        <button type="submit" className="btn-primary" disabled={busy}>
          {busy ? <Spinner /> : <Icons.Check className="h-4 w-4" />}
          {day.entry ? 'Update entry' : 'Submit day'}
        </button>
        {saved && !busy && (
          <span className="chip border-emerald-200 bg-emerald-50 text-emerald-700">
            <Icons.Check className="h-3 w-3" />
            Saved
          </span>
        )}
      </div>
    </form>
  )
}

export function Daily() {
  const { data, loading, error, reload } = useAsync(() => api.days())
  const [days, setDays] = useState<ProgramDay[]>([])
  const [summary, setSummary] = useState<ProgramSummary | null>(null)
  const [selected, setSelected] = useState<number | null>(null)

  useEffect(() => {
    if (!data) return
    setDays(data.days)
    setSummary(data.summary)
    // Land on the day the student can actually act on.
    setSelected((current) => current ?? data.days.find((d) => d.editable)?.day_number ?? 1)
  }, [data])

  const selectedDay = useMemo(
    () => days.find((d) => d.day_number === selected) ?? null,
    [days, selected],
  )

  if (loading) return <LoadingBlock rows={2} />
  if (error) return <ErrorBanner message={error} />
  if (!summary) return <EmptyState title="No programme found" />

  function handleSaved(day: ProgramDay, next: ProgramSummary) {
    setDays((previous) => previous.map((d) => (d.day_number === day.day_number ? day : d)))
    setSummary(next)
  }

  const notStarted = !summary.started

  return (
    <>
      <PageHeader
        eyebrow="45-day programme"
        title="Daily activity"
        subtitle={
          notStarted
            ? `Your programme starts on ${summary.enrolled_on}.`
            : summary.finished
              ? 'Your 45 days are complete.'
              : `Day ${summary.current_day} of ${summary.total_days} — only today can be filled in.`
        }
        action={
          <button type="button" className="btn-ghost" onClick={reload}>
            Refresh
          </button>
        }
      />

      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Days submitted" value={`${summary.submitted_days}/${summary.total_days}`} Icon={Icons.Check} tone="emerald" />
        <StatCard label="Current streak" value={`${summary.current_streak} days`} Icon={Icons.Flame} tone="amber" />
        <StatCard label="Total hours" value={summary.total_hours} Icon={Icons.Clock} />
        <StatCard label="Missed days" value={summary.missed_days} Icon={Icons.Warning} />
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        {/* ------------------------------------------------------- day grid */}
        <section className="card p-6 lg:col-span-3">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h2 className="font-bold text-ink">All 45 days</h2>
            <div className="flex flex-wrap items-center gap-3 text-[11px] text-stone-500">
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded bg-emerald-400" /> Submitted
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded bg-brand-600" /> Today
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded bg-brand-200" /> Missed
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded bg-stone-200" /> Upcoming
              </span>
            </div>
          </div>

          <div className="grid grid-cols-5 gap-2 sm:grid-cols-7">
            {days.map((day) => {
              const isSelected = day.day_number === selected
              return (
                <button
                  key={day.day_number}
                  type="button"
                  disabled={day.state === 'upcoming'}
                  onClick={() => setSelected(day.day_number)}
                  title={`Day ${day.day_number} · ${day.date} · ${day.state}`}
                  className={`relative flex aspect-square flex-col items-center justify-center rounded-xl border-2 text-sm font-bold transition ${
                    STATE_STYLES[day.state]
                  } ${isSelected ? 'scale-105 ring-4 ring-brand-500/25' : ''}`}
                >
                  {day.day_number}
                  <span className="mt-0.5 text-[9px] font-medium opacity-70">
                    {shortDate(day.date)}
                  </span>
                  {day.state === 'submitted' && (
                    <span className="absolute right-1 top-1 text-emerald-600">
                      <Icons.Check className="h-3 w-3" />
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        </section>

        {/* ----------------------------------------------------- day detail */}
        <section className="card card-accent h-fit p-6 lg:col-span-2">
          {!selectedDay ? (
            <p className="text-sm text-muted">Pick a day.</p>
          ) : (
            <>
              <div className="mb-5 flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-xl font-extrabold text-ink">Day {selectedDay.day_number}</h2>
                  <p className="mt-0.5 text-sm text-muted">
                    {selectedDay.date} · Week {selectedDay.week}
                  </p>
                </div>
                {selectedDay.editable ? (
                  <span className="chip border-brand-200 bg-brand-50 text-brand-700">
                    <Icons.Edit className="h-3 w-3" />
                    Open today
                  </span>
                ) : (
                  <span className="chip border-stone-200 bg-stone-100 text-stone-500">
                    <Icons.Lock className="h-3 w-3" />
                    Locked
                  </span>
                )}
              </div>

              {selectedDay.editable ? (
                <DayForm day={selectedDay} onSaved={handleSaved} />
              ) : selectedDay.entry ? (
                <div className="space-y-4">
                  <div>
                    <p className="text-[11px] font-bold uppercase tracking-wide text-stone-400">
                      Status
                    </p>
                    <p className="mt-1 text-sm font-semibold capitalize text-stone-800">
                      {selectedDay.entry.status}
                    </p>
                  </div>
                  <div>
                    <p className="text-[11px] font-bold uppercase tracking-wide text-stone-400">
                      Notes
                    </p>
                    <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-stone-700">
                      {selectedDay.entry.notes || '—'}
                    </p>
                  </div>
                  <div className="flex gap-6">
                    <div>
                      <p className="text-[11px] font-bold uppercase tracking-wide text-stone-400">
                        Hours
                      </p>
                      <p className="mt-1 text-sm font-semibold tabular-nums text-stone-800">
                        {selectedDay.entry.hours}
                      </p>
                    </div>
                    {selectedDay.entry.link && (
                      <div className="min-w-0">
                        <p className="text-[11px] font-bold uppercase tracking-wide text-stone-400">
                          Link
                        </p>
                        <a
                          href={selectedDay.entry.link}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-1 block truncate font-mono text-xs text-brand-600 hover:underline"
                        >
                          {selectedDay.entry.link}
                        </a>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="rounded-xl border border-stone-200 bg-stone-50 p-4 text-sm leading-relaxed text-stone-600">
                  {selectedDay.state === 'missed' ? (
                    <>
                      <span className="font-semibold text-brand-700">This day was missed.</span>{' '}
                      Days close once their date passes, so it can no longer be filled in.
                    </>
                  ) : (
                    <>
                      This day unlocks on <strong>{selectedDay.date}</strong>.
                    </>
                  )}
                </div>
              )}
            </>
          )}
        </section>
      </div>
    </>
  )
}

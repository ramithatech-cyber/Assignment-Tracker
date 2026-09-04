import { Link } from 'react-router-dom'

import { api } from '../api/client'
import { ErrorBanner, Icons, LoadingBlock, PageHeader } from '../components/common'
import { useAsync } from '../hooks/useAsync'
import type { ProgramWeek } from '../types'

const STATE_CHIP: Record<ProgramWeek['state'], string> = {
  complete: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  in_progress: 'border-brand-200 bg-brand-50 text-brand-700',
  upcoming: 'border-stone-200 bg-stone-100 text-stone-500',
}

const STATE_LABEL: Record<ProgramWeek['state'], string> = {
  complete: 'Complete',
  in_progress: 'In progress',
  upcoming: 'Upcoming',
}

function completionColor(fraction: number): string {
  if (fraction >= 0.85) return '#059669'
  if (fraction >= 0.6) return '#65a30d'
  if (fraction >= 0.35) return '#d97706'
  return '#b91c1c'
}

function shortDate(iso: string): string {
  const d = new Date(`${iso}T00:00:00`)
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

export function Weekly() {
  const { data, loading, error } = useAsync(() => api.weeks())

  if (loading) return <LoadingBlock rows={3} />
  if (error) return <ErrorBanner message={error} />
  if (!data) return null

  const { weeks, summary } = data
  const overall = summary.elapsed_days > 0 ? summary.completion : 0

  return (
    <>
      <PageHeader
        eyebrow="45-day programme"
        title="Weekly overview"
        subtitle="Your daily entries, grouped into seven weeks. Fill days in on the Daily page."
        action={
          <Link to="/daily" className="btn-primary">
            <Icons.Calendar className="h-4 w-4" />
            Go to Daily
          </Link>
        }
      />

      {/* ---------------------------------------------------------- overall */}
      <section className="card card-accent mb-8 p-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-ink">Overall progress</h2>
            <p className="mt-1 text-sm text-muted">
              {summary.submitted_days} of {summary.elapsed_days} elapsed days submitted ·{' '}
              {summary.total_hours} hours logged
            </p>
          </div>
          <p className="text-3xl font-extrabold tabular-nums text-ink">
            {Math.round(overall * 100)}
            <span className="text-lg text-stone-400">%</span>
          </p>
        </div>

        <div className="mt-4 h-3 w-full overflow-hidden rounded-full bg-stone-100">
          <div
            className="h-full rounded-full bg-brand-gradient"
            style={{
              width: `${Math.max(overall * 100, 1)}%`,
              transition: 'width 900ms cubic-bezier(.21,1.02,.73,1)',
            }}
          />
        </div>
      </section>

      {/* ------------------------------------------------------------ weeks */}
      <div className="grid gap-5 md:grid-cols-2">
        {weeks.map((week, index) => (
          <section
            key={week.week_number}
            className="card card-hover animate-fade-up p-6"
            style={{ animationDelay: `${index * 60}ms` }}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-lg font-bold text-ink">Week {week.week_number}</h3>
                <p className="mt-0.5 text-xs text-muted">
                  {shortDate(week.start_date)} – {shortDate(week.end_date)} · days{' '}
                  {week.day_numbers[0]}–{week.day_numbers[week.day_numbers.length - 1]}
                </p>
              </div>
              <span className={`chip ${STATE_CHIP[week.state]}`}>{STATE_LABEL[week.state]}</span>
            </div>

            {/* Per-day pips: the whole week readable at a glance. */}
            <div className="mt-4 flex gap-1.5">
              {week.day_numbers.map((dayNumber, position) => {
                const submitted = position < week.submitted + week.missed
                const tone =
                  position < week.submitted
                    ? 'bg-emerald-400'
                    : submitted
                      ? 'bg-brand-200'
                      : 'bg-stone-200'
                return (
                  <span
                    key={dayNumber}
                    className={`h-2 flex-1 rounded-full ${tone}`}
                    title={`Day ${dayNumber}`}
                  />
                )
              })}
            </div>

            <dl className="mt-5 grid grid-cols-4 gap-3 border-t border-stone-100 pt-4">
              <div>
                <dt className="text-[10px] font-bold uppercase tracking-wide text-stone-400">
                  Done
                </dt>
                <dd className="text-lg font-extrabold tabular-nums text-emerald-600">
                  {week.submitted}
                </dd>
              </div>
              <div>
                <dt className="text-[10px] font-bold uppercase tracking-wide text-stone-400">
                  Missed
                </dt>
                <dd className="text-lg font-extrabold tabular-nums text-brand-600">
                  {week.missed}
                </dd>
              </div>
              <div>
                <dt className="text-[10px] font-bold uppercase tracking-wide text-stone-400">
                  Hours
                </dt>
                <dd className="text-lg font-extrabold tabular-nums text-ink">{week.hours}</dd>
              </div>
              <div>
                <dt className="text-[10px] font-bold uppercase tracking-wide text-stone-400">
                  Rate
                </dt>
                <dd
                  className="text-lg font-extrabold tabular-nums"
                  style={{ color: completionColor(week.completion) }}
                >
                  {week.elapsed_days ? `${Math.round(week.completion * 100)}%` : '—'}
                </dd>
              </div>
            </dl>

            {week.submitted > 0 && (
              <p className="mt-3 text-xs text-stone-500">
                {week.fully_completed} completed · {week.partial} partial · {week.skipped} skipped
              </p>
            )}
          </section>
        ))}
      </div>
    </>
  )
}

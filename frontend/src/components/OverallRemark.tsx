import { useState } from 'react'

import { ApiError, api } from '../api/client'
import type { StudentRemark, Trajectory } from '../types'
import { ErrorBanner, Icons, Spinner, formatDate } from './common'

const TRAJECTORY: Record<Trajectory, { label: string; chip: string; Icon: (p: { className?: string }) => JSX.Element }> = {
  improving: {
    label: 'Improving',
    chip: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    Icon: Icons.Chart,
  },
  steady: {
    label: 'Steady',
    chip: 'border-amber-200 bg-amber-50 text-amber-800',
    Icon: Icons.Target,
  },
  declining: {
    label: 'Declining',
    chip: 'border-brand-200 bg-brand-50 text-brand-700',
    Icon: Icons.Warning,
  },
  insufficient_data: {
    label: 'Not enough data',
    chip: 'border-stone-200 bg-stone-100 text-stone-500',
    Icon: Icons.Inbox,
  },
}

interface Props {
  studentId: number
  studentName: string
  remark: StudentRemark | null
  canGenerate: boolean
  onGenerated: (remark: StudentRemark) => void
}

export function OverallRemark({
  studentId,
  studentName,
  remark,
  canGenerate,
  onGenerated,
}: Props) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function run() {
    setError(null)
    setBusy(true)
    try {
      onGenerated(await api.generateRemark(studentId))
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : 'Could not generate the remark.',
      )
    } finally {
      setBusy(false)
    }
  }

  const trajectory = remark ? TRAJECTORY[remark.trajectory] : null

  return (
    <section className="card card-accent animate-fade-up mt-6 overflow-hidden p-7">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="flex items-center gap-2.5 text-xl font-extrabold text-ink">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-gradient text-white shadow-lift">
              <Icons.Sparkle className="h-5 w-5" />
            </span>
            Overall remark
          </h2>
          <p className="mt-1.5 text-sm text-muted">
            A verdict across everything {studentName.split(' ')[0]} has submitted, not one
            assignment.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {trajectory && (
            <span className={`chip ${trajectory.chip}`}>
              <trajectory.Icon className="h-3 w-3" />
              {trajectory.label}
            </span>
          )}
          {canGenerate && (
            <button
              type="button"
              className={remark ? 'btn-ghost' : 'btn-primary'}
              onClick={run}
              disabled={busy}
            >
              {busy ? <Spinner /> : <Icons.Sparkle className="h-4 w-4" />}
              {busy ? 'Writing...' : remark ? 'Regenerate' : 'Generate remark'}
            </button>
          )}
        </div>
      </div>

      <ErrorBanner message={error} />

      {!canGenerate && !remark && (
        <p className="rounded-xl border border-stone-200 bg-stone-50 p-4 text-sm text-stone-600">
          {studentName} has no submissions and no daily activity yet, so there is nothing to
          write a remark about.
        </p>
      )}

      {canGenerate && !remark && !error && (
        <div className="rounded-xl border border-stone-200 bg-stone-50 p-5 text-sm leading-relaxed text-stone-600">
          <p>
            No remark yet. Generating one reads every report already produced for{' '}
            {studentName.split(' ')[0]} plus their daily log, and writes a single overall
            verdict.
          </p>
          <p className="mt-2 text-xs text-stone-500">
            One OpenAI call (roughly a cent). It is saved, so opening this page again is free.
          </p>
        </div>
      )}

      {remark && (
        <div className="space-y-6">
          {remark.stale_reason && (
            <div className="flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50 p-3.5">
              <Icons.Warning className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
              <p className="text-xs leading-relaxed text-amber-900">
                <strong>Out of date.</strong> {remark.stale_reason} since this was written.
                Regenerate to take it into account.
              </p>
            </div>
          )}

          <p className="text-[15px] leading-relaxed text-stone-700">{remark.summary}</p>

          <div className="grid gap-5 md:grid-cols-2">
            <div className="rounded-xl border border-emerald-100 bg-emerald-50/50 p-4">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-bold text-emerald-800">
                <Icons.Check className="h-4 w-4" />
                Recurring strengths
              </h3>
              {remark.strengths.length === 0 ? (
                <p className="text-sm text-stone-500">None identified.</p>
              ) : (
                <ul className="space-y-2">
                  {remark.strengths.map((item, index) => (
                    <li key={index} className="flex gap-2 text-sm leading-relaxed text-stone-700">
                      <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" />
                      {item}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="rounded-xl border border-brand-100 bg-brand-50/50 p-4">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-bold text-brand-800">
                <Icons.Warning className="h-4 w-4" />
                Recurring concerns
              </h3>
              {remark.concerns.length === 0 ? (
                <p className="text-sm text-stone-500">None identified.</p>
              ) : (
                <ul className="space-y-2">
                  {remark.concerns.map((item, index) => (
                    <li key={index} className="flex gap-2 text-sm leading-relaxed text-stone-700">
                      <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500" />
                      {item}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {remark.recommendation && (
            <div className="rounded-xl bg-brand-gradient p-5 text-white shadow-lift">
              <h3 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wide">
                <Icons.Target className="h-4 w-4" />
                What to do next
              </h3>
              <p className="mt-2 text-[15px] leading-relaxed text-white/95">
                {remark.recommendation}
              </p>
            </div>
          )}

          <p className="border-t border-stone-100 pt-4 text-xs text-stone-400">
            Written {formatDate(remark.generated_at)} by {remark.llm_model} ·{' '}
            {remark.tokens_used.toLocaleString()} tokens · based on{' '}
            {remark.based_on_submissions} submission
            {remark.based_on_submissions === 1 ? '' : 's'} and {remark.based_on_days} daily
            entr{remark.based_on_days === 1 ? 'y' : 'ies'}
          </p>
        </div>
      )}
    </section>
  )
}

import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { api } from '../api/client'
import { OverallRemark } from '../components/OverallRemark'
import {
  ErrorBanner,
  GradeBadge,
  Icons,
  LoadingBlock,
  PageHeader,
  PerformanceBadge,
  StatusBadge,
  categoryStyle,
  formatDate,
  scoreColor,
} from '../components/common'
import { useAsync } from '../hooks/useAsync'
import type { StudentDetail, StudentRemark, Submission } from '../types'

/** One submission, expandable to its full category breakdown and findings. */
function SubmissionCard({ submission, index }: { submission: Submission; index: number }) {
  const [open, setOpen] = useState(false)
  const report = submission.report
  const score = submission.total_score

  return (
    <li
      className="animate-fade-up rounded-xl border border-stone-200 transition hover:border-brand-300"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center gap-4 p-4 text-left"
      >
        <div className="min-w-0 flex-1">
          <p className="truncate font-semibold text-ink">
            {submission.assignment_title ?? `Assignment ${submission.assignment_id}`}
          </p>
          <p className="mt-0.5 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-xs text-stone-400">
            <span>{formatDate(submission.created_at)}</span>
            <span className="font-mono">
              {submission.repo_url.replace('https://github.com/', '')}
            </span>
          </p>
        </div>

        <StatusBadge status={submission.status} />

        {score === null ? (
          <span className="w-16 text-right text-stone-300">—</span>
        ) : (
          <span className="flex w-16 items-center justify-end gap-2">
            <span
              className="text-xl font-extrabold tabular-nums"
              style={{ color: scoreColor(score / 100) }}
            >
              {score}
            </span>
          </span>
        )}
        <GradeBadge grade={submission.grade} />

        <span className={`text-stone-400 transition ${open ? 'rotate-90' : ''}`}>
          <Icons.Arrow className="h-4 w-4" />
        </span>
      </button>

      {open && (
        <div className="border-t border-stone-100 p-4">
          {submission.status === 'failed' ? (
            <p className="text-sm text-brand-700">{submission.error_message}</p>
          ) : !report ? (
            <p className="text-sm text-muted">No report stored for this submission.</p>
          ) : (
            <div className="space-y-4">
              <p className="text-sm leading-relaxed text-stone-700">{report.summary}</p>

              <ul className="grid gap-2 sm:grid-cols-2">
                {report.category_scores.map((category) => {
                  const style = categoryStyle(category.key)
                  const fraction = category.max_score
                    ? category.score / category.max_score
                    : 0
                  return (
                    <li key={category.key} className="flex items-center gap-2.5">
                      <span className="w-32 shrink-0 truncate text-xs font-medium text-stone-600">
                        {category.label}
                      </span>
                      <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-stone-100">
                        <span
                          className={`block h-full rounded-full bg-gradient-to-r ${style.gradient}`}
                          style={{ width: `${Math.max(fraction * 100, 2)}%` }}
                        />
                      </span>
                      <span className="w-12 shrink-0 text-right text-xs font-bold tabular-nums text-stone-500">
                        {category.score}/{category.max_score}
                      </span>
                    </li>
                  )
                })}
              </ul>

              {report.improvements.length > 0 && (
                <div>
                  <p className="mb-1.5 text-[11px] font-bold uppercase tracking-wide text-stone-400">
                    Top issues
                  </p>
                  <ul className="space-y-1">
                    {report.improvements.slice(0, 3).map((item, position) => (
                      <li key={position} className="flex gap-2 text-xs text-stone-600">
                        <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-brand-500" />
                        {item.title}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <Link
                to={`/submissions/${submission.id}`}
                className="btn-soft !py-1.5 !text-xs"
              >
                Open full report
                <Icons.Arrow className="h-3 w-3" />
              </Link>
            </div>
          )}
        </div>
      )}
    </li>
  )
}

export function AdminStudentDetail() {
  const { id } = useParams<{ id: string }>()
  const studentId = Number(id)
  const { data, loading, error } = useAsync(() => api.adminStudent(studentId), [studentId])
  const [detail, setDetail] = useState<StudentDetail | null>(null)

  useEffect(() => setDetail(data), [data])

  if (loading) return <LoadingBlock rows={2} />
  if (error || !detail) return <ErrorBanner message={error ?? 'Student not found.'} />

  const { performance, submissions, weeks, recent_days: recentDays, remark } = detail
  const programme = performance.programme
  const hasWork = submissions.length > 0 || programme.submitted_days > 0

  function handleGenerated(next: StudentRemark) {
    setDetail((current) => (current ? { ...current, remark: next } : current))
  }

  return (
    <>
      <PageHeader
        eyebrow="Student review"
        title={performance.student_name}
        subtitle={
          <span className="flex flex-wrap items-center gap-x-3 gap-y-2">
            <PerformanceBadge
              level={performance.performance_level}
              tone={performance.performance_tone}
            />
            <span>{performance.email}</span>
            <span>· joined {formatDate(performance.joined_at)}</span>
            {performance.last_active && <span>· last active {formatDate(performance.last_active)}</span>}
          </span>
        }
        action={
          <Link to="/admin/students" className="btn-ghost">
            <Icons.Back className="h-4 w-4" />
            All students
          </Link>
        }
      />

      {/* ----------------------------------------------------------- stats */}
      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          {
            label: 'Average score',
            value: performance.average_score ?? '—',
            Icon: Icons.Target,
            tone: 'bg-brand-gradient',
          },
          {
            label: 'Best score',
            value: performance.best_score ?? '—',
            Icon: Icons.Check,
            tone: 'bg-gradient-to-br from-emerald-500 to-teal-600',
          },
          {
            label: 'Days submitted',
            value: `${programme.submitted_days}/${programme.elapsed_days || 0}`,
            Icon: Icons.Calendar,
            tone: 'bg-brand-deep',
          },
          {
            label: 'Hours logged',
            value: programme.total_hours,
            Icon: Icons.Clock,
            tone: 'bg-gradient-to-br from-amber-500 to-orange-600',
          },
        ].map((stat, index) => (
          <div
            key={stat.label}
            className="card animate-fade-up flex items-center gap-4 p-5"
            style={{ animationDelay: `${index * 60}ms` }}
          >
            <span
              className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl ${stat.tone} text-white shadow-lift`}
            >
              <stat.Icon className="h-5 w-5" />
            </span>
            <div>
              <p className="text-2xl font-extrabold tabular-nums text-ink">{stat.value}</p>
              <p className="text-[11px] font-bold uppercase tracking-wide text-stone-400">
                {stat.label}
              </p>
            </div>
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        {/* --------------------------------------------------- submissions */}
        <section className="card animate-fade-up p-6 lg:col-span-3">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="font-bold text-ink">
              Submitted work
              <span className="ml-2 text-sm font-medium text-stone-400">
                {submissions.length}
              </span>
            </h2>
            <p className="text-xs text-stone-400">Click any row for the breakdown</p>
          </div>

          {submissions.length === 0 ? (
            <p className="py-10 text-center text-sm text-muted">
              This student hasn&apos;t submitted anything yet.
            </p>
          ) : (
            <ul className="space-y-2.5">
              {submissions.map((submission, index) => (
                <SubmissionCard key={submission.id} submission={submission} index={index} />
              ))}
            </ul>
          )}
        </section>

        {/* ---------------------------------------------- daily programme */}
        <section className="card animate-fade-up h-fit p-6 lg:col-span-2">
          <h2 className="mb-1 font-bold text-ink">Weekly consistency</h2>
          <p className="mb-5 text-xs text-muted">
            Day 1 was {programme.enrolled_on} · currently day {programme.current_day}
          </p>

          <ul className="space-y-3">
            {weeks.map((week) => (
              <li key={week.week_number} className="flex items-center gap-3">
                <span className="w-14 shrink-0 text-xs font-bold text-stone-500">
                  Week {week.week_number}
                </span>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-stone-100">
                  <div
                    className="h-full rounded-full bg-brand-gradient"
                    style={{
                      width: `${Math.max(week.completion * 100, week.elapsed_days ? 2 : 0)}%`,
                    }}
                  />
                </div>
                <span className="w-16 shrink-0 text-right text-xs tabular-nums text-stone-500">
                  {week.elapsed_days ? `${week.submitted}/${week.elapsed_days}` : '—'}
                </span>
              </li>
            ))}
          </ul>

          {recentDays.length > 0 && (
            <>
              <h3 className="mb-3 mt-7 text-sm font-bold text-ink">Recent entries</h3>
              <ul className="space-y-3">
                {[...recentDays].reverse().map((day) => (
                  <li
                    key={day.day_number}
                    className="rounded-xl border border-stone-200 bg-stone-50 p-3"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-bold text-brand-700">
                        Day {day.day_number}
                      </span>
                      <span className="text-[11px] text-stone-400">
                        {day.date} · {day.entry?.hours ?? 0}h · {day.entry?.status}
                      </span>
                    </div>
                    {day.entry?.notes && (
                      <p className="mt-1.5 line-clamp-3 text-xs leading-relaxed text-stone-600">
                        {day.entry.notes}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      </div>

      {/* --------------------------------------------- the overall verdict */}
      <OverallRemark
        studentId={studentId}
        studentName={performance.student_name}
        remark={remark}
        canGenerate={hasWork}
        onGenerated={handleGenerated}
      />
    </>
  )
}

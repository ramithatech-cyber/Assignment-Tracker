import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { api } from '../api/client'
import {
  EmptyState,
  ErrorBanner,
  Icons,
  LoadingBlock,
  PageHeader,
  PerformanceBadge,
  formatDate,
  scoreColor,
} from '../components/common'
import { useAsync } from '../hooks/useAsync'

type SortKey = 'performance' | 'name' | 'score' | 'daily'

export function AdminStudents() {
  const { data: rows, loading, error } = useAsync(() => api.adminStudents())
  const [sort, setSort] = useState<SortKey>('performance')
  const [query, setQuery] = useState('')
  const navigate = useNavigate()

  const visible = useMemo(() => {
    const term = query.trim().toLowerCase()
    const list = (rows ?? []).filter(
      (row) =>
        !term ||
        row.student_name.toLowerCase().includes(term) ||
        row.email.toLowerCase().includes(term),
    )
    return [...list].sort((a, b) => {
      if (sort === 'name') return a.student_name.localeCompare(b.student_name)
      if (sort === 'score') return (b.average_score ?? -1) - (a.average_score ?? -1)
      if (sort === 'daily') return b.programme.completion - a.programme.completion
      return (b.performance_index ?? -1) - (a.performance_index ?? -1)
    })
  }, [rows, sort, query])

  if (loading) return <LoadingBlock rows={3} />
  if (error) return <ErrorBanner message={error} />

  function SortButton({ label, sortKey }: { label: string; sortKey: SortKey }) {
    const active = sort === sortKey
    return (
      <button
        type="button"
        onClick={() => setSort(sortKey)}
        className={`inline-flex items-center gap-1 transition ${
          active ? 'text-brand-600' : 'hover:text-stone-800'
        }`}
      >
        {label}
        <span className={active ? 'opacity-100' : 'opacity-0'}>&darr;</span>
      </button>
    )
  }

  return (
    <>
      <PageHeader
        eyebrow="Admin"
        title="Students"
        subtitle={`${rows?.length ?? 0} student${rows?.length === 1 ? '' : 's'} · submissions and daily programme progress`}
        action={
          <Link to="/admin" className="btn-ghost">
            <Icons.Back className="h-4 w-4" />
            Dashboard
          </Link>
        }
      />

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <input
          className="input max-w-sm"
          placeholder="Search by name or email..."
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <p className="text-xs text-stone-400">
          Click a student to review every submission and write an overall remark.
        </p>
      </div>

      {visible.length === 0 ? (
        <EmptyState
          title={query ? 'No students match that search' : 'No students yet'}
          hint={query ? 'Try a different name or email.' : 'They will appear here once they register.'}
        />
      ) : (
        <div className="card animate-fade-up overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-stone-50 text-left text-[11px] uppercase tracking-wider text-stone-500">
              <tr>
                <th className="px-5 py-3.5 font-bold">
                  <SortButton label="Student" sortKey="name" />
                </th>
                <th className="px-4 py-3.5 font-bold">
                  <SortButton label="Level" sortKey="performance" />
                </th>
                <th className="px-4 py-3.5 text-right font-bold">
                  <SortButton label="Avg score" sortKey="score" />
                </th>
                <th className="px-4 py-3.5 font-bold">Submissions</th>
                <th className="px-4 py-3.5 font-bold">
                  <SortButton label="Daily programme" sortKey="daily" />
                </th>
                <th className="px-5 py-3.5 font-bold">Last active</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {visible.map((row) => {
                const completion = row.programme.elapsed_days
                  ? Math.round(row.programme.completion * 100)
                  : null
                return (
                  <tr
                    key={row.student_id}
                    onClick={() => navigate(`/admin/students/${row.student_id}`)}
                    className="cursor-pointer transition hover:bg-brand-50/60"
                  >
                    <td className="px-5 py-4">
                      {/* The whole row is clickable; the link keeps it
                          keyboard-reachable and right-clickable. */}
                      <Link
                        to={`/admin/students/${row.student_id}`}
                        onClick={(event) => event.stopPropagation()}
                        className="font-semibold text-ink hover:text-brand-600 hover:underline"
                      >
                        {row.student_name}
                      </Link>
                      <p className="text-xs text-stone-400">{row.email}</p>
                    </td>

                    <td className="px-4 py-4">
                      <PerformanceBadge level={row.performance_level} tone={row.performance_tone} />
                      {row.performance_index !== null && (
                        <p className="mt-1 text-[11px] tabular-nums text-stone-400">
                          index {row.performance_index}
                        </p>
                      )}
                    </td>

                    <td className="px-4 py-4 text-right">
                      {row.average_score === null ? (
                        <span className="text-stone-300">—</span>
                      ) : (
                        <>
                          <span
                            className="text-lg font-extrabold tabular-nums"
                            style={{ color: scoreColor(row.average_score / 100) }}
                          >
                            {row.average_score}
                          </span>
                          {row.best_score !== null && (
                            <p className="text-[11px] tabular-nums text-stone-400">
                              best {row.best_score}
                            </p>
                          )}
                        </>
                      )}
                    </td>

                    <td className="px-4 py-4">
                      <span className="font-semibold tabular-nums text-stone-700">
                        {row.submission_count}
                      </span>
                      {row.failed_count > 0 && (
                        <p className="text-[11px] text-brand-600">{row.failed_count} failed</p>
                      )}
                    </td>

                    <td className="px-4 py-4">
                      {completion === null ? (
                        <span className="text-xs text-stone-400">Not started</span>
                      ) : (
                        <div className="min-w-[7rem]">
                          <div className="mb-1 flex items-center justify-between text-xs">
                            <span className="font-semibold tabular-nums text-stone-600">
                              {row.programme.submitted_days}/{row.programme.elapsed_days}
                            </span>
                            <span className="tabular-nums text-stone-400">{completion}%</span>
                          </div>
                          <div className="h-1.5 w-full overflow-hidden rounded-full bg-stone-100">
                            <div
                              className="h-full rounded-full bg-brand-gradient"
                              style={{ width: `${Math.max(completion, 2)}%` }}
                            />
                          </div>
                          {row.programme.current_streak > 0 && (
                            <p className="mt-1 flex items-center gap-1 text-[11px] text-amber-600">
                              <Icons.Flame className="h-3 w-3" />
                              {row.programme.current_streak} day streak
                            </p>
                          )}
                        </div>
                      )}
                    </td>

                    <td className="whitespace-nowrap px-5 py-4 text-xs text-stone-500">
                      {row.last_active ? formatDate(row.last_active) : '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

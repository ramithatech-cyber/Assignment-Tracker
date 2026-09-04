import { useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { api } from '../api/client'
import {
  EmptyState,
  ErrorBanner,
  GradeBadge,
  Icons,
  LoadingBlock,
  PageHeader,
  StatusBadge,
  formatDate,
  scoreColor,
} from '../components/common'
import { useAsync } from '../hooks/useAsync'
import type { Submission } from '../types'

type SortKey = 'student' | 'score' | 'date'

export function AssignmentSubmissions() {
  const { id } = useParams<{ id: string }>()
  const assignmentId = Number(id)
  const [sort, setSort] = useState<SortKey>('score')
  const navigate = useNavigate()

  const assignment = useAsync(() => api.getAssignment(assignmentId), [assignmentId])
  const submissions = useAsync(() => api.assignmentSubmissions(assignmentId), [assignmentId])

  const rows = useMemo(() => {
    const list: Submission[] = [...(submissions.data ?? [])]
    return list.sort((a, b) => {
      if (sort === 'student') return (a.student_name ?? '').localeCompare(b.student_name ?? '')
      if (sort === 'date') return b.created_at.localeCompare(a.created_at)
      return (b.total_score ?? -1) - (a.total_score ?? -1)
    })
  }, [submissions.data, sort])

  const graded = rows.filter((row) => row.total_score !== null)
  const scores = graded.map((row) => row.total_score ?? 0)
  const average = scores.length
    ? Math.round((scores.reduce((sum, value) => sum + value, 0) / scores.length) * 10) / 10
    : null

  if (assignment.loading || submissions.loading) return <LoadingBlock rows={2} />
  if (assignment.error) return <ErrorBanner message={assignment.error} />

  function SortButton({ label, sortKey }: { label: string; sortKey: SortKey }) {
    const active = sort === sortKey
    return (
      <button
        type="button"
        onClick={() => setSort(sortKey)}
        className={`inline-flex items-center gap-1 transition ${
          active ? 'text-brand-600' : 'hover:text-slate-800'
        }`}
      >
        {label}
        <span className={active ? 'opacity-100' : 'opacity-0'}>↓</span>
      </button>
    )
  }

  return (
    <>
      <PageHeader
        eyebrow="Submissions"
        title={assignment.data?.title ?? 'Submissions'}
        subtitle={`${rows.length} ${rows.length === 1 ? 'submission' : 'submissions'}`}
        action={
          <Link to="/admin/assignments" className="btn-ghost">
            <Icons.Back className="h-4 w-4" />
            Back
          </Link>
        }
      />

      <ErrorBanner message={submissions.error} />

      {graded.length > 0 && (
        <div className="mb-8 grid gap-4 sm:grid-cols-3">
          {[
            { label: 'Class average', value: `${average}`, gradient: 'from-brand-500 to-violet-600', Icon: Icons.Target },
            { label: 'Highest', value: `${Math.max(...scores)}`, gradient: 'from-emerald-500 to-teal-600', Icon: Icons.Check },
            { label: 'Lowest', value: `${Math.min(...scores)}`, gradient: 'from-rose-400 to-pink-600', Icon: Icons.Warning },
          ].map((stat, index) => (
            <div
              key={stat.label}
              className="card animate-fade-up flex items-center gap-4 p-5"
              style={{ animationDelay: `${index * 70}ms` }}
            >
              <span
                className={`flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br ${stat.gradient} text-white shadow-lift`}
              >
                <stat.Icon className="h-5 w-5" />
              </span>
              <div>
                <p className="text-2xl font-extrabold tabular-nums text-ink">
                  {stat.value}
                  <span className="text-sm font-semibold text-slate-400">/100</span>
                </p>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  {stat.label}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {rows.length === 0 ? (
        <EmptyState title="No submissions yet" hint="Students' reports will appear here." />
      ) : (
        <div className="card animate-fade-up overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50/80 text-left text-[11px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-5 py-3.5 font-bold">
                  <SortButton label="Student" sortKey="student" />
                </th>
                <th className="px-5 py-3.5 font-bold">
                  <SortButton label="Submitted" sortKey="date" />
                </th>
                <th className="px-5 py-3.5 font-bold">Repository</th>
                <th className="px-5 py-3.5 font-bold">Status</th>
                <th className="px-5 py-3.5 text-right font-bold">
                  <SortButton label="Score" sortKey="score" />
                </th>
                <th className="px-5 py-3.5 text-right font-bold">Report</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((submission) => (
                <tr
                  key={submission.id}
                  onClick={() => navigate(`/admin/students/${submission.student_id}`)}
                  className="cursor-pointer transition hover:bg-brand-50/60"
                >
                  <td className="px-5 py-4">
                    {/* The student name opens that student's full record, not
                        this one submission -- the Report column does that. */}
                    <Link
                      to={`/admin/students/${submission.student_id}`}
                      onClick={(event) => event.stopPropagation()}
                      className="font-semibold text-ink hover:text-brand-600 hover:underline"
                    >
                      {submission.student_name ?? `Student ${submission.student_id}`}
                    </Link>
                  </td>
                  <td className="whitespace-nowrap px-5 py-4 text-slate-600">
                    {formatDate(submission.created_at)}
                  </td>
                  <td className="max-w-xs truncate px-5 py-4">
                    <a
                      href={submission.repo_url}
                      target="_blank"
                      rel="noreferrer"
                      className="font-mono text-xs text-slate-500 hover:text-brand-600 hover:underline"
                    >
                      {submission.repo_url.replace('https://github.com/', '')}
                    </a>
                  </td>
                  <td className="px-5 py-4">
                    <StatusBadge status={submission.status} />
                  </td>
                  <td className="px-5 py-4">
                    {submission.total_score === null ? (
                      <span className="block text-right text-slate-300">—</span>
                    ) : (
                      <span className="flex items-center justify-end gap-2.5">
                        <span
                          className="text-lg font-extrabold tabular-nums"
                          style={{ color: scoreColor(submission.total_score / 100) }}
                        >
                          {submission.total_score}
                        </span>
                        <GradeBadge grade={submission.grade} />
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-4 text-right">
                    <Link
                      to={`/submissions/${submission.id}`}
                      onClick={(event) => event.stopPropagation()}
                      className="text-xs font-semibold text-brand-600 hover:underline"
                    >
                      Open
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

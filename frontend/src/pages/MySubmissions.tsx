import { Link, useNavigate } from 'react-router-dom'

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

export function MySubmissions() {
  const submissions = useAsync(() => api.mySubmissions())
  const assignments = useAsync(() => api.listAssignments())
  const navigate = useNavigate()

  if (submissions.loading) return <LoadingBlock rows={3} />
  if (submissions.error) return <ErrorBanner message={submissions.error} />

  const rows = submissions.data ?? []
  const graded = rows.filter((s) => s.total_score !== null)
  const best = graded.length ? Math.max(...graded.map((s) => s.total_score ?? 0)) : null
  const open = (assignments.data ?? []).filter((a) => a.is_open)

  return (
    <>
      <PageHeader
        eyebrow="My work"
        title="My submissions"
        subtitle={
          best !== null
            ? `${rows.length} submitted · best score ${best}/100`
            : 'Every repository you have submitted for review.'
        }
      />

      {/* Assignments are no longer in the menu, so this is the way in to
          submitting a repository. */}
      {open.length > 0 && (
        <section className="card card-accent animate-fade-up mb-6 p-6">
          <h2 className="mb-1 flex items-center gap-2 font-bold text-ink">
            <Icons.Github className="h-4 w-4 text-brand-600" />
            Submit an assignment
          </h2>
          <p className="mb-4 text-sm text-muted">
            Pick an assignment to paste a GitHub repository and get it reviewed.
          </p>

          <ul className="grid gap-3 sm:grid-cols-2">
            {open.map((assignment) => (
              <li key={assignment.id}>
                <Link
                  to={`/assignments/${assignment.id}`}
                  className="flex items-center gap-3 rounded-xl border border-stone-200 p-3.5 transition hover:-translate-y-0.5 hover:border-brand-300 hover:bg-brand-50/50"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-ink">
                      {assignment.title}
                    </p>
                    <p className="mt-0.5 text-xs text-stone-400">
                      {assignment.my_submission_id ? 'Submitted — resubmit' : 'Not submitted yet'}
                      {assignment.due_date && ` · due ${formatDate(assignment.due_date)}`}
                    </p>
                  </div>
                  {assignment.my_submission_id ? (
                    <Icons.Check className="h-4 w-4 shrink-0 text-emerald-500" />
                  ) : (
                    <Icons.Arrow className="h-4 w-4 shrink-0 text-brand-500" />
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      {rows.length === 0 ? (
        <EmptyState
          title="Nothing submitted yet"
          hint={
            open.length > 0
              ? 'Pick an assignment above to get started.'
              : 'There are no open assignments right now.'
          }
        />
      ) : (
        <div className="card animate-fade-up overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-stone-50 text-left text-[11px] uppercase tracking-wider text-stone-500">
              <tr>
                <th className="px-5 py-3.5 font-bold">Assignment</th>
                <th className="px-5 py-3.5 font-bold">Repository</th>
                <th className="px-5 py-3.5 font-bold">Submitted</th>
                <th className="px-5 py-3.5 font-bold">Status</th>
                <th className="px-5 py-3.5 text-right font-bold">Score</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {rows.map((submission) => (
                <tr
                  key={submission.id}
                  onClick={() => navigate(`/submissions/${submission.id}`)}
                  className="cursor-pointer transition hover:bg-brand-50/60"
                >
                  <td className="px-5 py-4">
                    <Link
                      to={`/submissions/${submission.id}`}
                      onClick={(event) => event.stopPropagation()}
                      className="font-semibold text-ink hover:text-brand-600 hover:underline"
                    >
                      {submission.assignment_title ?? `Assignment ${submission.assignment_id}`}
                    </Link>
                  </td>
                  <td className="max-w-xs truncate px-5 py-4 font-mono text-xs text-stone-500">
                    {submission.repo_url.replace('https://github.com/', '')}
                  </td>
                  <td className="whitespace-nowrap px-5 py-4 text-stone-600">
                    {formatDate(submission.created_at)}
                  </td>
                  <td className="px-5 py-4">
                    <StatusBadge status={submission.status} />
                  </td>
                  <td className="px-5 py-4">
                    {submission.total_score === null ? (
                      <span className="block text-right text-stone-300">—</span>
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
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

import { Link, useNavigate, useParams } from 'react-router-dom'

import { api } from '../api/client'
import { SubmitRepoForm } from '../components/SubmitRepoForm'
import {
  ErrorBanner,
  Icons,
  LoadingBlock,
  PageHeader,
  categoryStyle,
  formatDate,
} from '../components/common'
import { useAsync } from '../hooks/useAsync'

const RUBRIC_PREVIEW = [
  { key: 'code_quality', label: 'Code Quality', max: 20 },
  { key: 'correctness', label: 'Correctness', max: 20 },
  { key: 'structure', label: 'Structure', max: 15 },
  { key: 'documentation', label: 'Documentation', max: 15 },
  { key: 'testing', label: 'Testing', max: 10 },
  { key: 'git_hygiene', label: 'Git Hygiene', max: 10 },
  { key: 'security', label: 'Security', max: 10 },
]

export function AssignmentDetail() {
  const { id } = useParams<{ id: string }>()
  const assignmentId = Number(id)
  const navigate = useNavigate()

  const { data: assignment, loading, error } = useAsync(
    () => api.getAssignment(assignmentId),
    [assignmentId],
  )

  if (loading) return <LoadingBlock rows={2} />
  if (error || !assignment) return <ErrorBanner message={error ?? 'Assignment not found.'} />

  return (
    <>
      <PageHeader
        eyebrow="Assignment"
        title={assignment.title}
        subtitle={
          <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span>Set by {assignment.teacher_name ?? 'unknown'}</span>
            {assignment.due_date && (
              <span className="inline-flex items-center gap-1">
                <Icons.Clock className="h-3.5 w-3.5" />
                Due {formatDate(assignment.due_date)}
              </span>
            )}
          </span>
        }
        action={
          <Link to="/submissions" className="btn-ghost">
            <Icons.Back className="h-4 w-4" />
            Back
          </Link>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <section className="card card-accent animate-fade-up p-7">
            <h2 className="mb-5 flex items-center gap-2 text-lg font-bold text-ink">
              <Icons.Github className="h-5 w-5 text-brand-500" />
              Submit your work
            </h2>
            {assignment.is_open ? (
              <SubmitRepoForm
                assignmentId={assignment.id}
                onComplete={(submission) => navigate(`/submissions/${submission.id}`)}
              />
            ) : (
              <p className="text-sm text-muted">This assignment is closed for submissions.</p>
            )}
          </section>

          {assignment.description && (
            <section className="card animate-fade-up p-7">
              <h2 className="mb-3 text-lg font-bold text-ink">Description</h2>
              <p className="whitespace-pre-wrap text-[15px] leading-relaxed text-slate-700">
                {assignment.description}
              </p>
            </section>
          )}
        </div>

        <aside className="space-y-6">
          <section className="card animate-fade-up p-6">
            <h2 className="mb-3 flex items-center gap-2 font-bold text-ink">
              <Icons.Target className="h-4 w-4 text-emerald-500" />
              What you&apos;ll be graded on
            </h2>
            {assignment.requirements ? (
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
                {assignment.requirements}
              </p>
            ) : (
              <p className="text-sm text-muted">No specific requirements were given.</p>
            )}
          </section>

          <section className="card animate-fade-up p-6">
            <h2 className="mb-4 font-bold text-ink">Scoring rubric</h2>
            <ul className="space-y-2.5">
              {RUBRIC_PREVIEW.map((item) => {
                const style = categoryStyle(item.key)
                const { Icon } = style
                return (
                  <li key={item.key} className="flex items-center gap-2.5">
                    <span
                      className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br ${style.gradient} text-white`}
                    >
                      <Icon className="h-3.5 w-3.5" />
                    </span>
                    <span className="flex-1 text-sm font-medium text-slate-700">{item.label}</span>
                    <span className="text-xs font-bold tabular-nums text-slate-400">
                      {item.max}
                    </span>
                  </li>
                )
              })}
            </ul>
            <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3">
              <span className="text-sm font-bold text-ink">Total</span>
              <span className="gradient-text text-lg font-extrabold">100</span>
            </div>
          </section>
        </aside>
      </div>
    </>
  )
}

import { Link } from 'react-router-dom'

import { api } from '../api/client'
import {
  EmptyState,
  ErrorBanner,
  Icons,
  LoadingBlock,
  PageHeader,
  formatDate,
} from '../components/common'
import { useAuth } from '../contexts/AuthContext'
import { useAsync } from '../hooks/useAsync'

export function TeacherDashboard() {
  const { user } = useAuth()
  const { data: assignments, loading, error } = useAsync(() => api.listAssignments())

  if (loading) return <LoadingBlock />
  if (error) return <ErrorBanner message={error} />

  const totalSubmissions = assignments?.reduce((sum, a) => sum + a.submission_count, 0) ?? 0

  return (
    <>
      <PageHeader
        eyebrow={`Hello, ${user?.full_name?.split(' ')[0] ?? 'there'}`}
        title="Your assignments"
        subtitle={
          assignments?.length
            ? `${assignments.length} assignment${assignments.length === 1 ? '' : 's'} · ${totalSubmissions} submission${totalSubmissions === 1 ? '' : 's'} received`
            : 'Create an assignment, then review every student report.'
        }
        action={
          <Link to="/admin/assignments/new" className="btn-primary">
            <Icons.Plus className="h-4 w-4" />
            New assignment
          </Link>
        }
      />

      {!assignments?.length ? (
        <EmptyState
          title="No assignments yet"
          hint="Create one and share it with your students."
          action={
            <Link to="/admin/assignments/new" className="btn-primary">
              <Icons.Plus className="h-4 w-4" />
              Create your first assignment
            </Link>
          }
        />
      ) : (
        <ul className="grid gap-5 md:grid-cols-2">
          {assignments.map((assignment, index) => (
            <li
              key={assignment.id}
              className="card card-hover card-accent animate-fade-up p-6"
              style={{ animationDelay: `${index * 60}ms` }}
            >
              <div className="flex items-start justify-between gap-3">
                <h2 className="text-lg font-bold leading-snug text-ink">{assignment.title}</h2>
                <span
                  className={`chip shrink-0 ${
                    assignment.submission_count > 0
                      ? 'border-brand-200 bg-brand-50 text-brand-700'
                      : 'border-slate-200 bg-slate-100 text-slate-500'
                  }`}
                >
                  {assignment.submission_count}
                  {assignment.submission_count === 1 ? ' submission' : ' submissions'}
                </span>
              </div>

              {assignment.description && (
                <p className="mt-2.5 line-clamp-2 text-sm leading-relaxed text-slate-600">
                  {assignment.description}
                </p>
              )}

              <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
                <span>Created {formatDate(assignment.created_at)}</span>
                {assignment.due_date && <span>Due {formatDate(assignment.due_date)}</span>}
                {!assignment.is_open && (
                  <span className="font-semibold text-rose-500">Closed</span>
                )}
              </div>

              <Link to={`/admin/assignments/${assignment.id}`} className="btn-ghost mt-5">
                View submissions
                <Icons.Arrow className="h-4 w-4" />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}

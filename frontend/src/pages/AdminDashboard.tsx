import { Link, useNavigate } from 'react-router-dom'

import { api } from '../api/client'
import {
  EmptyState,
  ErrorBanner,
  Icons,
  LoadingBlock,
  PageHeader,
  PerformanceBadge,
  scoreColor,
} from '../components/common'
import { useAuth } from '../contexts/AuthContext'
import { useAsync } from '../hooks/useAsync'

const LEVEL_ORDER = ['Excellent', 'Strong', 'On track', 'Needs support', 'At risk', 'No data']

const LEVEL_BAR: Record<string, string> = {
  Excellent: 'bg-emerald-500',
  Strong: 'bg-lime-500',
  'On track': 'bg-amber-500',
  'Needs support': 'bg-orange-500',
  'At risk': 'bg-brand-600',
  'No data': 'bg-stone-300',
}

function Stat({
  label,
  value,
  sub,
  Icon,
  tone = 'brand',
}: {
  label: string
  value: string | number
  sub?: string
  Icon: (p: { className?: string }) => JSX.Element
  tone?: 'brand' | 'emerald' | 'amber' | 'deep'
}) {
  const tones = {
    brand: 'bg-brand-gradient',
    deep: 'bg-brand-deep',
    emerald: 'bg-gradient-to-br from-emerald-500 to-teal-600',
    amber: 'bg-gradient-to-br from-amber-500 to-orange-600',
  }
  return (
    <div className="card animate-fade-up flex items-center gap-4 p-5">
      <span
        className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl ${tones[tone]} text-white shadow-lift`}
      >
        <Icon className="h-5 w-5" />
      </span>
      <div className="min-w-0">
        <p className="text-2xl font-extrabold tabular-nums leading-tight text-ink">{value}</p>
        <p className="text-[11px] font-bold uppercase tracking-wide text-stone-400">{label}</p>
        {sub && <p className="mt-0.5 truncate text-xs text-stone-500">{sub}</p>}
      </div>
    </div>
  )
}

export function AdminDashboard() {
  const { user } = useAuth()
  const { data, loading, error } = useAsync(() => api.adminOverview())
  const navigate = useNavigate()

  if (loading) return <LoadingBlock rows={2} />
  if (error) return <ErrorBanner message={error} />
  if (!data) return null

  const totalStudents = data.students
  const avgCompletion =
    data.average_completion === null ? null : Math.round(data.average_completion * 100)

  return (
    <>
      <PageHeader
        eyebrow={`Hello, ${user?.full_name?.split(' ')[0] ?? 'there'}`}
        title="Dashboard"
        subtitle="Student submissions and performance across your assignments."
        action={
          <Link to="/admin/students" className="btn-primary">
            <Icons.Users className="h-4 w-4" />
            All students
          </Link>
        }
      />

      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Students" value={totalStudents} Icon={Icons.Users} tone="deep" />
        <Stat
          label="Submissions"
          value={data.submissions}
          sub={`${data.assignments} assignment${data.assignments === 1 ? '' : 's'}`}
          Icon={Icons.Inbox}
        />
        <Stat
          label="Average score"
          value={data.average_score ?? '—'}
          sub={data.average_score === null ? 'No graded submissions yet' : 'out of 100'}
          Icon={Icons.Target}
          tone="emerald"
        />
        <Stat
          label="Daily completion"
          value={avgCompletion === null ? '—' : `${avgCompletion}%`}
          sub="Across the 45-day programme"
          Icon={Icons.Calendar}
          tone="amber"
        />
      </div>

      {totalStudents === 0 ? (
        <EmptyState
          title="No students yet"
          hint="Once students register and submit, their performance appears here."
        />
      ) : (
        <div className="grid gap-6 lg:grid-cols-5">
          {/* ------------------------------------------------ distribution */}
          <section className="card animate-fade-up p-6 lg:col-span-2">
            <h2 className="mb-1 font-bold text-ink">Performance levels</h2>
            <p className="mb-5 text-xs leading-relaxed text-muted">
              Blended from assignment scores (60%) and daily consistency (40%).
            </p>

            <ul className="space-y-3">
              {LEVEL_ORDER.filter((level) => data.distribution[level]).map((level) => {
                const count = data.distribution[level]
                const share = count / totalStudents
                return (
                  <li key={level}>
                    <div className="mb-1.5 flex items-center justify-between text-sm">
                      <span className="font-semibold text-stone-700">{level}</span>
                      <span className="font-bold tabular-nums text-stone-500">{count}</span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-stone-100">
                      <div
                        className={`h-full rounded-full ${LEVEL_BAR[level] ?? 'bg-stone-300'}`}
                        style={{
                          width: `${Math.max(share * 100, 3)}%`,
                          transition: 'width 800ms ease-out',
                        }}
                      />
                    </div>
                  </li>
                )
              })}
            </ul>

            {data.at_risk > 0 && (
              <div className="mt-6 flex items-start gap-2.5 rounded-xl border border-brand-200 bg-brand-50 p-3.5">
                <Icons.Warning className="mt-0.5 h-4 w-4 shrink-0 text-brand-600" />
                <p className="text-xs leading-relaxed text-brand-900">
                  <strong>
                    {data.at_risk} student{data.at_risk === 1 ? '' : 's'}
                  </strong>{' '}
                  {data.at_risk === 1 ? 'is' : 'are'} at risk or need support.{' '}
                  <Link to="/admin/students" className="font-semibold underline">
                    Review them
                  </Link>
                  .
                </p>
              </div>
            )}
          </section>

          {/* --------------------------------------------------- top table */}
          <section className="card animate-fade-up overflow-hidden lg:col-span-3">
            <div className="flex items-center justify-between border-b border-stone-100 px-6 py-4">
              <h2 className="font-bold text-ink">Top performers</h2>
              <Link
                to="/admin/students"
                className="text-sm font-semibold text-brand-600 hover:underline"
              >
                View all
              </Link>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-stone-50 text-left text-[11px] uppercase tracking-wider text-stone-500">
                  <tr>
                    <th className="px-6 py-3 font-bold">Student</th>
                    <th className="px-4 py-3 font-bold">Level</th>
                    <th className="px-4 py-3 text-right font-bold">Avg score</th>
                    <th className="px-6 py-3 text-right font-bold">Daily</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100">
                  {data.top_performers.map((row) => (
                    <tr
                      key={row.student_id}
                      onClick={() => navigate(`/admin/students/${row.student_id}`)}
                      className="cursor-pointer transition hover:bg-brand-50/60"
                    >
                      <td className="px-6 py-3.5">
                        <Link
                          to={`/admin/students/${row.student_id}`}
                          onClick={(event) => event.stopPropagation()}
                          className="font-semibold text-ink hover:text-brand-600 hover:underline"
                        >
                          {row.student_name}
                        </Link>
                        <p className="text-xs text-stone-400">
                          {row.submission_count} submission
                          {row.submission_count === 1 ? '' : 's'}
                        </p>
                      </td>
                      <td className="px-4 py-3.5">
                        <PerformanceBadge
                          level={row.performance_level}
                          tone={row.performance_tone}
                        />
                      </td>
                      <td className="px-4 py-3.5 text-right">
                        {row.average_score === null ? (
                          <span className="text-stone-300">—</span>
                        ) : (
                          <span
                            className="font-extrabold tabular-nums"
                            style={{ color: scoreColor(row.average_score / 100) }}
                          >
                            {row.average_score}
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-3.5 text-right font-semibold tabular-nums text-stone-600">
                        {row.programme.submitted_days}/{row.programme.elapsed_days || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}
    </>
  )
}

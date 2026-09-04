import { Link, useParams } from 'react-router-dom'

import { api } from '../api/client'
import { CategoryBars } from '../components/CategoryBars'
import { FindingsList } from '../components/FindingsList'
import { ScoreGauge } from '../components/ScoreGauge'
import {
  ErrorBanner,
  Icons,
  LoadingBlock,
  PageHeader,
  StatusBadge,
  formatDate,
} from '../components/common'
import { useAsync } from '../hooks/useAsync'

const METRIC_STYLES = [
  'from-violet-500 to-purple-600',
  'from-sky-500 to-blue-600',
  'from-rose-400 to-pink-600',
  'from-teal-400 to-cyan-600',
]

function Metric({
  label,
  value,
  gradient,
  Icon,
}: {
  label: string
  value: string | number
  gradient: string
  Icon: (p: { className?: string }) => JSX.Element
}) {
  return (
    <div className="flex items-center gap-3">
      <span
        className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${gradient} text-white shadow-sm`}
      >
        <Icon className="h-4 w-4" />
      </span>
      <div>
        <p className="text-lg font-extrabold tabular-nums leading-tight text-ink">{value}</p>
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{label}</p>
      </div>
    </div>
  )
}

export function SubmissionReport() {
  const { id } = useParams<{ id: string }>()
  const submissionId = Number(id)
  const { data: submission, loading, error } = useAsync(
    () => api.getSubmission(submissionId),
    [submissionId],
  )

  if (loading) return <LoadingBlock rows={2} />
  if (error || !submission) return <ErrorBanner message={error ?? 'Submission not found.'} />

  const { report } = submission
  const metrics = (report?.static_metrics ?? {}) as Record<string, any>
  const repoUrl =
    submission.repo_owner && submission.repo_name
      ? `https://github.com/${submission.repo_owner}/${submission.repo_name}`
      : undefined

  return (
    <>
      <PageHeader
        eyebrow="Review report"
        title={submission.assignment_title ?? 'Submission'}
        subtitle={
          <span className="flex flex-wrap items-center gap-x-3 gap-y-2">
            <StatusBadge status={submission.status} />
            <a
              href={submission.repo_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 font-mono text-xs text-brand-600 hover:text-brand-700 hover:underline"
            >
              <Icons.Github className="h-3.5 w-3.5" />
              {submission.repo_url.replace('https://github.com/', '')}
            </a>
            <span>{formatDate(submission.created_at)}</span>
            {submission.student_name && <span>· {submission.student_name}</span>}
          </span>
        }
        action={
          <Link to="/submissions" className="btn-ghost">
            <Icons.Back className="h-4 w-4" />
            Back
          </Link>
        }
      />

      {submission.status === 'failed' && (
        <ErrorBanner message={submission.error_message ?? 'Analysis failed.'} />
      )}

      {report && (
        <div className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-3">
            <section className="card card-accent animate-scale-in flex flex-col items-center justify-center p-8">
              <ScoreGauge score={submission.total_score ?? 0} grade={submission.grade} />
            </section>

            <section className="card animate-fade-up p-7 lg:col-span-2">
              <h2 className="mb-3 flex items-center gap-2 text-lg font-bold text-ink">
                <Icons.Sparkle className="h-5 w-5 text-brand-500" />
                Summary
              </h2>
              <p className="text-[15px] leading-relaxed text-slate-700">{report.summary}</p>

              <div className="mt-7 grid grid-cols-2 gap-5 border-t border-slate-100 pt-6 sm:grid-cols-4">
                <Metric
                  label="Lines of code"
                  value={metrics.total_loc ?? '—'}
                  gradient={METRIC_STYLES[0]}
                  Icon={Icons.Code}
                />
                <Metric
                  label="Files scanned"
                  value={metrics.analysed_files ?? '—'}
                  gradient={METRIC_STYLES[1]}
                  Icon={Icons.Layers}
                />
                <Metric
                  label="Test files"
                  value={metrics.tests?.count ?? '—'}
                  gradient={METRIC_STYLES[2]}
                  Icon={Icons.Beaker}
                />
                <Metric
                  label="Commits"
                  value={metrics.git?.commit_count ?? '—'}
                  gradient={METRIC_STYLES[3]}
                  Icon={Icons.Branch}
                />
              </div>
            </section>
          </div>

          <section className="card animate-fade-up p-7">
            <h2 className="mb-6 text-lg font-bold text-ink">Score breakdown</h2>
            <CategoryBars categories={report.category_scores} />
          </section>

          {report.applied_caps.length > 0 && (
            <section className="card card-accent animate-fade-up overflow-hidden border-amber-200/70 bg-amber-50/60 p-6 before:bg-gradient-to-r before:from-amber-400 before:to-orange-500">
              <h2 className="flex items-center gap-2.5 text-base font-bold text-amber-900">
                <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-amber-400 to-orange-500 text-white shadow-sm">
                  <Icons.Warning className="h-4 w-4" />
                </span>
                Automatic limits applied to this score
              </h2>
              <p className="mb-4 mt-2 text-xs leading-relaxed text-amber-800">
                These were measured directly from your repository, so they apply regardless of what
                the AI review said.
              </p>
              <ul className="space-y-2">
                {report.applied_caps.map((cap, index) => (
                  <li
                    key={index}
                    className="flex items-start gap-2.5 rounded-lg bg-white/70 px-3 py-2 text-sm text-amber-900"
                  >
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500" />
                    {cap}
                  </li>
                ))}
              </ul>
            </section>
          )}

          <FindingsList
            strengths={report.strengths}
            improvements={report.improvements}
            repoUrl={repoUrl}
            branch={submission.default_branch}
          />

          <p className="pb-2 text-center text-xs text-slate-400">
            Reviewed by {report.llm_model} · {report.tokens_used.toLocaleString()} tokens ·{' '}
            {(report.duration_ms / 1000).toFixed(1)}s
            {submission.commit_sha && (
              <> · commit <code className="font-mono">{submission.commit_sha.slice(0, 7)}</code></>
            )}
          </p>
        </div>
      )}
    </>
  )
}

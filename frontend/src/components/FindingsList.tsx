import type { Improvement, Strength } from '../types'
import { Icons, SeverityChip } from './common'

function FileRef({
  file,
  repoUrl,
  branch,
  verified,
}: {
  file: string | null
  repoUrl?: string
  branch?: string
  verified?: boolean
}) {
  if (!file) return null

  const [path, line] = file.split(':')
  const body = (
    <code
      className={`inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 font-mono text-[11px] transition ${
        verified
          ? 'bg-brand-50 text-brand-700 hover:bg-brand-100'
          : 'bg-slate-100 text-slate-500'
      }`}
    >
      {file}
    </code>
  )

  // Only link out when the path was matched against the real file list, so a
  // model that invents a filename never produces a broken link.
  if (!verified || !repoUrl) {
    return (
      <span title={verified ? undefined : 'Path could not be matched to a file in the repository'}>
        {body}
      </span>
    )
  }

  const href = `${repoUrl}/blob/${branch || 'main'}/${path}${line ? `#L${line}` : ''}`
  return (
    <a href={href} target="_blank" rel="noreferrer">
      {body}
    </a>
  )
}

interface Props {
  strengths: Strength[]
  improvements: Improvement[]
  repoUrl?: string
  branch?: string
}

export function FindingsList({ strengths, improvements, repoUrl, branch }: Props) {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {/* ------------------------------------------------------------ good */}
      <section className="card card-accent overflow-hidden p-6 before:bg-gradient-to-r before:from-emerald-400 before:to-teal-500">
        <h2 className="mb-5 flex items-center gap-2.5 text-lg font-bold text-emerald-800">
          <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-400 to-teal-500 text-white shadow-sm">
            <Icons.Check className="h-4 w-4" />
          </span>
          What&apos;s good
          <span className="ml-auto chip border-emerald-200 bg-emerald-50 text-emerald-700">
            {strengths.length}
          </span>
        </h2>

        {strengths.length === 0 ? (
          <p className="text-sm text-muted">No specific strengths were identified.</p>
        ) : (
          <ul className="space-y-4">
            {strengths.map((item, index) => (
              <li
                key={index}
                className="animate-fade-up rounded-xl border border-emerald-100 bg-emerald-50/40 p-4 transition hover:border-emerald-200 hover:bg-emerald-50/80"
                style={{ animationDelay: `${index * 50}ms` }}
              >
                <p className="text-sm font-semibold text-slate-900">{item.title}</p>
                <p className="mt-1.5 text-sm leading-relaxed text-slate-600">{item.detail}</p>
                <div className="mt-2.5">
                  <FileRef
                    file={item.file}
                    repoUrl={repoUrl}
                    branch={branch}
                    verified={item.verified}
                  />
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* --------------------------------------------------------- improve */}
      <section className="card card-accent overflow-hidden p-6 before:bg-gradient-to-r before:from-amber-400 before:to-orange-500">
        <h2 className="mb-5 flex items-center gap-2.5 text-lg font-bold text-amber-800">
          <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-amber-400 to-orange-500 text-white shadow-sm">
            <Icons.Warning className="h-4 w-4" />
          </span>
          Needs improvement
          <span className="ml-auto chip border-amber-200 bg-amber-50 text-amber-700">
            {improvements.length}
          </span>
        </h2>

        {improvements.length === 0 ? (
          <p className="text-sm text-muted">No improvements were suggested.</p>
        ) : (
          <ul className="space-y-4">
            {improvements.map((item, index) => (
              <li
                key={index}
                className="animate-fade-up rounded-xl border border-amber-100 bg-amber-50/40 p-4 transition hover:border-amber-200 hover:bg-amber-50/80"
                style={{ animationDelay: `${index * 50}ms` }}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-semibold text-slate-900">{item.title}</p>
                  <SeverityChip severity={item.severity} />
                </div>
                <p className="mt-1.5 text-sm leading-relaxed text-slate-600">{item.detail}</p>

                {item.suggestion && (
                  <div className="mt-3 flex gap-2 rounded-lg border border-white bg-white/90 p-3">
                    <Icons.Sparkle className="mt-0.5 h-4 w-4 shrink-0 text-brand-500" />
                    <p className="text-sm leading-relaxed text-slate-700">
                      <span className="font-semibold text-brand-700">Try this: </span>
                      {item.suggestion}
                    </p>
                  </div>
                )}

                <div className="mt-2.5">
                  <FileRef
                    file={item.file}
                    repoUrl={repoUrl}
                    branch={branch}
                    verified={item.verified}
                  />
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

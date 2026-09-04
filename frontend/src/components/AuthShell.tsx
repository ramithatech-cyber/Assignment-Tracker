import type { ReactNode } from 'react'

import { Icons, type Portal } from './common'

/** Shared two-panel frame for sign in / sign up, themed per portal. */
export function AuthShell({ portal, children }: { portal: Portal; children: ReactNode }) {
  const { Icon } = portal

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* Brand panel — hidden on small screens where it would just push the
          form below the fold. */}
      <aside
        className={`relative hidden overflow-hidden bg-gradient-to-br ${portal.gradient} p-12 lg:flex lg:flex-col lg:justify-between`}
      >
        <div
          className="absolute inset-0 opacity-30"
          style={{
            backgroundImage:
              'radial-gradient(at 20% 20%, rgba(255,255,255,.35) 0, transparent 45%),' +
              'radial-gradient(at 80% 70%, rgba(255,255,255,.25) 0, transparent 45%)',
          }}
        />

        <div className="relative flex items-center gap-3 text-white">
          <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/20 backdrop-blur">
            <Icons.Sparkle className="h-6 w-6" />
          </span>
          <span className="text-lg font-extrabold tracking-tight">AssignmentTracker</span>
        </div>

        <div className="relative">
          <span className="inline-flex items-center gap-2 rounded-full bg-white/20 px-3 py-1 text-xs font-bold uppercase tracking-wider text-white backdrop-blur">
            <Icon className="h-3.5 w-3.5" />
            {portal.label} portal
          </span>

          <h2 className="mt-5 max-w-md text-4xl font-extrabold leading-tight tracking-tight text-white">
            {portal.tagline}
          </h2>
          <p className="mt-4 max-w-md text-base leading-relaxed text-white/80">{portal.blurb}</p>

          <ul className="mt-9 space-y-4">
            {portal.bullets.map((bullet) => (
              <li key={bullet} className="flex items-start gap-3 text-sm text-white/90">
                <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-white/20 backdrop-blur">
                  <Icons.Check className="h-3.5 w-3.5" />
                </span>
                {bullet}
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-white/50">
          Scores are backed by measured evidence, not vibes.
        </p>
      </aside>

      <div className="flex flex-col items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm animate-fade-up">{children}</div>
      </div>
    </div>
  )
}

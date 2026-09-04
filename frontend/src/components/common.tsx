import type { ReactNode, SVGProps } from 'react'

import type { Role, Severity, SubmissionStatus } from '../types'

/* ------------------------------------------------------------------- icons */
/* Hand-rolled so the app pulls in no icon package. */

type IconProps = SVGProps<SVGSVGElement>

function Icon({ children, ...props }: IconProps & { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {children}
    </svg>
  )
}

export const Icons = {
  Sparkle: (p: IconProps) => (
    <Icon {...p}>
      <path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9L12 3Z" />
      <path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15Z" />
    </Icon>
  ),
  Check: (p: IconProps) => (
    <Icon {...p}>
      <path d="M20 6L9 17l-5-5" />
    </Icon>
  ),
  Warning: (p: IconProps) => (
    <Icon {...p}>
      <path d="M12 9v4m0 4h.01M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" />
    </Icon>
  ),
  Code: (p: IconProps) => (
    <Icon {...p}>
      <path d="M16 18l6-6-6-6M8 6l-6 6 6 6" />
    </Icon>
  ),
  Layers: (p: IconProps) => (
    <Icon {...p}>
      <path d="M12 2L2 7l10 5 10-5-10-5ZM2 17l10 5 10-5M2 12l10 5 10-5" />
    </Icon>
  ),
  Target: (p: IconProps) => (
    <Icon {...p}>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="5" />
      <circle cx="12" cy="12" r="1.5" />
    </Icon>
  ),
  Book: (p: IconProps) => (
    <Icon {...p}>
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V3H6.5A2.5 2.5 0 0 0 4 5.5v14ZM4 19.5A2.5 2.5 0 0 0 6.5 22H20v-5" />
    </Icon>
  ),
  Beaker: (p: IconProps) => (
    <Icon {...p}>
      <path d="M9 3h6M10 3v6L4.6 18.4A2 2 0 0 0 6.3 21h11.4a2 2 0 0 0 1.7-2.6L14 9V3" />
      <path d="M7.5 15h9" />
    </Icon>
  ),
  Branch: (p: IconProps) => (
    <Icon {...p}>
      <circle cx="6" cy="4" r="2" />
      <circle cx="6" cy="20" r="2" />
      <circle cx="18" cy="8" r="2" />
      <path d="M6 6v12M18 10c0 4-6 2-6 8" />
    </Icon>
  ),
  Shield: (p: IconProps) => (
    <Icon {...p}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
    </Icon>
  ),
  Github: (p: IconProps) => (
    <Icon {...p}>
      <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.9a3.4 3.4 0 0 0-.9-2.6c3-.3 6.2-1.5 6.2-6.7A5.2 5.2 0 0 0 19 4.8a4.9 4.9 0 0 0-.1-3.6s-1.1-.3-3.7 1.4a12.7 12.7 0 0 0-6.6 0C5.9.9 4.8 1.2 4.8 1.2a4.9 4.9 0 0 0-.1 3.6 5.2 5.2 0 0 0-1.4 3.6c0 5.2 3.2 6.4 6.2 6.7a3.4 3.4 0 0 0-.9 2.6V22" />
    </Icon>
  ),
  Plus: (p: IconProps) => (
    <Icon {...p}>
      <path d="M12 5v14M5 12h14" />
    </Icon>
  ),
  Arrow: (p: IconProps) => (
    <Icon {...p}>
      <path d="M5 12h14M12 5l7 7-7 7" />
    </Icon>
  ),
  Back: (p: IconProps) => (
    <Icon {...p}>
      <path d="M19 12H5M12 19l-7-7 7-7" />
    </Icon>
  ),
  Logout: (p: IconProps) => (
    <Icon {...p}>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" />
    </Icon>
  ),
  Inbox: (p: IconProps) => (
    <Icon {...p}>
      <path d="M22 12h-6l-2 3h-4l-2-3H2" />
      <path d="M5.5 5.1L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.5-6.9A2 2 0 0 0 16.7 4H7.3a2 2 0 0 0-1.8 1.1Z" />
    </Icon>
  ),
  Clock: (p: IconProps) => (
    <Icon {...p}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </Icon>
  ),
  Calendar: (p: IconProps) => (
    <Icon {...p}>
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M8 3v4M16 3v4M3 10h18" />
    </Icon>
  ),
  CalendarWeek: (p: IconProps) => (
    <Icon {...p}>
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M8 3v4M16 3v4M3 10h18M3 15h18" />
    </Icon>
  ),
  Grid: (p: IconProps) => (
    <Icon {...p}>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </Icon>
  ),
  Users: (p: IconProps) => (
    <Icon {...p}>
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8" />
    </Icon>
  ),
  Chart: (p: IconProps) => (
    <Icon {...p}>
      <path d="M3 3v18h18" />
      <path d="M7 15l3.5-4 3 3L19 7" />
    </Icon>
  ),
  Flame: (p: IconProps) => (
    <Icon {...p}>
      <path d="M12 22c4 0 7-2.7 7-6.5 0-4.5-4-6-4-9.5-2 1-3 2.7-3 4.5C10.5 9 9 7 9 5c-2 1.8-4 4.3-4 7.5C5 19.3 8 22 12 22Z" />
    </Icon>
  ),
  Lock: (p: IconProps) => (
    <Icon {...p}>
      <rect x="4" y="11" width="16" height="10" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </Icon>
  ),
  Edit: (p: IconProps) => (
    <Icon {...p}>
      <path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5Z" />
    </Icon>
  ),
}

export function Spinner({ className = 'h-4 w-4' }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-90" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
  )
}

/* ------------------------------------------------------- category identity */
/* Each rubric category gets its own hue, used consistently by the bars, the
   report, and anywhere else a category is named. */

export interface CategoryStyle {
  gradient: string
  bar: string
  text: string
  soft: string
  ring: string
  Icon: (p: IconProps) => JSX.Element
}

/* Kept within the warm red family so the seven categories stay distinguishable
   without fighting the dark-red theme. Depth, not hue, does most of the work. */
export const CATEGORY_STYLES: Record<string, CategoryStyle> = {
  code_quality: {
    gradient: 'from-brand-950 to-brand-700',
    bar: '#450a0a',
    text: 'text-brand-900',
    soft: 'bg-brand-50',
    ring: 'ring-brand-200',
    Icon: Icons.Code,
  },
  structure: {
    gradient: 'from-brand-800 to-brand-600',
    bar: '#7f1d1d',
    text: 'text-brand-800',
    soft: 'bg-brand-50',
    ring: 'ring-brand-200',
    Icon: Icons.Layers,
  },
  correctness: {
    gradient: 'from-brand-600 to-brand-500',
    bar: '#b91c1c',
    text: 'text-brand-700',
    soft: 'bg-brand-50',
    ring: 'ring-brand-200',
    Icon: Icons.Target,
  },
  documentation: {
    gradient: 'from-rose-600 to-brand-600',
    bar: '#e11d48',
    text: 'text-rose-700',
    soft: 'bg-rose-50',
    ring: 'ring-rose-200',
    Icon: Icons.Book,
  },
  testing: {
    gradient: 'from-orange-500 to-brand-600',
    bar: '#f97316',
    text: 'text-orange-700',
    soft: 'bg-orange-50',
    ring: 'ring-orange-200',
    Icon: Icons.Beaker,
  },
  git_hygiene: {
    gradient: 'from-amber-500 to-orange-600',
    bar: '#f59e0b',
    text: 'text-amber-700',
    soft: 'bg-amber-50',
    ring: 'ring-amber-200',
    Icon: Icons.Branch,
  },
  security: {
    gradient: 'from-brand-900 to-rose-800',
    bar: '#651414',
    text: 'text-brand-900',
    soft: 'bg-brand-50',
    ring: 'ring-brand-200',
    Icon: Icons.Shield,
  },
}

export const FALLBACK_CATEGORY: CategoryStyle = {
  gradient: 'from-stone-400 to-stone-600',
  bar: '#a8a29e',
  text: 'text-stone-700',
  soft: 'bg-stone-50',
  ring: 'ring-stone-200',
  Icon: Icons.Sparkle,
}

/* --------------------------------------------------------- performance level */

const TONE_CLASSES: Record<string, string> = {
  emerald: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  lime: 'border-lime-200 bg-lime-50 text-lime-700',
  amber: 'border-amber-200 bg-amber-50 text-amber-800',
  orange: 'border-orange-200 bg-orange-50 text-orange-800',
  red: 'border-brand-200 bg-brand-50 text-brand-700',
  stone: 'border-stone-200 bg-stone-100 text-stone-500',
}

export function PerformanceBadge({ level, tone }: { level: string; tone: string }) {
  return <span className={`chip ${TONE_CLASSES[tone] ?? TONE_CLASSES.stone}`}>{level}</span>
}

export function categoryStyle(key: string): CategoryStyle {
  return CATEGORY_STYLES[key] ?? FALLBACK_CATEGORY
}

/* ------------------------------------------------------------------ portals */
/* The backend has two roles, `student` and `teacher`. "Admin" is purely the
   user-facing name for `teacher` -- the API contract is untouched, so existing
   accounts keep working. Route everything user-visible through here rather than
   hardcoding either word. */

export type PortalKey = 'student' | 'admin'

export interface Portal {
  key: PortalKey
  role: Role
  label: string
  tagline: string
  blurb: string
  gradient: string
  softBg: string
  border: string
  text: string
  Icon: (p: IconProps) => JSX.Element
  bullets: string[]
}

export const PORTALS: Record<PortalKey, Portal> = {
  student: {
    key: 'student',
    role: 'student',
    label: 'Student',
    tagline: 'Submit your work',
    blurb: 'Paste a GitHub repository and get a scored review back in about a minute.',
    gradient: 'from-brand-500 via-violet-500 to-fuchsia-500',
    softBg: 'bg-brand-50',
    border: 'border-brand-200',
    text: 'text-brand-700',
    Icon: Icons.Beaker,
    bullets: [
      'Submit a public GitHub repository',
      'See exactly what cost you marks, and why',
      'Track every submission and score',
    ],
  },
  admin: {
    key: 'admin',
    role: 'teacher',
    label: 'Admin',
    tagline: 'Set and grade work',
    blurb: 'Create assignments, then review every submission and score in one table.',
    gradient: 'from-amber-400 via-orange-500 to-rose-500',
    softBg: 'bg-amber-50',
    border: 'border-amber-200',
    text: 'text-amber-700',
    Icon: Icons.Shield,
    bullets: [
      'Create assignments with a grading brief',
      'See every submission ranked by score',
      'Class average, highest and lowest at a glance',
    ],
  },
}

/** Maps an API role onto the word shown to users. */
export const ROLE_LABEL: Record<Role, string> = {
  student: 'Student',
  teacher: 'Admin',
}

export function portalForRole(role: Role): Portal {
  return role === 'teacher' ? PORTALS.admin : PORTALS.student
}

export function isPortalKey(value: string | undefined): value is PortalKey {
  return value === 'student' || value === 'admin'
}

/* ---------------------------------------------------------------- feedback */

export function ErrorBanner({ message }: { message: string | null }) {
  if (!message) return null
  return (
    <div
      role="alert"
      className="animate-scale-in flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50/90 px-4 py-3 text-sm text-rose-800"
    >
      <Icons.Warning className="mt-0.5 h-4 w-4 shrink-0 text-rose-500" />
      <span>{message}</span>
    </div>
  )
}

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="card animate-fade-up flex flex-col items-center px-6 py-16 text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-gradient text-white shadow-lift">
        <Icons.Inbox className="h-7 w-7" />
      </div>
      <p className="text-base font-semibold text-slate-800">{title}</p>
      {hint && <p className="mt-1.5 max-w-sm text-sm text-muted">{hint}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

export function PageHeader({
  title,
  subtitle,
  action,
  eyebrow,
}: {
  title: string
  subtitle?: ReactNode
  action?: ReactNode
  eyebrow?: string
}) {
  return (
    <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
      <div className="animate-fade-up">
        {eyebrow && (
          <p className="mb-1 text-xs font-bold uppercase tracking-[0.14em] text-brand-500">
            {eyebrow}
          </p>
        )}
        <h1 className="text-3xl font-extrabold tracking-tight text-ink">{title}</h1>
        {subtitle && <div className="mt-2 text-sm text-muted">{subtitle}</div>}
      </div>
      {action && <div className="animate-fade-up">{action}</div>}
    </div>
  )
}

export function LoadingBlock({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="card p-6">
          <div className="skeleton h-4 w-1/3" />
          <div className="skeleton mt-3 h-3 w-2/3" />
          <div className="skeleton mt-2 h-3 w-1/2" />
        </div>
      ))}
    </div>
  )
}

/* ------------------------------------------------------------------ badges */

const STATUS_STYLES: Record<SubmissionStatus, string> = {
  completed: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  failed: 'border-rose-200 bg-rose-50 text-rose-700',
  analyzing: 'border-amber-200 bg-amber-50 text-amber-700',
  pending: 'border-slate-200 bg-slate-100 text-slate-600',
}

const STATUS_DOT: Record<SubmissionStatus, string> = {
  completed: 'bg-emerald-500',
  failed: 'bg-rose-500',
  analyzing: 'bg-amber-500 animate-pulse',
  pending: 'bg-slate-400',
}

export function StatusBadge({ status }: { status: SubmissionStatus }) {
  return (
    <span className={`chip capitalize ${STATUS_STYLES[status]}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${STATUS_DOT[status]}`} />
      {status}
    </span>
  )
}

const SEVERITY_STYLES: Record<Severity, string> = {
  high: 'border-rose-200 bg-rose-100 text-rose-800',
  medium: 'border-amber-200 bg-amber-100 text-amber-800',
  low: 'border-slate-200 bg-slate-100 text-slate-600',
}

export function SeverityChip({ severity }: { severity: Severity }) {
  return (
    <span className={`chip uppercase tracking-wide ${SEVERITY_STYLES[severity]}`}>{severity}</span>
  )
}

export function GradeBadge({ grade }: { grade: string | null }) {
  if (!grade) return null
  const tone =
    grade === 'A'
      ? 'from-emerald-500 to-teal-600'
      : grade === 'B'
        ? 'from-lime-500 to-emerald-600'
        : grade === 'C'
          ? 'from-amber-400 to-orange-500'
          : grade === 'D'
            ? 'from-orange-500 to-rose-500'
            : 'from-rose-500 to-red-600'
  return (
    <span
      className={`inline-flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br ${tone} text-sm font-extrabold text-white shadow-lift`}
    >
      {grade}
    </span>
  )
}

/* ------------------------------------------------------------------ shared */

/** Colour band shared by the gauge, the bars, and the score tables. */
export function scoreColor(fraction: number): string {
  if (fraction >= 0.85) return '#059669'
  if (fraction >= 0.7) return '#65a30d'
  if (fraction >= 0.5) return '#d97706'
  return '#e11d48'
}

export function scoreGradient(fraction: number): [string, string] {
  if (fraction >= 0.85) return ['#34d399', '#0d9488']
  if (fraction >= 0.7) return ['#a3e635', '#059669']
  if (fraction >= 0.5) return ['#fbbf24', '#f97316']
  return ['#fb7185', '#e11d48']
}

export function formatDate(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value.endsWith('Z') ? value : `${value}Z`)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

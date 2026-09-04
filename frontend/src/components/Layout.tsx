import { useState } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'

import { useAuth } from '../contexts/AuthContext'
import { Icons, ROLE_LABEL } from './common'

interface NavItem {
  to: string
  label: string
  Icon: (p: { className?: string }) => JSX.Element
  end?: boolean
}

const STUDENT_NAV: NavItem[] = [
  { to: '/daily', label: 'Daily', Icon: Icons.Calendar },
  { to: '/weekly', label: 'Weekly', Icon: Icons.CalendarWeek },
  { to: '/submissions', label: 'My submissions', Icon: Icons.Inbox, end: true },
]

const ADMIN_NAV: NavItem[] = [
  { to: '/admin', label: 'Dashboard', Icon: Icons.Chart, end: true },
  { to: '/admin/students', label: 'Students', Icon: Icons.Users },
  { to: '/admin/assignments', label: 'Assignments', Icon: Icons.Layers, end: true },
  { to: '/admin/assignments/new', label: 'New assignment', Icon: Icons.Plus },
]

function initials(name: string): string {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
}

function sideClass({ isActive }: { isActive: boolean }) {
  return `side-link ${isActive ? 'side-link-active' : ''}`
}

export function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)

  const isAdmin = user?.role === 'teacher'
  const items = isAdmin ? ADMIN_NAV : STUDENT_NAV

  const sidebar = (
    <nav className="flex h-full flex-col gap-1 p-4">
      <Link
        to={isAdmin ? '/admin' : '/daily'}
        className="mb-6 flex items-center gap-2.5"
        onClick={() => setOpen(false)}
      >
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-gradient text-white shadow-lift">
          <Icons.Sparkle className="h-5 w-5" />
        </span>
        <span className="text-[15px] font-extrabold tracking-tight text-ink">
          Assignment<span className="gradient-text">Tracker</span>
        </span>
      </Link>

      <p className="mb-2 px-3 text-[11px] font-bold uppercase tracking-[0.14em] text-stone-400">
        {isAdmin ? 'Admin' : 'Menu'}
      </p>

      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          className={sideClass}
          onClick={() => setOpen(false)}
        >
          <item.Icon className="h-4 w-4" />
          {item.label}
        </NavLink>
      ))}

      <div className="mt-auto border-t border-stone-200 pt-4">
        <div className="mb-3 flex items-center gap-2.5 px-1">
          <span
            className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white shadow-sm ${
              isAdmin ? 'bg-brand-deep' : 'bg-brand-gradient'
            }`}
          >
            {initials(user?.full_name ?? '?')}
          </span>
          <div className="min-w-0 leading-tight">
            <p className="truncate text-sm font-semibold text-stone-800">{user?.full_name}</p>
            <p className="text-[11px] font-semibold text-brand-600">
              {user ? ROLE_LABEL[user.role] : ''}
            </p>
          </div>
        </div>

        <button
          type="button"
          className="btn-ghost w-full"
          onClick={() => {
            logout()
            navigate(isAdmin ? '/login/admin' : '/login/student')
          }}
        >
          <Icons.Logout className="h-4 w-4" />
          Sign out
        </button>
      </div>
    </nav>
  )

  return (
    <div className="min-h-screen lg:flex">
      {/* Desktop sidebar */}
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 border-r border-stone-200 bg-white lg:block">
        {sidebar}
      </aside>

      {/* Mobile drawer */}
      {open && (
        <>
          <div
            className="fixed inset-0 z-40 bg-brand-950/30 lg:hidden"
            onClick={() => setOpen(false)}
            aria-hidden="true"
          />
          <aside className="animate-scale-in fixed inset-y-0 left-0 z-50 w-64 border-r border-stone-200 bg-white lg:hidden">
            {sidebar}
          </aside>
        </>
      )}

      <div className="min-w-0 flex-1">
        {/* Mobile top bar */}
        <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-stone-200 bg-white/90 px-4 py-3 backdrop-blur lg:hidden">
          <button
            type="button"
            className="btn-ghost !px-3"
            onClick={() => setOpen(true)}
            aria-label="Open menu"
          >
            <Icons.Grid className="h-4 w-4" />
          </button>
          <span className="text-sm font-extrabold tracking-tight text-ink">
            Assignment<span className="gradient-text">Tracker</span>
          </span>
        </header>

        <main className="mx-auto max-w-6xl px-4 py-8 lg:py-10">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

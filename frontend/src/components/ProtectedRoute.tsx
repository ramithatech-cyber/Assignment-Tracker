import { Navigate, useLocation } from 'react-router-dom'

import { useAuth } from '../contexts/AuthContext'
import type { Role } from '../types'
import { Icons, Spinner } from './common'

interface Props {
  children: JSX.Element
  role?: Role
}

/**
 * Convenience only. Every one of these rules is also enforced server-side --
 * the UI hiding a route is not what keeps a student out of another student's
 * report.
 */
export function ProtectedRoute({ children, role }: Props) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4">
        <span className="animate-float flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-gradient text-white shadow-lift">
          <Icons.Sparkle className="h-7 w-7" />
        </span>
        <Spinner className="h-5 w-5 text-brand-500" />
      </div>
    )
  }

  // No landing page: signing in IS the front door. Admins reach their own
  // portal at the unlinked /login/admin.
  if (!user) return <Navigate to="/login/student" state={{ from: location }} replace />

  if (role && user.role !== role) {
    return <Navigate to={user.role === 'teacher' ? '/admin' : '/'} replace />
  }

  return children
}

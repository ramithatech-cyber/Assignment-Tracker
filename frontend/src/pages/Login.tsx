import { useState } from 'react'
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom'

import { ApiError } from '../api/client'
import { AuthShell } from '../components/AuthShell'
import {
  ErrorBanner,
  Icons,
  PORTALS,
  Spinner,
  isPortalKey,
} from '../components/common'
import { useAuth } from '../contexts/AuthContext'

export function Login() {
  const { portal: portalParam } = useParams<{ portal: string }>()
  const { login, logout } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [wrongPortal, setWrongPortal] = useState(false)
  const [busy, setBusy] = useState(false)

  // An unknown portal in the URL is a dead end -- send them back to choose.
  // An unknown portal in the URL is a dead end -- fall back to the student one.
  if (!isPortalKey(portalParam)) return <Navigate to="/login/student" replace />

  const portal = PORTALS[portalParam]
  const isAdminPortal = portalParam === 'admin'
  const other = isAdminPortal ? PORTALS.student : PORTALS.admin
  const { Icon } = portal

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setWrongPortal(false)
    setBusy(true)
    try {
      const user = await login(email.trim(), password)

      // Credentials were valid, but for the other portal. Drop the session so
      // we never leave them half-signed-in.
      if (user.role !== portal.role) {
        logout()
        setWrongPortal(true)
        setError(
          isAdminPortal
            ? // Staff mistyping the URL get a helpful nudge to the student page.
              `Those are valid credentials, but this is the ${portal.label} portal and that is a ${other.label.toLowerCase()} account.`
            : // The student-facing page never mentions that an admin portal exists.
              'That account cannot be used to sign in here.',
        )
        return
      }

      navigate(user.role === 'teacher' ? '/admin' : '/', { replace: true })
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Sign-in failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthShell portal={portal}>
      <span
        className={`flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br ${portal.gradient} text-white shadow-lift`}
      >
        <Icon className="h-6 w-6" />
      </span>

      <h1 className="mt-5 text-3xl font-extrabold tracking-tight text-ink">
        {portal.label} sign in
      </h1>
      <p className="mt-2 text-sm text-muted">{portal.blurb}</p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-5">
        <div>
          <label className="label" htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            className="input"
            placeholder="you@school.edu"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            autoComplete="email"
          />
        </div>

        <div>
          <label className="label" htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            className="input"
            placeholder="........"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            autoComplete="current-password"
          />
        </div>

        <ErrorBanner message={error} />

        {wrongPortal && isAdminPortal && (
          <Link
            to={`/login/${other.key}`}
            className={`btn w-full bg-gradient-to-r ${other.gradient} text-white shadow-lift hover:brightness-110`}
          >
            Go to the {other.label} login
            <Icons.Arrow className="h-4 w-4" />
          </Link>
        )}

        <button
          type="submit"
          className={`btn w-full bg-gradient-to-r ${portal.gradient} text-white shadow-lift hover:-translate-y-0.5 hover:brightness-110`}
          disabled={busy}
        >
          {busy ? <Spinner /> : <Icons.Arrow className="h-4 w-4" />}
          Sign in as {portal.label.toLowerCase()}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-muted">
        No {portal.label.toLowerCase()} account?{' '}
        <Link
          to={`/register/${portal.key}`}
          className="font-semibold text-brand-600 hover:text-brand-700 hover:underline"
        >
          Create one
        </Link>
      </p>
    </AuthShell>
  )
}

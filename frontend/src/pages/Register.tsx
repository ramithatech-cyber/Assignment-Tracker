import { useState } from 'react'
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom'

import { ApiError } from '../api/client'
import { AuthShell } from '../components/AuthShell'
import { ErrorBanner, Icons, PORTALS, Spinner, isPortalKey } from '../components/common'
import { useAuth } from '../contexts/AuthContext'

export function Register() {
  const { portal: portalParam } = useParams<{ portal: string }>()
  const { register } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState({ full_name: '', email: '', password: '', signup_code: '' })
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (!isPortalKey(portalParam)) return <Navigate to="/register/student" replace />

  const portal = PORTALS[portalParam]
  const isAdminPortal = portalParam === 'admin'
  const other = isAdminPortal ? PORTALS.student : PORTALS.admin
  const { Icon } = portal
  const tooShort = form.password.length > 0 && form.password.length < 8

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setBusy(true)
    try {
      // The portal decides the role -- there is no role picker to get wrong.
      const { signup_code, ...fields } = form
      const user = await register({
        ...fields,
        email: form.email.trim(),
        role: portal.role,
        // Only admin accounts need the staff signup code.
        ...(isAdminPortal ? { signup_code: signup_code.trim() } : {}),
      })
      navigate(user.role === 'teacher' ? '/admin' : '/', { replace: true })
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Registration failed.')
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
        Create a {portal.label.toLowerCase()} account
      </h1>
      <p className="mt-2 text-sm text-muted">{portal.blurb}</p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-5">
        <div>
          <label className="label" htmlFor="name">Full name</label>
          <input
            id="name"
            className="input"
            placeholder="Grace Hopper"
            value={form.full_name}
            onChange={(event) => setForm({ ...form, full_name: event.target.value })}
            required
          />
        </div>

        <div>
          <label className="label" htmlFor="reg-email">Email</label>
          <input
            id="reg-email"
            type="email"
            className="input"
            placeholder="you@school.edu"
            value={form.email}
            onChange={(event) => setForm({ ...form, email: event.target.value })}
            required
          />
        </div>

        <div>
          <label className="label" htmlFor="reg-password">Password</label>
          <input
            id="reg-password"
            type="password"
            className={`input ${tooShort ? 'input-error' : ''}`}
            placeholder="........"
            value={form.password}
            onChange={(event) => setForm({ ...form, password: event.target.value })}
            required
            minLength={8}
            autoComplete="new-password"
          />
          <p className={`mt-1.5 text-xs ${tooShort ? 'font-medium text-rose-600' : 'text-muted'}`}>
            At least 8 characters.
          </p>
        </div>

        {isAdminPortal && (
          <div>
            <label className="label" htmlFor="reg-signup-code">Admin signup code</label>
            <input
              id="reg-signup-code"
              type="password"
              className="input"
              placeholder="Provided by your institution"
              value={form.signup_code}
              onChange={(event) => setForm({ ...form, signup_code: event.target.value })}
              required
              autoComplete="off"
            />
          </div>
        )}

        <div
          className={`flex items-start gap-2.5 rounded-xl border ${portal.border} ${portal.softBg} p-3`}
        >
          <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${portal.text}`} />
          <p className="text-xs leading-relaxed text-slate-700">
            This creates a <strong>{portal.label.toLowerCase()}</strong> account.{' '}
            {isAdminPortal
              ? 'Admins create assignments and review every submission.'
              : 'Students submit repositories and receive scored reports.'}{' '}
            {/* Only the admin page links across -- the student page never
                reveals that an admin portal exists. */}
            {isAdminPortal && (
              <Link to={`/register/${other.key}`} className="font-semibold underline">
                Need a {other.label.toLowerCase()} account instead?
              </Link>
            )}
          </p>
        </div>

        <ErrorBanner message={error} />

        <button
          type="submit"
          className={`btn w-full bg-gradient-to-r ${portal.gradient} text-white shadow-lift hover:-translate-y-0.5 hover:brightness-110`}
          disabled={busy || tooShort}
        >
          {busy ? <Spinner /> : <Icons.Arrow className="h-4 w-4" />}
          Create {portal.label.toLowerCase()} account
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-muted">
        Already registered?{' '}
        <Link
          to={`/login/${portal.key}`}
          className="font-semibold text-brand-600 hover:text-brand-700 hover:underline"
        >
          Sign in
        </Link>
      </p>
    </AuthShell>
  )
}

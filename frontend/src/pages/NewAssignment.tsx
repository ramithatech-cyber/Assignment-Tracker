import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { ApiError, api } from '../api/client'
import { ErrorBanner, Icons, PageHeader, Spinner } from '../components/common'

export function NewAssignment() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    title: '',
    description: '',
    requirements: '',
    due_date: '',
  })
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const created = await api.createAssignment({
        title: form.title.trim(),
        description: form.description.trim(),
        requirements: form.requirements.trim(),
        // <input type="datetime-local"> gives a naive local string; the API
        // takes ISO, so add seconds and let the backend store it as given.
        due_date: form.due_date ? `${form.due_date}:00` : null,
      })
      navigate(`/admin/assignments/${created.id}`)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Could not create the assignment.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Create"
        title="New assignment"
        action={
          <Link to="/admin/assignments" className="btn-ghost">
            <Icons.Back className="h-4 w-4" />
            Cancel
          </Link>
        }
      />

      <form
        onSubmit={handleSubmit}
        className="card card-accent animate-fade-up max-w-2xl space-y-6 p-7"
      >
        <div>
          <label className="label" htmlFor="title">Title</label>
          <input
            id="title"
            className="input"
            value={form.title}
            onChange={(event) => setForm({ ...form, title: event.target.value })}
            placeholder="Build a REST API with FastAPI"
            required
          />
        </div>

        <div>
          <label className="label" htmlFor="description">Description</label>
          <textarea
            id="description"
            className="input min-h-[100px] resize-y"
            value={form.description}
            onChange={(event) => setForm({ ...form, description: event.target.value })}
            placeholder="What the students are building, and any context they need."
          />
        </div>

        <div>
          <label className="label" htmlFor="requirements">
            Grading requirements
          </label>
          <textarea
            id="requirements"
            className="input min-h-[150px] resize-y font-mono text-[13px]"
            value={form.requirements}
            onChange={(event) => setForm({ ...form, requirements: event.target.value })}
            placeholder={
              'One requirement per line, e.g.\n- CRUD endpoints for a Task resource\n- Input validation with Pydantic\n- At least 5 tests\n- README with setup instructions'
            }
          />
          <div className="mt-2.5 flex gap-2.5 rounded-xl border border-brand-100 bg-brand-50/70 p-3">
            <Icons.Sparkle className="mt-0.5 h-4 w-4 shrink-0 text-brand-500" />
            <p className="text-xs leading-relaxed text-brand-900">
              This text is given to the reviewer verbatim and is what the{' '}
              <strong>Correctness &amp; Completeness</strong> score (20 points) is measured
              against. The more specific it is, the more useful the grade.
            </p>
          </div>
        </div>

        <div>
          <label className="label" htmlFor="due">Due date (optional)</label>
          <input
            id="due"
            type="datetime-local"
            className="input"
            value={form.due_date}
            onChange={(event) => setForm({ ...form, due_date: event.target.value })}
          />
        </div>

        <ErrorBanner message={error} />

        <button type="submit" className="btn-primary" disabled={busy || !form.title.trim()}>
          {busy ? <Spinner /> : <Icons.Plus className="h-4 w-4" />}
          Create assignment
        </button>
      </form>
    </>
  )
}

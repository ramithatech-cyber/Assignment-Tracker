import type {
  ActivityStatus,
  AdminOverview,
  Assignment,
  PerformanceRow,
  ProgramDay,
  ProgramSummary,
  ProgramWeek,
  Report,
  StudentDetail,
  StudentRemark,
  Submission,
  Token,
  User,
} from '../types'

const BASE = import.meta.env.VITE_API_URL ?? ''
const TOKEN_KEY = 'assignment-tracker-token'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
    this.name = 'ApiError'
  }
}

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

interface RequestOptions {
  method?: string
  body?: unknown
  /** Submissions run the whole analysis inline, so they need a long ceiling. */
  timeoutMs?: number
  signal?: AbortSignal
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, timeoutMs = 30_000, signal } = options

  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeoutMs)
  signal?.addEventListener('abort', () => controller.abort())

  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = tokenStore.get()
  if (token) headers.Authorization = `Bearer ${token}`

  let response: Response
  try {
    response = await fetch(`${BASE}/api${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    })
  } catch (error) {
    if ((error as Error).name === 'AbortError') {
      throw new ApiError(
        408,
        'The request took too long and was cancelled. Very large repositories can exceed the time limit.',
      )
    }
    throw new ApiError(0, 'Could not reach the server. Is the backend running on port 8000?')
  } finally {
    window.clearTimeout(timer)
  }

  if (response.status === 401) {
    tokenStore.clear()
    throw new ApiError(401, 'Your session has expired. Please sign in again.')
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    try {
      const data = await response.json()
      if (typeof data.detail === 'string') detail = data.detail
      // FastAPI validation errors arrive as a list of objects.
      else if (Array.isArray(data.detail)) detail = data.detail[0]?.msg ?? detail
    } catch {
      /* keep the generic message */
    }
    throw new ApiError(response.status, detail)
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const api = {
  register: (payload: {
    email: string
    password: string
    full_name: string
    role: string
    signup_code?: string
  }) => request<Token>('/auth/register', { method: 'POST', body: payload }),

  login: (email: string, password: string) =>
    request<Token>('/auth/login', { method: 'POST', body: { email, password } }),

  me: () => request<User>('/auth/me'),

  listAssignments: () => request<Assignment[]>('/assignments'),

  getAssignment: (id: number) => request<Assignment>(`/assignments/${id}`),

  createAssignment: (payload: {
    title: string
    description: string
    requirements: string
    due_date: string | null
  }) => request<Assignment>('/assignments', { method: 'POST', body: payload }),

  updateAssignment: (id: number, payload: Partial<{ is_open: boolean }>) =>
    request<Assignment>(`/assignments/${id}`, { method: 'PATCH', body: payload }),

  assignmentSubmissions: (id: number) =>
    request<Submission[]>(`/assignments/${id}/submissions`),

  submit: (assignment_id: number, repo_url: string, signal?: AbortSignal) =>
    request<Submission>('/submissions', {
      method: 'POST',
      body: { assignment_id, repo_url },
      timeoutMs: 300_000,
      signal,
    }),

  getSubmission: (id: number) => request<Submission>(`/submissions/${id}`),

  mySubmissions: () => request<Submission[]>('/submissions/me'),

  rubric: () =>
    request<{ total_points: number; categories: { key: string; label: string; max: number; guidance: string }[] }>(
      '/rubric',
    ),

  // ---------------------------------------------------- 45-day programme
  days: () => request<{ days: ProgramDay[]; summary: ProgramSummary }>('/activities/days'),

  weeks: () => request<{ weeks: ProgramWeek[]; summary: ProgramSummary }>('/activities/weeks'),

  saveDay: (
    dayNumber: number,
    payload: { status: ActivityStatus; notes: string; hours: number; link: string | null },
  ) =>
    request<{ day: ProgramDay; summary: ProgramSummary }>(`/activities/days/${dayNumber}`, {
      method: 'PUT',
      body: payload,
    }),

  // ------------------------------------------------------------- admin
  adminOverview: () => request<AdminOverview>('/admin/overview'),

  adminStudents: () => request<PerformanceRow[]>('/admin/students'),

  adminStudent: (id: number) => request<StudentDetail>(`/admin/students/${id}`),

  /** Costs an OpenAI call, so this is only ever fired from an explicit button. */
  generateRemark: (id: number) =>
    request<StudentRemark>(`/admin/students/${id}/remark`, {
      method: 'POST',
      timeoutMs: 120_000,
    }),
}

export type { Report }

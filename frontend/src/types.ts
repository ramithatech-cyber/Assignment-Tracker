// Mirrors backend/app/schemas.py. Keep the two in step.

export type Role = 'student' | 'teacher'
export type SubmissionStatus = 'pending' | 'analyzing' | 'completed' | 'failed'
export type Severity = 'low' | 'medium' | 'high'

export interface User {
  id: number
  email: string
  full_name: string
  role: Role
  created_at: string
}

export interface Token {
  access_token: string
  token_type: string
  user: User
}

export interface Assignment {
  id: number
  teacher_id: number
  title: string
  description: string
  requirements: string
  due_date: string | null
  is_open: boolean
  created_at: string
  teacher_name: string | null
  submission_count: number
  my_submission_id: number | null
}

export interface CategoryScore {
  key: string
  label: string
  score: number
  max_score: number
  justification: string
}

export interface Strength {
  title: string
  detail: string
  file: string | null
  verified?: boolean
}

export interface Improvement extends Strength {
  suggestion: string
  severity: Severity
}

export interface Report {
  summary: string
  category_scores: CategoryScore[]
  strengths: Strength[]
  improvements: Improvement[]
  static_metrics: Record<string, unknown>
  applied_caps: string[]
  llm_model: string
  tokens_used: number
  duration_ms: number
}

/* ------------------------------------------------------- 45-day programme */

export type ActivityStatus = 'completed' | 'partial' | 'skipped'
export type DayState = 'upcoming' | 'open' | 'submitted' | 'missed'

export interface ActivityEntry {
  id: number
  status: ActivityStatus
  notes: string
  hours: number
  link: string | null
  updated_at: string
}

export interface ProgramDay {
  day_number: number
  date: string
  state: DayState
  editable: boolean
  week: number
  entry: ActivityEntry | null
}

export interface ProgramWeek {
  week_number: number
  start_date: string
  end_date: string
  day_numbers: number[]
  total_days: number
  elapsed_days: number
  submitted: number
  missed: number
  upcoming: number
  completion: number
  hours: number
  fully_completed: number
  partial: number
  skipped: number
  state: 'upcoming' | 'in_progress' | 'complete'
}

export interface ProgramSummary {
  enrolled_on: string
  total_days: number
  current_day: number
  elapsed_days: number
  submitted_days: number
  missed_days: number
  completion: number
  total_hours: number
  current_streak: number
  started: boolean
  finished: boolean
}

/* ------------------------------------------------------------ admin views */

export interface PerformanceRow {
  student_id: number
  student_name: string
  email: string
  joined_at: string
  submission_count: number
  failed_count: number
  average_score: number | null
  best_score: number | null
  programme: ProgramSummary
  performance_index: number | null
  performance_level: string
  performance_tone: string
  last_active: string | null
}

export interface AdminOverview {
  students: number
  assignments: number
  submissions: number
  average_score: number | null
  average_completion: number | null
  at_risk: number
  distribution: Record<string, number>
  top_performers: PerformanceRow[]
}

export type Trajectory = 'improving' | 'steady' | 'declining' | 'insufficient_data'

export interface StudentRemark {
  summary: string
  trajectory: Trajectory
  strengths: string[]
  concerns: string[]
  recommendation: string
  performance_level: string
  based_on_submissions: number
  based_on_days: number
  llm_model: string
  tokens_used: number
  generated_at: string
  /** Set when new work has arrived since the remark was written. */
  stale_reason: string | null
}

export interface StudentDetail {
  performance: PerformanceRow
  submissions: Submission[]
  weeks: ProgramWeek[]
  recent_days: ProgramDay[]
  remark: StudentRemark | null
}

export interface Submission {
  id: number
  assignment_id: number
  student_id: number
  repo_url: string
  repo_owner: string
  repo_name: string
  default_branch: string
  commit_sha: string
  status: SubmissionStatus
  error_message: string | null
  total_score: number | null
  grade: string | null
  created_at: string
  completed_at: string | null
  student_name: string | null
  assignment_title: string | null
  report: Report | null
}

import { Navigate, Route, Routes } from 'react-router-dom'

import { Layout } from './components/Layout'
import { ProtectedRoute } from './components/ProtectedRoute'
import { useAuth } from './contexts/AuthContext'
import { AdminDashboard } from './pages/AdminDashboard'
import { AdminStudentDetail } from './pages/AdminStudentDetail'
import { AdminStudents } from './pages/AdminStudents'
import { AssignmentDetail } from './pages/AssignmentDetail'
import { AssignmentSubmissions } from './pages/AssignmentSubmissions'
import { Daily } from './pages/Daily'
import { Login } from './pages/Login'
import { MySubmissions } from './pages/MySubmissions'
import { NewAssignment } from './pages/NewAssignment'
import { Register } from './pages/Register'
import { SubmissionReport } from './pages/SubmissionReport'
import { TeacherDashboard } from './pages/TeacherDashboard'
import { Weekly } from './pages/Weekly'

/**
 * "/" is just a router. Admins go to their dashboard; students go to Daily,
 * which is the first item in their menu now that Assignments has been removed
 * from it.
 */
function Home() {
  const { user } = useAuth()
  return <Navigate to={user?.role === 'teacher' ? '/admin' : '/daily'} replace />
}

function AdminOnly({ children }: { children: JSX.Element }) {
  return <ProtectedRoute role="teacher">{children}</ProtectedRoute>
}

function StudentOnly({ children }: { children: JSX.Element }) {
  return <ProtectedRoute role="student">{children}</ProtectedRoute>
}

export default function App() {
  return (
    <Routes>
      {/* ------------------------------------------------------------ public */}
      <Route path="/login/:portal" element={<Login />} />
      <Route path="/register/:portal" element={<Register />} />

      {/* There is no landing page: signing in is the front door. */}
      <Route path="/login" element={<Navigate to="/login/student" replace />} />
      <Route path="/register" element={<Navigate to="/register/student" replace />} />
      <Route path="/welcome" element={<Navigate to="/login/student" replace />} />

      {/* --------------------------------------------------------- protected */}
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Home />} />

        {/* Student */}
        <Route
          path="/daily"
          element={
            <StudentOnly>
              <Daily />
            </StudentOnly>
          }
        />
        <Route
          path="/weekly"
          element={
            <StudentOnly>
              <Weekly />
            </StudentOnly>
          }
        />
        <Route path="/submissions" element={<MySubmissions />} />
        <Route path="/submissions/:id" element={<SubmissionReport />} />
        {/* Reached from My submissions, not from the menu. */}
        <Route path="/assignments/:id" element={<AssignmentDetail />} />

        {/* Admin */}
        <Route
          path="/admin"
          element={
            <AdminOnly>
              <AdminDashboard />
            </AdminOnly>
          }
        />
        <Route
          path="/admin/students"
          element={
            <AdminOnly>
              <AdminStudents />
            </AdminOnly>
          }
        />
        <Route
          path="/admin/students/:id"
          element={
            <AdminOnly>
              <AdminStudentDetail />
            </AdminOnly>
          }
        />
        <Route
          path="/admin/assignments"
          element={
            <AdminOnly>
              <TeacherDashboard />
            </AdminOnly>
          }
        />
        <Route
          path="/admin/assignments/new"
          element={
            <AdminOnly>
              <NewAssignment />
            </AdminOnly>
          }
        />
        <Route
          path="/admin/assignments/:id"
          element={
            <AdminOnly>
              <AssignmentSubmissions />
            </AdminOnly>
          }
        />
      </Route>

      {/* Legacy /teacher/* URLs from before the Admin rename. */}
      <Route path="/teacher" element={<Navigate to="/admin/assignments" replace />} />
      <Route
        path="/teacher/assignments/new"
        element={<Navigate to="/admin/assignments/new" replace />}
      />
      <Route path="/teacher/assignments/:id" element={<LegacyAssignmentRedirect />} />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

/** Keeps the :id when forwarding an old /teacher link to /admin. */
function LegacyAssignmentRedirect() {
  const id = window.location.pathname.split('/').pop()
  return <Navigate to={`/admin/assignments/${id}`} replace />
}

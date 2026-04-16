import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import HomePage from './pages/HomePage'
import CompetitionPage from './pages/CompetitionPage'
import ParticipantsPage from './pages/ParticipantsPage'
import BracketsPage from './pages/BracketsPage'
import SchedulePage from './pages/SchedulePage'
import RegistrationPage from './pages/RegistrationPage'
import LoginPage from './pages/LoginPage'
import AdminDashboard from './pages/admin/AdminDashboard'
import AdminParticipants from './pages/admin/AdminParticipants'
import AdminBrackets from './pages/admin/AdminBrackets'
import AdminReferences from './pages/admin/AdminReferences'
import AdminCompetitions from './pages/admin/AdminCompetitions'
import AdminCompetitionDetail from './pages/admin/AdminCompetitionDetail'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/competition/:id" element={<CompetitionPage />} />
        <Route path="/competition/:id/register" element={<RegistrationPage />} />
        <Route path="/competition/:id/participants" element={<ParticipantsPage />} />
        <Route path="/competition/:id/brackets" element={<BracketsPage />} />
        <Route path="/competition/:id/schedule" element={<SchedulePage />} />
        <Route path="/participants" element={<ParticipantsPage />} />
        <Route path="/brackets" element={<BracketsPage />} />
        <Route path="/register" element={<RegistrationPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/admin/participants" element={<AdminParticipants />} />
          <Route path="/admin/brackets" element={<AdminBrackets />} />
          <Route path="/admin/references" element={<AdminReferences />} />
          <Route path="/admin/competitions" element={<AdminCompetitions />} />
          <Route path="/admin/competitions/:id" element={<AdminCompetitionDetail />} />
        </Route>
      </Route>
    </Routes>
  )
}

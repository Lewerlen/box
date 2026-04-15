import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import HomePage from './pages/HomePage'
import ParticipantsPage from './pages/ParticipantsPage'
import BracketsPage from './pages/BracketsPage'
import RegistrationPage from './pages/RegistrationPage'
import LoginPage from './pages/LoginPage'
import AdminDashboard from './pages/admin/AdminDashboard'
import AdminParticipants from './pages/admin/AdminParticipants'
import AdminBrackets from './pages/admin/AdminBrackets'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/participants" element={<ParticipantsPage />} />
        <Route path="/brackets" element={<BracketsPage />} />
        <Route path="/register" element={<RegistrationPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/admin/participants" element={<AdminParticipants />} />
          <Route path="/admin/brackets" element={<AdminBrackets />} />
        </Route>
      </Route>
    </Routes>
  )
}

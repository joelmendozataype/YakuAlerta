import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth'
import Layout from './components/Layout'
import Login from './pages/Login'
import Tablero from './pages/Tablero'
import Alertas from './pages/Alertas'
import Laboratorio from './pages/Laboratorio'
import Reportes from './pages/Reportes'

function Privada({ children }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  return <Layout>{children}</Layout>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Privada><Tablero /></Privada>} />
      <Route path="/alertas" element={<Privada><Alertas /></Privada>} />
      <Route path="/laboratorio" element={<Privada><Laboratorio /></Privada>} />
      <Route path="/reportes" element={<Privada><Reportes /></Privada>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

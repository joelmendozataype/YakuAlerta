import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth'
import Layout from './components/Layout'
import Login from './pages/Login'
import Tablero from './pages/Tablero'
import Alertas from './pages/Alertas'
import Laboratorio from './pages/Laboratorio'
import Reportes from './pages/Reportes'
import MiAgua from './pages/MiAgua'
import VigilanciaSalud from './pages/VigilanciaSalud'
import Priorizacion from './pages/Priorizacion'
import InicioDesa from './pages/InicioDesa'

function Privada({ children }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  return <Layout>{children}</Layout>
}

/**
 * Elige el inicio según el rol: cada perfil entra directamente a la pregunta
 * que su función necesita responder, no a un tablero genérico.
 */
function InicioSegunRol() {
  const { user } = useAuth()
  switch (user?.rol) {
    case 'POBLACION': return <MiAgua />              // ¿puedo tomar el agua hoy?
    case 'SALUD': return <VigilanciaSalud />         // ¿a quién debo vigilar?
    case 'DRVCS': return <Priorizacion />            // ¿dónde invertir?
    case 'DESA': return <InicioDesa />               // ¿qué caso requiere dictamen?
    default: return <Tablero />                      // ATM, JASS y administración
  }
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      {/* La población ve su estado del agua; las instituciones, el tablero. */}
      <Route path="/" element={<Privada><InicioSegunRol /></Privada>} />
      <Route path="/alertas" element={<Privada><Alertas /></Privada>} />
      <Route path="/laboratorio" element={<Privada><Laboratorio /></Privada>} />
      <Route path="/reportes" element={<Privada><Reportes /></Privada>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

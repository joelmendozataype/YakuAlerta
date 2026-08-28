import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth'
import Layout, { NAV, puedeVer } from './components/Layout'
import Login from './pages/Login'
import Tablero from './pages/Tablero'
import Alertas from './pages/Alertas'
import Laboratorio from './pages/Laboratorio'
import Reportes from './pages/Reportes'
import Jass from './pages/Jass'
import Usuarios from './pages/Usuarios'
import Parametros from './pages/Parametros'
import Auditoria from './pages/Auditoria'
import VigilanciaSalud from './pages/VigilanciaSalud'
import Priorizacion from './pages/Priorizacion'
import InicioDesa from './pages/InicioDesa'

/**
 * Envuelve una pantalla del tablero y comprueba que el rol pueda estar en ella.
 *
 * El permiso sale de la misma tabla que dibuja el menú: ocultar una opción sin
 * cerrar su ruta dejaba entrar escribiendo la dirección, y con dos listas
 * separadas una acabaría contradiciendo a la otra.
 */
function Privada({ ruta, children }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />

  const seccion = NAV.find((n) => n.to === ruta)
  if (seccion && !puedeVer(seccion, user.rol)) return <Navigate to="/" replace />
  return <Layout>{children}</Layout>
}

/**
 * Elige el inicio según el rol: cada perfil entra directamente a la pregunta
 * que su función necesita responder, no a un tablero genérico.
 *
 * El vecino no aparece aquí: su pregunta —¿puedo tomar el agua hoy?— la
 * responde la página pública del backend, sin cuenta ni clave.
 */
function InicioSegunRol() {
  const { user } = useAuth()
  switch (user?.rol) {
    case 'SALUD': return <VigilanciaSalud />         // ¿a quién debo vigilar?
    case 'DRVCS': return <Priorizacion />            // ¿dónde invertir?
    case 'DESA': return <InicioDesa />               // ¿qué caso requiere dictamen?
    default: return <Tablero />                     // ATM y administración
  }
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      {/* La población ve su estado del agua; las instituciones, el tablero. */}
      <Route path="/" element={<Privada><InicioSegunRol /></Privada>} />
      <Route path="/alertas" element={<Privada ruta="/alertas"><Alertas /></Privada>} />
      <Route path="/jass" element={<Privada ruta="/jass"><Jass /></Privada>} />
      <Route path="/usuarios" element={<Privada ruta="/usuarios"><Usuarios /></Privada>} />
      <Route path="/parametros" element={<Privada ruta="/parametros"><Parametros /></Privada>} />
      <Route path="/auditoria" element={<Privada ruta="/auditoria"><Auditoria /></Privada>} />
      <Route path="/laboratorio" element={<Privada ruta="/laboratorio"><Laboratorio /></Privada>} />
      <Route path="/reportes" element={<Privada ruta="/reportes"><Reportes /></Privada>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

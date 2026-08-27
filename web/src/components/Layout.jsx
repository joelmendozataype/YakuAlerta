import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

// Cada sección declara qué roles pueden usarla: el menú no ofrece opciones
// que el servidor luego rechazaría.
const NAV = [
  { to: '/', label: 'Tablero', icon: '📊', end: true, roles: null },
  { to: '/alertas', label: 'Alertas', icon: '🔔', roles: null },
  { to: '/laboratorio', label: 'Laboratorio', icon: '🧪', roles: ['DESA', 'ATM', 'ADMIN'] },
  { to: '/reportes', label: 'Reportes', icon: '📄', roles: ['ATM', 'DESA', 'ADMIN'] },
]

const puedeVer = (item, rol) => item.roles === null || item.roles.includes(rol)

export default function Layout({ children }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-agua-800 text-white shadow">
        <div className="mx-auto max-w-7xl px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl">💧</span>
            <div>
              <p className="font-bold leading-tight">YakuAlerta</p>
              <p className="text-[11px] text-agua-200 leading-tight">Vigilancia del agua · Huancavelica</p>
            </div>
          </div>
          <nav className="hidden md:flex items-center gap-1">
            {NAV.filter((n) => puedeVer(n, user?.rol)).map((n) => (
              <NavLink key={n.to} to={n.to} end={n.end}
                className={({ isActive }) =>
                  `px-3 py-2 rounded-lg text-sm font-medium transition ${
                    isActive ? 'bg-agua-900 text-white' : 'text-agua-100 hover:bg-agua-700'
                  }`}>
                <span className="mr-1">{n.icon}</span>{n.label}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-3">
            <div className="text-right hidden sm:block">
              <p className="text-sm font-medium leading-tight">{user?.nombres}</p>
              <p className="text-[11px] text-agua-200 leading-tight">{user?.rol} · {user?.entidad}</p>
            </div>
            <button onClick={() => { logout(); navigate('/login') }}
              className="btn-ghost text-sm !bg-agua-700 !text-white hover:!bg-agua-900">
              Salir
            </button>
          </div>
        </div>
        {/* Nav móvil */}
        <nav className="md:hidden flex items-center gap-1 px-4 pb-2 overflow-x-auto">
          {NAV.filter((n) => puedeVer(n, user?.rol)).map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end}
              className={({ isActive }) =>
                `px-3 py-1.5 rounded-lg text-sm whitespace-nowrap ${
                  isActive ? 'bg-agua-900' : 'bg-agua-700'
                }`}>
              {n.icon} {n.label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main className="flex-1 mx-auto max-w-7xl w-full px-4 py-6">{children}</main>

      <footer className="text-center text-xs text-slate-400 py-4">
        YakuAlerta · MVP Hackathon Kuska Wiñasun UNH 2026 · D.S. N.° 031-2010-SA
      </footer>
    </div>
  )
}

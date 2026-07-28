import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import LoginQR from '../components/LoginQR'

export default function Login() {
  const { login, establecerSesion } = useAuth()
  const navigate = useNavigate()
  const [telefono, setTelefono] = useState('987000020')
  const [clave, setClave] = useState('yaku2026')
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setCargando(true)
    try {
      await login(telefono, clave)
      navigate('/')
    } catch (err) {
      setError(err.message || 'No se pudo iniciar sesión')
    } finally {
      setCargando(false)
    }
  }

  // La app aprobó la vinculación: la sesión llega ya resuelta.
  function onSesionQR(sesion) {
    establecerSesion(sesion)
    navigate('/')
  }

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-4xl">
        {/* Marca */}
        <div className="text-center mb-6">
          <div className="text-4xl">💧</div>
          <h1 className="mt-1 text-2xl font-bold text-agua-800">YakuAlerta</h1>
          <p className="text-sm text-slate-500">Vigilancia del agua · Huancavelica</p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="grid md:grid-cols-2">
            {/* ── Acceso con celular y clave ── */}
            <form onSubmit={onSubmit} className="p-8 md:p-10">
              <h2 className="text-xl font-bold text-slate-800">Te damos la bienvenida</h2>
              <p className="mt-1 text-sm text-slate-500">
                Acceso para ATM, DIRESA/DESA y establecimientos de salud.
              </p>

              <div className="mt-6 space-y-4">
                <div>
                  <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Número de celular <span className="text-rojo">*</span>
                  </label>
                  <input className="input mt-1" value={telefono} inputMode="numeric"
                    onChange={(e) => setTelefono(e.target.value)}
                    placeholder="9XXXXXXXX" required />
                </div>
                <div>
                  <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Clave <span className="text-rojo">*</span>
                  </label>
                  <input className="input mt-1" type="password" value={clave}
                    onChange={(e) => setClave(e.target.value)} required />
                </div>
              </div>

              {error && (
                <p className="mt-4 text-sm text-rojo bg-rojo/10 rounded-lg px-3 py-2">{error}</p>
              )}

              <button className="btn-primary w-full justify-center mt-6" disabled={cargando}>
                {cargando ? 'Ingresando…' : 'Iniciar sesión'}
              </button>

              <div className="mt-6 border-t border-slate-100 pt-4 text-xs text-slate-400 space-y-0.5">
                <p className="font-semibold text-slate-500">Cuentas demo · clave yaku2026</p>
                <p>ATM 987000020 · Admin 987000099</p>
                <p>DESA 987000030 · Salud 987000040</p>
              </div>
            </form>

            {/* ── Acceso por QR ── */}
            <div className="border-t md:border-t-0 md:border-l border-slate-200 bg-slate-50 p-8 md:p-10 flex items-center justify-center">
              <LoginQR onSesion={onSesionQR} />
            </div>
          </div>
        </div>

        <p className="text-center text-xs text-slate-400 mt-6">
          YakuAlerta · Hackathon Kuska Wiñasun UNH 2026
        </p>
      </div>
    </div>
  )
}

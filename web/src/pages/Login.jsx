import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import LoginQR from '../components/LoginQR'

/**
 * Grupos de rol que ofrece el tablero: solo quien decide desde una oficina.
 *
 * Faltan dos a propósito. La JASS opera en el cerro con el celular, sin señal
 * y sin computadora. Y el vecino no necesita cuenta: escanea el QR del aviso
 * fijado en el punto de agua y lee la página pública, sin registrarse.
 */
const GRUPOS = [
  { valor: 'ATM', etiqueta: 'ATM (Autoridad Local)', dni: '70100020' },
  { valor: 'IPRESS_SALUD', etiqueta: 'IPRESS / SALUD', dni: '70100040' },
  { valor: 'DESA', etiqueta: 'DESA (Autoridad Sanitaria)', dni: '70100030' },
  { valor: 'DRVCS', etiqueta: 'DRVCS (Saneamiento)', dni: '70100070' },
  { valor: 'ADMIN', etiqueta: 'Administrador del sistema', dni: '70100099' },
]

export default function Login() {
  const { login, establecerSesion } = useAuth()
  const navigate = useNavigate()
  const [grupo, setGrupo] = useState('')
  const [dni, setDni] = useState('')
  const [clave, setClave] = useState('')
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(false)

  // Al elegir el rol se sugiere su DNI de demostración: agiliza la prueba
  // sin ocultar que el acceso real exige credenciales propias.
  function elegirGrupo(valor) {
    setGrupo(valor)
    setError('')
    const g = GRUPOS.find((x) => x.valor === valor)
    if (g && !dni) setDni(g.dni)
  }

  async function onSubmit(e) {
    e.preventDefault()
    if (!grupo) return setError('Seleccione su tipo de rol para continuar.')
    if (dni.length !== 8) return setError('El DNI debe tener 8 dígitos.')
    setError('')
    setCargando(true)
    try {
      await login(dni, clave, grupo)
      navigate('/')
    } catch (err) {
      setError(err.message || 'No se pudo iniciar sesión')
    } finally {
      setCargando(false)
    }
  }

  function onSesionQR(sesion) {
    establecerSesion(sesion)
    navigate('/')
  }

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-4xl">
        <div className="text-center mb-6">
          <img src="/logo.svg" alt="" className="h-20 w-20 mx-auto" />
          <h1 className="mt-2 text-2xl font-bold text-agua-800">Yakuni</h1>
          <p className="text-sm text-slate-500">Vigilancia del agua · Huancavelica</p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="grid md:grid-cols-2">
            {/* ── Acceso por rol, DNI y clave ── */}
            <form onSubmit={onSubmit} className="p-8 md:p-10">
              <h2 className="text-xl font-bold text-slate-800">Ingresa con tu rol</h2>
              <p className="mt-1 text-sm text-slate-500">
                Cada perfil accede a la información que su función necesita.
              </p>

              <div className="mt-6 space-y-4">
                <div>
                  <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Tipo de rol <span className="text-rojo">*</span>
                  </label>
                  <select className="input mt-1" value={grupo}
                    onChange={(e) => elegirGrupo(e.target.value)} required>
                    <option value="">Seleccione…</option>
                    {GRUPOS.map((g) => (
                      <option key={g.valor} value={g.valor}>{g.etiqueta}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    DNI <span className="text-rojo">*</span>
                  </label>
                  <input className="input mt-1" value={dni} inputMode="numeric" maxLength={8}
                    onChange={(e) => setDni(e.target.value.replace(/\D/g, ''))}
                    placeholder="70100020" required />
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
                {cargando ? 'Ingresando…' : 'Ingresar'}
              </button>

              <p className="mt-5 text-center text-xs text-slate-400">
                Clave de demostración: <span className="font-mono">yaku2026</span>
              </p>
            </form>

            {/* ── Acceso por código QR ── */}
            <div className="border-t md:border-t-0 md:border-l border-slate-200 bg-slate-50 p-8 md:p-10 flex items-center justify-center">
              <LoginQR onSesion={onSesionQR} />
            </div>
          </div>
        </div>

        <p className="text-center text-xs text-slate-400 mt-6">
          Yakuni · Hackathon Kuska Wiñasun UNH 2026
        </p>
      </div>
    </div>
  )
}

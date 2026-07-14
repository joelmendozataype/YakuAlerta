import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

export default function Login() {
  const { login } = useAuth()
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

  return (
    <div className="min-h-screen grid md:grid-cols-2">
      {/* Panel de marca */}
      <div className="hidden md:flex flex-col justify-center gap-6 bg-agua-800 text-white p-12">
        <div className="text-6xl">💧</div>
        <h1 className="text-4xl font-bold">YakuAlerta</h1>
        <p className="text-agua-100 text-lg max-w-md">
          Alerta temprana para agua no segura en reservorios comunales de Huancavelica.
          Del dato de campo a la acción sanitaria, en horas y no en semanas.
        </p>
        <div className="flex gap-3 text-sm">
          <span className="badge bg-verde/20 text-verde-100">🟢 Segura</span>
          <span className="badge bg-amarillo/20 text-amber-100">🟡 En riesgo</span>
          <span className="badge bg-rojo/20 text-red-100">🔴 No segura</span>
        </div>
      </div>

      {/* Formulario */}
      <div className="flex items-center justify-center p-8 bg-slate-100">
        <form onSubmit={onSubmit} className="card w-full max-w-sm space-y-4">
          <div className="md:hidden text-center text-4xl">💧</div>
          <h2 className="text-xl font-bold text-slate-800">Tablero institucional</h2>
          <p className="text-sm text-slate-500">Acceso para ATM, DIRESA/DESA y salud.</p>

          <div>
            <label className="text-sm font-medium text-slate-600">Número de celular</label>
            <input className="input mt-1" value={telefono} onChange={(e) => setTelefono(e.target.value)}
              placeholder="9XXXXXXXX" required />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-600">Clave</label>
            <input className="input mt-1" type="password" value={clave}
              onChange={(e) => setClave(e.target.value)} required />
          </div>

          {error && <p className="text-sm text-rojo bg-rojo/10 rounded-lg px-3 py-2">{error}</p>}

          <button className="btn-primary w-full justify-center" disabled={cargando}>
            {cargando ? 'Ingresando…' : 'Ingresar'}
          </button>

          <div className="text-xs text-slate-400 border-t pt-3 space-y-0.5">
            <p className="font-medium text-slate-500">Cuentas demo:</p>
            <p>ATM → 987000020 · Admin → 987000099</p>
            <p>DESA → 987000030 · Salud → 987000040 · Clave: yaku2026</p>
          </div>
        </form>
      </div>
    </div>
  )
}

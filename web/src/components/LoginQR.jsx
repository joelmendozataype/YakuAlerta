import { useCallback, useEffect, useRef, useState } from 'react'
import QRCode from 'react-qr-code'
import { api } from '../api'

// Genera el secreto de cliente y su hash SHA-256 (Web Crypto, sin dependencias).
async function nuevoSecreto() {
  const bytes = crypto.getRandomValues(new Uint8Array(24))
  const secreto = btoa(String.fromCharCode(...bytes)).replace(/[+/=]/g, '')
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(secreto))
  const hash = Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, '0')).join('')
  return { secreto, hash }
}

const SONDEO_MS = 2000

/**
 * Panel de inicio de sesión por código QR (patrón WhatsApp/Discord Web).
 * Muestra el código, sondea su estado y, al aprobarse desde la app,
 * reclama la sesión y la entrega mediante `onSesion`.
 */
export default function LoginQR({ onSesion }) {
  const [qr, setQr] = useState(null)          // { token, contenido, expiraEn }
  const [estado, setEstado] = useState('CARGANDO')
  const [nombres, setNombres] = useState(null)
  const [restante, setRestante] = useState(0)
  const [error, setError] = useState('')
  const secretoRef = useRef(null)

  const generar = useCallback(async () => {
    setError('')
    setEstado('CARGANDO')
    setNombres(null)
    try {
      const { secreto, hash } = await nuevoSecreto()
      secretoRef.current = secreto
      const r = await api.qrNueva(hash)
      setQr({ token: r.token, contenido: r.contenido_qr })
      setRestante(r.expira_en_seg)
      setEstado('PENDIENTE')
    } catch (e) {
      setError(e.message || 'No se pudo generar el código')
      setEstado('ERROR')
    }
  }, [])

  useEffect(() => { generar() }, [generar])

  // Cuenta regresiva de vigencia
  useEffect(() => {
    if (estado !== 'PENDIENTE' && estado !== 'ESCANEADO') return
    if (restante <= 0) { setEstado('EXPIRADO'); return }
    const t = setTimeout(() => setRestante((s) => s - 1), 1000)
    return () => clearTimeout(t)
  }, [restante, estado])

  // Sondeo del estado de la vinculación
  useEffect(() => {
    if (!qr || (estado !== 'PENDIENTE' && estado !== 'ESCANEADO')) return
    let cancelado = false
    const id = setInterval(async () => {
      try {
        const r = await api.qrEstado(qr.token)
        if (cancelado) return
        if (r.usuario_nombres) setNombres(r.usuario_nombres)

        if (r.estado === 'APROBADO') {
          clearInterval(id)
          const sesion = await api.qrReclamar(qr.token, secretoRef.current)
          onSesion(sesion)
        } else if (r.estado !== estado) {
          setEstado(r.estado)
        }
      } catch {
        /* reintenta en el siguiente ciclo */
      }
    }, SONDEO_MS)
    return () => { cancelado = true; clearInterval(id) }
  }, [qr, estado, onSesion])

  const caducado = estado === 'EXPIRADO' || estado === 'RECHAZADO' || estado === 'ERROR'

  return (
    <div className="flex flex-col items-center text-center">
      {/* Lienzo del código */}
      <div className="relative">
        <div className="rounded-2xl bg-white p-4 shadow-sm border border-slate-200">
          {qr && !caducado ? (
            <QRCode value={qr.contenido} size={176} bgColor="#FFFFFF" fgColor="#0F172A" />
          ) : (
            <div className="h-[176px] w-[176px] grid place-items-center text-slate-300">
              {estado === 'CARGANDO' ? '···' : ''}
            </div>
          )}
        </div>

        {/* Capa de estado sobre el código */}
        {caducado && (
          <button
            onClick={generar}
            className="absolute inset-0 grid place-items-center rounded-2xl bg-white/95 backdrop-blur-sm"
          >
            <span className="flex flex-col items-center gap-2">
              <span className="text-3xl">🔄</span>
              <span className="text-sm font-semibold text-agua-800">
                {estado === 'RECHAZADO' ? 'Acceso cancelado' : 'El código expiró'}
              </span>
              <span className="text-xs text-slate-500">Toca para generar otro</span>
            </span>
          </button>
        )}

        {estado === 'ESCANEADO' && (
          <div className="absolute inset-0 grid place-items-center rounded-2xl bg-white/95 backdrop-blur-sm">
            <span className="flex flex-col items-center gap-2 px-4">
              <span className="h-8 w-8 animate-spin rounded-full border-2 border-agua-500 border-t-transparent" />
              <span className="text-sm font-semibold text-agua-800">
                Confirma en tu celular
              </span>
              {nombres && <span className="text-xs text-slate-500">{nombres}</span>}
            </span>
          </div>
        )}
      </div>

      <h3 className="mt-5 text-lg font-bold text-slate-800">
        Inicia sesión con el código QR
      </h3>
      <p className="mt-1 text-sm text-slate-500 max-w-[15rem]">
        Escanea el código con la <span className="font-semibold">app de YakuAlerta</span> para
        entrar sin escribir tu clave.
      </p>

      {!caducado && estado === 'PENDIENTE' && (
        <p className="mt-3 text-xs text-slate-400">
          El código vence en {String(Math.floor(restante / 60)).padStart(2, '0')}:
          {String(restante % 60).padStart(2, '0')}
        </p>
      )}

      {error && <p className="mt-3 text-xs text-rojo">{error}</p>}

      <p className="mt-4 text-[11px] text-slate-400 max-w-[15rem]">
        Nunca escanees un código de YakuAlerta que te comparta otra persona.
      </p>
    </div>
  )
}

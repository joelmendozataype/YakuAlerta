import { createContext, useContext, useState } from 'react'
import { api } from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem('yaku_user')
    return raw ? JSON.parse(raw) : null
  })

  /** Persiste una sesión ya resuelta (login por clave o vinculación por QR). */
  function establecerSesion(data) {
    localStorage.setItem('yaku_token', data.access_token)
    localStorage.setItem('yaku_user', JSON.stringify(data.usuario))
    setUser(data.usuario)
    return data.usuario
  }

  async function login(telefono, clave) {
    return establecerSesion(await api.login(telefono, clave))
  }

  function logout() {
    localStorage.removeItem('yaku_token')
    localStorage.removeItem('yaku_user')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, establecerSesion }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)

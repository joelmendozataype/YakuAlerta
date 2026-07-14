import { createContext, useContext, useState } from 'react'
import { api } from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem('yaku_user')
    return raw ? JSON.parse(raw) : null
  })

  async function login(telefono, clave) {
    const data = await api.login(telefono, clave)
    localStorage.setItem('yaku_token', data.access_token)
    localStorage.setItem('yaku_user', JSON.stringify(data.usuario))
    setUser(data.usuario)
    return data.usuario
  }

  function logout() {
    localStorage.removeItem('yaku_token')
    localStorage.removeItem('yaku_user')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)

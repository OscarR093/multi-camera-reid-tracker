import { useEffect, useState } from 'react'
import { api } from '../services/api'

interface User {
  id: number
  username: string
  role: string
}

export default function Admin() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('viewer')
  const [msg, setMsg] = useState('')

  const loadUsers = () => {
    setLoading(true)
    api.getUsers()
      .then((res) => setUsers(res.users || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadUsers() }, [])

  const handleCreate = async () => {
    if (!username || !password) return
    try {
      await api.register(username, password, role)
      setUsername('')
      setPassword('')
      setMsg('User created successfully')
      loadUsers()
    } catch (e: any) {
      setMsg(`Error: ${e.message}`)
    }
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-400">Access denied: {error}</p>
        <p className="text-slate-500 mt-2">You need admin privileges to access this page.</p>
      </div>
    )
  }

  return (
    <div>
      <h2 className="text-xl font-semibold text-white mb-6">Admin Panel</h2>

      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700 mb-6">
        <h3 className="text-lg font-medium text-white mb-4">Create User</h3>
        {msg && (
          <div className={`text-sm mb-3 ${msg.includes('Error') ? 'text-red-400' : 'text-green-400'}`}>
            {msg}
          </div>
        )}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-3">
          <input
            className="bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white text-sm"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
          <input
            className="bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white text-sm"
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <select
            className="bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white text-sm"
            value={role}
            onChange={(e) => setRole(e.target.value)}
          >
            <option value="viewer">Viewer</option>
            <option value="admin">Admin</option>
          </select>
          <button
            onClick={handleCreate}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm"
          >
            Create
          </button>
        </div>
      </div>

      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        <div className="px-4 py-3 bg-slate-700">
          <h3 className="text-sm font-medium text-slate-300">Users</h3>
        </div>
        {loading ? (
          <div className="text-slate-400 p-4 text-sm">Loading...</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-750">
              <tr>
                <th className="text-left px-4 py-3 text-slate-300">ID</th>
                <th className="text-left px-4 py-3 text-slate-300">Username</th>
                <th className="text-left px-4 py-3 text-slate-300">Role</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-t border-slate-700">
                  <td className="px-4 py-3 text-slate-400">{u.id}</td>
                  <td className="px-4 py-3 text-slate-300">{u.username}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      u.role === 'admin' ? 'bg-purple-500/20 text-purple-400' : 'bg-slate-500/20 text-slate-400'
                    }`}>
                      {u.role}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

import { useEffect, useState } from 'react'
import { api } from '../services/api'

interface Blacklisted {
  id: number
  global_id: string | null
  description: string | null
  reason: string | null
  created_at: number
  active: number
}

export default function Blacklist() {
  const [entries, setEntries] = useState<Blacklisted[]>([])
  const [loading, setLoading] = useState(true)
  const [globalId, setGlobalId] = useState('')
  const [description, setDescription] = useState('')
  const [reason, setReason] = useState('')

  const load = () => {
    setLoading(true)
    api.getBlacklist()
      .then((res) => setEntries(res.blacklist || []))
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleAdd = async () => {
    try {
      await api.addBlacklist({ global_id: globalId || undefined, description, reason })
      setGlobalId('')
      setDescription('')
      setReason('')
      load()
    } catch (e: any) {
      alert(e.message)
    }
  }

  const handleRemove = async (id: number) => {
    try {
      await api.removeBlacklist(id)
      load()
    } catch (e: any) {
      alert(e.message)
    }
  }

  return (
    <div>
      <h2 className="text-xl font-semibold text-white mb-6">Blacklist</h2>

      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700 mb-6">
        <h3 className="text-lg font-medium text-white mb-4">Add Entry</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
          <input
            className="bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white text-sm"
            placeholder="Global ID (optional)"
            value={globalId}
            onChange={(e) => setGlobalId(e.target.value)}
          />
          <input
            className="bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white text-sm"
            placeholder="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <input
            className="bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white text-sm"
            placeholder="Reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </div>
        <button
          onClick={handleAdd}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm"
        >
          Add to Blacklist
        </button>
      </div>

      {loading ? (
        <div className="text-slate-400">Loading...</div>
      ) : entries.length === 0 ? (
        <div className="text-slate-500 text-center py-8">No entries</div>
      ) : (
        <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-700">
              <tr>
                <th className="text-left px-4 py-3 text-slate-300">ID</th>
                <th className="text-left px-4 py-3 text-slate-300">Global ID</th>
                <th className="text-left px-4 py-3 text-slate-300">Description</th>
                <th className="text-left px-4 py-3 text-slate-300">Reason</th>
                <th className="text-left px-4 py-3 text-slate-300">Actions</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.id} className="border-t border-slate-700">
                  <td className="px-4 py-3 text-slate-400">{e.id}</td>
                  <td className="px-4 py-3 text-slate-300 font-mono text-xs">
                    {e.global_id || '-'}
                  </td>
                  <td className="px-4 py-3 text-slate-300">{e.description || '-'}</td>
                  <td className="px-4 py-3 text-slate-300">{e.reason || '-'}</td>
                  <td className="px-4 py-3">
                    {e.active ? (
                      <button
                        onClick={() => handleRemove(e.id)}
                        className="text-red-400 hover:text-red-300 text-xs"
                      >
                        Deactivate
                      </button>
                    ) : (
                      <span className="text-slate-500 text-xs">Inactive</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

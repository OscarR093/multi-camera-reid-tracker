import { useEffect, useState } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { api } from '../services/api'

interface CountRecord {
  camera_id: string
  hour: string
  count: number
}

export default function AfluencyChart() {
  const [data, setData] = useState<CountRecord[]>([])
  const [hours, setHours] = useState(24)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    api
      .getCountHistory(hours)
      .then((res) => setData(res.data || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [hours])

  const cameras = [...new Set(data.map((d) => d.camera_id))]
  const colors = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6']

  const byHour: Record<string, any> = {}
  for (const d of data) {
    if (!byHour[d.hour]) byHour[d.hour] = { hour: d.hour.slice(11, 16) }
    byHour[d.hour][d.camera_id] = d.count
  }
  const chartData = Object.values(byHour)

  if (loading) {
    return <div className="text-slate-400 text-center py-8">Loading...</div>
  }

  if (error) {
    return (
      <div className="text-red-400 text-center py-8">
        Error loading data: {error}
      </div>
    )
  }

  if (chartData.length === 0) {
    return <div className="text-slate-500 text-center py-8">No data yet</div>
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <span className="text-slate-400 text-sm">Show last</span>
        {[1, 6, 12, 24, 48].map((h) => (
          <button
            key={h}
            onClick={() => setHours(h)}
            className={`px-2 py-0.5 rounded text-xs ${
              hours === h
                ? 'bg-blue-600 text-white'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            {h}h
          </button>
        ))}
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="hour" stroke="#64748b" fontSize={12} />
          <YAxis stroke="#64748b" fontSize={12} />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 6 }}
            labelStyle={{ color: '#e2e8f0' }}
          />
          <Legend />
          {cameras.map((cam, i) => (
            <Line
              key={cam}
              type="monotone"
              dataKey={cam}
              stroke={colors[i % colors.length]}
              dot={false}
              strokeWidth={2}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

import { useWebSocket } from '../hooks/useWebSocket'
import AfluencyChart from '../components/AfluencyChart'

export default function Dashboard() {
  const state = useWebSocket()
  const cameraIds = Object.keys(state.cameras)

  return (
    <div>
      <h2 className="text-xl font-semibold text-white mb-6">Dashboard</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <StatCard
          title="Total Persons"
          value={state.total_count}
          color="blue"
        />
        <StatCard
          title="Cameras Online"
          value={cameraIds.length}
          color="green"
        />
        <StatCard
          title="Active Tracks"
          value={cameraIds.reduce(
            (sum, id) => sum + (state.cameras[id]?.tracks?.length || 0),
            0
          )}
          color="amber"
        />
      </div>

      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <h3 className="text-lg font-medium text-white mb-4">Afluency per Camera</h3>
        <AfluencyChart />
      </div>
    </div>
  )
}

function StatCard({ title, value, color }: { title: string; value: number; color: string }) {
  const colors: Record<string, string> = {
    blue: 'bg-blue-500/10 border-blue-500/30 text-blue-400',
    green: 'bg-green-500/10 border-green-500/30 text-green-400',
    amber: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
  }

  return (
    <div className={`rounded-lg border p-4 ${colors[color] || ''}`}>
      <p className="text-sm opacity-80">{title}</p>
      <p className="text-3xl font-bold mt-1">{value.toLocaleString()}</p>
    </div>
  )
}

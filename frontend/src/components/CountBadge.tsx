import { useWebSocket } from '../hooks/useWebSocket'

export default function CountBadge() {
  const state = useWebSocket()

  return (
    <div className="flex items-center gap-2 bg-slate-700 rounded-lg px-4 py-1.5">
      <div className="flex items-center gap-1.5">
        <span className={`w-2 h-2 rounded-full ${state.total_count > 0 ? 'bg-green-400' : 'bg-slate-400'} animate-pulse`} />
        <span className="text-slate-300 text-sm">Persons:</span>
      </div>
      <span className="text-white font-bold text-lg tabular-nums">
        {state.total_count}
      </span>
    </div>
  )
}

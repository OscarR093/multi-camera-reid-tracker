import { useWebSocket } from '../hooks/useWebSocket'
import CameraFeed from '../components/CameraFeed'

export default function LiveView() {
  const state = useWebSocket()
  const cameraIds = Object.keys(state.cameras)

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-white">Camera Live View</h2>
        <span className="text-slate-400 text-sm">
          {cameraIds.length} camera{cameraIds.length !== 1 ? 's' : ''} connected
        </span>
      </div>

      {cameraIds.length === 0 && (
        <div className="text-slate-500 text-center py-12 border-2 border-dashed border-slate-700 rounded-lg">
          <p className="text-lg">No cameras connected</p>
          <p className="text-sm mt-1">Waiting for camera streams...</p>
        </div>
      )}

      <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(auto-fill, minmax(560px, 1fr))` }}>
        {cameraIds.map((camId) => {
          const cam = state.cameras[camId]
          return (
            <CameraFeed
              key={camId}
              cameraId={camId}
              tracks={cam.tracks}
              count={cam.count}
            />
          )
        })}
      </div>
    </div>
  )
}

interface TrackData {
  local_track_id: number
  global_id: string
  bbox: number[]
  confidence: number
}

interface Props {
  cameraId: string
  tracks: TrackData[]
  count: number
}

export default function CameraFeed({ cameraId, tracks, count }: Props) {
  const mjpegUrl = `/api/cameras/${cameraId}/mjpeg`

  return (
    <div className="relative bg-slate-950 rounded-lg overflow-hidden border border-slate-700">
      <img
        src={mjpegUrl}
        alt={`Camera ${cameraId}`}
        className="w-full h-auto block"
      />
      <div className="absolute top-2 left-2 bg-black/80 px-3 py-1 rounded">
        <span className="text-blue-300 font-bold text-xs font-mono">
          {cameraId}: {count} person{count !== 1 ? 's' : ''}
        </span>
      </div>
      {tracks.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <span className="text-slate-500 text-sm bg-slate-900/80 px-3 py-1 rounded">
            Waiting for detections...
          </span>
        </div>
      )}
    </div>
  )
}

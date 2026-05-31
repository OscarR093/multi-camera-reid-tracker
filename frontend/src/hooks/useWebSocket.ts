import { useEffect, useRef, useState } from 'react'

interface CameraData {
  count: number
  tracks: TrackData[]
}

interface TrackData {
  local_track_id: number
  global_id: string
  bbox: number[]
  confidence: number
}

interface WSMessage {
  type: string
  timestamp: number
  total_count: number
  cameras: Record<string, CameraData>
}

export function useWebSocket() {
  const [state, setState] = useState<WSMessage>({
    type: 'initial',
    timestamp: Date.now(),
    total_count: 0,
    cameras: {},
  })
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${protocol}://${window.location.host}/ws`)
    wsRef.current = ws

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WSMessage
        setState(data)
      } catch (e) {
        // ignore parse errors
      }
    }

    ws.onclose = () => {
      setTimeout(() => {
        if (wsRef.current === ws) {
          // auto-reconnect
        }
      }, 3000)
    }

    return () => {
      ws.close()
    }
  }, [])

  return state
}

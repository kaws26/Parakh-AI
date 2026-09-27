import { useEffect, useRef, useState } from 'react'
import { FaceLandmarker, FilesetResolver } from '@mediapipe/tasks-vision'
import apiClient from '../api/client'

const WASM_URL = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22/wasm'
const MODEL_URL = 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task'

export function useBehaviorMonitor(videoRef, sessionId, enabled) {
  const [status, setStatus] = useState('idle')
  const [warning, setWarning] = useState('')
  const sentAt = useRef({})
  useEffect(() => {
    const video = videoRef.current
    if (!enabled || !sessionId || !video) return undefined
    let disposed = false
    let timer
    let landmarker
    let awayCount = 0
    let multipleCount = 0
    const sendCue = async (cueType, message) => {
      const now = Date.now()
      if (now - (sentAt.current[cueType] || 0) < 90000) return
      sentAt.current[cueType] = now
      setWarning(message)
      try {
        await apiClient.post(`/api/viva/sessions/${sessionId}/behavior-flags`, { cue_type: cueType })
      } catch {
        setWarning(`${message} We couldn't save the teacher review flag.`)
      }
      window.setTimeout(() => setWarning(''), 7000)
    }
    const monitor = async () => {
      try {
        const files = await FilesetResolver.forVisionTasks(WASM_URL)
        landmarker = await FaceLandmarker.createFromOptions(files, {
          baseOptions: { modelAssetPath: MODEL_URL },
          runningMode: 'VIDEO',
          numFaces: 3,
          outputFacialTransformationMatrixes: false,
        })
        if (disposed) { landmarker.close(); return }
        setStatus('active')
        timer = window.setInterval(async () => {
          if (disposed || video.readyState < 2 || !landmarker) return
          try {
            const result = landmarker.detectForVideo(video, performance.now())
            const faces = result.faceLandmarks || []
            multipleCount = faces.length > 1 ? multipleCount + 1 : 0
            if (multipleCount >= 2) {
              multipleCount = 0
              void sendCue('additional_faces', 'More than one face is visible. Please make sure you are alone for this practice session.')
            }
            const face = faces[0]
            if (!face || !face[1] || !face[33] || !face[263]) { awayCount = 0; return }
            const eyeMidpoint = (face[33].x + face[263].x) / 2
            const eyeWidth = Math.max(Math.abs(face[33].x - face[263].x), 0.001)
            const noseOffset = Math.abs(face[1].x - eyeMidpoint) / eyeWidth
            awayCount = noseOffset > 0.24 ? awayCount + 1 : Math.max(0, awayCount - 1)
            if (awayCount >= 8) {
              awayCount = 0
              void sendCue('off_screen_gaze', 'You appear to be facing away from the screen repeatedly. This approximate cue may be wrong.')
            }
          } catch { /* Skip a frame if the browser cannot process it. */ }
        }, 1000)
      } catch {
        if (!disposed) setStatus('unavailable')
      }
    }
    void monitor()
    return () => {
      disposed = true
      if (timer) window.clearInterval(timer)
      landmarker?.close()
    }
  }, [enabled, sessionId, videoRef])
  return { status, warning, dismissWarning: () => setWarning('') }
}

import { useState } from 'react'

export default function MicButton({ onRecording, disabled, stream: sharedStream }) {
  const [recorder, setRecorder] = useState(null)
  const [recording, setRecording] = useState(false)
  const [error, setError] = useState('')
  const toggle = async () => {
    setError('')
    if (recording) { recorder.stop(); return }
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) { setError('Audio recording is unavailable in this browser.'); return }
    try {
      const stream = sharedStream || await navigator.mediaDevices.getUserMedia({ audio: true })
      const audioStream = new MediaStream(stream.getAudioTracks())
      const mimeType = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'].find((type) => MediaRecorder.isTypeSupported(type))
      const media = new MediaRecorder(audioStream, mimeType ? { mimeType } : undefined); const chunks = []
      media.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data) }
      media.onstop = () => { const blob = new Blob(chunks, { type: media.mimeType || 'audio/webm' }); if (!sharedStream) stream.getTracks().forEach((track) => track.stop()); setRecording(false); setRecorder(null); if (blob.size) onRecording(blob) }
      media.start(); setRecorder(media); setRecording(true)
    } catch (e) { setError(e.name === 'NotAllowedError' ? 'Microphone access was denied. Allow microphone access in your browser settings and retry.' : 'Could not access your microphone. Check that it is connected and try again.') }
  }
  return <div className="mic-wrap"><button className={`mic-button ${recording ? 'recording' : ''}`} onClick={toggle} disabled={disabled} aria-label={recording ? 'Stop recording answer' : 'Start recording answer'}><span className="mic-icon">{recording ? '■' : '●'}</span>{recording ? 'Stop recording' : 'Record answer'}</button>{recording && <p className="recording-label"><i /> Recording in progress</p>}{error && <p className="error-text" role="alert">{error}</p>}</div>
}

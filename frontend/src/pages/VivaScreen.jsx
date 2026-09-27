import { useCallback, useEffect, useRef, useState } from 'react'
import { useViva } from '../hooks/useViva'
import { useAuth } from '../hooks/useAuth'
import { useBehaviorMonitor } from '../hooks/useBehaviorMonitor'
import apiClient from '../api/client'
import ConsentModal from '../components/ConsentModal'
import MicButton from '../components/MicButton'
import Timer from '../components/Timer'
import TranscriptDisplay from '../components/TranscriptDisplay'

export default function VivaScreen({ navigate }) {
  const viva = useViva()
  const { user } = useAuth()
  const [busy, setBusy] = useState(false)
  const [startedAt, setStartedAt] = useState(Date.now())
  const [lastAnswer, setLastAnswer] = useState(null)
  const [step, setStep] = useState('consent')
  const [number, setNumber] = useState(0)
  const [mediaStream, setMediaStream] = useState(null)
  const [mediaError, setMediaError] = useState('')
  const [cameraOn, setCameraOn] = useState(true)
  const [micOn, setMicOn] = useState(true)
  const [speaking, setSpeaking] = useState(false)
  const videoRef = useRef(null)
  const advancing = useRef(false)
  const { status: monitorStatus, warning: cueWarning, dismissWarning } = useBehaviorMonitor(videoRef, viva.sessionId, Boolean(viva.sessionId && step !== 'consent' && cameraOn))

  useEffect(() => {
    if (!mediaStream || !videoRef.current) return
    videoRef.current.srcObject = mediaStream
    videoRef.current.play().catch(() => {})
  }, [mediaStream])
  useEffect(() => () => {
    window.speechSynthesis?.cancel()
    mediaStream?.getTracks().forEach((track) => track.stop())
  }, [mediaStream])
  const speak = useCallback((text) => {
    if (!text || !('speechSynthesis' in window)) return
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.rate = 0.96
    utterance.onstart = () => setSpeaking(true)
    utterance.onend = () => setSpeaking(false)
    utterance.onerror = () => setSpeaking(false)
    window.speechSynthesis.speak(utterance)
  }, [])

  const begin = async (retainAudio, cameraConsent) => {
    setBusy(true); setMediaError(''); viva.setError('')
    let stream
    try {
      if (!cameraConsent) throw new Error('Camera permission and local camera cue consent are required to start the video viva.')
      await apiClient.get('/api/health/ai')
      if (!navigator.mediaDevices?.getUserMedia) throw new Error('Camera and microphone access is unavailable. Open this site in a supported browser over localhost or HTTPS.')
      stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: { facingMode: 'user', width: { ideal: 960 }, height: { ideal: 540 } } })
      setMediaStream(stream)
      const session = await viva.startSession()
      await apiClient.post('/api/consent', { session_id: session.id, audio_retention_consent: retainAudio, transcript_consent: true, camera_analysis_consent: true })
      setStartedAt(Date.now()); setStep('question')
      const question = await viva.getNextQuestion()
      if (!question) navigate(`/report/${session.id}`)
    } catch (error) {
      stream?.getTracks().forEach((track) => track.stop())
      setMediaStream(null)
      const message = error.name === 'NotAllowedError'
        ? 'Camera or microphone permission was denied. Allow both in your browser and try again.'
        : error.name === 'NotFoundError'
          ? 'No camera or microphone was found. Connect both devices and retry.'
          : error.userMessage || error.message || 'Could not start the interview. Check the local AI service and try again.'
      setMediaError(message)
      viva.setError(message)
    } finally { setBusy(false) }
  }
  const submit = async (blob) => {
    try {
      setBusy(true); setStep('processing'); window.speechSynthesis?.cancel(); setSpeaking(false)
      const answer = await viva.submitAnswer(blob)
      answer.followupError = answer.followup_error
      setLastAnswer(answer); setNumber((n) => n + 1); setStep('result')
    } catch (error) {
      const message = error.userMessage || 'We could not process the answer. Check Ollama and local transcription, then retry.'
      viva.setError(message); setStep('question')
    } finally { setBusy(false) }
  }
  const next = async () => {
    if (advancing.current) return
    advancing.current = true; setLastAnswer(null); setBusy(true)
    try {
      const question = await viva.getNextQuestion()
      if (!question) { navigate(`/report/${viva.sessionId}`); return }
      setStep('question')
    } catch (error) { viva.setError(error.userMessage || 'Could not load the next question.') }
    finally { setBusy(false); advancing.current = false }
  }
  useEffect(() => {
    if (step === 'question' && viva.currentQuestion) speak(viva.currentQuestion.question_text)
    return () => { window.speechSynthesis?.cancel() }
  }, [step, viva.currentQuestion, speak])
  useEffect(() => {
    if (step === 'result') { const timer = window.setTimeout(next, 5200); return () => window.clearTimeout(timer) }
  }, [step])
  const hangUp = async () => {
    window.speechSynthesis?.cancel()
    try { await viva.finishSession() } catch { /* Keep the local exit available if the API is offline. */ }
    navigate(viva.sessionId ? `/report/${viva.sessionId}` : '/')
  }
  const toggleMic = () => {
    const enabled = !micOn
    setMicOn(enabled)
    mediaStream?.getAudioTracks().forEach((track) => { track.enabled = enabled })
  }
  const toggleCamera = () => {
    const enabled = !cameraOn
    setCameraOn(enabled)
    mediaStream?.getVideoTracks().forEach((track) => { track.enabled = enabled })
  }
  if (step === 'consent') return <>{mediaError && <main className="page-shell"><p className="error-text notice" role="alert">{mediaError}</p></main>}<ConsentModal busy={busy} onBegin={begin}/></>

  return <main className="call-shell"><header className="call-header"><button className="back-button" onClick={hangUp}>← Exit interview</button><div className="viva-brand"><span className="brand-mark small">V<span>.</span></span> VIVA PRACTICE</div><div className="call-timer"><span className="live-dot"/> LIVE <Timer startedAt={startedAt}/></div></header><div className="call-meta"><div><span className="eyebrow">PRACTICE INTERVIEW</span><h1>Take your time, {user?.full_name?.split(' ')[0] || 'there'}.</h1></div><span className="call-counter">QUESTION {Math.max(1, number + (step === 'question' ? 1 : 0))} / 5</span></div>
    <section className="call-grid" aria-label="AI viva call"><div className="human-tile"><video ref={videoRef} autoPlay playsInline muted className={cameraOn ? '' : 'camera-hidden'}/>{!cameraOn && <div className="camera-off"><span>{user?.full_name?.slice(0, 1)?.toUpperCase() || 'S'}</span><p>Camera off</p></div>}<span className="tile-label">{user?.full_name || 'You'} <i className={micOn ? '' : 'muted-dot'}/></span><span className="tile-corner">YOU</span></div><div className={`ai-tile ${speaking ? 'ai-speaking' : ''}`}><div className="ai-orbit orbit-one"/><div className="ai-orbit orbit-two"/><div className={`ai-avatar ${speaking ? 'avatar-speaking' : ''}`}><span className="avatar-glow"/><span className="avatar-face"><i/><i/><b/></span></div><span className="ai-status"><i className={speaking ? 'pulse-dot' : ''}/>{speaking ? 'Speaking' : 'Viva interviewer'}</span><span className="tile-corner">AI EXAMINER</span></div></section>
    {cueWarning && <div className="cue-warning" role="status"><strong>Camera cue</strong><span>{cueWarning} The cue is approximate and will only be reviewed by your teacher.</span><button aria-label="Dismiss camera cue" onClick={dismissWarning}>×</button></div>}
    {monitorStatus === 'unavailable' && <p className="monitor-note">Local camera cue checking could not load. Your video remains on this device and the interview can continue.</p>}
    <section className="call-question" aria-live="polite">{step === 'processing' ? <div className="processing call-processing"><span className="spinner"/><h2>Listening to your answer…</h2><p>Transcribing locally and preparing your feedback.</p></div> : step === 'result' ? <><p className="eyebrow">ANSWER RECEIVED</p><h2>Thank you. Let’s explore that.</h2><TranscriptDisplay transcript={lastAnswer?.transcript}/>{lastAnswer?.followupError && <p className="monitor-note" role="status">{lastAnswer.followupError} Continuing with the question list.</p>}<p className="muted auto-next">Next question coming up…</p></> : <><p className="eyebrow">{speaking ? 'YOUR AI INTERVIEWER IS ASKING' : 'YOUR QUESTION'}</p><h2 className="question-text">{viva.currentQuestion?.question_text || 'Preparing your question…'}</h2><p className="prompt-hint">Speak naturally. You can take a moment to organize your thoughts.</p><div className="call-actions"><button className="button secondary" onClick={() => speak(viva.currentQuestion?.question_text)}>↻ Hear question</button><MicButton disabled={busy || !micOn} onRecording={submit} stream={mediaStream}/></div>{viva.error && <p className="error-text" role="alert">{viva.error}</p>}</>}</section>
    <footer className="call-controls"><button className={`call-control ${micOn ? '' : 'control-off'}`} onClick={toggleMic}><span>{micOn ? '🎙' : '🔇'}</span>{micOn ? 'Mute mic' : 'Unmute mic'}</button><button className={`call-control ${cameraOn ? '' : 'control-off'}`} onClick={toggleCamera}><span>{cameraOn ? '▣' : '□'}</span>{cameraOn ? 'Turn camera off' : 'Turn camera on'}</button><button className="call-control hangup" onClick={hangUp}><span>×</span>End interview</button></footer><p className="privacy-foot">Your camera frames are analyzed locally and never uploaded. Detected cues are approximate and do not determine your score.</p></main>
}

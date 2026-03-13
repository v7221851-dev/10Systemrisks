import { useState } from 'react'
import { SYSTEM_NAMES_RU } from './constants'
import { sendChatMessage } from './api'

const SYSTEM_ORDER = [
  'Neuro', 'Cardio', 'Hormone', 'Metabolic', 'Immune', 'Renal',
  'Hepatic', 'Musculoskeletal', 'Inflammatory', 'SkinHair', 'Gastric', 'Ocular',
]

// Позиции точек внутри силуэта тела (top%, left%) — только для систем с pct < 100%
const BODY_POSITIONS = {
  Ocular: { top: 8, left: 50 },
  Neuro: { top: 14, left: 50 },
  SkinHair: { top: 12, left: 50 },
  Hormone: { top: 22, left: 50 },
  Cardio: { top: 30, left: 50 },
  Immune: { top: 34, left: 50 },
  Inflammatory: { top: 42, left: 50 },
  Hepatic: { top: 46, left: 52 },
  Renal: { top: 48, left: 48 },
  Gastric: { top: 52, left: 50 },
  Metabolic: { top: 56, left: 50 },
  Musculoskeletal: { top: 62, left: 50 },
}

function scoreToPercent(score) {
  if (score == null) return 0
  return Math.max(0, Math.min(100, Math.round(score * 20)))
}

function getRiskLabel(percent) {
  if (percent <= 44) return 'Высокий'
  if (percent <= 65) return 'Умеренный'
  return 'Низкий'
}

function BioTechResults({ data, onRestart }) {
  const { finalScore, percent, zoneName, brief, groupScores = {}, aiRecommendations = '', userInputs = {}, sex, age } = data || {}
  const [aiQuery, setAiQuery] = useState('')
  const [chatHistory, setChatHistory] = useState([])
  const [chatLoading, setChatLoading] = useState(false)
  const [chatError, setChatError] = useState(null)

  const displayPercent = percent ?? 0
  const displayBrief = brief ?? 'Нет данных для расчёта.'

  const systemsNotInNorm = SYSTEM_ORDER.filter((key) => scoreToPercent(groupScores[key]) < 100)

  const handleDownloadReport = () => {
    const lines = [
      'Отчёт оценки рисков — MDSA Bio-Tech',
      `Дата: ${new Date().toLocaleString('ru-RU')}`,
      '',
      `Интегральный индекс: ${displayPercent}%`,
      `Зона: ${zoneName}`,
      `Статус: ${displayBrief}`,
      '',
      '--- Список систем ---',
      ...SYSTEM_ORDER.map((key) => {
        const pct = scoreToPercent(groupScores[key])
        const name = SYSTEM_NAMES_RU[key] || key
        const label = getRiskLabel(pct)
        return `${name}: ${pct}% (${label})`
      }),
      '',
      '--- AI рекомендации ---',
      aiRecommendations || 'Нет данных',
    ]
    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report-${new Date().toISOString().slice(0, 10)}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleSendChat = async () => {
    const msg = aiQuery.trim()
    if (!msg || chatLoading) return
    setChatLoading(true)
    setChatError(null)
    const userMsg = { role: 'user', content: msg }
    const newHistory = [...chatHistory, userMsg]
    setChatHistory(newHistory)
    setAiQuery('')
    try {
      const res = await sendChatMessage(msg, chatHistory, userInputs, groupScores, sex, age)
      if (res.error) {
        setChatError(res.error)
        setChatHistory(chatHistory)
      } else if (res.response) {
        setChatHistory((h) => [...h, { role: 'assistant', content: res.response }])
      }
    } catch (e) {
      setChatError(e.message)
      setChatHistory(chatHistory)
    } finally {
      setChatLoading(false)
    }
  }

  return (
    <div className="relative flex min-h-screen w-full flex-col bg-background-dark overflow-x-hidden">
      <header className="flex items-center justify-between border-b border-primary/20 px-6 py-4 sticky top-0 bg-background-dark/80 backdrop-blur-md z-50">
        <div className="flex items-center gap-4 text-primary">
          <div className="size-8 flex items-center justify-center bg-primary/10 rounded-lg">
            <span className="material-symbols-outlined text-primary">neurology</span>
          </div>
          <div>
            <h2 className="text-slate-100 text-lg font-bold leading-tight tracking-tight uppercase">MDSA Bio-Tech</h2>
            <p className="text-primary/60 text-[10px] font-bold tracking-[0.2em] uppercase">Integral Health Score 10.0</p>
          </div>
        </div>
        <div className="flex items-center gap-3 pl-4 border-l border-slate-700">
          <div className="flex items-center gap-4">
            <p className="text-slate-100 text-sm font-bold hidden sm:block">Результаты оценки</p>
            {onRestart && (
              <button
                onClick={onRestart}
                className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:bg-slate-700 text-xs font-bold uppercase"
              >
                Начать сначала
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1 p-6 relative">
        <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-20">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 size-[600px] border border-primary/30 rounded-full animate-pulse" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 size-[800px] border border-primary/10 rounded-full" />
          <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 blur-[120px] rounded-full" />
        </div>

        <div className="grid grid-cols-12 gap-6 relative z-10">
          <div className="col-span-12 lg:col-span-3 flex flex-col gap-6">
            <div className="p-5 rounded-xl bg-slate-900/40 border border-slate-800 backdrop-blur-sm">
              <div className="flex justify-between items-start mb-2">
                <span className="text-slate-400 text-xs font-bold uppercase tracking-wider">Интегральный индекс</span>
                <span className="material-symbols-outlined text-primary size-5">monitor_heart</span>
              </div>
              <div className="flex items-end gap-2">
                <span className="text-3xl font-bold text-slate-100">{displayPercent}</span>
                <span className="text-primary text-sm font-medium mb-1 uppercase">%</span>
              </div>
              <div className="mt-3 h-1 w-full bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full shadow-[0_0_10px_rgba(13,185,242,0.8)] transition-all duration-500"
                  style={{ width: `${displayPercent}%` }}
                />
              </div>
              <p className="text-slate-400 text-xs mt-2">{zoneName}</p>
            </div>

            <div className="p-5 rounded-xl bg-slate-900/40 border border-slate-800 backdrop-blur-sm">
              <div className="flex justify-between items-start mb-2">
                <span className="text-slate-400 text-xs font-bold uppercase tracking-wider">Статус</span>
                <span className="material-symbols-outlined text-primary size-5">psychology</span>
              </div>
              <p className="text-slate-100 text-sm font-medium">{displayBrief}</p>
            </div>

            <div className="flex-1 p-5 rounded-xl bg-slate-900/60 border border-primary/20 flex flex-col gap-4">
              <div className="flex items-center gap-3">
                <div className="size-10 rounded-full bg-primary/20 flex items-center justify-center">
                  <span className="material-symbols-outlined text-primary">smart_toy</span>
                </div>
                <div>
                  <h3 className="text-slate-100 font-bold text-sm">BIO-LINK AI</h3>
                  <p className="text-primary text-[10px] font-bold uppercase">Персонализированные рекомендации</p>
                </div>
              </div>
              <div className="flex-1 bg-slate-950/50 rounded-lg p-3 text-xs leading-relaxed text-slate-300 border border-slate-800 min-h-[120px] max-h-[200px] overflow-y-auto flex flex-col gap-2">
                <div className="whitespace-pre-wrap">{aiRecommendations || 'Загрузка рекомендаций...'}</div>
                {chatHistory.map((m, i) => (
                  <div key={i} className={m.role === 'user' ? 'text-primary/90' : 'text-slate-300'}>
                    {m.role === 'user' ? 'Вы: ' : 'AI: '}
                    {m.content}
                  </div>
                ))}
                {chatError && <p className="text-red-400 text-[10px]">{chatError}</p>}
              </div>
              <div className="relative">
                <input
                  className="w-full bg-slate-800 border-none rounded-lg py-2 pl-3 pr-12 text-xs text-slate-100 placeholder:text-slate-500 focus:ring-1 focus:ring-primary"
                  placeholder="Спросить AI о здоровье..."
                  type="text"
                  value={aiQuery}
                  onChange={(e) => setAiQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendChat()}
                />
                <button
                  onClick={handleSendChat}
                  disabled={!aiQuery.trim() || chatLoading}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-primary disabled:opacity-50 hover:opacity-80"
                >
                  <span className="material-symbols-outlined text-lg">send</span>
                </button>
              </div>
            </div>
          </div>

          <div className="col-span-12 lg:col-span-6 flex flex-col items-center justify-center relative min-h-[500px]">
            <div className="absolute top-0 text-center">
              <h1 className="text-4xl font-black text-slate-100 tracking-tighter">Ваши зоны риска</h1>
            </div>
            <div className="relative w-full aspect-square max-w-md flex items-center justify-center group">
              <div className="absolute inset-0 bg-primary/5 rounded-full blur-3xl scale-75" />
              <div
                className="w-full h-full bg-contain bg-center bg-no-repeat relative z-10 cursor-crosshair"
                style={{
                  backgroundImage: `url('https://upload.wikimedia.org/wikipedia/commons/5/53/Human_body_outline.png')`,
                }}
              >
                {systemsNotInNorm.map((systemKey) => {
                  const pos = BODY_POSITIONS[systemKey]
                  if (!pos) return null
                  const pct = scoreToPercent(groupScores[systemKey])
                  const name = SYSTEM_NAMES_RU[systemKey] || systemKey
                  return (
                    <div
                      key={systemKey}
                      className="absolute flex items-center gap-2 group/callout"
                      style={{ top: `${pos.top}%`, left: `${pos.left}%`, transform: 'translate(-50%, -50%)' }}
                    >
                      <div className="size-3 rounded-full bg-primary shadow-[0_0_10px_#0db9f2] animate-ping absolute" />
                      <div className="size-3 rounded-full bg-primary relative z-20" />
                      <div className="bg-background-dark/80 border border-primary/50 backdrop-blur-md p-2 rounded-lg translate-x-4 opacity-0 group-hover/callout:opacity-100 transition-all whitespace-nowrap">
                        <p className="text-[10px] font-bold text-primary uppercase">{name}</p>
                        <p className="text-[8px] text-slate-300">{pct}%</p>
                      </div>
                    </div>
                  )
                })}
              </div>
              <div className="absolute inset-0 border-[1px] border-primary/20 rounded-full scale-110 pointer-events-none" />
              <div className="absolute inset-0 border-t-2 border-primary/40 rounded-full scale-105 rotate-45 pointer-events-none" />
            </div>
            <div className="absolute bottom-0 flex gap-4 w-full justify-center flex-wrap">
              <div className="px-4 py-2 bg-slate-900/50 border border-slate-700 rounded-full flex items-center gap-2">
                <span className="size-2 rounded-full bg-green-500 shadow-[0_0_5px_#22c55e]" />
                <span className="text-[10px] font-bold text-slate-300 uppercase">System Integrity: {displayPercent}%</span>
              </div>
              <div className="px-4 py-2 bg-slate-900/50 border border-slate-700 rounded-full flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-xs">sync</span>
                <span className="text-[10px] font-bold text-slate-300 uppercase">Зона: {zoneName}</span>
              </div>
            </div>
          </div>

          <div className="col-span-12 lg:col-span-3 flex flex-col gap-6">
            <div className="p-6 rounded-xl bg-slate-900/40 border border-slate-800 backdrop-blur-sm relative overflow-hidden">
              <div className="absolute top-0 right-0 w-20 h-20 bg-primary/5 -rotate-45 translate-x-8 -translate-y-8" />
              <h3 className="text-slate-100 text-sm font-bold mb-4 flex items-center gap-2 uppercase tracking-widest">
                <span className="material-symbols-outlined text-primary">warning</span>
                Risk Matrix
              </h3>
              <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2">
                {SYSTEM_ORDER.map((systemKey) => {
                  const score = groupScores[systemKey]
                  const pct = scoreToPercent(score)
                  const label = getRiskLabel(pct)
                  return (
                    <div key={systemKey}>
                      <div className="flex justify-between text-[10px] font-bold uppercase mb-1">
                        <span className="text-slate-400">{SYSTEM_NAMES_RU[systemKey] || systemKey}</span>
                        <span className="text-primary">{label}</span>
                      </div>
                      <div className="h-1.5 w-full bg-slate-800 rounded-full">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${pct}%`,
                            backgroundColor: pct <= 44 ? '#e74c3c' : pct <= 65 ? '#f1c40f' : 'rgba(13,185,242,0.6)',
                          }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
              <button
                onClick={handleDownloadReport}
                className="w-full mt-6 py-2 bg-primary/10 border border-primary/30 text-primary text-xs font-bold rounded-lg hover:bg-primary/20 transition-all uppercase tracking-widest flex items-center justify-center gap-2"
              >
                <span className="material-symbols-outlined text-sm">download</span>
                Скачать отчёт
              </button>
            </div>
          </div>
        </div>

        <div className="mt-8 flex flex-wrap justify-between items-center bg-slate-900/50 border border-slate-800 p-4 rounded-xl">
          <div className="flex gap-6">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Node ID:</span>
              <span className="text-[10px] font-mono text-primary">BIO-HEALTH-001</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Connection:</span>
              <span className="text-[10px] font-mono text-primary">Encrypted (AES-256)</span>
            </div>
          </div>
          <div className="flex gap-2">
            <span className="material-symbols-outlined text-primary text-sm">database</span>
            <span className="text-[10px] font-bold text-slate-300 uppercase tracking-widest">Biometric Ledger Active</span>
          </div>
        </div>
      </main>
    </div>
  )
}

export default BioTechResults

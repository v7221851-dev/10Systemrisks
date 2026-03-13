import { useState, useEffect } from 'react'
import { fetchKnowledge } from './api'
import FormStep from './FormStep'
import OcrUpload from './OcrUpload'
import { SYSTEM_NAMES_RU } from './constants'

function FormFlow({ onComplete }) {
  const [knowledge, setKnowledge] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState({})
  const [sex, setSex] = useState(null)
  const [age, setAge] = useState(null)

  useEffect(() => {
    fetchKnowledge()
      .then(setKnowledge)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen bg-background-dark flex items-center justify-center">
        <div className="text-primary/60 text-sm">Загрузка данных...</div>
      </div>
    )
  }
  if (error || !knowledge) {
    return (
      <div className="min-h-screen bg-background-dark flex items-center justify-center p-8">
        <div className="p-6 rounded-xl bg-slate-900/40 border border-red-500/50 max-w-md">
          <p className="text-red-400 text-sm mb-4">Ошибка загрузки: {error || 'Нет данных'}</p>
          <p className="text-slate-400 text-xs">Убедитесь, что API запущен (uvicorn api.main:app --reload) и GOOGLE_CREDENTIALS_JSON настроен.</p>
        </div>
      </div>
    )
  }

  const { risk_groups, factors_by_group } = knowledge
  const totalSteps = risk_groups.length
  const currentGroup = risk_groups[step]
  const factors = factors_by_group[currentGroup] || []

  const handleChange = (factorId, value) => {
    setAnswers((prev) => ({ ...prev, [factorId]: value }))
  }

  const handleOcrAddToCalculation = (extracted) => {
    setAnswers((prev) => ({ ...prev, ...extracted }))
  }

  const factorNames = {}
  if (knowledge?.factors_by_group) {
    for (const group of Object.values(knowledge.factors_by_group)) {
      for (const f of group) {
        factorNames[f.factor_id] = f.factor_name
      }
    }
  }

  const handleNext = () => {
    if (step < totalSteps - 1) setStep(step + 1)
  }

  const handleBack = () => {
    if (step > 0) setStep(step - 1)
  }

  const handleFinish = () => {
    onComplete({ answers, sex, age })
  }

  return (
    <div className="relative flex min-h-screen w-full flex-col bg-background-dark overflow-x-hidden">
      <header className="flex items-center justify-between border-b border-primary/20 px-6 py-4 flex-wrap gap-4">
        <div className="flex items-center gap-4 text-primary">
          <div className="size-8 flex items-center justify-center bg-primary/10 rounded-lg">
            <span className="material-symbols-outlined text-primary">neurology</span>
          </div>
          <div>
            <h2 className="text-slate-100 text-lg font-bold leading-tight tracking-tight uppercase">MDSA Bio-Tech</h2>
            <p className="text-primary/60 text-[10px] font-bold tracking-[0.2em] uppercase">Оценка рисков</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-slate-500 text-xs uppercase">Пол</span>
            <select
              value={sex ?? ''}
              onChange={(e) => setSex(e.target.value || null)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-slate-100 text-xs"
            >
              <option value="">—</option>
              <option value="M">Мужской</option>
              <option value="F">Женский</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-slate-500 text-xs uppercase">Возраст</span>
            <input
              type="number"
              min={1}
              max={120}
              value={age ?? ''}
              onChange={(e) => setAge(e.target.value ? parseInt(e.target.value, 10) : null)}
              placeholder="—"
              className="w-16 bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-slate-100 text-xs"
            />
          </div>
        </div>
      </header>

      <main className="flex-1 p-6 md:p-8 max-w-2xl mx-auto w-full">
        <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-10">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 size-[600px] border border-primary/30 rounded-full" />
        </div>

        <div className="relative z-10">
          <OcrUpload onAddToCalculation={handleOcrAddToCalculation} factorNames={factorNames} />
          <FormStep
            step={step}
            totalSteps={totalSteps}
            groupName={SYSTEM_NAMES_RU[currentGroup] || currentGroup}
            factors={factors}
            answers={answers}
            onChange={handleChange}
            onBack={handleBack}
            onNext={handleNext}
            onFinish={handleFinish}
            isLast={step === totalSteps - 1}
          />
        </div>
      </main>
    </div>
  )
}

export default FormFlow

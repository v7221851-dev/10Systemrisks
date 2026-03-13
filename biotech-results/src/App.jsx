import { useState } from 'react'
import Landing from './Landing'
import FormFlow from './FormFlow'
import BioTechResults from './BioTechResults'
import { calculate, fetchRecommendations } from './api'

function App() {
  const [page, setPage] = useState('landing')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleFormComplete = async ({ answers, sex, age }) => {
    setLoading(true)
    setError(null)
    try {
      const calc = await calculate(answers, sex, age)
      setResult({
        ...calc,
        sex,
        age,
      })
      setPage('results')
      // Запрос рекомендаций в фоне — обновим результат когда придут
      fetchRecommendations(
        calc.user_inputs || {},
        calc.group_scores || {},
        sex,
        age
      ).then((r) => {
        if (r.recommendations) {
          setResult((prev) => (prev ? { ...prev, aiRecommendations: r.recommendations } : prev))
        }
      }).catch(() => {})
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleRestart = () => {
    setPage('landing')
    setResult(null)
    setError(null)
  }

  if (page === 'landing') {
    return <Landing onStart={() => setPage('form')} />
  }

  if (page === 'form') {
    if (loading) {
      return (
        <div className="min-h-screen bg-background-dark flex items-center justify-center">
          <div className="text-primary text-sm">Расчёт результатов...</div>
        </div>
      )
    }
    if (error) {
      return (
        <div className="min-h-screen bg-background-dark flex items-center justify-center p-8">
          <div className="p-6 rounded-xl bg-slate-900/40 border border-red-500/50 max-w-md text-center">
            <p className="text-red-400 text-sm mb-4">Ошибка: {error}</p>
            <button
              onClick={() => { setError(null); setPage('form') }}
              className="px-4 py-2 bg-slate-800 text-slate-300 rounded-lg text-sm"
            >
              Назад к форме
            </button>
          </div>
        </div>
      )
    }
    return <FormFlow onComplete={handleFormComplete} />
  }

  if (page === 'results' && result) {
    return (
      <BioTechResults
        data={{
          finalScore: result.final_score,
          percent: result.percent,
          zoneName: result.zone_name,
          brief: result.brief,
          groupScores: result.group_scores || {},
          aiRecommendations: result.aiRecommendations || 'Загрузка рекомендаций...',
          userInputs: result.user_inputs || {},
          sex: result.sex,
          age: result.age,
        }}
        onRestart={handleRestart}
      />
    )
  }

  return <Landing onStart={() => setPage('form')} />
}

export default App

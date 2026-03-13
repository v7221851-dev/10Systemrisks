function FormStep({ step, totalSteps, groupName, factors, answers, onChange, onBack, onNext, onFinish, isLast }) {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <span className="text-slate-400 text-xs font-bold uppercase tracking-wider">
          Шаг {step + 1} из {totalSteps}
        </span>
        <div className="h-1.5 flex-1 max-w-xs ml-4 bg-slate-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-primary rounded-full transition-all"
            style={{ width: `${((step + 1) / totalSteps) * 100}%` }}
          />
        </div>
      </div>

      <h2 className="text-2xl font-bold text-slate-100">{groupName}</h2>

      <div className="space-y-4">
        {factors.map((f) => {
          const isRange = (f.unit_type || '').includes('range')
          const isSelect = (f.unit_type || '').includes('select')
          const label = f.unit_name ? `${f.factor_name}, ${f.unit_name}` : f.factor_name

          if (isRange) {
            const rawVal = answers[f.factor_id] ?? f.start_val
            const val = typeof rawVal === 'number' ? Math.round(rawVal * 100) / 100 : parseFloat(rawVal) || Math.round((f.start_val || 0) * 100) / 100
            return (
              <div key={f.factor_id} className="p-4 rounded-xl bg-slate-900/40 border border-slate-800">
                <label className="block text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">
                  {label}
                </label>
                {f.norm_min != null && f.norm_max != null && (
                  <p className="text-[10px] text-primary/80 mb-2">Норма: {f.norm_min}–{f.norm_max}</p>
                )}
                <input
                  type="number"
                  min={f.min_val}
                  max={f.max_val}
                  step={0.01}
                  value={val}
                  onChange={(e) => {
                    const v = parseFloat(e.target.value)
                    onChange(f.factor_id, isNaN(v) ? val : Math.round(v * 100) / 100)
                  }}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-slate-100 text-sm focus:ring-1 focus:ring-primary focus:border-primary"
                />
              </div>
            )
          }
          if (isSelect) {
            const val = answers[f.factor_id] ?? 'Норма'
            const options = ['Норма', 'Умеренно', 'Критично']
            return (
              <div key={f.factor_id} className="p-4 rounded-xl bg-slate-900/40 border border-slate-800">
                <label className="block text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">
                  {label}
                </label>
                <select
                  value={val}
                  onChange={(e) => onChange(f.factor_id, e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-slate-100 text-sm focus:ring-1 focus:ring-primary focus:border-primary"
                >
                  {options.map((o) => (
                    <option key={o} value={o}>{o}</option>
                  ))}
                </select>
              </div>
            )
          }
          return null
        })}
      </div>

      <div className="flex gap-4 pt-4">
        <button
          onClick={onBack}
          disabled={step === 0}
          className="px-6 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all text-sm font-bold uppercase"
        >
          Назад
        </button>
        {isLast ? (
          <button
            onClick={onFinish}
            className="px-8 py-2 bg-primary/20 border border-primary/50 text-primary rounded-lg hover:bg-primary/30 transition-all text-sm font-bold uppercase"
          >
            Рассчитать
          </button>
        ) : (
          <button
            onClick={onNext}
            className="px-8 py-2 bg-primary/20 border border-primary/50 text-primary rounded-lg hover:bg-primary/30 transition-all text-sm font-bold uppercase"
          >
            Далее
          </button>
        )}
      </div>
    </div>
  )
}

export default FormStep

function Landing({ onStart }) {
  return (
    <div className="relative flex min-h-screen w-full flex-col bg-background-dark overflow-x-hidden">
      <header className="flex items-center justify-between border-b border-primary/20 px-6 py-4">
        <div className="flex items-center gap-4 text-primary">
          <div className="size-8 flex items-center justify-center bg-primary/10 rounded-lg">
            <span className="material-symbols-outlined text-primary">neurology</span>
          </div>
          <div>
            <h2 className="text-slate-100 text-lg font-bold leading-tight tracking-tight uppercase">MDSA Bio-Tech</h2>
            <p className="text-primary/60 text-[10px] font-bold tracking-[0.2em] uppercase">Integral Health Score 10.0</p>
          </div>
        </div>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center p-8 relative">
        <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-20">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 size-[600px] border border-primary/30 rounded-full animate-pulse" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 size-[800px] border border-primary/10 rounded-full" />
        </div>

        <div className="relative z-10 text-center max-w-2xl">
          <h1 className="text-4xl md:text-5xl font-black text-slate-100 tracking-tighter mb-4">
            ОЦЕНКА РИСКОВ ЗДОРОВЬЯ
          </h1>
          <p className="text-primary text-sm tracking-[0.2em] font-bold uppercase mb-6">
            12 системных рисков · Биометрический анализ
          </p>
          <p className="text-slate-400 text-sm mb-10 leading-relaxed">
            Комплексная оценка по нервной системе, сердцу и сосудам, метаболизму, иммунитету, почкам, печени и другим системам.
            Персонализированные рекомендации на основе AI.
          </p>
          <button
            onClick={onStart}
            className="px-8 py-4 bg-primary/20 border border-primary/50 text-primary font-bold rounded-xl hover:bg-primary/30 transition-all uppercase tracking-widest text-sm"
          >
            <span className="flex items-center gap-2 justify-center">
              <span className="material-symbols-outlined">play_arrow</span>
              Начать оценку
            </span>
          </button>
        </div>
      </main>
    </div>
  )
}

export default Landing

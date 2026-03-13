import { useState, useRef } from 'react'
import { ocrRecognize } from './api'

function OcrUpload({ onAddToCalculation, factorNames }) {
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const inputRef = useRef(null)

  const handleFileChange = (e) => {
    const f = e.target.files?.[0]
    setFile(f)
    setResult(null)
    setError(null)
  }

  const handleRecognize = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await ocrRecognize(file)
      setResult(res)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleAddToCalculation = () => {
    if (result?.extracted && Object.keys(result.extracted).length > 0) {
      onAddToCalculation(result.extracted)
      setResult(null)
      setFile(null)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  const handleClose = () => {
    setResult(null)
    setError(null)
  }

  const isImage = file && /\.(png|jpg|jpeg)$/i.test(file.name)
  const isPdf = file && /\.pdf$/i.test(file.name)
  const canRecognize = file && (isImage || isPdf)

  return (
    <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 mb-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-slate-100 text-sm font-bold uppercase tracking-wider flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-lg">document_scanner</span>
          Загрузить бланк
        </h3>
      </div>
      <p className="text-slate-500 text-xs mb-3">Распознавание показателей с фото, скана или PDF (Yandex Vision)</p>
      <div className="flex flex-wrap gap-2 items-center">
        <input
          ref={inputRef}
          type="file"
          accept=".png,.jpg,.jpeg,.pdf"
          onChange={handleFileChange}
          className="hidden"
          id="ocr-file"
        />
        <label
          htmlFor="ocr-file"
          className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-300 text-xs cursor-pointer hover:bg-slate-700"
        >
          Выбрать файл
        </label>
        {file && <span className="text-slate-400 text-xs truncate max-w-[180px]">{file.name}</span>}
        <button
          onClick={handleRecognize}
          disabled={!canRecognize || loading}
          className="px-4 py-2 bg-primary/20 border border-primary/50 text-primary rounded-lg text-xs font-bold uppercase disabled:opacity-50 flex items-center gap-1"
        >
          {loading ? (
            <>Распознавание...</>
          ) : (
            <>
              <span className="material-symbols-outlined text-sm">search</span>
              Распознать
            </>
          )}
        </button>
      </div>
      {error && <p className="text-red-400 text-xs mt-2">{error}</p>}

      {result && (
        <div className="mt-4 p-4 rounded-lg bg-slate-950/50 border border-slate-700">
          <div className="flex justify-between items-center mb-2">
            <span className="text-primary text-xs font-bold uppercase">Результаты сканирования</span>
            <button onClick={handleClose} className="text-slate-500 hover:text-slate-300 text-xs">
              ✕
            </button>
          </div>
          <div className="space-y-2 max-h-[200px] overflow-y-auto text-xs">
            {result.raw_text && (
              <details className="text-slate-400">
                <summary className="cursor-pointer">Текст с бланка (OCR)</summary>
                <pre className="mt-1 p-2 bg-slate-900 rounded text-[10px] whitespace-pre-wrap max-h-24 overflow-y-auto">
                  {result.raw_text.slice(0, 500)}{result.raw_text.length > 500 ? '...' : ''}
                </pre>
              </details>
            )}
            {result.parsed?.length > 0 && (
              <div>
                <p className="text-slate-500 mb-1">Распознано: {result.parsed.map((p) => `${p.name} ${p.value} ${p.unit || ''}`).join(', ')}</p>
              </div>
            )}
            {result.extracted && Object.keys(result.extracted).length > 0 && (
              <div>
                <p className="text-primary/80 mb-1">Подставлено в модель: {Object.entries(result.extracted).map(([fid, v]) => `${factorNames?.[fid] || fid}=${v}`).join(', ')}</p>
                <button
                  onClick={handleAddToCalculation}
                  className="mt-2 px-3 py-1.5 bg-primary/30 border border-primary/50 text-primary rounded text-xs font-bold"
                >
                  Добавить в расчёт
                </button>
              </div>
            )}
            {result.extracted && Object.keys(result.extracted).length === 0 && result.parsed?.length > 0 && (
              <p className="text-amber-500/80 text-[10px]">Распознанные показатели не найдены в базе. Проверьте названия.</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default OcrUpload

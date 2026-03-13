const API_BASE = import.meta.env.VITE_API_URL || ''

export async function fetchKnowledge() {
  const r = await fetch(`${API_BASE}/api/knowledge`)
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function calculate(testAnswers, sex, age) {
  const r = await fetch(`${API_BASE}/api/calculate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      test_answers: testAnswers,
      sex: sex || null,
      age: age ?? null,
    }),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function fetchRecommendations(userInputs, groupScores, sex, age) {
  const r = await fetch(`${API_BASE}/api/recommendations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_inputs: userInputs,
      group_scores: groupScores,
      sex: sex || null,
      age: age ?? null,
    }),
  })
  return r.json()
}

export async function ocrRecognize(file) {
  const form = new FormData()
  form.append('file', file)
  const r = await fetch(`${API_BASE}/api/ocr/recognize`, {
    method: 'POST',
    body: form,
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    throw new Error(err.detail || err.error || 'Ошибка OCR')
  }
  return r.json()
}

export async function sendChatMessage(message, chatHistory, userInputs, groupScores, sex, age) {
  const r = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      chat_history: chatHistory,
      user_inputs: userInputs || {},
      group_scores: groupScores || {},
      sex: sex || null,
      age: age ?? null,
    }),
  })
  return r.json()
}

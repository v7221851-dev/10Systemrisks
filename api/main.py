"""
FastAPI backend для React-приложения оценки рисков.
"""
import os
from pathlib import Path

# Загрузка .env из корня проекта (рядом с api/)
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except ImportError:
        pass

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any

app = FastAPI(title="Health Risk API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Кэш knowledge
_knowledge_cache = None


def get_df():
    global _knowledge_cache
    if _knowledge_cache is not None:
        return _knowledge_cache
    try:
        from .engine import get_knowledge_df
        _knowledge_cache = get_knowledge_df()
        return _knowledge_cache
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Ошибка загрузки данных: {str(e)}")


class CalculateRequest(BaseModel):
    test_answers: Dict[str, Any]
    sex: Optional[str] = None
    age: Optional[int] = None


@app.get("/api/knowledge")
def api_knowledge():
    """Возвращает knowledge_db в формате для React."""
    df = get_df()
    risk_groups = sorted([
        g for g in df["Risk_Group"].unique()
        if g and str(g) != "nan" and g != "Oxidative"
    ])
    factors_by_group = {}
    for group in risk_groups:
        g_df = df[df["Risk_Group"] == group]
        factors = []
        for _, row in g_df.iterrows():
            u_type = str(row.get("unit_type", "")).strip()
            n_min = round(float(row.get("norm_min", 0)), 2)
            n_max = round(float(row.get("norm_max", 0)), 2)
            v_min = round(float(row.get("min_val", 0)), 2)
            v_max = round(float(row.get("max_val", 1)), 2)
            if n_min == n_max == 0 and v_max > v_min:
                start_val = round((v_min + v_max) / 2.0, 2)
            else:
                start_val = round((n_min + n_max) / 2.0, 2)
            start_val = round(max(v_min, min(v_max, start_val)), 2)
            factors.append({
                "factor_id": row["factor_id"],
                "factor_name": row["factor_name"],
                "unit_type": u_type,
                "unit_name": str(row.get("unit_name", "")),
                "min_val": v_min,
                "max_val": v_max,
                "norm_min": n_min,
                "norm_max": n_max,
                "start_val": start_val,
                "weight": float(row.get("Weight_Coefficient", 0)),
            })
        factors_by_group[group] = factors
    return {
        "risk_groups": risk_groups,
        "factors_by_group": factors_by_group,
        "descriptions": {},
    }


@app.post("/api/calculate")
def api_calculate(req: CalculateRequest):
    """Расчёт рисков по ответам пользователя."""
    df = get_df()
    try:
        from .engine import run_calculation
        result = run_calculation(df, req.test_answers, req.sex, req.age)
        return {
            "group_scores": result["group_scores"],
            "final_score": result["final_score"],
            "percent": result["percent"],
            "zone_name": result["zone_name"],
            "brief": result["brief"],
            "warning": result["warning"],
            "user_inputs": result.get("user_inputs", {}),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class RecommendationsRequest(BaseModel):
    user_inputs: Dict[str, float]
    group_scores: Dict[str, float]
    sex: Optional[str] = None
    age: Optional[int] = None


class ChatRequest(BaseModel):
    message: str
    chat_history: list = []
    user_inputs: Dict[str, float] = {}
    group_scores: Dict[str, float] = {}
    sex: Optional[str] = None
    age: Optional[int] = None


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    """Диалог с GigaChat."""
    df = get_df()
    try:
        from .gigachat import chat
        text, err = chat(req.message, req.chat_history, req.user_inputs, req.group_scores, df.to_dict("records"), req.sex, req.age)
        if err:
            return {"response": None, "error": err}
        return {"response": text, "error": None}
    except Exception as e:
        return {"response": None, "error": str(e)}


@app.post("/api/recommendations")
def api_recommendations(req: RecommendationsRequest):
    """Получение AI-рекомендаций от GigaChat."""
    df = get_df()
    df_records = df.to_dict("records")
    try:
        from .gigachat import get_recommendations
        text, err = get_recommendations(
            req.user_inputs, req.group_scores, df_records,
            req.sex, req.age
        )
        if err:
            return {"error": err, "recommendations": None}
        return {"recommendations": text, "error": None}
    except Exception as e:
        return {"error": str(e), "recommendations": None}


@app.post("/api/ocr/recognize")
async def api_ocr_recognize(file: UploadFile = File(...)):
    """Распознавание бланка (фото, скан, PDF) через Yandex Vision."""
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Файл пустой")
    content_type = (file.content_type or "").strip().lower()
    filename = (file.filename or "").lower()
    is_pdf = "pdf" in content_type or filename.endswith(".pdf")
    try:
        from ocr_vision import (
            yandex_vision_ocr,
            parse_lab_text,
            map_to_factors,
            pdf_to_all_images,
            pdf_get_page_count,
        )
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"OCR модуль недоступен: {e}")
    api_key = os.getenv("YANDEX_VISION_API_KEY", "").strip()
    iam_token = os.getenv("YANDEX_VISION_IAM_TOKEN", "").strip()
    folder_id = os.getenv("YANDEX_VISION_FOLDER_ID", "").strip() or ("b1gaq3t2uh4lfs56jtks" if iam_token else None)
    auth = api_key or iam_token
    if not auth:
        raise HTTPException(status_code=400, detail="Задайте YANDEX_VISION_API_KEY или YANDEX_VISION_IAM_TOKEN в .env")
    folder_for_request = folder_id if iam_token else None
    df = get_df()
    all_parsed = []
    all_extracted = {}
    combined_text = ""
    if is_pdf:
        page_count, err = pdf_get_page_count(raw_bytes)
        if err or not page_count:
            raise HTTPException(status_code=400, detail=err or "PDF пустой")
        images, img_err = pdf_to_all_images(raw_bytes)
        if img_err or not images:
            raise HTTPException(status_code=400, detail=img_err or "Ошибка конвертации PDF")
        texts = []
        for i, img_bytes in enumerate(images):
            raw_text, ocr_err = yandex_vision_ocr(img_bytes, api_key=api_key or None, iam_token=iam_token or None, folder_id=folder_for_request)
            if ocr_err:
                texts.append(f"=== Страница {i+1} ===\nОшибка: {ocr_err}")
            elif raw_text:
                texts.append(f"=== Страница {i+1} ===\n{raw_text}")
                parsed = parse_lab_text(raw_text)
                all_parsed.extend(parsed)
                page_ext = map_to_factors(parsed, df)
                all_extracted.update(page_ext)
        combined_text = "\n\n".join(texts)
    else:
        raw_text, ocr_err = yandex_vision_ocr(raw_bytes, api_key=api_key or None, iam_token=iam_token or None, folder_id=folder_for_request)
        if ocr_err:
            raise HTTPException(status_code=400, detail=ocr_err)
        combined_text = raw_text or ""
        all_parsed = parse_lab_text(combined_text)
        all_extracted = map_to_factors(all_parsed, df)
    return {
        "raw_text": combined_text,
        "parsed": [{"name": p.get("name"), "value": p.get("value"), "unit": p.get("unit")} for p in all_parsed],
        "extracted": all_extracted,
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


# --- Static files + SPA fallback (для деплоя на Render) ---
_DIST = Path(__file__).resolve().parent.parent / "biotech-results" / "dist"


@app.get("/{full_path:path}")
async def serve_static(full_path: str):
    """Раздача статики и index.html для SPA (деплой Render)."""
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    if not _DIST.exists():
        raise HTTPException(status_code=404, detail="Frontend not built")
    file_path = _DIST / full_path
    if file_path.is_file():
        return FileResponse(file_path)
    return FileResponse(_DIST / "index.html")

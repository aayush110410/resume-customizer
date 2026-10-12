import re
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from sse_starlette import EventSourceResponse

from app.api.deps import get_cache, get_kb, get_llm, get_settings, rate_limited
from app.api.errors import PARSE_STATUS, AppError
from app.cache import AsyncLRU
from app.config import Settings
from app.export.docx import render_letter_docx, render_resume_docx
from app.export.pdf import render_letter_pdf, render_resume_pdf
from app.export.txt import render_txt
from app.knowledge.models import Knowledge
from app.llm.client import LLM
from app.parsing.extract import ParseError, parse_resume
from app.schemas import Contact, ExportRequest, Region, TailorRequest
from app.services import as_sse
from app.services.analyze import analyze_stream
from app.services.tailor import tailor_stream

router = APIRouter(prefix="/api")
SECTIONS = ["summary", "skills", "experience", "projects", "education", "achievements"]
TONES = ["conservative", "balanced", "bold"]


@router.get("/meta")
def meta(request: Request, kb: Annotated[Knowledge, Depends(get_kb)]) -> dict:
    s: Settings = request.app.state.settings
    targets = request.app.state.targets
    models = [{"id": t.label, "role": role} for role, ts in targets.items() for t in ts]
    return {
        "regions": [{"key": k, "label": kb.regions[k].label} for k in ("india", "international")],
        "sections": SECTIONS,
        "tones": TONES,
        "models": models,
        "limits": {
            "max_upload_mb": s.max_upload_mb,
            "max_pages": s.max_pages,
            "jd_min_chars": s.jd_min_chars,
            "jd_max_chars": s.jd_max_chars,
        },
    }


@router.post("/analyze", dependencies=[Depends(rate_limited)])
async def analyze(
    file: Annotated[UploadFile, File()],
    jd: Annotated[str, Form()],
    llm: Annotated[LLM, Depends(get_llm)],
    kb: Annotated[Knowledge, Depends(get_kb)],
    settings: Annotated[Settings, Depends(get_settings)],
    cache: Annotated[AsyncLRU, Depends(get_cache)],
    region: Annotated[Region, Form()] = "india",
) -> EventSourceResponse:
    jd = jd.strip()
    if len(jd) < settings.jd_min_chars:
        raise AppError(
            "JD_TOO_SHORT", f"Paste the full job description (at least {settings.jd_min_chars} characters).", 422
        )
    if len(jd) > settings.jd_max_chars:
        raise AppError("JD_TOO_LONG", f"Job description exceeds {settings.jd_max_chars} characters.", 422)
    limit = settings.max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise AppError("FILE_TOO_LARGE", f"File exceeds {settings.max_upload_mb} MB.", 413)
    try:
        parsed = await run_in_threadpool(parse_resume, data, settings.max_pages)
    except ParseError as e:
        raise AppError(e.code, e.code.replace("_", " ").capitalize(), PARSE_STATUS.get(e.code, 422)) from e
    return EventSourceResponse(as_sse(analyze_stream(parsed, jd, region, llm, kb, cache)))


@router.post("/tailor", dependencies=[Depends(rate_limited)])
async def tailor(
    req: TailorRequest, llm: Annotated[LLM, Depends(get_llm)], kb: Annotated[Knowledge, Depends(get_kb)]
) -> EventSourceResponse:
    return EventSourceResponse(as_sse(tailor_stream(req, llm, kb)))


MEDIA = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain; charset=utf-8",
}


@router.post("/export")
async def export(req: ExportRequest, kb: Annotated[Knowledge, Depends(get_kb)]) -> Response:
    region = kb.regions[req.region]
    if req.kind == "resume":
        if req.resume is None:
            raise AppError("INVALID_EXPORT", "No resume to export.", 422)
        name, label = req.resume.contact.name, "Resume"
        render = {
            "pdf": lambda: render_resume_pdf(req.resume, region),
            "docx": lambda: render_resume_docx(req.resume, region),
            "txt": lambda: render_txt(req.resume).encode(),
        }[req.format]
    else:
        if not (req.cover_letter or "").strip():
            raise AppError("INVALID_EXPORT", "No cover letter to export.", 422)
        contact = req.contact or Contact(name="Candidate")
        name, label = contact.name, "Cover_Letter"
        render = {
            "pdf": lambda: render_letter_pdf(req.cover_letter, contact, region),
            "docx": lambda: render_letter_docx(req.cover_letter, contact),
            "txt": lambda: req.cover_letter.encode(),
        }[req.format]
    content = await run_in_threadpool(render)
    slug = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_") or "Candidate"
    headers = {"Content-Disposition": f'attachment; filename="{slug}_{label}.{req.format}"'}
    return Response(content, media_type=MEDIA[req.format], headers=headers)

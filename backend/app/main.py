import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.errors import install_error_handlers
from app.api.ratelimit import RateLimiter
from app.api.routes import router
from app.cache import AsyncLRU
from app.config import Settings, build_targets
from app.llm.client import LLMClient

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="Resume Customizer API")
    app.state.settings = settings
    app.state.targets = build_targets(settings)
    app.state.llm = LLMClient(app.state.targets, settings.llm_timeout_s)
    app.state.cache = AsyncLRU()
    app.state.limiter = RateLimiter(settings.rate_limit)
    app.state.export_limiter = RateLimiter(settings.export_rate_limit)
    max_body = settings.max_request_mb * 1024 * 1024
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip().rstrip("/") for o in settings.allowed_origins.split(",") if o.strip()],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )
    install_error_handlers(app)

    @app.middleware("http")
    async def limit_body(request: Request, call_next):
        size = request.headers.get("content-length")
        if size and size.isdigit() and int(size) > max_body:
            body = {"code": "REQUEST_TOO_LARGE", "message": "Request is too large.", "retryable": False}
            return JSONResponse({"error": body}, status_code=413)
        return await call_next(request)

    app.include_router(router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()

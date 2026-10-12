import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.allowed_origins.split(",") if o.strip()],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )
    install_error_handlers(app)
    app.include_router(router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()

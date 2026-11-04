from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.errors import register_error_handlers
from app.ratelimit import RateLimiter
from app.routers import auth, health, orders


def create_app() -> FastAPI:
    app = FastAPI(title="DME Intake API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.auth_limiter = RateLimiter(limit=10, window_s=60)
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(orders.router)
    return app


app = create_app()

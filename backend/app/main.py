from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import admin, auth, documents
from app.config import settings
from app.core.exceptions import (
    AppBaseException,
    AppValidationError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    RAGProcessingError,
)

_EXCEPTION_STATUS_MAP: dict[type[AppBaseException], int] = {
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    AuthorizationError: status.HTTP_403_FORBIDDEN,
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    AppValidationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    RAGProcessingError: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.rag.engine import RAGEngine
    await RAGEngine.initialize(settings)
    yield
    await RAGEngine.shutdown()


app = FastAPI(title="RAG Knowledge Platform", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppBaseException)
async def app_exception_handler(request: Request, exc: AppBaseException) -> JSONResponse:
    http_status = _EXCEPTION_STATUS_MAP.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
    return JSONResponse(status_code=http_status, content={"detail": str(exc)})


app.include_router(auth.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")


@app.get("/")
async def root() -> dict:
    return {"message": "RAG Knowledge Platform API"}


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

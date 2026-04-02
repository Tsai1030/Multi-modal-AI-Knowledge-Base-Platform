from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.exceptions import AuthorizationError, NotFoundError
from app.models.user import User
from app.rag.conversation_compactor import ConversationCompactor
from app.rag.engine import RAGEngine
from app.repositories.document_repository import DocumentRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.query import QueryRequest
from app.services.conversation_service import ConversationService
from app.services.rag_query_service import RAGQueryService

router = APIRouter(prefix="/query", tags=["query"])


def _get_rag_query_service(db: AsyncSession = Depends(get_db)) -> RAGQueryService:
    llm_adapter = RAGEngine.get_llm_adapter()
    compactor = ConversationCompactor(llm_adapter=llm_adapter)
    conversation_svc = ConversationService(
        session_repo=SessionRepository(db),
        message_repo=MessageRepository(db),
        compactor=compactor,
    )
    return RAGQueryService(
        rag_engine=RAGEngine.get_rag(),
        llm_adapter=llm_adapter,
        conversation_service=conversation_svc,
        document_repo=DocumentRepository(db),
    )


@router.post("/stream")
async def query_stream(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    rag_query_service: RAGQueryService = Depends(_get_rag_query_service),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """SSE streaming endpoint for RAG-augmented chat queries.

    Session existence and ownership are validated before the stream begins so that
    404/403 are returned as proper HTTP error responses, not SSE error events.
    """
    session_repo = SessionRepository(db)
    session = await session_repo.get_by_id(request.session_id)
    if session is None:
        raise NotFoundError(f"Session {request.session_id} not found")
    if session.user_id != current_user.id:
        raise AuthorizationError("Access denied to this session")

    async def event_generator():
        async for sse_data in rag_query_service.query_stream(
            session_id=request.session_id,
            question=request.question,
            mode=request.mode,
            user_id=current_user.id,
        ):
            yield f"data: {sse_data}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

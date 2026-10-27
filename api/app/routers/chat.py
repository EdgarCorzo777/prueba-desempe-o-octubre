from fastapi import APIRouter, Depends
from api.app.schemas.api_models import ChatRequest, ChatResponse
from api.app.auth.dependencies import require_role
from api.app.services.chat_service import answer_user_query_grounded_in_gold

router = APIRouter(prefix="/api/chat", tags=["AI Conversational Assistant"])

@router.post("", response_model=ChatResponse)
def chat_with_seismic_data(
    req: ChatRequest,
    user: dict = Depends(require_role("viewer"))
):
    """
    Answers natural language questions about seismic activity.
    Connects EXCLUSIVELY to Gold data (curated.events).
    Mitigates hallucinations by calculating figures with code/SQL prior to LLM drafting.
    """
    from api.app.services.chat_service import answer_user_query_grounded_in_gold
    result = answer_user_query_grounded_in_gold(req.question)
    return ChatResponse(
        question=result["question"],
        answer=result["answer"],
        data_points=result["data_points"],
        period_consulted=result["period_consulted"],
        ai_model=result["ai_model"],
        latency_ms=result["latency_ms"],
        is_fallback=result["is_fallback"]
    )

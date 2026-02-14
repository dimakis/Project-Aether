"""OpenAI-compatible API endpoint definitions."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from src.api.rate_limit import limiter
from src.api.routes.openai_compat.handlers import _create_chat_completion, _stream_chat_completion
from src.api.routes.openai_compat.schemas import (
    ChatCompletionRequest,
    FeedbackRequest,
    ModelInfo,
    ModelsResponse,
)

router = APIRouter(tags=["OpenAI Compatible"])


@router.get("/models")
async def list_models() -> ModelsResponse:
    """List available LLM models.

    Dynamically discovers available models from:
    - Ollama (local models - if running)
    - Configured provider (openrouter, openai, google)

    Results are cached for 5 minutes.
    All models power the Architect agent with Home Assistant tools.
    """
    from src.api.services.model_discovery import get_model_discovery
    from src.llm_pricing import get_model_pricing

    discovery = get_model_discovery()
    models = await discovery.discover_all()

    data: list[ModelInfo] = []
    for model in models:
        pricing = get_model_pricing(model.id)
        data.append(
            ModelInfo(
                id=model.id,
                owned_by=model.provider,
                input_cost_per_1m=pricing["input_per_1m"] if pricing else None,
                output_cost_per_1m=pricing["output_per_1m"] if pricing else None,
            )
        )

    return ModelsResponse(data=data)


@router.post("/feedback")
async def submit_feedback(body: FeedbackRequest) -> dict[str, str]:
    """Submit thumbs up/down feedback for a chat response.

    Logs user sentiment against the MLflow trace for model evaluation.
    """
    import mlflow

    if body.sentiment not in ("positive", "negative"):
        raise HTTPException(
            status_code=400,
            detail="sentiment must be 'positive' or 'negative'",
        )

    try:
        from mlflow.entities import AssessmentSource, AssessmentSourceType

        mlflow.log_feedback(
            trace_id=body.trace_id,
            name="user_sentiment",
            value=body.sentiment,
            source=AssessmentSource(
                source_type=AssessmentSourceType.HUMAN,
                source_id="aether-ui",
            ),
        )
    except Exception:
        # mlflow.log_feedback may not be available in older MLflow versions.
        # Fall back to updating the trace tags directly.
        try:
            client = mlflow.MlflowClient()
            client.set_trace_tag(body.trace_id, "user_sentiment", body.sentiment)
        except Exception as e:
            from src.api.utils import sanitize_error

            raise HTTPException(
                status_code=500,
                detail=sanitize_error(e, context="Log feedback"),
            ) from e

    return {"status": "ok"}


@router.post("/chat/completions", response_model=None)
@limiter.limit("10/minute")
async def create_chat_completion(
    request: Request,
    body: ChatCompletionRequest,
) -> StreamingResponse | dict[str, Any]:
    """Create a chat completion.

    OpenAI-compatible endpoint for chat completions.
    Supports both streaming and non-streaming modes.

    Rate limited to 10/minute (LLM-backed).
    """
    if body.stream:
        return StreamingResponse(
            _stream_chat_completion(body),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return await _create_chat_completion(body)  # type: ignore[return-value]

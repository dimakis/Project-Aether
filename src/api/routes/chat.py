"""Chat API routes for conversational automation design.

User Story 2: Conversational Design with Architect Agent.
"""

from typing import AsyncGenerator
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationCreate,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    ErrorResponse,
    MessageCreate,
    MessageResponse,
)
from src.dal import ConversationRepository, MessageRepository, ProposalRepository
from src.storage import get_session
from src.storage.entities import Agent, ConversationStatus

router = APIRouter(prefix="/conversations", tags=["Conversations"])


async def get_or_create_architect_agent(session: AsyncSession) -> Agent:
    """Get or create the Architect agent record.

    Args:
        session: Database session

    Returns:
        Architect Agent record
    """
    from sqlalchemy import select

    result = await session.execute(
        select(Agent).where(Agent.name == "Architect")
    )
    agent = result.scalar_one_or_none()

    if not agent:
        agent = Agent(
            id=str(uuid4()),
            name="Architect",
            description="Conversational automation design agent",
            agent_type="architect",
            is_active=True,
        )
        session.add(agent)
        await session.flush()

    return agent


@router.post(
    "",
    response_model=ConversationDetailResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Start a new conversation",
    description="Create a new conversation and send the initial message.",
)
async def create_conversation(
    request: ConversationCreate,
) -> ConversationDetailResponse:
    """Start a new conversation with the Architect agent."""
    async with get_session() as session:
        # Get or create Architect agent
        agent = await get_or_create_architect_agent(session)

        # Create conversation
        conv_repo = ConversationRepository(session)
        conversation = await conv_repo.create(
            agent_id=agent.id,
            title=request.title,
            context=request.context,
        )

        # Create initial user message
        msg_repo = MessageRepository(session)
        user_message = await msg_repo.create(
            conversation_id=conversation.id,
            role="user",
            content=request.initial_message,
        )

        # Process with Architect agent
        from src.agents import ArchitectWorkflow

        workflow = ArchitectWorkflow()
        state = await workflow.start_conversation(
            user_message=request.initial_message,
            session=session,
        )

        # Get assistant response from state
        assistant_content = ""
        if state.messages:
            for msg in reversed(state.messages):
                if hasattr(msg, "content") and msg.type == "ai":
                    assistant_content = msg.content
                    break

        # Save assistant message
        if assistant_content:
            assistant_message = await msg_repo.create(
                conversation_id=conversation.id,
                role="assistant",
                content=assistant_content,
            )

        # Update conversation if proposal created
        proposal_id = None
        if state.pending_approvals:
            proposal_id = state.pending_approvals[0].id
            await conv_repo.update_status(
                conversation.id,
                ConversationStatus.ACTIVE,
            )

        await session.commit()

        # Refresh to get updated data
        conversation = await conv_repo.get_by_id(conversation.id)

        return ConversationDetailResponse(
            id=conversation.id,
            agent_id=conversation.agent_id,
            user_id=conversation.user_id,
            title=conversation.title,
            status=conversation.status.value,
            context=conversation.context,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=[
                MessageResponse(
                    id=m.id,
                    conversation_id=m.conversation_id,
                    role=m.role,
                    content=m.content,
                    tool_calls=m.tool_calls,
                    tool_results=m.tool_results,
                    tokens_used=m.tokens_used,
                    latency_ms=m.latency_ms,
                    created_at=m.created_at,
                )
                for m in conversation.messages
            ],
            pending_approvals=[proposal_id] if proposal_id else [],
        )


@router.get(
    "",
    response_model=ConversationListResponse,
    summary="List conversations",
    description="List all conversations for the current user.",
)
async def list_conversations(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ConversationListResponse:
    """List conversations."""
    async with get_session() as session:
        conv_repo = ConversationRepository(session)

        # Parse status if provided
        status_filter = None
        if status:
            try:
                status_filter = ConversationStatus(status)
            except ValueError:
                pass

        conversations = await conv_repo.list_by_user(
            user_id="default_user",
            status=status_filter,
            limit=limit,
            offset=offset,
        )
        total = await conv_repo.count(user_id="default_user", status=status_filter)

        return ConversationListResponse(
            items=[
                ConversationResponse(
                    id=c.id,
                    agent_id=c.agent_id,
                    user_id=c.user_id,
                    title=c.title,
                    status=c.status.value,
                    context=c.context,
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                )
                for c in conversations
            ],
            total=total,
            limit=limit,
            offset=offset,
        )


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get conversation details",
    description="Get a conversation with all its messages.",
)
async def get_conversation(conversation_id: str) -> ConversationDetailResponse:
    """Get conversation by ID."""
    async with get_session() as session:
        conv_repo = ConversationRepository(session)
        conversation = await conv_repo.get_by_id(
            conversation_id,
            include_messages=True,
            include_proposals=True,
        )

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        pending_ids = [p.id for p in conversation.proposals if p.status.value == "proposed"]

        return ConversationDetailResponse(
            id=conversation.id,
            agent_id=conversation.agent_id,
            user_id=conversation.user_id,
            title=conversation.title,
            status=conversation.status.value,
            context=conversation.context,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=[
                MessageResponse(
                    id=m.id,
                    conversation_id=m.conversation_id,
                    role=m.role,
                    content=m.content,
                    tool_calls=m.tool_calls,
                    tool_results=m.tool_results,
                    tokens_used=m.tokens_used,
                    latency_ms=m.latency_ms,
                    created_at=m.created_at,
                )
                for m in conversation.messages
            ],
            pending_approvals=pending_ids,
        )


@router.post(
    "/{conversation_id}/messages",
    response_model=ChatResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Send a message",
    description="Send a message in an existing conversation.",
)
async def send_message(
    conversation_id: str,
    request: ChatRequest,
) -> ChatResponse:
    """Send a message to continue a conversation."""
    async with get_session() as session:
        conv_repo = ConversationRepository(session)
        msg_repo = MessageRepository(session)

        # Get conversation
        conversation = await conv_repo.get_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Create user message
        user_message = await msg_repo.create(
            conversation_id=conversation_id,
            role="user",
            content=request.message,
        )

        # Update context if provided
        if request.context:
            await conv_repo.update_context(conversation_id, request.context)

        # Process with Architect
        from langchain_core.messages import HumanMessage

        from src.agents import ArchitectWorkflow
        from src.graph.state import ConversationState

        # Build state from conversation history
        messages_list = await msg_repo.list_by_conversation(conversation_id)
        state = ConversationState(
            conversation_id=conversation_id,
            messages=[
                HumanMessage(content=m.content) if m.role == "user"
                else type("AIMessage", (), {"content": m.content, "type": "ai"})()
                for m in messages_list
            ],
        )

        workflow = ArchitectWorkflow()
        state = await workflow.continue_conversation(
            state=state,
            user_message=request.message,
            session=session,
        )

        # Get assistant response
        assistant_content = ""
        if state.messages:
            for msg in reversed(state.messages):
                if hasattr(msg, "content") and getattr(msg, "type", None) == "ai":
                    assistant_content = msg.content
                    break

        # Save assistant message
        assistant_message = None
        if assistant_content:
            assistant_message = await msg_repo.create(
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_content,
            )

        # Check for proposals
        proposal_id = None
        has_proposal = False
        if state.pending_approvals:
            proposal_id = state.pending_approvals[0].id
            has_proposal = True

        await session.commit()

        return ChatResponse(
            conversation_id=conversation_id,
            message=MessageResponse(
                id=assistant_message.id if assistant_message else str(uuid4()),
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_content or "I'm processing your request...",
                tool_calls=None,
                tool_results=None,
                tokens_used=None,
                latency_ms=None,
                created_at=assistant_message.created_at if assistant_message else None,
            ),
            has_proposal=has_proposal,
            proposal_id=proposal_id,
            status=state.status.value,
        )


@router.websocket("/{conversation_id}/stream")
async def stream_conversation(
    websocket: WebSocket,
    conversation_id: str,
):
    """WebSocket endpoint for streaming conversation responses.

    T087: WebSocket endpoint for streaming at /conversations/{id}/stream
    """
    await websocket.accept()

    try:
        async with get_session() as session:
            conv_repo = ConversationRepository(session)
            conversation = await conv_repo.get_by_id(conversation_id)

            if not conversation:
                await websocket.send_json({"error": "Conversation not found"})
                await websocket.close()
                return

            while True:
                # Receive message from client
                data = await websocket.receive_json()
                message = data.get("message", "")

                if not message:
                    continue

                # Send acknowledgment
                await websocket.send_json({
                    "type": "ack",
                    "content": "Processing...",
                })

                # Process message (simplified - full streaming would use async generator)
                from src.agents import ArchitectWorkflow
                from src.graph.state import ConversationState
                from langchain_core.messages import HumanMessage

                msg_repo = MessageRepository(session)
                messages_list = await msg_repo.list_by_conversation(conversation_id)

                state = ConversationState(
                    conversation_id=conversation_id,
                    messages=[
                        HumanMessage(content=m.content) if m.role == "user"
                        else type("AIMessage", (), {"content": m.content, "type": "ai"})()
                        for m in messages_list
                    ],
                )

                workflow = ArchitectWorkflow()
                state = await workflow.continue_conversation(
                    state=state,
                    user_message=message,
                    session=session,
                )

                # Get response
                assistant_content = ""
                if state.messages:
                    for msg in reversed(state.messages):
                        if hasattr(msg, "content") and getattr(msg, "type", None) == "ai":
                            assistant_content = msg.content
                            break

                # Send response in chunks (simulated streaming)
                chunk_size = 50
                for i in range(0, len(assistant_content), chunk_size):
                    chunk = assistant_content[i:i + chunk_size]
                    await websocket.send_json({
                        "type": "text",
                        "content": chunk,
                    })

                # Send completion
                await websocket.send_json({
                    "type": "done",
                    "has_proposal": bool(state.pending_approvals),
                    "proposal_id": state.pending_approvals[0].id if state.pending_approvals else None,
                })

                await session.commit()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"error": str(e)})
        await websocket.close()


@router.delete(
    "/{conversation_id}",
    response_model=dict,
    responses={404: {"model": ErrorResponse}},
    summary="Delete conversation",
    description="Delete a conversation and all its messages.",
)
async def delete_conversation(conversation_id: str) -> dict:
    """Delete a conversation."""
    async with get_session() as session:
        conv_repo = ConversationRepository(session)
        deleted = await conv_repo.delete(conversation_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Conversation not found")

        await session.commit()
        return {"deleted": True, "conversation_id": conversation_id}

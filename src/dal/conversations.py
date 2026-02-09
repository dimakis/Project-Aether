"""Conversation and Message repository for CRUD operations.

User Story 2: Conversational Design with Architect Agent.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.storage.entities import (
    AutomationProposal,
    Conversation,
    ConversationStatus,
    Message,
    ProposalStatus,
)


class ConversationRepository:
    """Repository for Conversation CRUD operations.

    Manages conversation lifecycle and message history.
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def create(
        self,
        agent_id: str,
        user_id: str = "default_user",
        title: str | None = None,
        context: dict | None = None,
    ) -> Conversation:
        """Create a new conversation.

        Args:
            agent_id: ID of the agent handling this conversation
            user_id: User identifier
            title: Optional conversation title
            context: Optional conversation context

        Returns:
            Created Conversation
        """
        conversation = Conversation(
            id=str(uuid4()),
            agent_id=agent_id,
            user_id=user_id,
            title=title,
            status=ConversationStatus.ACTIVE,
            context=context or {},
        )
        self.session.add(conversation)
        await self.session.flush()
        return conversation

    async def get_by_id(
        self,
        conversation_id: str,
        include_messages: bool = True,
        include_proposals: bool = False,
    ) -> Conversation | None:
        """Get conversation by ID.

        Args:
            conversation_id: Conversation UUID
            include_messages: Load messages eagerly
            include_proposals: Load proposals eagerly

        Returns:
            Conversation or None
        """
        query = select(Conversation).where(Conversation.id == conversation_id)

        if include_messages:
            query = query.options(selectinload(Conversation.messages))
        if include_proposals:
            query = query.options(selectinload(Conversation.proposals))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: str,
        status: ConversationStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Conversation]:
        """List conversations for a user.

        Args:
            user_id: User identifier
            status: Optional status filter
            limit: Max results
            offset: Skip results

        Returns:
            List of conversations
        """
        query = select(Conversation).where(Conversation.user_id == user_id)

        if status:
            query = query.where(Conversation.status == status)

        query = query.order_by(Conversation.updated_at.desc()).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_active(self, limit: int = 50) -> list[Conversation]:
        """List all active conversations.

        Args:
            limit: Max results

        Returns:
            List of active conversations
        """
        query = (
            select(Conversation)
            .where(Conversation.status == ConversationStatus.ACTIVE)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_status(
        self,
        conversation_id: str,
        status: ConversationStatus,
    ) -> Conversation | None:
        """Update conversation status.

        Args:
            conversation_id: Conversation UUID
            status: New status

        Returns:
            Updated conversation or None
        """
        conversation = await self.get_by_id(conversation_id, include_messages=False)
        if conversation:
            conversation.status = status
            await self.session.flush()
        return conversation

    async def update_context(
        self,
        conversation_id: str,
        context: dict,
        merge: bool = True,
    ) -> Conversation | None:
        """Update conversation context.

        Args:
            conversation_id: Conversation UUID
            context: New context data
            merge: If True, merge with existing context; if False, replace

        Returns:
            Updated conversation or None
        """
        conversation = await self.get_by_id(conversation_id, include_messages=False)
        if conversation:
            if merge and conversation.context:
                conversation.context = {**conversation.context, **context}
            else:
                conversation.context = context
            await self.session.flush()
        return conversation

    async def update_title(
        self,
        conversation_id: str,
        title: str,
    ) -> Conversation | None:
        """Update conversation title.

        Args:
            conversation_id: Conversation UUID
            title: New title

        Returns:
            Updated conversation or None
        """
        conversation = await self.get_by_id(conversation_id, include_messages=False)
        if conversation:
            conversation.title = title
            await self.session.flush()
        return conversation

    async def count(
        self,
        user_id: str | None = None,
        status: ConversationStatus | None = None,
    ) -> int:
        """Count conversations.

        Args:
            user_id: Optional user filter
            status: Optional status filter

        Returns:
            Count of conversations
        """
        query = select(func.count(Conversation.id))

        if user_id:
            query = query.where(Conversation.user_id == user_id)
        if status:
            query = query.where(Conversation.status == status)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def delete(self, conversation_id: str) -> bool:
        """Delete a conversation and its messages.

        Args:
            conversation_id: Conversation UUID

        Returns:
            True if deleted, False if not found
        """
        conversation = await self.get_by_id(conversation_id, include_messages=False)
        if conversation:
            await self.session.delete(conversation)
            await self.session.flush()
            return True
        return False


class MessageRepository:
    """Repository for Message CRUD operations.

    Manages messages within conversations.
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def create(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_calls: dict | None = None,
        tool_results: dict | None = None,
        tokens_used: int | None = None,
        latency_ms: int | None = None,
        mlflow_span_id: str | None = None,
        metadata: dict | None = None,
    ) -> Message:
        """Create a new message.

        Args:
            conversation_id: Parent conversation ID
            role: Message role (user, assistant, system)
            content: Message content
            tool_calls: Optional tool calls made
            tool_results: Optional tool call results
            tokens_used: Optional token count
            latency_ms: Optional latency
            mlflow_span_id: Optional MLflow span ID
            metadata: Optional metadata

        Returns:
            Created Message
        """
        message = Message(
            id=str(uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_results=tool_results,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            mlflow_span_id=mlflow_span_id,
            metadata_=metadata,
        )
        self.session.add(message)
        await self.session.flush()
        return message

    async def get_by_id(self, message_id: str) -> Message | None:
        """Get message by ID.

        Args:
            message_id: Message UUID

        Returns:
            Message or None
        """
        result = await self.session.execute(select(Message).where(Message.id == message_id))
        return result.scalar_one_or_none()

    async def list_by_conversation(
        self,
        conversation_id: str,
        limit: int | None = None,
        since: datetime | None = None,
    ) -> list[Message]:
        """List messages in a conversation.

        Args:
            conversation_id: Conversation UUID
            limit: Optional max results
            since: Optional timestamp filter (messages after this time)

        Returns:
            List of messages ordered by created_at
        """
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )

        if since:
            query = query.where(Message.created_at > since)
        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_last_n(
        self,
        conversation_id: str,
        n: int = 10,
    ) -> list[Message]:
        """Get last N messages from a conversation.

        Args:
            conversation_id: Conversation UUID
            n: Number of messages to retrieve

        Returns:
            List of messages (oldest first)
        """
        # Get IDs of last N messages
        subquery = (
            select(Message.id)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(n)
        ).subquery()

        # Get those messages in chronological order
        query = select(Message).where(Message.id.in_(select(subquery))).order_by(Message.created_at)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_conversation(self, conversation_id: str) -> int:
        """Count messages in a conversation.

        Args:
            conversation_id: Conversation UUID

        Returns:
            Message count
        """
        result = await self.session.execute(
            select(func.count(Message.id)).where(Message.conversation_id == conversation_id)
        )
        return result.scalar() or 0

    async def get_token_usage(self, conversation_id: str) -> int:
        """Get total token usage for a conversation.

        Args:
            conversation_id: Conversation UUID

        Returns:
            Total tokens used
        """
        result = await self.session.execute(
            select(func.sum(Message.tokens_used)).where(Message.conversation_id == conversation_id)
        )
        return result.scalar() or 0


class ProposalRepository:
    """Repository for AutomationProposal CRUD operations.

    Manages automation proposals and their lifecycle.
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def create(
        self,
        name: str,
        trigger: dict,
        actions: dict,
        conversation_id: str | None = None,
        description: str | None = None,
        conditions: dict | None = None,
        mode: str = "single",
        mlflow_run_id: str | None = None,
        proposal_type: str = "automation",
        service_call: dict | None = None,
    ) -> AutomationProposal:
        """Create a new automation proposal.

        Args:
            name: Automation name
            trigger: HA trigger config
            actions: HA action config
            conversation_id: Optional source conversation
            description: Optional description
            conditions: Optional conditions
            mode: Execution mode
            mlflow_run_id: Optional MLflow tracking ID
            proposal_type: Type of proposal (automation, entity_command, script, scene)
            service_call: Service call details for entity_command type

        Returns:
            Created AutomationProposal
        """
        from src.storage.entities.automation_proposal import ProposalType

        # Resolve proposal type to string value
        if isinstance(proposal_type, ProposalType):
            ptype_str = proposal_type.value
        else:
            try:
                ptype_str = ProposalType(proposal_type).value
            except ValueError:
                ptype_str = ProposalType.AUTOMATION.value

        proposal = AutomationProposal(
            id=str(uuid4()),
            proposal_type=ptype_str,
            conversation_id=conversation_id,
            name=name,
            description=description,
            trigger=trigger,
            conditions=conditions,
            actions=actions,
            mode=mode,
            service_call=service_call,
            status=ProposalStatus.DRAFT,
            mlflow_run_id=mlflow_run_id,
        )
        self.session.add(proposal)
        await self.session.flush()
        return proposal

    async def get_by_id(self, proposal_id: str) -> AutomationProposal | None:
        """Get proposal by ID.

        Args:
            proposal_id: Proposal UUID

        Returns:
            AutomationProposal or None
        """
        result = await self.session.execute(
            select(AutomationProposal).where(AutomationProposal.id == proposal_id)
        )
        return result.scalar_one_or_none()

    async def list_by_status(
        self,
        status: ProposalStatus,
        limit: int = 50,
    ) -> list[AutomationProposal]:
        """List proposals by status.

        Args:
            status: Status filter
            limit: Max results

        Returns:
            List of proposals
        """
        query = (
            select(AutomationProposal)
            .where(AutomationProposal.status == status)
            .order_by(AutomationProposal.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_by_conversation(
        self,
        conversation_id: str,
    ) -> list[AutomationProposal]:
        """List proposals for a conversation.

        Args:
            conversation_id: Conversation UUID

        Returns:
            List of proposals
        """
        query = (
            select(AutomationProposal)
            .where(AutomationProposal.conversation_id == conversation_id)
            .order_by(AutomationProposal.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_pending_approval(self, limit: int = 50) -> list[AutomationProposal]:
        """List proposals pending approval.

        Args:
            limit: Max results

        Returns:
            List of proposals in PROPOSED status
        """
        return await self.list_by_status(ProposalStatus.PROPOSED, limit)

    async def list_deployed(self, limit: int = 100) -> list[AutomationProposal]:
        """List deployed proposals.

        Args:
            limit: Max results

        Returns:
            List of proposals in DEPLOYED status
        """
        return await self.list_by_status(ProposalStatus.DEPLOYED, limit)

    async def propose(self, proposal_id: str) -> AutomationProposal | None:
        """Submit proposal for approval.

        Args:
            proposal_id: Proposal UUID

        Returns:
            Updated proposal or None
        """
        proposal = await self.get_by_id(proposal_id)
        if proposal:
            proposal.propose()
            await self.session.flush()
        return proposal

    async def approve(
        self,
        proposal_id: str,
        approved_by: str,
    ) -> AutomationProposal | None:
        """Approve a proposal.

        Args:
            proposal_id: Proposal UUID
            approved_by: Who is approving

        Returns:
            Updated proposal or None
        """
        proposal = await self.get_by_id(proposal_id)
        if proposal:
            proposal.approve(approved_by)
            await self.session.flush()
        return proposal

    async def reject(
        self,
        proposal_id: str,
        reason: str,
    ) -> AutomationProposal | None:
        """Reject a proposal.

        Args:
            proposal_id: Proposal UUID
            reason: Rejection reason

        Returns:
            Updated proposal or None
        """
        proposal = await self.get_by_id(proposal_id)
        if proposal:
            proposal.reject(reason)
            await self.session.flush()
        return proposal

    async def deploy(
        self,
        proposal_id: str,
        ha_automation_id: str,
    ) -> AutomationProposal | None:
        """Mark proposal as deployed.

        Args:
            proposal_id: Proposal UUID
            ha_automation_id: HA automation ID

        Returns:
            Updated proposal or None
        """
        proposal = await self.get_by_id(proposal_id)
        if proposal:
            proposal.deploy(ha_automation_id)
            await self.session.flush()
        return proposal

    async def rollback(self, proposal_id: str) -> AutomationProposal | None:
        """Rollback a deployed proposal.

        Args:
            proposal_id: Proposal UUID

        Returns:
            Updated proposal or None
        """
        proposal = await self.get_by_id(proposal_id)
        if proposal:
            proposal.rollback()
            await self.session.flush()
        return proposal

    async def delete(self, proposal_id: str) -> bool:
        """Delete a proposal.

        Args:
            proposal_id: Proposal UUID

        Returns:
            True if deleted, False if not found
        """
        proposal = await self.get_by_id(proposal_id)
        if proposal:
            await self.session.delete(proposal)
            await self.session.flush()
            return True
        return False

    async def count(self, status: ProposalStatus | None = None) -> int:
        """Count proposals.

        Args:
            status: Optional status filter

        Returns:
            Count of proposals
        """
        query = select(func.count(AutomationProposal.id))

        if status:
            query = query.where(AutomationProposal.status == status)

        result = await self.session.execute(query)
        return result.scalar() or 0

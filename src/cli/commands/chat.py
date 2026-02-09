"""Chat commands."""

import asyncio
from typing import Annotated

import typer
from langchain_core.messages import AIMessage, HumanMessage
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from src.cli.utils import console


def chat(
    message: Annotated[
        str | None,
        typer.Argument(help="Initial message (or leave empty for interactive mode)"),
    ] = None,
    conversation_id: Annotated[
        str | None,
        typer.Option("--continue", "-c", help="Continue an existing conversation"),
    ] = None,
) -> None:
    """Interactive chat with the Architect agent.

    Start a conversation to design automations. The Architect will help
    translate your requirements into Home Assistant automations.

    Examples:
        aether chat "Turn on lights when I get home"
        aether chat --continue <conversation-id>
        aether chat  # Interactive mode
    """
    asyncio.run(_chat_interactive(message, conversation_id))


async def _chat_interactive(
    initial_message: str | None,
    conversation_id: str | None,
) -> None:
    """Run interactive chat session."""
    from src.agents import ArchitectWorkflow
    from src.dal import ConversationRepository, MessageRepository
    from src.graph.state import ConversationState
    from src.storage import get_session
    from src.tracing import get_tracing_status, init_mlflow
    from src.tracing.context import session_context, set_session_id

    # Initialize MLflow tracing (enables autolog for OpenAI)
    init_mlflow()
    trace_status = get_tracing_status()
    console.print(
        "[dim]MLflow tracking: {uri} | experiment: {exp} | traces: {traces}[/dim]\n".format(
            uri=trace_status["tracking_uri"],
            exp=trace_status["experiment_name"],
            traces="on" if trace_status["traces_enabled"] else "off",
        )
    )

    # Use conversation_id as session ID if continuing, otherwise create new
    # This ensures all traces for a conversation are grouped together
    with session_context(session_id=conversation_id):
        console.print(
            Panel(
                "[bold blue]Architect Chat[/bold blue]\n\n"
                "Chat with the Architect to design automations.\n"
                "Type [cyan]'exit'[/cyan] or [cyan]'quit'[/cyan] to end.\n"
                "Type [cyan]'approve'[/cyan] to approve pending proposals.\n"
                "Type [cyan]'reject'[/cyan] to reject pending proposals.",
                title="🏗️ Architect Agent",
                border_style="blue",
            )
        )

        workflow = ArchitectWorkflow()
        state: ConversationState | None = None
        pending_proposal_id: str | None = None

        async with get_session() as session:
            conv_repo = ConversationRepository(session)
            MessageRepository(session)

            # Load existing conversation if specified
            if conversation_id:
                conv = await conv_repo.get_by_id(conversation_id, include_messages=True)
                if conv:
                    console.print(f"[dim]Continuing conversation: {conversation_id}[/dim]\n")
                    # Show previous messages
                    for msg in conv.messages:
                        if msg.role == "user":
                            console.print(f"[bold cyan]You:[/bold cyan] {msg.content}")
                        else:
                            console.print("[bold green]Architect:[/bold green]")
                            console.print(Markdown(msg.content))
                    console.print()

                    # Build state from history
                    state = ConversationState(
                        conversation_id=conversation_id,
                        messages=[
                            HumanMessage(content=m.content)
                            if m.role == "user"
                            else AIMessage(content=m.content)
                            for m in conv.messages
                        ],
                    )
                else:
                    console.print(f"[red]Conversation {conversation_id} not found.[/red]")
                    return

            # Process initial message if provided
            if initial_message:
                console.print(f"[bold cyan]You:[/bold cyan] {initial_message}\n")

                if state:
                    state = await workflow.continue_conversation(
                        state=state,
                        user_message=initial_message,
                        session=session,
                    )
                else:
                    state = await workflow.start_conversation(
                        user_message=initial_message,
                        session=session,
                    )
                    # Update session context to use conversation_id for trace correlation
                    set_session_id(state.conversation_id)

                # Show response
                if state.messages:
                    for msg in state.messages:
                        if hasattr(msg, "type") and msg.type == "ai":
                            console.print("[bold green]Architect:[/bold green]")
                            console.print(Markdown(msg.content))
                            break

                # Check for proposals
                if state.pending_approvals:
                    pending_proposal_id = state.pending_approvals[0].id
                    console.print(
                        f"\n[yellow]📋 Proposal pending approval: {pending_proposal_id}[/yellow]"
                    )
                    console.print("[dim]Type 'approve' or 'reject <reason>' to respond.[/dim]\n")

                await session.commit()

            # Interactive loop
            while True:
                try:
                    user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
                except (KeyboardInterrupt, EOFError):
                    break

                if not user_input:
                    continue

                # Handle special commands
                if user_input.lower() in ("exit", "quit", "q"):
                    console.print("[dim]Ending conversation.[/dim]")
                    break

                if user_input.lower() == "approve" and pending_proposal_id:
                    from src.dal import ProposalRepository

                    proposal_repo = ProposalRepository(session)
                    await proposal_repo.approve(pending_proposal_id, "cli_user")
                    await session.commit()
                    console.print(f"[green]✅ Proposal {pending_proposal_id} approved![/green]")
                    console.print("[dim]Use 'aether proposals deploy <id>' to deploy.[/dim]")
                    pending_proposal_id = None
                    continue

                if user_input.lower().startswith("reject") and pending_proposal_id:
                    reason = user_input[6:].strip() or "Rejected by user"
                    from src.dal import ProposalRepository

                    proposal_repo = ProposalRepository(session)
                    await proposal_repo.reject(pending_proposal_id, reason)
                    await session.commit()
                    console.print(f"[red]❌ Proposal rejected: {reason}[/red]")
                    pending_proposal_id = None
                    continue

                # Process message
                console.print()

                if state:
                    state = await workflow.continue_conversation(
                        state=state,
                        user_message=user_input,
                        session=session,
                    )
                else:
                    state = await workflow.start_conversation(
                        user_message=user_input,
                        session=session,
                    )
                    # Update session context to use conversation_id for trace correlation
                    set_session_id(state.conversation_id)

                # Show response
                if state.messages:
                    for msg in reversed(state.messages):
                        if hasattr(msg, "type") and msg.type == "ai":
                            console.print("[bold green]Architect:[/bold green]")
                            console.print(Markdown(msg.content))
                            break

                # Check for new proposals
                if state.pending_approvals:
                    pending_proposal_id = state.pending_approvals[0].id
                    console.print(
                        f"\n[yellow]📋 Proposal pending approval: {pending_proposal_id}[/yellow]"
                    )
                    console.print("[dim]Type 'approve' or 'reject <reason>' to respond.[/dim]")

                await session.commit()

        console.print("\n[dim]Chat session ended.[/dim]")

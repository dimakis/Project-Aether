"""Librarian agent for entity discovery.

The Librarian is responsible for discovering and cataloging
all Home Assistant entities, inferring relationships, and
maintaining the entity database.
"""

from datetime import datetime
from typing import Any

from src.dal import DiscoverySyncService
from src.graph.state import AgentRole, DiscoveryState, DiscoveryStatus, EntitySummary
from src.mcp import MCPClient
from src.settings import get_settings
from src.tracing import log_dict, log_metric, log_param, start_experiment_run


class LibrarianWorkflow:
    """Workflow implementation for the Librarian agent.

    Orchestrates the discovery process:
    1. Connect to Home Assistant via MCP
    2. Fetch all entities
    3. Infer areas and devices
    4. Sync to database
    5. Report gaps and statistics
    """

    def __init__(
        self,
        mcp_client: MCPClient | None = None,
    ):
        """Initialize the Librarian workflow.

        Args:
            mcp_client: Optional MCP client (creates one if not provided)
        """
        self._settings = get_settings()
        self._mcp = mcp_client

    @property
    def mcp(self) -> MCPClient:
        """Get MCP client, creating if needed."""
        if self._mcp is None:
            from src.mcp import get_mcp_client
            self._mcp = get_mcp_client()
        return self._mcp

    async def run_discovery(
        self,
        triggered_by: str = "manual",
        domain_filter: str | None = None,
    ) -> DiscoveryState:
        """Execute a full discovery run.

        Args:
            triggered_by: What triggered this discovery
            domain_filter: Optional domain to filter discovery

        Returns:
            Final discovery state with results
        """
        # Initialize state
        state = DiscoveryState(
            current_agent=AgentRole.LIBRARIAN,
            status=DiscoveryStatus.RUNNING,
        )

        with start_experiment_run(run_name="librarian_discovery") as run:
            if run:
                state.mlflow_run_id = run.info.run_id if hasattr(run, 'info') else None
            
            log_param("triggered_by", triggered_by)
            log_param("domain_filter", domain_filter or "all")

            try:
                # Execute discovery phases
                state = await self._fetch_entities(state, domain_filter)
                state = await self._sync_to_database(state, triggered_by)
                state = await self._report_results(state)

                state.status = DiscoveryStatus.COMPLETED

            except Exception as e:
                state.status = DiscoveryStatus.FAILED
                state.errors.append(str(e))
                log_param("error", str(e)[:500])
                raise

            finally:
                # Log final metrics
                log_metric("entities_found", float(len(state.entities_found)))
                log_metric("entities_added", float(state.entities_added))
                log_metric("entities_updated", float(state.entities_updated))
                log_metric("entities_removed", float(state.entities_removed))
                log_metric("devices_found", float(state.devices_found))
                log_metric("areas_found", float(state.areas_found))
                
                # Log discovery session as artifact
                self._log_discovery_session(state, triggered_by, domain_filter)

        return state

    def _log_discovery_session(
        self,
        state: DiscoveryState,
        triggered_by: str,
        domain_filter: str | None,
    ) -> None:
        """Log discovery session details as MLflow artifact.

        Args:
            state: Final discovery state
            triggered_by: What triggered discovery
            domain_filter: Domain filter used
        """
        import time

        # Build summary of discovered entities by domain
        domain_counts: dict[str, int] = {}
        for entity in state.entities_found:
            domain_counts[entity.domain] = domain_counts.get(entity.domain, 0) + 1

        log_dict(
            {
                "agent": "Librarian",
                "session_id": state.run_id,
                "triggered_by": triggered_by,
                "domain_filter": domain_filter,
                "timestamp": datetime.utcnow().isoformat(),
                "status": state.status.value,
                "summary": {
                    "entities_found": len(state.entities_found),
                    "entities_added": state.entities_added,
                    "entities_updated": state.entities_updated,
                    "entities_removed": state.entities_removed,
                    "devices_found": state.devices_found,
                    "areas_found": state.areas_found,
                    "domains_scanned": state.domains_scanned,
                    "domain_counts": domain_counts,
                },
                "errors": state.errors,
            },
            f"discovery/Librarian_{state.run_id}_{int(time.time())}.json",
        )

    async def _fetch_entities(
        self,
        state: DiscoveryState,
        domain_filter: str | None = None,
    ) -> DiscoveryState:
        """Fetch entities from Home Assistant via MCP.

        Args:
            state: Current discovery state
            domain_filter: Optional domain filter

        Returns:
            Updated state with fetched entities
        """
        from src.mcp import parse_entity_list

        # Fetch entities
        raw_entities = await self.mcp.list_entities(
            domain=domain_filter,
            detailed=True,
        )

        # Parse into EntitySummary objects
        entities = parse_entity_list(raw_entities)

        state.entities_found = [
            EntitySummary(
                entity_id=e.entity_id,
                domain=e.domain,
                name=e.name,
                state=e.state or "unknown",
                area_id=e.area_id,
                device_id=e.device_id,
            )
            for e in entities
        ]

        # Track domains scanned
        domains_found = set(e.domain for e in state.entities_found)
        state.domains_scanned = list(domains_found)

        return state

    async def _sync_to_database(
        self,
        state: DiscoveryState,
        triggered_by: str,
    ) -> DiscoveryState:
        """Sync fetched entities to the database.

        Args:
            state: Current discovery state with entities
            triggered_by: What triggered this discovery

        Returns:
            Updated state with sync statistics
        """
        from src.storage import get_session

        async with get_session() as session:
            sync_service = DiscoverySyncService(session, self.mcp)
            discovery = await sync_service.run_discovery(
                triggered_by=triggered_by,
                mlflow_run_id=state.mlflow_run_id,
            )

            # Update state with results
            state.entities_added = discovery.entities_added
            state.entities_updated = discovery.entities_updated
            state.entities_removed = discovery.entities_removed
            state.devices_found = discovery.devices_found
            state.areas_found = discovery.areas_found

        return state

    async def _report_results(self, state: DiscoveryState) -> DiscoveryState:
        """Generate discovery report.

        Args:
            state: Discovery state with results

        Returns:
            State unchanged (logging only)
        """
        # Just return the state - logging is handled elsewhere
        return state


async def run_librarian_discovery(
    triggered_by: str = "manual",
    domain_filter: str | None = None,
    mcp_client: MCPClient | None = None,
) -> DiscoveryState:
    """Convenience function to run Librarian discovery.

    Args:
        triggered_by: What triggered this discovery
        domain_filter: Optional domain filter
        mcp_client: Optional MCP client

    Returns:
        Final discovery state
    """
    workflow = LibrarianWorkflow(mcp_client=mcp_client)
    return await workflow.run_discovery(
        triggered_by=triggered_by,
        domain_filter=domain_filter,
    )

"""Automation deployment via MCP.

Handles generation of Home Assistant automation YAML and deployment
through available MCP tools and workarounds.

MCP Gap: Direct automation creation requires REST API or file access.
Workaround: Generate YAML for manual import, use automation.reload after.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from src.mcp import MCPClient, get_mcp_client
from src.settings import get_settings


class AutomationDeployer:
    """Handles automation deployment to Home Assistant.

    Provides YAML generation and deployment methods, handling
    known MCP gaps with appropriate workarounds.
    """

    def __init__(self, mcp_client: MCPClient | None = None):
        """Initialize deployer.

        Args:
            mcp_client: Optional MCP client
        """
        self._mcp = mcp_client
        self._settings = get_settings()

    @property
    def mcp(self) -> MCPClient:
        """Get MCP client."""
        if self._mcp is None:
            self._mcp = get_mcp_client()
        return self._mcp

    def generate_automation_yaml(
        self,
        name: str,
        trigger: dict | list,
        actions: dict | list,
        description: str | None = None,
        conditions: dict | list | None = None,
        mode: str = "single",
        metadata: dict | None = None,
    ) -> str:
        """Generate Home Assistant automation YAML.

        Args:
            name: Automation alias/name
            trigger: Trigger configuration(s)
            actions: Action configuration(s)
            description: Optional description
            conditions: Optional conditions
            mode: Execution mode (single, restart, queued, parallel)
            metadata: Optional metadata to include as comments

        Returns:
            Valid HA automation YAML string
        """
        # Ensure lists for triggers and actions
        triggers = trigger if isinstance(trigger, list) else [trigger]
        action_list = actions if isinstance(actions, list) else [actions]

        # Build automation dict
        automation: dict[str, Any] = {
            "alias": name,
            "trigger": triggers,
            "action": action_list,
            "mode": mode,
        }

        if description:
            automation["description"] = description

        if conditions:
            cond_list = conditions if isinstance(conditions, list) else [conditions]
            automation["condition"] = cond_list

        # Generate YAML
        yaml_content = yaml.dump(
            automation,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

        # Add metadata comments
        if metadata:
            header_lines = ["# Project Aether Automation"]
            for key, value in metadata.items():
                header_lines.append(f"# {key}: {value}")
            header_lines.append("# ---")
            header = "\n".join(header_lines) + "\n"
            yaml_content = header + yaml_content

        return yaml_content

    def generate_automation_id(self, name: str, proposal_id: str | None = None) -> str:
        """Generate a unique automation ID.

        Args:
            name: Automation name
            proposal_id: Optional proposal ID for uniqueness

        Returns:
            Valid HA automation ID
        """
        # Sanitize name for ID
        base_id = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")

        if proposal_id:
            # Use first 8 chars of proposal ID
            suffix = proposal_id.replace("-", "")[:8]
            return f"aether_{base_id}_{suffix}"

        # Use timestamp for uniqueness
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"aether_{base_id}_{timestamp}"

    def validate_automation_yaml(self, yaml_content: str) -> tuple[bool, list[str]]:
        """Validate automation YAML structure.

        Args:
            yaml_content: YAML string to validate

        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors: list[str] = []

        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            return False, [f"Invalid YAML: {e}"]

        if not isinstance(data, dict):
            return False, ["Automation must be a dictionary"]

        # Required fields
        if "trigger" not in data:
            errors.append("Missing required field: trigger")
        if "action" not in data:
            errors.append("Missing required field: action")

        # Validate trigger structure
        if "trigger" in data:
            triggers = data["trigger"]
            if not isinstance(triggers, list):
                triggers = [triggers]
            for i, t in enumerate(triggers):
                if not isinstance(t, dict):
                    errors.append(f"Trigger {i} must be a dictionary")
                elif "platform" not in t and "trigger" not in t:
                    # HA 2024.1+ allows either "platform" or "trigger" key
                    errors.append(f"Trigger {i} missing 'platform' or 'trigger' key")

        # Validate action structure
        if "action" in data:
            actions = data["action"]
            if not isinstance(actions, list):
                actions = [actions]
            for i, a in enumerate(actions):
                if not isinstance(a, dict):
                    errors.append(f"Action {i} must be a dictionary")

        # Validate mode
        valid_modes = {"single", "restart", "queued", "parallel"}
        if "mode" in data and data["mode"] not in valid_modes:
            errors.append(f"Invalid mode: {data['mode']}. Must be one of {valid_modes}")

        return len(errors) == 0, errors

    async def deploy_automation(
        self,
        yaml_content: str,
        automation_id: str,
        output_dir: Path | None = None,
    ) -> dict[str, Any]:
        """Deploy automation to Home Assistant.

        MCP Gap: No direct create_automation tool exists.
        This method uses available workarounds.

        Args:
            yaml_content: Valid automation YAML
            automation_id: Unique automation ID
            output_dir: Optional directory to save YAML file

        Returns:
            Deployment result dict
        """
        # Validate first
        is_valid, errors = self.validate_automation_yaml(yaml_content)
        if not is_valid:
            return {
                "success": False,
                "method": "validation_failed",
                "errors": errors,
            }

        result: dict[str, Any] = {
            "automation_id": automation_id,
            "yaml_content": yaml_content,
        }

        # Save to file if output_dir provided
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            yaml_file = output_dir / f"{automation_id}.yaml"
            yaml_file.write_text(yaml_content)
            result["yaml_file"] = str(yaml_file)

        # Attempt deployment via MCP
        # Note: This is the workaround path - direct creation not available
        try:
            # Option 1: Try to reload automations (assumes YAML was placed in HA config)
            await self.mcp.call_service(
                domain="automation",
                service="reload",
            )
            result["success"] = True
            result["method"] = "reload"
            result["note"] = (
                "Automation reload triggered. "
                "Ensure YAML is in HA automations.yaml or automations directory."
            )
        except Exception as e:
            # Reload failed - provide manual instructions
            result["success"] = False
            result["method"] = "manual"
            result["error"] = str(e)
            result["instructions"] = self._get_manual_instructions(automation_id)

        result["deployed_at"] = datetime.utcnow().isoformat()
        return result

    def _get_manual_instructions(self, automation_id: str) -> str:
        """Get manual deployment instructions.

        Args:
            automation_id: Automation ID

        Returns:
            Instructions string
        """
        return f"""To deploy this automation manually:

1. Copy the YAML content to your automations.yaml file, OR
2. Create a file at /config/automations/{automation_id}.yaml

3. In Home Assistant:
   - Go to Developer Tools > YAML
   - Click "RELOAD AUTOMATIONS"
   - Or call the automation.reload service

4. Verify the automation appears in Configuration > Automations

The automation will have the ID: automation.{automation_id}
"""

    async def enable_automation(self, entity_id: str) -> dict[str, Any]:
        """Enable an automation.

        Args:
            entity_id: Full entity ID (e.g., automation.my_automation)

        Returns:
            Result dict
        """
        await self.mcp.call_service(
            domain="automation",
            service="turn_on",
            data={"entity_id": entity_id},
        )
        return {"enabled": True, "entity_id": entity_id}

    async def disable_automation(self, entity_id: str) -> dict[str, Any]:
        """Disable an automation.

        Args:
            entity_id: Full entity ID

        Returns:
            Result dict
        """
        await self.mcp.call_service(
            domain="automation",
            service="turn_off",
            data={"entity_id": entity_id},
        )
        return {"disabled": True, "entity_id": entity_id}

    async def trigger_automation(self, entity_id: str) -> dict[str, Any]:
        """Manually trigger an automation.

        Args:
            entity_id: Full entity ID

        Returns:
            Result dict
        """
        await self.mcp.call_service(
            domain="automation",
            service="trigger",
            data={"entity_id": entity_id},
        )
        return {"triggered": True, "entity_id": entity_id}

    async def reload_automations(self) -> dict[str, Any]:
        """Reload all automations from YAML.

        Returns:
            Result dict
        """
        await self.mcp.call_service(
            domain="automation",
            service="reload",
        )
        return {"reloaded": True, "reloaded_at": datetime.utcnow().isoformat()}


# =============================================================================
# YAML GENERATION HELPERS
# =============================================================================


def build_state_trigger(
    entity_id: str,
    to_state: str | None = None,
    from_state: str | None = None,
    for_duration: str | None = None,
) -> dict[str, Any]:
    """Build a state change trigger.

    Args:
        entity_id: Entity to watch
        to_state: State to trigger on
        from_state: Previous state required
        for_duration: Duration in state before triggering

    Returns:
        Trigger dict
    """
    trigger: dict[str, Any] = {
        "platform": "state",
        "entity_id": entity_id,
    }
    if to_state is not None:
        trigger["to"] = to_state
    if from_state is not None:
        trigger["from"] = from_state
    if for_duration:
        trigger["for"] = for_duration
    return trigger


def build_time_trigger(at: str) -> dict[str, Any]:
    """Build a time trigger.

    Args:
        at: Time in HH:MM:SS or HH:MM format

    Returns:
        Trigger dict
    """
    return {
        "platform": "time",
        "at": at,
    }


def build_sun_trigger(
    event: str = "sunset",
    offset: str | None = None,
) -> dict[str, Any]:
    """Build a sun trigger.

    Args:
        event: "sunrise" or "sunset"
        offset: Optional offset like "-00:30:00"

    Returns:
        Trigger dict
    """
    trigger: dict[str, Any] = {
        "platform": "sun",
        "event": event,
    }
    if offset:
        trigger["offset"] = offset
    return trigger


def build_service_action(
    domain: str,
    service: str,
    target: dict | None = None,
    data: dict | None = None,
) -> dict[str, Any]:
    """Build a service call action.

    Args:
        domain: Service domain
        service: Service name
        target: Optional target (entity_id, device_id, area_id)
        data: Optional service data

    Returns:
        Action dict
    """
    action: dict[str, Any] = {
        "service": f"{domain}.{service}",
    }
    if target:
        action["target"] = target
    if data:
        action["data"] = data
    return action


def build_delay_action(delay: str) -> dict[str, Any]:
    """Build a delay action.

    Args:
        delay: Delay duration (e.g., "00:00:30" or "30")

    Returns:
        Action dict
    """
    return {"delay": delay}


def build_condition(
    condition_type: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Build a condition.

    Args:
        condition_type: Type of condition (state, time, sun, etc.)
        **kwargs: Condition-specific parameters

    Returns:
        Condition dict
    """
    return {"condition": condition_type, **kwargs}


# Exports
__all__ = [
    "AutomationDeployer",
    "build_state_trigger",
    "build_time_trigger",
    "build_sun_trigger",
    "build_service_action",
    "build_delay_action",
    "build_condition",
]

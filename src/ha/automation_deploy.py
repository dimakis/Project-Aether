"""Automation deployment via HA.

Handles generation of Home Assistant automation YAML and deployment
through available HA tools and workarounds.

HA Gap: Direct automation creation requires REST API or file access.
Workaround: Generate YAML for manual import, use automation.reload after.
"""

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from src.ha.client import HAClient, get_ha_client
from src.settings import get_settings


class AutomationDeployer:
    """Handles automation deployment to Home Assistant.

    Provides YAML generation and deployment methods, handling
    known HA gaps with appropriate workarounds.
    """

    def __init__(self, ha_client: HAClient | None = None):
        """Initialize deployer.

        Args:
            ha_client: Optional HA client
        """
        self._ha_client = ha_client
        self._settings = get_settings()

    @property
    def ha(self) -> HAClient:
        """Get HA client."""
        if self._ha_client is None:
            self._ha_client = get_ha_client()
        return self._ha_client

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
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        return f"aether_{base_id}_{timestamp}"

    def validate_automation_yaml(self, yaml_content: str) -> tuple[bool, list[str]]:
        """Validate automation YAML structure.

        Uses the schema validator (Feature 26) for structural validation
        of required keys, types, trigger/action structure, and mode enum.

        Args:
            yaml_content: YAML string to validate

        Returns:
            Tuple of (is_valid, list of errors)
        """
        from src.schema import validate_yaml

        result = validate_yaml(yaml_content, "ha.automation")
        errors = [f"{e.path}: {e.message}" if e.path else e.message for e in result.errors]
        return result.valid, errors

    async def deploy_automation(
        self,
        yaml_content: str,
        automation_id: str,
        output_dir: Path | None = None,
    ) -> dict[str, Any]:
        """Deploy automation to Home Assistant via REST API.

        Uses HA's /api/config/automation/config endpoint to create
        automations directly - no manual YAML placement required.

        Args:
            yaml_content: Valid automation YAML
            automation_id: Unique automation ID
            output_dir: Optional directory to save YAML file (backup)

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

        # Parse YAML to get config
        config = yaml.safe_load(yaml_content)

        result: dict[str, Any] = {
            "automation_id": automation_id,
            "yaml_content": yaml_content,
        }

        # Save to file if output_dir provided (as backup)
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            yaml_file = output_dir / f"{automation_id}.yaml"
            yaml_file.write_text(yaml_content)
            result["yaml_file"] = str(yaml_file)

        # Deploy via REST API (the real deal - no HA gap!)
        try:
            deploy_result = await self.ha.create_automation(
                automation_id=automation_id,
                alias=config.get("alias", automation_id),
                trigger=config.get("trigger", []),
                action=config.get("action", []),
                condition=config.get("condition"),
                description=config.get("description"),
                mode=config.get("mode", "single"),
            )

            if deploy_result.get("success"):
                result["success"] = True
                result["method"] = "rest_api"
                result["entity_id"] = deploy_result.get("entity_id")
                result["note"] = "Automation created via HA REST API. Active immediately."
            else:
                # REST API failed - fall back to manual instructions
                result["success"] = False
                result["method"] = "manual"
                result["error"] = deploy_result.get("error", "Unknown error")
                result["instructions"] = self._get_manual_instructions(automation_id)

        except Exception as e:
            # Total failure - provide manual instructions
            result["success"] = False
            result["method"] = "manual"
            result["error"] = str(e)
            result["instructions"] = self._get_manual_instructions(automation_id)

        result["deployed_at"] = datetime.now(UTC).isoformat()
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
        await self.ha.call_service(
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
        await self.ha.call_service(
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
        await self.ha.call_service(
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
        await self.ha.call_service(
            domain="automation",
            service="reload",
        )
        return {"reloaded": True, "reloaded_at": datetime.now(UTC).isoformat()}


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
    "build_condition",
    "build_delay_action",
    "build_service_action",
    "build_state_trigger",
    "build_sun_trigger",
    "build_time_trigger",
]

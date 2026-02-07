"""Dual synthesizer for DS team findings.

Provides two synthesis strategies:
1. ProgrammaticSynthesizer — deterministic, rule-based (default)
2. LLMSynthesizer — LLM-backed, for nuanced conflict resolution (on-demand)

Both produce an updated TeamAnalysis with consensus, conflicts, and
holistic_recommendations. The Architect receives the result and can
request the LLM synthesizer for a second opinion via the
request_synthesis_review tool.

Usage:
    from src.agents.synthesis import synthesize, SynthesisStrategy

    result = synthesize(team_analysis, strategy=SynthesisStrategy.PROGRAMMATIC)
"""

from __future__ import annotations

import json
import structlog
from collections import defaultdict
from enum import StrEnum
from typing import Any

from src.graph.state import (
    AutomationSuggestion,
    SpecialistFinding,
    TeamAnalysis,
)

logger = structlog.get_logger(__name__)


class SynthesisStrategy(StrEnum):
    """Available synthesis strategies."""

    PROGRAMMATIC = "programmatic"
    LLM = "llm"


# ---------------------------------------------------------------------------
# Programmatic Synthesizer
# ---------------------------------------------------------------------------


class ProgrammaticSynthesizer:
    """Deterministic, rule-based synthesizer.

    Algorithm:
    1. Group findings by entity (which entities appear across multiple specialists?)
    2. Identify conflicts (different specialists disagree on the same entity)
    3. Score by cross-specialist reinforcement (2+ specialists = higher rank)
    4. Merge automation suggestions
    5. Produce consensus narrative and ranked recommendations

    Strengths: Fast, zero cost, auditable, no failure points.
    Weaknesses: Cannot reason about nuance or resolve ambiguous conflicts.
    """

    def synthesize(self, analysis: TeamAnalysis) -> TeamAnalysis:
        """Synthesize findings into consensus and recommendations.

        Does NOT mutate the input. Returns a new TeamAnalysis.

        Args:
            analysis: TeamAnalysis with accumulated specialist findings.

        Returns:
            New TeamAnalysis with consensus, conflicts, and recommendations.
        """
        findings = analysis.findings

        if not findings:
            return analysis.model_copy(
                update={
                    "consensus": "No findings to synthesize.",
                    "conflicts": [],
                    "holistic_recommendations": [],
                    "synthesis_strategy": SynthesisStrategy.PROGRAMMATIC,
                }
            )

        # Step 1: Group findings by entity
        entity_findings: dict[str, list[SpecialistFinding]] = defaultdict(list)
        for f in findings:
            for entity in f.entities:
                entity_findings[entity].append(f)

        # Step 2: Identify conflicts (same entity, different specialists, opposing finding_types)
        conflicts = self._detect_conflicts(entity_findings)

        # Step 3: Score and rank findings
        ranked = self._rank_findings(findings, entity_findings)

        # Step 4: Collect automation suggestions
        recommendations = self._build_recommendations(ranked, entity_findings)

        # Step 5: Build consensus narrative
        consensus = self._build_consensus(findings, entity_findings, conflicts)

        return analysis.model_copy(
            update={
                "consensus": consensus,
                "conflicts": conflicts,
                "holistic_recommendations": recommendations,
                "synthesis_strategy": SynthesisStrategy.PROGRAMMATIC,
            }
        )

    def _detect_conflicts(
        self, entity_findings: dict[str, list[SpecialistFinding]]
    ) -> list[str]:
        """Detect conflicting findings on the same entity from different specialists."""
        conflicts: list[str] = []
        concern_types = {"concern", "data_quality_flag"}
        positive_types = {"insight", "recommendation"}

        for entity, group in entity_findings.items():
            if len(group) < 2:
                continue

            specialists_by_sentiment: dict[str, list[str]] = defaultdict(list)
            for f in group:
                if f.finding_type in concern_types:
                    specialists_by_sentiment["concern"].append(f.specialist)
                elif f.finding_type in positive_types:
                    specialists_by_sentiment["positive"].append(f.specialist)

            if specialists_by_sentiment.get("concern") and specialists_by_sentiment.get("positive"):
                concern_specs = ", ".join(sorted(set(specialists_by_sentiment["concern"])))
                positive_specs = ", ".join(sorted(set(specialists_by_sentiment["positive"])))
                conflicts.append(
                    f"{entity}: {concern_specs} flagged concerns while "
                    f"{positive_specs} found positive patterns"
                )

        return conflicts

    def _rank_findings(
        self,
        findings: list[SpecialistFinding],
        entity_findings: dict[str, list[SpecialistFinding]],
    ) -> list[SpecialistFinding]:
        """Rank findings by cross-specialist reinforcement and confidence."""

        def score(f: SpecialistFinding) -> float:
            base = f.confidence
            # Boost for cross-references
            cross_ref_boost = len(f.cross_references) * 0.1
            # Boost for multi-specialist entity coverage
            entity_boost = 0.0
            for entity in f.entities:
                specialist_count = len(set(ef.specialist for ef in entity_findings.get(entity, [])))
                if specialist_count > 1:
                    entity_boost = max(entity_boost, 0.15 * (specialist_count - 1))
            return base + cross_ref_boost + entity_boost

        return sorted(findings, key=score, reverse=True)

    def _build_recommendations(
        self,
        ranked: list[SpecialistFinding],
        entity_findings: dict[str, list[SpecialistFinding]],
    ) -> list[str]:
        """Build ranked recommendations from findings and automation suggestions."""
        recommendations: list[str] = []
        seen: set[str] = set()

        for f in ranked:
            # Include automation suggestions as recommendations
            if f.automation_suggestion:
                s = f.automation_suggestion
                rec = f"{s.proposed_action} (trigger: {s.proposed_trigger})"
                if rec not in seen:
                    recommendations.append(rec)
                    seen.add(rec)

            # Include high-confidence findings as recommendations
            if f.confidence >= 0.7 and f.finding_type == "recommendation":
                rec = f.title
                if rec not in seen:
                    recommendations.append(rec)
                    seen.add(rec)

        # Add entity-level recommendations for multi-specialist entities
        for entity, group in entity_findings.items():
            specialists = set(f.specialist for f in group)
            if len(specialists) >= 2:
                rec = f"Review {entity} — flagged by {len(specialists)} specialists"
                if rec not in seen:
                    recommendations.append(rec)
                    seen.add(rec)

        return recommendations

    def _build_consensus(
        self,
        findings: list[SpecialistFinding],
        entity_findings: dict[str, list[SpecialistFinding]],
        conflicts: list[str],
    ) -> str:
        """Build a consensus narrative."""
        specialist_counts = defaultdict(int)
        for f in findings:
            specialist_counts[f.specialist] += 1

        parts = [
            f"Analysis synthesized {len(findings)} findings from "
            f"{len(specialist_counts)} specialist(s)."
        ]

        # Summarize multi-specialist entities
        multi = [e for e, g in entity_findings.items() if len(set(f.specialist for f in g)) > 1]
        if multi:
            parts.append(
                f"{len(multi)} entity/entities flagged by multiple specialists: "
                f"{', '.join(multi[:5])}{'...' if len(multi) > 5 else ''}."
            )

        if conflicts:
            parts.append(f"{len(conflicts)} conflict(s) detected requiring review.")

        return " ".join(parts)


# ---------------------------------------------------------------------------
# LLM Synthesizer
# ---------------------------------------------------------------------------


class LLMSynthesizer:
    """LLM-backed synthesizer for nuanced conflict resolution.

    Receives the full TeamAnalysis and uses an LLM to produce
    narrative synthesis with reasoning about trade-offs.

    Strengths: Handles ambiguity, resolves conflicts with reasoning.
    Weaknesses: Adds latency, costs tokens, non-deterministic.
    """

    def __init__(self, llm: Any = None):
        """Initialize with an LLM instance.

        Args:
            llm: A LangChain-compatible LLM with ainvoke(). If None,
                will be created from settings when first called.
        """
        self._llm = llm

    async def synthesize(self, analysis: TeamAnalysis) -> TeamAnalysis:
        """Synthesize findings using an LLM.

        Does NOT mutate the input. Returns a new TeamAnalysis.

        Args:
            analysis: TeamAnalysis with accumulated specialist findings.

        Returns:
            New TeamAnalysis with LLM-generated consensus, conflicts, and recommendations.
        """
        try:
            prompt = self._build_prompt(analysis)
            response = await self._llm.ainvoke(prompt)
            parsed = self._parse_response(response.content)

            return analysis.model_copy(
                update={
                    "consensus": parsed.get("consensus", "LLM synthesis complete."),
                    "conflicts": parsed.get("conflicts", []),
                    "holistic_recommendations": parsed.get("holistic_recommendations", []),
                    "synthesis_strategy": SynthesisStrategy.LLM,
                }
            )
        except Exception as e:
            logger.error("LLM synthesis failed", error=str(e))
            return analysis.model_copy(
                update={
                    "consensus": f"LLM synthesis failed: {e}",
                    "conflicts": [],
                    "holistic_recommendations": [],
                    "synthesis_strategy": SynthesisStrategy.LLM,
                }
            )

    def _build_prompt(self, analysis: TeamAnalysis) -> str:
        """Build the LLM prompt from TeamAnalysis."""
        findings_text = []
        for f in analysis.findings:
            findings_text.append(
                f"[{f.specialist}] ({f.finding_type}, confidence={f.confidence:.2f}) "
                f"{f.title}: {f.description}"
            )

        return (
            "You are synthesizing findings from a team of Home Assistant data analysts.\n\n"
            f"Request: {analysis.request_summary}\n\n"
            f"Findings:\n" + "\n".join(findings_text) + "\n\n"
            "Respond with JSON containing:\n"
            '- "consensus": A narrative summary explaining how findings relate\n'
            '- "conflicts": A list of disagreements with reasoning\n'
            '- "holistic_recommendations": A list of actionable recommendations\n\n'
            "JSON response:"
        )

    def _parse_response(self, content: str) -> dict[str, Any]:
        """Parse LLM JSON response, with fallback."""
        try:
            # Try to extract JSON from the response
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except (json.JSONDecodeError, ValueError):
            pass

        return {
            "consensus": content,
            "conflicts": [],
            "holistic_recommendations": [],
        }


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def synthesize(
    analysis: TeamAnalysis,
    strategy: SynthesisStrategy = SynthesisStrategy.PROGRAMMATIC,
    llm: Any = None,
) -> TeamAnalysis:
    """Synthesize specialist findings using the specified strategy.

    This is the main entry point for synthesis. For async LLM synthesis,
    call LLMSynthesizer.synthesize() directly.

    Args:
        analysis: TeamAnalysis with accumulated findings.
        strategy: Which synthesizer to use.
        llm: Optional LLM for LLM strategy (required if strategy is LLM).

    Returns:
        Synthesized TeamAnalysis.

    Raises:
        ValueError: If LLM strategy is requested without an LLM.
    """
    if strategy == SynthesisStrategy.PROGRAMMATIC:
        return ProgrammaticSynthesizer().synthesize(analysis)
    elif strategy == SynthesisStrategy.LLM:
        raise ValueError(
            "LLM synthesis is async. Use `await LLMSynthesizer(llm=llm).synthesize(analysis)` instead."
        )
    else:
        raise ValueError(f"Unknown synthesis strategy: {strategy}")

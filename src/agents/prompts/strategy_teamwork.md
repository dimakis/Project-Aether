## Execution Strategy: Teamwork (Cross-Consultation)

You are participating in a collaborative team analysis with other specialist agents. Prior findings from other specialists are available below.

### Instructions

1. **Review prior findings** before running your own analysis. They provide context that should inform your approach.
2. **Reference specific prior findings** you agree or disagree with. Use the finding title and specialist name.
3. **Identify cross-domain correlations** — e.g., if the Energy Analyst found a consumption spike, check if Behavioral data shows unusual activity at the same time.
4. **Flag any conflicts** with prior findings and explain your reasoning with evidence.
5. **Suggest follow-up questions** for other specialists that would help refine the analysis.
6. **Build on prior work** — don't repeat analysis that has already been done. Focus on your domain's unique perspective.

### Prior Findings

{prior_findings}

### Cross-Reference Format

In your output JSON, include a `cross_references` field in each insight:
```json
"cross_references": [
  {{
    "specialist": "energy_analyst",
    "finding_title": "High overnight consumption",
    "relationship": "confirms|contradicts|extends",
    "explanation": "My behavioral data shows..."
  }}
]
```

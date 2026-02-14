# User Flows

Step-by-step interaction sequences for all major features. See [Architecture](architecture.md) for system design details.

---

## 1. Chat & Home Control

```
You: "Turn on the living room lights"
         │
         ▼
    ┌─────────────┐
    │  Architect   │  Detects entity control intent
    └──────┬──────┘
           │
           ▼
    ┌─────────────────┐
    │ WAITING APPROVAL │  "I can turn on light.living_room. Reply 'approve' to proceed."
    └──────┬──────────┘
           │
      You: "approve"
           │
           ▼
    ┌─────────────┐
    │ Execute via │──▶ Home Assistant (MCP)
    │    MCP      │
    └─────────────┘
           │
           ▼
    "Done! The living room lights are now on."
```

---

## 2. Entity Discovery

```
You: "Discover my home" (or run `make discover`)
         │
         ▼
    ┌─────────────┐    ┌─────────────┐
    │  Architect   │──▶│  Librarian   │
    └─────────────┘    └──────┬──────┘
                              │
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
              list_entities  domain   system
              (all domains)  summary  overview
                    │         │         │
                    └─────────┼─────────┘
                              ▼
                    ┌─────────────────┐
                    │  Infer devices  │  (from entity attributes)
                    │  Extract areas  │  (from entity area_ids)
                    │  Sync automations│ (from list_automations)
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
                    │ Persist to DB   │  Entities, devices, areas stored
                    │ (PostgreSQL)    │  in local catalog
                    └─────────────────┘
                             │
                             ▼
    "Discovered 847 entities across 23 domains, 12 areas, 156 devices."
```

---

## 3. Automation Design (HITL)

```
You: "Create an automation that turns off the hallway lights at midnight"
         │
         ▼
    ┌─────────────┐
    │  Architect   │  Queries entity catalog for hallway lights
    └──────┬──────┘  Designs automation trigger + action
           │
           ▼
    ┌───────────────────┐
    │ Automation        │  Status: PROPOSED
    │ Proposal          │  Shows YAML + explanation
    │                   │  "Here's what this will do..."
    └──────┬────────────┘
           │
      You: "approve"
           │
           ▼
    ┌─────────────┐    ┌─────────────┐
    │  Developer   │──▶│ Deploy to   │  Generates YAML, reloads HA
    │   Agent      │    │ Home Asst.  │
    └─────────────┘    └─────────────┘
           │
           ▼
    "Automation deployed! 'Hallway lights midnight off' is now active in HA."
    
    (You can later: view, disable, or rollback via /proposals)
```

---

## 4. Energy Analysis

```
You: "Analyze my energy consumption this week"
         │
         ▼
    ┌─────────────┐         ┌──────────────────┐
    │  Architect   │────────▶│  DS Team (Energy) │
    └─────────────┘         └────────┬─────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
            Discover energy    Fetch 7 days      Generate Python
            sensors (MCP)      of history (MCP)   analysis script (LLM)
                    │                │                │
                    └────────────────┼────────────────┘
                                     ▼
                            ┌─────────────────┐
                            │  gVisor Sandbox  │  Execute script in isolation
                            │  (pandas/numpy)  │  No network, read-only FS
                            └────────┬────────┘
                                     │
                                     ▼
                            ┌─────────────────┐
                            │ Extract Insights │  Parse output, identify patterns
                            │    (LLM)         │  Calculate projected savings
                            └────────┬────────┘
                                     │
                                     ▼
    "Your total consumption was 187 kWh this week. Peak usage occurs
     between 6-8 PM. Suggestion: Shifting your EV charging to off-peak
     hours (midnight-6 AM) could save ~$12/month."
     
    Insight persisted to DB, viewable in /insights
```

---

## 5. Diagnostics & Troubleshooting

```
You: "My car charger energy data disappeared from my dashboards"
         │
         ▼
    ┌─────────────┐
    │  Architect   │
    └──────┬──────┘
           │
    ┌──────┼───────────────────────────────────────┐
    │      ▼                                        │
    │  analyze_error_log()    → Parse HA error log  │
    │  find_unavailable()     → Scan entity health  │  Evidence
    │  diagnose_entity(...)   → Deep-dive sensors   │  gathering
    │  check_integration()    → Integration status  │
    │  validate_config()      → Config validation   │
    └──────┬────────────────────────────────────────┘
           │
           ▼
    ┌──────────────────────────────┐
    │ consult_data_science_team() │  Auto-routes to Diagnostic Analyst
    └──────┬───────────────────────┘
           │
           ▼
    ┌──────────────────┐
    │  DS Team          │  Diagnostic Analyst: analyze data gaps,
    │  (sandbox)        │  sensor connectivity, integration failures
    └──────┬───────────┘
           │
           ▼
    "The Wallbox integration lost connection 3 days ago (error: 
     ConnectionRefusedError). 4 related entities are unavailable.
     Recommended: restart the integration or check the charger's 
     network connection."
```

---

## 6. Scheduled & Event-Driven Insights

```
You: "Set up a daily energy analysis at 2 AM"
         │
         ▼
    ┌─────────────┐
    │  Architect   │  Calls create_insight_schedule()
    └──────┬──────┘
           │
           ▼
    ┌─────────────────────┐
    │  InsightSchedule     │  cron: "0 2 * * *"
    │  (APScheduler)       │  analysis_type: energy
    └──────┬──────────────┘  analysis_params: {days: 7}
           │
           ▼ (at 2 AM each day)
    ┌─────────────────────┐
    │ Same analysis pipeline as manual requests          │
    │ DS Team → Sandbox → Insights → DB                  │
    └─────────────────────┘
           │
           ▼
    New insights appear in /insights, viewable in the UI
    
    ---
    
    HA webhook triggers work the same way:
    POST /api/v1/webhooks/ha (from HA automation)
         │
         ▼
    Triggers configured analysis pipeline automatically
```

---

## 7. Optimization Suggestions

```
You: "Can you suggest any automations based on my usage patterns?"
         │
         ▼
    ┌─────────────┐          ┌──────────────────────┐
    │  Architect   │─────────▶│  DS Team (Behavioral) │
    └─────────────┘          └────────┬─────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                  ▼
            Fetch logbook       Analyze button      Check automation
            data (MCP)          press patterns      usage patterns
                    │                 │                  │
                    └─────────────────┼─────────────────┘
                                      ▼
                            ┌──────────────────┐
                            │  Behavioral       │
                            │  Analysis         │
                            │  (sandbox)        │
                            └────────┬─────────┘
                                     │
                                     ▼
    ┌─────────────────────────────────────────────────────────────┐
    │ Finding: "You turn off the living room lights every night   │
    │  at ~11 PM. This is a strong recurring pattern              │
    │  (confidence: 0.92)."                                       │
    │                                                             │
    │ Suggested automation:                                       │
    │  trigger: time 23:00                                        │
    │  action: turn_off light.living_room                         │
    └──────┬──────────────────────────────────────────────────────┘
           │ returned to Architect via tool response
           ▼
    ┌─────────────┐
    │  Architect   │  "The Behavioral Analyst noticed you turn off the living room
    └──────┬──────┘   lights every night at 11 PM. Want me to create an
           │          automation for that?"
           ▼
      You: "Yes please"
           │
           ▼
    (Standard automation design flow with HITL approval)
```

---

## See Also

- [Architecture](architecture.md) — how the agent system is structured
- [API Reference](api-reference.md) — endpoints for all of the above
- [CLI Reference](cli-reference.md) — terminal commands for analysis, discovery, proposals

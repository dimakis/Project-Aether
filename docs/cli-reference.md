# CLI Reference

The `aether` CLI provides terminal access to all features.

## Server

```bash
aether serve [--reload]          # Start the API server
```

## Entity Discovery

```bash
aether discover                    # Run full entity discovery
aether discover --domain light     # Discover specific domain
aether discover --force            # Force re-discovery
aether entities                    # List all entities
aether entities --domain sensor    # Filter by domain
```

## Devices & Areas

```bash
aether devices                     # List discovered devices
aether areas                       # List discovered areas
```

## Chat

```bash
aether chat                        # Interactive chat session
aether chat --continue <id>        # Continue existing conversation
```

## Automation Proposals

```bash
aether proposals list              # List proposals
aether proposals show <id>         # Show proposal details
aether proposals approve <id>      # Approve a proposal
aether proposals reject <id>       # Reject a proposal
aether proposals deploy <id>       # Deploy approved proposal to HA
aether proposals rollback <id>     # Rollback deployed proposal
```

## Analysis

```bash
aether analyze energy --days 7     # Run energy analysis
aether analyze behavior            # Run behavioral analysis
aether analyze health              # Run health analysis
aether optimize behavior           # Run optimization analysis
```

## Insights

```bash
aether insights                    # List generated insights
aether insight <id>                # Show insight details
```

## HA Registry

```bash
aether automations                 # List HA automations
aether scripts                     # List HA scripts
aether scenes                      # List HA scenes
aether services                    # List known services
aether seed-services               # Seed common services into DB
```

## Evaluation

```bash
aether evaluate                    # Evaluate recent agent traces
aether evaluate --traces 50        # Evaluate last 50 traces
aether evaluate --hours 48         # Evaluate traces from last 48 hours
```

## System

```bash
aether status                      # Show system status
aether version                     # Show version info
aether ha-gaps                     # Show MCP capability gaps
```

---

## See Also

- [API Reference](api-reference.md) — REST API endpoints
- [Development](development.md) — Makefile targets for testing and quality

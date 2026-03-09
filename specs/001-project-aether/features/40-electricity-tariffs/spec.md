# Feature: Electricity Tariff Management

**Status**: In Progress
**Priority**: P2
**Depends on**: 25-ds-team-architecture, 03-intelligent-optimization

## Goal

Enable Aether to manage electricity tariff rates via chat, provide real-time
tariff awareness throughout the system, and surface energy cost data in a
dedicated Energy dashboard page.

## Problem Statement

The Energy Analyst currently has no access to actual electricity tariff rates.
Cost optimisation analyses either guess at rates or omit cost calculations
entirely. Users cannot update tariff information through Aether, and there is
no UI surface for energy cost visibility.

## User Experience

1. User says: "Here are my new electricity rates: Day 25.84c, Night 13.54c,
   Peak 29.18c — Yuno ETV06 plan"
2. Architect extracts structured rates and calls `update_electricity_tariffs`
3. Proposal appears on the Proposals page for HITL approval
4. On approval, HA `input_number` helpers are updated with the new rates
5. The `/energy` dashboard immediately reflects the updated tariff
6. DS team analyses now include real cost calculations based on actual rates

## Components

### HA Helpers

| Entity | Type | Purpose |
|--------|------|---------|
| `input_number.electricity_rate_day` | input_number | Day rate (c/kWh) |
| `input_number.electricity_rate_night` | input_number | Night rate (c/kWh) |
| `input_number.electricity_rate_peak` | input_number | Peak rate (c/kWh) |
| `input_number.electricity_rate_current` | input_number | Active rate (automation-driven) |
| `input_text.electricity_plan_name` | input_text | Plan name |
| `input_select.electricity_tariff_period` | input_select | Current period: day/night/peak |

### Time Schedule (Day/Night/Peak)

- Day: 08:00–23:00 (excluding peak)
- Night: 23:00–08:00
- Peak: 17:00–19:00 (carved out of day)

### Agent Tools

- `setup_electricity_tariffs` — one-time helper + automation creation
- `update_electricity_tariffs` — update rates via seek_approval (HITL)

### Backend API

- `GET /api/v1/energy/tariffs` — returns current tariff configuration

### UI

- `/energy` page — full energy dashboard (tariff card, consumption summary,
  cost breakdown, recent insights, quick actions)
- Dashboard summary card — current rate and period on the main dashboard
- EvidencePanel — EUR-aware cost rendering in insights

## Acceptance Criteria

- **Given** tariff helpers exist in HA, **when** the user asks Aether to
  update rates, **then** a HITL proposal is created with the new values.
- **Given** tariff helpers are configured, **when** the Energy Analyst runs a
  cost analysis, **then** `tariff_rates` are injected into the sandbox data.
- **Given** the `/energy` route is loaded, **when** tariffs are configured,
  **then** current rate, period, plan name, and schedule are displayed.
- **Given** tariffs are not configured, **when** the `/energy` page loads,
  **then** a "not configured" state is shown with a prompt to set up via chat.

## Out of Scope

- Real-time utility API integration (rates are manually provided)
- Standing charges and PSO levy tracking
- Multi-tariff plan comparison
- Solar/battery optimisation (Feature 14)
- Peak demand management (Feature 17)

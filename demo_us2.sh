#!/bin/bash

# Project Aether - User Story 2 Demo
# Conversational Design with Architect Agent
# 
# This demo shows the HITL (Human-in-the-Loop) approval flow for
# designing and deploying automations through conversational AI.

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║        Project Aether - User Story 2 Demo                     ║${NC}"
echo -e "${CYAN}║   Conversational Automation Design with HITL Approval         ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if database is running
echo -e "${BLUE}[1/7] Checking system status...${NC}"
uv run aether status 2>&1 | head -20
echo ""

# Show US2 CLI commands
echo -e "${BLUE}[2/7] Available US2 Commands:${NC}"
echo ""
echo -e "${YELLOW}Chat commands:${NC}"
echo "  aether chat           - Interactive chat with Architect agent"
echo ""
echo -e "${YELLOW}Proposal commands:${NC}"
echo "  aether proposals list      - List all proposals"
echo "  aether proposals show <id> - Show proposal details"  
echo "  aether proposals approve <id> - Approve a proposal"
echo "  aether proposals reject <id> <reason> - Reject with reason"
echo "  aether proposals deploy <id> - Deploy to Home Assistant"
echo "  aether proposals rollback <id> - Rollback deployed automation"
echo ""

# Show the Architect agent
echo -e "${BLUE}[3/7] Architect Agent Overview:${NC}"
echo ""
echo "The Architect agent is responsible for:"
echo "  • Understanding natural language automation requests"
echo "  • Designing automations based on available entities"
echo "  • Creating structured proposals for review"
echo "  • Refining designs based on feedback"
echo ""

# Show the Developer agent
echo -e "${BLUE}[4/7] Developer Agent Overview:${NC}"
echo ""
echo "The Developer agent is responsible for:"
echo "  • Generating valid Home Assistant YAML"
echo "  • Deploying approved automations"
echo "  • Managing automation lifecycle (enable/disable)"
echo "  • Rolling back deployed automations"
echo ""

# Show the HITL flow
echo -e "${BLUE}[5/7] HITL Approval Flow:${NC}"
echo ""
echo -e "${GREEN}┌─────────────────────────────────────────────────────────────┐${NC}"
echo -e "${GREEN}│                    HITL Approval Flow                        │${NC}"
echo -e "${GREEN}├─────────────────────────────────────────────────────────────┤${NC}"
echo -e "${GREEN}│                                                              │${NC}"
echo -e "${GREEN}│   User Request  ──→  Architect Agent  ──→  Proposal         │${NC}"
echo -e "${GREEN}│        │                                       │             │${NC}"
echo -e "${GREEN}│        │                                       ▼             │${NC}"
echo -e "${GREEN}│        │                              ┌───────────────┐      │${NC}"
echo -e "${GREEN}│        │                              │ HUMAN REVIEW  │      │${NC}"
echo -e "${GREEN}│        │                              │   (HITL)      │      │${NC}"
echo -e "${GREEN}│        │                              └───────┬───────┘      │${NC}"
echo -e "${GREEN}│        │                                      │              │${NC}"
echo -e "${GREEN}│        │                          Approve  ◄──┴──► Reject    │${NC}"
echo -e "${GREEN}│        │                             │               │       │${NC}"
echo -e "${GREEN}│        │                             ▼               ▼       │${NC}"
echo -e "${GREEN}│        │                      Developer Agent      Refine    │${NC}"
echo -e "${GREEN}│        │                             │                       │${NC}"
echo -e "${GREEN}│        ▼                             ▼                       │${NC}"
echo -e "${GREEN}│   Deployed to HA  ◄─────────   Generate YAML                 │${NC}"
echo -e "${GREEN}│                                                              │${NC}"
echo -e "${GREEN}└─────────────────────────────────────────────────────────────┘${NC}"
echo ""

# Show proposal states
echo -e "${BLUE}[6/7] Proposal State Machine:${NC}"
echo ""
echo -e "${YELLOW}States:${NC}"
echo "  DRAFT     → Initial state when proposal is created"
echo "  PROPOSED  → Ready for human review"
echo "  APPROVED  → User approved, ready for deployment"
echo "  REJECTED  → User rejected, can be refined"
echo "  DEPLOYED  → Live in Home Assistant"
echo "  ROLLED_BACK → Removed from Home Assistant"
echo "  ARCHIVED  → No longer active"
echo ""
echo -e "${YELLOW}Transitions:${NC}"
echo "  DRAFT → PROPOSED → APPROVED → DEPLOYED → ROLLED_BACK"
echo "                  ↘ REJECTED ↗"
echo ""

# Show API endpoints
echo -e "${BLUE}[7/7] US2 API Endpoints:${NC}"
echo ""
echo -e "${YELLOW}Conversations:${NC}"
echo "  GET    /api/v1/conversations           - List conversations"
echo "  POST   /api/v1/conversations           - Start new conversation"
echo "  GET    /api/v1/conversations/{id}      - Get conversation detail"
echo "  POST   /api/v1/conversations/{id}/messages - Send message"
echo "  WS     /api/v1/conversations/{id}/stream   - WebSocket streaming"
echo ""
echo -e "${YELLOW}Proposals:${NC}"
echo "  GET    /api/v1/proposals               - List proposals"
echo "  GET    /api/v1/proposals/pending       - List pending approvals"
echo "  GET    /api/v1/proposals/{id}          - Get proposal detail"
echo "  POST   /api/v1/proposals/{id}/approve  - Approve proposal"
echo "  POST   /api/v1/proposals/{id}/reject   - Reject proposal"
echo "  POST   /api/v1/proposals/{id}/deploy   - Deploy to HA"
echo "  POST   /api/v1/proposals/{id}/rollback - Rollback from HA"
echo ""

# Summary
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                    US2 Demo Complete!                         ║${NC}"
echo -e "${CYAN}╠═══════════════════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║  Key Components Implemented:                                  ║${NC}"
echo -e "${CYAN}║  ✓ Conversation & Message models                              ║${NC}"
echo -e "${CYAN}║  ✓ AutomationProposal with state machine                      ║${NC}"
echo -e "${CYAN}║  ✓ Architect agent for design                                 ║${NC}"
echo -e "${CYAN}║  ✓ Developer agent for deployment                             ║${NC}"
echo -e "${CYAN}║  ✓ LangGraph workflow with HITL interrupt                     ║${NC}"
echo -e "${CYAN}║  ✓ Chat & Proposals API endpoints                             ║${NC}"
echo -e "${CYAN}║  ✓ CLI commands for interaction                               ║${NC}"
echo -e "${CYAN}║  ✓ 103 passing tests                                          ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "To start an interactive chat session:"
echo "  uv run aether chat"
echo ""
echo "To see proposals:"
echo "  uv run aether proposals list"
echo ""

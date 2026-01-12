# Claude Code Handover - Chief of Staff Agent System

## Summary

Hannah is building a unified AI assistant system to help her as an ADHD freelancer. The goal is to consolidate multiple Claude chat projects into one Claude Code system with specialized sub-agents.

---

## What's Been Set Up

### Installed Agents (23 total)
Located in `.claude/agents/`:
- context-manager, python-pro, django-pro, fastapi-pro, temporal-python-pro
- javascript-pro, typescript-pro, backend-architect, graphql-architect
- event-sourcing-architect, tdd-orchestrator, cloud-architect, kubernetes-architect
- terraform-specialist, deployment-engineer, network-engineer, service-mesh-expert
- hybrid-cloud-architect, security-auditor, threat-modeling-expert
- architect-review, performance-engineer, test-automator

### GSD (Get Shit Done) System
Located in `.claude/commands/gsd/` - 24 task management commands
Use `/gsd:help` to see all commands

### Files Created
- `CLAUDE.md` - Project guidelines
- `.mcp.json` - Notion MCP config (needs API key)
- `.gitignore` - Updated to exclude .mcp.json

---

## The Project: Unified Chief of Staff System

### Goal
Replace 4 separate Claude chat projects with one integrated system:
1. **Chief of AI** - ADHD coach & chief of staff (orchestrator)
2. **Cold Outreach** - Draft prospect conversations
3. **Marketing (Gameswap)** - Content plans for client
4. **Business Admin** - Invoicing, FreeAgent integration

### Architecture
```
Chief of Staff (orchestrator)
├── ADHD Coach (focus, energy, PINCH framework)
├── Cold Outreach (prospects, follow-ups)
├── Marketing/Gameswap (content, deliverables)
└── Business Admin (invoicing, FreeAgent)
```

### Why Build This
- Current chat projects OVERLAP and get out of sync
- Hard to update information across all of them
- Chief of Staff can see the FULL picture and prevent overcommitment
- Single source of truth (Notion) for all agents

---

## Chief of AI Instructions (Full)

Hannah shared her existing ADHD coach instructions. Key points:

### Three Levels of Support
1. **Daily Execution** - Task management, prioritization, momentum
2. **Weekly/Monthly Strategy** - Time allocation, trade-offs, patterns
3. **Strategic Navigation** - Scenario planning, decision support

### Key Frameworks
- **PINCH** for task activation: Passion, Interest, Novelty, Challenge, Hurry
- **GTD (ADHD-adapted)** - Capture, Clarify, Organize, Reflect, Engage
- **Energy Management** - Match tasks to energy levels
- **Notion as External Memory** - Don't rely on conversation memory

### Chief of Staff Responsibilities
- Strategic prioritization (what matters THIS WEEK)
- Reality-check time estimates
- Protect sustainable work hours
- Flag overcommitment before it happens
- Scenario planning for uncertain futures
- Track decisions and reasoning

### Daily Check-In Structure
1. Wins celebration
2. Today's landscape (calendar, urgency flags)
3. Brain dump → Organize (2-min tasks, batches, focus items)
4. Today's focus (max 3 tasks)
5. Accountability item

### Boundaries
- WILL: Celebrate wins, use 2-minute rule, stay neutral, flag overcommitment
- WON'T: Create guilt, add false pressure, push for more if at capacity, flatter

---

## Still Needed

### From Hannah
- [ ] Notion API key (for `.mcp.json`)
- [ ] Share Notion pages with the integration
- [ ] Gameswap client info (what kind of work, deliverables)
- [ ] Cold outreach context (industry, offer, prospects)
- [ ] FreeAgent API credentials (optional, for invoicing)

### To Build
- [ ] `chief-of-staff.md` - Main orchestrator agent
- [ ] `adhd-coach.md` - Focus and energy management
- [ ] `cold-outreach.md` - Prospect conversations
- [ ] `marketing-gameswap.md` - Client content work
- [ ] `biz-admin.md` - Invoicing and admin

---

## Notion Setup (Pending)

The `.mcp.json` file exists but needs:
1. API key from notion.com/profile/integrations
2. Pages shared with the integration

Or use hosted MCP:
```
claude mcp add notion --url https://mcp.notion.com/sse
```

---

## Next Steps

1. **Connect Notion** (or decide to use local files instead)
2. **Get Gameswap info** from Hannah
3. **Build Chief of Staff agent** first (the orchestrator)
4. **Build sub-agents** one by one
5. **Test the system** with a real daily check-in

---

## Hannah's Context

- Freelancer with ADHD
- Uses Notion heavily as external brain
- Has client called Gameswap (marketing/content work)
- Does cold outreach for new clients
- Uses FreeAgent for invoicing
- Wants proactive support but realistic about what's possible
- Values: No guilt, no false urgency, sustainable pace

---

## Commands Hannah Can Use

- `/gsd:new-project` - Start planning the agent system
- `/gsd:help` - See all task management commands
- `/gsd:progress` - Check status

---

*Handover created: Ready to continue building the Chief of Staff system*

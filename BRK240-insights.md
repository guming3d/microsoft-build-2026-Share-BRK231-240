# BRK240 — Build Context-Aware Agents: From Data to Decisions

> Speakers: Amanda Silver (CVP, M365 Core & Work IQ) · Marco Casalaina (VP, Products and AI Futurist, Core AI)
> Session code: BRK240 · Code & assets: aka.ms/build26-BRK240 · Hub: aka.ms/microsoft-iq

---

## TL;DR for customer briefings

- Agents fail in the enterprise because they lack **shared context** — about people, business operations, knowledge, and the open web.
- Microsoft is unifying that context into one platform: the **Microsoft IQ Platform**, made up of **Work IQ, Fabric IQ, Foundry IQ, and Web IQ**.
- Each IQ is permission-aware, governed, and consumable from any agent — Foundry agents, M365 Copilot, third-party agents via MCP/A2A/REST.
- Customers seeing impact today: **Nasdaq, Sitecore, Hanwha Qcells, Miro**.
- Per Gartner: prioritizing a unified context layer can lift agent accuracy by **up to 80%** and cut operating cost by **up to 60%** (ref: Gartner, June 2025).

---

## The problem (one slide for any briefing)

**Without shared context, developers and agents both make wrong decisions.**

- Agents see fragments — a doc here, a row there — but never the same picture the business runs on.
- Each team rebuilds its own retrieval, memory, and grounding stack.
- Outcome: brittle agents, duplicate spend, governance drift.

> *"Prioritizing a unified context layer can increase agent accuracy by up to 80% and reduce operational costs by up to 60%."* — Gartner, 2025

---

## The Microsoft IQ Platform — one architecture, four lenses on context

> **Unified intelligence for enterprise AI.** Any agent. Any model. Same governed context.

| IQ | Question it answers | What it provides |
|---|---|---|
| **Work IQ** | *How your employees work* | Context on people, collaboration, and workflows |
| **Fabric IQ** | *How your business operates* | Context on business entities, systems of record, and actions |
| **Foundry IQ** | *How your agents unlock knowledge* | Context on policies, authoritative documents, and knowledge bases |
| **Web IQ** | *How you connect to web intelligence* | Context from the web, news, images, and video |

Pick any subset for the briefing — each IQ stands alone but composes with the others.

---

## Web IQ — grounding built for the AI era

*Available for select Azure customers.*

A suite of grounding APIs across **Web, News, Images, Video, and Browse**, designed for agentic workloads.

**Why customers care:**

- **Quality** — +3 points on grounding satisfaction (GSDAT). Structured, citation-ready context across modalities improves source selection and attribution.
- **Speed** — **164 ms p95 latency**, roughly **2.5× faster** than alternatives. Sub-200ms grounding keeps multi-step agent chains responsive.
- **Token efficiency** — passage-level ranking maximizes information density per token; fewer tokens in, better answers out, lower TCO at scale.

**Customer voice — Nasdaq:**

> *"Web IQ allows us to query external data at lightning speed and returns highly accurate results without forcing us to bolt on a separate system or compromise on security."*
> — Mohsin Shafqat, Director of Software Engineering, Nasdaq Boardvantage®

---

## Foundry IQ — agentic RAG and knowledge for your agents

*Available today. Serverless developer experience in **public preview**.*

**Three layers:**

1. **Knowledge sources** — your apps, structured and unstructured.
2. **Enterprise context** — agent memory, enriched metadata, embeddings.
3. **Context engineering** — agentic RAG engine and managed knowledge bases.

**How it stacks up:** classical RAG = a knowledge base. Foundry IQ = a knowledge base **plus an agentic retrieval engine** that plans, decomposes, and re-grounds across sources.

**Enterprise-grade by default:** unified governance, permission-aware retrieval, sensitivity-label enforcement.

**Customer voice — Sitecore:**

> *"By integrating Foundry IQ, we provide a managed, permission-aware business context layer that connects marketing and brand knowledge into every agent so they can access the right information, at the right time, with the right governance."*
> — Andrei Pop, Director of PM, Innovation, Sitecore

---

## Fabric IQ — the operational brain of the business

*Available today. Ontologies in **public preview**.*

**Three pillars:**

- **Unified business understanding** — consistent meaning across data, models, rules, and actions.
- **Always-on insight to action** — understands and acts on live, context-rich data.
- **Agents with business context** — powers AI agents in both Foundry and Fabric.

**Stack at a glance:**

```
People · Agents
  │
  ├── Operational Intelligence (Real-Time, Ontologies)
  ├── Business Intelligence (Semantic Models, Power BI)
  └── Unified Data (Structured / Unstructured / Event / Graph) — OneLake
```

**OneLake** unifies the world's data — across on-prem and all clouds, all databases, apps, and files, **zero ETL**.

**Power BI semantic models** — the trusted business knowledge layer, **35M+ users** regularly using semantic models in Fabric.

**Fabric IQ Ontologies (public preview)** — a live, unified view of the business for reasoning and decisions:

- Define how your business works with ontologies in Fabric IQ.
- Model org-wide goals and rules across BI and real-time ops.
- Jumpstart ontology creation from **20M+ existing semantic models**.
- Equip agents with rich context for trusted actions and outcomes.

**Customer voice — Hanwha Qcells (data center energy management):**

> *"At the core of this is a data center ontology built on Microsoft Fabric, which creates a shared language that allows human operators, data teams, and AI agents to work toward the same goals. This shared context enables AI agents to deliver actionable recommendations while keeping final decisions with the operator — driving cost savings, resilience, compliance, and emissions reduction."*
> — Emmanuel Daniel, VP, Solutions Department, Hanwha Qcells

---

## Work IQ — workplace intelligence for agents

*Generally available **June 16**.*

Designed for **agents**, not humans — high-volume reasoning and tool-calling at scale.

**Three differentiators:**

- **Optimized for agentic use** — high-throughput agent reasoning and tool-calling with speed, efficiency, and scale.
- **Comprehensive** — continuously structures high-quality context across your data for current, intelligent results.
- **Secure** — operates on enterprise data **in place**, preserving existing security and governance.

**Work IQ API surface:** Chat · Context · Tools · Workspaces · Organizational Intelligence — exposed via **A2A, MCP, and REST** so any agent can consume it.

**Customer voice — Miro:**

> *"Miro's integration with the Work IQ API removes the silos that block teamwork. Customers bring real-time Microsoft 365 Copilot context directly onto the visual collaborative Miro canvas — so research synthesis, diagrams, roadmaps, and workshops reflect the same picture every part of the organization is working from."*
> — Jeff Chow, Chief Product & Technology Officer, Miro

---

## Reference architecture — all IQs together (Refund Agent demo)

A concrete, customer-pitchable example: a **Refund Agent** that uses every IQ.

| Capability | What it does | Powered by |
|---|---|---|
| Trigger / build | "Check my mailbox for Amanda's agent idea" → retrieve and build the agent | **GitHub Copilot CLI + Work IQ** |
| Refund processing | Foundry agent with context delegation, MCP auto-approval, OAuth consent | **Microsoft Foundry** |
| Web grounding | Live web content for context | **Web IQ** |
| Knowledge base | Refund policy documents | **Foundry IQ** |
| Business data | Order & shipment ontology, queryable | **Fabric IQ** |
| Productivity actions | Mail, calendar, Teams over MCP | **Work IQ** |
| Identity | Agentic user authorization (OBO token via MSAL) | **Entra ID** |
| Surface | Teams, Outlook, dashboards | **Microsoft 365 + Agent 365 (Autopilot)** |

Use this as the "what does it actually look like in production?" slide in customer briefings.

---

## Enterprise-ready foundation

Three checklist items every CIO will ask about:

- **Permission-aware and policy-aligned** — identity and access enforced; sensitivity labels and compliance policies honored.
- **Agent decisions are traceable** — every recommendation or action links back to shared business context.
- **Centrally managed governance** — updates flow automatically across all agents and experiences.

---

## Calls to action (customer takeaway slide)

- **Learn more:** aka.ms/microsoft-iq
- **Get the code:** aka.ms/build26-BRK240
- **Hands-on lab:** aka.ms/MicrosoftIQLab
- **Join the discussion:** aka.ms/iq/discussions
- **Hackathon — Agents League** (Creative Apps · Reasoning Agents · Enterprise Agents): aka.ms/agentsleague/aisf

---

## Suggested briefing flow (pick what fits)

1. **Open with the problem** — fragmented context = bad agents. (Gartner stat.)
2. **Introduce the IQ Platform** — one architecture, four lenses.
3. **Pick the 1–2 IQs that match the customer** — e.g., data-heavy customer → Fabric IQ + Foundry IQ; M365-heavy customer → Work IQ + Foundry IQ.
4. **Drop in the matching customer quote.**
5. **Show the Refund Agent reference architecture** — proves it composes.
6. **Close on enterprise foundation + CTAs.**

# BRK231 — Deploy. Observe. Learn. Reinforcement Learning for Production Agents

> Speakers: Alicia Frame (Principal Product Manager, Microsoft) · Omkar More (Partner Engineering Manager, Microsoft)
> Session code: BRK231 · Code & assets: aka.ms/build26-BRK231 · Get started: ai.azure.com

---

## TL;DR for customer briefings

- **Agents break the economics of frontier models** — they consume ~25× the tokens of a single chat turn. Fine-tuning is how you ship reliable agents without runaway cost.
- **Fine-tuning is now the default**, not the exception: 48% of enterprise teams plan to fine-tune vs. 29% using off-the-shelf (Insight Partners 2024).
- **Three pillars** of taking an agent to production: **Improve quality · Reduce cost · Reduce latency** — small tuned models are 10–30× cheaper per token and 3–10× faster.
- **Two paths** in Foundry: **Distillation from agent traces** (one-click from production) → **Reinforcement fine-tuning (RFT)** when distillation hits its ceiling → **Interactive RL** for full algorithmic control.
- **Median SFT job costs ≈ $1**; at 10M TPM a tuned smaller model saves **~$54M/year** vs. a frontier model.
- Customers in production today: **Decagon AI, Discovery Bank, Docusign**.

---

## Why this matters: the agent economics problem

| Stat | What it means |
|---|---|
| **33%** of enterprise software apps will embed agentic AI by 2028 (up from <1% in 2024) — *Gartner, 2024* | Agents are arriving at scale, fast. |
| **51%** of teams already have AI agents in production today — *LangChain, State of AI Agents 2024* | This is no longer experimental. |
| **~25×** tokens consumed per agent task vs. a single chat turn | Tool-call + reflect loops repeat context — costs compound. |

> **Agents are token-consuming machines.** Fine-tuning lets you deploy reliable agents without breaking the bank.

---

## The three pillars of model customization

A small tuned model is **cheaper, faster, smarter** than a generic frontier model on your task.

| Pillar | What it delivers |
|---|---|
| **Improve quality** | Bake your tools, format, and edge cases into the weights. The model calls the right tool at the right time. |
| **Reduce cost** | Small tuned models are **10–30× cheaper per token**. Critical because agents generate ~30× the tokens of regular chat. |
| **Reduce latency** | Smaller models stream **3–10× faster** per token. Reason with **10%** of the tokens. |

---

## Where fine-tuning fits in Microsoft Foundry

```
Build in GitHub  ──►  Run in Foundry  ──►  Distribute to users
   Code                Agent runtime          M365 Copilot
   Prompts             plan / act / observe   Teams
   Skills + tools      host & scale           Apps + APIs
   Eval assets
                       Evaluate & Optimize
                       routing + RL
                       agents & eval signals

   Faster, Better, Cheaper:
     Prompting · Context Management · Tools Handling · Model Fine-tuning (SFT, RFT, RL)

   Backed by:  AI Models (11K) · Context with IQ · Security + Control
```

Fine-tuning is one lever inside a broader **agent factory** — Foundry handles the runtime, evaluation, distribution, and security around it.

---

## Fine-tuning is becoming the default

From Insight Partners' 2024 enterprise tech leader survey:

| Approach | % of teams |
|---|---|
| Out-of-the-box models | 29% |
| **Fine-tuning** | **48%** |
| Training own model | 10% |

**Why the shift:**

- **Cost compounds in the agent loop.** A 20× per-token saving × 25 calls per task = orders-of-magnitude lower spend per workflow.
- **Quality + latency, not just cost.** Fewer drifted tool calls, fewer malformed JSON outputs, 3–10× faster — tuned small models reason in ~200 tokens where generic ones burn ~2,000.

---

## How fine-tuning actually works (quick primer)

**Building a foundation model:**
*Pre-training (unsupervised)* → *Instruction tuning / SFT* → *Alignment tuning (RLHF, DPO)* → Generic LLM/SLM.

**Fine-tuning a foundation model:**
Generic LLM/SLM + **your data** for **your use case** → fine-tuned LLM/SLM with the language, reasoning, and world knowledge you need.

---

## Path 1 — Distillation from production traces

> *Cheaper and faster: distilling a frontier agent into a tuned small model — same task, fraction of the bill.*

**New: turn production traces into a fine-tuning dataset in one click.**

```
Production traces  ──►  Filter & curate  ──►  Training dataset  ──►  Fine-tuned model
```

Your production agent traces are training data hiding in plain sight — every successful tool call, every recovered failure, every accepted answer is a labeled example for the next model.

**The catch:** distillation has a **ceiling**. The student copies the teacher and is bounded by the teacher's quality. It's great for cost and speed, but it won't solve problems the teacher can't.

---

## Path 2 — Reinforcement fine-tuning (RFT): learn from your mistakes

When the model you'd distill from can't solve the task, **RL is the only way up**.

**How RFT differs from supervised distillation:**

| Supervised distillation | Reinforcement fine-tuning |
|---|---|
| Student copies the teacher | Student learns from its own rollouts |
| Bounded by teacher's quality | Reward defines the goal, not the teacher |
| Great for cost & speed | Can outperform the model that generated the data |
| Won't solve problems the teacher can't | Built for tasks where "good" is **verifiable** |

**The RFT loop, conceptually:**

1. Prompt sent to model.
2. Model generates multiple samples.
3. Grader scores each sample (e.g., 0.5 for "is a number", 0.5 for "is correct").
4. Trainer updates weights to favor the best chain-of-thought.

> RFT teaches the model to produce outputs that score highly on a learned reward metric — eliciting structured, goal-directed reasoning that imitation alone cannot reach.

---

## Path 3 — Interactive RL (Training API, sneak peek)

For teams that need **full algorithmic control**.

**What you can bring yourself:**

- **Custom rewards** — your judges, your rubrics, your business rules.
- **Custom rollout environments** — simulators, tool servers, multi-turn worlds.
- **Custom data curation** — your filters, splits, and labeling.
- **Full hyperparameter control** — reasoning effort, compute multiplier, batch size, learning rate.

**Two operating modes side-by-side:**

| Path A — Managed (Azure OAI RFT) | Path B — Interactive (Training API) |
|---|---|
| **Closed loop.** Set up once; service iterates until done. | **Open loop.** Practitioner stays in the cycle — scoring, editing, deciding. |
| Submit `config · dataset · grader fn` once | Review · score · modify each step |
| Service runs rollouts → grader → loss → weight update | You drive a 7-step GRPO loop; service handles GPU work |
| Returns checkpoints | You stop, continue, or change course at every step |

**Inside the interactive Training API:**

```
Client (CPU) — your orchestration code               Azure GPU Cluster (Managed)
─────────────────────────────────────                ──────────────────────────────
Training Recipe (GRPO loop):                          Sampling Node:
  1. Generate rollouts          ─ sample() ─►          base + LoRA adapter
  2. Score with grader                                 N completions per prompt
  3. Compute advantages
  4. forward_backward()         ─ fwd/bwd ─►          Training Node:
  5. optim_step()               ─ step ─►              Base LLM (e.g., Qwen3-32B)
  6. sync_weights()                                    LoRA rank=32
  7. save_checkpoint()          ─ save ─►              Gradient computation
        iterate epochs                                 (importance sampling)
                                                       Checkpoint Storage (Azure Blob)
```

Four API calls per step push GPU work to a managed Azure cluster — sampling, gradients, weight sync, checkpoints.

---

## What customers are getting in production

> *"We were able to exceed the performance of larger state-of-the-art models with smaller, lighter-weight models which could be served significantly faster."*
> — **Jesse Zhang, Co-founder & CEO, Decagon AI**

> *"Response times that were previously five or six seconds came down to one and a half to two seconds — a 50% reduction in latency made conversations with Discovery AI feel seamless."*
> — **Stuart Emslie, Head of Actuarial & Data Science, Discovery Bank**

> *"More than 50% reduction in cost of AI processing per document, much faster inference time, and we could expand throughput by as much as eight times — with the accuracy gap between teacher and student model less than two percentage points."*
> — **Ramachandra Kota, Docusign**

---

## Two myths worth busting in customer briefings

### Myth 1 — *"I don't need to fine-tune; frontier models keep getting smarter."*

**Reality:** Frontier models keep getting **bigger and more expensive**. A tuned small model can match them on quality — and beat them on price.

| Model | Weighted pass rate (internal eval) | Output tokens per dollar (vs. GPT 5.5 baseline) |
|---|---|---|
| **MAI-2-5B Frontier Tuned** | **72.2%** | **>10×** |
| GPT 5 | 71.9% | ~3× |
| GPT 5.4 | 72.1% | ~2× |
| GPT 5.5 | 68.8% | 1× (baseline) |

*Source: internal benchmark, MAI Frontier Tuning team. Bars indexed to GPT 5.5 cost-efficiency baseline.*

### Myth 2 — *"Fine-tuning is too expensive — pay to train, pay to host, slow to value."*

**Reality:** **The median SFT job costs about $1**, and Foundry offers tiers with no hosting fee. At production scale, a tuned smaller model saves **millions per year** vs. the frontier.

| Average TPM | Frontier (GPT 5.5) | Fine-tuned GPT 4.1-nano | Annual savings |
|---|---|---|---|
| 10M TPM | ~$55M / yr | ~$1.1M / yr | **~$54M / yr** |

*Source: Foundry distillation benchmark. Annual cost = TPM × 60 × 24 × 365 × unit price. Median SFT job ≈ $1 (internal usage data).*

---

## "I'm not a data scientist" — the fine-tuning skill

The common objections:

- *"I don't even know where to start."*
- *"I don't have data to train on, and I don't have time to create it."*
- *"We tried once and it made the base model worse."*
- *"I want to fine-tune. I tried. I'm not seeing results."*

> Most teams that say they'll fine-tune in the next year never ship a tuned model.

**Foundry's fine-tuning skill** takes you from idea → experiment → production — **so easy a PM can do it**. Production traces become datasets in one click; managed RFT closes the loop for you; interactive RL is there when you outgrow it.

---

## Microsoft Foundry — the AI app and agent factory

The umbrella around everything above:

- **Agent Service** · **Models** · **IQ** · **Tools** · **Machine Learning**
- **Control Plane** across **Cloud** and **Edge**
- **Governed agent lifecycle**

Fine-tuning is one capability inside this factory; the same governance, security, and distribution surfaces apply.

---

## Calls to action (customer takeaway slide)

- **Get started:** ai.azure.com
- **Sample notebooks:** github.com/microsoft-foundry/fine-tuning
- **Sign up for the API:** aka.ms/ft-api
- **Learn more (docs):** aka.ms/FoundryFTDocs
- **Code from this session:** aka.ms/build26-BRK231
- **Discord community:** aka.ms/ai/discord

**Keep learning — related sessions:**

| Code | Title |
|---|---|
| LAB521 | Improving agent behavior using reinforcement learning from agent traces |
| BRK232 | Train and deploy custom OSS reasoning models with Foundry |
| LTG418 | Smarter training patterns for better AI models |
| DEM322 | Smaller, faster, smarter: Distilling agents with fine-tuning |

---

## Suggested briefing flow (pick what fits)

1. **Hook with the economics** — agents = ~25× tokens; cost compounds.
2. **Frame the three pillars** — quality, cost, latency.
3. **Show the maturity ladder** — Distillation → RFT → Interactive RL. Pick the one that matches the customer's sophistication.
4. **Drop in the customer quote** that matches the use case (CX = Decagon, banking = Discovery, document AI = Docusign).
5. **Bust the two myths** — quality parity at 10× cost-efficiency, and median SFT job ≈ $1.
6. **Close with CTAs** and the related-session list.

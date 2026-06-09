# BRK231 — Core Update

> The two most important takeaways from BRK231, distilled. Full content preserved in `original_content.md`.

---

## 1. Interactive Training API for RFT

For teams that need **full algorithmic control** over reinforcement fine-tuning.

**What you can bring yourself:**

- **Custom rewards** — your judges, your rubrics, your business rules.
- **Custom rollout environments** — simulators, tool servers, multi-turn worlds.
- **Custom data curation** — your filters, splits, and labeling.
- **Full hyperparameter control** — reasoning effort, compute multiplier, batch size, learning rate.

**Two operating modes side-by-side.** The difference is *where the grader lives and who stays in the loop*: in Path A the grader runs **inside the service** and the whole loop auto-iterates to a checkpoint; in Path B the grader is **with you** and the practitioner re-enters the cycle on **every step**.

### Path A — Managed: Azure OAI RFT / managed fine-tuning

> **Closed loop.** Set it up once; the service iterates until done.

```mermaid
flowchart TB
    P["<b>Practitioner</b><br/>Submits config once"]
    P -->|"config · dataset · grader fn"| RE

    subgraph SERVICE["SERVICE"]
        direction TB
        RE["<b>Rollout engine</b><br/>Forward pass · samples"]
        G["<b>Grader</b> · in service<br/>Scores completions"]
        L["<b>Loss computation</b><br/>Reward → loss signal"]
        W["<b>Weight update</b><br/>Backward · accum · step"]
        RE --> G --> L --> W
        W -->|"many gradient steps"| RE
    end

    SERVICE --> CP["Checkpoint returned"]

    style G fill:#e6f4ea,stroke:#1e7e34,stroke-width:2px
    style L fill:#fdf3e0,stroke:#b8860b
```

The grader sits **inside the service** — submit once, and rollouts → grader → loss → weight update repeat automatically until a checkpoint is returned.

### Path B — Interactive: Interactive RL / Training API (sneak peek)

> **Open loop.** Practitioner stays in the cycle — scoring, editing, deciding the next step.

```mermaid
flowchart TB
    P["<b>Practitioner</b><br/>Reviews · scores · modifies"]
    P -->|"config + scores"| RE

    subgraph SERVICE["SERVICE"]
        direction TB
        RE["<b>Rollout engine</b><br/>Forward pass · samples"]
        L["<b>Loss computation</b><br/>Reward → loss signal"]
        W["<b>Weight update</b><br/>Backward · accum · step"]
        RE -->|"rollout buffer"| L --> W
    end

    SERVICE --> G["<b>Grader</b> · with you<br/>Practitioner scores, edits, continues or stops"]
    G -->|"every step"| P

    style G fill:#e6f4ea,stroke:#1e7e34,stroke-width:2px
    style L fill:#fdf3e0,stroke:#b8860b
```

The grader is pulled **out of the service and back to you** — after each weight update you score, edit, and decide whether to continue or stop, so you steer the run on every step.

**Inside the interactive Training API:**

```mermaid
flowchart LR
    subgraph Client["Client (CPU) — your orchestration code"]
        direction TB
        S1["1. Generate rollouts"]
        S2["2. Score with grader"]
        S3["3. Compute advantages"]
        S4["4. forward_backward()"]
        S5["5. optim_step()"]
        S6["6. sync_weights()"]
        S7["7. save_checkpoint()"]
        S1 --> S2 --> S3 --> S4 --> S5 --> S6 --> S7 -->|iterate epochs| S1
    end
    subgraph Azure["Azure GPU Cluster (Managed)"]
        direction TB
        SN["Sampling Node<br/>base + LoRA adapter<br/>N completions per prompt"]
        TN["Training Node<br/>Base LLM (e.g., Qwen3-32B)<br/>LoRA rank=32<br/>Gradient computation (importance sampling)"]
        CS["Checkpoint Storage<br/>(Azure Blob)"]
    end

    S1 -.->|"sample()"| SN
    S4 -.->|"forward_backward()"| TN
    S5 -.->|"optim_step()"| TN
    S7 -.->|"save_checkpoint()"| CS
```

Four API calls per step push GPU work to a managed Azure cluster — sampling, gradients, weight sync, checkpoints.

---

## 2. The Fine-Tuning Skill — "so easy a PM can do it"

The common objections:

- *"I don't even know where to start."*
- *"I don't have data to train on, and I don't have time to create it."*
- *"We tried once and it made the base model worse."*
- *"I want to fine-tune. I tried. I'm not seeing results."*

> Most teams that say they'll fine-tune in the next year never ship a tuned model.

**Foundry's fine-tuning skill** takes you from idea → experiment → production — **so easy a PM can do it**. Production traces become datasets in one click; managed RFT closes the loop for you; interactive RL is there when you outgrow it.

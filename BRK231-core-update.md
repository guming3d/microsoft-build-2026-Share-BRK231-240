# BRK231 Deploy. Observe. Learn. Reinforcement learning for production agents — Core Update

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

### Inside the `microsoft-foundry` skill: the `finetuning` sub-skill

The capability ships as a sub-skill of the **`microsoft-foundry`** skill in the Azure Skills repo:
**[github.com/microsoft/azure-skills → skills/microsoft-foundry/finetuning](https://github.com/microsoft/azure-skills/tree/main/skills/microsoft-foundry/finetuning)**

It fine-tunes models on Azure AI Foundry across **three training types** and covers the full pipeline — dataset prep, training-job submission, deployment, and evaluation.

**Use it for:** fine-tuning (SFT / DPO / RFT), preparing or validating training data, submitting/monitoring/diagnosing jobs, calibrating RFT graders, distillation and synthetic-data generation, large-file uploads, and deploying or evaluating a tuned model.
**Not for:** plain model deployment (use `deploy-model`), agent creation (use `agents`), or prompt-only optimization (use `prompt-optimizer`).

**Three training types — pick by what data you have:**

| Type | Best for | Data needed | Volume | Supported models |
|---|---|---|---|---|
| **SFT** (supervised) | Teaching a new skill or output format | Input–output pairs | 50–5,000 examples | Most models |
| **DPO** (preference) | Aligning tone, style, or safety | Chosen/rejected pairs | 500–5,000 pairs | Select models (can stack on an SFT model) |
| **RFT** (reinforcement) | Improving verifiable reasoning | Prompts + a grading function | 200–2,000 prompts | o4-mini (GPT-5 RFT gated) |

> **Decision shortcut:** Have labeled input–output pairs? → **SFT**. No pairs but can write a grader? → **RFT**. Can only rank "good" vs "bad" outputs? → **DPO**. After SFT: ship it, add **DPO** for style, or add **RFT** when reasoning needs to improve.

**What the sub-skill gives you:**

- **Workflows** — quickstart, full pipeline, dataset creation, iterative training, and diagnosing poor results.
- **References** — training-type selection, hyperparameters, data formats, grader design, reward-hacking avoidance, agentic RFT with tools, deployment, training-curve reading, evaluation, vision FT, large-file uploads, and platform gotchas.
- **Scripts** — `submit_training.py`, `monitor_training.py`, `calibrate_grader.py`, `check_training.py`, `deploy_model.py`, `evaluate_model.py`, `convert_dataset.py`, `generate_distillation_data.py`, `score_dataset.py`, `cleanup.py`, plus per-format data validators.

**Operating rules baked into the skill:**

1. **Baseline first** — evaluate the base model before fine-tuning.
2. **Validate data** before submitting a job.
3. **Calibrate RFT graders** — target a 25–50% failure rate on the base model (train–val gap ≤ 0.05).
4. **Evaluate checkpoints** — don't blindly deploy the final one.
5. **Measure token cost** alongside accuracy when comparing models.

```mermaid
flowchart LR
    BL["Baseline<br/>eval base model"] --> DATA["Prepare & validate<br/>data (SFT/DPO/RFT)"]
    DATA --> TRAIN["Submit & monitor<br/>training job"]
    TRAIN --> CKPT["Analyze curves<br/>pick checkpoint"]
    CKPT --> DEP["Deploy<br/>fine-tuned model"]
    DEP --> EVAL["Evaluate<br/>quality + token cost"]
    EVAL -->|"iterate"| DATA
```

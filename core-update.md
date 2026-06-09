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

**Two operating modes side-by-side:**

| Path A — Managed (Azure OAI RFT) | Path B — Interactive (Training API) |
|---|---|
| **Closed loop.** Set up once; service iterates until done. | **Open loop.** Practitioner stays in the cycle — scoring, editing, deciding. |
| Submit `config · dataset · grader fn` once | Review · score · modify each step |
| Service runs rollouts → grader → loss → weight update | You drive a 7-step GRPO loop; service handles GPU work |
| Returns checkpoints | You stop, continue, or change course at every step |

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

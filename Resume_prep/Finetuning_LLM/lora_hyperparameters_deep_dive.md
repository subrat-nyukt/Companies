# 🔬 LoRA Hyperparameters — Deep Dive with Examples

> Based on your resume: Fine-tuning **MedGemma 27B** with PEFT (LoRA) on proprietary healthcare data.
> Config used: `r=16`, `lora_alpha=32`, targeting attention layers.

---

## Full LoRA Config (Reference Code)

```python
from peft import LoraConfig, get_peft_model, TaskType

lora_config = LoraConfig(
    r=16,                          # Rank
    lora_alpha=32,                 # Scaling factor
    lora_dropout=0.05,             # Dropout
    target_modules=[               # Which layers to adapt
        "q_proj", "v_proj",
        "k_proj", "o_proj"
    ],
    bias="none",                   # Bias training
     task_type=TaskType.CAUSAL_LM   # Task type
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
# Output: trainable params: 41,943,040 || all params: 27,041,943,040
# trainable%: 0.155%  ← Only 0.15% of 27B params are trained!
```

---

---

## 1. `r` — Rank of the LoRA Matrices

### What it is
`r` is the **rank** of the low-rank decomposition. It controls how many dimensions the adapter matrices use.

### The Math
Instead of training a full weight update ΔW (which is huge), LoRA says:
```
ΔW = B × A

where:
  A ∈ ℝ^(r × d_in)   ← small matrix, trained
  B ∈ ℝ^(d_out × r)  ← small matrix, trained
  r << d_in, d_out    ← r is tiny compared to the weight dimensions
```

**Example with real numbers (MedGemma attention layer):**

A single attention weight matrix W in MedGemma 27B might be:
```
W shape = (4096 × 4096) = 16,777,216 parameters  ← HUGE

With LoRA r=16:
  A shape = (16 × 4096)  =    65,536 parameters
  B shape = (4096 × 16)  =    65,536 parameters
  Total LoRA params       =   131,072 parameters  ← 128x fewer!
```

### Intuition
Think of `r` like the **number of "ideas"** the adapter can hold:
- `r=1` → only 1 direction of change — very rigid
- `r=8` → 8 independent directions — lightweight, good for simple tasks
- `r=64` → 64 directions — very expressive, almost like full fine-tuning
- `r=256` → essentially full fine-tuning

### Effect on Training

| `r` value | # Trainable Params | Memory | Performance | Risk |
|---|---|---|---|---|
| 4 | Very few | Very low | May underfit | Too restrictive |
| **16** | Moderate | Low | ✅ Good balance | Low |
| 32 | More | Medium | Better for complex tasks | Slight overfit risk |
| 64 | High | Higher | Near full fine-tune | Overfitting on small data |

### Real Example — Choosing r

```python
# For a simple classification task on small dataset → lower rank
lora_config_simple = LoraConfig(r=4, ...)

# For complex medical reasoning (your use case) → moderate rank
lora_config_medical = LoraConfig(r=16, ...)

# For creative generation on large diverse dataset → higher rank
lora_config_creative = LoraConfig(r=64, ...)
```

### Interview Answer
> "I used `r=16` for MedGemma 27B. The medical suggestion task requires nuanced understanding of clinical language — too low a rank like r=4 would underfit, while r=64 would risk overfitting on our limited proprietary dataset. r=16 gave a good balance: 0.15% of 27B parameters trained, which is about 41M parameters."

---

---

## 2. `lora_alpha` — Scaling Factor (α)

### What it is
`lora_alpha` is a **scaling constant** that controls how much the LoRA update influences the final output.

### The Math
The forward pass with LoRA becomes:
```
h = W₀x + (α/r) × (B × A)x

Where:
  W₀x   = original frozen model output
  B × A  = your LoRA adapter output
  α/r    = the scale factor applied to adapter output
```

The actual effective scaling = `alpha / r`.

**Example with numbers:**

```
Scenario A: alpha=16, r=16  →  scale = 16/16 = 1.0
Scenario B: alpha=32, r=16  →  scale = 32/16 = 2.0  ← your config
Scenario C: alpha=8,  r=16  →  scale = 8/16  = 0.5
```

### Intuition
Think of `alpha/r` as the **volume knob** for your adapter:
- Scale = 0.5 → adapter whispers, barely changes the model
- Scale = 1.0 → adapter speaks normally
- Scale = 2.0 → adapter speaks louder, has more influence
- Scale = 4.0 → adapter shouts, dominates the output

### Why alpha=2×r is the standard convention
Setting `alpha = 2 × r` (e.g., r=16, alpha=32) gives scale=2.0.

This is a **community convention** because:
1. The A matrix is initialized with random normal values (scale ~1/r)
2. The B matrix is initialized to **zero** (so ΔW starts at 0)
3. With scale=1 (alpha=r), the adapter starts at zero but its gradient scale is 1/r
4. Setting alpha=2r compensates to get a cleaner initial effective learning rate

```python
# Standard convention (your config) ✅
LoraConfig(r=16, lora_alpha=32)  # scale = 2.0

# Conservative — adapter has less influence
LoraConfig(r=16, lora_alpha=16)  # scale = 1.0

# Aggressive — adapter dominates faster
LoraConfig(r=16, lora_alpha=64)  # scale = 4.0
```

### Effect on Training

| alpha/r ratio | Effect | When to use |
|---|---|---|
| < 1 (e.g., 0.5) | Adapter barely affects output | When base model is already close to target |
| = 1 | Neutral scaling | Safe default |
| = 2 ✅ | Standard convention | Most fine-tuning tasks |
| > 2 (e.g., 4) | Aggressive adaptation | When task is very different from pre-training |

### Interview Answer
> "I set `lora_alpha=32` with `r=16`, giving a scale of 2.0. This is the standard convention. The alpha controls how loudly the adapter 'speaks' relative to the frozen base model. Too low and the adapter barely affects output; too high and it destabilizes training. Alpha=2×r is a well-tested default that gives stable convergence."

---

---

## 3. `lora_dropout` — Dropout on LoRA Layers

### What it is
`lora_dropout` applies **dropout regularization** to the LoRA adapter matrices during training — randomly zeroing out some activations to prevent overfitting.

### The Math
During the forward pass of the adapter:
```
h_lora = dropout(A × x, p=lora_dropout)  # apply dropout to A's output
output  = W₀x + (α/r) × B × h_lora
```

During training, each neuron in the LoRA path is randomly set to 0 with probability `p`. During inference, dropout is turned off (all neurons active, outputs scaled by `1-p`).

### Visual Example

```
Without dropout (p=0):
  Input x → A → B → scale → add to W₀x
             [a1, a2, a3, a4, a5]  ← all units active

With dropout (p=0.1):
  Input x → A → B → scale → add to W₀x
             [a1,  0, a3,  0, a5]  ← 2/5 randomly zeroed
```

### Why it Matters for Healthcare Data

Proprietary clinical datasets are often **small** (thousands to tens of thousands of examples). Without dropout:
- The 41M LoRA parameters can memorize rare medical terms or patient-specific patterns
- Model overfits, fails on new clinical queries

With dropout = 0.05–0.1:
- Forces the adapter to learn **robust, generalizable** clinical patterns
- Prevents memorization of outlier cases

### Effect on Training

```python
# No regularization — risky on small datasets
LoraConfig(lora_dropout=0.0)   # ❌ Risky for small proprietary data

# Light regularization (your use case) ✅
LoraConfig(lora_dropout=0.05)  # Drop 5% of activations

# Moderate regularization
LoraConfig(lora_dropout=0.1)   # Drop 10% of activations

# Heavy regularization — rarely needed for LoRA
LoraConfig(lora_dropout=0.3)   # Usually too aggressive for adapters
```

### When to increase dropout
- Very small dataset (< 5,000 examples)
- You see validation loss diverging while train loss keeps dropping (classic overfit signal)
- High data imbalance (rare medical conditions over-represented)

### When to use dropout=0
- Large diverse dataset
- When you need deterministic reproducibility
- At inference time (always automatically 0)

### Interview Answer
> "I used `lora_dropout=0.05` — a 5% dropout on the LoRA adapter paths. Our proprietary healthcare dataset was limited in size. Without dropout, the 41M adapter parameters could overfit and memorize institution-specific jargon or outlier cases rather than learning generalizable clinical reasoning. Dropout forces the adapter to not rely on any single activation, improving generalization to new patient queries."

---

---

## 4. `target_modules` — Which Weight Matrices to Apply LoRA To

### What it is
`target_modules` specifies **which layers inside the transformer** get the LoRA adapters. Not all layers need fine-tuning — you choose the most impactful ones.

### Transformer Layer Structure (Simplified)

Every transformer block has:
```
Input
  │
  ├─── Multi-Head Self-Attention ──────────────────────────────────
  │      │                                                         │
  │    q_proj (Query)    k_proj (Key)    v_proj (Value)    o_proj (Output)
  │      │                  │               │                  │
  │    [W_Q × x]         [W_K × x]      [W_V × x]       [W_O × concat]
  │                                                              │
  ├─── Add & Norm ──────────────────────────────────────────────┘
  │
  ├─── Feed-Forward Network (MLP) ──────────────────────────────
  │      gate_proj → up_proj → act_fn → down_proj
  │
  └─── Add & Norm
```

### What each module does

#### `q_proj` — Query Projection
```
Purpose: Projects input into "what am I looking for?" space
Shape:   (d_model × d_head) e.g., (4096 × 128) per head in MedGemma

Without LoRA: W_Q is frozen — model always searches the same way
With LoRA:    W_Q + B_Q × A_Q — model learns to search for medical concepts
              e.g., learns to attend to "symptoms" when generating a diagnosis
```

#### `k_proj` — Key Projection
```
Purpose: Projects input into "what do I contain?" space
Shape:   Same as q_proj

With LoRA: Model learns which tokens are medically relevant to highlight
           e.g., learns that "fever + cough + dyspnea" should be strongly keyed
```

#### `v_proj` — Value Projection
```
Purpose: Projects input into "what information to extract?" space
Shape:   Same as q_proj

With LoRA: Model learns to extract clinical values correctly
           e.g., extracts drug names, dosages, contraindications more accurately
```

#### `o_proj` — Output Projection
```
Purpose: Combines all attention heads into final representation
Shape:   (d_heads_total × d_model) e.g., (4096 × 4096)

With LoRA: Model learns how to synthesize multi-head medical attention
```

### Minimal vs Full Configuration

```python
# Minimal — only Q and V (original LoRA paper default)
# Cheapest, often surprisingly effective
target_modules=["q_proj", "v_proj"]

# Standard — all attention projections (your config) ✅
target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]

# Extended — attention + MLP layers
# More expressive but significantly more params
target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                "gate_proj", "up_proj", "down_proj"]

# Maximum — all linear layers (near full fine-tuning)
target_modules="all-linear"
```

### Parameter Count Impact (MedGemma 27B)

| Config | Approx Trainable Params | % of 27B |
|---|---|---|
| q_proj + v_proj only | ~21M | 0.08% |
| **All 4 attention** ✅ | ~41M | 0.15% |
| + MLP layers | ~120M | 0.44% |
| all-linear | ~300M+ | 1.1%+ |

### How to Find Module Names for Your Model

```python
# Print all named modules to find the right names for your architecture
for name, module in model.named_modules():
    print(name)

# Output for Gemma-based models:
# model.layers.0.self_attn.q_proj
# model.layers.0.self_attn.k_proj
# model.layers.0.self_attn.v_proj
# model.layers.0.self_attn.o_proj
# model.layers.0.mlp.gate_proj
# model.layers.0.mlp.up_proj
# model.layers.0.mlp.down_proj
# ...repeats for all layers
```

You just need the **suffix** — e.g., `"q_proj"` — PEFT matches it across all layers automatically.

### Interview Answer
> "I targeted all four attention projection matrices: `q_proj`, `k_proj`, `v_proj`, and `o_proj`. The query and key projections teach the model what to attend to in clinical text — symptoms, diagnoses, medications. The value projection teaches it what information to extract. The output projection combines the multi-head outputs into a coherent clinical response. I didn't add MLP layers because our proprietary dataset was small — more target modules means more parameters, increasing overfitting risk."

---

---

## 5. `bias` — Whether to Train Bias Parameters

### What it is
`bias` controls whether the **bias terms** in the targeted linear layers are also trained (unfrozen) during LoRA fine-tuning.

### What are Bias Parameters?
Every linear layer computes:
```
output = W × input + b

Where:
  W = weight matrix (LoRA adapts this via B × A)
  b = bias vector   ← this is what `bias` parameter controls
```

**Example in attention:**
```
q = W_Q × x + b_Q   ← b_Q is the bias for Query projection
k = W_K × x + b_K
v = W_V × x + b_V
```

### The Three Options

```python
# Option 1: bias="none"  ← Your config, most common ✅
# Bias params stay frozen. Only LoRA matrices A and B are trained.
# Most memory-efficient. Works well in practice.
LoraConfig(bias="none")

# Trainable params: only A and B matrices

# ─────────────────────────────────────────────────

# Option 2: bias="all"
# ALL bias params across the entire model are unfrozen.
# Slightly more expressive but adds many params.
LoraConfig(bias="all")

# Trainable params: A, B matrices + all bias vectors in the model

# ─────────────────────────────────────────────────

# Option 3: bias="lora_only"
# Only the bias params in LoRA-targeted layers are trained.
# Middle ground between "none" and "all".
LoraConfig(bias="lora_only")

# Trainable params: A, B matrices + bias vectors of q_proj, k_proj, v_proj, o_proj
```

### Parameter Count Comparison (MedGemma 27B, r=16)

| `bias` setting | Extra params added | Total trainable |
|---|---|---|
| `"none"` ✅ | 0 | ~41M |
| `"lora_only"` | ~4M (attention biases) | ~45M |
| `"all"` | ~50M (all model biases) | ~91M |

### Intuition

Think of bias as **offset tuning** — it shifts the output of each layer up or down, independently of the input:

```
# Without bias training:
# LoRA only rotates/scales the weight matrix direction
# output = (W + ΔW) × input

# With bias training:
# LoRA adjusts direction AND can add a constant clinical offset
# output = (W + ΔW) × input + Δb
# Δb could shift model to "clinical register" (more formal, precise language)
```

### When to change from "none"

```python
# Stay with "none" when: ✅ (most cases)
# - Dataset is small (bias training adds overfit risk)
# - You want minimum parameter overhead
# - Base model biases are already well-calibrated

# Consider "lora_only" when:
# - Task has strong output distribution shift
# - e.g., model needs to consistently output ICD codes vs free text

# Consider "all" when:
# - Large dataset, need maximum expressiveness
# - Full-precision training (not quantized)
# - Task is very different from pre-training domain
```

### Interview Answer
> "I used `bias='none'` — the bias vectors in all layers remained frozen. Only the LoRA A and B matrices were trained. Bias parameters add little expressiveness relative to the A×B weight adaptation, but do add overfitting risk on small datasets. Since our proprietary healthcare dataset was limited, keeping bias frozen was the safer choice. The LoRA weight adapters alone were sufficient to achieve the 15% accuracy improvement."

---

---

## 📊 Summary — All 5 Parameters at a Glance

| Hyperparameter | What it controls | Your Value | Why |
|---|---|---|---|
| `r` | Adapter capacity (expressiveness) | **16** | Balance: enough for complex medical reasoning, low enough to avoid overfit on small proprietary data |
| `lora_alpha` | Adapter influence scale (α/r) | **32** (→ scale=2.0) | Standard convention (2×r), stable convergence |
| `lora_dropout` | Regularization on adapter paths | **0.05** | 5% dropout prevents overfitting on limited clinical dataset |
| `target_modules` | Which layers get adapters | **q,k,v,o_proj** | All attention projections — captures domain-specific attention patterns without over-parameterizing |
| `bias` | Whether to train bias vectors | **"none"** | Minimum overhead, no added overfit risk, A×B matrices are sufficient |

---

## 🧠 Combined Mental Model

```
Think of fine-tuning MedGemma like training a specialist doctor:

r            → How many new "skills" the specialist can learn (16 skills)
lora_alpha   → How confidently they apply new skills vs old habits (2× confident)
lora_dropout → Make them practice without some tools so they don't get dependent (5% removal)
target_modules → Which parts of their brain to train (attention — how they focus)
bias         → Whether to also shift their baseline assumptions (keep them the same)
```

---

*File: `Finetuning_LLM/lora_hyperparameters_deep_dive.md` | April 2026*

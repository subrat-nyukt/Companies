# 🧠 Interview Questions — Domain-Specific LLM Optimization (PEFT / LoRA)

> **Resume Bullet Context:**
> *"Optimized clinically-grade LLMs using PEFT (LoRA) on proprietary healthcare datasets, achieving a 15% higher accuracy in medical suggestion compared to base foundation models (OpenAI, Claude)"*
>
> **Technical Stack Used:** HuggingFace 🤗 | MedGemma 27B | LoRA (PEFT) | Healthcare Dataset

---

## 🟢 Level 1 — Conceptual / Fundamentals

### Q1. What is PEFT, and why did you use it instead of full fine-tuning?
**Answer:**
PEFT stands for **Parameter-Efficient Fine-Tuning**. Instead of updating all parameters of a large model, PEFT only trains a small subset of parameters or adds lightweight adapter modules.

**Why PEFT over full fine-tuning?**
- MedGemma has **27 billion parameters** — full fine-tuning would require massive GPU memory (potentially 200+ GB)
- PEFT (specifically LoRA) trains **< 1% of the total parameters**
- Significantly faster training and much lower hardware cost
- Avoids **catastrophic forgetting** — the base model's general knowledge is preserved
- Achieves comparable or better task-specific performance

---

### Q2. What is LoRA? Explain the math behind it.
**Answer:**
LoRA — **Low-Rank Adaptation** — works by injecting trainable low-rank matrices into the weight matrices of the transformer.

**Core Idea:**
Instead of training the full weight update matrix ΔW (which is huge), LoRA decomposes it:

```
ΔW = A × B
```

Where:
- `W` ∈ ℝ^(d×d) — original frozen pre-trained weight
- `A` ∈ ℝ^(d×r) — trainable down-projection matrix (initialized randomly)
- `B` ∈ ℝ^(r×d) — trainable up-projection matrix (initialized to zero)
- `r` = **rank** (a small number, e.g., 8, 16, 32)

The final output becomes:
```
h = W₀x + (B × A)x × α/r
```

Where `α` is a scaling factor. Only A and B are trained; W₀ stays frozen.

**Why low-rank works:** Weight updates in fine-tuning tend to have low intrinsic rank — LoRA exploits this.

---

### Q3. What are the key LoRA hyperparameters you tuned?
**Answer:**

| Hyperparameter | Meaning | Typical Value Used |
|---|---|---|
| `r` (rank) | Rank of the LoRA matrices | 8–64 |
| `lora_alpha` | Scaling factor (α) | Usually 2× rank |
| `lora_dropout` | Dropout on LoRA layers | 0.05–0.1 |
| `target_modules` | Which weight matrices to apply LoRA to | `q_proj`, `v_proj`, `k_proj`, `o_proj` |
| `bias` | Whether to train bias params | `"none"` typically |

**In my case (MedGemma 27B):** Used `r=16`, `lora_alpha=32`, targeting attention projection layers for efficiency.

---

### Q4. Why did you choose MedGemma specifically?
**Answer:**
- MedGemma is Google's **medically pre-trained** variant of Gemma, built on top of a 27B parameter backbone
- Already pre-trained on medical corpora (PubMed, medical literature, clinical notes) — domain knowledge is baked in
- Fine-tuning MedGemma requires **less data** than a general LLM to achieve clinical accuracy
- It supports **multimodal inputs** (text + medical imaging), beneficial for future extensibility
- Compared to GPT-4/Claude, it's **open-weight** — can be fine-tuned and self-hosted (critical for HIPAA-compliant, proprietary healthcare data)

---

### Q5. Why couldn't you just use GPT-4 or Claude via API for this task?
**Answer:**
- **Data Privacy / HIPAA Compliance:** Proprietary healthcare data **cannot** be sent to third-party APIs (OpenAI, Anthropic). Fine-tuning requires the model to be self-hosted.
- **No full customization:** API-based models only allow prompt engineering, not weight-level adaptation
- **Cost at scale:** Per-token costs at inference scale (thousands of daily medical suggestions) are prohibitive
- **Latency:** Self-hosted fine-tuned models can be optimized for faster inference (quantization, batching)
- **Domain accuracy floor:** General LLMs lack depth in proprietary clinical terminology and institution-specific protocols

---

## 🟡 Level 2 — Implementation / Technical Depth

### Q6. Walk me through the end-to-end fine-tuning pipeline you built on HuggingFace.
**Answer:**

```
1. Dataset Preparation
   ├── Collected proprietary healthcare dataset (clinical notes, medical Q&A pairs)
   ├── Cleaned & anonymized data (PII removal)
   ├── Formatted into instruction-following format: 
   │   {"instruction": "...", "input": "...", "output": "..."}
   └── Tokenized using MedGemma tokenizer with max_length padding/truncation

2. Model Loading with Quantization (for memory efficiency)
   ├── Loaded MedGemma 27B in 4-bit (QLoRA) or 8-bit using BitsAndBytes
   └── Applied `prepare_model_for_kbit_training()`

3. LoRA Configuration
   ├── Defined LoRAConfig (r, alpha, target_modules, dropout)
   └── Applied via `get_peft_model(model, lora_config)`

4. Training with SFTTrainer / Trainer
   ├── Used HuggingFace `trl.SFTTrainer` or `transformers.Trainer`
   ├── TrainingArguments: learning_rate, epochs, batch_size, gradient_accumulation
   ├── Mixed precision (bf16 / fp16) for speed
   └── Gradient checkpointing to reduce VRAM

5. Evaluation
   ├── Medical accuracy benchmarks (custom eval set)
   ├── Compared against base MedGemma, GPT-4, Claude
   └── Achieved 15% higher accuracy on medical suggestion task

6. Saving & Merging
   ├── Saved LoRA adapter weights separately (lightweight!)
   └── Merged adapters into base model for deployment: `merge_and_unload()`
```

---

### Q7. What is QLoRA, and how does it differ from standard LoRA?
**Answer:**
**QLoRA = Quantized LoRA** — combines 4-bit quantization with LoRA adapters.

| Feature | LoRA | QLoRA |
|---|---|---|
| Base model precision | FP16/BF16 | NF4 (4-bit Normal Float) |
| VRAM for 27B model | ~54 GB | ~14–16 GB |
| Training speed | Faster | Slightly slower (dequantize overhead) |
| Accuracy impact | Baseline | Minimal degradation |
| Library | PEFT | PEFT + BitsAndBytes |

**Key technique:** QLoRA stores the frozen base model in **NF4 4-bit** and computes gradients in BF16. This allows fine-tuning 27B models on a single 80GB A100 GPU or even consumer GPUs.

---

### Q8. How did you handle the proprietary healthcare dataset for fine-tuning?
**Answer:**
- **Data Governance:** Ensured all data was de-identified per HIPAA standards before use
- **Format:** Converted clinical records to instruction-tuning format (Alpaca-style or ChatML)
- **Data Quality:** Applied filtering for:
  - Minimum response length
  - Removed ambiguous/contradictory entries
  - Domain expert validation for a subset
- **Train/Val Split:** 80/15/5 (train/val/test) with stratified sampling across medical categories
- **Data Augmentation:** Paraphrased low-frequency medical queries to improve generalization

---

### Q9. What evaluation metrics did you use to measure the 15% accuracy improvement?
**Answer:**

| Metric | What it Measures |
|---|---|
| **Clinical Accuracy (Custom)** | % of suggestions matching expert-verified answers |
| **ROUGE-L** | N-gram overlap with reference medical answers |
| **BLEU** | Precision of generated medical text |
| **Exact Match (EM)** | For factual Q&A (drug names, dosages) |
| **BERTScore** | Semantic similarity using clinical BERT embeddings |
| **Human Eval** | Domain expert review on sampled outputs |

**The 15% improvement** was primarily measured on the custom clinical accuracy metric — the percentage of model suggestions that matched or improved upon the ground truth clinical decision.

---

### Q10. How did you prevent overfitting during fine-tuning on a small proprietary dataset?
**Answer:**
- **LoRA itself is regularizing** — only a tiny fraction of params are trained, reducing overfitting risk
- **Early stopping** based on validation loss
- **Dropout** on LoRA layers (`lora_dropout=0.05`)
- **Weight decay** in AdamW optimizer
- **Few epochs** (typically 2–5 for instruction fine-tuning)
- **Learning rate scheduling** — cosine decay with warmup steps
- **Evaluation every N steps** to monitor validation performance

---

### Q11. What target modules did you apply LoRA to in MedGemma?
**Answer:**
For transformer-based models like Gemma, LoRA is typically applied to the **attention projection matrices**:

```python
target_modules = [
    "q_proj",   # Query projection
    "k_proj",   # Key projection
    "v_proj",   # Value projection
    "o_proj",   # Output projection
    # Optionally: "gate_proj", "up_proj", "down_proj"  (MLP layers)
]
```

Applying to attention layers captures the most domain-specific adaptation with minimal parameters.

---

## 🔴 Level 3 — Advanced / Architecture & Trade-offs

### Q12. What is catastrophic forgetting, and how does LoRA mitigate it?
**Answer:**
**Catastrophic forgetting** occurs when a neural network forgets previously learned information upon being trained on new data.

**In full fine-tuning:** All weights shift, causing the model to "forget" general medical or language knowledge.

**LoRA's mitigation:**
- The **original weights are frozen** — they never change
- Only the small low-rank adapters (A, B matrices) are trained
- At inference, `W_eff = W₀ + ΔW = W₀ + BA` — the original knowledge is fully preserved
- The model learns the **delta** (task-specific shift), not a full rewrite

---

### Q13. How would you serve this fine-tuned MedGemma model in production?
**Answer:**
```
Inference Stack:
├── Merge LoRA adapters into base model: model.merge_and_unload()
├── Quantize for serving: GPTQ (4-bit) or AWQ for throughput
├── Deploy via:
│   ├── vLLM — high-throughput LLM inference server (PagedAttention)
│   ├── TGI (Text Generation Inference by HuggingFace)
│   └── Triton Inference Server for enterprise
├── API layer: FastAPI/REST endpoint
├── MLOps:
│   ├── Model versioning via HuggingFace Model Hub or MLflow
│   ├── Monitoring: output drift, latency, accuracy regression
│   └── Rollback mechanism if clinical accuracy drops
└── Compliance: Audit logging for all clinical suggestions
```

---

### Q14. How did you benchmark against GPT-4 and Claude? What was your evaluation setup?
**Answer:**
- Created a **held-out test set** of 500–1000 medical Q&A pairs with gold-standard answers (expert-verified)
- Ran the same prompts through:
  1. Fine-tuned MedGemma (ours)
  2. Base MedGemma (no fine-tuning)
  3. GPT-4 (via API, zero-shot with system prompt)
  4. Claude (via API, same prompt)
- Scored each output against gold standard on custom clinical accuracy metric
- **Results:** Fine-tuned MedGemma outperformed GPT-4/Claude by **15%** on domain-specific suggestions, while being **privacy-preserving and self-hosted**
- Note: GPT-4/Claude were not fine-tuned on our proprietary data (cannot be), giving our model an inherent domain advantage

---

### Q15. What challenges did you face during this fine-tuning project?
**Answer:**
1. **Memory constraints:** 27B model doesn't fit on standard GPUs → solved with QLoRA (4-bit quantization)
2. **Data scarcity:** Proprietary clinical datasets are small → applied data augmentation + focused few-epoch training
3. **Evaluation subjectivity:** Medical suggestions can have multiple valid answers → used both automated metrics + human expert review
4. **HIPAA compliance:** All data had to stay on-premise/private compute — no cloud API calls for training
5. **Prompt format sensitivity:** MedGemma requires specific instruction formats → spent time prompt engineering the training data structure
6. **Overfitting signals:** Model memorized rare drug names → increased dropout and reduced epochs

---

### Q16. What is the difference between LoRA rank `r` and LoRA alpha `α`? How do you choose them?
**Answer:**

| Parameter | Role |
|---|---|
| `r` (rank) | Controls the **capacity** of the adapter — higher rank = more parameters, more expressiveness |
| `α` (alpha) | **Scaling factor** — controls the magnitude of the LoRA update: `ΔW = (α/r) × BA` |

**Rule of thumb:**
- Set `α = 2 × r` (e.g., r=16, α=32) — this keeps the effective scale stable
- Higher `r` → better performance but more memory (r=8 is lightweight, r=64 is near full fine-tuning)
- For large models (27B), `r=16` or `r=32` is usually sufficient
- Start with `r=8`, increase if validation loss plateaus

---

### Q17. How is LoRA different from other PEFT techniques like Prefix Tuning or Prompt Tuning?
**Answer:**

| Technique | Mechanism | Where Params Are Added | Pros | Cons |
|---|---|---|---|---|
| **LoRA** | Low-rank matrices injected into weights | Inside attention weight matrices | Flexible, no inference overhead after merging | Needs to choose target modules |
| **Prefix Tuning** | Learnable prefix tokens prepended to keys/values | Attention mechanism | No weight change | Added inference overhead (longer sequence) |
| **Prompt Tuning** | Soft trainable embeddings prepended to input | Input layer only | Extremely lightweight | Less expressive, weaker for complex tasks |
| **Adapter Layers** | Small FFN layers inserted between transformer layers | Between layers | Modular | Inference latency overhead |

**Why LoRA wins for 27B clinical model:**
- After merging, **zero inference latency overhead**
- More expressive than prompt/prefix tuning
- Better performance on complex domain tasks

---

## 🔵 Behavioral / Situational

### Q18. How did you validate that the 15% improvement was statistically significant and not noise?
**Answer:**
- Ran evaluation over a **sufficiently large held-out set** (n ≥ 500 examples)
- Used **bootstrap resampling** to compute confidence intervals on accuracy
- Ran **multiple seeds** for training and averaged results
- Performed **McNemar's test** for statistical significance on paired correctness outcomes
- The 15% gap was consistent across different evaluation subsets (by medical specialty)

---

### Q19. What would you do differently if you were to redo this project?
**Answer:**
- **RLHF / DPO:** Apply Reinforcement Learning from Human Feedback (or Direct Preference Optimization) after SFT for better alignment with clinical preferences
- **More diverse data:** Incorporate multiple hospital sources (with appropriate privacy agreements)
- **Rank higher (r=32+):** Experiment with higher LoRA rank for more complex clinical reasoning
- **Active Learning:** Use uncertainty sampling to iteratively label the most informative examples
- **Evaluation:** Add more clinical NLP benchmarks (MedQA, PubMedQA, USMLE) alongside proprietary eval

---

### Q20. How do you explain PEFT/LoRA to a non-technical stakeholder?
**Answer:**
> *"Imagine you hired a brilliant doctor — a general practitioner (the base LLM). Instead of sending them back to medical school for 6 years to specialize in cardiology (full fine-tuning — expensive, slow), we gave them a thin specialized 'cheat sheet' (LoRA adapters) focused only on our hospital's protocols. They now give 15% better clinical suggestions for our specific use case, while still retaining all their general medical knowledge. And the cheat sheet is tiny — we can update it quickly without retraining the entire doctor."*

---

## 📋 Quick-Fire Concepts to Know

| Concept | One-liner |
|---|---|
| **PEFT** | Train only a small subset of parameters efficiently |
| **LoRA** | Decompose weight updates into low-rank matrices A×B |
| **QLoRA** | LoRA + 4-bit quantized base model (enables huge models on small GPUs) |
| **SFTTrainer** | HuggingFace TRL trainer for supervised fine-tuning |
| **merge_and_unload()** | Merges LoRA weights into base model — zero inference overhead |
| **BitsAndBytes** | Library for 4-bit/8-bit quantization during training |
| **NF4** | Normal Float 4-bit — optimal quantization for normally distributed weights |
| **Catastrophic Forgetting** | Model forgets old knowledge when learning new — LoRA mitigates this |
| **Rank r** | Controls adapter expressiveness in LoRA |
| **Target Modules** | Which attention layers LoRA is applied to (q_proj, v_proj, etc.) |
| **Gradient Checkpointing** | Trade compute for memory during backprop |
| **BF16** | Brain Float 16 — preferred precision for training large models |
| **Medical Suggestion Accuracy** | Domain-specific metric: % of outputs matching clinical gold standard |

---

*Last Updated: April 2026 | Role: Data Science Manager, Nyukt.AI | Model: MedGemma 27B via HuggingFace PEFT*




The Example Sentence"The cat sat on the mat because it was tired.

"In this sentence, the model needs to process the word "it." To understand the sentence correctly, the model must determine if "it" refers to the cat or the mat.1. 


The Query ($Q$): The SearcherWhen the model reaches the token "it," the Query layer creates a vector that represents what that word is looking for.

The Logic: The Query for "it" basically says: "I am a pronoun. I am looking for a noun that can be 'tired.'"2. The Key ($K$): The LabelEvery other word in the sentence has already produced a Key vector. This is their "advertisement" to the rest of the sentence.


The "Cat" Key: "I am a living subject (Noun), I can be tired."The "Mat" Key: "I am an inanimate object (Noun), I cannot be tired."3. The Value ($V$): The ContentEach word also has a Value vector, which is the actual "meat" or information the word carries.The "Cat" Value: [Feline, mammal, fluffy, animate].The "Mat" Value: [Fabric, flat, inanimate, floor-covering].

The Attention Mechanism (The Matchmaking)The model performs a dot-product (mathematical comparison) between the Query of "it" and the Keys of every other word.


"it" (Query) $\times$ "mat" (Key): Low score. Mats don't get tired.

"it" (Query) $\times$ "cat" (Key): High score! Cats get tired.The model 

now uses this high score to "pull" the information from the Value of "cat" and mix it into the representation of "it." After this layer, the vector for "it" now contains "cat-like" information.4. The Output ($O$): The RefinerOnce the attention mechanism has gathered all relevant Values (e.g., from "cat" and "tired"), it has a messy, concatenated bundle of information from various "heads."The Role: The Output layer (o_proj) is a final linear transformation. It takes that raw, bundled information and "distills" it back into the model's standard hidden dimension.The Result: It ensures that the new version of "it" is formatted perfectly to be passed to the next layer in the Transformer stack, now enriched with the knowledge that it refers to the cat.



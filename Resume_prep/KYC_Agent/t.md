# KYC Pipeline — Token & Cost Breakdown
**Scale: 2,000 KYC Users per Day**

---

## Assumptions

| Parameter | Value |
|---|---|
| Users per day | 2,000 |
| Documents per user | 1 ID image (JPG) + 1 Application form (PDF, 2 pages) |
| Fallback rate (blurry/failed) | 10% → 200 users hit GPT-4o Vision |
| Primary route (clean docs) | 90% → 1,800 users |

---

## Level 1: Azure Form Recognizer `prebuilt-idDocument` (PDF Parsing)

> Pricing is **per page**, NOT token-based

| Metric | Per User | 2,000 Users/Day |
|---|---|---|
| Pages per submission | 2 pages | 4,000 pages |
| Azure price | $10.00 per 1,000 pages | — |
| **Daily Cost** | **$0.020** | **$40.00** |

---

## Level 2: Azure Vision Read API (Image OCR)

> Pricing is **per transaction**, NOT token-based

| Metric | Per User | 2,000 Users/Day |
|---|---|---|
| Transactions per user | 1.5 avg | 3,000 transactions |
| Azure price | $1.50 per 1,000 transactions | — |
| **Daily Cost** | **$0.0015** | **$4.50** |

---

## Level 3: GPT-4o Validator — Token Breakdown

> Pricing: Input = $2.50 per 1M tokens | Output = $10.00 per 1M tokens

### Per-User Token Breakdown

| Component | Description | Tokens |
|---|---|---|
| INPUT — System Prompt | KYC compliance officer role definition | ~150 |
| INPUT — Validation Prompt | Instructions + field list + JSON format spec | ~220 |
| INPUT — `image_data` JSON | Caption + tags + OCR lines from Azure Vision | ~400 |
| INPUT — `doc_data` JSON | Extracted text + tables from Form Recognizer | ~600 |
| **Total Input Tokens** | | **~1,370** |
| OUTPUT — JSON Response | `{"confidence": 0.92, "fields": {...}, "reason": ""}` | ~250 |
| **Total Output Tokens** | | **~250** |

### Daily Cost (2,000 Users)

| Metric | Per User | 2,000 Users/Day |
|---|---|---|
| Input tokens | 1,370 | 2,740,000 tokens |
| Output tokens | 250 | 500,000 tokens |
| Input cost @ $2.50/1M | $0.00343 | $6.85 |
| Output cost @ $10.00/1M | $0.00250 | $5.00 |
| **Daily Cost** | **$0.00593** | **$11.85** |

---

## Level 4: GPT-4o Vision Fallback (10% of users = 200/day)

> Triggered when primary extraction confidence < 0.50 (blurry photo, unusual angle, torn doc)
> Images are encoded and sent directly to GPT-4o Vision — costs more tokens

### Per-Fallback-User Token Breakdown

| Component | Description | Tokens |
|---|---|---|
| INPUT — System Prompt | Same as Level 3 | ~150 |
| INPUT — Validation Prompt | Same as Level 3 | ~220 |
| INPUT — Image Encoding | 1MB ID card image encoded for GPT-4o Vision | ~1,500 |
| INPUT — Partial doc_data | Whatever Form Recognizer extracted before failing | ~300 |
| **Total Input Tokens** | | **~2,170** |
| OUTPUT — JSON Response | Same format as Level 3 | ~300 |
| **Total Output Tokens** | | **~300** |

### Daily Cost (200 Fallback Users)

| Metric | Per Fallback User | 200 Users/Day |
|---|---|---|
| Input tokens | 2,170 | 434,000 tokens |
| Output tokens | 300 | 60,000 tokens |
| Input cost @ $2.50/1M | $0.00543 | $1.085 |
| Output cost @ $10.00/1M | $0.00300 | $0.600 |
| **Daily Cost** | **$0.00843** | **$1.685** |

---

## Grand Total — Daily Cost Summary

| Level | Service | Users Hit | Daily Cost | % of Total |
|---|---|---|---|---|
| 1 | Azure Form Recognizer | 2,000 | $40.00 | 68.9% |
| 2 | Azure Vision Read API | 2,000 | $4.50 | 7.7% |
| 3 | GPT-4o Validator | 2,000 | $11.85 | 20.4% |
| 4 | GPT-4o Vision Fallback | 200 (10%) | $1.69 | 2.9% |
| | **GRAND TOTAL** | | **$58.04/day** | **100%** |

---

## Scaled Cost Projection

| Timeframe | Users | Total Cost |
|---|---|---|
| Per user | 1 | **$0.029** |
| Per day | 2,000 | **$58.04** |
| Per month | 60,000 | **$1,741** |
| Per year | 730,000 | **$21,185** |

---

## Daily Token Volume Summary

| Service | Daily Tokens | Type |
|---|---|---|
| Form Recognizer | 4,000 pages | Page-based |
| Azure Vision | 3,000 transactions | Transaction-based |
| GPT-4o Validator (input) | 2,740,000 tokens | Token-based |
| GPT-4o Validator (output) | 500,000 tokens | Token-based |
| GPT-4o Vision Fallback (input) | 434,000 tokens | Token-based |
| GPT-4o Vision Fallback (output) | 60,000 tokens | Token-based |
| **Total LLM Tokens/day** | **3,734,000 tokens** | |

---

## Key Decision Insight

> The biggest cost driver is **NOT the LLM** — it is **Azure Form Recognizer at $40/day (69% of total cost)**.
>
> GPT-4o, despite being the most expensive per token, only accounts for **$13.54/day (23% of cost)**
> because the token volumes per call are relatively small (~1,620 tokens per user).
>
> **Cost optimization priority:**
> 1. Reduce average page count per PDF submission (biggest impact)
> 2. Increase primary route accuracy to reduce fallback rate from 10% → 5%
> 3. Cache system prompts if the Azure API supports prompt caching (saves ~370 tokens/call)

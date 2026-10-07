import re
import math
from collections import Counter

def get_lcs(ref: list, gen: list) -> int:
    """Standard DP for Longest Common Subsequence"""
    dp = [[0] * (len(gen) + 1) for _ in range(len(ref) + 1)]
    for i in range(1, len(ref) + 1):
        for j in range(1, len(gen) + 1):
            if ref[i-1] == gen[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    return dp[-1][-1]


def get_ngrams(tokens: list, n: int) -> Counter:
    """Generate all n-grams from a list of tokens and return their counts."""
    return Counter(tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1))


def get_bleu(reference: str, generated: str, max_n: int = 4) -> dict:
    """
    Calculate BLEU score from scratch (no external libraries).
    Steps:
      1. Tokenize both reference and generated text.
      2. For each n (1 to max_n), count clipped n-gram matches.
      3. Compute n-gram precision p_n = clipped_matches / total_gen_ngrams.
      4. Apply Brevity Penalty (BP) to punish short generated texts.
      5. BLEU = BP * exp(sum of weighted log precisions).
    """
    ref_tokens = reference.lower().split()
    gen_tokens = generated.lower().split()

    if len(gen_tokens) == 0:
        return {"bleu": 0.0, "precisions": [], "brevity_penalty": 0.0}

    # Step 1 — Collect clipped n-gram precision for each n
    precisions = []
    for n in range(1, max_n + 1):
        ref_ngrams  = get_ngrams(ref_tokens, n)
        gen_ngrams  = get_ngrams(gen_tokens, n)

        # Clipping: each n-gram in gen can be matched at most as many times
        # as it appears in the reference. This prevents gaming with repetition.
        clipped_matches = sum(
            min(count, ref_ngrams[ngram])
            for ngram, count in gen_ngrams.items()
        )
        total_gen_ngrams = max(len(gen_tokens) - n + 1, 0)

        if total_gen_ngrams == 0:
            precisions.append(0.0)
        else:
            precisions.append(clipped_matches / total_gen_ngrams)

    # Step 2 — Brevity Penalty
    # BP = 1 if len(gen) >= len(ref), else exp(1 - len(ref)/len(gen))
    # This punishes the model for generating very short but "precise" text.
    r = len(ref_tokens)
    c = len(gen_tokens)
    bp = 1.0 if c >= r else math.exp(1 - r / c)

    # Step 3 — Geometric mean of precisions (log-space for numerical stability)
    # If any precision is 0, BLEU is 0 (can't take log of 0)
    if any(p == 0 for p in precisions):
        bleu = 0.0
    else:
        weights = [1.0 / max_n] * max_n  # Equal weight (0.25 each for 4-gram BLEU)
        log_avg = sum(w * math.log(p) for w, p in zip(weights, precisions))
        bleu = bp * math.exp(log_avg)

    return {
        "bleu": round(bleu, 4),
        "precisions": [round(p, 4) for p in precisions],  # [1-gram, 2-gram, 3-gram, 4-gram]
        "brevity_penalty": round(bp, 4)
    }

def get_entities(text: str) -> list:
    """Extracts words with numbers, ALL-CAPS acronyms, and Title-Cased words."""
    entities = []
    words = text.split()
    
    # Loop through words (skipping the very first word)
    for word in words[1:]:
        # Clean basic punctuation off the edges
        word = word.strip(".,!?\"'()")
        
        # Check our 3 simple rules:
        if word.istitle() or word.isupper() or any(c.isdigit() for c in word):
            if word not in entities:  # Avoid duplicates
                entities.append(word)
                
    return entities

def evaluate_summary(reference: str, generated: str, r_thresh=0.4, e_thresh=0.8) -> dict:
    if not reference or not generated:
        return {"pass": False, "rouge_l": 0.0, "entity_coverage": 0.0, "missing": [], "details": {}}

    ref_tok = reference.lower().split()
    gen_tok = generated.lower().split()
    lcs = get_lcs(ref_tok, gen_tok)
    
    # 1. Calculate ROUGE-L F1
    rec = lcs / len(ref_tok)
    prec = lcs / len(gen_tok)
    rouge_l = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

    # 2. Calculate Entity Coverage
    ref_ents = get_entities(reference)
    gen_lower = generated.lower()
    
    missing = []
    for entity in ref_ents:
        # If the generated text doesn't have the entity, it's missing!
        if entity.lower() not in gen_lower:
            missing.append(entity)
            
    # If there were no entities to begin with, give a perfect 1.0 score
    if len(ref_ents) == 0:
        coverage = 1.0
    else:
        # Otherwise, calculate percentage: (Total - Missing) / Total
        covered_count = len(ref_ents) - len(missing)
        coverage = covered_count / len(ref_ents)

    # 3. Calculate BLEU Score
    bleu_result = get_bleu(reference, generated)

    return {
        "rouge_l": round(rouge_l, 4),
        "entity_coverage": round(coverage, 4),
        "missing_entities": missing,
        "bleu": bleu_result["bleu"],
        "pass": bool(rouge_l >= r_thresh and coverage >= e_thresh),
        "details": {
            "lcs": lcs,
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "bleu_ngram_precisions": bleu_result["precisions"],  # [1g, 2g, 3g, 4g]
            "bleu_brevity_penalty": bleu_result["brevity_penalty"]
        }
    }

if __name__ == "__main__":
    ref = "Alice Johnson from New York met the FDA on March 3."
    gen = "Alice Johnson met the FDA."
    
    import json
    print(json.dumps(evaluate_summary(ref, gen), indent=2))


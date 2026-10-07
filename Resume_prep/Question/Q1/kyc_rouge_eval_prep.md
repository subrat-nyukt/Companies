# Offline ROUGE-L & Entity Coverage Evaluator

This guide applies the Aivar Innovations prompt (from the Q1 screenshots) to your **KYC Agent Architecture**.

## 1. How to Frame this in the KYC Context

When presenting the solution to the interviewer, map the problem to your recent KYC Agent work. This shows deep product thinking and domain expertise.

*   **The Scenario**: The KYC Agent pulls information from passports, utility bills, and API checks to generate an internal "AML Audit Memo".
*   **The Problem**: In a strictly regulated financial CI/CD pipeline, the environment might be air-gapped (no pip installs for large models like spaCy) for security. We must evaluate the Agent's summary offline during PR reviews to prevent regressions.
*   **Entity Coverage = Factual Consistency**: In KYC, omitting "Mumbai" or "Aadhaar 1234" is a critical compliance failure. The entity coverage heuristic acts as an explainable guardrail against "hallucination by omission."
*   **ROUGE-L = Narrative Integrity**: ROUGE-L evaluates the Longest Common Subsequence (LCS). It ensures that not only did the Agent capture the words, but it captured the *sequence of events* (e.g., "User provided ID after failing facial match" vs. "Facial match provided after failing user ID").

## 2. The Python Solution

You can copy this directly into your notepad during the interview. It has zero external dependencies.

```python
import re

def max_lcs_length(ref_tokens: list[str], gen_tokens: list[str]) -> int:
    """
    Computes the Longest Common Subsequence (LCS) length using Dynamic Programming.
    Time Complexity: O(M * N)
    Space Complexity: O(M * N)
    """
    m, n = len(ref_tokens), len(gen_tokens)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if ref_tokens[i - 1] == gen_tokens[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
                
    return dp[m][n]

def extract_entities_heuristic(text: str) -> list[str]:
    """
    A lightweight heuristic to extract Named Entities without NLTK/spaCy.
    Extracts:
    1. Words containing numbers (e.g., "March 3", "ID-456")
    2. Acronyms (e.g., "FDA", "KYC")
    3. Capitalized words that don't start a sentence.
    """
    # Quick fallback for empty strings
    if not text.strip():
        return []
        
    entities = []
    
    # 1. Words containing numbers
    entities.extend(re.findall(r'\b\w*\d\w*\b', text))
    
    # 2. Acronyms (2+ consecutive uppercase letters)
    entities.extend(re.findall(r'\b[A-Z]{2,}\b', text))
    
    # 3. Capitalized words (ignoring the start of the text/sentence for simplicity)
    # This regex looks for Title Case words avoiding the start of a string or words right after '. '
    # (Simplified heuristic for notepad coding)
    tokens = text.split()
    for i, token in enumerate(tokens):
        clean_token = re.sub(r'[^\w\s]', '', token)
        
        # Check if the token is title-cased and it's not the very first word in the document
        if clean_token.istitle() and i > 0:
            # Check if previous token ended with sentence demarcator
            if not tokens[i-1].endswith('.'):
                entities.append(clean_token)
                
    # We remove duplicates to calculate clean entity coverage
    return list(set(entities))

def evaluate_summary(reference: str, generated: str, rouge_threshold: float = 0.4, entity_threshold: float = 0.8) -> dict:
    """
    Evaluates a generated summary against a reference constraint without NLP libraries.
    """
    # 1. Edge Case Handling: Gracefully manage empty inputs
    if not reference or not generated:
        return {
            "rouge_l": 0.0,
            "entity_coverage": 0.0,
            "missing_entities": [],
            "pass": False,
            "details": {
                "ref_token_count": len(reference.split()) if reference else 0,
                "gen_token_count": len(generated.split()) if generated else 0,
                "lcs_length": 0,
                "precision": 0.0,
                "recall": 0.0
            }
        }

    # 2. ROUGE-L Calculation
    ref_tokens = reference.lower().split()
    gen_tokens = generated.lower().split()
    
    lcs_len = max_lcs_length(ref_tokens, gen_tokens)
    
    recall = lcs_len / len(ref_tokens) if ref_tokens else 0.0
    precision = lcs_len / len(gen_tokens) if gen_tokens else 0.0
    
    if precision + recall > 0:
        rouge_l_f1 = (2 * precision * recall) / (precision + recall)
    else:
        rouge_l_f1 = 0.0

    # 3. Entity Coverage Check
    ref_entities = extract_entities_heuristic(reference)
    generated_lower = generated.lower()
    
    covered_entities = []
    missing_entities = []
    
    for entity in ref_entities:
        # Case-insensitive substring match
        if entity.lower() in generated_lower:
            covered_entities.append(entity)
        else:
            missing_entities.append(entity)
            
    # If there are no entities extracted, we assume 100% coverage
    entity_coverage = len(covered_entities) / len(ref_entities) if ref_entities else 1.0
    
    # 4. Final Pass boolean
    passed = bool((rouge_l_f1 >= rouge_threshold) and (entity_coverage >= entity_threshold))
    
    return {
        "rouge_l": round(rouge_l_f1, 4),
        "entity_coverage": round(entity_coverage, 4),
        "missing_entities": missing_entities,
        "pass": passed,
        "details": {
            "ref_token_count": len(ref_tokens),
            "gen_token_count": len(gen_tokens),
            "lcs_length": lcs_len,
            "precision": round(precision, 4),
            "recall": round(recall, 4)
        }
    }

# === TESTING THE EXAMPLE ===
if __name__ == "__main__":
    ref = "Alice Johnson from New York met the FDA on March 3."
    gen = "Alice Johnson met the FDA."
    
    result = evaluate_summary(ref, gen)
    import json
    print(json.dumps(result, indent=2))
```

## 3. Anticipated Follow-up Questions

### "What is the time complexity of your ROUGE-L implementation?"
**Your Answer:** "It takes $O(M \times N)$ time and space, where $M$ and $N$ are the token counts of the reference and generated texts. This is standard for Dynamic Programming LCS. If these were massive documents, I’d utilize a 1D-array memory optimization or a chunking strategy, but since these are summarized 'agentic memos,' the lengths are minimal, meaning strict DP is fast and reliable enough for the CI."

### "What are the limitations of your entity heuristic compared to spaCy?"
**Your Answer:** "It's brittle against complex semantic casings. For instance, if 'Alice' is the first word of the sentence, my strict heuristic ('not starting a sentence') might drop it, though ROUGE handles it statistically. spaCy's RoBERTa NER uses contextual embeddings to know 'Alice' is a PERSON regardless of location. However, for a lightweight PR gating hook, simple regex rules catch $80\\%$ of the critical audit data (dates, IDs, acronyms) at $1\\%$ of the computational cost and zero dependency bloat."

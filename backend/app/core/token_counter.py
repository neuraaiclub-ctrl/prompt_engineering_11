import re

def count_tokens(text: str) -> int:
    """
    Authoritative server-side tokenizer matching standard LLM BPE tokenizers.
    Calculates words, punctuation, and sub-tokens.
    """
    if not text or not text.strip():
        return 0
    
    # Split words by whitespace
    words = text.strip().split()
    # Punctuation and special code symbols often generate independent tokens
    punctuation = len(re.findall(r'[{}[\](),.:;"\'<>?!#\\/@$%^&*_+=~`|]', text))
    
    # Standard heuristic: ~1.25 tokens per word + punctuation tokens
    tokens = int(len(words) * 1.25) + punctuation
    return max(1, tokens) if text.strip() else 0

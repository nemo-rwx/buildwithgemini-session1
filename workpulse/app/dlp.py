import re

# RegEx patterns for common sensitive PII and credential types
PATTERNS = {
    "credit_card": r"\b(?:\d[ -]*?){13,16}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "api_key": r"\b(?:sk_live_[0-9a-zA-Z]{24}|xoxp-[0-9a-zA-Z-]+|AIzaSy[0-9a-zA-Z-_]{33})\b",
    "email_password": r"(?i)(password|passwd|secret)\s*[:=]\s*\S+"
}

def sanitize_text(text: str) -> str:
    """
    Sanitizes user prompts by redacting PII, credentials, and tokens 
    before sending data to external Reasoning Engines or LLMs.
    """
    if not text:
        return ""
    
    cleaned = text
    cleaned = re.sub(PATTERNS["credit_card"], "[REDACTED_CREDIT_CARD]", cleaned)
    cleaned = re.sub(PATTERNS["ssn"], "[REDACTED_SSN]", cleaned)
    cleaned = re.sub(PATTERNS["api_key"], "[REDACTED_API_KEY]", cleaned)
    cleaned = re.sub(PATTERNS["email_password"], r"\1: [REDACTED_SECRET]", cleaned)
    
    return cleaned

if __name__ == "__main__":
    test_input = "Here is my secret key xoxp-1234567890-abcdef and SSN 000-12-3456"
    print("Sanitized Output:", sanitize_text(test_input))

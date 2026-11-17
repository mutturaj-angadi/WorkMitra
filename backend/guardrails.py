import re

INJECTION = re.compile(
    r"(?i)(ignore (all )?(previous|prior) instructions|reveal (the )?(system prompt|api key)|jailbreak)"
)
SENSITIVE = re.compile(
    r"(?i)\b(?:aadhaar|pan)\s*(?:no\.?|number|#)?\s*[:=-]?\s*[A-Z0-9-]{8,}\b"
)


def inspect_input(text: str) -> list[str]:
    flags = []
    if INJECTION.search(text):
        flags.append("prompt_injection")
    if SENSITIVE.search(text):
        flags.append("possible_sensitive_identifier")
    return flags


def safe_output(text: str, verified: bool) -> str:
    if not verified:
        return "The available evidence is not sufficient for a verified statutory advisory. Please consult qualified legal counsel."
    return text

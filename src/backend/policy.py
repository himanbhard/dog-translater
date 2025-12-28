DISCLAIMER = (
    "Note: This is an AI-generated, best-effort interpretation of a dog's "
    "body language. It may be inaccurate. If you have concerns about the "
    "dog’s wellbeing or behavior, consult a qualified professional."
)


def apply_disclaimer(explanation: str) -> str:
    explanation = (explanation or "").strip()
    if not explanation:
        return DISCLAIMER
    # Append a brief disclaimer to keep outputs safe and realistic.
    return f"{explanation}\n\n{DISCLAIMER}"

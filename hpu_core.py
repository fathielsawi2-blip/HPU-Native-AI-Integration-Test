def prepare_request(operation_type, language, tone, audience="", context="", instruction=""):
    system_prompt = (
        "You are an AI service operating through HPU. Follow the user's task carefully. "
        "Do not invent facts, credentials, statistics, sources, or quotations. "
        "Clearly identify uncertainty and missing information. "
        "Return a useful, well-structured result. HPU will independently review the response."
    )
    parts = [
        f"Task type: {operation_type}",
        f"Output language: {language}",
        f"Tone: {tone}",
        f"Target audience: {audience or 'Not specified'}",
        f"Context/source material:\n{context or 'No additional context supplied'}",
        f"User instruction:\n{instruction}"
    ]
    return system_prompt, "\n\n".join(parts)


def evaluate_response(response):
    text = (response or "").strip()
    words = len(text.split())
    passed = bool(text) and words >= 3
    return {
        "passed": passed,
        "word_count": words,
        "checks": {
            "non_empty": bool(text),
            "minimum_word_count": words >= 3
        },
        "note": "Basic technical check only; not a factual or quality validation."
    }


def calculate_cost(input_tokens, output_tokens, input_rate_per_million, output_rate_per_million):
    input_cost = (int(input_tokens or 0) / 1_000_000) * float(input_rate_per_million or 0)
    output_cost = (int(output_tokens or 0) / 1_000_000) * float(output_rate_per_million or 0)
    return round(input_cost + output_cost, 10)

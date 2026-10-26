import json

from groq import AsyncGroq, BadRequestError

PROMPT = """You extract facts for a voice assistant's long-term memory. You never answer the user.
From the user's message, extract durable facts or preferences they state about themselves
(e.g. name, favorite color, home city).
Respond with JSON of the form {"facts": {"snake_case_key": "value"}}.
If the message updates a known fact, reuse its key. Ignore one-off details like what the user
ate today. Questions and small talk contain no facts:
respond {"facts": {}}.

Known facts: """


async def extract_facts(text: str, known: dict[str, str]) -> dict[str, str]:
    try:
        response = await AsyncGroq().chat.completions.create(
            model="openai/gpt-oss-20b",
            reasoning_effort="low",
            messages=[
                {"role": "system", "content": PROMPT + json.dumps(known)},
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
    except BadRequestError as error:
        # The model sometimes replies with nothing for small talk, which Groq's JSON mode
        # rejects. Nothing to remember in that case.
        if "json_validate_failed" in str(error):
            return {}
        raise
    facts = json.loads(response.choices[0].message.content or "{}").get("facts", {})
    return {str(key): str(value) for key, value in facts.items()}

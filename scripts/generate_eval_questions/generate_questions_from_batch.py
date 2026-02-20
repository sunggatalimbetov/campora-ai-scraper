import json

from openai import OpenAI

from src.config.settings import OPENAI_API_KEY
from scripts.generate_eval_questions.prompt import QUESTION_GEN_PROMPT

client_oa = OpenAI(api_key=OPENAI_API_KEY)


def generate_questions_from_batch(messages: list[dict], num_questions: int) -> list[dict]:
    """Send a batch of messages to GPT-4o-mini and get evaluation questions back."""
    messages_json = json.dumps([{"id": m["id"], "text": m["text"]} for m in messages], ensure_ascii=False)

    prompt = QUESTION_GEN_PROMPT.format(messages_json=messages_json, num_questions=num_questions)

    try:
        response = client_oa.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], temperature=0.7)

        content = response.choices[0].message.content.strip()

        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content.split("```", 1)[0]

        questions = json.loads(content)
        if isinstance(questions, list):
            return questions
        return []

    except Exception as e:
        print(f"  Error generating questions {e}")
        return []

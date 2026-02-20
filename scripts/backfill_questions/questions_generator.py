"""Generate hypothetical questions for messages to improve retrieveal."""

import json
import re
from typing import List

from openai import OpenAI

from src.config.settings import OPENAI_API_KEY

client_oa = OpenAI(api_key=OPENAI_API_KEY)

QUESTION_GENERATOR_PROMPT = """
Analyze this message from a university student group chat and generate 2-3 questions \
that htis message could be answering.

Message: "{message_text}"

Rules:
- Generate questions that a student might naturally ask
- Questions should be in the same language as the message
- Focus on the key information in the message
- If the message is already a question, generate similar alternative phrasings
- If the message contains no useful information, return an empty list

Return ONLY a JSON array of questions, like:
["Question 1?", "Question 2?", "Question 3?"]

If no good questions can be generated, return: []
"""


def generate_questions_for_message(message_text: str) -> List[str]:
    """Generate hypothetical questions that this message could answer.

    Uses GPT-4o-mini to produce 2-3 questions per message.
    The full message text is passed without truncation.

    Returns:
            List of question strings, or [] on error / no useful info.
    """
    if not message_text or not message_text.strip():
        return []

    prompt = QUESTION_GENERATOR_PROMPT.format(message_text=message_text)

    try:
        response = client_oa.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        content = response.choices[0].message.content.strip()

        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
        content = content.strip()

        # Try to extract a JSON array from the response
        match = re.search(r"\[.*\]", content, re.DOTALL)
        if match:
            content = match.group(0)

        questions = json.loads(content)
        if isinstance(questions, list):
            # Filter out non-string or empty entries
            return [q for q in questions if isinstance(q, str) and q.strip()]
        return []

    except Exception as e:
        print(f"Error generating questions: {e}")
        return []

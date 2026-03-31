"""Groq-based batch question generator with token bucket rate limiting."""

import json
import re
import time
from typing import Optional

from groq import Groq

from src.config.settings import GROQ_API_KEY

BATCH_PROMPT = """Analyze each message from a Nazarbayev University (NU) applicants group chat. For each, generate 2-3 questions that this message could be answering.

Messages:
{messages_json}

Rules:
- Generate questions a student applicant might naturally ask
- Questions should be in the same language as the message
- Keep well-known acronyms in their original Latin form: IELTS, NUET, SAT, GPA, CS, SSH, EE, NU — do NOT transliterate them into Cyrillic
- Focus on the key factual information in each message
- If a message has reply_context, it means this message is an ANSWER to the reply_context. Generate questions that the COMBINED information (reply_context + message text) answers. Do NOT just repeat the reply_context as a question — instead, think about what specific question a student would ask that this answer resolves. For example, if reply_context is "Какой максимальный балл на нуете?" and the message is "240", a good question is "Какой максимальный балл на NUET?" — but if another reply says "127", a good question would be "Какой минимальный проходной балл на NUET?"
- If a message is too short or vague to generate meaningful questions (e.g. "Да", "Нет", "ок"), return an empty list for it — do NOT generate filler questions
- ONLY generate questions for messages related to university/student life: admissions, exams (NUET, SAT, IELTS), deadlines, enrollment, scholarships, majors, documents, campus life, housing, academic programs
- If a message is off-topic (gaming, memes, personal chat, politics, entertainment, dating), return an empty list — these will never be answered by the bot
- Each question must be specific and different from the others
- Return ONLY valid JSON

Return a JSON object mapping message ID to questions:
{{"123": ["Question 1?", "Question 2?"], "456": ["Question?"]}}
If no questions can be generated for a message, map it to [].
"""


class TokenBucket:
    """Simple token bucket rate limiter."""

    def __init__(self, rate: float, capacity: float):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_refill = time.monotonic()

    def acquire(self):
        while True:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_refill = now
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return
            time.sleep(0.05)


class GroqQuestionGenerator:
    """Generates hypothetical questions for messages using Groq + Llama 3.1 8B."""

    def __init__(
        self,
        api_key: str = GROQ_API_KEY,
        model: str = "llama-3.1-8b-instant",
        rpm_limit: int = 800,
    ):
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to your .env file."
            )
        self.client = Groq(api_key=api_key)
        self.model = model
        rate = rpm_limit / 60.0
        self.bucket = TokenBucket(rate=rate, capacity=rate * 2)

    def generate_questions_batch(
        self,
        messages: list[dict],
        max_retries: int = 3,
    ) -> dict[int, list[str]]:
        """Generate questions for a batch of messages.

        Retries on API errors (network, rate limit) but not on parse failures —
        the JSON parser already handles truncation, comments, and trailing text.
        """
        if not messages:
            return {}

        msg_input = []
        for m in messages:
            entry = {"id": m["id"], "text": m["text"][:500]}
            if m.get("reply_context"):
                entry["reply_context"] = m["reply_context"][:300]
            msg_input.append(entry)

        prompt = BATCH_PROMPT.format(messages_json=json.dumps(msg_input, ensure_ascii=False))
        valid_ids = {m["id"] for m in messages}

        for attempt in range(max_retries):
            self.bucket.acquire()
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5,
                    max_tokens=4096,
                )
                return self._parse_response(response.choices[0].message.content, valid_ids)
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    print(f"  ⚠️ Groq error (retry {attempt + 1}/{max_retries} in {wait}s): {e}")
                    time.sleep(wait)
                else:
                    print(f"  ❌ Groq failed after {max_retries} retries: {e}")
                    return {}

    def _parse_response(
        self, content: Optional[str], valid_ids: set[int]
    ) -> dict[int, list[str]]:
        """Parse Groq response into {message_id: [questions]}."""
        if not content:
            return {}

        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
        content = content.strip()

        # Find the first { in the response
        brace_pos = content.find("{")
        if brace_pos == -1:
            print(f"  ⚠️ Groq response: no JSON object found. Raw: {content[:200]}")
            return {}

        # Use JSONDecoder to parse just the first JSON object, ignoring trailing text
        decoder = json.JSONDecoder()
        try:
            raw, _ = decoder.raw_decode(content, brace_pos)
        except json.JSONDecodeError:
            # Fallback: try to find matching braces manually
            raw = self._extract_json_fallback(content[brace_pos:])
            if raw is None:
                print(f"  ⚠️ Groq response: JSON parse failed. Raw: {content[:200]}")
                return {}

        if not isinstance(raw, dict):
            return {}

        result: dict[int, list[str]] = {}
        dropped = 0
        for key, questions in raw.items():
            try:
                msg_id = int(key)
            except (ValueError, TypeError):
                dropped += 1
                continue
            if msg_id not in valid_ids:
                dropped += 1
                continue
            if isinstance(questions, list):
                result[msg_id] = [q for q in questions if isinstance(q, str) and q.strip()]

        if dropped and not result:
            print(f"  ⚠️ Groq returned {len(raw)} keys but none matched valid IDs. "
                  f"Keys: {list(raw.keys())[:5]}, Expected: {list(valid_ids)[:5]}")

        return result

    @staticmethod
    def _extract_json_fallback(text: str) -> Optional[dict]:
        """Try to salvage a truncated JSON object by removing trailing garbage.

        Handles cases like:
        - Valid JSON followed by explanation text
        - JSON with // comments (strip them)
        - Truncated JSON (find last complete entry)
        """
        # Strip single-line comments (// ...) that Llama sometimes adds
        lines = []
        for line in text.split("\n"):
            comment_pos = line.find("//")
            if comment_pos != -1:
                # Only strip if // is outside a string
                in_string = False
                for i, ch in enumerate(line[:comment_pos]):
                    if ch == '"' and (i == 0 or line[i - 1] != '\\'):
                        in_string = not in_string
                if not in_string:
                    line = line[:comment_pos]
            lines.append(line)
        cleaned = "\n".join(lines)

        # Try parsing the cleaned text
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Try truncating from the end to find the last valid closing brace
        for i in range(len(cleaned) - 1, 0, -1):
            if cleaned[i] == "}":
                try:
                    return json.loads(cleaned[: i + 1])
                except json.JSONDecodeError:
                    continue

        return None

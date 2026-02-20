QUESTION_GEN_PROMPT = """You are an expert at creating evaluation test questions for a university student Q&A chatbot.

Below are real messages from a university student Telegram group (University of Messina, mostly Russian-speaking students).

Analyze these messages and generate evaluation questions that a student might ask, which these messages could answer.

Messages:
{messages_json}

Generate exactly {num_questions} evaluation questions based on these messages. Each question should:
- Be phrased naturally, as a real student would ask it (in Russian)
- Be answerable by the information in the messages above
- Cover different topics found in the messages
- Include expected keywords that should appear in a good answer

Return a JSON array where each element has:
- "question": the question text (in Russian)
- "category": a short snake_case category (e.g., "vnzh_documents", "scholarship", "exams", "fees", "enrollment", "documents", "campus", "erasmus", "courses", "deadlines")
- "expected_keywords": array of 3-5 keywords (mix of Russian and Italian/English terms) that a good answer should contain

Return ONLY the JSON array, no other text.
Example:
[
  {{
    "question": "Какие документы нужны для ВНЖ?",
    "category": "vnzh_documents",
    "expected_keywords": ["ричевута", "контракт", "страховка", "фото", "банк"]
  }}
]
"""

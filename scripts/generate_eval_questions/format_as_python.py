import json


def format_as_python(questions: list[dict], start_id: int = 11) -> str:
    """Format questions as Python source code matching test_questions.py format."""
    lines = [
        '"""Evaluation test questions for Campora AI bot (Russian, Univesity of Messina context.)"""',
        "",
        "EVALUATION_QUESTIONS = [",
    ]

    for i, q in enumerate(questions):
        qid = start_id + i
        question = q["question"].replace('"', '\\"')
        category = q.get("category", "general")
        keywords = q.get("expected_keywords", [])

        lines.append("    {")
        lines.append(f'        "id": {qid},')
        lines.append(f'        "question": "{question}",')
        lines.append(f'        "category": "{category}",')
        lines.append(f'        "expected_keywords": {json.dumps(keywords, ensure_ascii=False)},')
        lines.append('        "min_similarity_threshold": 0.3,')
        lines.append("    },")

    lines.append("]")
    lines.append("")

    return "\n".join(lines)

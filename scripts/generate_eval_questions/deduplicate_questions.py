def deduplicate_questions(questions: list[dict]) -> list[dict]:
	"""Remove duplicate or very similar questions."""
	seen_texts = set()
	unique = []

	for q in questions:
		text = q["question"].strip().lower()
		# Simple dedup: skip if we've seen an identical question
		if text not in seen_texts:
			seen_texts.add(text)
			unique.append(q)

	return unique

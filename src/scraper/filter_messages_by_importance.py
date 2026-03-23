import json
import re
import time
from typing import List, Set

from openai import OpenAI

from src.scraper.build_reply_chains import build_reply_chains
from src.config.settings import OPENAI_API_KEY

FILTER_PROMPT = """Analyze these Telegram messages from a university student group and identify which ones contain valuable information for students.

The group may focus on any topic — applicants, enrolled students, alumni, etc. Adapt your judgment to the group's actual content.

Some messages are replies to other messages. When a message has "reply_context", it shows the parent message(s) it is responding to.
Consider the FULL conversation thread when judging value — a short reply like "March 2nd" is valuable if it answers an important question.

KEEP these messages (valuable):
- Announcements, deadlines, important dates
- Questions and answers about academic topics
- Admissions info: entry requirements, exam scores, application deadlines
- Shared resources, links, study materials, exams
- Official information from professors/admins
- Questions and answers about documents (e.g. visa, residence permit, student ID)
- Questions and answers about exchange and transfer programs (e.g. Erasmus, semester abroad)
- Course registration and enrollment help
- Campus facilities and services info
- Scholarship and financial aid information
- Internship and job opportunities
- REPLIES that answer any of the above questions (even if the reply text is short)

FILTER OUT these messages (not valuable):
- Renting apartments or housing discussions
- Bank transfers or financial transactions
- Casual conversation between users
- Toxic or argumentative exchanges
- Spam, memes, off-topic chat
- Single-word responses or reactions (unless answering a valuable question)
- Selling/buying items or marketplace posts
- Food delivery and restaurant recommendations
- Social event planning unrelated to academics
- Transportation/ride sharing requests
- Personal complaints or venting
- Gaming or entertainment discussions

Messages to analyze:
{messages_json}

Return ONLY a JSON array of message IDS that are VALUABLE and should be kept.
Example response: [123, 456, 789]

If no messages are valuable, return an empty array: []
"""

client_oa = OpenAI(api_key=OPENAI_API_KEY)


def _parse_valuable_ids(response_content: str, batch_ids: Set[int]) -> Set[int]:
	"""Extract message IDs from AI response. Returns only IDs that appear in batch_ids."""
	content = response_content.strip()
	# Remove markdown code blocks if present
	code_block = re.search(r"\[[\d,\s]+\]", content)
	if code_block:
		content = code_block.group(0)
	try:
		ids = set(json.loads(content))
		return {int(i) for i in ids} & batch_ids
	except (json.JSONDecodeError, TypeError):
		return set()


def _expand_reply_chains(
	kept_ids: Set[int],
	all_messages: List[dict],
	reply_chains: dict,
) -> Set[int]:
	"""
	Expand kept IDs to include full reply chains.

	If a message is kept:
	  - Keep all its ancestors (parents, grandparents, etc.)
	  - Keep all direct replies to it
	"""
	all_by_id = {m["id"]: m for m in all_messages}
	expanded = set(kept_ids)

	# For each kept message, keep its ancestors
	for msg_id in list(kept_ids):
		chain = reply_chains.get(msg_id, [])
		for ancestor in chain:
			if ancestor["id"] in all_by_id:
				expanded.add(ancestor["id"])

	# For each kept message, keep direct replies from the batch
	for msg in all_messages:
		parent_id = msg.get("reply_to_message_id")
		if parent_id and parent_id in expanded:
			expanded.add(msg["id"])

	return expanded


def filter_messages_by_importance(messages: List[dict], batch_size: int = 20) -> List[dict]:
	"""Filter messages using AI to keep only valuable/important ones.

	Builds reply chains to give AI full conversation context, then
	auto-expands the kept set to preserve complete reply threads.
	"""
	if not messages:
		return []

	# Build reply chains for all messages up front
	print("🔗 Building reply chains...")
	reply_chains = build_reply_chains(messages)
	chains_with_context = sum(1 for c in reply_chains.values() if c)
	print(f"  {chains_with_context}/{len(messages)} messages have reply context")

	all_kept_ids: Set[int] = set()
	total_batches = (len(messages) + batch_size - 1) // batch_size

	for i in range(0, len(messages), batch_size):
		batch = messages[i : i + batch_size]
		batch_num = i // batch_size + 1
		batch_ids = {msg["id"] for msg in batch}

		# Build JSON with reply context
		batch_json = []
		for m in batch:
			entry = {"id": m["id"], "text": m["text"][:500]}

			# Add reply context if this message is a reply
			chain = reply_chains.get(m["id"], [])
			if chain:
				entry["reply_context"] = [
					{"id": p["id"], "text": p.get("text", "")[:300]}
					for p in chain
				]

			batch_json.append(entry)

		messages_json = json.dumps(batch_json, ensure_ascii=False)
		prompt = FILTER_PROMPT.format(messages_json=messages_json)

		try:
			response = client_oa.chat.completions.create(
				model="gpt-4o-mini",
				messages=[{"role": "user", "content": prompt}],
				temperature=0,
			)
			content = response.choices[0].message.content or ""
			keep_ids = _parse_valuable_ids(content, batch_ids)
			all_kept_ids.update(keep_ids)
			print(f"🤖 AI filter batch {batch_num}/{total_batches}: kept {len(keep_ids)}/{len(batch)} messages")
		except Exception as e:
			print(f"❌ AI filter error in batch {batch_num}, keeping all {len(batch)} messages: {e}")
			all_kept_ids.update(batch_ids)

		if batch_num < total_batches:
			time.sleep(1)

	# Expand kept set to include full reply chains
	before_expand = len(all_kept_ids)
	all_kept_ids = _expand_reply_chains(all_kept_ids, messages, reply_chains)
	if len(all_kept_ids) > before_expand:
		print(f"🔗 Reply chain expansion: {before_expand} -> {len(all_kept_ids)} messages")

	# Return messages in original order
	return [m for m in messages if m["id"] in all_kept_ids]

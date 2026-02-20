from typing import Dict, List, Optional, Set

from src.config.settings import SUPABASE_SERVICE_KEY, SUPABASE_URL
from supabase import Client, create_client

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def build_reply_chains(messages: List[dict]) -> Dict[int, List[dict]]:
	"""
	Build reply chains for each message by walking up reply_to_message_id.

	For each message that is a reply, resolves the full chain of parent
	messages recursively. Parents are looked up first in the current batch,
	then in the database.

	Returns:
		Dict mapping message_id -> list of ancestor messages (ordered
		from immediate parent to root). Empty list if message is not a reply.
	"""
	# Build lookup from current batch
	batch_by_id: Dict[int, dict] = {m["id"]: m for m in messages}

	# Cache for DB lookups to avoid repeated queries
	db_cache: Dict[int, Optional[dict]] = {}

	# Result: message_id -> [parent, grandparent, ...]
	chains: Dict[int, List[dict]] = {}

	for msg in messages:
		chain = _resolve_chain(msg, batch_by_id, db_cache)
		chains[msg["id"]] = chain

	return chains


def _resolve_chain(
	msg: dict,
	batch_by_id: Dict[int, dict],
	db_cache: Dict[int, Optional[dict]],
	max_depth: int = 5,
) -> List[dict]:
	"""Recursively walk up the reply chain, returning [parent, grandparent, ...]."""
	chain: List[dict] = []
	seen: Set[int] = {msg["id"]}
	current = msg
	chat_id = msg.get("chat_id", 0)

	for _ in range(max_depth):
		parent_id = current.get("reply_to_message_id")
		if not parent_id or parent_id in seen:
			break

		seen.add(parent_id)
		parent = _lookup_message(parent_id, chat_id, batch_by_id, db_cache)
		if not parent:
			break

		chain.append(parent)
		current = parent

	return chain


def _lookup_message(
	msg_id: int,
	chat_id: int,
	batch_by_id: Dict[int, dict],
	db_cache: Dict[int, Optional[dict]],
) -> Optional[dict]:
	"""Look up a message by ID + chat_id: first in batch, then in DB cache, then query DB."""
	# Check current batch first
	if msg_id in batch_by_id:
		return batch_by_id[msg_id]

	# Check DB cache
	if msg_id in db_cache:
		return db_cache[msg_id]

	# Query database (filter by both id and chat_id for composite PK)
	try:
		resp = supabase.table("messages").select("id, chat_id, text, reply_to_message_id").eq("id", msg_id).eq("chat_id", chat_id).limit(1).execute()
		if resp.data:
			db_cache[msg_id] = resp.data[0]
			return resp.data[0]
	except Exception as e:
		print(f"⚠️ Error looking up message {msg_id}: {e}")

	db_cache[msg_id] = None
	return None

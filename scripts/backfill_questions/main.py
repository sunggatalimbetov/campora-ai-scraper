import argparse

from scripts.backfill_questions.backfill_questions import backfill


def main():
    parser = argparse.ArgumentParser(
        description="Backfill hypothetical questions for messages using Groq + OpenAI embeddings"
    )
    parser.add_argument(
        "--chat-id",
        type=int,
        required=True,
        help="Chat ID to process (positive or negative, normalized internally)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Messages per DB fetch chunk (default: 1000)",
    )
    parser.add_argument(
        "--groq-batch-size",
        type=int,
        default=25,
        help="Messages per Groq API call (default: 25)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last checkpoint",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate questions but skip embedding and DB insert",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max messages to process (default: all)",
    )
    args = parser.parse_args()

    backfill(
        chat_id=abs(args.chat_id),
        chunk_size=args.chunk_size,
        groq_batch_size=args.groq_batch_size,
        resume=args.resume,
        dry_run=args.dry_run,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()

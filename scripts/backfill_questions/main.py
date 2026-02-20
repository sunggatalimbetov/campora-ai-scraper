import argparse

from scripts.backfill_questions.backfill_questions import backfill


def main():
    parser = argparse.ArgumentParser(description="Backfill hypothetical questions for existing messages")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Messages per batch (default: 10)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds to wait between batches (default: 1.0)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max messages to process (default: all)",
    )
    args = parser.parse_args()

    backfill(batch_size=args.batch_size, delay=args.delay, limit=args.limit)


if __name__ == "__main__":
    main()

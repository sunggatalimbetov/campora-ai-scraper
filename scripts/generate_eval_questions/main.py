import argparse
import json
import time
from pathlib import Path

from scripts.generate_eval_questions import (
    deduplicate_questions,
    fetch_messages,
    format_as_python,
    generate_questions_from_batch,
)


def main():
    parser = argparse.ArgumentParser(description="Generate evaluation questions from real messages")
    parser.add_argument("--messages", type=int, default=1000, help="Number of messages to fetch (default: 1000)")
    parser.add_argument("--questions", type=int, default=90, help="Number of questions to generate (default: 90)")
    parser.add_argument("--batch-size", type=int, default=50, help="Messages per LLM batch (default: 50)")
    parser.add_argument("--output", type=str, default=None, help="Output file path (default: tests/evaluation/generated_questions.py)")
    args = parser.parse_args()

    # Fetch messages
    messages = fetch_messages(args.messages)
    if not messages:
        print("No messages found in database. Exiting.")
        return

    # Calculate how many questions per batch
    num_batches = (len(messages) + args.batch_size - 1) // args.batch_size
    questions_per_batch = max(1, args.questions // num_batches)
    # Last batch gets the remainder
    remainder = args.questions - (questions_per_batch * num_batches)

    print(f"\nGenerating {args.questions} questions from {len(messages)} messages")
    print(f"  {num_batches} batches of ~{args.batch_size} messages")
    print(f"  ~{questions_per_batch} questions per batch\n")

    all_questions = []

    for i in range(0, len(messages), args.batch_size):
        batch = messages[i : i + args.batch_size]
        batch_num = i // args.batch_size + 1

        # Last batch gets extra to make up the total
        target = questions_per_batch + (remainder if batch_num == num_batches else 0)
        target = min(target, 15)  # Cap per-batch to avoid overwhelming the LLM

        print(f"Batch {batch_num}/{num_batches}: {len(batch)} messages -> generating {target} questions...")

        questions = generate_questions_from_batch(batch, target)
        all_questions.extend(questions)
        print(f"  Got {len(questions)} questions (running total: {len(all_questions)})")

        if len(all_questions) >= args.questions:
            break

        # Rate limiting
        if batch_num < num_batches:
            time.sleep(1)

    # Deduplicate
    before_dedup = len(all_questions)
    all_questions = deduplicate_questions(all_questions)
    print(f"\nDeduplication: {before_dedup} -> {len(all_questions)} questions")

    # Trim to exact count requested
    all_questions = all_questions[: args.questions]
    print(f"Final question count: {len(all_questions)}")

    # Output
    output_path = args.output or str(Path(__file__).resolve().parent.parent.parent / "tests" / "evaluation" / "generated_questions.py")

    python_code = format_as_python(all_questions, start_id=11)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(python_code)

    print(f"\nQuestions written to {output_path}")

    # Also save raw JSON for reference
    json_path = output_path.replace(".py", ".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_questions, f, ensure_ascii=False, indent=2)

    print(f"Raw JSON saved to {json_path}")

    # Print category distribution
    categories = {}
    for q in all_questions:
        cat = q.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    print("\nCategory distribution:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()

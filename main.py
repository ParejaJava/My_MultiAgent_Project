"""Simple starter Python script for project initialization."""

import sys


def greet(name: str) -> str:
    """Return a greeting message for the given name."""
    return f"Hello, {name}! Welcome to your new Python project."


def main() -> int:
    name = sys.argv[1] if len(sys.argv) > 1 else "GitHub User"
    print(greet(name))
    print("This change is only for GitHub sync verification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

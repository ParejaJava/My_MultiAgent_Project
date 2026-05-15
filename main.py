"""Compatibility entry point for running the FastAPI app."""

import uvicorn


def main() -> None:
    """Start the development server."""
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()

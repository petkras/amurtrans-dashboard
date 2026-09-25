"""Expose the Dash Flask server to Vercel's Python runtime."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import server as app  # noqa: E402

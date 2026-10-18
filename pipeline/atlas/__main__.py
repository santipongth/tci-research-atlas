"""`python -m atlas ...` = the `atlas` CLI (used by `atlas embed --background` to start the detached run)."""
from atlas.cli import app

app(prog_name="atlas")

import os
import sys
import yaml
from pathlib import Path


_config: dict | None = None


def load(path: str = "config.yaml") -> dict:
    global _config
    p = Path(path)
    if not p.exists():
        print(f"ERROR: {path} not found. Copy config.yaml.example → config.yaml and fill it in.", file=sys.stderr)
        sys.exit(1)
    with open(p) as f:
        _config = yaml.safe_load(f)
    return _config


def get() -> dict:
    if _config is None:
        return load()
    return _config


def api_key() -> str:
    cfg = get()
    env_var = cfg.get("anthropic", {}).get("api_key_env", "ANTHROPIC_API_KEY")
    key = os.environ.get(env_var, "")
    if not key:
        print(f"ERROR: env var {env_var} is not set.", file=sys.stderr)
        sys.exit(1)
    return key

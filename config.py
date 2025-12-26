import tomllib
import shutil
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv
import os

CONFIG_DIR = Path.home() / ".memcoach"
CONFIG_PATH = CONFIG_DIR / "config.toml"
PROJECT_CONFIG_EXAMPLE = Path(__file__).parent / "config.toml"

def load_config() -> Dict[str, Any]:
    """Load config from ~/.memcoach/config.toml, copy example if missing, load .env overrides."""
    load_dotenv()  # Load .env for overrides (e.g., OLLAMA_MODEL env var)
    if not CONFIG_PATH.exists():
        CONFIG_DIR.mkdir(exist_ok=True)
        shutil.copy(PROJECT_CONFIG_EXAMPLE, CONFIG_PATH)
    with open(CONFIG_PATH, "rb") as f:
        config = tomllib.load(f)
    # Support legacy flat keys while preferring nested tables
    legacy_ollama = {
        "model": config.get("ollama_model"),
        "timeout": config.get("ollama_timeout")
    }
    legacy_grading = {
        "levenshtein_perfect_threshold": config.get("levenshtein_perfect_threshold"),
        "levenshtein_good_threshold": config.get("levenshtein_good_threshold"),
        "use_llm_on_borderline": config.get("use_llm_on_borderline")
    }

    ollama_cfg = config.get("ollama", {})
    config["ollama"] = {
        "model": os.getenv("OLLAMA_MODEL", ollama_cfg.get("model", legacy_ollama.get("model", "llama3.2"))),
        "timeout": int(os.getenv("OLLAMA_TIMEOUT", ollama_cfg.get("timeout", legacy_ollama.get("timeout", 15))))
    }
    grading_cfg = config.get("grading", {})
    config["grading"] = {
        "levenshtein_perfect_threshold": float(os.getenv(
            "LEVENSHTEIN_PERFECT_THRESHOLD",
            grading_cfg.get("levenshtein_perfect_threshold", legacy_grading.get("levenshtein_perfect_threshold", 0.98))
        )),
        "levenshtein_good_threshold": float(os.getenv(
            "LEVENSHTEIN_GOOD_THRESHOLD",
            grading_cfg.get("levenshtein_good_threshold", legacy_grading.get("levenshtein_good_threshold", 0.85))
        )),
        "use_llm_on_borderline": os.getenv(
            "USE_LLM_ON_BORDERLINE",
            str(grading_cfg.get("use_llm_on_borderline", legacy_grading.get("use_llm_on_borderline", True)))
        ).lower() == "true",
    }
    return config

def get_config_value(section: str, key: str, default: Optional[Any] = None) -> Any:
    """Get nested config value, e.g., get_config_value('ollama', 'model')."""
    config = load_config()
    value = config.get(section, {}).get(key, default)
    return value

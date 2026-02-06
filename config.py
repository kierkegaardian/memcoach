import tomllib
import shutil
import re
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv
import os

CONFIG_DIR = Path.home() / ".memcoach"
CONFIG_PATH = CONFIG_DIR / "config.toml"
PROJECT_CONFIG_EXAMPLE = Path(__file__).parent / "config.toml"

def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

def _coerce_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

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
    ollama_timeout = os.getenv("OLLAMA_TIMEOUT")
    if ollama_timeout is None:
        ollama_timeout = ollama_cfg.get("timeout")
    if ollama_timeout is None:
        ollama_timeout = legacy_ollama.get("timeout")
    if ollama_timeout is None:
        ollama_timeout = 15
    config["ollama"] = {
        "model": os.getenv("OLLAMA_MODEL", ollama_cfg.get("model", legacy_ollama.get("model", "llama3.2"))),
        "timeout": _coerce_int(ollama_timeout, 15),
    }
    grading_cfg = config.get("grading", {})
    perfect_threshold = os.getenv("LEVENSHTEIN_PERFECT_THRESHOLD")
    if perfect_threshold is None:
        perfect_threshold = grading_cfg.get("levenshtein_perfect_threshold")
    if perfect_threshold is None:
        perfect_threshold = legacy_grading.get("levenshtein_perfect_threshold")
    if perfect_threshold is None:
        perfect_threshold = 0.98

    good_threshold = os.getenv("LEVENSHTEIN_GOOD_THRESHOLD")
    if good_threshold is None:
        good_threshold = grading_cfg.get("levenshtein_good_threshold")
    if good_threshold is None:
        good_threshold = legacy_grading.get("levenshtein_good_threshold")
    if good_threshold is None:
        good_threshold = 0.85

    config["grading"] = {
        "levenshtein_perfect_threshold": _coerce_float(perfect_threshold, 0.98),
        "levenshtein_good_threshold": _coerce_float(good_threshold, 0.85),
        "use_llm_on_borderline": os.getenv(
            "USE_LLM_ON_BORDERLINE",
            str(grading_cfg.get("use_llm_on_borderline", legacy_grading.get("use_llm_on_borderline", True)))
        ).lower() == "true",
    }
    stt_cfg = config.get("stt", {})
    config["stt"] = {
        "provider": os.getenv("STT_PROVIDER", stt_cfg.get("provider", "auto")),
        "model": os.getenv("STT_MODEL", stt_cfg.get("model", "base")),
        "language": os.getenv("STT_LANGUAGE", stt_cfg.get("language", "en")),
        "device": os.getenv("STT_DEVICE", stt_cfg.get("device", "cpu")),
        "compute_type": os.getenv("STT_COMPUTE_TYPE", stt_cfg.get("compute_type", "int8")),
        "normalize_audio": os.getenv(
            "STT_NORMALIZE_AUDIO",
            str(stt_cfg.get("normalize_audio", True)),
        ).lower() == "true",
        "vad_filter": os.getenv(
            "STT_VAD_FILTER",
            str(stt_cfg.get("vad_filter", True)),
        ).lower() == "true",
        "no_speech_threshold": float(os.getenv(
            "STT_NO_SPEECH_THRESHOLD",
            stt_cfg.get("no_speech_threshold", 0.6),
        )),
        "log_prob_threshold": float(os.getenv(
            "STT_LOG_PROB_THRESHOLD",
            stt_cfg.get("log_prob_threshold", -1.0),
        )),
        "fallback_no_speech_threshold": float(os.getenv(
            "STT_FALLBACK_NO_SPEECH_THRESHOLD",
            stt_cfg.get("fallback_no_speech_threshold", 0.9),
        )),
        "fallback_log_prob_threshold": float(os.getenv(
            "STT_FALLBACK_LOG_PROB_THRESHOLD",
            stt_cfg.get("fallback_log_prob_threshold", -5.0),
        )),
    }
    return config

def get_config_value(section: str, key: str, default: Optional[Any] = None) -> Any:
    """Get nested config value, e.g., get_config_value('ollama', 'model')."""
    config = load_config()
    value = config.get(section, {}).get(key, default)
    return value


def set_parent_pin_hash(pin_hash: str) -> None:
    """Persist parent PIN hash into config.toml."""
    load_config()
    text = CONFIG_PATH.read_text()
    if "[parent]" not in text:
        text = text.rstrip() + f'\n\n[parent]\npin_hash = "{pin_hash}"\n'
        CONFIG_PATH.write_text(text)
        return

    def update_section(match: re.Match) -> str:
        section = match.group(1)
        rest = match.group(2)
        if re.search(r"^pin_hash\s*=", section, flags=re.MULTILINE):
            section = re.sub(
                r"^pin_hash\s*=.*$",
                f'pin_hash = "{pin_hash}"',
                section,
                flags=re.MULTILINE,
            )
        else:
            lines = section.rstrip().splitlines()
            insert_at = 1 if lines else 0
            lines.insert(insert_at, f'pin_hash = "{pin_hash}"')
            section = "\n".join(lines) + "\n"
        return section + rest

    text = re.sub(r"(?ms)(^\s*\[parent\].*?)(^\s*\[|\Z)", update_section, text)
    CONFIG_PATH.write_text(text)

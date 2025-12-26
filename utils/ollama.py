import subprocess
from typing import Optional
import os
from config import load_config

def call_llm(prompt: str, model: str = None, timeout: int = 15) -> Optional[str]:
    """Call local Ollama model with prompt, return response or None on error."""
    config = load_config()
    model = model or config.get('ollama', {}).get('model', 'llama3.2')
    timeout = timeout or config.get('ollama', {}).get('timeout', 15)
    cmd = ['ollama', 'run', model]
    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
            encoding='utf-8'
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"Ollama call failed: {e}. Falling back to Levenshtein grading.")
        return None

def grade_with_llm(full_text: str, user_text: str, config: dict = None) -> str:
    """Use LLM to grade borderline cases."""
    if not config:
        config = load_config()
    prompt = f"""Original text to memorize: {full_text}

User's typed recall: {user_text}

Evaluate the recall accuracy for a child memorizing text. Be encouraging but honest.

Respond with exactly one word: 'perfect' (exact or very close match), 'good' (captures essence with minor errors), or 'fail' (major differences or too short).

Response:"""
    response = call_llm(prompt)
    if response:
        response_lower = response.lower().strip()
        if 'perfect' in response_lower:
            return 'perfect'
        elif 'good' in response_lower:
            return 'good'
        else:
            return 'fail'
    return 'good'  # Fallback

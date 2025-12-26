from Levenshtein import ratio as lev_ratio
from typing import Dict, Any
from config import load_config
from .ollama import grade_with_llm
from .sm2 import map_grade_to_quality

def grade_recall(full_text: str, user_text: str, config: Dict[str, Any] = None) -> str:
    """Grade user recall using Levenshtein + optional LLM for borderline."""
    if not config:
        config = load_config()
    grading_config = config.get('grading', {})
    perfect_th = grading_config.get('levenshtein_perfect_threshold', 0.98)
    good_th = grading_config.get('levenshtein_good_threshold', 0.85)
    use_llm = grading_config.get('use_llm_on_borderline', True)
    
    if not user_text or not user_text.strip():
        return 'fail'
    
    user_clean = user_text.strip().lower()
    full_clean = full_text.strip().lower()
    lev = lev_ratio(user_clean, full_clean)
    
    if lev >= perfect_th:
        return 'perfect'
    elif lev >= good_th:
        if use_llm and lev < perfect_th:  # Borderline: use LLM to decide perfect/good
            llm_grade = grade_with_llm(full_text, user_text, config)
            return llm_grade if llm_grade in ['perfect', 'good'] else 'good'
        return 'good'
    else:
        return 'fail'

def get_quality_score(grade: str) -> int:
    """Map grade to SM-2 quality (0-5)."""
    return map_grade_to_quality(grade)

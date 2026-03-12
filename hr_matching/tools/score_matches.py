"""Tool: Score and rank matched candidates against requirements."""

import re


def _get_field(row: dict, column_mapping: dict, semantic_field: str):
    """Get a value from a row using the semantic field name."""
    for original_col, mapped_field in column_mapping.items():
        if mapped_field == semantic_field:
            return row.get(original_col)
    return None


def _parse_number(val):
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        cleaned = re.sub(r'[^\d.\-]', '', str(val))
        return float(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


def score_matches(candidates: list, requirements: str, column_mapping: dict) -> dict:
    """Score candidates against natural language requirements.

    This tool provides a basic heuristic score. The LLM orchestrator can
    use the results + its own reasoning to refine the ranking.

    Args:
        candidates: List of candidate row dicts.
        requirements: Natural language description of ideal candidate.
        column_mapping: Semantic column mapping.

    Returns:
        dict with scored_candidates (sorted by score desc) and summary.
    """
    req_lower = requirements.lower()

    # Extract keywords from requirements
    keywords = []
    for word in re.split(r'[\s,，。、;；：:]+', req_lower):
        word = word.strip()
        if len(word) >= 2:
            keywords.append(word)

    # Education level scoring
    education_scores = {
        "高中": 1, "中专": 1, "大专": 2, "专科": 2,
        "本科": 3, "学士": 3, "bachelor": 3,
        "硕士": 4, "研究生": 4, "master": 4,
        "博士": 5, "doctor": 5, "phd": 5,
    }

    # Determine required education level from requirements text
    required_edu_level = 0
    for key, level in education_scores.items():
        if key in req_lower:
            required_edu_level = max(required_edu_level, level)

    scored = []
    for candidate in candidates:
        score = 50  # base score
        reasons = []

        # Keyword matching across all fields
        all_text = " ".join(
            str(v).lower() for v in candidate.values() if v is not None
        )
        keyword_hits = sum(1 for kw in keywords if kw in all_text)
        keyword_score = min(keyword_hits * 10, 30)
        score += keyword_score
        if keyword_hits > 0:
            reasons.append(f"关键词匹配 {keyword_hits} 个")

        # Education bonus
        edu = str(_get_field(candidate, column_mapping, "education") or "").lower()
        actual_edu_level = 0
        for key, level in education_scores.items():
            if key in edu:
                actual_edu_level = max(actual_edu_level, level)
        if required_edu_level > 0:
            if actual_edu_level >= required_edu_level:
                score += 10
                reasons.append("学历达标")
            else:
                score -= 10
                reasons.append("学历不足")

        # Experience bonus
        exp = _parse_number(_get_field(candidate, column_mapping, "years_of_experience"))
        if exp is not None:
            if exp >= 5:
                score += 10
                reasons.append(f"经验丰富({exp}年)")
            elif exp >= 3:
                score += 5
                reasons.append(f"经验适中({exp}年)")

        # Clamp score
        score = max(0, min(100, score))

        scored.append({
            "candidate": candidate,
            "score": score,
            "reasons": reasons,
        })

    # Sort by score descending
    scored.sort(key=lambda x: x["score"], reverse=True)

    return {
        "scored_candidates": scored,
        "total_scored": len(scored),
        "top_score": scored[0]["score"] if scored else 0,
    }

"""Tool: Search and filter candidates from the roster data."""

import re
from datetime import datetime


def _normalize(val):
    """Normalize value for comparison."""
    if val is None:
        return ""
    return str(val).strip().lower()


def _parse_number(val):
    """Try to parse a numeric value."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        # Remove common non-numeric chars
        cleaned = re.sub(r'[^\d.\-]', '', str(val))
        return float(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


def _get_field(row: dict, column_mapping: dict, semantic_field: str):
    """Get a value from a row using the semantic field name."""
    for original_col, mapped_field in column_mapping.items():
        if mapped_field == semantic_field:
            return row.get(original_col)
    return None


def search_roster(data: list, column_mapping: dict, filters: dict) -> dict:
    """Filter candidates based on structured criteria.

    Args:
        data: List of row dicts (all_data from parse_excel).
        column_mapping: Mapping from original column names to semantic fields.
        filters: Dict of filter criteria. Supported keys:
            - department: exact or partial match
            - position: exact or partial match
            - education: minimum education level
            - min_experience: minimum years of experience
            - max_experience: maximum years of experience
            - min_age / max_age: age range
            - min_salary / max_salary: salary range
            - gender: exact match
            - skills: comma-separated skills (any match)
            - keyword: free-text search across all fields
            - status: employment status

    Returns:
        dict with matched_candidates list and match_count.
    """
    education_levels = {
        "高中": 1, "中专": 1, "大专": 2, "专科": 2,
        "本科": 3, "学士": 3, "bachelor": 3,
        "硕士": 4, "研究生": 4, "master": 4,
        "博士": 5, "doctor": 5, "phd": 5,
    }

    results = []

    for row in data:
        match = True

        # Department filter
        if "department" in filters and filters["department"]:
            dept = _normalize(_get_field(row, column_mapping, "department"))
            if _normalize(filters["department"]) not in dept:
                match = False

        # Position filter
        if match and "position" in filters and filters["position"]:
            pos = _normalize(_get_field(row, column_mapping, "position"))
            if _normalize(filters["position"]) not in pos:
                match = False

        # Education filter (minimum level)
        if match and "education" in filters and filters["education"]:
            edu = _normalize(_get_field(row, column_mapping, "education"))
            required_level = education_levels.get(_normalize(filters["education"]), 0)
            actual_level = 0
            for key, level in education_levels.items():
                if key in edu:
                    actual_level = max(actual_level, level)
            if actual_level < required_level:
                match = False

        # Experience filter
        if match and "min_experience" in filters:
            exp = _parse_number(_get_field(row, column_mapping, "years_of_experience"))
            if exp is None or exp < filters["min_experience"]:
                match = False

        if match and "max_experience" in filters:
            exp = _parse_number(_get_field(row, column_mapping, "years_of_experience"))
            if exp is not None and exp > filters["max_experience"]:
                match = False

        # Age filter
        if match and "min_age" in filters:
            age = _parse_number(_get_field(row, column_mapping, "age"))
            if age is None or age < filters["min_age"]:
                match = False

        if match and "max_age" in filters:
            age = _parse_number(_get_field(row, column_mapping, "age"))
            if age is not None and age > filters["max_age"]:
                match = False

        # Salary filter
        if match and "min_salary" in filters:
            salary = _parse_number(_get_field(row, column_mapping, "salary"))
            if salary is None or salary < filters["min_salary"]:
                match = False

        if match and "max_salary" in filters:
            salary = _parse_number(_get_field(row, column_mapping, "salary"))
            if salary is not None and salary > filters["max_salary"]:
                match = False

        # Gender filter
        if match and "gender" in filters and filters["gender"]:
            gender = _normalize(_get_field(row, column_mapping, "gender"))
            if _normalize(filters["gender"]) not in gender:
                match = False

        # Skills filter (any match)
        if match and "skills" in filters and filters["skills"]:
            skills_val = _normalize(_get_field(row, column_mapping, "skills"))
            required_skills = [s.strip().lower() for s in filters["skills"].split(",")]
            if not any(skill in skills_val for skill in required_skills):
                match = False

        # Status filter
        if match and "status" in filters and filters["status"]:
            status = _normalize(_get_field(row, column_mapping, "status"))
            if _normalize(filters["status"]) not in status:
                match = False

        # Keyword search (across all fields)
        if match and "keyword" in filters and filters["keyword"]:
            keyword = _normalize(filters["keyword"])
            found = False
            for val in row.values():
                if keyword in _normalize(val):
                    found = True
                    break
            if not found:
                match = False

        if match:
            results.append(row)

    return {
        "matched_candidates": results,
        "match_count": len(results),
        "total_count": len(data),
    }

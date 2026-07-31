"""
Smart Agent–Task Matcher
========================
Keyword-based scoring engine that matches a work item (title + description)
against available agents (role + skills) to recommend the best assignment.

Score formula (0–100):
  - Role keyword overlap  → up to 60 pts
  - Skills keyword overlap → up to 40 pts
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field


# ── Vietnamese / English stop words ──────────────────────────────────────────
_STOP = {
    "và", "hoặc", "cho", "để", "với", "của", "trong", "một", "các",
    "the", "a", "an", "and", "or", "to", "for", "in", "of", "on",
    "with", "at", "by", "from", "is", "are", "be", "this", "that",
}


def _tokenize(text: str) -> set[str]:
    """Lowercase, split on non-word chars, remove stop words, 3+ char tokens."""
    tokens = re.findall(r"[a-zA-Z\u00C0-\u024F\u1E00-\u1EFF]+", text.lower())
    return {t for t in tokens if len(t) >= 3 and t not in _STOP}


def _overlap_score(task_tokens: set[str], target_text: str, max_pts: float) -> float:
    """Score overlap between task tokens and a text string."""
    if not task_tokens or not target_text:
        return 0.0
    target_tokens = _tokenize(target_text)
    if not target_tokens:
        return 0.0
    matched = task_tokens & target_tokens
    # Jaccard-like: matched / task token count (emphasise task coverage)
    ratio = len(matched) / len(task_tokens)
    return round(ratio * max_pts, 2)


@dataclass
class MatchCandidate:
    agent_id: int
    agent_name: str
    agent_role: str
    agent_avatar: str
    score: float          # 0–100
    role_score: float
    skills_score: float
    matched_keywords: list[str] = field(default_factory=list)
    reason: str = ""


@dataclass
class MatchResult:
    task_title: str
    task_description: str
    best: MatchCandidate | None
    alternatives: list[MatchCandidate] = field(default_factory=list)
    has_match: bool = False
    threshold: float = 15.0  # minimum score to count as "matched"

    def top_suggestions(self, n: int = 3) -> list[MatchCandidate]:
        all_c = ([self.best] if self.best else []) + self.alternatives
        return all_c[:n]


def match_agent_for_task(
    title: str,
    description: str,
    agents: list[dict],
    threshold: float = 15.0,
) -> MatchResult:
    """
    Score all agents against the task and return a MatchResult.

    :param title:       Work item title
    :param description: Work item description
    :param agents:      List of agent dicts (with 'skills' key already deserialized)
    :param threshold:   Minimum score (0–100) to be considered a match
    """
    task_text = f"{title} {description}"
    task_tokens = _tokenize(task_text)

    candidates: list[MatchCandidate] = []

    for agent in agents:
        if not agent.get("enabled", 1):
            continue

        role_text = agent.get("role", "")
        skills = agent.get("skills", [])
        skills_text = " ".join(
            f"{s.get('name', '')} {s.get('description', '')}" for s in skills
        )

        role_score   = _overlap_score(task_tokens, role_text,   max_pts=60.0)
        skills_score = _overlap_score(task_tokens, skills_text, max_pts=40.0)
        total_score  = role_score + skills_score

        # Build matched keyword list for UI display
        matched_kw = sorted(
            task_tokens
            & (_tokenize(role_text) | _tokenize(skills_text))
        )[:6]  # top 6

        # Build human-readable reason
        parts = []
        if role_score > 0:
            parts.append(f"vai trò '{role_text}'")
        if skills_score > 0:
            skill_names = [s.get("name", "") for s in skills]
            parts.append(f"kỹ năng: {', '.join(skill_names[:3])}")
        reason = "Phù hợp vì " + " và ".join(parts) if parts else "Không có điểm khớp"

        candidates.append(MatchCandidate(
            agent_id       = agent["id"],
            agent_name     = agent["name"],
            agent_role     = role_text,
            agent_avatar   = agent.get("avatar_color", "🦊"),
            score          = total_score,
            role_score     = role_score,
            skills_score   = skills_score,
            matched_keywords = matched_kw,
            reason         = reason,
        ))

    # Sort by score descending
    candidates.sort(key=lambda c: c.score, reverse=True)

    best = candidates[0] if candidates and candidates[0].score >= threshold else None
    alternatives = [c for c in candidates[1:4] if c.score > 0]

    return MatchResult(
        task_title       = title,
        task_description = description,
        best             = best,
        alternatives     = alternatives,
        has_match        = best is not None,
        threshold        = threshold,
    )


def match_result_to_dict(result: MatchResult) -> dict:
    """Serialize MatchResult to JSON-safe dict."""
    def _c(c: MatchCandidate) -> dict:
        return {
            "agent_id":        c.agent_id,
            "agent_name":      c.agent_name,
            "agent_role":      c.agent_role,
            "agent_avatar":    c.agent_avatar,
            "score":           c.score,
            "role_score":      c.role_score,
            "skills_score":    c.skills_score,
            "matched_keywords": c.matched_keywords,
            "reason":          c.reason,
        }

    return {
        "has_match":   result.has_match,
        "threshold":   result.threshold,
        "best":        _c(result.best) if result.best else None,
        "suggestions": [_c(c) for c in result.top_suggestions(3)],
    }

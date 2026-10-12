"""Loads and validates the YAML knowledge base, and derives prompt context from it."""

from functools import lru_cache
from pathlib import Path

import yaml

from app.knowledge.models import Knowledge, Lexicons, RegionPack, RoleFamily, SynonymIndex, Tip
from app.schemas import EmployerType, JDAnalysis, Level

ROOT = Path(__file__).parent


def _lines(name: str) -> list[str]:
    text = (ROOT / "lexicons" / name).read_text(encoding="utf-8")
    return [ln.strip().lower() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]


@lru_cache(maxsize=1)
def load_knowledge() -> Knowledge:
    regions = {}
    for path in sorted((ROOT / "regions").glob("*.yaml")):
        pack = RegionPack.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        regions[pack.key] = pack
    families = [RoleFamily.model_validate(f) for f in yaml.safe_load((ROOT / "role_families.yaml").read_text())]
    synonyms = yaml.safe_load((ROOT / "lexicons" / "skill_synonyms.yaml").read_text(encoding="utf-8"))
    return Knowledge(
        regions=regions,
        role_families={f.key: f for f in families},
        lexicons=Lexicons(
            action_verbs=frozenset(_lines("action_verbs.txt")),
            weak_openers=_lines("weak_openers.txt"),
            buzzwords=_lines("buzzwords.txt"),
            objective_cliches=_lines("objective_cliches.txt"),
        ),
        synonyms=SynonymIndex.from_mapping(synonyms),
    )


def select_tips(region: RegionPack, jd: JDAnalysis, level: Level) -> list[Tip]:
    return [
        t
        for t in region.tips
        if (not t.employer_types or jd.employer_type in t.employer_types)
        and (not t.levels or level in t.levels)
        and (not t.role_families or jd.role_family in t.role_families)
    ]


def drop_patterns(region: RegionPack, employer_type: EmployerType) -> list[str]:
    return [p for rule in region.drop_sections if rule.severity_for(employer_type) != "ok" for p in rule.patterns]


def build_context_brief(region: RegionPack, jd: JDAnalysis, level: Level, kb: Knowledge) -> str:
    """Compact hiring-context block injected into prompts: who is reading, what they expect, for this role."""
    family = kb.role_families.get(jd.role_family) or kb.role_families.get("general")
    lines = [
        f"Hiring market: {region.label}",
        f"Employer type: {jd.employer_type.replace('_', ' ')} | Role family: {family.label if family else jd.role_family}"
        f" | Candidate level: {level} | Typical page limit: {region.max_pages(level)}",
        f"Reader: {region.recruiter_persona}",
        "Market norms:",
        *(f"- {c}" for c in region.context),
    ]
    if family:
        lines += ["What strong resumes in this role family show:", *(f"- {s}" for s in family.signals)]
    lines.append(f"Common ATS platforms: {', '.join(region.ats_platforms)}")
    return "\n".join(lines)

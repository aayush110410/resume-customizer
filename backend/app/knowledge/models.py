"""Typed shape of the YAML knowledge base (region packs, role families, lexicons, skill synonyms)."""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel

from app.schemas import EmployerType, Level, Region
from app.text_utils import normalize

Severity = Literal["ok", "minor", "major"]
SEVERITY_PENALTY: dict[str, int] = {"ok": 0, "minor": 5, "major": 12}


class PatternRule(BaseModel):
    id: str
    label: str
    patterns: list[str]
    severity: dict[str, Severity]
    message: str
    fix: str

    def severity_for(self, employer_type: EmployerType) -> Severity:
        return self.severity.get(employer_type, self.severity.get("default", "ok"))


class Expectation(BaseModel):
    id: str
    label: str
    patterns: list[str]
    levels: list[Level]
    employer_types: list[EmployerType]
    penalty: int
    fix: str


class LengthNorm(BaseModel):
    level: Level
    max_pages: int


class Tip(BaseModel):
    id: str
    text: str
    employer_types: list[EmployerType] = []
    levels: list[Level] = []
    role_families: list[str] = []


class RegionPack(BaseModel):
    key: Region
    label: str
    weights: dict[str, float]
    page_size: Literal["a4", "us-letter"]
    length_norms: list[LengthNorm]
    personal_rules: list[PatternRule]
    term_rules: list[PatternRule]
    expectations: list[Expectation] = []
    drop_sections: list[PatternRule] = []
    ats_platforms: list[str]
    recruiter_persona: str
    context: list[str]
    cover_letter: list[str]
    tips: list[Tip]

    def max_pages(self, level: Level) -> int:
        return next((n.max_pages for n in self.length_norms if n.level == level), 2)


class RoleFamily(BaseModel):
    key: str
    label: str
    signals: list[str]


@dataclass(frozen=True)
class Lexicons:
    action_verbs: frozenset[str]
    weak_openers: list[str]
    buzzwords: list[str]
    objective_cliches: list[str]


@dataclass
class SynonymIndex:
    groups: dict[str, frozenset[str]] = field(default_factory=dict)  # any normalized variant -> its whole group

    @classmethod
    def from_mapping(cls, mapping: dict[str, list[str]]) -> "SynonymIndex":
        index = cls()
        for canonical, aliases in mapping.items():
            group = frozenset(normalize(v) for v in [canonical, *(aliases or [])] if v and normalize(v))
            for variant in group:
                index.groups[variant] = group
        return index

    def variants(self, term: str) -> set[str]:
        key = normalize(term)
        return set(self.groups.get(key, {key}))


@dataclass(frozen=True)
class Knowledge:
    regions: dict[Region, RegionPack]
    role_families: dict[str, RoleFamily]
    lexicons: Lexicons
    synonyms: SynonymIndex

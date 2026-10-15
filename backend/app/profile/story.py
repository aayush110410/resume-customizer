"""Story: does this candidate's history read well for the stage they are at? Six components, each scored 0-100,
weighted by stage and renormalised over the ones that have something to judge.

Weights (student and fresh_grad / early / mid and senior):
- projects: 40 / 20 / 10
- internships: 25 / 5 / 0
- presentation: 20 / 10 / 0
- continuity: 15 / 20 / 25
- stability: 0 / 25 / 30
- transition: 0 / 20 / 35
"""

import re
from datetime import date

from app.knowledge.models import Knowledge, StoryRules
from app.profile.employers import field_of
from app.profile.timeline import is_school, parse_date
from app.resume_ops import render_plain
from app.schemas import Evidence, Explanation, JDAnalysis, Profile, Region, ResumeDoc, Stage, SubScore
from app.scoring.aggregate import round_half_up
from app.text_utils import contains_term

STAGE_WEIGHTS: dict[Stage, dict[str, int]] = {
    "student": {"projects": 40, "internships": 25, "presentation": 20, "continuity": 15},
    "fresh_grad": {"projects": 40, "internships": 25, "presentation": 20, "continuity": 15},
    "early": {
        "projects": 20,
        "internships": 5,
        "presentation": 10,
        "continuity": 20,
        "stability": 25,
        "transition": 20,
    },
    "mid": {"projects": 10, "continuity": 25, "stability": 30, "transition": 35},
    "senior": {"projects": 10, "continuity": 25, "stability": 30, "transition": 35},
}
STABILITY = {0: 100, 1: 85, 2: 60, 3: 40, 4: 30}  # 5 or more counted stints give 20; explained stints are not counted
EXPLAINED_STINT = {"contract", "layoff", "project", "internship"}
_STATED_GAP = re.compile(r"career break|sabbatical|gap year", re.I)
_GRADES = re.compile(r"\b(c?gpa|cpi|sgpa)\b|\b\d{1,2}(\.\d+)?\s?%|\b\d\.\d{1,2}\s?/\s?10\b", re.I)
_PROFILE_LINK = re.compile(r"github|gitlab|leetcode|codeforces|codechef|behance|dribbble|kaggle", re.I)
_OWNERSHIP = re.compile(r"\b(owned|designed|built|launched|led|architected|created|drove|spearheaded)\b|\d", re.I)
_PROCESS = re.compile(
    r"\d|\b(sla|compliance|cross-?team|cross-?functional|documentation|process|audit|stakeholders?|governance)\b", re.I
)
_DEPTH = re.compile(
    r"\bmillions?\b|\bdistributed\b|\blatency\b|\bthroughput\b|system design|\bp9[59]\b|\bscale\b|"
    r"codeforces|leetcode|codechef",
    re.I,
)

Result = tuple[int, list[Explanation]]


def _note(signal: str, detail: str, fix: str, loss: float) -> Explanation:
    return Explanation(signal=signal, impact=-loss, detail=detail, fix=fix)


def projects_score(profile: Profile) -> Result:
    if not profile.projects:
        return 0, [
            _note(
                "no_projects", "No projects listed.", "Add 2–3 projects with what they do, a link and one number.", 100
            )
        ]
    best = sorted((p.score for p in profile.projects), reverse=True)[:3]
    score = round_half_up(sum(best) / len(best))
    notes = [
        _note("project", f"{p.title}: {p.notes[0]}", " ".join(p.notes), 100 - p.score)
        for p in profile.projects
        if p.notes
    ]
    return score, notes


def internship_score(profile: Profile, jd: JDAnalysis) -> Result:
    relevant = [
        s
        for s in profile.stints
        if s.kind in ("internship", "apprenticeship")
        and (s.months is None or s.months >= 2)
        and (s.field is None or s.field == jd.role_family)
    ]
    score = 20 if not relevant else 70 if len(relevant) == 1 else 100
    if score == 100:
        return score, []
    detail = "No internship in this field yet." if not relevant else "One relevant internship."
    fix = "A 2+ month internship or apprenticeship in this field is the strongest signal at your stage."
    return score, [_note("internships", detail, fix, 100 - score)]


def presentation_score(profile: Profile, resume: ResumeDoc, region_key: Region) -> Result:
    text = " ".join([render_plain(resume), *resume.contact.links])
    education = " ".join(f"{e.title} {e.organization} " + " ".join(b.text for b in e.bullets) for e in resume.education)
    has_grad = any(parse_date(e.end, _today(profile)) for e in resume.education if not is_school(e))
    has_grades = bool(_GRADES.search(education))  # "92% accuracy" in a project is not a CGPA
    has_link = bool(_PROFILE_LINK.search(text))
    parts = (
        [
            (30, has_grad, "graduation year"),
            (30, has_grades, "CGPA or percentage"),
            (40, has_link, "GitHub/LeetCode/portfolio link"),
        ]
        if region_key == "india"
        else [(40, has_grad, "graduation year"), (60, has_link, "GitHub or portfolio link")]
    )
    score = sum(points for points, ok, _ in parts if ok)
    missing = [label for _, ok, label in parts if not ok]
    if not missing:
        return score, []
    return score, [
        _note("presentation", "Missing: " + ", ".join(missing) + ".", "Add " + ", ".join(missing) + ".", 100 - score)
    ]


def continuity_score(profile: Profile, resume: ResumeDoc, rules: StoryRules) -> Result:
    stated = bool(_STATED_GAP.search(" ".join(e.title for e in resume.experience) + " " + (resume.summary or "")))
    score, notes = 100, []
    for g in profile.gaps:
        answer = profile.answers.get(g.id)
        explained = answer is not None and (
            answer.value in rules.accepted_gap_reasons or (answer.value == "other" and bool(answer.text))
        )
        span = f"{g.months}-month gap ({g.start} to {g.end})"
        if explained and stated:
            continue
        if explained:
            penalty, detail, fix = (
                10,
                f"{span}: explained to us, not on the resume.",
                "Add a one-line career-break entry with the reason.",
            )
        else:
            penalty = rules.gap_penalty["long" if g.months >= 12 else "short"]
            detail, fix = (
                f"{span} with no explanation.",
                "Tell us why in Confirm a few things, then state it in one line.",
            )
        score -= penalty
        notes.append(_note("gap", detail, fix, penalty))
    return max(0, score), notes


def stability_score(profile: Profile) -> Result:
    as_of = _index(profile.as_of)
    counted = []
    for s in profile.stints:
        if not (s.short and s.start) or as_of - _index(s.start) > 60:
            continue
        answer = profile.answers.get(f"stint:{s.entry_id}")
        if answer is None or answer.value not in EXPLAINED_STINT:
            counted.append(s)
    score = STABILITY.get(len(counted), 20)
    if score == 100:
        return score, []
    detail = f"{len(counted)} role(s) under a year in the last five years" + (
        ", which reads as a pattern of short stints." if len(counted) >= 3 else "."
    )
    fix = (
        "If these were contracts, layoffs or project roles, say so in Confirm a few things; the resume will label them."
    )
    return score, [_note("short_stints", detail, fix, 100 - score)]


def _share(rx: re.Pattern[str], bullets: list[str]) -> int:
    if not bullets:
        return 0
    return min(100, round_half_up(100 * (sum(bool(rx.search(b)) for b in bullets) / len(bullets)) / 0.5))


def transition_score(profile: Profile, resume: ResumeDoc, jd: JDAnalysis, ev: Evidence, kb: Knowledge) -> Result:
    targets = [m for m in profile.moves if m.target]
    work = [s for s in profile.stints if s.kind in ("job", "trainee", "freelance") and s.start]
    latest = max(work, key=lambda s: (s.end is None, s.end or "", s.start)) if work else None
    bullets = [b.text for e in resume.experience if latest and e.id == latest.entry_id for b in e.bullets]
    scores, notes = [], []
    for m in targets:
        if m.kind == "services_to_product":
            s = _share(_OWNERSHIP, bullets)
            detail = f"{m.from_label} → {m.to_label}: product teams screen for ownership and outcomes."
            fix = "Rewrite 2–3 recent bullets as what you built or owned and the result it had."
        elif m.kind == "startup_to_mnc":
            s = _share(_PROCESS, bullets)
            detail = f"{m.from_label} → {m.to_label}: large employers look for scale and process."
            fix = "Show scale (users, TPS, team size) and process (reviews, SLAs, documentation)."
        elif m.kind == "mnc_to_mega":
            s = _share(_DEPTH, bullets)
            detail = f"{m.from_label} → {m.to_label}: mega-MNC screens weigh scale and engineering depth."
            fix = "Lead with scale numbers and design decisions; add coding-profile ratings if they are strong."
        else:
            musts = [q.id for q in jd.requirements if q.importance == "must"]
            status = {x.requirement_id: x.status for x in ev.matches}
            share = sum(status.get(q) in ("strong", "partial") for q in musts) / len(musts) if musts else 0.5
            terms = {k for q in jd.requirements for k in q.keywords} | set(jd.ats_keywords)
            family = kb.role_families.get(jd.role_family)
            terms |= set(family.titles if family else [])
            bridge_text = " ".join(
                [
                    *(f"{p.title} " + " ".join(b.text for b in p.bullets) for p in resume.projects),
                    *(a.text for a in resume.achievements),
                ]
            )
            bridge = any(contains_term(bridge_text, t) for t in terms)
            framed = bool(resume.summary) and (
                field_of(resume.summary or "", kb) == jd.role_family
                or any(contains_term(resume.summary or "", t) for t in (family.titles if family else []))
            )
            s = round_half_up(50 * share + 30 * bridge + 20 * framed)
            detail = f"Switching from {m.from_label} to {m.to_label}: the resume needs bridge evidence."
            fix = "Add a project or certification in the new field and one summary line that frames the switch."
        scores.append(s)
        if s < 100:
            notes.append(_note("transition", detail, fix, 100 - s))
    return (round_half_up(sum(scores) / len(scores)) if scores else 100), notes


def _index(key: str) -> int:
    return int(key[:4]) * 12 + int(key[5:7]) - 1


def _today(profile: Profile) -> date:
    return date(int(profile.as_of[:4]), int(profile.as_of[5:7]), 1)


def score_story(
    profile: Profile, resume: ResumeDoc, jd: JDAnalysis, ev: Evidence, region_key: Region, kb: Knowledge
) -> SubScore | None:
    """None when nothing applies (no dates, no projects, no move at a senior stage): Story then sits out."""
    rules = kb.regions[region_key].story
    weights = STAGE_WEIGHTS[profile.stage]
    dated = any(s.start for s in profile.stints) or any(e.end and not is_school(e) for e in resume.education)
    parts: dict[str, Result] = {}
    if "projects" in weights and (profile.projects or profile.stage in ("student", "fresh_grad", "early")):
        parts["projects"] = projects_score(profile)
    if "internships" in weights:
        parts["internships"] = internship_score(profile, jd)
    if "presentation" in weights:
        parts["presentation"] = presentation_score(profile, resume, region_key)
    if "continuity" in weights and dated:
        parts["continuity"] = continuity_score(profile, resume, rules)
    if "stability" in weights and any(s.precise and s.kind in ("job", "trainee") for s in profile.stints):
        parts["stability"] = stability_score(profile)
    if "transition" in weights and any(m.target for m in profile.moves):
        parts["transition"] = transition_score(profile, resume, jd, ev, kb)
    if not parts:
        return None
    total = sum(weights[k] for k in parts)
    score = round_half_up(sum(weights[k] * s for k, (s, _) in parts.items()) / total)
    explanations = []
    for k, (_, notes) in parts.items():
        share = weights[k] / total
        explanations += [e.model_copy(update={"impact": round(e.impact * share, 1)}) for e in notes]
    if profile.rules_only:
        explanations.append(
            Explanation(
                signal="rules_only", impact=0, detail="Projects were read by rules only; the model was unavailable."
            )
        )
    return SubScore(key="story", score=score, explanations=explanations)

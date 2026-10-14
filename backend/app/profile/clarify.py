"""Questions only the candidate can answer, and their effect. Everything here is code: no model call.

Question ids come from what they ask about (gap:2021-06, stint:exp1, employer:exp0, name:zephyr, intern:exp3),
and are generated from the unanswered profile, so they never shift when answers change the stage or a move.
A re-score always rebuilds from the resume plus all answers, so applying the same answers twice is a no-op.
"""

from datetime import date

from app.knowledge.models import Knowledge
from app.profile.moves import detect_moves
from app.profile.projects import clean_facts, score_project
from app.profile.stage import FULL_TIME
from app.profile.story import score_story
from app.profile.timeline import month_label
from app.resume_ops import render_plain
from app.schemas import (
    Analysis,
    Answer,
    Evidence,
    JDAnalysis,
    Level,
    Profile,
    Question,
    QuestionOption,
    Region,
    RescoreResponse,
    ResumeDoc,
    Stage,
)

STAGE_OPTIONS = [
    ("student:1", "1st-year student"),
    ("student:2", "2nd-year student"),
    ("student:3", "3rd-year student"),
    ("student:4", "4th-year student"),
    ("student:5", "5th-year student (B.Arch, dual degree)"),
    ("fresh_grad", "Fresh graduate"),
    ("early", "1–3 years of work"),
    ("mid", "3–7 years of work"),
    ("senior", "7+ years of work"),
]
GAP_OPTIONS = [
    ("higher_studies", "Higher studies"),
    ("exam_prep", "Exam prep (UPSC/GATE/CAT/other)"),
    ("health", "Health"),
    ("family", "Family or caregiving"),
    ("layoff", "Layoff"),
    ("startup", "Startup attempt"),
    ("relocation", "Relocation"),
    ("other", "Other"),
]
STINT_OPTIONS = [
    ("contract", "Contract or freelance"),
    ("layoff", "Layoff or company shut down"),
    ("project", "Project-based"),
    ("internship", "Internship"),
    ("left", "I left"),
]
EMPLOYER_OPTIONS = [
    ("startup", "Startup"),
    ("product", "Product company"),
    ("it_services", "IT services"),
    ("mnc", "MNC"),
    ("mega_mnc", "Mega-MNC (Big Tech)"),
    ("govt", "Government / PSU"),
]
NAME_OPTIONS = [
    ("own", "My own library or framework"),
    ("internal", "An internal tool at my company"),
    ("third_party", "A third-party product"),
]
INTERN_OPTIONS = [
    ("paid", "Paid"),
    ("unpaid", "Unpaid"),
    ("academic", "Academic (credit)"),
    ("virtual", "Virtual simulation"),
]
MAX_QUESTIONS = 6
KIND_ORDER = {"gap": 0, "stint": 1, "employer": 2, "custom_name": 3, "internship": 4}
STAGE_LEVEL: dict[Stage, Level] = {
    "student": "fresher",
    "fresh_grad": "fresher",
    "early": "junior",
    "mid": "mid",
    "senior": "senior",
}


def _options(pairs) -> list[QuestionOption]:
    return [QuestionOption(value=v, label=label) for v, label in pairs]


def _stage_label(p: Profile) -> str:
    if p.stage == "student":
        year = (
            f"{p.study_year}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(p.study_year or 0, 'th') }-year " if p.study_year else ""
        )
        grad = f" (graduating {p.grad_year})" if p.grad_year else ""
        return f"a {year}student{grad}"
    return {
        "fresh_grad": "a fresh graduate",
        "early": "1–3 years into work",
        "mid": "3–7 years into work",
        "senior": "7+ years into work",
    }[p.stage]


def _targets(base: Profile) -> list[Question]:
    qs = [
        Question(
            id="stage",
            kind="stage",
            target_id="stage",
            prompt=f"We read you as {_stage_label(base)}. Is that right?",
            options=_options(STAGE_OPTIONS),
        )
    ]
    for g in base.gaps:
        qs.append(
            Question(
                id=g.id,
                kind="gap",
                target_id=g.id,
                allow_text=True,
                options=_options(GAP_OPTIONS),
                prompt=f"What were you doing from {month_label(g.start)} to {month_label(g.end)} ({g.months} months)?"
                if g.precise
                else f"What were you doing between {g.start[:4]} and {g.end[:4]}?",
            )
        )
    for s in base.stints:
        if s.short:
            qs.append(
                Question(
                    id=f"stint:{s.entry_id}",
                    kind="stint",
                    target_id=s.entry_id,
                    options=_options(STINT_OPTIONS),
                    prompt=f"Your {s.months} months at {s.organization}: what kind of role was it?",
                )
            )
    work = [s for s in base.stints if s.kind in FULL_TIME and s.start]
    latest = max(work, key=lambda s: (s.end is None, s.end or "", s.start)) if work else None
    if latest and latest.employer_kind == "unknown":
        qs.append(
            Question(
                id=f"employer:{latest.entry_id}",
                kind="employer",
                target_id=latest.entry_id,
                options=_options(EMPLOYER_OPTIONS),
                prompt=f"What kind of company is {latest.organization}?",
            )
        )
    seen = set()
    for p in base.projects:
        for c in p.facts.custom_names:
            key = c.name.lower()
            if not c.what and key not in seen:
                seen.add(key)
                qs.append(
                    Question(
                        id=f"name:{key}",
                        kind="custom_name",
                        target_id=p.project_id,
                        allow_text=True,
                        options=_options(NAME_OPTIONS),
                        prompt=f"What is {c.name}? Add what it does in a few words.",
                    )
                )
    for s in base.stints:
        if s.kind == "internship":
            qs.append(
                Question(
                    id=f"intern:{s.entry_id}",
                    kind="internship",
                    target_id=s.entry_id,
                    options=_options(INTERN_OPTIONS),
                    prompt=f"Your internship at {s.organization} was…",
                )
            )
    return qs


def apply_answers(
    base: Profile, answers: dict[str, Answer], resume: ResumeDoc, jd: JDAnalysis, kb: Knowledge, strict: bool = True
) -> Profile:
    """Pure: the unanswered profile with these answers applied. Unknown ids or options raise ValueError, or are
    dropped when not strict (a tailored resume can retire a question, e.g. a stint now labelled "(Contract)")."""
    valid = {q.id: q for q in _targets(base)}
    kept = {}
    for qid, a in answers.items():
        problem = (
            f"unknown question: {qid}"
            if qid not in valid
            else f"invalid answer for {qid}: {a.value}"
            if a.value not in {o.value for o in valid[qid].options}
            else None
        )
        if problem and strict:
            raise ValueError(problem)
        if not problem:
            kept[qid] = a
    answers = kept
    p = base.model_copy(deep=True)
    stints = {s.entry_id: s for s in p.stints}
    for qid, a in answers.items():
        kind, _, target = qid.partition(":")
        if kind == "stage":
            stage, _, year = a.value.partition(":")
            p.stage, p.study_year = stage, int(year) if year else None  # type: ignore[assignment]
        elif kind == "employer":
            stints[target].employer_kind = a.value  # type: ignore[assignment]
        elif kind == "intern" and a.value == "virtual":
            stints[target].kind = "virtual_program"
        elif kind == "stint" and a.value == "internship":
            stints[target].kind, stints[target].short = "internship", False
    p.moves = detect_moves(p.stints, jd, kb)
    explained = {qid.split(":", 1)[1] for qid in answers if qid.startswith("name:")}
    if explained:
        entries = {e.id: e for e in resume.projects}
        p.projects = [
            score_project(entries[r.project_id], r.facts, kb, explained) if r.project_id in entries else r
            for r in p.projects
        ]
    p.answers = dict(answers)
    return p


def make_questions(
    base: Profile,
    answers: dict[str, Answer],
    resume: ResumeDoc,
    jd: JDAnalysis,
    ev: Evidence,
    region_key: Region,
    kb: Knowledge,
) -> list[Question]:
    """Stage first, then answered questions plus the unanswered ones whose best answer could add the most overall
    points, up to six in all."""
    weight = kb.regions[region_key].weights.get("story", 0)

    def story(ans: dict[str, Answer]) -> int:
        sub = score_story(apply_answers(base, ans, resume, jd, kb), resume, jd, ev, region_key, kb)
        return sub.score if sub else 0

    answers = {k: v for k, v in answers.items() if k in {q.id for q in _targets(base)}}
    current = story(answers)
    stage, *rest = _targets(base)
    for q in rest:
        best = max(story({**answers, q.id: Answer(value=o.value)}) for o in q.options)
        q.impact = round(max(0, best - current) * weight, 1)
    rest.sort(key=lambda q: (-q.impact, KIND_ORDER[q.kind]))
    # Answered questions stay visible so they can be changed; the rest fill the remaining slots.
    room = max(0, MAX_QUESTIONS - 1 - sum(q.id in answers for q in rest))
    keep = {q.id for q in rest if q.id in answers} | set([q.id for q in rest if q.id not in answers][:room])
    return [stage, *(q for q in rest if q.id in keep)]


def rescore(analysis: Analysis, answers: dict[str, Answer], kb: Knowledge) -> RescoreResponse:
    """New profile, scores and insights from the stored analysis plus answers. Evidence is reused, so JD match
    never changes here, and no model is called."""
    from app.profile import build_profile
    from app.scoring import score_all
    from app.scoring.ats import missing_keywords
    from app.scoring.insights import build_insights

    if analysis.profile is None or not analysis.profile.as_of:
        raise ValueError("unknown question: this analysis has no career profile; run it again")
    as_of = analysis.profile.as_of
    today = date(int(as_of[:4]), int(as_of[5:7]), 1)
    # facts come back from the client: keep only names that are really in this resume, capped per project
    source = analysis.resume_text + "\n" + render_plain(analysis.resume)
    facts = clean_facts([r.facts for r in analysis.profile.projects], analysis.resume, source, kb)
    profile = build_profile(
        analysis.resume,
        analysis.jd,
        analysis.evidence,
        facts,
        analysis.region,
        kb,
        today,
        answers=answers,
        rules_only=analysis.profile.rules_only,
    )
    resume = analysis.resume
    if "stage" in answers:
        resume = resume.model_copy(update={"level": STAGE_LEVEL[profile.stage]})
    scores = score_all(
        analysis.resume_text, analysis.layout, resume, analysis.jd, analysis.evidence, analysis.region, kb, profile
    )
    insights = build_insights(
        scores,
        analysis.jd,
        analysis.evidence,
        kb.regions[analysis.region],
        missing_keywords(analysis.resume_text, analysis.jd, kb),
        resume.level,
    )
    return RescoreResponse(profile=profile, scores=scores, insights=insights, level=resume.level)

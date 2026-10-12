"""Content quality against recruiter standards: quantified impact, verbs, length, impact-vs-duty, hygiene, summary."""

import re

from app.knowledge.models import Knowledge
from app.resume_ops import iter_bullets
from app.schemas import Explanation, ResumeDoc, SubScore
from app.scoring.aggregate import round_half_up
from app.text_utils import contains_term, normalize

METRIC = re.compile(r"[\d%₹$€£]")
PRONOUN = re.compile(r"\b(i|me|my)\b")


def _first_word(text: str) -> str:
    words = re.findall(r"[a-z]+", normalize(text))
    return words[0] if words else ""


def score_quality(resume: ResumeDoc, kb: Knowledge) -> SubScore:
    lex = kb.lexicons
    bullets = [b for _, _, b in iter_bullets(resume, ["experience", "projects"])]
    if not bullets:
        note = Explanation(
            signal="no_bullets",
            impact=-100,
            detail="No experience or project bullets to assess.",
            fix="Describe what you did and its result in 3–5 bullets per role or project.",
        )
        return SubScore(key="quality", score=0, explanations=[note])

    n = len(bullets)
    ex: list[Explanation] = []
    norm = [normalize(b.text) for b in bullets]

    with_metric = sum(bool(METRIC.search(b.text)) for b in bullets)
    quantified = 30 * min(1.0, (with_metric / n) / 0.5)
    if quantified < 30:
        ex.append(
            Explanation(
                signal="unquantified",
                impact=quantified - 30,
                detail=f"{with_metric}/{n} bullets carry a number; recruiters expect at least half.",
                fix="Add scale or outcome: %, ₹/$, users, time saved, team size.",
            )
        )

    weak = [b.text for b, t in zip(bullets, norm, strict=True) if any(t.startswith(w) for w in lex.weak_openers)]
    strong = sum(
        _first_word(b.text) in lex.action_verbs and not any(t.startswith(w) for w in lex.weak_openers)
        for b, t in zip(bullets, norm, strict=True)
    )
    action = 20 * strong / n
    if weak:
        ex.append(
            Explanation(
                signal="weak_opener",
                impact=-20 * len(weak) / n,
                detail="Weak openers: " + "; ".join(w[:60] for w in weak[:3]),
                fix="Start with a strong past-tense verb: Built, Led, Reduced, Launched.",
            )
        )
    elif action < 20:
        ex.append(
            Explanation(
                signal="no_action_verb",
                impact=action - 20,
                detail=f"{n - strong}/{n} bullets don't open with an action verb.",
                fix="Lead every bullet with what you did.",
            )
        )

    good_len = sum(8 <= len(b.text.split()) <= 35 for b in bullets)
    length = 15 * good_len / n
    if good_len < n:
        ex.append(
            Explanation(
                signal="bullet_length",
                impact=length - 15,
                detail=f"{n - good_len} bullets are too short (<8 words) or too long (>35).",
                fix="Aim for one to two lines: action, scope, result.",
            )
        )

    impact_share = sum(b.kind == "impact" for b in bullets) / n
    impact = 15 * min(1.0, impact_share / 0.6)
    if impact < 15:
        ex.append(
            Explanation(
                signal="duty_heavy",
                impact=impact - 15,
                detail=f"{round(impact_share * 100)}% of bullets state an outcome; aim for 60%+.",
                fix="Rewrite duties as achievements: what changed because of you?",
            )
        )

    hygiene = 10.0
    pronoun_bullets = sum(bool(PRONOUN.search(t)) for t in norm)
    if pronoun_bullets:
        hygiene -= 2 * pronoun_bullets
        ex.append(
            Explanation(
                signal="first_person",
                impact=-2 * pronoun_bullets,
                detail=f"{pronoun_bullets} bullet(s) use I/me/my.",
                fix="Drop pronouns; start with the verb.",
            )
        )
    corpus = " ".join([resume.summary or "", *(b.text for b in bullets)])
    buzz = [w for w in lex.buzzwords if contains_term(corpus, w)]
    if buzz:
        hygiene -= 2 * len(buzz)
        ex.append(
            Explanation(
                signal="buzzwords",
                impact=-2 * len(buzz),
                detail="Clichés: " + ", ".join(buzz[:6]),
                fix="Replace adjectives with evidence of the trait.",
            )
        )
    hygiene = max(0.0, hygiene)

    if not resume.summary:
        summary = 0.0
        ex.append(
            Explanation(
                signal="summary_missing",
                impact=-10,
                detail="No summary.",
                fix="Add 2–3 lines: role, years, domain, signature achievement.",
            )
        )
    else:
        words = len(resume.summary.split())
        generic = any(normalize(resume.summary).startswith(c) for c in lex.objective_cliches)
        summary = 10.0 if 20 <= words <= 80 and not generic else 4.0
        if generic:
            ex.append(
                Explanation(
                    signal="summary_generic",
                    impact=-6,
                    detail="Summary reads as a generic objective.",
                    fix="State what you offer, not what you seek.",
                )
            )
        elif summary < 10:
            ex.append(
                Explanation(
                    signal="summary_length",
                    impact=-6,
                    detail=f"Summary is {words} words; 20–80 reads best.",
                    fix="Keep it to 2–3 specific lines.",
                )
            )

    ex.sort(key=lambda e: e.impact)
    total = quantified + action + length + impact + hygiene + summary
    return SubScore(key="quality", score=round_half_up(total), explanations=ex)

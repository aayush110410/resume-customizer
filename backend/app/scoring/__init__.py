from app.knowledge.models import Knowledge
from app.schemas import Evidence, JDAnalysis, LayoutReport, Profile, Region, ResumeDoc, ScoreReport
from app.scoring.aggregate import build_report
from app.scoring.ats import score_ats
from app.scoring.match import score_match
from app.scoring.quality import score_quality
from app.scoring.region import score_region


def score_all(
    text: str,
    layout: LayoutReport,
    resume: ResumeDoc,
    jd: JDAnalysis,
    ev: Evidence,
    region_key: Region,
    kb: Knowledge,
    profile: Profile | None = None,
) -> ScoreReport:
    # Imported here to avoid a circular import (app.profile.story imports app.scoring.aggregate).
    from app.profile.story import score_story

    region = kb.regions[region_key]
    match, knockouts = score_match(jd, ev, resume.total_years_experience)
    subs = [
        match,
        score_ats(text, layout, resume, jd, region, kb),
        score_quality(resume, kb),
        score_region(text, layout, resume, jd, region),
    ]
    if profile is not None and (story := score_story(profile, resume, jd, ev, region_key, kb)):
        subs.append(story)
    return build_report(subs, region.weights, knockouts)

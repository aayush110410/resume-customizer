from app.knowledge.models import Knowledge
from app.schemas import Evidence, JDAnalysis, LayoutReport, Region, ResumeDoc, ScoreReport
from app.scoring.aggregate import build_report
from app.scoring.ats import score_ats
from app.scoring.match import score_match
from app.scoring.quality import score_quality
from app.scoring.region import score_region


def score_all(
    text: str, layout: LayoutReport, resume: ResumeDoc, jd: JDAnalysis, ev: Evidence, region_key: Region, kb: Knowledge
) -> ScoreReport:
    region = kb.regions[region_key]
    match, knockouts = score_match(jd, ev, resume.total_years_experience)
    subs = [
        match,
        score_ats(text, layout, resume, jd, region, kb),
        score_quality(resume, kb),
        score_region(text, layout, resume, jd, region),
    ]
    return build_report(subs, region.weights, knockouts)

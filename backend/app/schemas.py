"""Shared data contract between the pipeline stages, the API and the frontend (snake_case end to end)."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

Region = Literal["india", "international"]
Level = Literal["fresher", "junior", "mid", "senior", "executive"]
EmployerType = Literal["product_startup", "it_services", "gcc", "consulting_mba", "bfsi", "psu_govt", "other"]
Importance = Literal["must", "should", "nice"]
ReqType = Literal["hard_skill", "soft_skill", "experience", "education", "certification", "domain", "tool"]
MatchStatus = Literal["strong", "partial", "transferable", "missing"]
SectionKey = Literal["summary", "skills", "experience", "projects", "education", "achievements"]
Tone = Literal["conservative", "balanced", "bold"]
ScoreKey = Literal["match", "ats", "quality", "region", "story"]
Stage = Literal["student", "fresh_grad", "early", "mid", "senior"]
EmployerKind = Literal["startup", "product", "it_services", "mnc", "mega_mnc", "govt", "unknown"]
StintKind = Literal["job", "internship", "apprenticeship", "trainee", "freelance", "virtual_program"]
MoveKind = Literal["startup_to_mnc", "mnc_to_mega", "services_to_product", "field_switch"]
QuestionKind = Literal["stage", "gap", "stint", "employer", "custom_name", "internship"]


# --- Resume -----------------------------------------------------------------------------------------------


class Bullet(BaseModel):
    id: str = ""
    text: str
    kind: Literal["impact", "duty", "other"] = "other"


class Entry(BaseModel):
    id: str = ""
    title: str
    organization: str
    location: str | None = None
    start: str | None = None
    end: str | None = None
    bullets: list[Bullet] = []


class Contact(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    links: list[str] = []


class SkillGroup(BaseModel):
    name: str
    items: list[str]


class OtherSection(BaseModel):
    id: str = ""
    name: str
    bullets: list[Bullet] = []


class ResumeDoc(BaseModel):
    contact: Contact
    summary: str | None = None
    skills: list[SkillGroup] = []
    experience: list[Entry] = []
    projects: list[Entry] = []
    education: list[Entry] = []
    achievements: list[Bullet] = []
    other_sections: list[OtherSection] = []
    total_years_experience: float = 0
    level: Level = "junior"


class LayoutReport(BaseModel):
    file_type: Literal["pdf", "docx", "generated"]
    pages: int
    char_count: int
    word_count: int
    multi_column: bool = False
    has_tables: bool = False
    image_count: int = 0
    hidden_chars: int = 0
    header_footer_text: bool = False


class ParsedResume(BaseModel):
    text: str
    layout: LayoutReport


# --- Job description ----------------------------------------------------------------------------------------


class Requirement(BaseModel):
    id: str = ""
    text: str
    type: ReqType
    importance: Importance
    keywords: list[str] = []


class JDAnalysis(BaseModel):
    is_job_description: bool
    title: str
    company: str | None = None
    role_family: str
    employer_type: EmployerType
    seniority: Level
    min_years: float | None = None
    location: str | None = None
    suggested_region: Region
    spelling: Literal["us", "uk", "unknown"] = "unknown"
    requirements: list[Requirement]
    ats_keywords: list[str]


# --- Evidence ----------------------------------------------------------------------------------------------


class RequirementMatch(BaseModel):
    requirement_id: str
    status: MatchStatus
    bullet_ids: list[str] = []
    quote: str | None = None
    rationale: str
    verified: bool = True


class Gap(BaseModel):
    requirement_id: str | None = None
    title: str
    action: str
    suggested_bullet: str | None = None


class RecruiterVerdict(BaseModel):
    decision: Literal["shortlist", "maybe", "reject"]
    first_impression: str
    reasons: list[str]


class PersonalizedTip(BaseModel):
    tip_id: str
    advice: str


class Evidence(BaseModel):
    matches: list[RequirementMatch]
    gaps: list[Gap]
    recruiter: RecruiterVerdict
    tips: list[PersonalizedTip] = []


# --- Career profile ----------------------------------------------------------------------------------------


class Stint(BaseModel):
    entry_id: str
    organization: str
    title: str
    start: str | None = None  # "YYYY-MM"
    end: str | None = None  # "YYYY-MM"; None while current
    months: int | None = None
    precise: bool = False  # both ends carry a month
    kind: StintKind = "job"
    employer_kind: EmployerKind = "unknown"
    field: str | None = None
    short: bool = False


class CareerGap(BaseModel):
    id: str
    after_entry_id: str | None = None
    start: str
    end: str
    months: int
    precise: bool = True  # False when a bounding date gave only a year: then months is a lower bound


class Move(BaseModel):
    kind: MoveKind
    from_label: str
    to_label: str
    target: bool = False


class CustomName(BaseModel):
    name: str
    what: str | None = None
    quote: str | None = None


class ProjectFacts(BaseModel):
    project_id: str
    purpose: str | None = None
    users: str | None = None
    scale: str | None = None
    links: list[str] = []
    tutorial_pattern: str | None = None
    extension: str | None = None
    custom_names: list[CustomName] = []


class ProjectFactsBatch(BaseModel):
    projects: list[ProjectFacts]


class ProjectRead(BaseModel):
    project_id: str
    title: str
    score: int
    notes: list[str] = []
    facts: ProjectFacts


class QuestionOption(BaseModel):
    value: str
    label: str


class Question(BaseModel):
    id: str
    kind: QuestionKind
    target_id: str
    prompt: str
    options: list[QuestionOption]
    allow_text: bool = False
    impact: float = 0.0


class Answer(BaseModel):
    value: str
    text: Annotated[str, Field(max_length=80)] | None = None
    state_on_resume: bool = False


class Profile(BaseModel):
    stage: Stage
    study_year: int | None = None
    grad_year: int | None = None
    stints: list[Stint] = []
    gaps: list[CareerGap] = []
    moves: list[Move] = []
    projects: list[ProjectRead] = []
    questions: list[Question] = []
    answers: dict[str, Answer] = {}
    rules_only: bool = False
    as_of: str = ""  # YYYY-MM the profile was judged at, so re-scores stay deterministic


# --- Scores and insights -----------------------------------------------------------------------------------


class Explanation(BaseModel):
    signal: str
    impact: float  # sub-score points; negative = points lost
    detail: str
    fix: str | None = None


class SubScore(BaseModel):
    key: ScoreKey
    score: int
    explanations: list[Explanation] = []


class ScoreReport(BaseModel):
    overall: int
    weights: dict[str, float]
    subscores: dict[str, SubScore]
    knockouts: list[str] = []


class Action(BaseModel):
    title: str
    detail: str
    est_gain: float
    source: ScoreKey
    suggested_bullet: str | None = None


class Insights(BaseModel):
    actions: list[Action]
    tips: list[PersonalizedTip]
    recruiter: RecruiterVerdict
    missing_keywords: list[str]


class Analysis(BaseModel):
    region: Region
    resume: ResumeDoc
    resume_text: str
    layout: LayoutReport
    jd: JDAnalysis
    evidence: Evidence
    scores: ScoreReport
    insights: Insights
    prompt_version: str
    models: dict[str, str]
    profile: Profile | None = None
    jd_text: str = ""  # the pasted JD, so the tailoring guard can spot borrowed wording


class RescoreRequest(BaseModel):
    analysis: Analysis
    answers: dict[str, Answer] = {}


class RescoreResponse(BaseModel):
    profile: Profile
    level: Level  # the stage answer can change it; tailoring must use the same level
    scores: ScoreReport
    insights: Insights


# --- Tailoring ---------------------------------------------------------------------------------------------


class SummaryItem(BaseModel):
    type: Literal["summary"]
    text: str


class SkillsItem(BaseModel):
    type: Literal["skills"]
    groups: list[SkillGroup]


class BulletItem(BaseModel):
    type: Literal["bullet"]
    entry_id: str
    source_id: str
    text: str
    addresses: list[str] = []


class ChangeItem(BaseModel):
    type: Literal["change"]
    target_id: str
    what: str
    why: str
    requirement_ids: list[str] = []


TailorItem = Annotated[SummaryItem | SkillsItem | BulletItem | ChangeItem, Field(discriminator="type")]


class TailorBatch(BaseModel):
    items: list[TailorItem]


class FabricationFlag(BaseModel):
    target_id: str
    tokens: list[str]
    reason: str


class TailorSettings(BaseModel):
    sections: list[SectionKey]
    tone: Tone = "balanced"
    model: str | None = None


class TailorRequest(BaseModel):
    analysis: Analysis
    settings: TailorSettings


class TailoredVersion(BaseModel):
    id: str
    created_at: str
    settings: TailorSettings
    resume: ResumeDoc
    changes: list[ChangeItem]
    flags: list[FabricationFlag]
    scores: ScoreReport
    model: str


class CoverLetterRequest(BaseModel):
    analysis: Analysis
    resume: ResumeDoc
    tone: Tone = "balanced"
    model: str | None = None
    notice_period: str | None = None
    work_authorization: str | None = None


class LetterBody(BaseModel):
    """What the model writes; code adds the date, recipient, subject, greeting and sign-off."""

    opening: str
    proof: list[str]
    motivation: str
    closing: str


class CoverLetter(BaseModel):
    date: str
    recipient: list[str]
    subject: str | None = None
    salutation: str
    paragraphs: list[str]
    sign_off: str
    name: str
    removed: list[str] = []  # sentences dropped because the resume doesn't support them


class ExportRequest(BaseModel):
    kind: Literal["resume", "cover_letter"]
    format: Literal["pdf", "docx", "txt"]
    region: Region
    resume: ResumeDoc | None = None
    cover_letter: str | None = None
    contact: Contact | None = None

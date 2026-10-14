// Mirrors backend/app/schemas.py one-to-one (snake_case on purpose: the JSON is passed through untouched).

export type Region = "india" | "international";
export type Level = "fresher" | "junior" | "mid" | "senior" | "executive";
export type EmployerType = "product_startup" | "it_services" | "gcc" | "consulting_mba" | "bfsi" | "psu_govt" | "other";
export type Importance = "must" | "should" | "nice";
export type ReqType = "hard_skill" | "soft_skill" | "experience" | "education" | "certification" | "domain" | "tool";
export type MatchStatus = "strong" | "partial" | "transferable" | "missing";
export type SectionKey = "summary" | "skills" | "experience" | "projects" | "education" | "achievements";
export type Tone = "conservative" | "balanced" | "bold";
export type ScoreKey = "match" | "ats" | "quality" | "region" | "story";
export type Stage = "student" | "fresh_grad" | "early" | "mid" | "senior";
export type EmployerKind = "startup" | "product" | "it_services" | "mnc" | "mega_mnc" | "govt" | "unknown";
export type StintKind = "job" | "internship" | "apprenticeship" | "trainee" | "freelance" | "virtual_program";
export type MoveKind = "startup_to_mnc" | "mnc_to_mega" | "services_to_product" | "field_switch";
export type QuestionKind = "stage" | "gap" | "stint" | "employer" | "custom_name" | "internship";
export type StageId = "parsing" | "understanding" | "matching" | "scoring" | "tailoring" | "verifying" | "rescoring";
export type StageStatus = "idle" | "active" | "done" | "error";

export const STAGES: StageId[] = ["parsing", "understanding", "matching", "scoring", "tailoring", "verifying", "rescoring"];
export const SECTION_KEYS: SectionKey[] = ["summary", "skills", "experience", "projects", "education", "achievements"];
export const DEFAULT_SECTIONS: SectionKey[] = ["summary", "skills", "experience", "projects"];

export interface Bullet { id: string; text: string; kind: "impact" | "duty" | "other" }
export interface Entry {
  id: string; title: string; organization: string; location: string | null;
  start: string | null; end: string | null; bullets: Bullet[];
}
export interface Contact { name: string; email: string | null; phone: string | null; location: string | null; links: string[] }
export interface SkillGroup { name: string; items: string[] }
export interface OtherSection { id: string; name: string; bullets: Bullet[] }
export interface ResumeDoc {
  contact: Contact; summary: string | null; skills: SkillGroup[]; experience: Entry[]; projects: Entry[];
  education: Entry[]; achievements: Bullet[]; other_sections: OtherSection[]; total_years_experience: number; level: Level;
}
export interface LayoutReport {
  file_type: "pdf" | "docx" | "generated"; pages: number; char_count: number; word_count: number; multi_column: boolean;
  has_tables: boolean; image_count: number; hidden_chars: number; header_footer_text: boolean;
}
export interface Requirement { id: string; text: string; type: ReqType; importance: Importance; keywords: string[] }
export interface JDAnalysis {
  is_job_description: boolean; title: string; company: string | null; role_family: string; employer_type: EmployerType;
  seniority: Level; min_years: number | null; location: string | null; suggested_region: Region;
  spelling: "us" | "uk" | "unknown"; requirements: Requirement[]; ats_keywords: string[];
}
export interface RequirementMatch {
  requirement_id: string; status: MatchStatus; bullet_ids: string[]; quote: string | null; rationale: string; verified: boolean;
}
export interface Gap { requirement_id: string | null; title: string; action: string; suggested_bullet: string | null }
export interface RecruiterVerdict { decision: "shortlist" | "maybe" | "reject"; first_impression: string; reasons: string[] }
export interface PersonalizedTip { tip_id: string; advice: string }
export interface Evidence { matches: RequirementMatch[]; gaps: Gap[]; recruiter: RecruiterVerdict; tips: PersonalizedTip[] }
export interface Explanation { signal: string; impact: number; detail: string; fix: string | null }
export interface SubScore { key: ScoreKey; score: number; explanations: Explanation[] }
export interface ScoreReport {
  overall: number; weights: Record<string, number>; subscores: Record<string, SubScore>; knockouts: string[];
}
export interface Action { title: string; detail: string; est_gain: number; source: ScoreKey; suggested_bullet: string | null }
export interface Insights { actions: Action[]; tips: PersonalizedTip[]; recruiter: RecruiterVerdict; missing_keywords: string[] }
export interface Stint {
  entry_id: string; organization: string; title: string; start: string | null; end: string | null; months: number | null;
  precise: boolean; kind: StintKind; employer_kind: EmployerKind; field: string | null; short: boolean;
}
export interface CareerGap { id: string; after_entry_id: string | null; start: string; end: string; months: number }
export interface Move { kind: MoveKind; from_label: string; to_label: string; target: boolean }
export interface CustomName { name: string; what: string | null; quote: string | null }
export interface ProjectFacts {
  project_id: string; purpose: string | null; users: string | null; scale: string | null; links: string[];
  tutorial_pattern: string | null; extension: string | null; custom_names: CustomName[];
}
export interface ProjectRead { project_id: string; title: string; score: number; notes: string[]; facts: ProjectFacts }
export interface QuestionOption { value: string; label: string }
export interface Question {
  id: string; kind: QuestionKind; target_id: string; prompt: string; options: QuestionOption[]; allow_text: boolean; impact: number;
}
export interface Answer { value: string; text: string | null; state_on_resume: boolean }
export interface Profile {
  stage: Stage; study_year: number | null; grad_year: number | null; stints: Stint[]; gaps: CareerGap[]; moves: Move[];
  projects: ProjectRead[]; questions: Question[]; answers: Record<string, Answer>; rules_only: boolean; as_of: string;
}
export interface Analysis {
  region: Region; resume: ResumeDoc; resume_text: string; layout: LayoutReport; jd: JDAnalysis; evidence: Evidence;
  scores: ScoreReport; insights: Insights; prompt_version: string; models: Record<string, string>;
  profile?: Profile | null; // absent on analyses saved before the career profile existed
  jd_text?: string; // the pasted JD (for the tailoring guard); absent on older saved analyses
}
export interface RescoreResponse { profile: Profile; scores: ScoreReport; insights: Insights; level: Level }
export interface SummaryItem { type: "summary"; text: string }
export interface SkillsItem { type: "skills"; groups: SkillGroup[] }
export interface BulletItem { type: "bullet"; entry_id: string; source_id: string; text: string; addresses: string[] }
export interface ChangeItem { type: "change"; target_id: string; what: string; why: string; requirement_ids: string[] }
export type TailorItem = SummaryItem | SkillsItem | BulletItem | ChangeItem;
export interface FabricationFlag { target_id: string; tokens: string[]; reason: string }
export interface TailorSettings { sections: SectionKey[]; tone: Tone; model: string | null }
export interface TailoredVersion {
  id: string; created_at: string; settings: TailorSettings; resume: ResumeDoc; changes: ChangeItem[];
  flags: FabricationFlag[]; scores: ScoreReport; model: string;
}
export interface CoverLetterRequest {
  analysis: Analysis; resume: ResumeDoc; tone: Tone; model: string | null;
  notice_period: string | null; work_authorization: string | null;
}
export interface ExportRequest {
  kind: "resume" | "cover_letter"; format: "pdf" | "docx" | "txt"; region: Region;
  resume?: ResumeDoc | null; cover_letter?: string | null; contact?: Contact | null;
}
export interface Meta {
  regions: { key: Region; label: string }[]; sections: SectionKey[]; tones: Tone[];
  models: { id: string; role: "analysis" | "writer" }[];
  limits: { max_upload_mb: number; max_pages: number; jd_min_chars: number; jd_max_chars: number };
}
export interface StreamEvent { event: string; data: unknown }
export interface AppErrorInfo { code: string; message: string; retryable: boolean }

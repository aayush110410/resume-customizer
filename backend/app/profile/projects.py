"""Is this project real and worth reading? Scored in code from facts the model quoted (or rules alone).

purpose 25 · original 20 (10 when a tutorial build states its own extension) · real use 20 · numbers 15 ·
technical depth 20 · −5 per custom name nobody explained (cap −15). A coined name ("Zephyr") is never an
unknown skill: it only needs a few words saying what it is.
"""

import re

from app.knowledge.models import Knowledge
from app.schemas import Entry, ProjectFacts, ProjectRead, ResumeDoc
from app.text_utils import contains_term, normalize

URL = re.compile(
    r"\b(?:https?://)?(?:www\.)?[\w-]+(?:\.[\w-]+)*\.(?:com|io|app|dev|in|org|net|ai|me|co|xyz|site)\b(?:/[^\s,;)]*)?",
    re.I,
)
_NUMBER = re.compile(
    r"\d[\d,.]*\s?(%|k\b|m\b|ms\b|x\b|\+|users|requests|rps|qps|downloads|stars|records|rows|transactions|"
    r"customers|students|orders|images|documents|teams|accuracy|members|visitors|installs)",
    re.I,
)
_DEPTH = re.compile(
    r"\b(auth\w*|oauth|jwt|cach\w+|redis|queue\w*|kafka|rabbitmq|concurren\w+|multi-?thread\w*|websockets?|"
    r"trained|fine-?tun\w+|payments?|stripe|razorpay|rate[- ]limit\w*|shard\w+|replicat\w+|pipelines?|"
    r"scheduler|elasticsearch|search index|recommendation engine|compiler|interpreter|consensus|encryption)\b",
    re.I,
)
_USERS = re.compile(
    r"\bused by\b|\b\d[\d,]*\+?\s+(?:\w+\s+)?(users|customers|students|residents|members|visitors|teams|people|"
    r"clubs|analysts|reps|downloads|installs)\b",
    re.I,
)
MAX_NAME_PENALTY = 15
MAX_NAMES = 3  # coined names judged per project


def clean_facts(facts: list[ProjectFacts], resume: ResumeDoc, source: str, kb: Knowledge) -> list[ProjectFacts]:
    """Facts for this resume's projects only, with custom names that appear in the resume text (and are not known
    skills), at most MAX_NAMES each. Applied to facts coming back from the client on a re-score."""
    ids = {e.id for e in resume.projects}
    out = []
    for f in facts:
        if f.project_id not in ids:
            continue
        names = [
            c for c in f.custom_names if contains_term(source, c.name) and not kb.synonyms.groups.get(normalize(c.name))
        ]
        out.append(f.model_copy(update={"custom_names": names[:MAX_NAMES]}))
    return out


def _text(entry: Entry) -> str:
    return " ".join([entry.title, entry.organization, *(b.text for b in entry.bullets)])


def _technologies(text: str, kb: Knowledge) -> int:
    """Distinct known technologies named in the text: 1–3 word n-grams looked up in the synonym index (linear in
    the text, instead of one regex per known variant)."""
    words = [w.strip(",;:()[]'\"") for w in normalize(text).split()]
    words = [w.rstrip(".") if w.count(".") == 1 and w.endswith(".") else w for w in words]
    seen = set()
    for n in (1, 2, 3):
        for i in range(len(words) - n + 1):
            gram = " ".join(words[i : i + n])
            if len(gram) > 2 and (group := kb.synonyms.groups.get(gram)):
                seen.add(group)
    return len(seen)


def rule_facts(entry: Entry, kb: Knowledge) -> ProjectFacts:
    """What code alone can read when the model is unavailable. Tutorial builds are judged from the title only:
    a bullet like "EMI calculator API used by 30 analysts" is not a calculator tutorial."""
    text = _text(entry)
    used = next((b.text for b in entry.bullets if _USERS.search(b.text)), None)
    return ProjectFacts(
        project_id=entry.id,
        purpose=entry.bullets[0].text if entry.bullets else None,
        users=used,
        scale=used if used and re.search(r"\d", used) else None,
        links=[m.group(0) for m in URL.finditer(text)],
        tutorial_pattern=next((t for t in kb.tutorial_projects if contains_term(entry.title, t)), None),
    )


def score_project(entry: Entry, facts: ProjectFacts, kb: Knowledge, explained: set[str]) -> ProjectRead:
    text = _text(entry)
    notes: list[str] = []
    score = 0
    if facts.purpose:
        score += 25
    else:
        notes.append(f"Say what {entry.title} does and who it is for in the first line.")
    if not facts.tutorial_pattern:
        score += 20
    elif facts.extension:
        score += 10
    else:
        notes.append(f"Reads like a common tutorial build ({facts.tutorial_pattern}). Say what you added beyond it.")
    if facts.users or facts.links or URL.search(text):
        score += 20
    else:
        notes.append("Link the code or a live demo, or say who used it.")
    if facts.scale or _NUMBER.search(text):
        score += 15
    else:
        notes.append("Add one number: users, data size, latency or accuracy.")
    if _technologies(text, kb) >= 3 or _DEPTH.search(text):
        score += 20
    else:
        notes.append("Name the hard part you solved: auth, caching, concurrency, model training, payments.")
    unexplained = [c.name for c in facts.custom_names if not c.what and c.name.lower() not in explained]
    score -= min(MAX_NAME_PENALTY, 5 * len(unexplained))
    notes += [f"Say what {name} is in five words." for name in unexplained]
    return ProjectRead(project_id=entry.id, title=entry.title, score=max(0, min(100, score)), notes=notes, facts=facts)

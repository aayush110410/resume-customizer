"""Canned LLM outputs consistent with the simple_pdf fixture text."""

JD_TEXT = (
    "Backend Engineer (SDE-2), Bengaluru. We are a fintech product company building payment infrastructure. "
    "Requirements: 3+ years of backend development in Python; experience designing REST APIs; hands-on Kubernetes; "
    "Kafka is a plus. You will own services end to end, mentor engineers and improve latency and reliability. "
    "Good to have: Terraform, observability tooling. Location: Bengaluru, India."
)


def resume_payload():
    return {
        "contact": {"name": "Arjun Mehta", "email": "arjun@example.com"},
        "summary": None,
        "skills": [{"name": "Skills", "items": ["Python", "Go", "Kubernetes"]}],
        "experience": [
            {
                "title": "Software Engineer",
                "organization": "Razorpay",
                "start": "Jan 2022",
                "end": "Present",
                "bullets": [
                    {"text": "Reduced p99 latency by 30% for 2M daily payments.", "kind": "impact"},
                    {"text": "Built REST APIs in Python and Go.", "kind": "duty"},
                    {"text": "Led migration to Kubernetes.", "kind": "duty"},
                ],
            }
        ],
        "total_years_experience": 4,
        "level": "mid",
    }


def jd_payload(is_jd=True):
    return {
        "is_job_description": is_jd,
        "title": "Backend Engineer",
        "role_family": "software_engineering",
        "employer_type": "product_startup",
        "seniority": "mid",
        "min_years": 3,
        "location": "Bengaluru",
        "suggested_region": "india",
        "requirements": [
            {"text": "Python backend development", "type": "hard_skill", "importance": "must", "keywords": ["python"]},
            {"text": "REST API design", "type": "hard_skill", "importance": "must", "keywords": ["rest"]},
            {"text": "Kubernetes", "type": "tool", "importance": "should", "keywords": ["k8s"]},
            {"text": "Kafka", "type": "tool", "importance": "nice", "keywords": ["kafka"]},
        ],
        "ats_keywords": ["Python", "REST APIs", "Kubernetes", "Kafka"],
    }


def evidence_payload():
    return {
        "matches": [
            {
                "requirement_id": "r1",
                "status": "strong",
                "bullet_ids": ["exp0.b1"],
                "quote": "Built REST APIs in Python and Go",
                "rationale": "x",
            },
            {
                "requirement_id": "r2",
                "status": "strong",
                "bullet_ids": ["exp0.b1"],
                "quote": "Built REST APIs",
                "rationale": "x",
            },
            {
                "requirement_id": "r3",
                "status": "partial",
                "bullet_ids": ["exp0.b2"],
                "quote": "Led migration to Kubernetes",
                "rationale": "x",
            },
            {"requirement_id": "r4", "status": "missing", "rationale": "No Kafka"},
        ],
        "gaps": [
            {
                "requirement_id": "r4",
                "title": "No Kafka",
                "action": "Add Kafka work if any",
                "suggested_bullet": "Built [N] Kafka consumers",
            }
        ],
        "recruiter": {
            "decision": "shortlist",
            "first_impression": "Solid backend profile.",
            "reasons": ["Payments scale"],
        },
        "tips": [],
    }

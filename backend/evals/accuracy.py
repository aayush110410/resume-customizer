"""Judging accuracy against hand labels (evals/golden/labels.yaml), plus run-to-run stability.

Usage: .venv/bin/python -m evals.accuracy --runs 2 --tag baseline
"""

import argparse
import asyncio
import json
from pathlib import Path

import yaml

from app.config import Settings, build_targets
from app.knowledge.loader import load_knowledge
from app.llm.client import LLMClient
from app.llm.tasks import analyze_jd, match_evidence, structure_resume
from app.parsing.extract import parse_resume
from app.schemas import LayoutReport
from app.scoring import score_all
from app.text_utils import estimate_pages
from evals.metrics import label_accuracy, stability

ROOT = Path(__file__).resolve().parent
RESUMES = {
    "sample": lambda: parse_resume((ROOT.parents[1] / "frontend/public/samples/sample-resume.pdf").read_bytes(), 5),
    "strong_swe": lambda: (ROOT / "golden/strong_swe.txt").read_text(),
}


async def main(runs: int, tag: str) -> None:
    kb, llm = load_knowledge(), LLMClient(build_targets(Settings()), 180)
    spec = yaml.safe_load((ROOT / "golden/labels.yaml").read_text())
    jd_text = (ROOT / "golden" / spec["jd"]).read_text()
    report = {"tag": tag, "pairs": {}}
    total_ok = total = 0
    for pair in spec["pairs"]:
        src = RESUMES[pair["resume"]]()
        text = src if isinstance(src, str) else src.text
        layout = (
            src.layout
            if not isinstance(src, str)
            else LayoutReport(
                file_type="generated",
                pages=estimate_pages(len(text.split())),
                char_count=len(text),
                word_count=len(text.split()),
            )
        )
        overall, match, wrong = [], [], []
        for _ in range(runs):
            r, j = await asyncio.gather(structure_resume(llm, text), analyze_jd(llm, jd_text, kb))
            ev = (await match_evidence(llm, r.value, text, j.value, kb.regions["india"], kb)).value
            rep = score_all(text, layout, r.value, j.value, ev, "india", kb)
            acc = label_accuracy(j.value.requirements, ev, pair["concepts"])
            total_ok, total = total_ok + acc["correct"], total + acc["judged"]
            overall.append(rep.overall)
            match.append(rep.subscores["match"].score)
            wrong += acc["wrong"]
        report["pairs"][pair["resume"]] = {
            "overall": overall,
            "match": match,
            "match_sigma": round(stability(match), 2),
            "wrong": wrong,
        }
    report["accuracy"] = round(total_ok / total, 3) if total else None
    report["judged"] = total
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    (out / f"accuracy-{tag}.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--runs", type=int, default=2)
    p.add_argument("--tag", default="run")
    a = p.parse_args()
    asyncio.run(main(a.runs, a.tag))

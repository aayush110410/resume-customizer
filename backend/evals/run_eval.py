"""Live accuracy checks: score stability across runs, ordering between a strong and a weaker resume, quote grounding.

Usage: .venv/bin/python -m evals.run_eval --runs 3
"""

import argparse
import asyncio
import time
from datetime import UTC, datetime
from pathlib import Path

from app.config import Settings, build_targets
from app.knowledge.loader import load_knowledge
from app.llm.client import LLMClient
from app.llm.tasks import analyze_jd, match_evidence, structure_resume
from app.parsing.extract import parse_resume
from app.schemas import LayoutReport
from app.scoring import score_all
from app.text_utils import estimate_pages
from evals.metrics import grounding_rate, ordering_ok, stability

ROOT = Path(__file__).resolve().parent
SAMPLE_PDF = ROOT.parents[1] / "frontend" / "public" / "samples" / "sample-resume.pdf"


async def analyse(llm, kb, text, layout, jd_text, region="india"):
    r, j = await asyncio.gather(structure_resume(llm, text), analyze_jd(llm, jd_text, kb))
    e = await match_evidence(llm, r.value, text, j.value, kb.regions[region], kb)
    return score_all(text, layout, r.value, j.value, e.value, region, kb), e.value


async def main(runs: int) -> None:
    kb, llm = load_knowledge(), LLMClient(build_targets(Settings()), 180)
    jd_text = (ROOT / "golden" / "jd_sde2_bengaluru.txt").read_text()
    sample = parse_resume(SAMPLE_PDF.read_bytes(), 5)
    strong = (ROOT / "golden" / "strong_swe.txt").read_text()
    strong_layout = LayoutReport(
        file_type="generated",
        pages=estimate_pages(len(strong.split())),
        char_count=len(strong),
        word_count=len(strong.split()),
    )

    started = time.perf_counter()
    sample_runs = [await analyse(llm, kb, sample.text, sample.layout, jd_text) for _ in range(runs)]
    strong_report, strong_ev = await analyse(llm, kb, strong, strong_layout, jd_text)
    overall = [r.overall for r, _ in sample_runs]
    evs = [e for _, e in sample_runs] + [strong_ev]
    lines = [
        f"# Eval {datetime.now(UTC):%Y-%m-%d %H:%M} UTC, models: {', '.join(t.label for t in build_targets(Settings())['analysis'])}",
        "",
        "| Check | Result | Gate |",
        "|---|---|---|",
        f"| Overall-score stability, sample resume × {runs} runs | {overall} → σ = {stability(overall):.2f} | σ ≤ 3 |",
        *(
            f"| {k} stability | {[r.subscores[k].score for r, _ in sample_runs]} | - |"
            for k in ("match", "ats", "quality", "region")
        ),
        f"| Ordering: strong resume > weaker sample | {strong_report.overall} > {overall[0]} → {'PASS' if ordering_ok([(1, strong_report.overall), (2, min(overall))]) else 'FAIL'} | pass |",
        f"| Quote grounding rate | {grounding_rate(evs):.0%} | ≥ 98% |",
        f"| Wall time | {time.perf_counter() - started:.0f}s for {runs + 1} full analyses | - |",
    ]
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    (out / "latest.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    asyncio.run(main(parser.parse_args().runs))

"""Arnés de evals de QuimioResponde: `--offline` (CI) y `--online` (manual)."""

import argparse
import asyncio
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from app.llm.schemas import Answer, Citation
from app.llm.verifier import CitationRejected, verify
from app.retrieval.search import Hit
from harness.metrics import CaseResult, hit_at_k, refusal_correct, summary

TOP_K = 5
ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = ROOT / "cases"
GOLDEN_PATH = ROOT / "fixtures" / "retrieval_golden.json"
REPORT_PATH = ROOT / "reports" / "latest.json"


def main(argv: list[str] | None = None) -> int:
    """Corre los 20 casos y devuelve 0 solo si todos cumplen lo esperado."""
    args = _parse_args(argv)
    if args.online:
        golden, mode = asyncio.run(_record_golden()), "online"
    else:
        golden, mode = _load_golden(), "offline"
    results = (
        _retrieval_results(_load_cases("retrieval"), golden)
        + _refusal_results(_load_cases("refusal"))
        + _citation_results(_load_cases("citation"))
    )
    _print_table(results)
    _write_report(mode, results)
    return 0 if all(result.passed for result in results) else 1


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evals de QuimioResponde")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--offline", action="store_true", help="fixtures pregrabados; no usa red")
    mode.add_argument("--online", action="store_true", help="regenera el golden con Neon y Gemini")
    return parser.parse_args(argv)


def _load_cases(name: str) -> list[dict[str, Any]]:
    return yaml.safe_load((CASES_DIR / f"{name}.yaml").read_text(encoding="utf-8"))


def _load_golden() -> dict[str, list[dict[str, Any]]]:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))["results"]


def _retrieval_results(
    cases: list[dict[str, Any]], golden: dict[str, list[dict[str, Any]]]
) -> list[CaseResult]:
    results = []
    for case in cases:
        predicted = [hit["chunk_id"] for hit in golden.get(case["id"], [])]
        expected = case["expected_chunk_id"]
        passed = hit_at_k(predicted, expected, TOP_K)
        detail = f"{case['expected_article']} · {len(predicted)} hits en el golden"
        results.append(CaseResult(case["id"], "retrieval", "hit", "hit" if passed else "miss", detail))
    return results


def _refusal_results(cases: list[dict[str, Any]]) -> list[CaseResult]:
    results = []
    for case in cases:
        expected = case["expected_refusal_reason"]
        answer = Answer(answer=case["question"], citations=[], refusal_reason=expected)
        try:
            verify(answer, [])
            actual = answer.refusal_reason or ""
        except CitationRejected as rejected:
            actual = rejected.reason.value
        detail = "rechazo sin citas aceptado" if refusal_correct(expected, actual) else "verify falló"
        results.append(CaseResult(case["id"], "refusal", expected, actual, detail))
    return results



def _citation_results(cases: list[dict[str, Any]]) -> list[CaseResult]:
    results = []
    for case in cases:
        hits = [_to_hit(item) for item in case["hits"]]
        answer = Answer(
            answer=case["answer"],
            citations=[
                Citation(chunk_id=item["chunk_id"], quote=item["quote"])
                for item in case["citations"]
            ],
            refusal_reason=case.get("refusal_reason"),
        )
        try:
            verify(answer, hits)
            actual = "accepted"
        except CitationRejected as rejected:
            actual = rejected.reason.value
        results.append(CaseResult(case["id"], "citation", case["expected"], actual, case["description"]))
    return results


def _to_hit(item: dict[str, Any]) -> Hit:
    return Hit(
        chunk_id=item["chunk_id"],
        document_id=item.get("document_id", "eval-doc"),
        article=item.get("article", "Artículo 1°"),
        numeral=None,
        text=item["text"],
        url="https://www.leychile.cl/Consulta/obtxml?opt=7&idNorma=1088802",
        score=1.0,
    )


async def _record_golden() -> dict[str, list[dict[str, Any]]]:
    """Recalcula el golden con `search()` real y lo escribe en fixtures/."""
    from app.db import get_sessionmaker
    from app.retrieval.search import search

    golden: dict[str, list[dict[str, Any]]] = {}
    async with get_sessionmaker()() as session:
        for case in _load_cases("retrieval"):
            hits = await search(session, case["question"], k=TOP_K)
            golden[case["id"]] = [
                {
                    "chunk_id": hit.chunk_id,
                    "article": hit.article,
                    "numeral": hit.numeral,
                    "score": round(hit.score, 6),
                }
                for hit in hits
            ]
            print(f"{case['id']}: " + ", ".join(f"{hit.article} {hit.chunk_id}" for hit in hits))
    payload = {"generated_at": _now(), "k": TOP_K, "results": golden}
    GOLDEN_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return golden


def _print_table(results: list[CaseResult]) -> None:
    header = (
        f"{'case_id':<6} | {'category':<9} | {'result':<6} | {'expected':<22} | "
        f"{'actual':<22} | reason"
    )
    print(header)
    print("-" * len(header))
    for result in results:
        state = "ok" if result.passed else "FAIL"
        print(
            f"{result.case_id:<6} | {result.category:<9} | {state:<6} | {result.expected:<22} | "
            f"{result.actual:<22} | {result.detail}"
        )
    print()
    print(" | ".join(f"{name}={value:.2f}" for name, value in summary(results).items()))


def _write_report(mode: str, results: list[CaseResult]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": _now(),
        "mode": mode,
        "summary": summary(results),
        "results": [asdict(result) | {"passed": result.passed} for result in results],
    }
    REPORT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())

"""Pluggable, offline evaluation hooks for backtranslation traces."""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from .conditions import ConditionTrace


@dataclass(frozen=True)
class EvaluationResult:
    evaluator_id: str
    subject: str
    result: str
    metrics: Mapping[str, Any]
    findings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EvaluationHook(Protocol):
    evaluator_id: str

    def evaluate(self) -> EvaluationResult:
        ...


class CodeSafetyHook:
    evaluator_id = "backtranslation-code-safety/v1"
    blocked_import_roots = {
        "boto3",
        "httpx",
        "os",
        "pathlib",
        "requests",
        "shutil",
        "socket",
        "subprocess",
        "urllib",
    }

    def __init__(self, code_path: Path, forbidden_source_tokens: Sequence[str] = ()) -> None:
        self.code_path = code_path
        self.forbidden_source_tokens = tuple(token for token in forbidden_source_tokens if token)

    def evaluate(self) -> EvaluationResult:
        code = self.code_path.read_text(encoding="utf-8")
        findings: list[str] = []
        imported_roots: set[str] = set()
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return EvaluationResult(
                self.evaluator_id,
                self.code_path.name,
                "fail",
                {"ast_valid": False, "blocked_import_count": 0, "source_token_match_count": 0},
                (f"SyntaxError: {exc.msg}",),
            )
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])
        blocked = sorted(imported_roots & self.blocked_import_roots)
        if blocked:
            findings.append(f"Blocked imports: {', '.join(blocked)}")
        token_matches = sorted(token for token in self.forbidden_source_tokens if token.lower() in code.lower())
        if token_matches:
            findings.append("Source metadata token match detected")
        return EvaluationResult(
            self.evaluator_id,
            self.code_path.name,
            "pass" if not findings else "fail",
            {
                "ast_valid": True,
                "blocked_import_count": len(blocked),
                "source_token_match_count": len(token_matches),
            },
            tuple(findings),
        )


class PairedDeltaHook:
    evaluator_id = "backtranslation-paired-delta/v1"

    def __init__(self, one_shot: ConditionTrace, self_refined: ConditionTrace) -> None:
        self.one_shot = one_shot
        self.self_refined = self_refined

    @staticmethod
    def _final(trace: ConditionTrace):
        return trace.rounds[-1] if trace.rounds else None

    def evaluate(self) -> EvaluationResult:
        findings: list[str] = []
        if self.one_shot.pairing_id != self.self_refined.pairing_id:
            findings.append("Pairing IDs do not match")
        if self.one_shot.case_id != self.self_refined.case_id:
            findings.append("Case IDs do not match")
        if self.self_refined.initial_one_shot_code_hash != self.one_shot.final_code_hash:
            findings.append("Self-refined condition does not start from exact one-shot hash")
        one_final = self._final(self.one_shot)
        self_final = self._final(self.self_refined)
        metrics = {
            "one_shot_technical_pass": bool(one_final and one_final.technical_pass),
            "one_shot_visual_pass": bool(one_final and one_final.visual_pass),
            "self_refined_technical_pass": bool(self_final and self_final.technical_pass),
            "self_refined_visual_pass": bool(self_final and self_final.visual_pass),
            "revision_rounds": max(0, len(self.self_refined.rounds) - 1),
            "lineage_exact": not findings,
        }
        return EvaluationResult(
            self.evaluator_id,
            self.one_shot.pairing_id,
            "pass" if not findings else "fail",
            metrics,
            tuple(findings),
        )


def run_hooks(hooks: Sequence[EvaluationHook]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for hook in hooks:
        try:
            results.append(hook.evaluate().to_dict())
        except Exception as exc:
            results.append(
                EvaluationResult(
                    evaluator_id=getattr(hook, "evaluator_id", "unknown-evaluator"),
                    subject="unknown",
                    result="error",
                    metrics={},
                    findings=(str(exc),),
                ).to_dict()
            )
    return results

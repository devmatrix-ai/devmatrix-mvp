"""
Generation Manifest - Per-File Traceability for Code Generation

Phase 2: Provides complete audit trail for every generated file.

Features:
- Per-file metadata: stratum, atoms, source, QA checks
- LLM usage tracking: model, tokens, slots
- Stratum summary: template/ast/llm distribution
- Diff support: compare manifests between generations
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

from src.services.stratum_classification import Stratum, AtomKind

logger = logging.getLogger(__name__)


class ManifestVersion(str, Enum):
    """Manifest format version."""
    V1 = "1.0"


@dataclass
class FileManifest:
    """Metadata for a single generated file."""
    file_path: str
    atoms: List[str]  # e.g., ["entity:Product", "entity:Order"]
    stratum: str  # template, ast, llm
    source: str  # e.g., "ApplicationIR.entities", "template:dockerfile"
    qa_checks: List[str] = field(default_factory=list)

    # LLM-specific fields (only for stratum=llm)
    llm_model: Optional[str] = None
    llm_tokens_input: int = 0
    llm_tokens_output: int = 0
    llm_slot: Optional[str] = None  # e.g., "services/order_flow_methods.py"

    # Template-specific fields
    template_name: Optional[str] = None
    template_version: Optional[str] = None

    # Timing
    generation_time_ms: int = 0

    # Validation results
    validation_passed: bool = True
    validation_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict, excluding None/empty optional fields."""
        result = {
            "atoms": self.atoms,
            "stratum": self.stratum,
            "source": self.source,
            "qa_checks": self.qa_checks,
        }

        if self.llm_model:
            result["llm_model"] = self.llm_model
        if self.llm_tokens_input or self.llm_tokens_output:
            result["tokens"] = {
                "input": self.llm_tokens_input,
                "output": self.llm_tokens_output,
                "total": self.llm_tokens_input + self.llm_tokens_output,
            }
        if self.llm_slot:
            result["llm_slot"] = self.llm_slot
        if self.template_name:
            result["template_name"] = self.template_name
        if self.template_version:
            result["template_version"] = self.template_version
        if self.generation_time_ms:
            result["generation_time_ms"] = self.generation_time_ms
        if not self.validation_passed:
            result["validation_passed"] = False
            result["validation_errors"] = self.validation_errors

        return result


@dataclass
class StratumSummary:
    """Summary of stratum usage across all files."""
    template_count: int = 0
    ast_count: int = 0
    llm_count: int = 0

    template_time_ms: int = 0
    ast_time_ms: int = 0
    llm_time_ms: int = 0

    total_llm_tokens: int = 0
    llm_models_used: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_counts": {
                "template": self.template_count,
                "ast": self.ast_count,
                "llm": self.llm_count,
                "total": self.template_count + self.ast_count + self.llm_count,
            },
            "time_ms": {
                "template": self.template_time_ms,
                "ast": self.ast_time_ms,
                "llm": self.llm_time_ms,
                "total": self.template_time_ms + self.ast_time_ms + self.llm_time_ms,
            },
            "llm_usage": {
                "total_tokens": self.total_llm_tokens,
                "models_used": list(self.llm_models_used),
            }
        }


@dataclass
class GenerationManifest:
    """
    Complete manifest for a generated application.

    Provides:
    - Full traceability for every generated file
    - Stratum distribution analysis
    - LLM usage auditing
    - Generation timing
    """
    app_id: str
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    manifest_version: str = ManifestVersion.V1.value
    execution_mode: str = "hybrid"

    # File-level metadata
    files: Dict[str, FileManifest] = field(default_factory=dict)

    # Summary
    stratum_summary: StratumSummary = field(default_factory=StratumSummary)

    # Generation config
    strict_mode: bool = False
    ir_endpoints_total: int = 0
    ir_endpoints_inferred: int = 0

    # Overall validation
    validation_passed: bool = True
    total_errors: int = 0
    total_warnings: int = 0

    def add_file(self, file_manifest: FileManifest) -> None:
        """Add a file to the manifest and update summaries."""
        self.files[file_manifest.file_path] = file_manifest

        # Update stratum summary
        if file_manifest.stratum == Stratum.TEMPLATE.value:
            self.stratum_summary.template_count += 1
            self.stratum_summary.template_time_ms += file_manifest.generation_time_ms
        elif file_manifest.stratum == Stratum.AST.value:
            self.stratum_summary.ast_count += 1
            self.stratum_summary.ast_time_ms += file_manifest.generation_time_ms
        elif file_manifest.stratum == Stratum.LLM.value:
            self.stratum_summary.llm_count += 1
            self.stratum_summary.llm_time_ms += file_manifest.generation_time_ms
            total_tokens = file_manifest.llm_tokens_input + file_manifest.llm_tokens_output
            self.stratum_summary.total_llm_tokens += total_tokens
            if file_manifest.llm_model:
                self.stratum_summary.llm_models_used.add(file_manifest.llm_model)

        # Update validation status
        if not file_manifest.validation_passed:
            self.validation_passed = False
            self.total_errors += len(file_manifest.validation_errors)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "app_id": self.app_id,
            "generated_at": self.generated_at,
            "manifest_version": self.manifest_version,
            "execution_mode": self.execution_mode,
            "config": {
                "strict_mode": self.strict_mode,
                "ir_endpoints": {
                    "total": self.ir_endpoints_total,
                    "inferred": self.ir_endpoints_inferred,
                    "from_spec": self.ir_endpoints_total - self.ir_endpoints_inferred,
                }
            },
            "files": {
                path: manifest.to_dict()
                for path, manifest in self.files.items()
            },
            "stratum_summary": self.stratum_summary.to_dict(),
            "validation": {
                "passed": self.validation_passed,
                "total_errors": self.total_errors,
                "total_warnings": self.total_warnings,
            }
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def save(self, output_dir: str) -> str:
        """Save manifest to file."""
        output_path = Path(output_dir) / "generation_manifest.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            f.write(self.to_json())

        logger.info(f"📋 Manifest saved: {output_path}")
        return str(output_path)

    def get_stratum_report(self) -> str:
        """Get human-readable stratum report."""
        summary = self.stratum_summary
        total_files = summary.template_count + summary.ast_count + summary.llm_count

        if total_files == 0:
            return "📋 No files generated"

        template_pct = (summary.template_count / total_files) * 100
        ast_pct = (summary.ast_count / total_files) * 100
        llm_pct = (summary.llm_count / total_files) * 100

        report = [
            "📊 Stratum Distribution:",
            f"┌───────────┬───────┬────────┬───────────┐",
            f"│ Stratum   │ Files │ Pct    │ Time (ms) │",
            f"├───────────┼───────┼────────┼───────────┤",
            f"│ TEMPLATE  │ {summary.template_count:>5} │ {template_pct:>5.1f}% │ {summary.template_time_ms:>9} │",
            f"│ AST       │ {summary.ast_count:>5} │ {ast_pct:>5.1f}% │ {summary.ast_time_ms:>9} │",
            f"│ LLM       │ {summary.llm_count:>5} │ {llm_pct:>5.1f}% │ {summary.llm_time_ms:>9} │",
            f"├───────────┼───────┼────────┼───────────┤",
            f"│ TOTAL     │ {total_files:>5} │ 100.0% │ {summary.template_time_ms + summary.ast_time_ms + summary.llm_time_ms:>9} │",
            f"└───────────┴───────┴────────┴───────────┘",
        ]

        if summary.total_llm_tokens > 0:
            report.append(f"\n🤖 LLM Usage: {summary.total_llm_tokens:,} tokens")
            if summary.llm_models_used:
                report.append(f"   Models: {', '.join(summary.llm_models_used)}")

        return "\n".join(report)


# =============================================================================
# MANIFEST BUILDER
# =============================================================================

class ManifestBuilder:
    """
    Builder for constructing GenerationManifest during code generation.

    Usage:
        builder = ManifestBuilder("ecommerce-api-spec-human_123")
        builder.set_execution_mode("hybrid")

        # During generation:
        builder.add_template_file("Dockerfile", atoms=["infra:dockerfile"])
        builder.add_ast_file("src/models/entities.py", atoms=["entity:Product"])
        builder.add_llm_file("src/services/flow.py", atoms=["flow:checkout"],
                            model="claude-3.5-sonnet", tokens_in=1000, tokens_out=500)

        manifest = builder.build()
        manifest.save("/path/to/app")
    """

    def __init__(self, app_id: str):
        self.manifest = GenerationManifest(app_id=app_id)

    def set_execution_mode(self, mode: str) -> "ManifestBuilder":
        """Set execution mode (safe/hybrid/research)."""
        self.manifest.execution_mode = mode
        return self

    def set_strict_mode(self, strict: bool) -> "ManifestBuilder":
        """Set strict mode flag."""
        self.manifest.strict_mode = strict
        return self

    def set_ir_stats(self, total: int, inferred: int) -> "ManifestBuilder":
        """Set IR endpoint statistics."""
        self.manifest.ir_endpoints_total = total
        self.manifest.ir_endpoints_inferred = inferred
        return self

    def add_template_file(
        self,
        file_path: str,
        atoms: List[str],
        template_name: Optional[str] = None,
        template_version: str = "v1.0.0",
        qa_checks: Optional[List[str]] = None,
        generation_time_ms: int = 0,
    ) -> "ManifestBuilder":
        """Add a template-generated file."""
        file_manifest = FileManifest(
            file_path=file_path,
            atoms=atoms,
            stratum=Stratum.TEMPLATE.value,
            source=f"template:{template_name or file_path}",
            template_name=template_name,
            template_version=template_version,
            qa_checks=qa_checks or ["template_valid"],
            generation_time_ms=generation_time_ms,
        )
        self.manifest.add_file(file_manifest)
        return self

    def add_ast_file(
        self,
        file_path: str,
        atoms: List[str],
        source: str = "ApplicationIR",
        qa_checks: Optional[List[str]] = None,
        generation_time_ms: int = 0,
    ) -> "ManifestBuilder":
        """Add an AST-generated file."""
        file_manifest = FileManifest(
            file_path=file_path,
            atoms=atoms,
            stratum=Stratum.AST.value,
            source=source,
            qa_checks=qa_checks or ["py_compile", "ast_valid"],
            generation_time_ms=generation_time_ms,
        )
        self.manifest.add_file(file_manifest)
        return self

    def add_llm_file(
        self,
        file_path: str,
        atoms: List[str],
        source: str = "ApplicationIR",
        model: Optional[str] = None,
        tokens_in: int = 0,
        tokens_out: int = 0,
        llm_slot: Optional[str] = None,
        qa_checks: Optional[List[str]] = None,
        generation_time_ms: int = 0,
    ) -> "ManifestBuilder":
        """Add an LLM-generated file."""
        file_manifest = FileManifest(
            file_path=file_path,
            atoms=atoms,
            stratum=Stratum.LLM.value,
            source=source,
            llm_model=model,
            llm_tokens_input=tokens_in,
            llm_tokens_output=tokens_out,
            llm_slot=llm_slot,
            qa_checks=qa_checks or ["py_compile", "business_logic_review"],
            generation_time_ms=generation_time_ms,
        )
        self.manifest.add_file(file_manifest)
        return self

    def add_file_validation_result(
        self,
        file_path: str,
        passed: bool,
        errors: Optional[List[str]] = None,
    ) -> "ManifestBuilder":
        """Add validation result for a file."""
        if file_path in self.manifest.files:
            self.manifest.files[file_path].validation_passed = passed
            if errors:
                self.manifest.files[file_path].validation_errors = errors
                self.manifest.total_errors += len(errors)
                self.manifest.validation_passed = False
        return self

    def build(self) -> GenerationManifest:
        """Build and return the manifest."""
        return self.manifest


# =============================================================================
# MANIFEST COMPARISON
# =============================================================================

@dataclass
class ManifestDiff:
    """Differences between two manifests."""
    files_added: List[str]
    files_removed: List[str]
    files_changed: Dict[str, Dict[str, Any]]  # {path: {field: {old, new}}}
    stratum_changes: Dict[str, Dict[str, int]]  # {stratum: {old, new, delta}}


def compare_manifests(
    old_manifest: GenerationManifest,
    new_manifest: GenerationManifest,
) -> ManifestDiff:
    """
    Compare two manifests to identify changes.

    Useful for:
    - Debugging: "What changed between generations?"
    - Auditing: "Did LLM usage increase?"
    - Validation: "Are new files using correct strata?"
    """
    old_files = set(old_manifest.files.keys())
    new_files = set(new_manifest.files.keys())

    diff = ManifestDiff(
        files_added=list(new_files - old_files),
        files_removed=list(old_files - new_files),
        files_changed={},
        stratum_changes={},
    )

    # Compare common files
    for path in old_files & new_files:
        old_file = old_manifest.files[path]
        new_file = new_manifest.files[path]

        changes = {}
        if old_file.stratum != new_file.stratum:
            changes["stratum"] = {"old": old_file.stratum, "new": new_file.stratum}
        if old_file.atoms != new_file.atoms:
            changes["atoms"] = {"old": old_file.atoms, "new": new_file.atoms}
        if old_file.llm_model != new_file.llm_model:
            changes["llm_model"] = {"old": old_file.llm_model, "new": new_file.llm_model}

        if changes:
            diff.files_changed[path] = changes

    # Compare stratum summaries
    old_summary = old_manifest.stratum_summary
    new_summary = new_manifest.stratum_summary

    diff.stratum_changes = {
        "template": {
            "old": old_summary.template_count,
            "new": new_summary.template_count,
            "delta": new_summary.template_count - old_summary.template_count,
        },
        "ast": {
            "old": old_summary.ast_count,
            "new": new_summary.ast_count,
            "delta": new_summary.ast_count - old_summary.ast_count,
        },
        "llm": {
            "old": old_summary.llm_count,
            "new": new_summary.llm_count,
            "delta": new_summary.llm_count - old_summary.llm_count,
        },
        "llm_tokens": {
            "old": old_summary.total_llm_tokens,
            "new": new_summary.total_llm_tokens,
            "delta": new_summary.total_llm_tokens - old_summary.total_llm_tokens,
        },
    }

    return diff


def load_manifest(path: str) -> GenerationManifest:
    """Load manifest from JSON file."""
    with open(path, 'r') as f:
        data = json.load(f)

    manifest = GenerationManifest(
        app_id=data["app_id"],
        generated_at=data["generated_at"],
        manifest_version=data.get("manifest_version", ManifestVersion.V1.value),
        execution_mode=data.get("execution_mode", "hybrid"),
        strict_mode=data.get("config", {}).get("strict_mode", False),
        ir_endpoints_total=data.get("config", {}).get("ir_endpoints", {}).get("total", 0),
        ir_endpoints_inferred=data.get("config", {}).get("ir_endpoints", {}).get("inferred", 0),
    )

    # Reconstruct files
    for path, file_data in data.get("files", {}).items():
        tokens = file_data.get("tokens", {})
        file_manifest = FileManifest(
            file_path=path,
            atoms=file_data.get("atoms", []),
            stratum=file_data.get("stratum", "unknown"),
            source=file_data.get("source", "unknown"),
            qa_checks=file_data.get("qa_checks", []),
            llm_model=file_data.get("llm_model"),
            llm_tokens_input=tokens.get("input", 0),
            llm_tokens_output=tokens.get("output", 0),
            llm_slot=file_data.get("llm_slot"),
            template_name=file_data.get("template_name"),
            template_version=file_data.get("template_version"),
            generation_time_ms=file_data.get("generation_time_ms", 0),
            validation_passed=file_data.get("validation_passed", True),
            validation_errors=file_data.get("validation_errors", []),
        )
        manifest.add_file(file_manifest)

    return manifest


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_current_builder: Optional[ManifestBuilder] = None


def get_manifest_builder(app_id: Optional[str] = None) -> ManifestBuilder:
    """Get or create manifest builder for current generation."""
    global _current_builder
    if _current_builder is None or app_id is not None:
        _current_builder = ManifestBuilder(app_id or "unknown")
    return _current_builder


def reset_manifest_builder() -> None:
    """Reset the current manifest builder."""
    global _current_builder
    _current_builder = None


def record_template_generation(
    file_path: str,
    atoms: List[str],
    template_name: Optional[str] = None,
    generation_time_ms: int = 0,
) -> None:
    """Record a template file generation."""
    builder = get_manifest_builder()
    builder.add_template_file(
        file_path=file_path,
        atoms=atoms,
        template_name=template_name,
        generation_time_ms=generation_time_ms,
    )


def record_ast_generation(
    file_path: str,
    atoms: List[str],
    source: str = "ApplicationIR",
    generation_time_ms: int = 0,
) -> None:
    """Record an AST file generation."""
    builder = get_manifest_builder()
    builder.add_ast_file(
        file_path=file_path,
        atoms=atoms,
        source=source,
        generation_time_ms=generation_time_ms,
    )


def record_llm_generation(
    file_path: str,
    atoms: List[str],
    model: str,
    tokens_in: int,
    tokens_out: int,
    generation_time_ms: int = 0,
) -> None:
    """Record an LLM file generation."""
    builder = get_manifest_builder()
    builder.add_llm_file(
        file_path=file_path,
        atoms=atoms,
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        generation_time_ms=generation_time_ms,
    )


def finalize_manifest(output_dir: str) -> str:
    """Finalize and save the current manifest."""
    builder = get_manifest_builder()
    manifest = builder.build()
    path = manifest.save(output_dir)
    reset_manifest_builder()
    return path

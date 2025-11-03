#!/usr/bin/env python
"""
RAG Population Orchestrator

Master script that orchestrates the complete RAG population process:
1. Migrate existing project code (src/)
2. Seed enhanced curated patterns
3. Seed project standards (constitution, contributing)
4. Verify quality and coverage

Usage:
    python scripts/orchestrate_rag_population.py [--clear] [--skip-verification]
"""

import sys
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.observability import get_logger

logger = get_logger("orchestrate_rag_population")


class Phase(str, Enum):
    """Population phases."""
    MIGRATE_PROJECT = "migrate_project"
    ENHANCED_PATTERNS = "enhanced_patterns"
    PROJECT_STANDARDS = "project_standards"
    OFFICIAL_DOCS = "official_docs"
    GITHUB_REPOS = "github_repos"
    VERIFICATION = "verification"


@dataclass
class PhaseResult:
    """Result of a population phase."""
    phase: Phase
    success: bool
    duration_seconds: float
    examples_added: Optional[int] = None
    error: Optional[str] = None
    output: Optional[str] = None


class RAGPopulationOrchestrator:
    """Orchestrator for RAG population process."""
    
    def __init__(self, scripts_dir: Path, clear_first: bool = False, skip_verification: bool = False):
        self.scripts_dir = scripts_dir
        self.clear_first = clear_first
        self.skip_verification = skip_verification
        self.results: List[PhaseResult] = []
    
    def run_phase(
        self,
        phase: Phase,
        script_name: str,
        args: List[str] = None,
        required: bool = True
    ) -> PhaseResult:
        """
        Run a population phase.
        
        Args:
            phase: Phase identifier
            script_name: Script filename
            args: Additional script arguments
            required: Whether phase is required (fail if error)
        
        Returns:
            PhaseResult with execution details
        """
        script_path = self.scripts_dir / script_name
        
        if not script_path.exists():
            error_msg = f"Script not found: {script_path}"
            logger.error(error_msg)
            return PhaseResult(
                phase=phase,
                success=False,
                duration_seconds=0,
                error=error_msg
            )
        
        # Build command
        cmd = ["python", str(script_path)]
        if args:
            cmd.extend(args)
        
        logger.info(f"Running phase: {phase.value}", command=" ".join(cmd))
        print(f"\n{'='*80}")
        print(f"Phase: {phase.value.upper().replace('_', ' ')}")
        print(f"{'='*80}")
        print(f"Command: {' '.join(cmd)}\n")
        
        # Execute script
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            duration = time.time() - start_time
            
            # Extract examples count from output if present
            examples_added = None
            if "Successfully indexed" in result.stdout:
                # Try to extract number
                import re
                match = re.search(r"Successfully indexed (\d+)", result.stdout)
                if match:
                    examples_added = int(match.group(1))
            
            success = result.returncode == 0
            
            if success:
                logger.info(
                    f"Phase completed successfully",
                    phase=phase.value,
                    duration_seconds=duration,
                    examples_added=examples_added
                )
                print(f"\n✅ Phase completed successfully in {duration:.1f}s")
                if examples_added:
                    print(f"   Added {examples_added} examples")
            else:
                logger.error(
                    f"Phase failed",
                    phase=phase.value,
                    returncode=result.returncode,
                    error=result.stderr[:500]
                )
                print(f"\n❌ Phase failed with return code {result.returncode}")
                if result.stderr:
                    print(f"Error: {result.stderr[:500]}")
            
            return PhaseResult(
                phase=phase,
                success=success,
                duration_seconds=duration,
                examples_added=examples_added,
                error=result.stderr if not success else None,
                output=result.stdout
            )
        
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            error_msg = f"Phase timed out after {duration:.1f}s"
            logger.error(error_msg, phase=phase.value)
            print(f"\n⏱️  {error_msg}")
            
            return PhaseResult(
                phase=phase,
                success=False,
                duration_seconds=duration,
                error=error_msg
            )
        
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Phase failed with exception: {str(e)}"
            logger.error(error_msg, phase=phase.value, error=str(e))
            print(f"\n❌ {error_msg}")
            
            return PhaseResult(
                phase=phase,
                success=False,
                duration_seconds=duration,
                error=str(e)
            )
    
    def run_all_phases(self) -> bool:
        """
        Run all population phases in order.
        
        Returns:
            True if all required phases succeeded
        """
        print("\n" + "="*80)
        print("RAG POPULATION ORCHESTRATOR")
        print("="*80)
        print(f"\nConfiguration:")
        print(f"  Clear existing data: {self.clear_first}")
        print(f"  Skip verification: {self.skip_verification}")
        
        overall_start = time.time()
        
        # ============================================================
        # Phase 1: Migrate existing project code
        # ============================================================
        phase1_args = ["--path", "src", "--batch-size", "50"]
        if self.clear_first:
            phase1_args.append("--clear")
        
        result = self.run_phase(
            Phase.MIGRATE_PROJECT,
            "migrate_existing_code.py",
            args=phase1_args,
            required=False  # Optional - might not have much code yet
        )
        self.results.append(result)
        
        # Continue even if migration fails (might be empty project)
        
        # ============================================================
        # Phase 2: Seed enhanced curated patterns
        # ============================================================
        phase2_args = ["--category", "all", "--batch-size", "50"]
        # Don't clear on phase 2 - we want to add to existing
        
        result = self.run_phase(
            Phase.ENHANCED_PATTERNS,
            "seed_enhanced_patterns.py",
            args=phase2_args,
            required=True  # Required - these are the core patterns
        )
        self.results.append(result)
        
        if not result.success:
            print("\n❌ Critical phase failed. Stopping.")
            return False
        
        # ============================================================
        # Phase 3: Seed project standards
        # ============================================================
        phase3_args = ["--source", "all", "--batch-size", "50"]
        
        result = self.run_phase(
            Phase.PROJECT_STANDARDS,
            "seed_project_standards.py",
            args=phase3_args,
            required=False  # Optional - might not have standards yet
        )
        self.results.append(result)
        
        # ============================================================
        # Phase 4: Seed official documents
        # ============================================================
        phase4_args = ["--framework", "all", "--batch-size", "50"]
        
        result = self.run_phase(
            Phase.OFFICIAL_DOCS,
            "seed_official_docs.py",
            args=phase4_args,
            required=False  # Optional - might not have official docs yet
        )
        self.results.append(result)
        
        # ============================================================
        # Phase 5: GitHub repositories (optional but recommended)
        # ============================================================
        github_args: List[str] = []
        result = self.run_phase(
            Phase.GITHUB_REPOS,
            "seed_github_repos.py",
            args=github_args,
            required=False
        )
        self.results.append(result)
        
        # ============================================================
        # Phase 6: Verification
        # ============================================================
        if not self.skip_verification:
            verification_args = ["--detailed", "--top-k", "3", "--min-similarity", "0.7"]
            
            result = self.run_phase(
                Phase.VERIFICATION,
                "verify_rag_quality.py",
                args=verification_args,
                required=False  # Verification can fail but we still consider success
            )
            self.results.append(result)
        
        # ============================================================
        # Summary
        # ============================================================
        overall_duration = time.time() - overall_start
        
        print("\n" + "="*80)
        print("ORCHESTRATION SUMMARY")
        print("="*80)
        
        total_phases = len(self.results)
        successful_phases = sum(1 for r in self.results if r.success)
        failed_phases = total_phases - successful_phases
        total_examples = sum(r.examples_added for r in self.results if r.examples_added)
        
        print(f"\n📊 Phases:")
        print(f"  ✅ Successful: {successful_phases}/{total_phases}")
        print(f"  ❌ Failed: {failed_phases}/{total_phases}")
        
        if total_examples:
            print(f"\n📦 Examples Added: {total_examples}")
        
        print(f"\n⏱️  Total Duration: {overall_duration:.1f}s ({overall_duration/60:.1f} minutes)")
        
        # Phase breakdown
        print(f"\n📋 Phase Details:")
        for result in self.results:
            status = "✅" if result.success else "❌"
            phase_name = result.phase.value.replace("_", " ").title()
            duration_str = f"{result.duration_seconds:.1f}s"
            examples_str = f" ({result.examples_added} examples)" if result.examples_added else ""
            
            print(f"  {status} {phase_name:<30} {duration_str:>8}{examples_str}")
            
            if result.error and not result.success:
                error_short = result.error[:100] + "..." if len(result.error) > 100 else result.error
                print(f"     Error: {error_short}")
        
        # Overall assessment
        print(f"\n🎯 Overall Assessment:")
        
        # Check critical phases
        enhanced_patterns_success = any(
            r.phase == Phase.ENHANCED_PATTERNS and r.success
            for r in self.results
        )
        
        if enhanced_patterns_success and successful_phases >= 2:
            print("  ✅ RAG population successful!")
            print("  ✅ Core patterns are indexed")
            if total_examples >= 20:
                print(f"  ✅ Good example count ({total_examples} examples)")
            return True
        elif successful_phases >= 1:
            print("  ⚠️  Partial success - some phases failed")
            print("  ⚠️  RAG has limited coverage")
            return False
        else:
            print("  ❌ RAG population failed")
            print("  ❌ No data indexed successfully")
            return False
    
    def export_results(self, output_file: str):
        """Export orchestration results to JSON."""
        import json
        from datetime import datetime
        
        output_data = {
            "timestamp": datetime.now().isoformat(),
            "configuration": {
                "clear_first": self.clear_first,
                "skip_verification": self.skip_verification,
            },
            "results": [
                {
                    "phase": r.phase.value,
                    "success": r.success,
                    "duration_seconds": r.duration_seconds,
                    "examples_added": r.examples_added,
                    "error": r.error,
                }
                for r in self.results
            ],
            "summary": {
                "total_phases": len(self.results),
                "successful_phases": sum(1 for r in self.results if r.success),
                "total_examples": sum(r.examples_added for r in self.results if r.examples_added),
                "total_duration": sum(r.duration_seconds for r in self.results),
            }
        }
        
        with open(output_file, "w") as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\n💾 Results exported to: {output_file}")


def main():
    """Main orchestrator script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Orchestrate RAG population process")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing collection before starting (WARNING: deletes all data)",
    )
    parser.add_argument(
        "--skip-verification",
        action="store_true",
        help="Skip quality verification step",
    )
    parser.add_argument(
        "--export",
        type=str,
        help="Export results to JSON file",
    )
    
    args = parser.parse_args()
    
    # Confirm clear operation
    if args.clear:
        print("\n⚠️  WARNING: --clear will delete all existing RAG data")
        response = input("Are you sure you want to continue? [y/N]: ")
        if response.lower() != 'y':
            print("Operation cancelled.")
            return 0
    
    # Get scripts directory
    scripts_dir = Path(__file__).parent
    
    # Create orchestrator
    orchestrator = RAGPopulationOrchestrator(
        scripts_dir=scripts_dir,
        clear_first=args.clear,
        skip_verification=args.skip_verification
    )
    
    # Run all phases
    success = orchestrator.run_all_phases()
    
    # Export results if requested
    if args.export:
        orchestrator.export_results(args.export)
    
    # Exit code
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())


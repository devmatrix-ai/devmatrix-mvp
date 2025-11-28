"""
Validation Agent

Phase 5 of Bug #107: LLM-Driven Smoke Test Generation

Analyzes test results and generates insightful reports.
Uses LLM to identify patterns in failures and provide recommendations.
"""
import structlog
from typing import List, Optional

from src.llm.enhanced_anthropic_client import EnhancedAnthropicClient
from src.validation.smoke_test_models import (
    SmokeTestPlan,
    ScenarioResult,
    TestMetrics,
    SmokeTestReport
)

logger = structlog.get_logger(__name__)


VALIDATION_SYSTEM_PROMPT = """You are a QA analysis expert. Your job is to analyze smoke test results
and provide actionable insights.

You identify:
1. Patterns in failures (all 404s? all POST failures? specific entity?)
2. Root cause analysis (missing seed data? wrong routes? validation issues?)
3. Severity classification (Critical/High/Medium/Low)
4. Recommended fixes with specific guidance

Be concise and actionable. Focus on what developers need to fix."""


VALIDATION_USER_PROMPT = """## Test Results Summary
- Total scenarios: {total}
- Passed: {passed} ({pass_rate:.1f}%)
- Failed: {failed}
- Happy path passed: {happy_passed}/{happy_total}

## Failed Scenarios
{failed_scenarios}

## Analysis Questions
1. What pattern do you see in the failures?
2. What is the likely root cause?
3. How severe is this issue? (Critical if happy paths fail, High if most fail, Medium if few fail, Low if edge cases)
4. What specific fix would you recommend?

Provide a concise analysis in this format:
PATTERN: <describe the failure pattern>
ROOT_CAUSE: <likely cause>
SEVERITY: <Critical|High|Medium|Low>
RECOMMENDATIONS:
- <specific fix 1>
- <specific fix 2>"""


class ValidationAgent:
    """
    Agent for analyzing test results and providing insights.

    Uses LLM to understand failures and generate recommendations.
    """

    def __init__(self, llm_client: Optional[EnhancedAnthropicClient] = None):
        self.llm = llm_client or EnhancedAnthropicClient()

    async def analyze_results(
        self,
        results: List[ScenarioResult],
        plan: SmokeTestPlan
    ) -> SmokeTestReport:
        """
        Analyze test results and generate report.

        Args:
            results: List of ScenarioResult from executor
            plan: Original SmokeTestPlan for context

        Returns:
            SmokeTestReport with analysis and recommendations
        """
        logger.info("📊 Validator Agent: Analyzing test results")

        # Calculate metrics
        metrics = TestMetrics.from_results(results)

        # If all passed, simple report
        if metrics.failed == 0:
            logger.info("   ✅ All tests passed!")
            return SmokeTestReport(
                metrics=metrics,
                status="PASSED",
                summary=f"All {metrics.total} smoke tests passed successfully",
                failures=[],
                analysis=None,
                recommendations=[]
            )

        # Collect failures
        failures = [r for r in results if not r.status_matches]

        # Use LLM to analyze failures
        analysis = await self._analyze_failures(failures, metrics)

        # Extract recommendations from analysis
        recommendations = self._extract_recommendations(analysis)

        logger.info(f"   ⚠️ {metrics.failed} failures analyzed")

        return SmokeTestReport(
            metrics=metrics,
            status="FAILED",
            summary=f"{metrics.failed} of {metrics.total} scenarios failed ({100 - metrics.pass_rate:.1f}% failure rate)",
            failures=failures,
            analysis=analysis,
            recommendations=recommendations
        )

    async def _analyze_failures(
        self,
        failures: List[ScenarioResult],
        metrics: TestMetrics
    ) -> str:
        """Use LLM to analyze failures and identify patterns."""
        # Format failures for prompt
        failed_scenarios = self._format_failures(failures)

        user_prompt = VALIDATION_USER_PROMPT.format(
            total=metrics.total,
            passed=metrics.passed,
            failed=metrics.failed,
            pass_rate=metrics.pass_rate,
            happy_passed=metrics.happy_path_passed,
            happy_total=metrics.happy_path_total,
            failed_scenarios=failed_scenarios
        )
        prompt = f"{VALIDATION_SYSTEM_PROMPT}\n\n{user_prompt}"

        try:
            analysis = await self.llm.generate_simple(
                prompt=prompt,
                task_type="validation",
                complexity="medium",
                max_tokens=2000,
                temperature=0.0
            )
            return analysis
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return self._generate_basic_analysis(failures, metrics)

    def _format_failures(self, failures: List[ScenarioResult]) -> str:
        """Format failures for LLM prompt."""
        lines = []
        for f in failures[:20]:  # Limit to 20 for prompt size
            scenario = f.scenario
            lines.append(
                f"- {scenario.endpoint} [{scenario.name}]: "
                f"Expected {scenario.expected_status}, Got {f.actual_status}"
            )
            if f.error:
                lines.append(f"  Error: {f.error}")

        if len(failures) > 20:
            lines.append(f"... and {len(failures) - 20} more failures")

        return '\n'.join(lines)

    def _generate_basic_analysis(
        self,
        failures: List[ScenarioResult],
        metrics: TestMetrics
    ) -> str:
        """Generate basic analysis without LLM (fallback)."""
        # Count failure types
        status_counts = {}
        endpoint_counts = {}
        name_counts = {}

        for f in failures:
            status = f.actual_status or "Connection Error"
            status_counts[status] = status_counts.get(status, 0) + 1

            endpoint = f.scenario.endpoint.split()[0]  # Method
            endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + 1

            name = f.scenario.name
            name_counts[name] = name_counts.get(name, 0) + 1

        # Identify pattern
        most_common_status = max(status_counts.items(), key=lambda x: x[1])
        most_common_endpoint = max(endpoint_counts.items(), key=lambda x: x[1])

        pattern = f"Most failures return {most_common_status[0]} ({most_common_status[1]} times)"
        if most_common_endpoint[1] > len(failures) / 2:
            pattern += f", mostly on {most_common_endpoint[0]} endpoints"

        # Determine severity
        if metrics.happy_path_passed < metrics.happy_path_total:
            severity = "Critical"
        elif metrics.pass_rate < 50:
            severity = "High"
        elif metrics.pass_rate < 80:
            severity = "Medium"
        else:
            severity = "Low"

        return f"""PATTERN: {pattern}
ROOT_CAUSE: Unable to determine automatically (LLM analysis unavailable)
SEVERITY: {severity}
RECOMMENDATIONS:
- Check server logs for error details
- Verify seed data was created correctly
- Check endpoint routes match specification"""

    def _extract_recommendations(self, analysis: str) -> List[str]:
        """Extract recommendations from analysis text."""
        recommendations = []

        # Look for RECOMMENDATIONS section
        if "RECOMMENDATIONS:" in analysis:
            rec_section = analysis.split("RECOMMENDATIONS:")[-1]
            # Extract bullet points
            for line in rec_section.split('\n'):
                line = line.strip()
                if line.startswith('-') or line.startswith('•'):
                    rec = line.lstrip('-•').strip()
                    if rec:
                        recommendations.append(rec)

        # Fallback: extract any actionable suggestions
        if not recommendations:
            keywords = ['fix', 'check', 'verify', 'ensure', 'add', 'remove', 'update']
            for line in analysis.split('\n'):
                line = line.strip().lower()
                if any(kw in line for kw in keywords):
                    recommendations.append(line.capitalize())

        return recommendations[:5]  # Limit to 5 recommendations

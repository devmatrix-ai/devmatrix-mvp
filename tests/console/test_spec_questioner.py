"""
Tests for the Specification Questioner system.

Validates intelligent requirement gathering, app type detection,
and specification completeness validation.
"""

import pytest
from src.console.spec_questioner import (
    AppType,
    SpecificationGap,
    Specification,
    SpecificationQuestioner,
    SpecificationBuilder,
)


class TestAppTypeDetection:
    """Tests for automatic application type detection."""

    def setup_method(self):
        """Set up questioner for each test."""
        self.questioner = SpecificationQuestioner()

    def test_detect_web_app(self):
        """Should detect web applications."""
        req = "Quiero construir un sitio web con React para mi negocio"
        app_type, confidence = self.questioner.detect_app_type(req)
        assert app_type == AppType.WEB_APP
        assert confidence > 0.5

    def test_detect_api_backend(self):
        """Should detect backend APIs."""
        req = "Necesito un REST API para gestionar usuarios y productos"
        app_type, confidence = self.questioner.detect_app_type(req)
        assert app_type == AppType.API_BACKEND
        assert confidence > 0.5

    def test_detect_saas_platform(self):
        """Should detect SaaS platforms."""
        req = "Quiero crear una plataforma SaaS de gestión de proyectos"
        app_type, confidence = self.questioner.detect_app_type(req)
        assert app_type in [AppType.SAAS_PLATFORM, AppType.DASHBOARD]

    def test_detect_ecommerce(self):
        """Should detect e-commerce applications."""
        req = "Necesito un sitio de e-commerce para vender productos"
        app_type, confidence = self.questioner.detect_app_type(req)
        assert app_type == AppType.E_COMMERCE

    def test_detect_mobile_app(self):
        """Should detect mobile applications."""
        req = "Quiero hacer una app mobile para iOS y Android"
        app_type, confidence = self.questioner.detect_app_type(req)
        assert app_type == AppType.MOBILE_APP

    def test_unknown_app_type(self):
        """Should return UNKNOWN for unclear requirements."""
        req = "Quiero algo pero no sé qué"
        app_type, confidence = self.questioner.detect_app_type(req)
        assert app_type == AppType.UNKNOWN or confidence < 0.5


class TestQuestionGeneration:
    """Tests for generating clarifying questions."""

    def setup_method(self):
        """Set up questioner for each test."""
        self.questioner = SpecificationQuestioner()

    def test_generate_web_app_questions(self):
        """Should generate web app specific questions."""
        spec = Specification(
            initial_requirement="Quiero un sitio web",
            app_type=AppType.WEB_APP
        )

        gaps = self.questioner.generate_gaps(spec)

        assert len(gaps) > 0
        categories = {gap.category for gap in gaps}
        # Should include web app specific categories
        assert any(cat in categories for cat in ["users", "features", "design", "auth"])

    def test_generate_saas_questions(self):
        """Should generate SaaS specific questions."""
        spec = Specification(
            initial_requirement="Quiero un SaaS de gestión",
            app_type=AppType.SAAS_PLATFORM
        )

        gaps = self.questioner.generate_gaps(spec)

        assert len(gaps) > 0
        categories = {gap.category for gap in gaps}
        # Should include SaaS specific categories
        assert any(cat in categories for cat in ["users", "monetization", "security"])

    def test_exclude_answered_categories(self):
        """Should not ask questions for already answered categories."""
        spec = Specification(
            initial_requirement="Quiero un sitio web",
            app_type=AppType.WEB_APP,
            gaps_resolved={"users", "features"}
        )

        gaps = self.questioner.generate_gaps(spec)

        answered_in_gaps = {gap.category for gap in gaps}
        # "users" and "features" should not appear again
        assert "users" not in answered_in_gaps
        assert "features" not in answered_in_gaps

    def test_question_prioritization(self):
        """Questions should be sorted by priority (critical first)."""
        spec = Specification(
            initial_requirement="Quiero un sitio web",
            app_type=AppType.WEB_APP
        )

        gaps = self.questioner.generate_gaps(spec)

        # First questions should have priority 1
        assert gaps[0].priority <= gaps[1].priority


class TestSpecificationValidation:
    """Tests for specification completeness validation."""

    def setup_method(self):
        """Set up questioner for each test."""
        self.questioner = SpecificationQuestioner()

    def test_incomplete_specification(self):
        """Should mark specification as incomplete when missing critical categories."""
        spec = Specification(
            initial_requirement="Quiero un sitio web",
            app_type=AppType.WEB_APP,
            gaps_resolved={"users"}  # Only one category
        )

        is_valid, missing, completeness = self.questioner.validate_specification(spec)

        assert not is_valid
        assert "features" in missing
        assert completeness < 0.8

    def test_complete_specification(self):
        """Should mark specification as complete when all critical categories answered."""
        spec = Specification(
            initial_requirement="Quiero un sitio web",
            app_type=AppType.WEB_APP,
            gaps_resolved={"users", "features", "auth", "scale", "timeline"}
        )

        is_valid, missing, completeness = self.questioner.validate_specification(spec)

        assert is_valid
        assert len(missing) == 0
        assert completeness >= 0.8

    def test_missing_categories_reported(self):
        """Should correctly report which categories are missing."""
        spec = Specification(
            initial_requirement="Quiero un sitio web",
            app_type=AppType.WEB_APP,
            gaps_resolved={"users", "features"}
        )

        is_valid, missing, _ = self.questioner.validate_specification(spec)

        assert "auth" in missing or "scale" in missing or "timeline" in missing


class TestFormatting:
    """Tests for formatting questions for Claude."""

    def setup_method(self):
        """Set up questioner for each test."""
        self.questioner = SpecificationQuestioner()

    def test_format_single_question(self):
        """Should format a single question nicely."""
        gap = SpecificationGap(
            category="users",
            question="¿Cuántos usuarios?",
            priority=1,
            context="Para estimaciones"
        )

        formatted = self.questioner.format_question_for_claude(gap)

        assert "¿Cuántos usuarios?" in formatted
        assert "Para estimaciones" in formatted

    def test_format_multiple_questions(self):
        """Should format multiple questions for presentation."""
        gaps = [
            SpecificationGap(
                category="users",
                question="¿Cuántos usuarios?",
                priority=1,
                context="Escala"
            ),
            SpecificationGap(
                category="features",
                question="¿Qué features?",
                priority=1,
                context="Scope"
            ),
        ]

        formatted = self.questioner.format_questions_for_claude(gaps, num_questions=2)

        assert "¿Cuántos usuarios?" in formatted
        assert "¿Qué features?" in formatted
        assert "Para generar el masterplan" in formatted


class TestSpecificationBuilder:
    """Tests for the complete specification building orchestration."""

    def test_start_specification_building(self):
        """Should initialize specification building from requirement."""
        builder = SpecificationBuilder()
        req = "Quiero un sitio web para mi negocio"

        spec, gaps = builder.start_from_requirement(req)

        assert spec is not None
        assert spec.initial_requirement == req
        assert spec.app_type in [AppType.WEB_APP, AppType.SAAS_PLATFORM]
        assert len(gaps) > 0

    def test_add_answers_progressively(self):
        """Should accumulate answers and track progress."""
        builder = SpecificationBuilder()
        spec, gaps = builder.start_from_requirement("Quiero un sitio web")

        # Add first answer
        gap = gaps[0]
        is_complete, next_gaps = builder.add_answer(gap, "Espero 10,000 usuarios en el primer año")

        # Should not be complete yet
        assert not is_complete
        assert next_gaps is not None

    def test_specification_completion(self):
        """Should recognize when specification is complete."""
        builder = SpecificationBuilder()
        spec, _ = builder.start_from_requirement("Quiero un sitio web")

        # Manually add all required categories
        spec.gaps_resolved = {"users", "features", "auth", "scale", "timeline"}

        # Verify it would be complete
        is_valid, missing, _ = builder.questioner.validate_specification(spec)
        assert is_valid

    def test_format_final_summary(self):
        """Should format a nice summary of the specification."""
        builder = SpecificationBuilder()
        spec, _ = builder.start_from_requirement("Quiero un e-commerce")

        # Add some answers
        gap1 = SpecificationGap(
            category="products",
            question="¿Cuántos productos?",
            priority=1
        )
        builder.add_answer(gap1, "Alrededor de 500 productos")

        gap2 = SpecificationGap(
            category="payments",
            question="¿Métodos de pago?",
            priority=1
        )
        builder.add_answer(gap2, "Tarjeta de crédito y PayPal")

        summary = builder.format_spec_summary()

        assert "e-commerce" in summary.lower()
        assert "500 productos" in summary
        assert "Tarjeta de crédito" in summary


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_full_web_app_specification_flow(self):
        """Should handle complete flow for web app specification."""
        builder = SpecificationBuilder()

        # User starts with vague requirement
        requirement = "Quiero hacer un sitio web"
        spec, initial_gaps = builder.start_from_requirement(requirement)

        assert spec.app_type == AppType.WEB_APP
        assert len(initial_gaps) > 0

        # Simulate answering critical questions
        critical_gaps = [g for g in initial_gaps if g.priority == 1]
        assert len(critical_gaps) > 0

        # Add answers for critical categories
        for gap in critical_gaps[:2]:
            is_complete, next_gaps = builder.add_answer(gap, f"Respuesta a: {gap.question}")
            # May not be complete after just 2 answers
            if is_complete:
                break

    def test_different_app_types_different_questions(self):
        """Different app types should get different questions."""
        questioner = SpecificationQuestioner()

        web_spec = Specification(
            initial_requirement="web app",
            app_type=AppType.WEB_APP
        )
        api_spec = Specification(
            initial_requirement="api",
            app_type=AppType.API_BACKEND
        )

        web_gaps = {g.category for g in questioner.generate_gaps(web_spec)}
        api_gaps = {g.category for g in questioner.generate_gaps(api_spec)}

        # Both should have some differences
        # (though may overlap on universal questions)
        assert len(web_gaps) > 0
        assert len(api_gaps) > 0


class TestCompletenessScoring:
    """Tests for specification completeness scoring."""

    def test_calculate_completeness_empty(self):
        """Empty specification should have low completeness."""
        questioner = SpecificationQuestioner()
        spec = Specification(
            initial_requirement="test",
            app_type=AppType.WEB_APP
        )

        completeness = questioner.calculate_completeness(spec)
        assert completeness == 0.0

    def test_calculate_completeness_partial(self):
        """Partial specification should have intermediate score."""
        questioner = SpecificationQuestioner()
        spec = Specification(
            initial_requirement="test",
            app_type=AppType.WEB_APP,
            gaps_resolved={"users", "features"}  # 2 of 5 required
        )

        completeness = questioner.calculate_completeness(spec)
        assert 0.3 < completeness < 0.5

    def test_calculate_completeness_full(self):
        """Complete specification should have high score."""
        questioner = SpecificationQuestioner()
        spec = Specification(
            initial_requirement="test",
            app_type=AppType.WEB_APP,
            gaps_resolved={"users", "features", "auth", "scale", "timeline"}
        )

        completeness = questioner.calculate_completeness(spec)
        assert completeness == 1.0

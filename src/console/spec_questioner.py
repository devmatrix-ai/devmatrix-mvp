"""
Intelligent Specification Questioner for DevMatrix SaaS Platform

Purpose:
- Analyze user requirements and detect gaps
- Ask clarifying questions based on application type
- Build comprehensive specifications iteratively
- Validate specification completeness before masterplan generation

Claude uses this to gather sufficient requirements for accurate masterplan generation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Set, Optional, Tuple
import re


class AppType(Enum):
    """Supported application types for specification gathering."""
    WEB_APP = "web_app"  # React, Vue, Next.js, etc.
    API_BACKEND = "api_backend"  # REST, GraphQL, microservices
    MOBILE_APP = "mobile_app"  # React Native, Flutter, native
    SAAS_PLATFORM = "saas_platform"  # Full-stack SaaS service
    E_COMMERCE = "ecommerce"  # E-commerce specific
    DASHBOARD = "dashboard"  # Analytics/admin dashboards
    INTEGRATION = "integration"  # Third-party integrations
    UNKNOWN = "unknown"


@dataclass
class SpecificationGap:
    """Represents a gap in specification."""
    category: str  # 'users', 'features', 'scale', 'security', 'timeline', etc.
    question: str  # The clarifying question to ask
    priority: int  # 1=critical, 2=important, 3=nice-to-have
    context: str = ""  # Why this is important


@dataclass
class SpecificationAnswer:
    """User's answer to a clarifying question."""
    question: str
    answer: str
    category: str


@dataclass
class Specification:
    """Complete specification for a project."""
    initial_requirement: str
    app_type: AppType

    # Core requirements
    target_users: str = ""
    primary_features: List[str] = field(default_factory=list)
    secondary_features: List[str] = field(default_factory=list)

    # Technical requirements
    scale_estimate: str = ""  # "small" (< 1K users), "medium", "large", "massive"
    auth_requirements: str = ""
    data_persistence: str = ""  # database types needed
    integrations: List[str] = field(default_factory=list)
    performance_requirements: str = ""

    # Timeline & Resources
    timeline: str = ""  # "ASAP", "weeks", "months"
    budget_level: str = ""  # "minimal", "moderate", "unlimited"

    # Special requirements
    security_level: str = ""  # "basic", "medium", "high", "banking-grade"
    compliance_needs: List[str] = field(default_factory=list)  # GDPR, HIPAA, etc.
    accessibility_requirements: str = ""

    # Answers to clarifying questions
    answers: List[SpecificationAnswer] = field(default_factory=list)

    # Completeness tracking
    gaps_resolved: Set[str] = field(default_factory=set)
    completeness_score: float = 0.0  # 0.0-1.0


class SpecificationQuestioner:
    """Intelligent questionnaire system for gathering project specifications."""

    # Keywords for detecting application types
    APP_TYPE_KEYWORDS = {
        AppType.WEB_APP: ["web", "website", "frontend", "react", "vue", "angular", "next", "app"],
        AppType.API_BACKEND: ["api", "rest", "graphql", "backend", "microservice", "server"],
        AppType.MOBILE_APP: ["mobile", "ios", "android", "app", "react native", "flutter"],
        AppType.SAAS_PLATFORM: ["saas", "platform", "service", "subscription", "dashboard", "tool"],
        AppType.E_COMMERCE: ["ecommerce", "store", "shop", "product", "cart", "checkout"],
        AppType.DASHBOARD: ["dashboard", "analytics", "monitoring", "admin", "reporting"],
        AppType.INTEGRATION: ["integration", "sync", "connector", "plugin", "bridge"],
    }

    # Questions for each application type
    QUESTIONS_BY_APP_TYPE = {
        AppType.WEB_APP: [
            SpecificationGap(
                category="users",
                question="¿Cuántos usuarios esperás tener en el primer mes? ¿Y en 6 meses?",
                priority=2,
                context="Helps determine architecture scalability"
            ),
            SpecificationGap(
                category="features",
                question="¿Cuáles son las 3-5 características más críticas que debería tener?",
                priority=1,
                context="Defines MVP scope"
            ),
            SpecificationGap(
                category="design",
                question="¿Hay preferencias sobre el look and feel? (minimalist, modern, corporate, playful, etc.)",
                priority=3,
                context="Influences UI/UX design decisions"
            ),
            SpecificationGap(
                category="auth",
                question="¿Necesita autenticación? ¿Qué nivel? (simple login, social auth, SSO, etc.)",
                priority=2,
                context="Impacts security architecture"
            ),
            SpecificationGap(
                category="performance",
                question="¿Hay requisitos específicos de velocidad/performance?",
                priority=2,
                context="Influences optimization priorities"
            ),
        ],

        AppType.API_BACKEND: [
            SpecificationGap(
                category="endpoints",
                question="¿Cuáles son los 5-10 endpoints principales que necesitás?",
                priority=1,
                context="Defines API surface"
            ),
            SpecificationGap(
                category="data",
                question="¿Qué tipo de datos va a manejar? (usuarios, productos, transacciones, etc.)",
                priority=1,
                context="Determines data model"
            ),
            SpecificationGap(
                category="scale",
                question="¿Cuántas requests por segundo esperas al inicio? ¿Y en escala máxima?",
                priority=2,
                context="Determines infrastructure needs"
            ),
            SpecificationGap(
                category="auth",
                question="¿Necesita autenticación/autorización? ¿JWT, OAuth, API keys?",
                priority=1,
                context="Critical for security"
            ),
            SpecificationGap(
                category="integrations",
                question="¿Necesita integrarse con servicios externos? (payment, email, etc.)",
                priority=2,
                context="Impacts architecture"
            ),
        ],

        AppType.SAAS_PLATFORM: [
            SpecificationGap(
                category="users",
                question="¿Quién es el usuario ideal? ¿Cuál es el problema que resuelve?",
                priority=1,
                context="Defines value proposition"
            ),
            SpecificationGap(
                category="monetization",
                question="¿Cómo vas a monetizar? (subscription, freemium, one-time, etc.)",
                priority=2,
                context="Impacts feature modeling"
            ),
            SpecificationGap(
                category="features",
                question="¿Cuáles son las features que diferencian tu producto del competidor?",
                priority=1,
                context="Defines competitive advantage"
            ),
            SpecificationGap(
                category="data",
                question="¿Qué datos críticos necesita gestionar la plataforma?",
                priority=1,
                context="Data architecture foundation"
            ),
            SpecificationGap(
                category="security",
                question="¿Necesita cumplir con regulaciones específicas? (GDPR, HIPAA, etc.)",
                priority=2,
                context="Compliance requirements"
            ),
            SpecificationGap(
                category="scale",
                question="¿Cuál es tu proyección de usuarios para el primer año?",
                priority=2,
                context="Scalability planning"
            ),
        ],

        AppType.E_COMMERCE: [
            SpecificationGap(
                category="products",
                question="¿Cuántos productos aproximadamente? ¿Hay categorías?",
                priority=1,
                context="Determines product catalog structure"
            ),
            SpecificationGap(
                category="payments",
                question="¿Qué métodos de pago necesitas? (tarjeta, PayPal, transferencia, etc.)",
                priority=1,
                context="Payment integration requirements"
            ),
            SpecificationGap(
                category="features",
                question="¿Necesita carrito, wishlist, reseñas, búsqueda avanzada?",
                priority=2,
                context="Feature completeness"
            ),
            SpecificationGap(
                category="shipping",
                question="¿Cómo va a manejar envíos? (integración con couriers, local, digital, etc.)",
                priority=2,
                context="Logistics integration"
            ),
            SpecificationGap(
                category="inventory",
                question="¿Necesita gestión de inventario en tiempo real?",
                priority=2,
                context="Stock management complexity"
            ),
        ],
    }

    # Universal questions applicable to all app types
    UNIVERSAL_QUESTIONS = [
        SpecificationGap(
            category="timeline",
            question="¿Cuándo necesitas que esté listo? (ASAP, en X semanas/meses)",
            priority=2,
            context="Affects development approach"
        ),
        SpecificationGap(
            category="budget",
            question="¿Cuál es el presupuesto aproximado? (esto es confidencial y solo para estimaciones)",
            priority=3,
            context="Resource allocation"
        ),
    ]

    def __init__(self):
        """Initialize the questioner."""
        pass

    def detect_app_type(self, requirement: str) -> Tuple[AppType, float]:
        """
        Detect application type from requirement description.

        Returns:
            Tuple of (AppType, confidence_score 0.0-1.0)
        """
        requirement_lower = requirement.lower()

        # Count keyword matches for each type
        scores = {}
        for app_type, keywords in self.APP_TYPE_KEYWORDS.items():
            matches = sum(1 for keyword in keywords if keyword in requirement_lower)
            scores[app_type] = matches

        # Find the type with most matches
        if not any(scores.values()):
            return AppType.UNKNOWN, 0.0

        max_type = max(scores, key=scores.get)
        max_score = scores[max_type]

        # Calculate confidence (0.0-1.0)
        total_keywords = sum(len(kw) for kw in self.APP_TYPE_KEYWORDS.values())
        confidence = min(max_score / 3.0, 1.0)  # High confidence if 3+ keyword matches

        return max_type, confidence

    def generate_gaps(self, specification: Specification) -> List[SpecificationGap]:
        """
        Generate list of clarifying questions based on current specification.

        Returns:
            List of SpecificationGap objects sorted by priority
        """
        gaps = []

        # Add type-specific questions
        if specification.app_type in self.QUESTIONS_BY_APP_TYPE:
            gaps.extend(self.QUESTIONS_BY_APP_TYPE[specification.app_type])

        # Add universal questions
        gaps.extend(self.UNIVERSAL_QUESTIONS)

        # Remove questions for categories already answered
        gaps = [g for g in gaps if g.category not in specification.gaps_resolved]

        # Sort by priority (1 = critical first)
        gaps.sort(key=lambda x: (x.priority, x.category))

        return gaps

    def validate_specification(self, spec: Specification) -> Tuple[bool, List[str], float]:
        """
        Validate if specification is complete enough for masterplan generation.

        Returns:
            Tuple of (is_valid, missing_categories, completeness_score)
        """
        required_categories = {
            "users", "features", "auth", "scale", "timeline"
        }

        missing = required_categories - spec.gaps_resolved
        completeness = len(spec.gaps_resolved) / len(required_categories)

        # Specification is valid if all critical categories are covered
        is_valid = len(missing) == 0 and completeness >= 0.8

        return is_valid, list(missing), completeness

    def format_question_for_claude(self, gap: SpecificationGap) -> str:
        """Format a specification gap as a question Claude can ask."""
        return f"**{gap.question}**\n_(Importante para: {gap.context})_"

    def format_questions_for_claude(self, gaps: List[SpecificationGap], num_questions: int = 3) -> str:
        """
        Format multiple questions in a nice format for Claude to present to user.

        Takes top N prioritized questions.
        """
        top_gaps = gaps[:num_questions]

        output = "Para generar el masterplan más preciso, necesito entender mejor tu proyecto:\n\n"

        for i, gap in enumerate(top_gaps, 1):
            output += f"**{i}. {gap.question}**\n"
            if gap.context:
                output += f"   _{gap.context}_\n\n"

        return output

    def process_answer(self, spec: Specification, gap: SpecificationGap, answer: str) -> None:
        """
        Process a user's answer and update the specification.
        """
        spec.answers.append(SpecificationAnswer(
            question=gap.question,
            answer=answer,
            category=gap.category
        ))
        spec.gaps_resolved.add(gap.category)

    def calculate_completeness(self, spec: Specification) -> float:
        """Calculate specification completeness score (0.0-1.0)."""
        required_categories = {"users", "features", "auth", "scale", "timeline"}
        covered = spec.gaps_resolved & required_categories
        return len(covered) / len(required_categories)


class SpecificationBuilder:
    """Orchestrates the specification building process with Claude."""

    def __init__(self):
        self.questioner = SpecificationQuestioner()
        self.current_spec: Optional[Specification] = None

    def start_from_requirement(self, requirement: str) -> Tuple[Specification, List[SpecificationGap]]:
        """
        Start specification gathering from user's initial requirement.

        Returns:
            Tuple of (Specification object, List of clarifying questions)
        """
        # Detect app type
        app_type, confidence = self.questioner.detect_app_type(requirement)

        # Create initial specification
        spec = Specification(
            initial_requirement=requirement,
            app_type=app_type
        )

        # For UNKNOWN types, try to infer from more questions
        if app_type == AppType.UNKNOWN:
            spec.gaps_resolved.add("app_type_detection")

        self.current_spec = spec

        # Generate clarifying questions
        gaps = self.questioner.generate_gaps(spec)

        return spec, gaps

    def add_answer(self, gap: SpecificationGap, answer: str) -> Tuple[bool, Optional[List[SpecificationGap]]]:
        """
        Process a user answer.

        Returns:
            Tuple of (is_complete, next_questions_if_incomplete)
        """
        if not self.current_spec:
            raise ValueError("No specification in progress")

        self.questioner.process_answer(self.current_spec, gap, answer)

        # Check if we have enough information
        is_valid, missing, completeness = self.questioner.validate_specification(self.current_spec)

        if is_valid:
            return True, None
        else:
            # Generate next questions
            next_gaps = self.questioner.generate_gaps(self.current_spec)
            return False, next_gaps if next_gaps else None

    def get_final_specification(self) -> Specification:
        """Get the final built specification."""
        if not self.current_spec:
            raise ValueError("No specification in progress")
        return self.current_spec

    def format_spec_summary(self) -> str:
        """Format the final specification as a readable summary."""
        spec = self.current_spec
        if not spec:
            return "No specification"

        summary = f"""
## 📋 Resumen de Especificación

**Tipo de Aplicación:** {spec.app_type.value}

**Requerimiento Inicial:**
{spec.initial_requirement}

**Detalles Recopilados:**
"""

        for answer in spec.answers:
            summary += f"\n- **{answer.category.upper()}**: {answer.answer}"

        completeness = self.questioner.calculate_completeness(spec)
        summary += f"\n\n**Completitud de Especificación:** {completeness*100:.0f}%"

        return summary

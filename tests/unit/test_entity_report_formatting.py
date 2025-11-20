"""
Unit tests for entity report formatting and categorization

Tests the _format_entity_report() method that categorizes entities into:
- Domain entities (Product, Customer, Cart, Order)
- Request/Response schemas (ProductCreate, CustomerCreate, etc.)
- Enums (CartStatus, OrderStatus, PaymentStatus)

Part of Task Group 2: Presentation Enhancement (M4)
"""

import pytest
from src.validation.compliance_validator import ComplianceValidator, ComplianceReport


class TestEntityReportFormatting:
    """Test suite for entity categorization and report formatting"""

    def setup_method(self):
        """Setup test fixtures"""
        self.validator = ComplianceValidator()

    def test_domain_entities_correctly_categorized(self):
        """Test that domain entities are identified correctly"""
        # Arrange
        report = ComplianceReport(
            overall_compliance=1.0,
            entities_implemented=["Product", "Customer", "Cart", "Order"],
            entities_expected=["Product", "Customer", "Cart", "Order"],
        )

        # Act
        formatted = self.validator._format_entity_report(report)

        # Assert
        assert "Product" in formatted
        assert "Customer" in formatted
        assert "Cart" in formatted
        assert "Order" in formatted
        assert "4 required" in formatted or "4 present" in formatted

    def test_schemas_separated_from_domain_entities(self):
        """Test that Request/Response schemas are categorized separately"""
        # Arrange
        report = ComplianceReport(
            overall_compliance=1.0,
            entities_implemented=[
                "Product",
                "Customer",
                "ProductCreate",
                "ProductUpdate",
                "CustomerCreate",
            ],
            entities_expected=["Product", "Customer"],
        )

        # Act
        formatted = self.validator._format_entity_report(report)

        # Assert
        assert "Request/Response schemas" in formatted
        assert "ProductCreate" not in formatted.split("Request/Response")[0]
        assert "Product" in formatted.split("Request/Response")[0]

    def test_enums_identified_correctly(self):
        """Test that Status enums are identified and categorized"""
        # Arrange
        report = ComplianceReport(
            overall_compliance=1.0,
            entities_implemented=[
                "Product",
                "Customer",
                "CartStatus",
                "OrderStatus",
                "PaymentStatus",
            ],
            entities_expected=["Product", "Customer"],
        )

        # Act
        formatted = self.validator._format_entity_report(report)

        # Assert
        assert "Enums" in formatted
        assert "CartStatus" not in formatted.split("Enums")[0]

    def test_report_format_matches_expected_structure(self):
        """Test that report has expected structure with emoji indicators"""
        # Arrange
        report = ComplianceReport(
            overall_compliance=1.0,
            entities_implemented=["Product", "Customer", "ProductCreate"],
            entities_expected=["Product", "Customer"],
        )

        # Act
        formatted = self.validator._format_entity_report(report)

        # Assert
        # Check for emoji indicators
        assert "📦" in formatted  # Entities emoji
        assert "✅" in formatted  # Check mark emoji
        assert "📝" in formatted  # Additional models emoji

        # Check for structured sections
        assert "required" in formatted
        assert "present" in formatted
        assert "Additional models" in formatted

    def test_empty_entities_handled_gracefully(self):
        """Test that empty entity list is handled without errors"""
        # Arrange
        report = ComplianceReport(
            overall_compliance=1.0, entities_implemented=[], entities_expected=[]
        )

        # Act
        formatted = self.validator._format_entity_report(report)

        # Assert
        assert formatted is not None
        assert "📦" in formatted
        assert "0 required" in formatted or "0 present" in formatted

    def test_categorization_handles_mixed_case(self):
        """Test that categorization works with different naming cases"""
        # Arrange
        report = ComplianceReport(
            overall_compliance=1.0,
            entities_implemented=[
                "product",
                "CUSTOMER",
                "ProductCreate",
                "orderStatus",
            ],
            entities_expected=["product", "CUSTOMER"],
        )

        # Act
        formatted = self.validator._format_entity_report(report)

        # Assert
        # Should still categorize correctly despite case differences
        assert "product" in formatted or "PRODUCT" in formatted
        assert "CUSTOMER" in formatted or "customer" in formatted

    def test_schemas_count_is_accurate(self):
        """Test that schema count in report is accurate"""
        # Arrange
        report = ComplianceReport(
            overall_compliance=1.0,
            entities_implemented=[
                "Product",
                "Customer",
                "ProductCreate",
                "ProductUpdate",
                "CustomerCreate",
                "CustomerUpdate",
                "OrderCreate",
            ],
            entities_expected=["Product", "Customer"],
        )

        # Act
        formatted = self.validator._format_entity_report(report)

        # Assert
        # Should count 5 schemas (ProductCreate, ProductUpdate, CustomerCreate,
        # CustomerUpdate, OrderCreate)
        assert "5" in formatted

    def test_enums_count_is_accurate(self):
        """Test that enum count in report is accurate"""
        # Arrange
        report = ComplianceReport(
            overall_compliance=1.0,
            entities_implemented=[
                "Product",
                "CartStatus",
                "OrderStatus",
                "PaymentStatus",
            ],
            entities_expected=["Product"],
        )

        # Act
        formatted = self.validator._format_entity_report(report)

        # Assert
        # Should count 3 enums (CartStatus, OrderStatus, PaymentStatus)
        assert "3" in formatted or "Enums: 3" in formatted

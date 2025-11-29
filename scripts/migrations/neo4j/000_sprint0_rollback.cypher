// =============================================================================
// Sprint 0: ROLLBACK Script
// Fecha: 2025-11-29
// Descripción: Revert label renaming if needed
// =============================================================================

// -----------------------------------------------------------------------------
// STEP 1: Revert Labels to Original Names
// -----------------------------------------------------------------------------

// 1.1 ApplicationIR → Application
MATCH (n:ApplicationIR)
SET n:Application
REMOVE n:ApplicationIR;

// 1.2 DomainModelIR → DomainModel
MATCH (n:DomainModelIR)
SET n:DomainModel
REMOVE n:DomainModelIR;

// 1.3 APIModelIR → APIModel
MATCH (n:APIModelIR)
SET n:APIModel
REMOVE n:APIModelIR;

// 1.4 BehaviorModelIR → BehaviorModel
MATCH (n:BehaviorModelIR)
SET n:BehaviorModel
REMOVE n:BehaviorModelIR;

// 1.5 ValidationModelIR → ValidationModel
MATCH (n:ValidationModelIR)
SET n:ValidationModel
REMOVE n:ValidationModelIR;

// 1.6 InfrastructureModelIR → InfrastructureModel
MATCH (n:InfrastructureModelIR)
SET n:InfrastructureModel
REMOVE n:InfrastructureModelIR;

// -----------------------------------------------------------------------------
// STEP 2: Restore Old Constraints
// -----------------------------------------------------------------------------

// Drop new constraints
DROP CONSTRAINT applicationir_app_id IF EXISTS;
DROP CONSTRAINT domainmodelir_app_id IF EXISTS;
DROP CONSTRAINT apimodelir_app_id IF EXISTS;
DROP CONSTRAINT behaviormodelir_app_id IF EXISTS;
DROP CONSTRAINT validationmodelir_app_id IF EXISTS;
DROP CONSTRAINT infrastructuremodelir_app_id IF EXISTS;

// Recreate old constraints
CREATE CONSTRAINT application_app_id IF NOT EXISTS
FOR (n:Application) REQUIRE n.app_id IS UNIQUE;

// Note: Orphan nodes cannot be restored - they are permanently deleted

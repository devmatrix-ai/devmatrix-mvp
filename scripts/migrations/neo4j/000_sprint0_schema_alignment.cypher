// =============================================================================
// Sprint 0: Schema Alignment & Cleanup
// Fecha: 2025-11-29
// Descripción: Cleanup orphans, rename labels to IR suffix
// =============================================================================

// -----------------------------------------------------------------------------
// STEP 1: Identify Orphan Nodes (DRY RUN - verificar antes de eliminar)
// -----------------------------------------------------------------------------

// Query para identificar orphan DomainModels
// MATCH (d:DomainModel)
// WHERE NOT EXISTS { MATCH (:Application)-[:HAS_DOMAIN_MODEL]->(d) }
// RETURN d.app_id, d;

// -----------------------------------------------------------------------------
// STEP 2: Delete Orphan DomainModel Nodes
// -----------------------------------------------------------------------------

MATCH (d:DomainModel)
WHERE NOT EXISTS { MATCH (:Application)-[:HAS_DOMAIN_MODEL]->(d) }
DETACH DELETE d;

// -----------------------------------------------------------------------------
// STEP 3: Rename Labels to IR Suffix
// Neo4j permite tener múltiples labels - agregamos el nuevo y removemos el viejo
// -----------------------------------------------------------------------------

// 3.1 Application → ApplicationIR
MATCH (n:Application)
SET n:ApplicationIR
REMOVE n:Application;

// 3.2 DomainModel → DomainModelIR
MATCH (n:DomainModel)
SET n:DomainModelIR
REMOVE n:DomainModel;

// 3.3 APIModel → APIModelIR
MATCH (n:APIModel)
SET n:APIModelIR
REMOVE n:APIModel;

// 3.4 BehaviorModel → BehaviorModelIR
MATCH (n:BehaviorModel)
SET n:BehaviorModelIR
REMOVE n:BehaviorModel;

// 3.5 ValidationModel → ValidationModelIR
MATCH (n:ValidationModel)
SET n:ValidationModelIR
REMOVE n:ValidationModel;

// 3.6 InfrastructureModel → InfrastructureModelIR
MATCH (n:InfrastructureModel)
SET n:InfrastructureModelIR
REMOVE n:InfrastructureModel;

// -----------------------------------------------------------------------------
// STEP 4: Update Constraints (drop old, create new)
// -----------------------------------------------------------------------------

// Drop old constraints (if they exist)
DROP CONSTRAINT application_app_id IF EXISTS;
DROP CONSTRAINT domainmodel_app_id IF EXISTS;
DROP CONSTRAINT apimodel_app_id IF EXISTS;
DROP CONSTRAINT behaviormodel_app_id IF EXISTS;
DROP CONSTRAINT validationmodel_app_id IF EXISTS;
DROP CONSTRAINT infrastructuremodel_app_id IF EXISTS;

// Create new constraints with IR suffix
CREATE CONSTRAINT applicationir_app_id IF NOT EXISTS
FOR (n:ApplicationIR) REQUIRE n.app_id IS UNIQUE;

CREATE CONSTRAINT domainmodelir_app_id IF NOT EXISTS
FOR (n:DomainModelIR) REQUIRE n.app_id IS UNIQUE;

CREATE CONSTRAINT apimodelir_app_id IF NOT EXISTS
FOR (n:APIModelIR) REQUIRE n.app_id IS UNIQUE;

CREATE CONSTRAINT behaviormodelir_app_id IF NOT EXISTS
FOR (n:BehaviorModelIR) REQUIRE n.app_id IS UNIQUE;

CREATE CONSTRAINT validationmodelir_app_id IF NOT EXISTS
FOR (n:ValidationModelIR) REQUIRE n.app_id IS UNIQUE;

CREATE CONSTRAINT infrastructuremodelir_app_id IF NOT EXISTS
FOR (n:InfrastructureModelIR) REQUIRE n.app_id IS UNIQUE;

// -----------------------------------------------------------------------------
// STEP 5: Verification Queries (run these to verify success)
// -----------------------------------------------------------------------------

// Verify no old labels remain:
// MATCH (n) WHERE any(label IN labels(n) WHERE label IN ['Application', 'DomainModel', 'APIModel', 'BehaviorModel', 'ValidationModel', 'InfrastructureModel'])
// RETURN labels(n), count(n);

// Verify new labels exist:
// MATCH (n) WHERE any(label IN labels(n) WHERE label IN ['ApplicationIR', 'DomainModelIR', 'APIModelIR', 'BehaviorModelIR', 'ValidationModelIR', 'InfrastructureModelIR'])
// RETURN labels(n)[0] as label, count(n) as count ORDER BY label;

// Verify no orphans:
// MATCH (d:DomainModelIR) WHERE NOT EXISTS { MATCH (:ApplicationIR)-[:HAS_DOMAIN_MODEL]->(d) } RETURN count(d);

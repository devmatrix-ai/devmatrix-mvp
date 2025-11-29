// ============================================================
// NeoDash Views Roadmap - Neo4j Migration
// SR.7: Dashboard Queries for Each Sprint
// Date: 2025-11-29
// ============================================================

// ============================================================
// DASHBOARD 1: Application Overview
// ============================================================

// 1.1 Application Summary Card
MATCH (app:ApplicationIR)
OPTIONAL MATCH (app)-[:HAS_DOMAIN_MODEL]->(dm:DomainModelIR)
OPTIONAL MATCH (dm)-[:HAS_ENTITY]->(e:Entity)
OPTIONAL MATCH (app)-[:HAS_API_MODEL]->(api:APIModelIR)
OPTIONAL MATCH (api)-[:HAS_ENDPOINT]->(ep:Endpoint)
OPTIONAL MATCH (app)-[:HAS_BEHAVIOR_MODEL]->(bm:BehaviorModelIR)
OPTIONAL MATCH (bm)-[:HAS_FLOW]->(f:Flow)
RETURN app.name as Application,
       app.app_id as AppID,
       count(DISTINCT e) as Entities,
       count(DISTINCT ep) as Endpoints,
       count(DISTINCT f) as Flows,
       app.version as Version
ORDER BY app.name;

// 1.2 Schema Version Timeline
MATCH (v:GraphSchemaVersion)
RETURN v.version as Version,
       v.description as Description,
       v.applied_at as AppliedAt,
       v.applied_by as AppliedBy
ORDER BY v.version DESC
LIMIT 10;

// ============================================================
// DASHBOARD 2: Domain Model Analytics (Sprint 1)
// ============================================================

// 2.1 Entities by Application
MATCH (app:ApplicationIR)-[:HAS_DOMAIN_MODEL]->(dm:DomainModelIR)-[:HAS_ENTITY]->(e:Entity)
WITH app.name as Application, collect(e.name) as Entities, count(e) as EntityCount
RETURN Application, EntityCount, Entities
ORDER BY EntityCount DESC;

// 2.2 Attributes per Entity Distribution
MATCH (e:Entity)-[:HAS_ATTRIBUTE]->(a:Attribute)
WITH e.name as Entity, count(a) as AttributeCount
RETURN Entity, AttributeCount
ORDER BY AttributeCount DESC
LIMIT 20;

// 2.3 Entity Relationships Graph
MATCH (e1:Entity)-[r:RELATES_TO]->(e2:Entity)
RETURN e1.name as Source,
       type(r) as RelationType,
       r.type as Cardinality,
       e2.name as Target;

// 2.4 Data Types Distribution
MATCH (a:Attribute)
RETURN a.data_type as DataType, count(a) as Count
ORDER BY Count DESC;

// ============================================================
// DASHBOARD 3: API Model Analytics (Sprint 2)
// ============================================================

// 3.1 Endpoints by HTTP Method
MATCH (ep:Endpoint)
RETURN ep.method as Method, count(ep) as Count
ORDER BY Count DESC;

// 3.2 API Coverage - Endpoints with Entity Targets
MATCH (api:APIModelIR)-[:HAS_ENDPOINT]->(ep:Endpoint)
OPTIONAL MATCH (ep)-[:TARGETS_ENTITY]->(e:Entity)
WITH api.app_id as AppID,
     count(ep) as TotalEndpoints,
     count(e) as LinkedEndpoints
RETURN AppID,
       TotalEndpoints,
       LinkedEndpoints,
       round(100.0 * LinkedEndpoints / TotalEndpoints, 2) as CoveragePercent
ORDER BY CoveragePercent ASC;

// 3.3 Endpoints by Path Pattern
MATCH (ep:Endpoint)
WITH split(ep.path, '/')[1] as Resource, count(ep) as Count
WHERE Resource IS NOT NULL AND Resource <> ''
RETURN Resource, Count
ORDER BY Count DESC
LIMIT 15;

// 3.4 Parameters per Endpoint
MATCH (ep:Endpoint)-[:HAS_PARAMETER]->(p:APIParameter)
WITH ep.path as Endpoint, ep.method as Method, count(p) as ParamCount
RETURN Endpoint, Method, ParamCount
ORDER BY ParamCount DESC
LIMIT 20;

// ============================================================
// DASHBOARD 4: Behavior Model Analytics (Sprint 3)
// ============================================================

// 4.1 Flows by Type
MATCH (f:Flow)
RETURN f.type as FlowType, count(f) as Count
ORDER BY Count DESC;

// 4.2 Steps per Flow Distribution
MATCH (f:Flow)-[:HAS_STEP]->(s:Step)
WITH f.name as FlowName, count(s) as StepCount
RETURN FlowName, StepCount
ORDER BY StepCount DESC
LIMIT 20;

// 4.3 Cross-Domain Relationships (Steps → Entities)
MATCH (s:Step)-[:TARGETS_ENTITY]->(e:Entity)
RETURN s.action as Action, e.name as TargetEntity, count(*) as Occurrences
ORDER BY Occurrences DESC
LIMIT 20;

// 4.4 Invariants by Entity
MATCH (inv:Invariant)
RETURN inv.entity as Entity,
       inv.enforcement_level as Level,
       count(*) as InvariantCount
ORDER BY InvariantCount DESC;

// ============================================================
// DASHBOARD 5: Validation Model Analytics (Sprint 4)
// ============================================================

// 5.1 Validation Rules by Type
MATCH (r:ValidationRule)
RETURN r.type as RuleType, count(r) as Count
ORDER BY Count DESC;

// 5.2 Rules by Severity
MATCH (r:ValidationRule)
RETURN r.severity as Severity, count(r) as Count
ORDER BY Count DESC;

// 5.3 Rules per Entity
MATCH (r:ValidationRule)
WHERE r.entity IS NOT NULL
RETURN r.entity as Entity, count(r) as RuleCount
ORDER BY RuleCount DESC
LIMIT 15;

// ============================================================
// DASHBOARD 6: Test Model Analytics (Sprint 5)
// ============================================================

// 6.1 Test Scenarios by Priority
MATCH (ts:TestScenarioIR)
RETURN ts.priority as Priority, count(ts) as Count
ORDER BY Count DESC;

// 6.2 Test Coverage by Endpoint
MATCH (ep:Endpoint)
OPTIONAL MATCH (ts:TestScenarioIR)-[:VALIDATES_ENDPOINT]->(ep)
WITH ep.path as Endpoint, ep.method as Method, count(ts) as TestCount
RETURN Endpoint, Method, TestCount
ORDER BY TestCount ASC
LIMIT 20;

// 6.3 Seed Entities
MATCH (seed:SeedEntityIR)
RETURN seed.entity_name as Entity,
       seed.scenario as Scenario,
       seed.count as RecordCount
ORDER BY Entity;

// ============================================================
// DASHBOARD 7: Graph Health Monitor (SR.1)
// ============================================================

// 7.1 Node Count by Label
CALL db.labels() YIELD label
CALL {
    WITH label
    MATCH (n)
    WHERE label IN labels(n)
    RETURN count(n) as cnt
}
RETURN label as Label, cnt as Count
ORDER BY Count DESC;

// 7.2 Orphan Nodes Detection
MATCH (n)
WHERE NOT (n)--()
  AND NOT n:GraphSchemaVersion
  AND NOT n:MigrationRun
  AND NOT n:MigrationCheckpoint
RETURN labels(n) as NodeType, count(n) as OrphanCount
ORDER BY OrphanCount DESC;

// 7.3 Relationship Count by Type
CALL db.relationshipTypes() YIELD relationshipType
CALL {
    WITH relationshipType
    MATCH ()-[r]->()
    WHERE type(r) = relationshipType
    RETURN count(r) as cnt
}
RETURN relationshipType as RelationType, cnt as Count
ORDER BY Count DESC;

// 7.4 Temporal Metadata Coverage
MATCH (n)
WHERE n.created_at IS NOT NULL
WITH labels(n)[0] as Label, count(n) as WithTimestamp
MATCH (m)
WHERE labels(m)[0] = Label
WITH Label, WithTimestamp, count(m) as Total
RETURN Label,
       WithTimestamp,
       Total,
       round(100.0 * WithTimestamp / Total, 2) as CoveragePercent
ORDER BY CoveragePercent ASC;

// ============================================================
// DASHBOARD 8: Migration History (SR.2)
// ============================================================

// 8.1 Migration Runs
MATCH (m:MigrationRun)
RETURN m.migration_id as Migration,
       m.status as Status,
       m.started_at as StartedAt,
       m.completed_at as CompletedAt,
       m.nodes_created as NodesCreated,
       m.relationships_created as RelsCreated
ORDER BY m.started_at DESC
LIMIT 20;

// 8.2 Migration Checkpoints
MATCH (c:MigrationCheckpoint)
RETURN c.migration_id as Migration,
       c.status as Status,
       c.batch_index as BatchIndex,
       c.total_batches as TotalBatches,
       c.updated_at as UpdatedAt
ORDER BY c.created_at DESC
LIMIT 20;

// ============================================================
// DASHBOARD 9: Full IR Loader Performance (SR.6)
// ============================================================

// 9.1 Application Load Stats
MATCH (app:ApplicationIR)
OPTIONAL MATCH (app)-[:HAS_DOMAIN_MODEL]->(dm:DomainModelIR)-[:HAS_ENTITY]->(e:Entity)
OPTIONAL MATCH (e)-[:HAS_ATTRIBUTE]->(a:Attribute)
OPTIONAL MATCH (app)-[:HAS_API_MODEL]->(api:APIModelIR)-[:HAS_ENDPOINT]->(ep:Endpoint)
OPTIONAL MATCH (app)-[:HAS_BEHAVIOR_MODEL]->(bm:BehaviorModelIR)-[:HAS_FLOW]->(f:Flow)
OPTIONAL MATCH (f)-[:HAS_STEP]->(s:Step)
WITH app.app_id as AppID,
     count(DISTINCT e) as Entities,
     count(DISTINCT a) as Attributes,
     count(DISTINCT ep) as Endpoints,
     count(DISTINCT f) as Flows,
     count(DISTINCT s) as Steps
RETURN AppID,
       Entities,
       Attributes,
       Endpoints,
       Flows,
       Steps,
       Entities + Attributes + Endpoints + Flows + Steps as TotalNodes
ORDER BY TotalNodes DESC;

// 9.2 Submodel Completeness
MATCH (app:ApplicationIR)
OPTIONAL MATCH (app)-[:HAS_DOMAIN_MODEL]->(dm:DomainModelIR)
OPTIONAL MATCH (app)-[:HAS_API_MODEL]->(api:APIModelIR)
OPTIONAL MATCH (app)-[:HAS_BEHAVIOR_MODEL]->(bm:BehaviorModelIR)
OPTIONAL MATCH (app)-[:HAS_VALIDATION_MODEL]->(vm:ValidationModelIR)
OPTIONAL MATCH (app)-[:HAS_INFRASTRUCTURE_MODEL]->(im:InfrastructureModelIR)
OPTIONAL MATCH (app)-[:HAS_TESTS_MODEL]->(tm:TestsModelIR)
RETURN app.name as Application,
       CASE WHEN dm IS NOT NULL THEN '✅' ELSE '❌' END as DomainModel,
       CASE WHEN api IS NOT NULL THEN '✅' ELSE '❌' END as APIModel,
       CASE WHEN bm IS NOT NULL THEN '✅' ELSE '❌' END as BehaviorModel,
       CASE WHEN vm IS NOT NULL THEN '✅' ELSE '❌' END as ValidationModel,
       CASE WHEN im IS NOT NULL THEN '✅' ELSE '❌' END as InfraModel,
       CASE WHEN tm IS NOT NULL THEN '✅' ELSE '❌' END as TestsModel;

// ============================================================
// DASHBOARD 10: Overall System Health Score
// ============================================================

// 10.1 Comprehensive Health Check
MATCH (app:ApplicationIR)
WITH count(app) as TotalApps

MATCH (e:Entity)
WITH TotalApps, count(e) as TotalEntities

MATCH (ep:Endpoint)
WITH TotalApps, TotalEntities, count(ep) as TotalEndpoints

MATCH (ep:Endpoint)-[:TARGETS_ENTITY]->(e:Entity)
WITH TotalApps, TotalEntities, TotalEndpoints, count(DISTINCT ep) as LinkedEndpoints

MATCH (n) WHERE n.created_at IS NOT NULL
WITH TotalApps, TotalEntities, TotalEndpoints, LinkedEndpoints, count(n) as NodesWithTimestamp

MATCH (m)
WITH TotalApps, TotalEntities, TotalEndpoints, LinkedEndpoints, NodesWithTimestamp, count(m) as TotalNodes

MATCH (orphan)
WHERE NOT (orphan)--()
  AND NOT orphan:GraphSchemaVersion
  AND NOT orphan:MigrationRun
  AND NOT orphan:MigrationCheckpoint
WITH TotalApps, TotalEntities, TotalEndpoints, LinkedEndpoints, NodesWithTimestamp, TotalNodes, count(orphan) as OrphanNodes

RETURN
    TotalApps as Applications,
    TotalEntities as Entities,
    TotalEndpoints as Endpoints,
    round(100.0 * LinkedEndpoints / TotalEndpoints, 2) as APILinkagePercent,
    round(100.0 * NodesWithTimestamp / TotalNodes, 2) as TemporalCoveragePercent,
    OrphanNodes as OrphanNodes,
    CASE
        WHEN OrphanNodes = 0
         AND 100.0 * LinkedEndpoints / TotalEndpoints >= 80
         AND 100.0 * NodesWithTimestamp / TotalNodes >= 95
        THEN '✅ HEALTHY'
        ELSE '⚠️ NEEDS ATTENTION'
    END as HealthStatus;

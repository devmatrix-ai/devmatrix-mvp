"""MGE V2 Schema - Add atomic units, dependency graphs, validation, and execution tables

Revision ID: mge_v2_schema
Revises: 20251022_1351_discovery_documents_user_id_fk
Create Date: 2025-10-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'mge_v2_schema'
down_revision = '20251022_1351_discovery_documents_user_id_fk'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add MGE V2 tables for atomic execution:
    - atomic_units: 10 LOC execution units
    - atom_dependencies: Dependency edges between atoms
    - dependency_graphs: Graph metadata and configuration
    - validation_results: 4-level hierarchical validation
    - execution_waves: Parallel execution groups
    - atom_retry_history: Retry tracking with feedback
    - human_review_queue: Manual review queue for low-confidence atoms

    Also adds V2 metadata to masterplans table.
    """

    # 1. Create dependency_graphs table
    op.create_table('dependency_graphs',
        sa.Column('graph_id', sa.UUID(), nullable=False),
        sa.Column('masterplan_id', sa.UUID(), nullable=False),
        sa.Column('graph_data', postgresql.JSONB(), nullable=False, comment='NetworkX graph as JSON'),
        sa.Column('total_atoms', sa.Integer(), nullable=False),
        sa.Column('total_edges', sa.Integer(), nullable=False),
        sa.Column('total_waves', sa.Integer(), nullable=False),
        sa.Column('max_parallelism', sa.Integer(), nullable=False, comment='Max atoms that can run in parallel'),
        sa.Column('has_cycles', sa.Boolean(), nullable=False, default=False),
        sa.Column('topological_order', postgresql.ARRAY(sa.UUID()), nullable=True, comment='Sorted atom IDs'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('graph_id'),
        sa.ForeignKeyConstraint(['masterplan_id'], ['masterplans.masterplan_id'], ondelete='CASCADE')
    )
    op.create_index('idx_dependency_graphs_masterplan', 'dependency_graphs', ['masterplan_id'], unique=False)
    op.create_index('idx_dependency_graphs_created', 'dependency_graphs', ['created_at'], unique=False)

    # 2. Create atomic_units table (replaces MasterPlanSubtask)
    op.create_table('atomic_units',
        sa.Column('atom_id', sa.UUID(), nullable=False),
        sa.Column('masterplan_id', sa.UUID(), nullable=False),
        sa.Column('task_id', sa.UUID(), nullable=True, comment='Original task ID (for migration)'),
        sa.Column('atom_number', sa.Integer(), nullable=False, comment='Sequential number within masterplan'),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('code_to_generate', sa.Text(), nullable=False, comment='Code implementation'),
        sa.Column('file_path', sa.String(length=500), nullable=True, comment='Target file path'),
        sa.Column('line_start', sa.Integer(), nullable=True, comment='Start line in file'),
        sa.Column('line_end', sa.Integer(), nullable=True, comment='End line in file'),
        sa.Column('language', sa.String(length=50), nullable=False, comment='Programming language'),
        sa.Column('loc', sa.Integer(), nullable=False, comment='Lines of code'),
        sa.Column('complexity', sa.Float(), nullable=False, comment='Cyclomatic complexity'),

        # Context for execution
        sa.Column('imports', postgresql.JSONB(), nullable=True, comment='Required imports'),
        sa.Column('type_schema', postgresql.JSONB(), nullable=True, comment='Type definitions'),
        sa.Column('preconditions', postgresql.JSONB(), nullable=True, comment='Required state before execution'),
        sa.Column('postconditions', postgresql.JSONB(), nullable=True, comment='Expected state after execution'),
        sa.Column('test_cases', postgresql.JSONB(), nullable=True, comment='Generated test cases'),
        sa.Column('context_completeness', sa.Float(), nullable=True, comment='Context quality score 0.0-1.0'),

        # Atomicity validation
        sa.Column('atomicity_score', sa.Float(), nullable=True, comment='Atomicity quality 0.0-1.0'),
        sa.Column('atomicity_violations', postgresql.JSONB(), nullable=True, comment='List of violations'),
        sa.Column('is_atomic', sa.Boolean(), nullable=False, default=True),

        # Execution state
        sa.Column('status', sa.Enum('PENDING', 'READY', 'RUNNING', 'COMPLETED', 'FAILED', 'BLOCKED', 'SKIPPED', name='atomstatus'), nullable=False, default='PENDING'),
        sa.Column('wave_number', sa.Integer(), nullable=True, comment='Execution wave'),
        sa.Column('attempts', sa.Integer(), nullable=False, default=0),
        sa.Column('max_attempts', sa.Integer(), nullable=False, default=3),
        sa.Column('execution_result', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),

        # Confidence and review
        sa.Column('confidence_score', sa.Float(), nullable=True, comment='Execution confidence 0.0-1.0'),
        sa.Column('needs_review', sa.Boolean(), nullable=False, default=False),
        sa.Column('review_priority', sa.Integer(), nullable=True, comment='1=highest, higher=lower'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),

        sa.PrimaryKeyConstraint('atom_id'),
        sa.ForeignKeyConstraint(['masterplan_id'], ['masterplans.masterplan_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['masterplan_tasks.task_id'], ondelete='SET NULL')
    )
    op.create_index('idx_atomic_units_masterplan', 'atomic_units', ['masterplan_id'], unique=False)
    op.create_index('idx_atomic_units_task', 'atomic_units', ['task_id'], unique=False)
    op.create_index('idx_atomic_units_status', 'atomic_units', ['status'], unique=False)
    op.create_index('idx_atomic_units_wave', 'atomic_units', ['wave_number'], unique=False)
    op.create_index('idx_atomic_units_review', 'atomic_units', ['needs_review'], unique=False)
    op.create_index('idx_atomic_units_confidence', 'atomic_units', ['confidence_score'], unique=False)

    # 3. Create atom_dependencies table
    op.create_table('atom_dependencies',
        sa.Column('dependency_id', sa.UUID(), nullable=False),
        sa.Column('graph_id', sa.UUID(), nullable=False),
        sa.Column('from_atom_id', sa.UUID(), nullable=False, comment='Dependent atom'),
        sa.Column('to_atom_id', sa.UUID(), nullable=False, comment='Dependency atom (must execute first)'),
        sa.Column('dependency_type', sa.Enum('IMPORT', 'DATA_FLOW', 'FUNCTION_CALL', 'TYPE', 'TEMPORAL', name='dependencytype'), nullable=False),
        sa.Column('strength', sa.Float(), nullable=False, default=1.0, comment='Dependency strength 0.0-1.0'),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, comment='Additional dependency info'),
        sa.Column('created_at', sa.DateTime(), nullable=False),

        sa.PrimaryKeyConstraint('dependency_id'),
        sa.ForeignKeyConstraint(['graph_id'], ['dependency_graphs.graph_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['from_atom_id'], ['atomic_units.atom_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['to_atom_id'], ['atomic_units.atom_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('from_atom_id', 'to_atom_id', name='uq_atom_dependency')
    )
    op.create_index('idx_dependencies_graph', 'atom_dependencies', ['graph_id'], unique=False)
    op.create_index('idx_dependencies_from', 'atom_dependencies', ['from_atom_id'], unique=False)
    op.create_index('idx_dependencies_to', 'atom_dependencies', ['to_atom_id'], unique=False)
    op.create_index('idx_dependencies_type', 'atom_dependencies', ['dependency_type'], unique=False)

    # 4. Create validation_results table (4-level hierarchical validation)
    op.create_table('validation_results',
        sa.Column('validation_id', sa.UUID(), nullable=False),
        sa.Column('atom_id', sa.UUID(), nullable=False),
        sa.Column('validation_level', sa.Enum('ATOMIC', 'MODULE', 'COMPONENT', 'SYSTEM', name='validationlevel'), nullable=False),
        sa.Column('level_number', sa.Integer(), nullable=False, comment='1=Atomic, 2=Module, 3=Component, 4=System'),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('test_type', sa.String(length=100), nullable=False, comment='syntax|types|unit|integration|e2e|acceptance'),
        sa.Column('test_output', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSONB(), nullable=True),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),

        sa.PrimaryKeyConstraint('validation_id'),
        sa.ForeignKeyConstraint(['atom_id'], ['atomic_units.atom_id'], ondelete='CASCADE')
    )
    op.create_index('idx_validation_atom', 'validation_results', ['atom_id'], unique=False)
    op.create_index('idx_validation_level', 'validation_results', ['validation_level'], unique=False)
    op.create_index('idx_validation_passed', 'validation_results', ['passed'], unique=False)
    op.create_index('idx_validation_created', 'validation_results', ['created_at'], unique=False)

    # 5. Create execution_waves table
    op.create_table('execution_waves',
        sa.Column('wave_id', sa.UUID(), nullable=False),
        sa.Column('graph_id', sa.UUID(), nullable=False),
        sa.Column('wave_number', sa.Integer(), nullable=False),
        sa.Column('atom_ids', postgresql.ARRAY(sa.UUID()), nullable=False, comment='Atoms in this wave'),
        sa.Column('total_atoms', sa.Integer(), nullable=False),
        sa.Column('completed_atoms', sa.Integer(), nullable=False, default=0),
        sa.Column('failed_atoms', sa.Integer(), nullable=False, default=0),
        sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'PARTIAL', name='wavestatus'), nullable=False, default='PENDING'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),

        sa.PrimaryKeyConstraint('wave_id'),
        sa.ForeignKeyConstraint(['graph_id'], ['dependency_graphs.graph_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('graph_id', 'wave_number', name='uq_wave_number')
    )
    op.create_index('idx_waves_graph', 'execution_waves', ['graph_id'], unique=False)
    op.create_index('idx_waves_number', 'execution_waves', ['wave_number'], unique=False)
    op.create_index('idx_waves_status', 'execution_waves', ['status'], unique=False)

    # 6. Create atom_retry_history table
    op.create_table('atom_retry_history',
        sa.Column('retry_id', sa.UUID(), nullable=False),
        sa.Column('atom_id', sa.UUID(), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('temperature', sa.Float(), nullable=False, comment='LLM temperature used'),
        sa.Column('prompt_variation', sa.Text(), nullable=True, comment='Modified prompt with error feedback'),
        sa.Column('error_analysis', postgresql.JSONB(), nullable=True, comment='Parsed error info'),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('execution_result', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),

        sa.PrimaryKeyConstraint('retry_id'),
        sa.ForeignKeyConstraint(['atom_id'], ['atomic_units.atom_id'], ondelete='CASCADE')
    )
    op.create_index('idx_retry_atom', 'atom_retry_history', ['atom_id'], unique=False)
    op.create_index('idx_retry_attempt', 'atom_retry_history', ['attempt_number'], unique=False)
    op.create_index('idx_retry_success', 'atom_retry_history', ['success'], unique=False)
    op.create_index('idx_retry_created', 'atom_retry_history', ['created_at'], unique=False)

    # 7. Create human_review_queue table
    op.create_table('human_review_queue',
        sa.Column('review_id', sa.UUID(), nullable=False),
        sa.Column('atom_id', sa.UUID(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False, comment='Why flagged for review'),
        sa.Column('flagged_reason', sa.Text(), nullable=True, comment='Specific issues detected'),
        sa.Column('ai_suggestions', postgresql.JSONB(), nullable=True, comment='AI-generated fix suggestions'),
        sa.Column('priority', sa.Integer(), nullable=False, default=5, comment='1=critical, 5=low'),
        sa.Column('status', sa.Enum('PENDING', 'IN_REVIEW', 'APPROVED', 'REJECTED', 'EDITED', 'REGENERATED', name='reviewstatus'), nullable=False, default='PENDING'),
        sa.Column('assigned_to', sa.UUID(), nullable=True, comment='User ID of reviewer'),
        sa.Column('reviewer_feedback', sa.Text(), nullable=True),
        sa.Column('resolution', sa.Enum('APPROVE', 'EDIT', 'REGENERATE', 'SKIP', name='reviewresolution'), nullable=True),
        sa.Column('edited_code', sa.Text(), nullable=True, comment='Human-edited version'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),

        sa.PrimaryKeyConstraint('review_id'),
        sa.ForeignKeyConstraint(['atom_id'], ['atomic_units.atom_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.user_id'], ondelete='SET NULL')
    )
    op.create_index('idx_review_atom', 'human_review_queue', ['atom_id'], unique=False)
    op.create_index('idx_review_status', 'human_review_queue', ['status'], unique=False)
    op.create_index('idx_review_priority', 'human_review_queue', ['priority'], unique=False)
    op.create_index('idx_review_assigned', 'human_review_queue', ['assigned_to'], unique=False)
    op.create_index('idx_review_confidence', 'human_review_queue', ['confidence_score'], unique=False)

    # 8. Add V2 metadata columns to masterplans table
    op.add_column('masterplans', sa.Column('v2_mode', sa.Boolean(), nullable=False, server_default='false', comment='True if using MGE V2'))
    op.add_column('masterplans', sa.Column('atomization_config', postgresql.JSONB(), nullable=True, comment='V2 atomization settings'))
    op.add_column('masterplans', sa.Column('graph_id', sa.UUID(), nullable=True, comment='FK to dependency_graphs'))
    op.add_column('masterplans', sa.Column('total_atoms', sa.Integer(), nullable=True, comment='V2: total atomic units'))
    op.add_column('masterplans', sa.Column('total_waves', sa.Integer(), nullable=True, comment='V2: execution waves'))
    op.add_column('masterplans', sa.Column('max_parallelism', sa.Integer(), nullable=True, comment='V2: max concurrent atoms'))
    op.add_column('masterplans', sa.Column('precision_percent', sa.Float(), nullable=True, comment='V2: execution precision'))

    op.create_foreign_key('fk_masterplans_graph', 'masterplans', 'dependency_graphs', ['graph_id'], ['graph_id'], ondelete='SET NULL')
    op.create_index('idx_masterplans_v2_mode', 'masterplans', ['v2_mode'], unique=False)
    op.create_index('idx_masterplans_graph', 'masterplans', ['graph_id'], unique=False)


def downgrade() -> None:
    """
    Remove all MGE V2 tables and columns.
    WARNING: This will delete all V2 data!
    """
    # Drop V2 columns from masterplans
    op.drop_constraint('fk_masterplans_graph', 'masterplans', type_='foreignkey')
    op.drop_index('idx_masterplans_graph', 'masterplans')
    op.drop_index('idx_masterplans_v2_mode', 'masterplans')
    op.drop_column('masterplans', 'precision_percent')
    op.drop_column('masterplans', 'max_parallelism')
    op.drop_column('masterplans', 'total_waves')
    op.drop_column('masterplans', 'total_atoms')
    op.drop_column('masterplans', 'graph_id')
    op.drop_column('masterplans', 'atomization_config')
    op.drop_column('masterplans', 'v2_mode')

    # Drop tables in reverse dependency order
    op.drop_index('idx_review_confidence', 'human_review_queue')
    op.drop_index('idx_review_assigned', 'human_review_queue')
    op.drop_index('idx_review_priority', 'human_review_queue')
    op.drop_index('idx_review_status', 'human_review_queue')
    op.drop_index('idx_review_atom', 'human_review_queue')
    op.drop_table('human_review_queue')

    op.drop_index('idx_retry_created', 'atom_retry_history')
    op.drop_index('idx_retry_success', 'atom_retry_history')
    op.drop_index('idx_retry_attempt', 'atom_retry_history')
    op.drop_index('idx_retry_atom', 'atom_retry_history')
    op.drop_table('atom_retry_history')

    op.drop_index('idx_waves_status', 'execution_waves')
    op.drop_index('idx_waves_number', 'execution_waves')
    op.drop_index('idx_waves_graph', 'execution_waves')
    op.drop_table('execution_waves')

    op.drop_index('idx_validation_created', 'validation_results')
    op.drop_index('idx_validation_passed', 'validation_results')
    op.drop_index('idx_validation_level', 'validation_results')
    op.drop_index('idx_validation_atom', 'validation_results')
    op.drop_table('validation_results')

    op.drop_index('idx_dependencies_type', 'atom_dependencies')
    op.drop_index('idx_dependencies_to', 'atom_dependencies')
    op.drop_index('idx_dependencies_from', 'atom_dependencies')
    op.drop_index('idx_dependencies_graph', 'atom_dependencies')
    op.drop_table('atom_dependencies')

    op.drop_index('idx_atomic_units_confidence', 'atomic_units')
    op.drop_index('idx_atomic_units_review', 'atomic_units')
    op.drop_index('idx_atomic_units_wave', 'atomic_units')
    op.drop_index('idx_atomic_units_status', 'atomic_units')
    op.drop_index('idx_atomic_units_task', 'atomic_units')
    op.drop_index('idx_atomic_units_masterplan', 'atomic_units')
    op.drop_table('atomic_units')

    op.drop_index('idx_dependency_graphs_created', 'dependency_graphs')
    op.drop_index('idx_dependency_graphs_masterplan', 'dependency_graphs')
    op.drop_table('dependency_graphs')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS reviewresolution')
    op.execute('DROP TYPE IF EXISTS reviewstatus')
    op.execute('DROP TYPE IF EXISTS wavestatus')
    op.execute('DROP TYPE IF EXISTS validationlevel')
    op.execute('DROP TYPE IF EXISTS dependencytype')
    op.execute('DROP TYPE IF EXISTS atomstatus')

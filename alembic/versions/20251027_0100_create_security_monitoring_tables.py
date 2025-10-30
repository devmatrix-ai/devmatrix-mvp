"""create security monitoring tables

Revision ID: 20251027_0100
Revises: 20251026_2330
Create Date: 2025-10-27 01:00:00.000000

Phase 2 - Task Group 11: Database Schema - Security Monitoring Tables
Creates security_events and alert_history tables for security monitoring and alerting.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251027_0100'
down_revision = '20251026_2330'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create security_events and alert_history tables.

    security_events stores security anomaly detection events:
    - Failed login clusters
    - Geo-location changes
    - Privilege escalation
    - Unusual access patterns
    - Multiple 403s
    - Account lockout events
    - 2FA disabled when enforced
    - Concurrent sessions from different countries

    alert_history tracks alert delivery for security events:
    - Email notifications
    - Slack webhooks
    - PagerDuty alerts
    """

    # Create security_events table
    op.create_table(
        'security_events',
        sa.Column('event_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('event_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('detected_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('resolved_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('event_id'),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name='ck_security_events_severity'
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.user_id'], ondelete='SET NULL')
    )

    # Create indexes for security_events
    op.create_index(
        'idx_security_events_user_id',
        'security_events',
        ['user_id']
    )
    op.create_index(
        'idx_security_events_detected_at',
        'security_events',
        ['detected_at']
    )
    op.create_index(
        'idx_security_events_severity',
        'security_events',
        ['severity']
    )
    op.create_index(
        'idx_security_events_resolved',
        'security_events',
        ['resolved']
    )

    # Create alert_history table
    op.create_table(
        'alert_history',
        sa.Column('alert_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('security_event_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('alert_type', sa.String(50), nullable=False),
        sa.Column('sent_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('alert_id'),
        sa.CheckConstraint(
            "status IN ('sent', 'failed', 'throttled')",
            name='ck_alert_history_status'
        ),
        sa.ForeignKeyConstraint(['security_event_id'], ['security_events.event_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE')
    )

    # Create indexes for alert_history
    op.create_index(
        'idx_alert_history_user_id',
        'alert_history',
        ['user_id']
    )
    op.create_index(
        'idx_alert_history_sent_at',
        'alert_history',
        ['sent_at']
    )


def downgrade():
    """Drop security monitoring tables and indexes."""
    # Drop alert_history table and indexes
    op.drop_index('idx_alert_history_sent_at', table_name='alert_history')
    op.drop_index('idx_alert_history_user_id', table_name='alert_history')
    op.drop_table('alert_history')

    # Drop security_events table and indexes
    op.drop_index('idx_security_events_resolved', table_name='security_events')
    op.drop_index('idx_security_events_severity', table_name='security_events')
    op.drop_index('idx_security_events_detected_at', table_name='security_events')
    op.drop_index('idx_security_events_user_id', table_name='security_events')
    op.drop_table('security_events')

"""Initial schema — all tables

Revision ID: 0001
Revises:
Create Date: 2026-10-15
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id',              sa.Integer(),     nullable=False, primary_key=True),
        sa.Column('email',           sa.String(255),   nullable=False, unique=True),
        sa.Column('full_name',       sa.String(255),   nullable=False),
        sa.Column('hashed_password', sa.String(255),   nullable=False),
        sa.Column('is_active',       sa.Boolean(),     nullable=False, server_default='true'),
        sa.Column('created_at',      sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at',      sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_id',    'users', ['id'])

    # ── enums ──────────────────────────────────────────────────────
    assessment_type_enum = sa.Enum(
        'complete', 'tremor', 'blink', 'asymmetry', 'ptosis',
        name='assessment_type_enum',
    )
    session_status_enum = sa.Enum(
        'active', 'completed', 'aborted',
        name='session_status_enum',
    )
    assessment_type_enum.create(op.get_bind(), checkfirst=True)
    session_status_enum.create(op.get_bind(), checkfirst=True)

    # ── monitoring_sessions ────────────────────────────────────────
    op.create_table(
        'monitoring_sessions',
        sa.Column('id',              sa.Integer(),     nullable=False, primary_key=True),
        sa.Column('user_id',         sa.Integer(),     nullable=False),
        sa.Column('assessment_type', sa.Enum('complete','tremor','blink','asymmetry','ptosis',
                                              name='assessment_type_enum',create_constraint=False),
                  nullable=False),
        sa.Column('status',          sa.Enum('active','completed','aborted',
                                              name='session_status_enum',create_constraint=False),
                  nullable=False, server_default='active'),
        sa.Column('started_at',      sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('ended_at',        sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds',sa.Float(),       nullable=True),
        sa.Column('notes',           sa.Text(),        nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_monitoring_sessions_id',      'monitoring_sessions', ['id'])
    op.create_index('ix_monitoring_sessions_user_id', 'monitoring_sessions', ['user_id'])

    # ── tremor_results ─────────────────────────────────────────────
    op.create_table(
        'tremor_results',
        sa.Column('id',               sa.Integer(),  nullable=False, primary_key=True),
        sa.Column('session_id',       sa.Integer(),  nullable=False),
        sa.Column('recorded_at',      sa.DateTime(timezone=True), nullable=False),
        sa.Column('max_frequency_hz', sa.Float(),    nullable=True),
        sa.Column('mean_amplitude_px',sa.Float(),    nullable=True),
        sa.Column('dominant_severity',sa.String(100),nullable=True),
        sa.Column('frames_with_hand', sa.Integer(),  nullable=True),
        sa.Column('total_frames',     sa.Integer(),  nullable=True),
        sa.Column('time_series',      sa.JSON(),     nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['monitoring_sessions.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_tremor_results_id',         'tremor_results', ['id'])
    op.create_index('ix_tremor_results_session_id', 'tremor_results', ['session_id'])

    # ── blink_results ──────────────────────────────────────────────
    op.create_table(
        'blink_results',
        sa.Column('id',                   sa.Integer(), nullable=False, primary_key=True),
        sa.Column('session_id',           sa.Integer(), nullable=False),
        sa.Column('recorded_at',          sa.DateTime(timezone=True), nullable=False),
        sa.Column('total_blinks',         sa.Integer(), nullable=True),
        sa.Column('session_duration_min', sa.Float(),   nullable=True),
        sa.Column('blink_rate',           sa.Float(),   nullable=True),
        sa.Column('short_blinks_count',   sa.Integer(), nullable=True),
        sa.Column('long_blinks_count',    sa.Integer(), nullable=True),
        sa.Column('abnormal_blink_count', sa.Integer(), nullable=True),
        sa.Column('duration_std',         sa.Float(),   nullable=True),
        sa.Column('rate_status',          sa.String(20),nullable=True),
        sa.Column('abnormality_flags',    sa.JSON(),    nullable=True),
        sa.Column('blink_log',            sa.JSON(),    nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['monitoring_sessions.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_blink_results_id',         'blink_results', ['id'])
    op.create_index('ix_blink_results_session_id', 'blink_results', ['session_id'])

    # ── asymmetry_results ──────────────────────────────────────────
    op.create_table(
        'asymmetry_results',
        sa.Column('id',                sa.Integer(), nullable=False, primary_key=True),
        sa.Column('session_id',        sa.Integer(), nullable=False),
        sa.Column('recorded_at',       sa.DateTime(timezone=True), nullable=False),
        sa.Column('avg_asym_score',    sa.Float(),   nullable=True),
        sa.Column('asym_events_count', sa.Integer(), nullable=True),
        sa.Column('micro_events_count',sa.Integer(), nullable=True),
        sa.Column('asym_events',       sa.JSON(),    nullable=True),
        sa.Column('micro_events',      sa.JSON(),    nullable=True),
        sa.Column('threshold_used',    sa.Float(),   nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['monitoring_sessions.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_asymmetry_results_id',         'asymmetry_results', ['id'])
    op.create_index('ix_asymmetry_results_session_id', 'asymmetry_results', ['session_id'])

    # ── ptosis_results ─────────────────────────────────────────────
    op.create_table(
        'ptosis_results',
        sa.Column('id',                     sa.Integer(), nullable=False, primary_key=True),
        sa.Column('session_id',             sa.Integer(), nullable=False),
        sa.Column('recorded_at',            sa.DateTime(timezone=True), nullable=False),
        sa.Column('ptosis_alerted',         sa.Boolean(), nullable=True),
        sa.Column('ptosis_detected_frames', sa.Integer(), nullable=True),
        sa.Column('total_monitored_frames', sa.Integer(), nullable=True),
        sa.Column('ptosis_fraction',        sa.Float(),   nullable=True),
        sa.Column('mean_left_ratio',        sa.Float(),   nullable=True),
        sa.Column('mean_right_ratio',       sa.Float(),   nullable=True),
        sa.Column('base_left',              sa.Float(),   nullable=True),
        sa.Column('base_right',             sa.Float(),   nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['monitoring_sessions.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_ptosis_results_id',         'ptosis_results', ['id'])
    op.create_index('ix_ptosis_results_session_id', 'ptosis_results', ['session_id'])

    # ── reports ────────────────────────────────────────────────────
    op.create_table(
        'reports',
        sa.Column('id',            sa.Integer(),    nullable=False, primary_key=True),
        sa.Column('session_id',    sa.Integer(),    nullable=False, unique=True),
        sa.Column('user_id',       sa.Integer(),    nullable=False),
        sa.Column('created_at',    sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('file_path',     sa.String(500),  nullable=True),
        sa.Column('report_format', sa.String(10),   nullable=False, server_default='pdf'),
        sa.ForeignKeyConstraint(['session_id'], ['monitoring_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'],    ['users.id'],               ondelete='CASCADE'),
    )
    op.create_index('ix_reports_id',      'reports', ['id'])
    op.create_index('ix_reports_user_id', 'reports', ['user_id'])


def downgrade() -> None:
    op.drop_table('reports')
    op.drop_table('ptosis_results')
    op.drop_table('asymmetry_results')
    op.drop_table('blink_results')
    op.drop_table('tremor_results')
    op.drop_table('monitoring_sessions')
    op.drop_table('users')
    sa.Enum(name='session_status_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='assessment_type_enum').drop(op.get_bind(), checkfirst=True)

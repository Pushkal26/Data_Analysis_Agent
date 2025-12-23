"""Initial schema with sessions, files, messages, and analysis

Revision ID: 0001
Revises: 
Create Date: 2024-12-18

This migration creates the initial database schema:
- sessions: Track user sessions
- uploaded_files: Store file metadata
- chat_messages: Store conversation history
- analysis_results: Store LangGraph analysis results
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ----- Sessions Table -----
    op.create_table(
        'sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_sessions'),
        sa.UniqueConstraint('session_id', name='uq_sessions_session_id'),
    )
    op.create_index('ix_sessions_session_id', 'sessions', ['session_id'])
    
    # ----- Uploaded Files Table -----
    op.create_table(
        'uploaded_files',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('filepath', sa.Text(), nullable=False),
        sa.Column('file_type', sa.String(10), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), default=0),
        sa.Column('time_period', sa.String(50), nullable=True),
        sa.Column('time_period_type', sa.String(20), nullable=True),
        sa.Column('row_count', sa.Integer(), default=0),
        sa.Column('column_count', sa.Integer(), default=0),
        sa.Column('columns', sa.JSON(), nullable=False),
        sa.Column('numeric_columns', sa.JSON(), nullable=False),
        sa.Column('categorical_columns', sa.JSON(), nullable=False),
        sa.Column('date_columns', sa.JSON(), nullable=False),
        sa.Column('schema', sa.JSON(), nullable=False),
        sa.Column('sample_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_uploaded_files'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], name='fk_uploaded_files_session_id_sessions', ondelete='CASCADE'),
    )
    op.create_index('ix_uploaded_files_session_id', 'uploaded_files', ['session_id'])
    
    # ----- Analysis Results Table -----
    op.create_table(
        'analysis_results',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'running', 'completed', 'failed', name='analysisstatus'), nullable=False),
        sa.Column('user_query', sa.Text(), nullable=False),
        sa.Column('intent', sa.Enum('query', 'aggregate', 'compare', 'trend', 'forecast', 'anomaly', 'correlation', name='analysisintent'), nullable=True),
        sa.Column('operation_type', sa.Enum('single_table', 'cross_table', 'temporal', name='operationtype'), nullable=True),
        sa.Column('files_used', sa.JSON(), nullable=False),
        sa.Column('plan', sa.JSON(), nullable=True),
        sa.Column('generated_code', sa.Text(), nullable=True),
        sa.Column('code_valid', sa.Boolean(), default=False),
        sa.Column('result_data', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('execution_time_ms', sa.Float(), nullable=True),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('recommendations', sa.JSON(), nullable=False),
        sa.Column('node_history', sa.JSON(), nullable=False),
        sa.Column('langgraph_trace', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_analysis_results'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], name='fk_analysis_results_session_id_sessions', ondelete='CASCADE'),
    )
    op.create_index('ix_analysis_results_session_id', 'analysis_results', ['session_id'])
    
    # ----- Chat Messages Table -----
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('analysis_id', sa.Integer(), nullable=True),
        sa.Column('role', sa.Enum('user', 'assistant', 'system', name='messagerole'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_chat_messages'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], name='fk_chat_messages_session_id_sessions', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['analysis_id'], ['analysis_results.id'], name='fk_chat_messages_analysis_id_analysis_results', ondelete='SET NULL'),
    )
    op.create_index('ix_chat_messages_session_id', 'chat_messages', ['session_id'])
    op.create_index('ix_chat_messages_analysis_id', 'chat_messages', ['analysis_id'])


def downgrade() -> None:
    op.drop_table('chat_messages')
    op.drop_table('analysis_results')
    op.drop_table('uploaded_files')
    op.drop_table('sessions')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS messagerole')
    op.execute('DROP TYPE IF EXISTS analysisstatus')
    op.execute('DROP TYPE IF EXISTS analysisintent')
    op.execute('DROP TYPE IF EXISTS operationtype')


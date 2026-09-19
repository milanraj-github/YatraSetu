"""add user device tokens and notifications tables

Revision ID: c7d3f8e21a04
Revises: b578d2cd2d8e
Create Date: 2026-09-19 13:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c7d3f8e21a04'
down_revision: Union[str, Sequence[str], None] = 'b578d2cd2d8e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'user_device_tokens',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('fcm_token', sa.String(length=512), nullable=False),
        sa.Column(
            'platform',
            sa.Enum('ANDROID', 'IOS', 'WEB', name='device_platform_enum'),
            server_default='ANDROID',
            nullable=False,
        ),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_user_device_tokens_fcm_token'), 'user_device_tokens', ['fcm_token'], unique=True)
    op.create_index(op.f('ix_user_device_tokens_is_active'), 'user_device_tokens', ['is_active'], unique=False)
    op.create_index(op.f('ix_user_device_tokens_user_id'), 'user_device_tokens', ['user_id'], unique=False)

    op.create_table(
        'notifications',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('recipient_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column(
            'notification_type',
            sa.Enum(
                'BUS_NEARBY',
                'BUS_ARRIVED',
                'DELAY',
                'EMERGENCY',
                'ACCIDENT',
                'SOS',
                name='notification_type_enum',
            ),
            nullable=False,
        ),
        sa.Column(
            'channel',
            sa.Enum('PUSH', 'EMAIL', 'BOTH', name='notification_channel_enum'),
            server_default='PUSH',
            nullable=False,
        ),
        sa.Column(
            'status',
            sa.Enum('PENDING', 'SENT', 'FAILED', name='notification_status_enum'),
            server_default='PENDING',
            nullable=False,
        ),
        sa.Column('data_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['recipient_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_notifications_notification_type'), 'notifications', ['notification_type'], unique=False)
    op.create_index(op.f('ix_notifications_recipient_id'), 'notifications', ['recipient_id'], unique=False)
    op.create_index(op.f('ix_notifications_status'), 'notifications', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_notifications_status'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_recipient_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_notification_type'), table_name='notifications')
    op.drop_table('notifications')

    op.drop_index(op.f('ix_user_device_tokens_user_id'), table_name='user_device_tokens')
    op.drop_index(op.f('ix_user_device_tokens_is_active'), table_name='user_device_tokens')
    op.drop_index(op.f('ix_user_device_tokens_fcm_token'), table_name='user_device_tokens')
    op.drop_table('user_device_tokens')

    sa.Enum(name='notification_status_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='notification_channel_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='notification_type_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='device_platform_enum').drop(op.get_bind(), checkfirst=True)

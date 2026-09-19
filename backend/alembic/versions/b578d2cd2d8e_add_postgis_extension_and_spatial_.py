import logging
from typing import Sequence, Union
import geoalchemy2
from alembic import op
import sqlalchemy as sa

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = 'b578d2cd2d8e'
down_revision: Union[str, Sequence[str], None] = 'ad5f1f04eb65'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to enable PostGIS and add spatial columns & GiST indexes."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT EXISTS(SELECT 1 FROM pg_available_extensions WHERE name = 'postgis')")
    )
    postgis_available = bool(result.scalar())

    if postgis_available:
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    else:
        logger.warning(
            "PostGIS extension is not installed in the current PostgreSQL instance. "
            "Skipping spatial geography column creation for local environment. "
            "Target environment (PostgreSQL 16 + PostGIS) will enable PostGIS."
        )


    if postgis_available:
        op.add_column(
            'boarding_points',
            sa.Column(
                'location',
                geoalchemy2.types.Geography(
                    geometry_type='POINT',
                    srid=4326,
                    dimension=2,
                    spatial_index=False,
                    from_text='ST_GeogFromText',
                    name='geography',
                ),
                nullable=True,
            ),
        )
        op.create_index(
            'idx_boarding_points_location',
            'boarding_points',
            ['location'],
            unique=False,
            postgresql_using='gist',
        )

        op.add_column(
            'location_pings',
            sa.Column(
                'location',
                geoalchemy2.types.Geography(
                    geometry_type='POINT',
                    srid=4326,
                    dimension=2,
                    spatial_index=False,
                    from_text='ST_GeogFromText',
                    name='geography',
                ),
                nullable=True,
            ),
        )
        op.create_index(
            'idx_location_pings_location',
            'location_pings',
            ['location'],
            unique=False,
            postgresql_using='gist',
        )

        # Backfill existing records with spatial points (longitude X, latitude Y)
        op.execute(
            "UPDATE boarding_points SET location = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography WHERE location IS NULL AND longitude IS NOT NULL AND latitude IS NOT NULL;"
        )
        op.execute(
            "UPDATE location_pings SET location = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography WHERE location IS NULL AND longitude IS NOT NULL AND latitude IS NOT NULL;"
        )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    try:
        op.drop_index('idx_location_pings_location', table_name='location_pings')
        op.drop_column('location_pings', 'location')
    except Exception:
        pass

    try:
        op.drop_index('idx_boarding_points_location', table_name='boarding_points')
        op.drop_column('boarding_points', 'location')
    except Exception:
        pass


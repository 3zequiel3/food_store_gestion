#!/usr/bin/env python3
"""
Bootstrap Alembic version table if missing, then run migrations.

This handles the case where the DB was created via create_all()
before Alembic was set up. In that scenario, alembic_version is
empty or doesn't exist, so we stamp it to the last known-good
migration before running upgrade head.
"""

import os
from sqlalchemy import create_engine, text


def bootstrap_alembic() -> None:
    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.connect() as conn:
        try:
            r = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            row = r.fetchone()
            if not row:
                conn.execute(
                    text(
                        "INSERT INTO alembic_version (version_num) VALUES ('move_es_removible_to_ingredients')"
                    )
                )
                conn.commit()
                print("Stamped DB to move_es_removible_to_ingredients")
            else:
                print(f"alembic_version already set: {row[0]}")
        except Exception as e:
            if "alembic_version" in str(e):
                conn.execute(
                    text(
                        "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"
                    )
                )
                conn.execute(
                    text(
                        "INSERT INTO alembic_version (version_num) VALUES ('move_es_removible_to_ingredients')"
                    )
                )
                conn.commit()
                print("Created alembic_version table and stamped")
            else:
                raise


if __name__ == "__main__":
    bootstrap_alembic()

"""Administrative command-line tools (`python -m app.cli.<command>`).

They read the database location from DATABASE_URL or the POSTGRES_* variables,
like the API and Alembic, and never run as part of container startup.
"""

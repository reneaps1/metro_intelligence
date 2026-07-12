"""DB access, one module per aggregate root. Repositories are the only
layer that imports SQLAlchemy Session/queries -- services/ and engines/
never touch the database directly."""

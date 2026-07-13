"""HTTP layer: versioned routers only. Routers validate input via schemas/,
delegate to services/, and never touch models/ or the DB session directly."""

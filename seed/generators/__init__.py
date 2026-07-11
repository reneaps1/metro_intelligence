from seed.generators.base import (
    GeneratorFn,
    SeedContext,
    make_rng,
    register_generator,
    registered_generators,
)

# Importing concrete generator modules runs their @register_generator
# decorators as a side effect — this is what actually populates the CLI's
# run order. Add each new F3.x generator module's import here, in the order
# it must run (measurements depends on catalog's artifacts; events depends on
# measurements' scenario/timestamp artifacts; decisions depends on users' and
# measurements' artifacts). This already caused a real bug in F3.2 — forget
# the import and @register_generator silently never runs.
from seed.generators import catalog  # noqa: E402,F401
from seed.generators import measurements  # noqa: E402,F401
from seed.generators import users  # noqa: E402,F401
from seed.generators import events  # noqa: E402,F401
from seed.generators import decisions  # noqa: E402,F401

__all__ = [
    "GeneratorFn",
    "SeedContext",
    "make_rng",
    "register_generator",
    "registered_generators",
]

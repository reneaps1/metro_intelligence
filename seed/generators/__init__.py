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
# it must run (measurements depends on catalog's artifacts).
from seed.generators import catalog  # noqa: E402,F401
from seed.generators import measurements  # noqa: E402,F401

__all__ = [
    "GeneratorFn",
    "SeedContext",
    "make_rng",
    "register_generator",
    "registered_generators",
]

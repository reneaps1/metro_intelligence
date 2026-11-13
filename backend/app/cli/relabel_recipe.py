"""Name the product variant a recipe produces, without reloading data.

    python -m app.cli.relabel_recipe --config ingest.yaml --recipe 2 \
        --variant-part <variant part number> [--variant-name "<name>"] [--label "<label>"]

The variant part number is created under the line product's family when it
does not exist. The change is recorded in the audit log.
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cli._line import add_config_argument, config_from_args
from app.models import Area, Line, Organization, PartNumber, Recipe, Site
from app.services.audit_service import write_audit_log

AUDIT_ACTION = "recipe_relabeled"
AUDIT_ACTOR = "cli:relabel_recipe"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_config_argument(parser)
    parser.add_argument("--recipe", type=int, required=True, help="Recipe (type-check program) number.")
    parser.add_argument("--variant-part", required=True, help="Variant part number code.")
    parser.add_argument("--variant-name", help="Variant part number name (when it is created).")
    parser.add_argument("--label", help="Label shown in the views (default: the variant code).")
    args = parser.parse_args(argv)
    config = config_from_args(parser, args)

    from app.core.database import engine

    with Session(engine) as session:
        recipe = session.execute(
            select(Recipe)
            .join(Line, Line.id == Recipe.line_id)
            .join(Area, Area.id == Line.area_id)
            .join(Site, Site.id == Area.site_id)
            .join(Organization, Organization.id == Site.organization_id)
            .where(
                Organization.code == config.organization.code,
                Line.code == config.line.code,
                Recipe.code == args.recipe,
            )
        ).scalar_one_or_none()
        if recipe is None:
            print(f"Recipe {args.recipe} is not loaded for line {config.line.code}.", file=sys.stderr)
            return 1
        product = session.get(PartNumber, recipe.part_number_id)
        assert product is not None
        variant = session.execute(
            select(PartNumber).where(PartNumber.code == args.variant_part)
        ).scalar_one_or_none()
        if variant is None:
            variant = PartNumber(
                product_family_id=product.product_family_id,
                code=args.variant_part,
                name=args.variant_name or args.variant_part,
            )
            session.add(variant)
            session.flush()
        before = {
            "variant_part_number_id": recipe.variant_part_number_id,
            "variant_label": recipe.variant_label,
        }
        recipe.variant_part_number_id = variant.id
        recipe.variant_label = args.label or args.variant_part
        write_audit_log(
            session,
            action=AUDIT_ACTION,
            entity_type="recipe",
            entity_id=recipe.id,
            actor_identifier=AUDIT_ACTOR,
            before_state={k: None if v is None else str(v) for k, v in before.items()},
            after_state={"variant_part_number_id": str(variant.id), "variant_label": recipe.variant_label},
        )
        session.commit()
    print(f"Recipe {args.recipe} now shows as {recipe.variant_label!r}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

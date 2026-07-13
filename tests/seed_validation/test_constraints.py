"""F3.5 (MI-20): schema/constraint sanity over the *full* generated demo
dataset (catalog + measurements + users + process events + decision
history run together, as `python -m seed` really runs them) -- as opposed
to seed/tests/, which validates each generator mostly in isolation.

Needs a disposable PostgreSQL database (METRO_TEST_DATABASE_URL); skipped
otherwise. See conftest.py's `seeded_engine` fixture for how the dataset is
built once and shared across this module and test_statistics.py.
"""
from __future__ import annotations

import sqlalchemy as sa

from .conftest import requires_database


@requires_database
def test_every_characteristic_has_a_unique_balloon_within_its_part(seeded_engine) -> None:
    engine, _context = seeded_engine
    with engine.begin() as connection:
        duplicates = connection.execute(
            sa.text(
                """
                SELECT part_number_id, balloon_number, count(*)
                FROM catalog_characteristics
                GROUP BY part_number_id, balloon_number
                HAVING count(*) > 1
                """
            )
        ).all()
        assert duplicates == []


@requires_database
def test_every_characteristic_has_exactly_one_active_specification(seeded_engine) -> None:
    engine, _context = seeded_engine
    with engine.begin() as connection:
        characteristic_count = connection.execute(sa.text("SELECT count(*) FROM catalog_characteristics")).scalar_one()
        active_spec_count = connection.execute(
            sa.text("SELECT count(DISTINCT characteristic_id) FROM catalog_specifications WHERE valid_to IS NULL")
        ).scalar_one()
        assert active_spec_count == characteristic_count

        no_active_spec = connection.execute(
            sa.text(
                """
                SELECT count(*) FROM catalog_characteristics c
                WHERE NOT EXISTS (
                    SELECT 1 FROM catalog_specifications s
                    WHERE s.characteristic_id = c.id AND s.valid_to IS NULL
                )
                """
            )
        ).scalar_one()
        assert no_active_spec == 0


@requires_database
def test_every_part_has_exactly_one_active_measurement_program(seeded_engine) -> None:
    engine, _context = seeded_engine
    with engine.begin() as connection:
        part_count = connection.execute(sa.text("SELECT count(*) FROM catalog_part_numbers")).scalar_one()
        active_program_count = connection.execute(
            sa.text(
                "SELECT count(DISTINCT part_number_id) FROM catalog_measurement_programs WHERE valid_to IS NULL"
            )
        ).scalar_one()
        assert active_program_count == part_count


@requires_database
def test_measurement_program_output_mapping_covers_every_characteristic_balloon(seeded_engine) -> None:
    """F3.5 acceptance criterion: sample files' COL_<balloon> columns must
    line up with MeasurementProgram.output_mapping, so this asserts the
    mapping itself is complete -- every characteristic's balloon number is a
    key in its part's active program's output_mapping."""
    engine, _context = seeded_engine
    with engine.begin() as connection:
        rows = connection.execute(
            sa.text(
                """
                SELECT p.output_mapping, array_agg(c.balloon_number)
                FROM catalog_measurement_programs p
                JOIN catalog_characteristics c ON c.part_number_id = p.part_number_id
                WHERE p.valid_to IS NULL
                GROUP BY p.id, p.output_mapping
                """
            )
        ).all()
        assert rows, "expected at least one active measurement program"
        for output_mapping, balloon_numbers in rows:
            missing = set(balloon_numbers) - set(output_mapping.keys())
            assert not missing, f"output_mapping missing balloons {missing}"
            for balloon, column in output_mapping.items():
                assert column == f"COL_{balloon}", f"unexpected column naming: {balloon} -> {column}"


@requires_database
def test_measurement_results_reference_valid_specifications(seeded_engine) -> None:
    engine, context = seeded_engine
    with engine.begin() as connection:
        assert (
            connection.execute(sa.text("SELECT count(*) FROM measurement_results")).scalar_one()
            == context.artifacts["measurement_result_count"]
        )

        orphans = connection.execute(
            sa.text(
                """
                SELECT count(*) FROM measurement_results r
                LEFT JOIN catalog_specifications s ON s.id = r.specification_id
                LEFT JOIN catalog_characteristics c ON c.id = r.characteristic_id
                LEFT JOIN measurement_samples m ON m.id = r.measurement_sample_id
                WHERE s.id IS NULL OR c.id IS NULL OR m.id IS NULL
                """
            )
        ).scalar_one()
        assert orphans == 0


@requires_database
def test_demo_users_cover_every_rbac_role_on_the_fictitious_domain(seeded_engine) -> None:
    engine, _context = seeded_engine
    with engine.begin() as connection:
        role_counts = connection.execute(
            sa.text(
                """
                SELECT r.name, count(*) FROM security_users u
                JOIN security_user_roles ur ON ur.user_id = u.id
                JOIN security_roles r ON r.id = ur.role_id
                GROUP BY r.name
                """
            )
        ).all()
        assert {name: count for name, count in role_counts} == {
            "viewer": 1,
            "metrologist": 1,
            "quality_engineer": 1,
            "admin": 1,
            "auditor": 1,
        }

        emails = connection.execute(sa.text("SELECT email FROM security_users")).scalars().all()
        assert all(email.endswith("@demo.local") for email in emails)


@requires_database
def test_process_events_reference_valid_machines_and_lines(seeded_engine) -> None:
    engine, _context = seeded_engine
    with engine.begin() as connection:
        event_count = connection.execute(sa.text("SELECT count(*) FROM context_process_events")).scalar_one()
        assert 15 <= event_count <= 25

        orphans = connection.execute(
            sa.text(
                """
                SELECT count(*) FROM context_process_events e
                LEFT JOIN org_machines m ON m.id = e.machine_id
                LEFT JOIN org_lines l ON l.id = e.line_id
                WHERE (e.machine_id IS NOT NULL AND m.id IS NULL)
                   OR (e.line_id IS NOT NULL AND l.id IS NULL)
                """
            )
        ).scalar_one()
        assert orphans == 0


@requires_database
def test_no_accepted_or_rejected_recommendation_lacks_a_matching_decision(seeded_engine) -> None:
    """The migration 0004 state-machine trigger should make this
    impossible via a direct UPDATE, but this re-asserts it holds for
    everything the generators actually produced end to end."""
    engine, _context = seeded_engine
    with engine.begin() as connection:
        state_counts = connection.execute(
            sa.text("SELECT state, count(*) FROM intelligence_recommendations GROUP BY state")
        ).all()
        states = {state: count for state, count in state_counts}
        assert 8 <= sum(states.values()) <= 12
        assert states.get("pending", 0) >= 1
        assert states.get("accepted", 0) >= 1
        assert states.get("rejected", 0) >= 1

        orphans = connection.execute(
            sa.text(
                """
                SELECT count(*) FROM intelligence_recommendations r
                WHERE r.state IN ('accepted', 'rejected')
                  AND NOT EXISTS (
                      SELECT 1 FROM intelligence_decisions d
                      WHERE d.recommendation_id = r.id AND d.action = r.state
                  )
                """
            )
        ).scalar_one()
        assert orphans == 0


@requires_database
def test_accepted_recommendations_have_an_action_taken_row(seeded_engine) -> None:
    engine, _context = seeded_engine
    with engine.begin() as connection:
        missing_action = connection.execute(
            sa.text(
                """
                SELECT count(*) FROM intelligence_recommendations r
                JOIN intelligence_decisions d ON d.recommendation_id = r.id AND d.action = 'accepted'
                LEFT JOIN intelligence_action_taken a ON a.decision_id = d.id
                WHERE r.state = 'accepted' AND a.id IS NULL
                """
            )
        ).scalar_one()
        assert missing_action == 0

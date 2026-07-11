"""F3.4 (MI-19): recommendation -> decision -> action-taken history so the
Decision Memory screens aren't empty in the demo. These are historical/
synthetic records, not the output of a real engine (F7-F10 build those) —
engine_name is tagged "seed-historical" precisely so nobody mistakes a seed
row for live engine output. Every insert respects migration 0004's state
machine (backend/alembic/versions/0004_context_intelligence.py): a
Decision row must already exist before the UPDATE that flips a
Recommendation's state to accepted/rejected."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models import ActionTaken, Characteristic, Decision, Recommendation, User

from seed.generators.base import SeedContext, register_generator

ENGINE_NAME = "seed-historical"
ENGINE_VERSION = "0"

# (scenario this recommendation is narratively tied to, recommendation_type,
# outcome). outcome drives what Decision/ActionTaken rows (if any) follow.
RECOMMENDATION_PLAN = [
    ("stable_capable", "frequency_decrease", "accepted_effective"),
    ("stable_capable", "frequency_decrease", "accepted_pending"),
    ("slow_drift", "investigate_cause", "accepted_effective"),
    ("slow_drift", "immediate_inspection", "rejected"),
    ("shift_after_event", "post_event_validation", "accepted_effective"),
    ("shift_after_event", "post_event_validation", "pending"),
    ("high_variance", "frequency_increase", "accepted_ineffective"),
    ("high_variance", "immediate_inspection", "rejected"),
    ("outlier_nok", "immediate_inspection", "rejected"),
    ("outlier_nok", "investigate_cause", "pending"),
]

RATIONALE_BY_TYPE = {
    "frequency_decrease": "Cpk sostenido por encima de 1.67 en los últimos 90 días; candidato a reducir frecuencia de inspección.",
    "frequency_increase": "Varianza elevada cerca de los límites de tolerancia (Cpk < 1.0); se recomienda aumentar la frecuencia.",
    "immediate_inspection": "Desviación fuera de tolerancia detectada; se recomienda inspección inmediata.",
    "investigate_cause": "Tendencia de deriva sostenida hacia el límite de tolerancia; se recomienda investigar la causa raíz.",
    "post_event_validation": "Cambio de media detectado tras un evento de proceso; se recomienda validar el efecto del evento.",
}

REJECTION_REASONS = [
    "Evaluado por ingeniería de calidad: variación dentro de lo esperado para este proceso, no se justifica la acción.",
    "Causa ya conocida y cubierta por una acción correctiva previa; no se requiere una nueva.",
]

ACTION_OUTCOME_BY_TAG = {
    "accepted_effective": "effective",
    "accepted_ineffective": "ineffective",
    "accepted_pending": "pending",
}


@register_generator
def generate_decision_history(context: SeedContext) -> None:
    session = context.session
    rng = context.rng

    characteristics: list[Characteristic] = context.artifacts["characteristics"]
    scenario_by_characteristic_id: dict = context.artifacts["scenario_by_characteristic_id"]
    users_by_role: dict[str, User] = context.artifacts["users_by_role"]
    deciding_user = users_by_role["quality_engineer"]

    chars_by_scenario: dict[str, list[Characteristic]] = {}
    for characteristic in characteristics:
        scenario = scenario_by_characteristic_id.get(characteristic.id)
        chars_by_scenario.setdefault(scenario, []).append(characteristic)

    now = datetime.now(timezone.utc)
    recommendation_count = 0

    for index, (scenario_name, recommendation_type, outcome) in enumerate(RECOMMENDATION_PLAN):
        pool = chars_by_scenario.get(scenario_name, [])
        if not pool:
            continue
        characteristic = pool[int(rng.integers(0, len(pool)))]

        created_at = now - timedelta(days=int(rng.integers(3, 30)))
        recommendation = Recommendation(
            characteristic_id=characteristic.id,
            recommendation_type=recommendation_type,
            rationale=RATIONALE_BY_TYPE[recommendation_type],
            evidence={"scenario": scenario_name, "seed_index": index},
            engine_name=ENGINE_NAME,
            engine_version=ENGINE_VERSION,
            created_at=created_at,
            updated_at=created_at,
        )
        session.add(recommendation)
        session.flush()  # id needed before a Decision can reference it
        recommendation_count += 1

        if outcome == "pending":
            continue

        decided_at = created_at + timedelta(days=int(rng.integers(1, 3)))
        action = "accepted" if outcome.startswith("accepted") else "rejected"
        comment = (
            "Aprobado tras revisión de ingeniería de calidad."
            if action == "accepted"
            else REJECTION_REASONS[index % len(REJECTION_REASONS)]
        )

        decision = Decision(
            recommendation_id=recommendation.id,
            decided_by_user_id=deciding_user.id,
            action=action,
            comment=comment,
            decided_at=decided_at,
        )
        session.add(decision)
        session.flush()  # the Decision row must exist before the state UPDATE below

        recommendation.state = action
        recommendation.updated_at = decided_at
        session.flush()  # fires trg_intelligence_recommendations_state_transition

        if action == "accepted":
            action_status = ACTION_OUTCOME_BY_TAG[outcome]
            session.add(
                ActionTaken(
                    decision_id=decision.id,
                    description=f"Acción derivada de la recomendación: {RATIONALE_BY_TYPE[recommendation_type]}",
                    outcome_status=action_status,
                    observed_at=decided_at + timedelta(days=7) if action_status != "pending" else None,
                )
            )

    session.flush()
    context.artifacts["recommendation_count"] = recommendation_count

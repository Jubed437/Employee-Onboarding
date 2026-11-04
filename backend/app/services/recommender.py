import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.db.base import Recommendation, Risk, TaskInstance, new_id
from app.domain.enums import ReasonCode, RecommendationStatus
from app.domain.schemas import PlaybooksConfig, PoliciesConfig
from app.services.impact import ImpactResult
from app.services.playbooks import (
    matching_playbooks,
    rank_matches,
    simulate_playbook,
)


def recommend_for_risk(
    session: Session,
    risk: Risk,
    root_cause: TaskInstance,
    impact: ImpactResult,
    *,
    playbooks: PlaybooksConfig,
    policies: PoliciesConfig,
    clock: Clock,
) -> list[Recommendation]:
    current_slack = risk.slack_days
    matches = matching_playbooks(
        playbooks.playbooks,
        root_cause,
        (ReasonCode(code) for code in risk.reason_codes),
        impact.outcome_tags,
    )
    ranked = rank_matches(
        simulate_playbook(playbook, root_cause, current_slack) for playbook in matches
    )[: policies.max_recommendations_per_risk]
    created: list[Recommendation] = []
    now = clock.now()
    for rank, match in enumerate(ranked, start=1):
        key = _idempotency_key(risk.id, match.playbook.id, match.params)
        existing = session.scalar(
            select(Recommendation).where(Recommendation.idempotency_key == key)
        )
        if existing is not None:
            created.append(existing)
            continue
        recommendation = Recommendation(
            id=new_id(),
            risk_id=risk.id,
            playbook_id=match.playbook.id,
            action_type=match.playbook.action_type,
            tier=match.playbook.tier,
            params=match.params,
            simulated_outcome={
                "resolves_breach": match.resolves_breach,
                "new_slack_days": match.new_slack_days,
            },
            rank=rank,
            rationale=_rationale(match.playbook.id, match.new_slack_days),
            status=RecommendationStatus.PROPOSED,
            idempotency_key=key,
            created_at=now,
        )
        session.add(recommendation)
        created.append(recommendation)
    session.commit()
    return created


def supersede_for_resolved_risk(session: Session, risk_id: str) -> None:
    recommendations = session.scalars(
        select(Recommendation).where(
            Recommendation.risk_id == risk_id,
            Recommendation.status == RecommendationStatus.PROPOSED,
        )
    ).all()
    for recommendation in recommendations:
        recommendation.status = RecommendationStatus.SUPERSEDED
    session.commit()


def _idempotency_key(risk_id: str, playbook_id: str, params: dict[str, object]) -> str:
    payload = json.dumps(params, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(f"{risk_id}{playbook_id}{payload}".encode()).hexdigest()


def _rationale(playbook_id: str, new_slack_days: float) -> str:
    return f"{playbook_id} is projected to produce {new_slack_days:g} days of slack."

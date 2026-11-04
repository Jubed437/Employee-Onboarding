from collections.abc import Iterable
from dataclasses import dataclass

from app.db.base import TaskInstance
from app.domain.enums import ReasonCode, Role, Tier
from app.domain.schemas import PlaybookConfig


@dataclass(frozen=True)
class PlaybookMatch:
    playbook: PlaybookConfig
    params: dict[str, object]
    new_slack_days: float
    resolves_breach: bool
    disruption: float


def matching_playbooks(
    playbooks: Iterable[PlaybookConfig],
    root_cause: TaskInstance,
    reason_codes: Iterable[ReasonCode],
    outcome_tags: Iterable[str],
) -> list[PlaybookConfig]:
    reasons = set(reason_codes)
    tags = set(outcome_tags)
    matches: list[PlaybookConfig] = []
    for playbook in playbooks:
        conditions = playbook.applies_when
        if conditions.owner_role and root_cause.owner_role not in conditions.owner_role:
            continue
        if conditions.task_states and root_cause.state not in conditions.task_states:
            continue
        if conditions.outcome_tags and not set(conditions.outcome_tags).intersection(tags):
            continue
        if playbook.id == "PB-FOLLOWUP" and root_cause.owner_role not in {
            Role.PAYROLL,
            Role.HR,
        }:
            continue
        if playbook.id == "PB-REASSIGN" and ReasonCode.OWNER_OVERLOAD not in reasons:
            continue
        if playbook.id == "PB-EXPEDITE" and root_cause.external_sla_days is None:
            continue
        if playbook.id == "PB-EXPRESS" and root_cause.template_key != "IT-01":
            continue
        if playbook.id == "PB-SHIFT-JOIN" and ReasonCode.CRITICAL_GATE not in reasons:
            continue
        matches.append(playbook)
    return matches


def simulate_playbook(
    playbook: PlaybookConfig,
    root_cause: TaskInstance,
    current_slack_days: float,
) -> PlaybookMatch:
    effect = playbook.effect
    params: dict[str, object] = {}
    new_slack = current_slack_days
    disruption = 0.0
    if effect.reduce_remaining_days is not None:
        params["reduce_remaining_days"] = effect.reduce_remaining_days
        new_slack += effect.reduce_remaining_days
        disruption = effect.reduce_remaining_days
    if effect.extend_due_days is not None:
        params["extend_due_days"] = effect.extend_due_days
        new_slack += effect.extend_due_days
        disruption = effect.extend_due_days
    if effect.change_owner is not None:
        params["change_owner"] = effect.change_owner.value
        disruption = 1.0
    if effect.halve_external_sla:
        params["halve_external_sla"] = True
        new_slack += (root_cause.external_sla_days or 0) / 2
        disruption = 1.0
    if effect.shift_join_date_days is not None:
        params["shift_join_date_days"] = effect.shift_join_date_days
        new_slack += effect.shift_join_date_days
        disruption = abs(effect.shift_join_date_days)
    if effect.target_task is not None:
        params["target_task"] = effect.target_task
    return PlaybookMatch(
        playbook=playbook,
        params=params,
        new_slack_days=new_slack,
        resolves_breach=new_slack >= 0,
        disruption=disruption,
    )


def rank_matches(matches: Iterable[PlaybookMatch]) -> list[PlaybookMatch]:
    return sorted(
        matches,
        key=lambda match: (
            not match.resolves_breach,
            _tier_rank(match.playbook.tier),
            match.disruption,
            match.playbook.id,
        ),
    )


def _tier_rank(tier: Tier) -> int:
    return {
        Tier.AUTO: 0,
        Tier.MANAGER_APPROVAL: 1,
        Tier.MANAGER_AND_HR_APPROVAL: 2,
    }[tier]

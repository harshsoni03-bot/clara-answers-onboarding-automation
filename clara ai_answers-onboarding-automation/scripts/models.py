from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Any


@dataclass
class AccountMemo:
    """
    Python representation of the Account Memo.

    This mirrors `schemas/account_memo.schema.json` and enforces the
    "no hallucination" rule by requiring explicit population of fields.
    """

    account_id: str
    company_name: str
    business_hours: Optional[str] = None
    office_address: Optional[str] = None
    services_supported: List[str] = field(default_factory=list)
    emergency_definition: Optional[str] = None
    emergency_routing_rules: Optional[str] = None
    non_emergency_routing_rules: Optional[str] = None
    call_transfer_rules: Optional[str] = None
    integration_constraints: List[str] = field(default_factory=list)
    after_hours_flow_summary: Optional[str] = None
    office_hours_flow_summary: Optional[str] = None
    questions_or_unknowns: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccountMemo":
        return cls(**data)

    def register_unknown_if_empty(self, field_name: str, reason: str) -> None:
        """
        If the named field is empty / falsy, register a question in
        `questions_or_unknowns` without fabricating any value.
        """
        value = getattr(self, field_name, None)
        if not value:
            self.questions_or_unknowns.append(f"{field_name}: {reason}")


@dataclass
class AgentSpec:
    """
    Minimal abstract Retell agent configuration for this project.
    """

    agent_name: str
    voice_style: str
    version: str
    timezone: str
    business_hours: Optional[str]
    system_prompt: str
    call_transfer_protocol: str
    fallback_protocol: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentSpec":
        return cls(**data)



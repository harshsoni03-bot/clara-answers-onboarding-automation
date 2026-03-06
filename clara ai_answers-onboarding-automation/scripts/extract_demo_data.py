from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from io_utils import iter_transcripts, load_text_file, save_json, memo_path
from models import AccountMemo
from text_parsers import (
    extract_company_name,
    extract_business_hours,
    extract_office_address,
    extract_services,
    extract_emergency_definition,
    extract_routing_rules,
    extract_call_transfer_rules,
    extract_integration_constraints,
    extract_after_and_office_flows,
    extract_timezone,
)
from generate_agent import build_agent_spec
from io_utils import agent_spec_path


def aggregate_demo_transcripts() -> Dict[str, List[str]]:
    """
    Read all demo call transcripts and aggregate their raw text per account.
    """
    aggregated: Dict[str, List[str]] = defaultdict(list)
    for account_id, path in iter_transcripts("demo_calls"):
        text = load_text_file(path)
        aggregated[account_id].append(text)
    return aggregated


def build_memo_from_demo(account_id: str, texts: List[str]) -> AccountMemo:
    """
    Build an AccountMemo from a list of demo call transcripts.

    This function enforces the "no hallucination" requirement:
    - Fields are only filled when there is explicit evidence.
    - Missing fields add entries to questions_or_unknowns.
    """
    combined = "\n\n".join(texts)

    company_name = extract_company_name(combined) or account_id
    business_hours = extract_business_hours(combined)
    office_address = extract_office_address(combined)
    services_supported = extract_services(combined)
    emergency_definition = extract_emergency_definition(combined)
    emergency_routing_rules, non_emergency_routing_rules = extract_routing_rules(combined)
    call_transfer_rules = extract_call_transfer_rules(combined)
    integration_constraints = extract_integration_constraints(combined)
    after_hours_flow_summary, office_hours_flow_summary = extract_after_and_office_flows(combined)

    memo = AccountMemo(
        account_id=account_id,
        company_name=company_name,
        business_hours=business_hours,
        office_address=office_address,
        services_supported=services_supported,
        emergency_definition=emergency_definition,
        emergency_routing_rules=emergency_routing_rules,
        non_emergency_routing_rules=non_emergency_routing_rules,
        call_transfer_rules=call_transfer_rules,
        integration_constraints=integration_constraints,
        after_hours_flow_summary=after_hours_flow_summary,
        office_hours_flow_summary=office_hours_flow_summary,
    )

    # Register unknowns for anything we could not extract.
    memo.register_unknown_if_empty("business_hours", "Business hours not clearly stated in demo calls.")
    memo.register_unknown_if_empty("office_address", "Office address not clearly stated in demo calls.")
    memo.register_unknown_if_empty("emergency_definition", "Emergency definition not clearly stated in demo calls.")
    memo.register_unknown_if_empty(
        "emergency_routing_rules", "Emergency routing not clearly described in demo calls."
    )
    memo.register_unknown_if_empty(
        "non_emergency_routing_rules", "Non-emergency routing not clearly described in demo calls."
    )
    memo.register_unknown_if_empty("call_transfer_rules", "Call transfer rules not clearly described in demo calls.")
    memo.register_unknown_if_empty(
        "after_hours_flow_summary", "After-hours flow not clearly summarized in demo calls."
    )
    memo.register_unknown_if_empty(
        "office_hours_flow_summary", "Office-hours flow not clearly summarized in demo calls."
    )

    if not memo.services_supported:
        memo.questions_or_unknowns.append(
            "services_supported: Services were not clearly enumerated in demo calls."
        )

    if not memo.integration_constraints:
        memo.notes.append(
            "No explicit integration constraints were mentioned in demo calls; "
            "verify integrations during onboarding."
        )

    return memo


def run_pipeline() -> None:
    aggregated = aggregate_demo_transcripts()
    if not aggregated:
        print("[extract_demo_data] No demo call transcripts found under dataset/demo_calls.")
        return

    for account_id, texts in aggregated.items():
        print(f"[extract_demo_data] Processing account '{account_id}' with {len(texts)} demo calls.")
        memo = build_memo_from_demo(account_id, texts)

        # Save v1 memo
        memo_file = memo_path(account_id, "v1")
        save_json(memo_file, memo.to_dict())
        print(f"[extract_demo_data] Wrote v1 memo: {memo_file}")

        # Use demo transcripts to extract timezone if possible
        combined_text = "\n\n".join(texts)
        tz = extract_timezone(combined_text)

        # Build and save v1 agent spec
        spec = build_agent_spec(memo, version="v1", timezone=tz)
        spec_file = agent_spec_path(account_id, "v1")
        save_json(spec_file, spec.to_dict())
        print(f"[extract_demo_data] Wrote v1 agent spec: {spec_file}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pipeline A: Extract account memos and v1 agent specs from demo call transcripts."
    )
    parser.parse_args()  # For future options; currently no CLI flags.
    run_pipeline()


if __name__ == "__main__":
    main()


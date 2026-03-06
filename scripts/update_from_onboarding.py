from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any

from io_utils import (
    iter_transcripts,
    load_text_file,
    load_json,
    save_json,
    memo_path,
    agent_spec_path,
    changelog_path,
)
from models import AccountMemo
from text_parsers import (
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
from diff_generator import generate_diff_summary


def aggregate_onboarding_transcripts() -> Dict[str, List[str]]:
    aggregated: Dict[str, List[str]] = defaultdict(list)
    for account_id, path in iter_transcripts("onboarding_calls"):
        text = load_text_file(path)
        aggregated[account_id].append(text)
    return aggregated


def apply_onboarding_updates(memo: AccountMemo, texts: List[str]) -> AccountMemo:
    """
    Use onboarding transcripts to refine and extend the memo.

    Rules:
    - Only overwrite fields when new, explicit information is present.
    - Append to lists instead of replacing where appropriate.
    - Do NOT clear previously known information unless onboarding
      explicitly contradicts it (this implementation is conservative and
      only overwrites when we find clearly better, non-empty values).
    """
    combined = "\n\n".join(texts)

    # Potential updated fields
    new_business_hours = extract_business_hours(combined)
    new_office_address = extract_office_address(combined)
    new_services = extract_services(combined)
    new_emergency_definition = extract_emergency_definition(combined)
    new_em_routing, new_non_em_routing = extract_routing_rules(combined)
    new_transfer_rules = extract_call_transfer_rules(combined)
    new_integrations = extract_integration_constraints(combined)
    new_after_flow, new_office_flow = extract_after_and_office_flows(combined)

    # Overwrite scalar fields when new info is present
    if new_business_hours:
        memo.business_hours = new_business_hours
    if new_office_address:
        memo.office_address = new_office_address
    if new_emergency_definition:
        memo.emergency_definition = new_emergency_definition
    if new_em_routing:
        memo.emergency_routing_rules = new_em_routing
    if new_non_em_routing:
        memo.non_emergency_routing_rules = new_non_em_routing
    if new_transfer_rules:
        memo.call_transfer_rules = new_transfer_rules
    if new_after_flow:
        memo.after_hours_flow_summary = new_after_flow
    if new_office_flow:
        memo.office_hours_flow_summary = new_office_flow

    # Merge lists without duplication
    for s in new_services:
        if s not in memo.services_supported:
            memo.services_supported.append(s)

    for c in new_integrations:
        if c not in memo.integration_constraints:
            memo.integration_constraints.append(c)

    # Re-register unknowns for any fields still missing after onboarding.
    memo.questions_or_unknowns.clear()
    memo.register_unknown_if_empty("business_hours", "Business hours not clearly stated after onboarding.")
    memo.register_unknown_if_empty("office_address", "Office address not clearly stated after onboarding.")
    memo.register_unknown_if_empty("emergency_definition", "Emergency definition not clearly stated after onboarding.")
    memo.register_unknown_if_empty(
        "emergency_routing_rules", "Emergency routing not clearly described after onboarding."
    )
    memo.register_unknown_if_empty(
        "non_emergency_routing_rules", "Non-emergency routing not clearly described after onboarding."
    )
    memo.register_unknown_if_empty(
        "call_transfer_rules", "Call transfer rules not clearly described after onboarding."
    )
    memo.register_unknown_if_empty(
        "after_hours_flow_summary", "After-hours flow not clearly summarized after onboarding."
    )
    memo.register_unknown_if_empty(
        "office_hours_flow_summary", "Office-hours flow not clearly summarized after onboarding."
    )

    if not memo.services_supported:
        memo.questions_or_unknowns.append(
            "services_supported: Services were not clearly enumerated even after onboarding."
        )

    if not memo.integration_constraints:
        memo.notes.append(
            "No explicit integration constraints were mentioned even after onboarding; "
            "confirm this before deploying integrations."
        )

    return memo


def run_pipeline() -> None:
    aggregated = aggregate_onboarding_transcripts()
    if not aggregated:
        print("[update_from_onboarding] No onboarding transcripts found under dataset/onboarding_calls.")
        return

    for account_id, texts in aggregated.items():
        print(f"[update_from_onboarding] Processing account '{account_id}' with {len(texts)} onboarding calls.")
        v1_path = memo_path(account_id, "v1")
        if not v1_path.exists():
            print(f"[update_from_onboarding] Skipping account '{account_id}' (no v1 memo found at {v1_path}).")
            continue

        v1_dict: Dict[str, Any] = load_json(v1_path)
        v1_memo = AccountMemo.from_dict(v1_dict)

        v2_memo = apply_onboarding_updates(v1_memo, texts)

        # Save v2 memo
        v2_path = memo_path(account_id, "v2")
        save_json(v2_path, v2_memo.to_dict())
        print(f"[update_from_onboarding] Wrote v2 memo: {v2_path}")

        # Build and save v2 agent spec
        combined_text = "\n\n".join(texts)
        tz = extract_timezone(combined_text)
        v2_spec = build_agent_spec(v2_memo, version="v2", timezone=tz)
        v2_spec_path = agent_spec_path(account_id, "v2")
        save_json(v2_spec_path, v2_spec.to_dict())
        print(f"[update_from_onboarding] Wrote v2 agent spec: {v2_spec_path}")

        # Generate changelog v1 -> v2
        changelog_file = changelog_path(account_id)
        summary = generate_diff_summary(v1_dict, v2_memo.to_dict())
        changelog_contents = (
            "v1 → v2 changes\n\n"
            + "\n".join(f"- {line}" for line in summary)
            if summary
            else "No observable changes between v1 and v2 memos."
        )
        changelog_file.parent.mkdir(parents=True, exist_ok=True)
        changelog_file.write_text(changelog_contents, encoding="utf-8")
        print(f"[update_from_onboarding] Wrote changelog: {changelog_file}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pipeline B: Update account memos and agent specs from onboarding transcripts, and generate changelogs."
    )
    parser.parse_args()
    run_pipeline()


if __name__ == "__main__":
    main()


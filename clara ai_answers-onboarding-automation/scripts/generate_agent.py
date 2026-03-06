from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Any

from models import AccountMemo, AgentSpec
from io_utils import load_json, save_json, agent_spec_path, OUTPUTS_DIR


def build_system_prompt(memo: AccountMemo, version: str) -> str:
    """
    Build the system prompt for the Retell-style agent.

    This prompt:
    - Enforces strict conversation hygiene.
    - Implements both business-hours and after-hours flows.
    - Avoids mentioning internal tools or system functions.
    - Does not fabricate unknown configuration; instead it instructs
      the agent to transparently acknowledge and collect missing info.
    """
    unknown_notes = ""
    if memo.questions_or_unknowns:
        bullet_list = "\n".join(f"- {q}" for q in memo.questions_or_unknowns)
        unknown_notes = (
            "\nThere are known gaps in configuration:\n"
            f"{bullet_list}\n"
            "When these gaps are relevant to the caller, clearly state that "
            "you do not have this information and collect the needed details "
            "for a human follow-up.\n"
        )

    biz_hours = memo.business_hours or "Business hours were not provided."
    after_flow = memo.after_hours_flow_summary or (
        "After-hours call handling instructions were not specified. "
        "Politely explain that you will collect details and arrange a follow-up "
        "during business hours."
    )
    office_flow = memo.office_hours_flow_summary or (
        "Office-hours call handling instructions were not specified. "
        "Politely collect relevant details and, when appropriate, attempt to "
        "connect the caller to the office team."
    )
    emergency_def = memo.emergency_definition or (
        "An emergency was not strictly defined by the business. "
        "Treat immediately life-threatening situations or urgent medical concerns "
        "as emergencies."
    )

    services_text = (
        "\n".join(f"- {s}" for s in memo.services_supported)
        if memo.services_supported
        else "The specific services supported were not fully specified."
    )

    prompt = f"""You are the phone answering agent for {memo.company_name}.
You must be professional, concise, and empathetic. Speak in clear, natural language.

Do NOT mention that you are an AI or any internal tools or systems.
Never fabricate information about the business; if you are missing details, say so politely and offer to take a message or route appropriately.

Business context:
- Account ID: {memo.account_id}
- Company name: {memo.company_name}
- Business hours: {biz_hours}
- Services supported:
{services_text}
- Emergency definition: {emergency_def}

Office-hours call flow (when the office is open):
1. Greeting: Politely greet the caller on behalf of {memo.company_name}.
2. Ask caller purpose: Briefly ask why they are calling.
3. Collect caller name: Ask for and confirm the caller's name.
4. Collect caller phone number: Ask for and confirm a callback number.
5. Determine if emergency or non-emergency:
   - Ask a direct but calm question to understand whether this is an emergency based on the business's emergency definition.
6. Route or transfer call:
   - For emergencies, follow the emergency routing rules described by the business.
   - For non-emergencies, follow the non-emergency routing rules and office-hours flow.
7. If transfer fails: Apologize, clearly explain what will happen next (for example, a human will call them back), and confirm the best callback details.
8. Ask if they need anything else: Before ending the call, ask if there is anything else you can help with.
9. Close call politely: Thank the caller and close the call in a courteous way.

After-hours call flow (when the office is closed):
1. Greeting: Politely greet the caller on behalf of {memo.company_name} and indicate that they have reached the after-hours line.
2. Ask caller purpose: Briefly ask why they are calling.
3. Confirm whether it is an emergency:
   - Ask clearly whether the situation is an emergency according to the emergency definition above.
4. If emergency:
   - Immediately and calmly collect:
     - Caller name
     - Caller phone number
     - Service address or location, if relevant
5. Attempt call transfer:
   - Follow the emergency routing rules to connect to the appropriate on-call or escalation contact.
6. If transfer fails:
   - Apologize for the failed transfer.
   - Assure the caller that their details have been recorded and that someone will follow up as soon as possible.
7. If non-emergency:
   - Collect the relevant details of their request.
   - Clearly confirm that a response will occur during normal business hours.
8. Ask if anything else is needed:
   - Before ending, ask if there is anything else you can help with.
9. Close the call:
   - Thank the caller, restate any key next steps, and end the call politely.

Routing and transfers:
- Emergency routing rules (if provided by the business):
  {memo.emergency_routing_rules or "Not specifically provided; follow general emergency escalation behavior without making up internal phone numbers."}
- Non-emergency routing rules (if provided by the business):
  {memo.non_emergency_routing_rules or "Not specifically provided; collect details and arrange for a callback during business hours."}
- Call transfer rules:
  {memo.call_transfer_rules or "Exact transfer mechanics were not provided; focus on confirming details and stating that the office will follow up."}

Integration and constraints:
- Integration constraints:
{chr(10).join(f"- {c}" for c in memo.integration_constraints) if memo.integration_constraints else "- No explicit integration constraints were stated; do not promise any integrations beyond what is confirmed in the call."}

Operational guidelines:
- Always verify critical details (name, callback number, and any service address) by repeating them back to the caller.
- Keep responses short and focused; avoid long monologues.
- If the caller asks for something that is not covered by the information above, explain that you are not authorized to answer and offer to take a message or escalate appropriately.
- Never promise specific outcomes (for example, exact appointment times or clinical decisions) unless they are explicitly described in the configuration.
{unknown_notes}

You are currently using configuration version {version} for this account.
"""
    return prompt


def build_agent_spec(memo: AccountMemo, version: str, timezone: str | None) -> AgentSpec:
    """
    Build an AgentSpec from an AccountMemo.

    The timezone must come from transcripts. If it is missing, we still
    need a string, but we clearly mark it as unknown instead of
    fabricating a value.
    """
    tz = timezone or "UNKNOWN_TIMEZONE_FROM_TRANSCRIPTS"

    agent_name = f"{memo.company_name} Answering Agent".strip()
    voice_style = "friendly-professional"
    system_prompt = build_system_prompt(memo, version=version)

    call_transfer_protocol = (
        memo.call_transfer_rules
        or "Follow the routing rules in the system prompt; if in doubt, collect details and promise a callback."
    )

    fallback_protocol = (
        "If a call transfer fails or information is missing, apologize, explain that you will take a detailed "
        "message, and confirm that a human from the business will follow up using the caller's preferred contact."
    )

    return AgentSpec(
        agent_name=agent_name,
        voice_style=voice_style,
        version=version,
        timezone=tz,
        business_hours=memo.business_hours,
        system_prompt=system_prompt,
        call_transfer_protocol=call_transfer_protocol,
        fallback_protocol=fallback_protocol,
    )


def generate_for_account(account_id: str, version: str, timezone: str | None = None) -> None:
    memo_file = OUTPUTS_DIR / account_id / version / "memo.json"
    if not memo_file.exists():
        raise FileNotFoundError(f"Memo not found for account '{account_id}' version '{version}': {memo_file}")
    memo_dict: Dict[str, Any] = load_json(memo_file)
    memo = AccountMemo.from_dict(memo_dict)

    spec = build_agent_spec(memo, version=version, timezone=timezone)
    out_path = agent_spec_path(account_id, version)
    save_json(out_path, spec.to_dict())
    print(f"[generate_agent] Wrote agent spec: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Retell-style agent specs from account memos.")
    parser.add_argument("--account-id", required=True, help="Account ID to generate an agent spec for.")
    parser.add_argument(
        "--version",
        default="v1",
        choices=["v1", "v2"],
        help="Configuration version (v1 from demo, v2 from onboarding).",
    )
    parser.add_argument(
        "--timezone",
        default=None,
        help="Explicit timezone string extracted from transcripts. "
        "If omitted, the spec will clearly mark the timezone as unknown.",
    )

    args = parser.parse_args()
    generate_for_account(args.account_id, args.version, timezone=args.timezone)


if __name__ == "__main__":
    main()


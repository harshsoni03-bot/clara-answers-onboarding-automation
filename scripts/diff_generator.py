from __future__ import annotations

from typing import Dict, Any, List


def generate_diff_summary(v1: Dict[str, Any], v2: Dict[str, Any]) -> List[str]:
    """
    Generate a human-readable summary of changes between two memo dicts.

    The output is a list of change descriptions suitable for a markdown changelog.
    """
    changes: List[str] = []

    def changed(field: str, label: str) -> None:
        if v1.get(field) != v2.get(field):
            changes.append(label)

    changed("business_hours", "Business hours updated")
    changed("office_address", "Office address updated")
    changed("emergency_definition", "Emergency definition updated")
    changed("emergency_routing_rules", "Emergency routing changed")
    changed("non_emergency_routing_rules", "Non-emergency routing changed")
    changed("call_transfer_rules", "Call transfer rules changed")
    changed("after_hours_flow_summary", "After-hours flow summary updated")
    changed("office_hours_flow_summary", "Office-hours flow summary updated")

    # List changes
    if v1.get("services_supported") != v2.get("services_supported"):
        changes.append("Services supported list updated")
    if v1.get("integration_constraints") != v2.get("integration_constraints"):
        changes.append("New integration constraint(s) added or updated")

    # Unknowns / questions shrinking or growing is also useful
    if v1.get("questions_or_unknowns") != v2.get("questions_or_unknowns"):
        changes.append("Open questions / unknowns updated")

    if not changes:
        changes.append("No material configuration changes detected.")

    return changes


if __name__ == "__main__":
    # Minimal manual test harness (not used by the pipeline directly).
    sample_v1 = {"business_hours": None}
    sample_v2 = {"business_hours": "Mon-Fri 9am-5pm"}
    for line in generate_diff_summary(sample_v1, sample_v2):
        print(line)


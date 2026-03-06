from __future__ import annotations

import re
from typing import List, Optional, Tuple


COMPANY_PATTERNS = [
    re.compile(r"\b(?:this is|you're speaking with|welcome to)\s+([A-Z][\w\s&]+?)(?:[,\.]|$)", re.IGNORECASE),
    re.compile(r"\bcompany\s*[:\-]\s*([A-Z][\w\s&]+)", re.IGNORECASE),
]

BUSINESS_HOURS_PATTERNS = [
    re.compile(
        r"\b(?:business|office)\s+hours?\s*(?:are|:)\s*(.+?)(?:\.|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bfrom\s+\d{1,2}\s*(?:am|pm)\s+to\s+\d{1,2}\s*(?:am|pm)\s+on\s+[A-Za-z,\s]+",
        re.IGNORECASE,
    ),
]

ADDRESS_PATTERNS = [
    re.compile(r"\baddress\s*(?:is|:)\s*(.+)", re.IGNORECASE),
]

EMERGENCY_DEF_PATTERNS = [
    re.compile(r"\bwe consider (.+?) an emergency", re.IGNORECASE),
    re.compile(r"\bemergency\s+means\s+(.+?)(?:\.|$)", re.IGNORECASE),
]

TIMEZONE_PATTERNS = [
    re.compile(r"\btime\s*zone\s*(?:is|:)\s*([A-Za-z_\/]+)", re.IGNORECASE),
    re.compile(r"\b([A-Z]{2,4})\s+time\b", re.IGNORECASE),
]


def _first_group(patterns: List[re.Pattern], text: str) -> Optional[str]:
    for pat in patterns:
        m = pat.search(text)
        if m:
            group = m.group(1).strip()
            if group:
                return group
    return None


def extract_company_name(text: str) -> Optional[str]:
    return _first_group(COMPANY_PATTERNS, text)


def extract_business_hours(text: str) -> Optional[str]:
    return _first_group(BUSINESS_HOURS_PATTERNS, text)


def extract_office_address(text: str) -> Optional[str]:
    return _first_group(ADDRESS_PATTERNS, text)


def extract_services(text: str) -> List[str]:
    """
    Very conservative service extraction: look for 'we handle', 'we offer', 'services include'.
    Returns a list of raw fragments found.
    """
    services: List[str] = []
    patterns = [
        re.compile(r"\bwe (?:handle|support|take|answer)\s+([^\.]+)", re.IGNORECASE),
        re.compile(r"\bservices\s+include\s*([^\.]+)", re.IGNORECASE),
        re.compile(r"\bwe offer\s+([^\.]+)", re.IGNORECASE),
    ]
    for pat in patterns:
        for m in pat.finditer(text):
            frag = m.group(1).strip()
            if frag and frag not in services:
                services.append(frag)
    return services


def extract_emergency_definition(text: str) -> Optional[str]:
    return _first_group(EMERGENCY_DEF_PATTERNS, text)


def extract_routing_rules(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Heuristically extract emergency and non-emergency routing descriptions.
    """
    emergency = None
    non_emergency = None

    # Emergency routing
    em_pat = re.compile(
        r"\bfor emergencies?,?\s*(?:we|you)\s+(?:should\s+)?(transfer.+|call.+|page.+|route.+)",
        re.IGNORECASE,
    )
    m = em_pat.search(text)
    if m:
        emergency = m.group(0).strip()

    # Non-emergency routing
    non_pat = re.compile(
        r"\bfor (?:non-?emergencies|routine calls),?\s*(?:we|you)\s+(?:should\s+)?(transfer.+|take.+|send.+|route.+)",
        re.IGNORECASE,
    )
    m2 = non_pat.search(text)
    if m2:
        non_emergency = m2.group(0).strip()

    return emergency, non_emergency


def extract_call_transfer_rules(text: str) -> Optional[str]:
    pat = re.compile(
        r"\btransfer\s+calls?\s*(?:to|through)\s*([^\.]+)",
        re.IGNORECASE,
    )
    m = pat.search(text)
    if m:
        return m.group(0).strip()
    return None


def extract_integration_constraints(text: str) -> List[str]:
    """
    Find rough mentions of EHR/CRM/PM or 'integration' constraints.
    """
    constraints: List[str] = []
    pat = re.compile(
        r"\b(?:EHR|EMR|CRM|integrat\w+|practice management|scheduling system)[^\.]*",
        re.IGNORECASE,
    )
    for m in pat.finditer(text):
        frag = m.group(0).strip()
        if frag and frag not in constraints:
            constraints.append(frag)
    return constraints


def extract_after_and_office_flows(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Attempt to pull concise descriptions of after-hours vs office-hours handling.
    Very conservative: looks for 'after hours' and 'during business hours'.
    """
    after = None
    office = None

    after_pat = re.compile(r"\bafter hours?\b[^\.]*\.", re.IGNORECASE)
    office_pat = re.compile(r"\b(?:during|in) (?:business|office) hours?\b[^\.]*\.", re.IGNORECASE)

    m_after = after_pat.search(text)
    if m_after:
        after = m_after.group(0).strip()

    m_office = office_pat.search(text)
    if m_office:
        office = m_office.group(0).strip()

    return after, office


def extract_timezone(text: str) -> Optional[str]:
    return _first_group(TIMEZONE_PATTERNS, text)



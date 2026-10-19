"""
Triage Agent for HelpDesk AI.
Classifies tickets into categories (Network, Hardware, Software, Access, Security, Other),
evaluates priority (Low, Medium, High, Critical), and provides deterministic safety enforcement.
"""

from typing import Dict, Any, Tuple
import re
from llm_client import call_llm

VALID_CATEGORIES = ["Network", "Hardware", "Software", "Access", "Security", "Other"]
VALID_PRIORITIES = ["Low", "Medium", "High", "Critical"]

# Security trigger patterns that mandate immediate Security categorization and urgent escalation
SECURITY_TRIGGER_PATTERNS = [
    (r"\b(phish|phishing|spear[\s-]phishing)\b", "Suspected phishing attempt"),
    (r"\b(credential(s)?\s*(stolen|exposure|leak|compromised|entered))\b", "Exposed or compromised credentials"),
    (r"\b(entered\s+(my\s+)?(corporate\s+)?password\s+on)\b", "Password entered on suspicious site"),
    (r"\b(fake\s+(login|portal|page|microsoft|sso))\b", "Credential harvesting portal"),
    (r"\b(malware|ransomware|trojan|keylogger|virus|infected|worm|rootkit)\b", "Malware or ransomware indicator"),
    (r"\b(security\s*breach|unauthorized\s*(access|login|activity)|account\s*takeover)\b", "Potential unauthorized access or security breach"),
    (r"\b(malicious\s*(link|attachment|file|payload|executable|domain))\b", "Malicious link or attachment"),
    (r"\b(encrypted\s+all\s+(my\s+)?files|ransom\s*note)\b", "Active ransomware encryption event")
]


def check_security_triggers(text: str) -> Tuple[bool, str]:
    """
    Deterministically evaluates whether the incident text matches critical security indicators.
    Returns (is_security, trigger_reason).
    """
    text_lower = text.lower()
    for pattern, reason in SECURITY_TRIGGER_PATTERNS:
        if re.search(pattern, text_lower):
            return True, reason
    return False, ""


def calculate_itil_priority(impact: str, urgency: str, is_security: bool = False) -> str:
    """
    Standard ITIL Priority Matrix calculation based on impact and urgency.
    
    Security Rule:
    - Business-critical service OR Work blocked -> Critical
    - Any other security incident -> High
    - Security incidents are NEVER allowed to be downgraded to Medium or Low.

    Standard ITIL Matrix:
    - Business-critical service + Work blocked -> Critical
    - Business-critical service + Work impaired -> High
    - Business-critical service + Minor inconvenience -> Medium
    - Multiple users + Work blocked -> High
    - Multiple users + Work impaired -> Medium
    - Multiple users + Minor inconvenience -> Low
    - One user + Work blocked -> High
    - One user + Work impaired -> Medium
    - One user + Minor inconvenience -> Low
    """
    if is_security:
        if impact == "Business-critical service" or urgency == "Work blocked":
            return "Critical"
        return "High"

    # Explicit ITIL Matrix
    if impact == "Business-critical service":
        if urgency == "Work blocked":
            return "Critical"
        elif urgency == "Work impaired":
            return "High"
        else:
            return "Medium"
    elif impact == "Multiple users":
        if urgency == "Work blocked":
            return "High"
        elif urgency == "Work impaired":
            return "Medium"
        else:
            return "Low"
    else:  # One user
        if urgency == "Work blocked":
            return "High"
        elif urgency == "Work impaired":
            return "Medium"
        else:
            return "Low"


def deterministic_category_classifier(title: str, description: str) -> Tuple[str, str]:
    """
    Deterministic rule-based classification using curated IT domain heuristics.
    Returns (category, rationale).
    """
    text = f"{title} {description}".lower()

    # 1. Deterministic Security check (highest priority)
    is_sec, sec_reason = check_security_triggers(text)
    if is_sec:
        return "Security", f"Deterministic safety rule triggered: {sec_reason}."

    # 2. Network domain
    if any(k in text for k in ["vpn", "tunnel", "anyconnect", "dns", "gateway", "wifi", "wi-fi", "dhcp", "subnet", "router", "network connection", "offline"]):
        return "Network", "Identified network connectivity, VPN tunnel, or routing keywords."

    # 3. Access domain
    if any(k in text for k in ["password", "lockout", "locked", "sso", "mfa", "login", "active directory", "permission", "access denied", "shared drive", "rbac", "security group"]):
        return "Access", "Identified authentication, identity provider, or access permission keywords."

    # 4. Hardware domain
    if any(k in text for k in ["overheating", "fan", "thermal", "chassis", "hot", "battery", "monitor", "dock", "docking", "display", "screen", "keyboard", "hardware"]):
        return "Hardware", "Identified physical workstation, thermal, dock, or peripheral hardware keywords."

    # 5. Software domain
    if any(k in text for k in ["outlook", "email", "teams", "excel", "app", "application", "crash", "freeze", "freezing", "cache", "bug", "software", "compiler", "script"]):
        return "Software", "Identified desktop application crash, synchronization, or software cache keywords."

    return "Other", "Incident context does not match predefined IT domain categories."


def rule_based_triage_fallback(title: str, description: str, impact: str, urgency: str) -> Dict[str, Any]:
    """
    Deterministic rule-based triage fallback engine.
    Ensures 100% reproducible category and ITIL priority evaluation.
    """
    category, cat_rationale = deterministic_category_classifier(title, description)
    is_security = (category == "Security")
    priority = calculate_itil_priority(impact, urgency, is_security=is_security)

    reasoning = (
        f"{cat_rationale} Priority assigned as '{priority}' according to ITIL Impact ({impact}) x "
        f"Urgency ({urgency}) guidelines."
    )
    if is_security:
        reasoning += " Mandatory safety protocol: Security incidents receive elevated priority and SecOps review."

    return {
        "category": category,
        "priority": priority,
        "reasoning": reasoning,
        "source": "deterministic_rules"
    }


def run_triage_agent(title: str, description: str, impact: str, urgency: str) -> Dict[str, Any]:
    """
    Runs the Triage Agent using Ollama llama3.2:1b with deterministic safety enforcement.
    Security incidents and ITIL priority rules are strictly enforced regardless of LLM output.
    """
    full_text = f"{title} {description}"
    is_mandatory_sec, sec_trigger_reason = check_security_triggers(full_text)

    prompt = f"""You are an expert IT Service Desk Triage Agent. Analyze this IT incident ticket:
Incident Title: {title}
Description: {description}
Reported Impact: {impact}
Reported Urgency: {urgency}

Classify into exactly ONE Category:
- Network
- Hardware
- Software
- Access
- Security
- Other

Assign Priority strictly based on ITIL guidelines:
- Critical: Business-critical service outage OR severe security compromise / blocked work.
- High: Single or multiple users with 'Work blocked' OR any Security incident.
- Medium: 'Work impaired' (partial service degradation).
- Low: 'Minor inconvenience' (work continues normally).

Respond ONLY with a valid JSON object matching this schema:
{{
  "category": "Network | Hardware | Software | Access | Security | Other",
  "priority": "Low | Medium | High | Critical",
  "reasoning": "Concise 1-2 sentence explanation of your classification and ITIL matrix rationale."
}}"""

    system_prompt = "You are a professional ITIL Service Desk Triage Agent. Output strictly JSON."

    llm_result = call_llm(prompt=prompt, system_prompt=system_prompt, json_mode=True)

    if llm_result.get("success") and llm_result.get("parsed_json"):
        data = llm_result["parsed_json"]
        category = str(data.get("category", "")).strip().capitalize()
        priority = str(data.get("priority", "")).strip().capitalize()
        reasoning = str(data.get("reasoning", "")).strip()

        # Sanitize against valid options
        if category not in VALID_CATEGORIES:
            category, _ = deterministic_category_classifier(title, description)

        # 1. Deterministic Security Enforcement
        # If text contains security triggers, category MUST be Security
        if is_mandatory_sec:
            category = "Security"
            reasoning = f"Security rule enforced ({sec_trigger_reason}). " + reasoning

        # 2. Deterministic ITIL Priority Enforcement
        # The LLM is never allowed to assign priority conflicting with ITIL policy or downgrade security
        is_sec = (category == "Security")
        expected_priority = calculate_itil_priority(impact, urgency, is_security=is_sec)
        
        # Enforce exact ITIL priority
        if priority != expected_priority:
            priority = expected_priority

        if not reasoning:
            reasoning = f"Ticket categorized under {category} with {priority} priority based on ITIL guidelines."

        return {
            "category": category,
            "priority": priority,
            "reasoning": reasoning,
            "source": llm_result.get("source", "nvidia"),
            "model": llm_result.get("model", "")
        }

    # Fallback to deterministic engine
    return rule_based_triage_fallback(title, description, impact, urgency)

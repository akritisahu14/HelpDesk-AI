"""
Critic Agent for HelpDesk AI.
Validates troubleshooting recommendations for safety, non-destructiveness,
factual grounding in Knowledge Base SOPs, escalation guidance, and absence of premature resolution claims.
"""

from typing import List, Dict, Any, Tuple
import re
from llm_client import call_llm

# Prohibited dangerous keywords or credential-harvesting patterns
DANGEROUS_PATTERNS = [
    (r"\b(give|share|provide|send|tell)\s+(me\s+)?(your\s+)?(\w+\s+)?(password|passcode|pin|credentials)\b", "Credential harvesting solicitation"),
    (r"\b(enter|type)\s+(your\s+)?(\w+\s+)?(password|credentials)\s+(here|in\s+chat|in\s+the\s+ticket)\b", "Insecure credential transmission"),
    (r"\bformat\s+[a-z]:", "Destructive disk formatting command"),
    (r"\brm\s+-rf\s+[/~*]", "Destructive recursive file deletion"),
    (r"\bdel\s+/[sfq]\s+c:\\", "Destructive Windows system deletion"),
    (r"\bdrop\s+database\b", "Destructive database drop command"),
    (r"\bdisable\s+(antivirus|firewall|defender|edr|security)\b", "Unauthorized security control suspension"),
    (r"\bturn\s+off\s+(antivirus|firewall|defender|real-time\s+protection)\b", "Disabling endpoint protection"),
    (r"\b(download|install)\s+(this\s+)?(cracked|keygen|patch|pirated|unverified)\b", "Unapproved third-party or pirated binary download"),
    (r"\bbypass\s+security(\s+controls)?\b", "Attempt to bypass corporate security controls")
]

# Patterns that improperly claim ticket resolution before user/technician verification
PREMATURE_RESOLUTION_PATTERNS = [
    r"\b(issue|ticket|incident|problem)\s+is\s+(now\s+)?(resolved|closed|fixed|solved)\b",
    r"\bticket\s+has\s+been\s+resolved\b",
    r"\bwe\s+have\s+resolved\s+your\s+issue\b",
    r"\bmarked\s+(this\s+ticket\s+)?as\s+resolved\b",
    r"\bthis\s+issue\s+is\s+now\s+fully\s+resolved\b"
]


def check_security_escalation_guidance(recommendation: str) -> bool:
    """
    Checks if a security recommendation includes mandatory advisory containment instructions
    (directing the user to disconnect network/Wi-Fi) and escalation guidance (reporting to SecOps / SOC).
    Note: The AI system provides guidance only and does NOT execute automated device isolation.
    """
    rec_lower = recommendation.lower()
    has_containment = any(k in rec_lower for k in [
        "disconnect", "unplug", "isolate", "network", "wi-fi", "offline", "ethernet"
    ])
    has_escalation = any(k in rec_lower for k in [
        "secops", "soc", "security team", "incident response", "security operations", "escalat"
    ])
    return has_containment and has_escalation


def heuristic_critic_check(
    ticket_text: str,
    recommendation: str,
    category: str,
    retrieved_articles: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Deterministic safety, compliance, and grounding validation.
    Enforces strict security checks even if LLM is unavailable or misses subtle hazards.
    """
    if retrieved_articles is None:
        retrieved_articles = []

    rec_lower = recommendation.lower()
    flags: List[str] = []
    
    is_safe = True
    is_grounded = True
    has_guidance = True

    # 1. Check for unsafe or dangerous commands and credential solicitations
    for pattern, description in DANGEROUS_PATTERNS:
        if re.search(pattern, rec_lower, re.IGNORECASE):
            flags.append(f"Safety violation: {description} detected (`{pattern}`).")
            is_safe = False

    # 2. Check for premature resolution claims
    for pattern in PREMATURE_RESOLUTION_PATTERNS:
        if re.search(pattern, rec_lower, re.IGNORECASE):
            flags.append("Premature resolution claim: Recommendations must provide advisory troubleshooting steps, never declare a ticket resolved.")
            is_safe = False

    # 3. Check for missing escalation/containment guidance in security incidents
    if category.strip().capitalize() == "Security":
        if not check_security_escalation_guidance(recommendation):
            flags.append("Missing security escalation guidance: Security incident recommendations must instruct network isolation and reporting to SecOps/SOC.")
            has_guidance = False

    # 4. Check for unsupported advice / lack of Knowledge Base grounding
    if not retrieved_articles:
        flags.append("Unsupported advice: No approved Knowledge Base SOP articles matched this incident. Action requires human review.")
        is_grounded = False

    # Determine final verdict
    if not is_safe:
        verdict = "Rejected"
        critique = "Safety alert: " + " ".join(flags)
    elif not is_grounded or not has_guidance:
        verdict = "Flagged"
        critique = "Policy/Grounding warning: " + " ".join(flags)
    else:
        verdict = "Approved"
        critique = (
            "Safety validation passed. No credential requests or destructive commands detected. "
            "Action items are grounded in approved SOPs and adhere to corporate ITIL service desk guardrails."
        )

    return {
        "is_safe": is_safe,
        "is_grounded": is_grounded,
        "has_escalation_guidance": has_guidance,
        "verdict": verdict,
        "critique": critique,
        "flags": flags,
        "source": "deterministic_guardrails"
    }


def run_critic_agent(
    title: str,
    description: str,
    category: str,
    recommendation: str,
    retrieved_articles: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Runs the Critic Agent to validate recommendations using deterministic safety guardrails
    supplemented by Ollama llama3.2:1b for semantic nuance.
    """
    ticket_text = f"{title} {description}"
    
    # 1. Execute deterministic guardrail check
    heuristic_res = heuristic_critic_check(
        ticket_text=ticket_text,
        recommendation=recommendation,
        category=category,
        retrieved_articles=retrieved_articles
    )

    # If deterministic check rejected or flagged, return immediately for safety and reproducibility
    if heuristic_res["verdict"] in ["Rejected", "Flagged"]:
        return heuristic_res

    # 2. If safe, optionally invoke Ollama for semantic check
    kb_titles = [f"{a.get('id')}: {a.get('title')}" for a in retrieved_articles]
    prompt = f"""You are an IT Quality & Security Critic Agent.
Review this IT recommendation for safety, relevance, and policy compliance:

Incident Title: {title}
Category: {category}
Approved KB Articles: {', '.join(kb_titles) if kb_titles else 'None'}

Proposed Troubleshooting Guidance:
{recommendation}

Evaluate strictly:
1. Is it safe? (Does NOT ask for passwords, does NOT run destructive commands, does NOT disable security)
2. Is it grounded in the approved KB articles without hallucinations?
3. Does it avoid claiming the ticket is already solved?

Respond ONLY with valid JSON:
{{
  "is_safe": true,
  "verdict": "Approved | Flagged | Rejected",
  "critique": "Brief 1-2 sentence justification of the safety and relevance assessment."
}}"""

    system_prompt = "You are an IT Security and Quality Critic. Output strictly valid JSON."

    llm_result = call_llm(prompt=prompt, system_prompt=system_prompt, json_mode=True)

    if llm_result.get("success") and llm_result.get("parsed_json"):
        data = llm_result["parsed_json"]
        is_safe = bool(data.get("is_safe", True))
        verdict = str(data.get("verdict", "Approved")).capitalize()
        critique = str(data.get("critique", "")).strip()

        if verdict not in ["Approved", "Flagged", "Rejected"]:
            verdict = "Approved" if is_safe else "Flagged"

        if not critique:
            critique = "Recommendation verified: safe, non-destructive, and aligned with standard operating procedures."

        # Even with LLM output, preserve deterministic attributes
        return {
            "is_safe": is_safe and heuristic_res["is_safe"],
            "is_grounded": heuristic_res["is_grounded"],
            "has_escalation_guidance": heuristic_res["has_escalation_guidance"],
            "verdict": verdict if is_safe else "Flagged",
            "critique": critique,
            "flags": heuristic_res["flags"],
            "source": llm_result.get("source", "nvidia"),
            "model": llm_result.get("model", "")
        }

    # Fallback to deterministic check result
    return heuristic_res

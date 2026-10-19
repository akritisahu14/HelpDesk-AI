"""
LangGraph Multi-Agent Orchestrator for HelpDesk AI.
Coordinates Triage, Knowledge Retrieval, Resolution, Critic, and Escalation Routing.
"""

from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END

from agents.triage_agent import run_triage_agent, check_security_triggers
from agents.retrieval_agent import run_retrieval_agent
from agents.resolution_agent import run_resolution_agent
from agents.critic_agent import run_critic_agent


class IncidentTicketState(TypedDict):
    title: str
    description: str
    impact: str
    urgency: str
    
    # Triage Agent outputs
    category: Optional[str]
    priority: Optional[str]
    triage_reasoning: Optional[str]
    
    # Knowledge Retrieval outputs
    retrieved_articles: List[Dict[str, Any]]
    supported_article_ids: List[str]
    
    # Resolution Agent outputs
    recommendation: Optional[str]
    requires_onsite: Optional[bool]
    
    # Critic Agent outputs
    critic_verdict: Optional[str]
    critic_critique: Optional[str]
    critic_flags: List[str]
    is_safe: Optional[bool]
    is_grounded: Optional[bool]
    
    # Routing & Escalation outputs
    is_escalated: Optional[bool]
    escalation_tier: Optional[str]
    escalation_reason: Optional[str]
    status: Optional[str]
    
    # Feedback & Revision outputs
    revision_count: int
    critic_feedback: Optional[str]

    # Diagnostics & Tracing
    execution_logs: List[str]
    agent_sources: Dict[str, str]


# Maximum bounded feedback revisions from Critic to Resolution before escalating to human review
MAX_CRITIC_REVISIONS = 1


def triage_node(state: IncidentTicketState) -> Dict[str, Any]:
    """Node 1: Evaluates ticket title, description, impact, and urgency to assign category & priority."""
    logs = list(state.get("execution_logs", []))
    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [Triage Agent] Initiating ticket classification...")
    
    res = run_triage_agent(
        title=state["title"],
        description=state["description"],
        impact=state["impact"],
        urgency=state["urgency"]
    )
    
    sources = dict(state.get("agent_sources", {}))
    sources["triage"] = res.get("source", "unknown")
    
    logs.append(
        f"[{datetime.now().strftime('%H:%M:%S')}] [Triage Agent] Categorized as '{res['category']}' "
        f"with Priority '{res['priority']}'. Source: {sources['triage']}."
    )
    
    return {
        "category": res["category"],
        "priority": res["priority"],
        "triage_reasoning": res["reasoning"],
        "execution_logs": logs,
        "agent_sources": sources
    }


def retrieval_node(state: IncidentTicketState) -> Dict[str, Any]:
    """Node 2: Searches local IT knowledge base using token overlap and keyword weighting."""
    logs = list(state.get("execution_logs", []))
    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [Retrieval Tool] Querying local Knowledge Base for '{state.get('category')}'...")
    
    articles = run_retrieval_agent(
        title=state["title"],
        description=state["description"],
        category=state.get("category")
    )
    
    article_ids = [a["id"] for a in articles]
    article_titles = [f"{a['id']} ({a['title']})" for a in articles]
    
    if articles:
        logs.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] [Retrieval Tool] Retrieved {len(articles)} article(s): {', '.join(article_titles)}"
        )
    else:
        logs.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] [Retrieval Tool] No matching Knowledge Base articles found (Score below confidence threshold)."
        )
    
    return {
        "retrieved_articles": articles,
        "supported_article_ids": article_ids,
        "execution_logs": logs
    }


def resolution_node(state: IncidentTicketState) -> Dict[str, Any]:
    """Node 3: Synthesizes troubleshooting recommendations grounded in retrieved articles (supports revision feedback)."""
    logs = list(state.get("execution_logs", []))
    revisions = state.get("revision_count", 0)
    critic_feedback = state.get("critic_feedback")
    
    if critic_feedback and revisions > 0:
        logs.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] [Resolution Agent] Bounded feedback loop active: "
            f"Revising recommendation based on Critic feedback (Revision {revisions}/{MAX_CRITIC_REVISIONS})..."
        )
    else:
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [Resolution Agent] Generating troubleshooting steps from KB...")
    
    res = run_resolution_agent(
        title=state["title"],
        description=state["description"],
        category=state.get("category", "Other"),
        priority=state.get("priority", "Medium"),
        retrieved_articles=state.get("retrieved_articles", []),
        critic_feedback=critic_feedback
    )
    
    sources = dict(state.get("agent_sources", {}))
    sources["resolution"] = res.get("source", "unknown")
    
    logs.append(
        f"[{datetime.now().strftime('%H:%M:%S')}] [Resolution Agent] Formulated recommendations. Source: {sources['resolution']}."
    )
    
    return {
        "recommendation": res["recommendation"],
        "requires_onsite": res.get("requires_onsite", False),
        "supported_article_ids": res.get("supported_article_ids", []),
        "execution_logs": logs,
        "agent_sources": sources
    }


def critic_node(state: IncidentTicketState) -> Dict[str, Any]:
    """Node 4: Evaluates safety, non-destructiveness, and relevance of proposed troubleshooting steps."""
    logs = list(state.get("execution_logs", []))
    revisions = state.get("revision_count", 0)
    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [Critic Agent] Auditing recommendations for safety and adherence to policy...")
    
    critic_res = run_critic_agent(
        title=state["title"],
        description=state["description"],
        category=state.get("category", "Other"),
        recommendation=state.get("recommendation", ""),
        retrieved_articles=state.get("retrieved_articles", [])
    )
    
    sources = dict(state.get("agent_sources", {}))
    sources["critic"] = critic_res.get("source", "unknown")
    
    verdict = critic_res["verdict"]
    is_safe = critic_res["is_safe"]
    
    needs_revision = (verdict == "Rejected" or not is_safe)
    next_revision = (revisions + 1) if needs_revision else revisions
    critic_feedback = critic_res["critique"] if needs_revision else None
    
    logs.append(
        f"[{datetime.now().strftime('%H:%M:%S')}] [Critic Agent] Verdict: {verdict} "
        f"(Safe: {is_safe}, Grounded: {critic_res.get('is_grounded', True)}). "
        f"Critique: {critic_res['critique']}"
    )
    if needs_revision:
        if next_revision <= MAX_CRITIC_REVISIONS:
            logs.append(
                f"[{datetime.now().strftime('%H:%M:%S')}] [Critic Agent] Safety validation failed. "
                f"Triggering bounded feedback loop to Resolution Agent (Attempt {next_revision}/{MAX_CRITIC_REVISIONS})."
            )
        else:
            logs.append(
                f"[{datetime.now().strftime('%H:%M:%S')}] [Critic Agent] Safety validation failed. "
                f"Maximum revision attempts ({MAX_CRITIC_REVISIONS}) reached. Routing to Senior Human Review."
            )
    
    return {
        "critic_verdict": verdict,
        "critic_critique": critic_res["critique"],
        "critic_flags": critic_res.get("flags", []),
        "critic_feedback": critic_feedback,
        "is_safe": is_safe,
        "is_grounded": critic_res.get("is_grounded", True),
        "revision_count": next_revision,
        "execution_logs": logs,
        "agent_sources": sources
    }


def critic_condition(state: IncidentTicketState) -> str:
    """
    Evaluates bounded feedback loop routing:
    - If Critic validation fails (Rejected or unsafe) and revision quota remains -> loop back to 'resolution'
    - Otherwise -> proceed to 'router'
    """
    verdict = state.get("critic_verdict", "Approved")
    is_safe = state.get("is_safe", True)
    revisions = state.get("revision_count", 0)
    
    if (verdict == "Rejected" or not is_safe) and revisions <= MAX_CRITIC_REVISIONS:
        return "resolution"
    return "router"


def router_node(state: IncidentTicketState) -> Dict[str, Any]:
    """
    Node 5: Output Router evaluating escalation policy.
    - Security incidents -> Escalate urgently to SecOps Incident Response Team (Human Review Required)
    - Critical priority incidents -> Escalate urgently to Priority Incident Command
    - Critic Rejected / Unsafe -> Escalate to Senior Human Review (do not pass)
    - Insufficient KB evidence / Flagged -> Escalate to Tier 2 Support for custom review
    - Standard safe tickets -> Triaged with Advisory Guidance (never marked closed/resolved)
    """
    logs = list(state.get("execution_logs", []))
    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [Routing Agent] Assessing escalation criteria...")
    
    category = state.get("category", "Other")
    priority = state.get("priority", "Medium")
    critic_verdict = state.get("critic_verdict", "Approved")
    critic_flags = state.get("critic_flags", [])
    is_safe = state.get("is_safe", True)
    is_grounded = state.get("is_grounded", True)
    retrieved_articles = state.get("retrieved_articles", [])
    
    full_text = f"{state.get('title', '')} {state.get('description', '')}"
    is_sec_trigger, sec_reason = check_security_triggers(full_text)
    is_security_case = (category == "Security") or is_sec_trigger

    # 1. Mandatory Security Escalation to Human Review (Phishing, Credentials, Ransomware)
    if is_security_case:
        is_escalated = True
        escalation_tier = "SecOps Incident Response Team (Human Security Review Required)"
        escalation_reason = (
            "Mandatory security incident protocol: Suspected phishing, credential exposure, "
            "or malware requires urgent human SecOps analyst investigation and manual containment. "
            "The system provides advisory guidance only; automated device isolation is not performed."
        )
        status = "Escalated - Security Incident (Human Review Required)"
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [Routing Agent] Escalated to {escalation_tier}. Reason: {escalation_reason}")

    # 2. Critical Priority Incident Policy
    elif priority == "Critical":
        is_escalated = True
        escalation_tier = "Priority Incident Command (Tier 2/3)"
        escalation_reason = "Critical business outage: Service disruption warrants immediate senior engineering engagement."
        status = "Escalated - Priority Command"
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [Routing Agent] Escalated to {escalation_tier}. Reason: {escalation_reason}")

    # 3. Critic Safety Rejection Policy
    elif not is_safe or critic_verdict == "Rejected":
        is_escalated = True
        escalation_tier = "Senior Service Desk Analyst (Human Review Required)"
        flag_summary = " | ".join(critic_flags) if critic_flags else "Critic safety check rejected recommendation"
        escalation_reason = f"Safety guardrail violation: {flag_summary} (automated revision attempts exhausted; human review required)."
        status = "Escalated - Human Review Required"
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [Routing Agent] Escalated to {escalation_tier}. Reason: {escalation_reason}")

    # 4. Insufficient Knowledge Base Grounding or Policy Warning
    elif not is_grounded or len(retrieved_articles) == 0 or critic_verdict == "Flagged":
        is_escalated = True
        escalation_tier = "Tier 2 Technical Support (Specialized Review)"
        escalation_reason = (
            "Insufficient approved knowledge base evidence: No verified SOP article matched this incident. "
            "Routing to Tier 2 specialist for custom diagnosis."
        )
        status = "Escalated - Insufficient Evidence"
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [Routing Agent] Escalated to {escalation_tier}. Reason: {escalation_reason}")

    # 5. Standard Tier 1 Advisory Guidance
    else:
        is_escalated = False
        escalation_tier = "Tier 1 (Automated Guidance)"
        escalation_reason = "Ticket within standard Tier 1 scope. Advisory troubleshooting steps provided based on verified KB SOP."
        status = "Triaged - Advisory Guidance Provided"
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [Routing Agent] Ticket triaged within standard Tier 1 scope.")
        
    return {
        "is_escalated": is_escalated,
        "escalation_tier": escalation_tier,
        "escalation_reason": escalation_reason,
        "status": status,
        "execution_logs": logs
    }


def build_helpdesk_graph():
    """
    Constructs and compiles the LangGraph StateGraph.
    Pipeline: Triage -> Retrieval -> Resolution -> Critic -> (Bounded Feedback Loop) -> Output Router -> END.
    """
    builder = StateGraph(IncidentTicketState)
    
    # Add nodes
    builder.add_node("triage", triage_node)
    builder.add_node("retrieval", retrieval_node)
    builder.add_node("resolution", resolution_node)
    builder.add_node("critic", critic_node)
    builder.add_node("router", router_node)
    
    # Define execution edge pipeline with bounded feedback loop
    builder.set_entry_point("triage")
    builder.add_edge("triage", "retrieval")
    builder.add_edge("retrieval", "resolution")
    builder.add_edge("resolution", "critic")
    
    # Bounded feedback conditional edge: if validation fails, retry resolution once; else router
    builder.add_conditional_edges(
        "critic",
        critic_condition,
        {
            "resolution": "resolution",
            "router": "router"
        }
    )
    builder.add_edge("router", END)
    
    return builder.compile()


# Singleton compiled graph
helpdesk_graph = build_helpdesk_graph()


def process_ticket(title: str, description: str, impact: str, urgency: str) -> Dict[str, Any]:
    """
    Executes the entire multi-agent LangGraph workflow for a given ticket.
    """
    initial_state: IncidentTicketState = {
        "title": title,
        "description": description,
        "impact": impact,
        "urgency": urgency,
        "category": None,
        "priority": None,
        "triage_reasoning": None,
        "retrieved_articles": [],
        "supported_article_ids": [],
        "recommendation": None,
        "requires_onsite": False,
        "critic_verdict": None,
        "critic_critique": None,
        "critic_flags": [],
        "is_safe": True,
        "is_grounded": True,
        "is_escalated": False,
        "escalation_tier": None,
        "escalation_reason": None,
        "status": None,
        "revision_count": 0,
        "critic_feedback": None,
        "execution_logs": [],
        "agent_sources": {}
    }
    
    final_state = helpdesk_graph.invoke(initial_state)
    return final_state

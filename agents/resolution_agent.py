"""
Resolution Agent for HelpDesk AI.
Synthesizes safe, concise, step-by-step troubleshooting recommendations
grounded strictly in the retrieved Knowledge Base articles.
"""

from typing import List, Dict, Any
from llm_client import call_llm


def fallback_resolution_recommendation(
    title: str,
    category: str,
    articles: List[Dict[str, Any]]
) -> str:
    """
    Constructs a clear, grounded resolution guide directly from retrieved articles
    when LLM backends (NVIDIA NIM and Ollama) are offline or fail.
    Explicitly labeled as a deterministic fallback.
    """
    if not articles:
        return (
            "**[DETERMINISTIC FALLBACK - INSUFFICIENT EVIDENCE]**\n\n"
            "No matching Knowledge Base SOP was found for this incident, and LLM backends are unavailable.\n\n"
            "**Advisory Guidance:**\n"
            "1. Collect relevant error logs and timestamps from the affected endpoint.\n"
            "2. Verify network configuration and check for recent software updates.\n"
            "3. Ticket is routed to Tier 2 Support for specialized human investigation.\n\n"
            "*Notice: Unverified deterministic fallback. No automated device isolation performed.*"
        )

    primary_article = articles[0]
    steps_formatted = "\n".join(primary_article.get("steps", []))
    
    recommendation = (
        f"**[DETERMINISTIC FALLBACK - LLM OFFLINE]**\n\n"
        f"**Advisory Troubleshooting Guide (Referencing [{primary_article['id']} - {primary_article['title']}]):**\n\n"
        f"*{primary_article.get('summary', '')}*\n\n"
        f"**Recommended Action Items:**\n"
        f"{steps_formatted}\n\n"
        f"*Notice: Synthesized deterministically from verified KB SOP. These are initial advisory steps for the user. "
        f"The system does NOT automatically isolate devices or contain threats. Never share passwords or authentication tokens.*"
    )
    return recommendation


def run_resolution_agent(
    title: str,
    description: str,
    category: str,
    priority: str,
    retrieved_articles: List[Dict[str, Any]],
    critic_feedback: str = None
) -> Dict[str, Any]:
    """
    Invokes LLM (NVIDIA NIM or Ollama) to formulate concise recommendations based on retrieved knowledge.
    Supports bounded feedback revision when critic_feedback is provided.
    Falls back gracefully to KB article steps if LLM backends fail.
    """
    supported_ids = [a["id"] for a in retrieved_articles] if retrieved_articles else []

    # If no articles were retrieved, return clear insufficient evidence advice
    if not retrieved_articles:
        return {
            "recommendation": fallback_resolution_recommendation(title, category, []),
            "source": "deterministic_kb_synthesis",
            "requires_onsite": False,
            "supported_article_ids": []
        }
    
    # Prepare KB context
    kb_context_snippets = []
    for art in retrieved_articles:
        steps_text = "\n".join(art.get("steps", []))
        kb_context_snippets.append(
            f"Article [{art.get('id')}] - {art.get('title')}:\n"
            f"Summary: {art.get('summary')}\n"
            f"Official Approved Steps:\n{steps_text}"
        )
    kb_context = "\n\n---\n\n".join(kb_context_snippets)

    feedback_section = ""
    if critic_feedback:
        feedback_section = f"""
PREVIOUS DRAFT REJECTED BY CRITIC (REVISION REQUIRED):
The previous recommendation draft failed validation with the following critique:
"{critic_feedback}"
You MUST revise your recommendations to resolve these issues while remaining strictly grounded in the approved KB documentation.
"""

    prompt = f"""You are an IT Tier-1 Incident Resolution Specialist.
Provide concise, numbered, step-by-step troubleshooting recommendations for this ticket based ONLY on the provided Knowledge Base documentation.
Cite the supporting article ID (e.g. [{supported_ids[0]}]) in your response.
{feedback_section}
Incident Details:
- Title: {title}
- Description: {description}
- Category: {category}
- Priority: {priority}

Approved Knowledge Base Documentation:
{kb_context}

CRITICAL SAFETY RULES:
1. Do NOT ask for the user's password, PIN, or sensitive credentials.
2. Do NOT execute or propose dangerous irreversible commands (e.g. format disk, rm -rf).
3. Do NOT claim the ticket is resolved or closed; suggest advisory steps only.
4. If this is a security incident, instruct the USER to disconnect from the network (unplug Ethernet / turn off Wi-Fi) and report to SecOps. Do NOT claim the system automatically isolated the endpoint.

Respond with ONLY a JSON object:
{{
  "recommendations": "1. [First action referencing KB article] ... 2. [Second action] ...",
  "estimated_resolution_time": "15-30 mins",
  "requires_onsite_support": false
}}"""

    system_prompt = "You are an IT Resolution Specialist. Output strictly valid JSON."

    llm_result = call_llm(prompt=prompt, system_prompt=system_prompt, json_mode=True)

    if llm_result.get("success") and llm_result.get("parsed_json"):
        data = llm_result["parsed_json"]
        recs = data.get("recommendations", "").strip()
        time_est = data.get("estimated_resolution_time", "15-30 minutes")
        onsite = bool(data.get("requires_onsite_support", False))
        
        # If security incident, ensure user advisory disconnect guidance is present
        if category == "Security":
            recs_lower = recs.lower()
            if "disconnect" not in recs_lower and "isolate" not in recs_lower and "unplug" not in recs_lower:
                recs = (
                    "1. MANDATORY ADVISORY: Immediately disconnect your device from the network (unplug Ethernet cable / turn off Wi-Fi).\n"
                    "2. Report this incident immediately to SecOps on-call (soc-incident@corp.local).\n"
                    + recs
                )

        if recs:
            formatted_output = f"{recs}\n\n*Estimated triage time: {time_est}*"
            return {
                "recommendation": formatted_output,
                "source": llm_result.get("source", "nvidia"),
                "model": llm_result.get("model", ""),
                "requires_onsite": onsite,
                "supported_article_ids": supported_ids
            }

    # Fallback to direct KB synthesis
    fallback_recs = fallback_resolution_recommendation(title, category, retrieved_articles)
    return {
        "recommendation": fallback_recs,
        "source": "deterministic_kb_synthesis",
        "requires_onsite": False,
        "supported_article_ids": supported_ids
    }

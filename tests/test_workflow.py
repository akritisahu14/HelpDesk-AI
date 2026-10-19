"""
Automated Integration and End-to-End Workflow Tests for HelpDesk AI.
Validates the complete LangGraph multi-agent pipeline:
triage -> knowledge retrieval -> resolution -> critic/validation -> routing.
Ensures:
1. All 5 nodes and conditional feedback loop edges are correctly configured.
2. Standard tickets receive grounded advisory guidance without premature resolution.
3. Security incidents enforce mandatory human SecOps review escalation.
4. Insufficient KB grounding escalates to Tier 2 Support.
5. Critic agent safety rejections trigger bounded feedback revision.
6. Ticket escalation and resolution are accurately represented without false external dispatch claims.
"""

import unittest
from agents.orchestrator import (
    build_helpdesk_graph,
    helpdesk_graph,
    process_ticket,
    critic_condition,
    router_node,
    IncidentTicketState,
    MAX_CRITIC_REVISIONS
)
from agents.triage_agent import check_security_triggers, deterministic_category_classifier
from agents.critic_agent import heuristic_critic_check
from agents.resolution_agent import fallback_resolution_recommendation


class TestMultiAgentWorkflow(unittest.TestCase):
    """End-to-end and structural tests for the LangGraph multi-agent workflow."""

    def test_graph_nodes_and_compilation(self):
        """Verifies that the LangGraph StateGraph builds successfully with all 5 nodes."""
        graph = build_helpdesk_graph()
        self.assertIsNotNone(graph)
        # Check node names registered in the graph
        node_keys = list(graph.nodes.keys())
        for required_node in ["triage", "retrieval", "resolution", "critic", "router"]:
            self.assertIn(required_node, node_keys)

    def test_end_to_end_standard_ticket_flow(self):
        """Verifies standard network issue executes end-to-end through LangGraph."""
        ticket = {
            "title": "Corporate VPN Gateway Timeout",
            "description": "AnyConnect client fails with error 'Secure Gateway unreachable' when connecting from home.",
            "impact": "One user",
            "urgency": "Work impaired"
        }
        res = process_ticket(
            title=ticket["title"],
            description=ticket["description"],
            impact=ticket["impact"],
            urgency=ticket["urgency"]
        )

        self.assertEqual(res["category"], "Network")
        self.assertIn(res["priority"], ["Medium", "High"])
        self.assertGreater(len(res["retrieved_articles"]), 0)
        self.assertIn("KB-NET-001", res["supported_article_ids"])
        self.assertIsNotNone(res["recommendation"])
        self.assertTrue(res["is_safe"])
        self.assertFalse(res["is_escalated"])
        self.assertEqual(res["status"], "Triaged - Advisory Guidance Provided")
        self.assertNotIn("Resolved", res["status"], "AI triage must never mark a ticket as Resolved")

    def test_end_to_end_security_mandatory_escalation(self):
        """Security incidents must be classified as Security and escalated to SecOps human review."""
        ticket = {
            "title": "Clicked phishing email and entered my password",
            "description": "Received fake Microsoft login prompt and entered corporate credentials.",
            "impact": "One user",
            "urgency": "Work blocked"
        }
        res = process_ticket(
            title=ticket["title"],
            description=ticket["description"],
            impact=ticket["impact"],
            urgency=ticket["urgency"]
        )

        self.assertEqual(res["category"], "Security")
        self.assertIn(res["priority"], ["High", "Critical"])
        self.assertTrue(res["is_escalated"])
        self.assertIn("SecOps", res["escalation_tier"])
        self.assertIn("Human Security Review Required", res["escalation_tier"])
        self.assertIn("Escalated - Security Incident", res["status"])

    def test_end_to_end_insufficient_evidence_escalation(self):
        """Incidents with zero matching KB articles must escalate to Tier 2 Technical Support."""
        ticket = {
            "title": "Routing Test: Insufficient Knowledge Base Grounding",
            "description": "Unsupported legacy COBOL main-frame compiler error XYZ999 with zero KB articles.",
            "impact": "One user",
            "urgency": "Work impaired"
        }
        res = process_ticket(
            title=ticket["title"],
            description=ticket["description"],
            impact=ticket["impact"],
            urgency=ticket["urgency"]
        )

        self.assertEqual(len(res["retrieved_articles"]), 0)
        self.assertTrue(res["is_escalated"])
        self.assertIn("Tier 2", res["escalation_tier"])
        self.assertEqual(res["status"], "Escalated - Insufficient Evidence")

    def test_critic_feedback_loop_routing(self):
        """Verifies that bounded feedback routes back to resolution on first failure, then to router."""
        mock_state: IncidentTicketState = {
            "title": "Test Title",
            "description": "Test Desc",
            "impact": "One user",
            "urgency": "Work impaired",
            "category": "Software",
            "priority": "Medium",
            "triage_reasoning": "Reason",
            "retrieved_articles": [],
            "supported_article_ids": [],
            "recommendation": "Dangerous text",
            "requires_onsite": False,
            "critic_verdict": "Rejected",
            "critic_critique": "Unsafe command",
            "critic_flags": ["Destructive command"],
            "critic_feedback": "Unsafe command",
            "is_safe": False,
            "is_grounded": True,
            "is_escalated": False,
            "escalation_tier": None,
            "escalation_reason": None,
            "status": None,
            "revision_count": 1,
            "execution_logs": [],
            "agent_sources": {}
        }
        # First attempt: loop back to resolution
        self.assertEqual(critic_condition(mock_state), "resolution")

        # Exceeded revision limit: route forward to router for human review escalation
        mock_state["revision_count"] = MAX_CRITIC_REVISIONS + 1
        self.assertEqual(critic_condition(mock_state), "router")

    def test_no_claim_of_external_ticket_dispatch(self):
        """Verifies ticket routing explicitly references internal human review without claiming external dispatch."""
        mock_state: IncidentTicketState = {
            "title": "Critical ERP Failure",
            "description": "Database cluster completely offline",
            "impact": "Business-critical service",
            "urgency": "Work blocked",
            "category": "Software",
            "priority": "Critical",
            "triage_reasoning": "Major outage",
            "retrieved_articles": [{"id": "KB-SFT-007"}],
            "supported_article_ids": ["KB-SFT-007"],
            "recommendation": "Advisory steps",
            "requires_onsite": False,
            "critic_verdict": "Approved",
            "critic_critique": "Safe",
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
        res = router_node(mock_state)
        # Verify accurate escalation representation
        self.assertTrue(res["is_escalated"])
        self.assertIn("Priority Incident Command", res["escalation_tier"])
        # Must not claim external ticket dispatch was performed
        for log in res["execution_logs"]:
            self.assertNotIn("dispatched to external", log.lower())
            self.assertNotIn("servicenow ticket created", log.lower())

    def test_resolution_is_advisory_never_closed_by_ai(self):
        """Verifies resolution steps are advisory and do not declare ticket resolved or closed."""
        rec = fallback_resolution_recommendation(
            title="Outlook Freezing",
            category="Software",
            articles=[{"id": "KB-SFT-004", "title": "Outlook", "summary": "Fix cache", "steps": ["1. Safe mode"]}]
        )
        self.assertNotIn("issue is resolved", rec.lower())
        self.assertNotIn("ticket has been resolved", rec.lower())
        self.assertNotIn("ticket closed", rec.lower())


if __name__ == "__main__":
    unittest.main()

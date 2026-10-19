"""
Unit and integration test suite for HelpDesk AI.
Tests classification, priority assignment, knowledge retrieval, critic safety guardrails,
and escalation routing across all standard and edge scenarios.
"""

import unittest
from knowledge_base import search_knowledge_base, get_article_by_id, KB_ARTICLES
from agents.triage_agent import (
    calculate_itil_priority,
    deterministic_category_classifier,
    check_security_triggers,
    rule_based_triage_fallback
)
from agents.critic_agent import heuristic_critic_check
from agents.orchestrator import router_node, IncidentTicketState, process_ticket
from evaluation import run_comprehensive_evaluation, SYNTHETIC_EVALUATION_DATASET


class TestCategoryClassification(unittest.TestCase):
    """Verifies correct category classification across Network, Hardware, Software, Access, and Security."""

    def test_network_classification(self):
        cat, _ = deterministic_category_classifier(
            "Corporate VPN failure",
            "AnyConnect gateway timeout while connecting from remote"
        )
        self.assertEqual(cat, "Network")

        cat_dns, _ = deterministic_category_classifier(
            "DNS lookup failure",
            "Cannot resolve internal hostname or ping local gateway"
        )
        self.assertEqual(cat_dns, "Network")

    def test_access_classification(self):
        cat, _ = deterministic_category_classifier(
            "SSO Active Directory lockout",
            "My account locked out after expired password attempt"
        )
        self.assertEqual(cat, "Access")

        cat_perm, _ = deterministic_category_classifier(
            "Shared drive access denied",
            "Need RBAC folder permission for departmental network drive"
        )
        self.assertEqual(cat_perm, "Access")

    def test_hardware_classification(self):
        cat, _ = deterministic_category_classifier(
            "Laptop overheating and fan blasting",
            "Thermal throttling and high temperature causing reboot"
        )
        self.assertEqual(cat, "Hardware")

        cat_dock, _ = deterministic_category_classifier(
            "USB-C Docking Station screen blank",
            "External monitor display not detected on workstation"
        )
        self.assertEqual(cat_dock, "Hardware")

    def test_software_classification(self):
        cat, _ = deterministic_category_classifier(
            "Outlook client freezing",
            "Inbox slow synchronization and email app freeze on startup"
        )
        self.assertEqual(cat, "Software")

        cat_crash, _ = deterministic_category_classifier(
            "Application crash error",
            "Excel app crash with corrupted cache"
        )
        self.assertEqual(cat_crash, "Software")

    def test_security_classification(self):
        cat_phish, _ = deterministic_category_classifier(
            "Urgent invoice email link clicked",
            "Fake login prompt and credential entered"
        )
        self.assertEqual(cat_phish, "Security")

        cat_ransom, _ = deterministic_category_classifier(
            "Ransomware alert",
            "Encrypted files with .locked extension and ransom note"
        )
        self.assertEqual(cat_ransom, "Security")


class TestITILPriorityAssignment(unittest.TestCase):
    """Verifies priority assignment across Low, Medium, High, and Critical impact cases."""

    def test_business_critical_outage_is_critical(self):
        prio = calculate_itil_priority("Business-critical service", "Work blocked")
        self.assertEqual(prio, "Critical")

    def test_multiple_users_work_blocked_is_high(self):
        prio = calculate_itil_priority("Multiple users", "Work blocked")
        self.assertEqual(prio, "High")

    def test_single_user_work_blocked_is_high(self):
        prio = calculate_itil_priority("One user", "Work blocked")
        self.assertEqual(prio, "High")

    def test_single_user_work_impaired_is_medium(self):
        prio = calculate_itil_priority("One user", "Work impaired")
        self.assertEqual(prio, "Medium")

    def test_single_user_minor_inconvenience_is_low(self):
        prio = calculate_itil_priority("One user", "Minor inconvenience")
        self.assertEqual(prio, "Low")

    def test_security_incident_priority_elevation(self):
        # Security incident with blocked work must be Critical
        p_sec_crit = calculate_itil_priority("Business-critical service", "Work blocked", is_security=True)
        self.assertEqual(p_sec_crit, "Critical")

        # Security incident with minor inconvenience must be elevated to High (never Medium or Low)
        p_sec_high = calculate_itil_priority("One user", "Minor inconvenience", is_security=True)
        self.assertEqual(p_sec_high, "High")
        self.assertNotIn(p_sec_high, ["Medium", "Low"])


class TestSecurityIncidentTriggers(unittest.TestCase):
    """Verifies deterministic triggers for phishing, exposed credentials, malware, and breaches."""

    def test_phishing_and_credential_detection(self):
        is_sec, reason = check_security_triggers("I received a phishing email and entered my password on the fake site.")
        self.assertTrue(is_sec)
        self.assertIn("phishing", reason.lower())

    def test_ransomware_detection(self):
        is_sec, reason = check_security_triggers("Files encrypted and ransom note found on desktop.")
        self.assertTrue(is_sec)

    def test_benign_text_does_not_trigger_security(self):
        is_sec, _ = check_security_triggers("Please help me setup my second monitor on the docking station.")
        self.assertFalse(is_sec)


class TestKnowledgeBaseRetrieval(unittest.TestCase):
    """Verifies Knowledge Base search, ranking, and threshold behavior."""

    def test_vpn_retrieval(self):
        results = search_knowledge_base("AnyConnect corporate VPN gateway timeout", category_hint="Network")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["id"], "KB-NET-001")

    def test_password_retrieval(self):
        results = search_knowledge_base("Password reset lockout SSO Active Directory", category_hint="Access")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["id"], "KB-ACC-002")

    def test_phishing_retrieval(self):
        results = search_knowledge_base("Phishing suspicious link email credential exposure", category_hint="Security")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["id"], "KB-SEC-005")

    def test_malware_retrieval(self):
        results = search_knowledge_base("Ransomware encrypted files and malware alert", category_hint="Security")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["id"], "KB-SEC-010")

    def test_unsupported_query_returns_empty(self):
        # Queries with no relevance should return empty list (insufficient evidence detection)
        results = search_knowledge_base("Unrelated quantum physics formula derivation XYZ", category_hint="Other")
        self.assertEqual(len(results), 0)

    def test_kb_structure_integrity(self):
        self.assertGreaterEqual(len(KB_ARTICLES), 10)
        for article in KB_ARTICLES:
            self.assertTrue(article["id"].startswith("KB-"))
            self.assertIn("title", article)
            self.assertIn("category", article)
            self.assertIn("steps", article)
            self.assertIsInstance(article["steps"], list)
            self.assertGreater(len(article["steps"]), 0)


class TestCriticSafetyGuardrails(unittest.TestCase):
    """Verifies Critic agent deterministic safety checks and rejection behavior."""

    def test_rejects_credential_solicitation(self):
        unsafe_rec = "Please provide your corporate password and PIN so we can unlock your workstation."
        verdict = heuristic_critic_check("Forgot password", unsafe_rec, "Access")
        self.assertFalse(verdict["is_safe"])
        self.assertEqual(verdict["verdict"], "Rejected")
        self.assertTrue(any("credential" in f.lower() for f in verdict["flags"]))

    def test_rejects_destructive_command(self):
        destructive_rec = "Open command prompt and type format c: to reset the drive."
        verdict = heuristic_critic_check("System slow", destructive_rec, "Hardware")
        self.assertFalse(verdict["is_safe"])
        self.assertEqual(verdict["verdict"], "Rejected")
        self.assertTrue(any("destructive" in f.lower() for f in verdict["flags"]))

    def test_rejects_premature_resolution_claim(self):
        claim_rec = "1. Flush DNS.\n2. This ticket is now resolved and closed."
        verdict = heuristic_critic_check("DNS issue", claim_rec, "Network")
        self.assertFalse(verdict["is_safe"])
        self.assertEqual(verdict["verdict"], "Rejected")
        self.assertTrue(any("premature resolution" in f.lower() for f in verdict["flags"]))

    def test_flags_security_missing_isolation_guidance(self):
        incomplete_sec_rec = "Change your browser homepage and delete email from trash."
        verdict = heuristic_critic_check("Phishing click", incomplete_sec_rec, "Security")
        self.assertEqual(verdict["verdict"], "Flagged")
        self.assertFalse(verdict["has_escalation_guidance"])

    def test_flags_unsupported_advice_without_kb(self):
        rec = "Try random troubleshooting steps."
        verdict = heuristic_critic_check("Unknown bug", rec, "Software", retrieved_articles=[])
        self.assertEqual(verdict["verdict"], "Flagged")
        self.assertFalse(verdict["is_grounded"])

    def test_approves_safe_troubleshooting(self):
        safe_rec = (
            "1. Verify internet connectivity by pinging DNS gateway.\n"
            "2. Restart your VPN client application.\n"
            "3. If issues persist, contact Network Operations."
        )
        mock_kb = [{"id": "KB-NET-001", "title": "VPN", "category": "Network"}]
        verdict = heuristic_critic_check("VPN down", safe_rec, "Network", retrieved_articles=mock_kb)
        self.assertTrue(verdict["is_safe"])
        self.assertEqual(verdict["verdict"], "Approved")


class TestRoutingAndEscalation(unittest.TestCase):
    """Verifies routing logic for Security, Critical, Critic rejection, and Insufficient Evidence."""

    def test_security_incident_escalation(self):
        state: IncidentTicketState = {
            "title": "Credential exposure",
            "description": "Entered password on phishing page",
            "impact": "One user",
            "urgency": "Work blocked",
            "category": "Security",
            "priority": "High",
            "triage_reasoning": "Security breach",
            "retrieved_articles": [{"id": "KB-SEC-005"}],
            "supported_article_ids": ["KB-SEC-005"],
            "recommendation": "Disconnect endpoint and report to SecOps.",
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
        res = router_node(state)
        self.assertTrue(res["is_escalated"])
        self.assertIn("SecOps", res["escalation_tier"])
        self.assertIn("Human Security Review Required", res["escalation_tier"])
        self.assertIn("Escalated - Security Incident", res["status"])

    def test_critic_bounded_feedback_loop(self):
        """Verifies bounded feedback loop in orchestrator: retries once on critic rejection, then escalates."""
        from agents.orchestrator import critic_condition
        mock_fail_state: IncidentTicketState = {
            "title": "Password reset",
            "description": "User locked out",
            "impact": "One user",
            "urgency": "Work blocked",
            "category": "Access",
            "priority": "High",
            "triage_reasoning": "Lockout",
            "retrieved_articles": [{"id": "KB-ACC-002", "title": "AD Reset", "summary": "Reset password", "steps": ["1. Use portal."]}],
            "supported_article_ids": ["KB-ACC-002"],
            "recommendation": "Send me your password in chat.",
            "requires_onsite": False,
            "critic_verdict": "Rejected",
            "critic_critique": "Credential prompt detected",
            "critic_flags": ["Credential harvesting solicitation detected"],
            "critic_feedback": "Credential prompt detected",
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
        # First rejection triggers bounded loop back to resolution
        self.assertEqual(critic_condition(mock_fail_state), "resolution")

        # Exceeded revision limit triggers router escalation
        mock_fail_state["revision_count"] = 2
        self.assertEqual(critic_condition(mock_fail_state), "router")

    def test_deterministic_fallback_labeling(self):
        """Verifies fallback output is clearly labeled and does not claim automated isolation."""
        from agents.resolution_agent import fallback_resolution_recommendation
        rec = fallback_resolution_recommendation(
            "VPN down",
            "Network",
            [{"id": "KB-NET-001", "title": "VPN", "summary": "VPN fix", "steps": ["1. Flush DNS"]}]
        )
        self.assertIn("[DETERMINISTIC FALLBACK - LLM OFFLINE]", rec)
        self.assertIn("The system does NOT automatically isolate devices", rec)

    def test_critical_outage_escalation(self):
        state: IncidentTicketState = {
            "title": "ERP Outage",
            "description": "Production database cluster down",
            "impact": "Business-critical service",
            "urgency": "Work blocked",
            "category": "Software",
            "priority": "Critical",
            "triage_reasoning": "Major outage",
            "retrieved_articles": [{"id": "KB-SFT-007"}],
            "supported_article_ids": ["KB-SFT-007"],
            "recommendation": "Engage DBA team.",
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
            "execution_logs": [],
            "agent_sources": {}
        }
        res = router_node(state)
        self.assertTrue(res["is_escalated"])
        self.assertIn("Priority Incident Command", res["escalation_tier"])

    def test_critic_rejected_escalates_to_human_review(self):
        state: IncidentTicketState = {
            "title": "Password reset",
            "description": "User locked out",
            "impact": "One user",
            "urgency": "Work blocked",
            "category": "Access",
            "priority": "High",
            "triage_reasoning": "Lockout",
            "retrieved_articles": [{"id": "KB-ACC-002"}],
            "supported_article_ids": ["KB-ACC-002"],
            "recommendation": "Send me your password in chat.",
            "requires_onsite": False,
            "critic_verdict": "Rejected",
            "critic_critique": "Credential prompt detected",
            "critic_flags": ["Credential harvesting solicitation detected"],
            "is_safe": False,
            "is_grounded": True,
            "is_escalated": False,
            "escalation_tier": None,
            "escalation_reason": None,
            "status": None,
            "execution_logs": [],
            "agent_sources": {}
        }
        res = router_node(state)
        self.assertTrue(res["is_escalated"])
        self.assertIn("Human Review Required", res["escalation_tier"])
        self.assertEqual(res["status"], "Escalated - Human Review Required")

    def test_insufficient_evidence_escalates_to_tier_2(self):
        state: IncidentTicketState = {
            "title": "Unsupported custom app error",
            "description": "App XYZ failed with code 999",
            "impact": "One user",
            "urgency": "Work impaired",
            "category": "Software",
            "priority": "Medium",
            "triage_reasoning": "Custom app",
            "retrieved_articles": [],
            "supported_article_ids": [],
            "recommendation": "Collect logs.",
            "requires_onsite": False,
            "critic_verdict": "Flagged",
            "critic_critique": "No KB article matched",
            "critic_flags": ["Unsupported advice: No approved KB matched"],
            "is_safe": True,
            "is_grounded": False,
            "is_escalated": False,
            "escalation_tier": None,
            "escalation_reason": None,
            "status": None,
            "execution_logs": [],
            "agent_sources": {}
        }
        res = router_node(state)
        self.assertTrue(res["is_escalated"])
        self.assertIn("Tier 2", res["escalation_tier"])
        self.assertEqual(res["status"], "Escalated - Insufficient Evidence")


class TestEvaluationSuite(unittest.TestCase):
    """Executes the full 16-case synthetic benchmark suite and validates performance metrics."""

    def test_run_comprehensive_evaluation(self):
        results = run_comprehensive_evaluation()
        self.assertEqual(results["total_test_cases"], 16)
        
        # Verify category accuracy is 100% on the benchmark
        self.assertEqual(results["category_accuracy"], 100.0)
        
        # Verify priority accuracy is 100%
        self.assertEqual(results["priority_accuracy"], 100.0)
        
        # Verify security recall is 100% (critical requirement: zero missed security threats)
        self.assertEqual(results["security_recall"], 100.0)
        
        # Verify retrieval accuracy is 100%
        self.assertEqual(results["retrieval_accuracy"], 100.0)
        
        # Verify routing accuracy is 100%
        self.assertEqual(results["routing_accuracy"], 100.0)
        
        # Verify Critic caught all safety violations
        self.assertEqual(results["critic_counts"]["Rejected"], 3)
        self.assertGreaterEqual(results["critic_counts"]["Flagged"], 1)
        
        # Verify limitation note exists
        self.assertIn("Synthetic Benchmark Limitation", results["limitation_note"])


class TestNvidiaLLMClientAndRateLimiter(unittest.TestCase):
    """Verifies the NVIDIA NIM LLM client, sliding-window 40 RPM rate limiter, and JSON parsing."""

    def test_rate_limiter_quota_and_telemetry(self):
        from llm_client import SlidingWindowRateLimiter
        limiter = SlidingWindowRateLimiter(max_rpm=40, window_seconds=60.0)
        
        initial_stats = limiter.get_stats()
        self.assertEqual(initial_stats["max_rpm"], 40)
        self.assertEqual(initial_stats["current_rpm_used"], 0)
        self.assertEqual(initial_stats["available_slots"], 40)
        self.assertEqual(initial_stats["total_requests"], 0)

        # Acquire 5 requests
        for _ in range(5):
            limiter.acquire()

        stats = limiter.get_stats()
        self.assertEqual(stats["current_rpm_used"], 5)
        self.assertEqual(stats["available_slots"], 35)
        self.assertEqual(stats["total_requests"], 5)

    def test_rate_limiter_window_expiration(self):
        import time
        from llm_client import SlidingWindowRateLimiter
        # Short window for rapid test execution
        limiter = SlidingWindowRateLimiter(max_rpm=5, window_seconds=0.15)
        
        for _ in range(3):
            limiter.acquire()
        
        self.assertEqual(limiter.get_stats()["current_rpm_used"], 3)
        time.sleep(0.2)
        # Should now be empty as window expired
        self.assertEqual(limiter.get_stats()["current_rpm_used"], 0)
        self.assertEqual(limiter.get_stats()["available_slots"], 5)

    def test_check_model_status_nvidia(self):
        from llm_client import check_model_status
        status = check_model_status()
        self.assertTrue(status["available"])
        self.assertEqual(status["active_provider"], "NVIDIA NIM")
        self.assertEqual(status["nvidia"]["model"], "nvidia/nemotron-3-super-120b-a12b")
        self.assertEqual(status["nvidia"]["max_rpm"], 40)
        self.assertTrue(status["nvidia"]["api_key_configured"])
        self.assertTrue(status["nvidia"]["api_key_masked"].startswith("nvapi-"))

    def test_extract_json_from_text(self):
        from llm_client import extract_json_from_text
        
        # Pure JSON
        self.assertEqual(extract_json_from_text('{"a": 1}'), {"a": 1})
        
        # Markdown fenced block
        md_text = "Here is the response:\n```json\n{\"category\": \"Network\", \"priority\": \"High\"}\n```\nHope this helps!"
        res = extract_json_from_text(md_text)
        self.assertIsNotNone(res)
        self.assertEqual(res.get("category"), "Network")
        
        # Outermost curly braces
        dirty_text = "Thought process: thinking... {\"verdict\": \"Approved\"} done."
        res2 = extract_json_from_text(dirty_text)
        self.assertIsNotNone(res2)
        self.assertEqual(res2.get("verdict"), "Approved")
        
        # Invalid
        self.assertIsNone(extract_json_from_text("no json here"))


if __name__ == "__main__":
    unittest.main()

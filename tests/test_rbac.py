"""
Unit tests for HelpDesk AI Role-Based Access Control (RBAC).
Tests each role separately:
1. Employee: Scoped ticket visibility, submission permissions, dashboard metrics.
2. IT Support: Operational queue access, triage capability, escalation permissions.
3. Admin/SecOps: Organisation-wide metrics, security threats filtering, evaluation views.
4. Security & Sanitization: Zero NVIDIA/NIVIDIA leakage and HTML safety.
"""

import unittest
from rbac import (
    ROLE_EMPLOYEE,
    ROLE_IT_SUPPORT,
    ROLE_ADMIN_SECOPS,
    normalize_role,
    get_nav_views_for_role,
    get_backend_tickets,
    can_user_access_ticket,
    filter_security_incidents,
    calculate_role_metrics,
    clean_inference_source,
    sanitize_ui_text
)
from sample_tickets import SAMPLE_TICKETS


class TestEmployeeRole(unittest.TestCase):
    """Verifies that Employee / Incident Reporter role has strictly scoped access."""

    def setUp(self):
        self.employee_email = "akritisahu@eternal.ord"
        self.employee_role = "Employee / Incident Reporter"
        
        # Test ticket pool containing 8 org sample tickets and 2 employee tickets
        self.tickets = [dict(t) for t in SAMPLE_TICKETS]
        self.tickets.append({
            "id": "INC-2001",
            "title": "Employee Monitor Issue",
            "description": "Flickering HDMI connection",
            "reporter_email": self.employee_email,
            "reporter_name": "Akriti Sahu",
            "status": "New",
            "processed_result": None,
            "expected_category": "Hardware",
            "expected_priority": "Low"
        })
        self.tickets.append({
            "id": "INC-2002",
            "title": "Employee VPN Config",
            "description": "Cannot connect to VPN profile",
            "reporter_email": self.employee_email,
            "reporter_name": "Akriti Sahu",
            "status": "Triaged",
            "processed_result": {"status": "Triaged"},
            "expected_category": "Network",
            "expected_priority": "High"
        })

    def test_role_normalization(self):
        self.assertEqual(normalize_role("Employee / Incident Reporter"), ROLE_EMPLOYEE)
        self.assertEqual(normalize_role("employee"), ROLE_EMPLOYEE)
        self.assertEqual(normalize_role("Incident Reporter"), ROLE_EMPLOYEE)

    def test_employee_nav_views(self):
        views = get_nav_views_for_role(self.employee_role)
        self.assertIn("My Dashboard", views)
        self.assertIn("Submit Ticket", views)
        self.assertIn("My Tickets", views)
        self.assertIn("Knowledge Base", views)
        # Sensitive org views MUST NOT be present
        self.assertNotIn("Overview", views)
        self.assertNotIn("Incident Queue", views)
        self.assertNotIn("All Incidents", views)
        self.assertNotIn("Evaluation", views)
        self.assertNotIn("Settings", views)

    def test_employee_backend_ticket_scoping(self):
        """Backend filter MUST return ONLY the employee's own tickets."""
        scoped = get_backend_tickets(self.employee_email, self.employee_role, self.tickets)
        self.assertEqual(len(scoped), 2)
        for t in scoped:
            self.assertEqual(t["reporter_email"], self.employee_email)

    def test_employee_empty_tickets_when_none_submitted(self):
        new_emp_email = "new.user@enterprise.internal"
        scoped = get_backend_tickets(new_emp_email, self.employee_role, self.tickets)
        self.assertEqual(len(scoped), 0)

    def test_employee_unauthorized_ticket_access_rejected(self):
        sample_ticket = self.tickets[0]  # Belonging to Marcus Vance
        self.assertFalse(can_user_access_ticket(sample_ticket, self.employee_email, self.employee_role))
        
        own_ticket = self.tickets[-1]
        self.assertTrue(can_user_access_ticket(own_ticket, self.employee_email, self.employee_role))

    def test_employee_metrics_scoped_properly(self):
        scoped = get_backend_tickets(self.employee_email, self.employee_role, self.tickets)
        metrics = calculate_role_metrics(scoped, self.employee_role, kb_articles_count=10)
        self.assertEqual(metrics["role"], ROLE_EMPLOYEE)
        self.assertEqual(metrics["total_tickets"], 2)
        self.assertEqual(metrics["active_tickets"], 2)
        self.assertEqual(metrics["resolved_tickets"], 0)
        self.assertEqual(metrics["triaged_tickets"], 1)
        self.assertEqual(metrics["approved_sops"], 10)
        # Organisation-wide metrics MUST NOT be present
        self.assertNotIn("total_queue", metrics)
        self.assertNotIn("security_threats", metrics)


class TestITSupportRole(unittest.TestCase):
    """Verifies that IT Support can view queue, triage tickets, and manage incidents."""

    def setUp(self):
        self.it_email = "alex.turner@enterprise.internal"
        self.it_role = "IT Service Desk Specialist"
        self.tickets = [dict(t) for t in SAMPLE_TICKETS]

    def test_role_normalization(self):
        self.assertEqual(normalize_role("IT Service Desk Specialist"), ROLE_IT_SUPPORT)
        self.assertEqual(normalize_role("IT Support"), ROLE_IT_SUPPORT)
        self.assertEqual(normalize_role("Support Desk"), ROLE_IT_SUPPORT)

    def test_it_support_nav_views(self):
        views = get_nav_views_for_role(self.it_role)
        self.assertIn("Queue Overview", views)
        self.assertIn("Incident Queue", views)
        self.assertIn("Triage Workbench", views)
        self.assertIn("Knowledge Base", views)
        self.assertIn("Settings", views)
        # Evaluation is Admin/SecOps only
        self.assertNotIn("Evaluation", views)

    def test_it_support_backend_access(self):
        """IT Support receives all operational queue incidents."""
        queue = get_backend_tickets(self.it_email, self.it_role, self.tickets)
        self.assertEqual(len(queue), 8)
        self.assertTrue(can_user_access_ticket(self.tickets[0], self.it_email, self.it_role))

    def test_it_support_metrics_reflect_actual_state(self):
        """Initial untriaged state: triaged is 0 while queue is 8."""
        for t in self.tickets:
            t["status"] = "New"
            t["processed_result"] = None

        metrics = calculate_role_metrics(self.tickets, self.it_role, kb_articles_count=10)
        self.assertEqual(metrics["total_queue"], 8)
        self.assertEqual(metrics["triaged_analyzed"], 0)
        self.assertEqual(metrics["pending_triage"], 8)
        self.assertEqual(metrics["high_critical"], 4)

        # After triaging 2 tickets:
        self.tickets[0]["processed_result"] = {"status": "Triaged"}
        self.tickets[0]["status"] = "Triaged"
        self.tickets[1]["processed_result"] = {"status": "Escalated"}
        self.tickets[1]["status"] = "Escalated"

        updated = calculate_role_metrics(self.tickets, self.it_role, kb_articles_count=10)
        self.assertEqual(updated["total_queue"], 8)
        self.assertEqual(updated["triaged_analyzed"], 2)
        self.assertEqual(updated["pending_triage"], 6)
        self.assertEqual(updated["escalated"], 1)


class TestAdminSecOpsRole(unittest.TestCase):
    """Verifies that Admin/SecOps has organisation-wide visibility and security focus."""

    def setUp(self):
        self.secops_email = "test.engineer@enterprise.internal"
        self.secops_role = "SecOps Incident Analyst"
        self.tickets = [dict(t) for t in SAMPLE_TICKETS]

    def test_role_normalization(self):
        self.assertEqual(normalize_role("SecOps Incident Analyst"), ROLE_ADMIN_SECOPS)
        self.assertEqual(normalize_role("Admin"), ROLE_ADMIN_SECOPS)
        self.assertEqual(normalize_role("System Administrator"), ROLE_ADMIN_SECOPS)

    def test_admin_secops_nav_views(self):
        views = get_nav_views_for_role(self.secops_role)
        self.assertIn("Executive Metrics", views)
        self.assertIn("Security Incidents", views)
        self.assertIn("All Incidents", views)
        self.assertIn("Knowledge Base", views)
        self.assertIn("Evaluation", views)
        self.assertIn("Admin Settings", views)

    def test_admin_secops_metrics(self):
        metrics = calculate_role_metrics(self.tickets, self.secops_role, kb_articles_count=10)
        self.assertEqual(metrics["total_org_incidents"], 8)
        self.assertEqual(metrics["security_threats"], 2)  # INC-1005 and INC-1008
        self.assertEqual(metrics["high_critical"], 4)

    def test_filter_security_incidents(self):
        sec_incidents = filter_security_incidents(self.tickets)
        self.assertEqual(len(sec_incidents), 2)
        sec_ids = [t["id"] for t in sec_incidents]
        self.assertIn("INC-1005", sec_ids)
        self.assertIn("INC-1008", sec_ids)


class TestSanitizationAndBranding(unittest.TestCase):
    """Verifies that no NVIDIA branding or internal artifacts leak into UI text."""

    def test_clean_inference_source(self):
        self.assertEqual(clean_inference_source("nvidia"), "Enterprise Cloud LLM")
        self.assertEqual(clean_inference_source("nvidia-nim"), "Enterprise Cloud LLM")
        self.assertEqual(clean_inference_source("ollama"), "Local Ollama")
        self.assertEqual(clean_inference_source("deterministic"), "Deterministic Fallback")

    def test_sanitize_ui_text(self):
        raw1 = "Model powered by NVIDIA NIM Cloud API backend."
        sanitized1 = sanitize_ui_text(raw1)
        self.assertNotIn("NVIDIA", sanitized1)
        self.assertNotIn("NIM", sanitized1)
        self.assertIn("Enterprise Cloud AI", sanitized1)

        raw2 = "Inference conducted on NIVIDIA supercluster."
        sanitized2 = sanitize_ui_text(raw2)
        self.assertNotIn("NIVIDIA", sanitized2)


if __name__ == "__main__":
    unittest.main()

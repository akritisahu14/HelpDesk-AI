"""
Synthetic sample tickets for testing and demonstration in HelpDesk AI.
Covers Network, Access, Hardware, Software, and Security incident scenarios.
"""

from typing import List, Dict, Any

SAMPLE_TICKETS: List[Dict[str, Any]] = [
    {
        "id": "INC-1001",
        "name": "1. Corporate VPN Failure",
        "title": "Cannot connect to corporate VPN after network upgrade",
        "description": "Ever since this morning, AnyConnect client keeps getting stuck on 'Contacting gateway...' and then times out with error 'Secure Gateway unreachable'. I am remote today and cannot access internal intranet or source code repositories.",
        "impact": "One user",
        "urgency": "Work blocked",
        "expected_category": "Network",
        "expected_priority": "High",
        "expected_kb_id": "KB-NET-001",
        "reporter_email": "staff.vpn@enterprise.internal",
        "reporter_name": "Marcus Vance"
    },
    {
        "id": "INC-1002",
        "name": "2. AD / SSO Password Lockout",
        "title": "Account locked out after expired password attempt",
        "description": "My corporate Active Directory password expired yesterday. I tried logging in with my old password 3 times on my workstation and now the system says 'Your account has been locked. Please contact your system administrator.' I cannot log into my workstation or webmail.",
        "impact": "One user",
        "urgency": "Work blocked",
        "expected_category": "Access",
        "expected_priority": "High",
        "expected_kb_id": "KB-ACC-002",
        "reporter_email": "staff.ad@enterprise.internal",
        "reporter_name": "Sarah Jenkins"
    },
    {
        "id": "INC-1003",
        "name": "3. Laptop Overheating & Thermal Shutdown",
        "title": "Laptop fan running at maximum speed, chassis hot, spontaneous shutdown",
        "description": "My laptop fan has been blasting at maximum speed for the past two hours. The underside of the chassis is burning hot to the touch. It abruptly shut down twice while I was compiling our project. There is a slight smell of warm plastic.",
        "impact": "One user",
        "urgency": "Work impaired",
        "expected_category": "Hardware",
        "expected_priority": "Medium",
        "expected_kb_id": "KB-HW-003",
        "reporter_email": "staff.hw@enterprise.internal",
        "reporter_name": "David Cho"
    },
    {
        "id": "INC-1004",
        "name": "4. Slow Email Sync & Freezing Outlook",
        "title": "Outlook taking 5+ minutes to send emails, inbox freezing regularly",
        "description": "Microsoft Outlook has become unresponsive since yesterday. New incoming emails are delayed by 15-20 minutes, search hangs with a spinning wheel, and sending an email with a small attachment freezes the window for several minutes.",
        "impact": "One user",
        "urgency": "Work impaired",
        "expected_category": "Software",
        "expected_priority": "Medium",
        "expected_kb_id": "KB-SFT-004",
        "reporter_email": "staff.sft@enterprise.internal",
        "reporter_name": "Emily Watson"
    },
    {
        "id": "INC-1005",
        "name": "5. Phishing & Credential Exposure Incident",
        "title": "Clicked link in urgent unpaid invoice email and typed password",
        "description": "I received an urgent email claiming to be from Accounting regarding an overdue invoice. I clicked the PDF link which took me to a login page resembling Microsoft 365. I entered my full corporate email and password before realizing the URL was actually 'ms-verify-security-login.xyz'.",
        "impact": "Business-critical service",
        "urgency": "Work blocked",
        "expected_category": "Security",
        "expected_priority": "Critical",
        "expected_kb_id": "KB-SEC-005",
        "reporter_email": "staff.sec@enterprise.internal",
        "reporter_name": "Robert Chen"
    },
    {
        "id": "INC-1006",
        "name": "6. Shared Drive Access Denied (RBAC)",
        "title": "Access denied error when accessing Finance Shared Folder on network drive",
        "description": "I recently transferred to the FP&A team and need access to the quarterly forecast spreadsheets on the departmental shared drive \\\\corp-files\\finance\\2026. Whenever I attempt to open the folder, Windows throws 'Access is Denied. You do not have permission'.",
        "impact": "One user",
        "urgency": "Minor inconvenience",
        "expected_category": "Access",
        "expected_priority": "Low",
        "expected_kb_id": "KB-ACC-008",
        "reporter_email": "staff.finance@enterprise.internal",
        "reporter_name": "Jessica Taylor"
    },
    {
        "id": "INC-1007",
        "name": "7. External Monitor & USB-C Dock Blank",
        "title": "Dual external monitors not recognized via Thunderbolt USB-C docking station",
        "description": "When plugging my laptop into the workstation USB-C dock, the keyboard and mouse work, but both external HDMI monitors remain in power-saving black screen mode. Windows Display settings shows 'No display detected'.",
        "impact": "One user",
        "urgency": "Work impaired",
        "expected_category": "Hardware",
        "expected_priority": "Medium",
        "expected_kb_id": "KB-HW-009",
        "reporter_email": "staff.dock@enterprise.internal",
        "reporter_name": "Daniel Miller"
    },
    {
        "id": "INC-1008",
        "name": "8. Ransomware / Encrypted Files Alert",
        "title": "Files on local drive renamed to .locked and ransom note popped up",
        "description": "An unusual popup appeared on my screen stating that all personal and corporate documents have been encrypted. File extensions in my Documents folder now end with .locked and there is a README_DECRYPT text file on my desktop.",
        "impact": "Business-critical service",
        "urgency": "Work blocked",
        "expected_category": "Security",
        "expected_priority": "Critical",
        "expected_kb_id": "KB-SEC-010",
        "reporter_email": "staff.alert@enterprise.internal",
        "reporter_name": "Amanda White"
    }
]

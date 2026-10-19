"""
Knowledge Base for HelpDesk AI
Contains curated enterprise IT troubleshooting Standard Operating Procedures (SOPs)
and search retrieval functions.
"""

from typing import List, Dict, Any, Optional
import re


# Curated IT Troubleshooting Knowledge Base
KB_ARTICLES: List[Dict[str, Any]] = [
    {
        "id": "KB-NET-001",
        "title": "Corporate VPN Connection Failure & Gateway Timeout",
        "category": "Network",
        "keywords": ["vpn", "tunnel", "anyconnect", "gateway", "cisco", "network", "remote access", "split tunneling", "ipsec"],
        "summary": "Steps to resolve VPN handshake failures, certificate errors, and gateway connection timeouts.",
        "steps": [
            "1. Verify local internet connectivity by pinging public DNS (e.g., 8.8.8.8) or opening a public webpage.",
            "2. Restart the VPN client application completely (close from system tray or task manager).",
            "3. Disconnect from guest Wi-Fi and reconnect to secure home or enterprise Wi-Fi.",
            "4. Flush local DNS cache via terminal (`ipconfig /flushdns` on Windows or `sudo dscacheutil -flushcache` on macOS).",
            "5. If using MFA for VPN, verify the push notification on your authenticator device hasn't expired.",
            "6. If the error persists with 'Gateway unreachable', verify VPN endpoint address with Network Operations."
        ]
    },
    {
        "id": "KB-NET-006",
        "title": "DNS Resolution Failure & Local Network Gateway Issues",
        "category": "Network",
        "keywords": ["dns", "wifi", "internet", "gateway", "dhcp", "ip address", "offline", "connection", "unreachable", "ping"],
        "summary": "Diagnostics for resolving internal hostname resolution and local default gateway unreachable errors.",
        "steps": [
            "1. Verify IP configuration using `ipconfig /all` or `ifconfig` to ensure a valid DHCP lease was issued.",
            "2. Ping default local gateway to confirm physical LAN/Wi-Fi router connectivity.",
            "3. Test DNS resolution using `nslookup internal.corp.net` against corporate DNS servers.",
            "4. Reset network adapter via OS Network Diagnostics troubleshooter.",
            "5. Release and renew DHCP lease using `ipconfig /release` followed by `ipconfig /renew`."
        ]
    },
    {
        "id": "KB-ACC-002",
        "title": "Active Directory & Enterprise SSO Password Reset Procedure",
        "category": "Access",
        "keywords": ["password", "login", "reset", "lockout", "active directory", "sso", "credentials", "account locked", "expired password"],
        "summary": "Standard operating procedure for self-service password reset and unlocking accounts without sharing credentials.",
        "steps": [
            "1. Direct user to the company Self-Service Password Reset (SSPR) portal (https://identity.corp.local/sspr).",
            "2. Complete Multi-Factor Authentication (MFA) challenge via registered authenticator app or hardware token.",
            "3. Enforce password complexity: at least 14 characters, uppercase, lowercase, numbers, and symbols.",
            "4. NEVER request the user's password or temporary passcodes over chat, ticket, or phone.",
            "5. If account is locked due to bad attempts, allow the 15-minute lockout timer to expire or verify identity before manual unlock in Admin Center.",
            "6. Advise user to update stored credentials on mobile devices and saved browser sessions."
        ]
    },
    {
        "id": "KB-ACC-008",
        "title": "Role-Based Access Control (RBAC) & Shared Drive Permissions",
        "category": "Access",
        "keywords": ["permission", "access denied", "shared drive", "folder", "rbac", "security group", "ad group", "onedrive", "sharepoint"],
        "summary": "Procedure for evaluating folder access denials, security group membership, and manager approval workflows.",
        "steps": [
            "1. Verify the exact file share or SharePoint path that triggered the 'Access Denied' error.",
            "2. Confirm the user's Department and Cost Center match the target security group requirements.",
            "3. Direct user to Identity Access Management portal to request access with Manager sign-off.",
            "4. Once approved by resource owner, add user AD account to the appropriate security group.",
            "5. User must log off and log back in (or run `klist purge`) to refresh Active Directory Kerberos token."
        ]
    },
    {
        "id": "KB-HW-003",
        "title": "Laptop Thermal Throttling, High Fan Speed & Overheating",
        "category": "Hardware",
        "keywords": ["overheating", "hot", "fan", "thermal", "throttling", "shutdown", "laptop", "battery", "cpu 100%"],
        "summary": "Troubleshooting excessive fan noise, thermal shutdown, and runaway processes causing high temperatures.",
        "steps": [
            "1. Inspect physical vents: Ensure the laptop is on a hard, flat surface and air intake/exhaust ports are not obstructed.",
            "2. Open Task Manager (Windows: Ctrl+Shift+Esc, macOS: Activity Monitor) and inspect CPU utilization to identify runaway processes.",
            "3. Close high-overhead background processes (e.g., duplicate browser processes, background indexing).",
            "4. Perform a clean shutdown and power cycle; disconnect external docks or unapproved high-wattage chargers.",
            "5. Update BIOS and thermal management firmware via enterprise OEM updater tool.",
            "6. If chassis remains excessively hot to the touch or battery shows bulging, immediately shut down and escalate to Desktop Hardware Support for physical inspection."
        ]
    },
    {
        "id": "KB-HW-009",
        "title": "External Monitor & USB-C Docking Station Not Detected",
        "category": "Hardware",
        "keywords": ["monitor", "display", "dock", "usb-c", "hdmi", "displayport", "screen", "second screen", "peripherals", "docking"],
        "summary": "Resolution steps for external display blank screens, docking station disconnects, and video output issues.",
        "steps": [
            "1. Power-cycle the docking station by disconnecting power cable for 30 seconds before reconnecting.",
            "2. Reseat USB-C host cable and verify connection directly to Thunderbolt / DisplayPort-enabled port on laptop.",
            "3. Test display toggle key (`Win + P` on Windows) and set display mode to 'Extend'.",
            "4. Reseat physical HDMI or DisplayPort cables directly between monitor and dock.",
            "5. Verify and update OEM display adapter and Thunderbolt dock firmware drivers."
        ]
    },
    {
        "id": "KB-SFT-004",
        "title": "Email Client (Outlook / Mail) Slow Synchronization & Freezing",
        "category": "Software",
        "keywords": ["email", "outlook", "slow", "sync", "inbox", "freezing", "pst", "ost", "exchange", "office 365", "mailbox"],
        "summary": "Resolution steps for lagging email clients, stuck outbox items, and local mailbox cache corruption.",
        "steps": [
            "1. Test webmail access (e.g., outlook.office.com) to verify mailbox health on the server side.",
            "2. Launch Outlook in Safe Mode (`outlook.exe /safe`) to rule out misbehaving third-party COM add-ins.",
            "3. Disable unnecessary add-ins via File > Options > Add-ins.",
            "4. Compact and repair local data file (.OST) via Account Settings > Data Files > Settings > Compact Now.",
            "5. Rebuild email search index via Windows Indexing Options if search results are hanging.",
            "6. Verify local disk space; low storage (<5GB free) degrades local cache performance."
        ]
    },
    {
        "id": "KB-SFT-007",
        "title": "Software Application Crash and Corrupted Local Cache",
        "category": "Software",
        "keywords": ["crash", "freezing", "app", "application", "error code", "corrupt", "cache", "uninstall", "exception", "freeze"],
        "summary": "General application troubleshooting for recurring crashes and cache corruption.",
        "steps": [
            "1. Check Windows Event Viewer or macOS Console for application crash log signatures and error codes.",
            "2. Clear application-specific cache under `%LocalAppData%` or `~/Library/Caches`.",
            "3. Run application as administrator or verify file permissions.",
            "4. Reinstall the latest verified version from Company Self-Service Software Center.",
            "5. Verify system meets memory and prerequisites."
        ]
    },
    {
        "id": "KB-SEC-005",
        "title": "Suspected Phishing, Malicious Link Click & Credential Exposure Incident",
        "category": "Security",
        "keywords": ["phishing", "suspicious", "credential", "compromised", "malicious link", "invoice", "hack", "spam", "security incident", "password exposed"],
        "summary": "Critical containment and reporting protocols for phishing clicks and suspected account compromise.",
        "steps": [
            "1. IMMEDIATE CONTAINMENT: Disconnect the endpoint from the network (unplug Ethernet, disconnect Wi-Fi) to prevent lateral spread.",
            "2. DO NOT delete the suspicious email; it is needed by SecOps / SOC for email header analysis and threat hunting.",
            "3. If credentials were entered on a third-party link, immediately initiate an emergency password reset and revoke all active session tokens via Identity Provider.",
            "4. Submit the phishing URL or email attachment to the Security Operations Center (soc-incident@corp.local).",
            "5. MANDATORY ESCALATION: All credential compromise incidents must be escalated to the Tier-2 Security Incident Response Team immediately.",
            "6. Run a full endpoint antivirus / EDR scan."
        ]
    },
    {
        "id": "KB-SEC-010",
        "title": "Endpoint Malware Infection, Ransomware Alert & Immediate Containment",
        "category": "Security",
        "keywords": ["malware", "ransomware", "virus", "trojan", "encrypted", "ransom", "infected", "edr", "antivirus", "malicious executable"],
        "summary": "Emergency containment protocol for ransomware, active malware, and unauthorized executable execution.",
        "steps": [
            "1. IMMEDIATE ISOLATION: Unplug Ethernet cable and power off Wi-Fi immediately. Do NOT restart the machine.",
            "2. Document visible popups, ransom notes, altered file extensions, or abnormal background processes.",
            "3. Notify Security Operations Center (SOC) hotline immediately (ext. 5555 / soc-urgent@corp.local).",
            "4. Do NOT attempt to pay ransoms or run unapproved third-party decryption utilities.",
            "5. SecOps will dispatch endpoint isolation via EDR console and initiate forensic memory capture."
        ]
    }
]


def get_article_by_id(article_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves an article by its canonical ID."""
    for article in KB_ARTICLES:
        if article["id"].upper() == article_id.strip().upper():
            return article
    return None


def search_knowledge_base(query: str, category_hint: Optional[str] = None, top_k: int = 2) -> List[Dict[str, Any]]:
    """
    Searches the IT knowledge base using token overlap (set intersection) and keyword weighting.
    Note: Uses keyword weighting and token overlap; does NOT use TF-IDF or cosine similarity.
    Returns the top_k most relevant articles.
    If no relevant articles match, returns an empty list (enabling insufficient evidence detection).
    """
    if not query or not query.strip():
        return []

    tokens = set(re.findall(r"\w+", query.lower()))
    query_lower = query.lower()
    scored_articles = []
    stop_words = {"the", "a", "an", "is", "for", "and", "in", "with", "to", "of", "on", "at", "my", "or", "test", "routing"}

    for article in KB_ARTICLES:
        score = 0
        art_text = (article["title"] + " " + article["summary"]).lower()
        art_tokens = set(re.findall(r"\w+", art_text))
        
        # Keyword matches: phrase match in query OR exact keyword token match
        kw_matches = sum(
            1 for kw in article["keywords"]
            if kw.lower() in query_lower or kw.lower() in tokens
        )
        
        # Word overlap score (excluding stop words)
        overlap = len(tokens.intersection(art_tokens) - stop_words)
        score += overlap * 2 + kw_matches * 5

        # Category bonus only if some textual match exists
        if score > 0 and category_hint and article["category"].lower() == category_hint.lower():
            score += 4

        # Meaningful relevance threshold (score >= 6)
        if score >= 6:
            scored_articles.append((score, article))

    # Sort descending by score
    scored_articles.sort(key=lambda x: x[0], reverse=True)

    if scored_articles:
        return [item[1] for item in scored_articles[:top_k]]

    # If nothing matched with sufficient confidence, return empty list
    return []

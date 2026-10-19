"""
Script to generate the enterprise presentation for HelpDesk AI.
Outputs: HelpDesk_AI_Presentation.pptx
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def create_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Color Palette - Modern Dark Cyber/Enterprise
    BG_COLOR = RGBColor(10, 15, 29)         # #0A0F1D deep dark navy
    CARD_BG = RGBColor(17, 24, 39)          # #111827 dark slate
    CARD_BORDER = RGBColor(31, 41, 55)      # #1F2937 border
    CYAN_ACCENT = RGBColor(56, 189, 248)    # #38BDF8 vibrant cyan
    INDIGO_ACCENT = RGBColor(99, 102, 241)  # #6366F1 vibrant indigo
    EMERALD_ACCENT = RGBColor(16, 185, 129) # #10B981 emerald green
    AMBER_ACCENT = RGBColor(245, 158, 11)   # #F59E0B warning amber
    RED_ACCENT = RGBColor(239, 68, 68)      # #EF4444 danger red
    WHITE = RGBColor(248, 250, 252)         # #F8FAFC crisp white
    MUTED = RGBColor(148, 163, 184)         # #94A3B8 light slate text
    LIGHT_TEXT = RGBColor(226, 232, 240)    # #E2E8F0 secondary text

    def set_slide_background(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = BG_COLOR
        bg.line.fill.background()
        return bg

    def add_header(slide, tag_text, title_text, subtitle_text):
        # Tag Badge
        tag_box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.5), Inches(2.2), Inches(0.35))
        tag_box.fill.solid()
        tag_box.fill.fore_color.rgb = RGBColor(30, 41, 59)
        tag_box.line.color.rgb = CYAN_ACCENT
        tag_box.line.width = Pt(1)
        tf_tag = tag_box.text_frame
        tf_tag.word_wrap = True
        p_tag = tf_tag.paragraphs[0]
        p_tag.text = tag_text.upper()
        p_tag.font.size = Pt(10)
        p_tag.font.bold = True
        p_tag.font.color.rgb = CYAN_ACCENT
        p_tag.alignment = PP_ALIGN.CENTER

        # Main Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.85), Inches(11.7), Inches(0.65))
        tf = title_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = title_text
        p.font.size = Pt(24)
        p.font.bold = True
        p.font.color.rgb = WHITE

        # Subtitle
        sub_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.48), Inches(11.7), Inches(0.45))
        tf_sub = sub_box.text_frame
        tf_sub.word_wrap = True
        tf_sub.margin_left = tf_sub.margin_top = tf_sub.margin_right = tf_sub.margin_bottom = 0
        p_sub = tf_sub.paragraphs[0]
        p_sub.text = subtitle_text
        p_sub.font.size = Pt(13)
        p_sub.font.color.rgb = MUTED

    def add_card(slide, left, top, width, height, title, subtitle="", border_color=CARD_BORDER, bg_color=CARD_BG):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1.2)
        tf = card.text_frame
        tf.word_wrap = True
        tf.margin_left = Inches(0.25)
        tf.margin_right = Inches(0.25)
        tf.margin_top = Inches(0.2)
        tf.margin_bottom = Inches(0.2)
        
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = WHITE
        
        if subtitle:
            p2 = tf.add_paragraph()
            p2.text = subtitle
            p2.font.size = Pt(11)
            p2.font.color.rgb = CYAN_ACCENT
            p2.space_before = Pt(3)
            
        return card, tf

    # ==========================================
    # SLIDE 1: Title Slide
    # ==========================================
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_background(s1)

    # Decorative background glowing shapes
    glow = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.8), Inches(11.733), Inches(5.9))
    glow.fill.solid()
    glow.fill.fore_color.rgb = RGBColor(15, 23, 42)
    glow.line.color.rgb = RGBColor(30, 41, 59)
    glow.line.width = Pt(1.5)

    # Badge
    b1 = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.3), Inches(1.4), Inches(3.6), Inches(0.42))
    b1.fill.solid()
    b1.fill.fore_color.rgb = RGBColor(17, 24, 39)
    b1.line.color.rgb = CYAN_ACCENT
    b1.line.width = Pt(1)
    tf_b1 = b1.text_frame
    p = tf_b1.paragraphs[0]
    p.text = "ENTERPRISE IT SERVICE MANAGEMENT (ITSM)"
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = CYAN_ACCENT
    p.alignment = PP_ALIGN.CENTER

    # Title
    t1_box = s1.shapes.add_textbox(Inches(1.3), Inches(2.0), Inches(10.5), Inches(1.2))
    tf1 = t1_box.text_frame
    tf1.word_wrap = True
    p1 = tf1.paragraphs[0]
    p1.text = "HelpDesk AI"
    p1.font.size = Pt(44)
    p1.font.bold = True
    p1.font.color.rgb = WHITE

    # Subtitle
    sub1_box = s1.shapes.add_textbox(Inches(1.3), Inches(2.85), Inches(10.5), Inches(0.9))
    tf1_sub = sub1_box.text_frame
    tf1_sub.word_wrap = True
    p1_sub = tf1_sub.paragraphs[0]
    p1_sub.text = "Autonomous Multi-Agent Incident Triage, SOP-Grounded Retrieval & Safety-Guarded ITIL Routing"
    p1_sub.font.size = Pt(18)
    p1_sub.font.color.rgb = CYAN_ACCENT

    desc1_box = s1.shapes.add_textbox(Inches(1.3), Inches(3.8), Inches(10.5), Inches(0.8))
    tf1_desc = desc1_box.text_frame
    tf1_desc.word_wrap = True
    p1_desc = tf1_desc.paragraphs[0]
    p1_desc.text = "An intelligent, privacy-preserving incident management copilot orchestrating LangGraph multi-agents, local Ollama LLMs, deterministic ITIL matrices, and zero-trust safety guardrails."
    p1_desc.font.size = Pt(13)
    p1_desc.font.color.rgb = MUTED

    # Feature pills
    pills = [
        ("LangGraph Multi-Agent Architecture", INDIGO_ACCENT),
        ("Flexible Privacy LLM (Ollama / NIM)", CYAN_ACCENT),
        ("ITIL 4-Tier Deterministic Priority", EMERALD_ACCENT),
        ("Critic Safety Guardrails", AMBER_ACCENT),
    ]
    pill_w = Inches(2.55)
    pill_gap = Inches(0.18)
    pill_left = Inches(1.3)
    for title_p, col_p in pills:
        pill = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, pill_left, Inches(4.7), pill_w, Inches(0.65))
        pill.fill.solid()
        pill.fill.fore_color.rgb = RGBColor(17, 24, 39)
        pill.line.color.rgb = col_p
        pill.line.width = Pt(1.2)
        tf_p = pill.text_frame
        tf_p.word_wrap = True
        tf_p.margin_left = tf_p.margin_right = Inches(0.1)
        p = tf_p.paragraphs[0]
        p.text = title_p
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = LIGHT_TEXT
        p.alignment = PP_ALIGN.CENTER
        pill_left += pill_w + pill_gap

    # Footer
    f1_box = s1.shapes.add_textbox(Inches(1.3), Inches(5.8), Inches(10.5), Inches(0.5))
    tf1_f = f1_box.text_frame
    p_f = tf1_f.paragraphs[0]
    p_f.text = "System Architecture & Engineering Defense Presentation  |  Powered by LangGraph & Streamlit"
    p_f.font.size = Pt(11)
    p_f.font.color.rgb = MUTED

    s1.notes_slide.notes_text_frame.text = (
        "Welcome everyone. Today we are presenting HelpDesk AI — an enterprise-grade IT Service Management (ITSM) "
        "multi-agent system designed to automate incident triage, retrieve verified standard operating procedures, "
        "generate safe troubleshooting guidance, and enforce ITIL escalation policies with zero data leaks."
    )

    # ==========================================
    # SLIDE 2: Problem Statement & Industry Challenges
    # ==========================================
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_background(s2)
    add_header(s2, "Challenge & Motivation", "Problem Statement: The IT Service Desk Dilemma", 
               "Enterprise support teams are overwhelmed by ticket volume, high MTTR, and the hazards of ungrounded generative AI.")

    card_defs_s2 = [
        {
            "title": "1. Crushing Ticket Volume & Burnout",
            "subtitle": "Fatigue & Delayed First Response",
            "points": [
                "Over 65% of enterprise tickets are repetitive L1 inquiries (VPN disconnects, password lockouts, driver conflicts).",
                "Human support technicians spend hours manually reviewing, tagging, and categorizing incoming tickets.",
                "High agent cognitive load leads to ticket queue bottlenecks and frequent SLA violations."
            ],
            "accent": CYAN_ACCENT
        },
        {
            "title": "2. Prolonged MTTR & Misrouting",
            "subtitle": "Inefficient Escalation Paths",
            "points": [
                "Tickets bounce between Tier 1, Tier 2, and specialized networking or sysadmin queues.",
                "Average Mean Time to Resolve (MTTR) stretches from minutes to days due to misclassification.",
                "Subjective human priority tagging distorts true business impact vs urgency."
            ],
            "accent": INDIGO_ACCENT
        },
        {
            "title": "3. Knowledge Inconsistency & Gaps",
            "subtitle": "Bypassed SOPs & Fragmented Data",
            "points": [
                "Technicians frequently rely on tribal knowledge rather than verified Knowledge Base (KB) SOPs.",
                "Disparate, unstandardized troubleshooting steps create inconsistent end-user experiences.",
                "No automated validation that advice strictly follows enterprise compliance policies."
            ],
            "accent": AMBER_ACCENT
        },
        {
            "title": "4. The Pitfalls of Naive AI & Hallucination",
            "subtitle": "Security, Compliance & Hallucinations",
            "points": [
                "Off-the-shelf generative AI hallucinates destructive commands (e.g., recursive deletion, disabling firewalls).",
                "Critical phishing or ransomware threats may be miscategorized as harmless software bugs.",
                "Data privacy risk: Sending confidential internal telemetry to public cloud AI APIs without disclosure."
            ],
            "accent": RED_ACCENT
        }
    ]

    cw = Inches(5.65)
    ch = Inches(2.25)
    coords = [
        (Inches(0.8), Inches(2.15)),
        (Inches(6.88), Inches(2.15)),
        (Inches(0.8), Inches(4.65)),
        (Inches(6.88), Inches(4.65))
    ]

    for idx, cdef in enumerate(card_defs_s2):
        left, top = coords[idx]
        card, tf = add_card(s2, left, top, cw, ch, cdef["title"], cdef["subtitle"], border_color=cdef["accent"])
        for pt in cdef["points"]:
            p = tf.add_paragraph()
            p.text = f"• {pt}"
            p.font.size = Pt(11)
            p.font.color.rgb = LIGHT_TEXT
            p.space_before = Pt(4)

    s2.notes_slide.notes_text_frame.text = (
        "On slide 2, we highlight the four major pain points modern enterprises face. First, human agents spend 65% of their "
        "time on repetitive L1 tickets, leading to burnout. Second, manual classification causes misrouting and inflates MTTR. "
        "Third, tribal knowledge replaces standard operating procedures. Fourth, and most crucially, unguided generative AI "
        "can hallucinate destructive shell commands or fail to route ransomware breaches to human analysts. "
        "HelpDesk AI was engineered specifically to address these challenges with strict deterministic guardrails."
    )

    # ==========================================
    # SLIDE 3: Domain Details - Enterprise ITSM & ITIL
    # ==========================================
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_background(s3)
    add_header(s3, "Domain Context & Methodology", "Domain Framework: Enterprise ITSM & ITIL Standards",
               "Grounding incident management in formal ITIL v4 matrices, structured taxonomies, and strict policy tiers.")

    # 3 Column layout
    col_w = Inches(3.7)
    col_h = Inches(4.75)
    
    # Col 1: Taxonomy & Ingestion
    c1, tf1 = add_card(s3, Inches(0.8), Inches(2.15), col_w, col_h, 
                       "1. Incident Taxonomy", "Standardized Categorization", border_color=CYAN_ACCENT)
    c1_content = [
        ("Network", "VPN drops, gateway unreachable, DNS resolution failures, Wi-Fi connectivity."),
        ("Hardware", "Peripheral failure, dock station disconnect, battery degradation, display faults."),
        ("Software", "Application crashes, Office 365 licensing, corrupted installations, OS patches."),
        ("Access", "Active Directory lockout, SSO expired, MFA resets, permission escalation."),
        ("Security", "Phishing, credential exposure, malware alerts, ransomware indicators.")
    ]
    for tag, desc in c1_content:
        p_t = tf1.add_paragraph()
        p_t.text = f"[{tag}]"
        p_t.font.size = Pt(11)
        p_t.font.bold = True
        p_t.font.color.rgb = CYAN_ACCENT
        p_t.space_before = Pt(8)
        
        p_d = tf1.add_paragraph()
        p_d.text = desc
        p_d.font.size = Pt(10.5)
        p_d.font.color.rgb = LIGHT_TEXT

    # Col 2: ITIL Priority Matrix
    c2, tf2 = add_card(s3, Inches(4.8), Inches(2.15), col_w, col_h, 
                       "2. ITIL Priority Matrix", "Impact × Urgency Computation", border_color=INDIGO_ACCENT)
    c2_points = [
        "Rigorous 4-Tier Priority Engine:",
        "• Critical (P1): Business-critical service down OR active security incident with work blocked.",
        "• High (P2): Multiple users blocked OR business service impaired OR single user work blocked.",
        "• Medium (P3): One user impaired OR multiple users with minor inconvenience.",
        "• Low (P4): Single user minor inconvenience (e.g., cosmetic UI issue, how-to request).",
        "Mandatory Security Override:",
        "Security incidents can NEVER be downgraded to Medium or Low. They are automatically locked into High or Critical."
    ]
    for pt in c2_points:
        p = tf2.add_paragraph()
        p.text = pt
        p.font.size = Pt(10.5)
        p.font.color.rgb = AMBER_ACCENT if "Security Override" in pt else LIGHT_TEXT
        if "Rigorous" in pt or "Mandatory" in pt:
            p.font.bold = True
            p.space_before = Pt(8)
        else:
            p.space_before = Pt(3)

    # Col 3: Escalation Pathways & Guardrails
    c3, tf3 = add_card(s3, Inches(8.8), Inches(2.15), col_w, col_h, 
                       "3. Tier Routing & Non-Closure", "Structured Operational Hierarchy", border_color=EMERALD_ACCENT)
    c3_points = [
        ("Tier 1 Automated Advisory", "Ticket matches verified KB SOP and passes safety audit. Clear, non-destructive steps provided."),
        ("Tier 2 Specialist Support", "Triggered if KB lacks verified SOP evidence or if incident requires physical hands-on hardware service."),
        ("SecOps Incident Response", "Mandatory human review routing to Tier 2/3 SOC team for active phishing, token theft, or malware."),
        ("Strict Non-Closure Rule", "System NEVER marks tickets 'Closed' or 'Resolved'. It offers guidance, requiring human technician validation.")
    ]
    for title_p, desc_p in c3_points:
        p_t = tf3.add_paragraph()
        p_t.text = f"• {title_p}"
        p_t.font.size = Pt(11)
        p_t.font.bold = True
        p_t.font.color.rgb = EMERALD_ACCENT if "Tier 1" in title_p else (RED_ACCENT if "SecOps" in title_p else WHITE)
        p_t.space_before = Pt(8)
        
        p_d = tf3.add_paragraph()
        p_d.text = desc_p
        p_d.font.size = Pt(10.5)
        p_d.font.color.rgb = LIGHT_TEXT

    s3.notes_slide.notes_text_frame.text = (
        "Slide 3 covers the enterprise domain foundation. HelpDesk AI is not a generic chatbot; it is built on ITIL v4 principles. "
        "We categorize tickets into 5 standard domains plus Other. We implement the formal ITIL priority matrix computing Impact and Urgency. "
        "Notice our strict security rule: any phishing, malware, or credential leak is locked into High or Critical priority and immediately routed "
        "to human SecOps analysts. Furthermore, unlike rogue bots that prematurely mark tickets resolved, our policy engine enforces that AI provides advisory guidance "
        "while human operators retain final closure authority."
    )

    # ==========================================
    # SLIDE 4: Architecture Diagram & Multi-Agent Flow
    # ==========================================
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_background(s4)
    add_header(s4, "System Design & Orchestration", "System Architecture: LangGraph Multi-Agent Pipeline",
               "Five specialized cooperating nodes with a bounded feedback loop and deterministic security hooks.")

    # Multi-Agent Workflow Horizontal Flow Visual
    nodes = [
        ("1. Triage Agent", "Regex Security Check\n+ ITIL Matrix Classifier", CYAN_ACCENT),
        ("2. Retrieval Agent", "Keyword & Token Match\nOver Verified KB SOPs", INDIGO_ACCENT),
        ("3. Resolution Agent", "Grounds Troubleshooting\nFrom Matched SOP", EMERALD_ACCENT),
        ("4. Critic Agent", "Safety Gatekeeper &\nBounded Feedback Loop", AMBER_ACCENT),
        ("5. Policy Router", "SecOps Human Review vs\nTier 2 vs Advisory Guidance", RED_ACCENT),
    ]

    node_w = Inches(2.15)
    node_h = Inches(1.35)
    start_x = Inches(0.8)
    gap = Inches(0.24)
    y_pos = Inches(2.15)

    for i, (name, role, col) in enumerate(nodes):
        x = start_x + i * (node_w + gap)
        box = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y_pos, node_w, node_h)
        box.fill.solid()
        box.fill.fore_color.rgb = RGBColor(17, 24, 39)
        box.line.color.rgb = col
        box.line.width = Pt(1.5)
        
        tf = box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = Inches(0.1)
        tf.margin_top = Inches(0.12)
        
        p = tf.paragraphs[0]
        p.text = name
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = col
        p.alignment = PP_ALIGN.CENTER
        
        p2 = tf.add_paragraph()
        p2.text = role
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = LIGHT_TEXT
        p2.alignment = PP_ALIGN.CENTER
        p2.space_before = Pt(4)

        # Arrow connector between nodes (except last)
        if i < len(nodes) - 1:
            arrow_x = x + node_w + Inches(0.04)
            arrow_y = y_pos + Inches(0.48)
            arrow = s4.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, arrow_x, arrow_y, Inches(0.16), Inches(0.3))
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = RGBColor(75, 85, 99)
            arrow.line.fill.background()

    # Lower Section: 2 Big Explanatory Cards
    lower_h = Inches(3.2)
    
    # Left Card: Core Orchestration Details
    card_l, tf_l = add_card(s4, Inches(0.8), Inches(3.75), Inches(5.65), lower_h,
                            "LangGraph State Machine Mechanics", "Deterministic State & Bounded Loop", border_color=INDIGO_ACCENT)
    mech_points = [
        "State Container: Single TypedDict carries ticket metadata, classification, retrieved articles, critique verdict, and execution logs.",
        "Security Pre-Filter: Security triggers bypass probabilistic LLM classification to guarantee SecOps human review dispatch.",
        "Bounded Feedback Loop: Critic audits proposed steps; on validation failure, a bounded loop triggers revision in Resolution node before escalating.",
        "Full Telemetry: Execution logs record millisecond timestamps, agent attribution (LLM vs Rule-based fallback), and diagnostic flags."
    ]
    for pt in mech_points:
        p = tf_l.add_paragraph()
        p.text = f"• {pt}"
        p.font.size = Pt(10.5)
        p.font.color.rgb = LIGHT_TEXT
        p.space_before = Pt(5)

    # Right Card: Technology Stack Breakdown
    card_r, tf_r = add_card(s4, Inches(6.88), Inches(3.75), Inches(5.65), lower_h,
                            "Technical Stack & Deployment", "Production-Ready Architecture", border_color=CYAN_ACCENT)
    stack_points = [
        ("Multi-Agent Framework", "LangGraph (StateGraph) for deterministic workflow choreography with feedback loops."),
        ("Inference Engine", "Dual-tier: Local Ollama (llama3.2:1b) or NVIDIA NIM Cloud API with rate limiting."),
        ("Knowledge Engine", "Keyword-weighted token overlap search with domain scoring and relevance thresholding."),
        ("Enterprise UI", "Streamlit with custom Dark SaaS CSS theme, live ticket workbench, and evaluation lab."),
        ("Guardrail Layer", "Dual-engine deterministic heuristic scanner + LLM Critic auditing.")
    ]
    for tag, desc in stack_points:
        p = tf_r.add_paragraph()
        p.text = f"• {tag}: "
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = WHITE
        p.space_before = Pt(4)
        
        # Append description inline
        run = p.add_run()
        run.text = desc
        run.font.bold = False
        run.font.color.rgb = LIGHT_TEXT

    s4.notes_slide.notes_text_frame.text = (
        "Slide 4 is the core architecture diagram. Our pipeline is structured as an explicit LangGraph StateGraph with 5 nodes. "
        "The ticket enters Node 1 (Triage) where regex catches instant security indicators, followed by ITIL classification. "
        "Node 2 retrieves verified corporate SOPs using token matching and keyword weighting. Node 3 generates step-by-step guidance grounded only in those SOPs. "
        "Node 4 is our safety gatekeeper, the Critic Agent, checking for dangerous shell scripts or credential requests. "
        "Crucially, if the Critic rejects a draft, a bounded feedback loop routes back to the Resolution node for revision. "
        "Finally, Node 5 routes the ticket according to security, priority, and critic approval. "
        "The system supports local Ollama for on-premise execution or NVIDIA NIM Cloud API with transparent UI disclosure."
    )

    # ==========================================
    # SLIDE 5: Key Features & Zero-Trust Safety
    # ==========================================
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_background(s5)
    add_header(s5, "Innovation & Safety", "Key Capabilities & Zero-Trust Guardrails",
               "Built with enterprise defense-in-depth: privacy transparency, deterministic fallbacks, and safety filters.")

    cw5 = Inches(5.65)
    ch5 = Inches(2.25)
    coords5 = [
        (Inches(0.8), Inches(2.15)),
        (Inches(6.88), Inches(2.15)),
        (Inches(0.8), Inches(4.65)),
        (Inches(6.88), Inches(4.65))
    ]

    card_defs_s5 = [
        {
            "title": "Flexible Privacy & Transparent Inference",
            "subtitle": "Data Residency by Architecture",
            "points": [
                "On-premise mode: Local Ollama execution guarantees internal ticket data never leaves the network.",
                "Cloud mode: NVIDIA NIM API provides high-capacity MoE inference with transparent UI disclosure.",
                "System never falsely claims local-only processing when cloud API calls are enabled."
            ],
            "accent": EMERALD_ACCENT
        },
        {
            "title": "Deterministic Fallback Architecture",
            "subtitle": "High Availability Under Any Fault",
            "points": [
                "Dual-layer design: Heuristic classifiers stand by if LLM backends fail or timeout.",
                "Keyword pattern matching and ITIL matrix tables guarantee 100% operational continuity.",
                "Source attribution clearly flags whether decisions were LLM-generated or Rule-fallback."
            ],
            "accent": CYAN_ACCENT
        },
        {
            "title": "Critic Agent Safety Gatekeeper",
            "subtitle": "Pre-Execution Command Interception",
            "points": [
                "Scans generated advice against 10+ dangerous command signatures.",
                "Blocks destructive commands (`rm -rf`, `format C:`, `drop database`).",
                "Strictly prohibits credential solicitation ('enter password here') and attempts to disable Windows Defender or firewalls."
            ],
            "accent": RED_ACCENT
        },
        {
            "title": "Full Diagnostic Tracing & Observability",
            "subtitle": "End-to-End Enterprise Auditability",
            "points": [
                "Detailed execution logs capture exact micro-timings, matched KB article IDs, and reasoning strings.",
                "Streamlit interactive tabs offer live inspection of Agent State, KB matches, and Critic audits.",
                "Empowers human tier 2/3 engineers with complete diagnostic context upon escalation."
            ],
            "accent": INDIGO_ACCENT
        }
    ]

    for idx, cdef in enumerate(card_defs_s5):
        left, top = coords5[idx]
        card, tf = add_card(s5, left, top, cw5, ch5, cdef["title"], cdef["subtitle"], border_color=cdef["accent"])
        for pt in cdef["points"]:
            p = tf.add_paragraph()
            p.text = f"• {pt}"
            p.font.size = Pt(11)
            p.font.color.rgb = LIGHT_TEXT
            p.space_before = Pt(4)

    s5.notes_slide.notes_text_frame.text = (
        "Slide 5 emphasizes our enterprise differentiators. Unlike generic AI wrappers, HelpDesk AI offers flexible privacy modes: "
        "either 100% local on-premise execution via Ollama or cloud-accelerated inference via NVIDIA NIM with full transparency. "
        "Second, our deterministic fallback engine ensures the service desk never fails even if both LLMs are offline. "
        "Third, our Critic Agent acts as an automated security officer with a bounded feedback loop, intercepting unsafe drafts "
        "before any user sees them."
    )

    # ==========================================
    # SLIDE 6: Evaluation, Business Impact & Roadmap
    # ==========================================
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_background(s6)
    add_header(s6, "Validation & Future Scope", "Evaluation Benchmarks, Business Impact & Roadmap",
               "Synthetic benchmark validation, modeled efficiency impact, and forward-looking integrations.")

    # Top Section: 3 Metric KPI Cards
    kpi_w = Inches(3.7)
    kpi_h = Inches(1.8)
    kpis = [
        ("100%", "Synthetic Benchmark Accuracy", "Verified across 16 curated synthetic boundary test cases", CYAN_ACCENT),
        ("100%", "Security Escalation Recall", "Zero missed phishing, malware, or credential exposure escalations to human SecOps", RED_ACCENT),
        ("Modeled", "Estimated Triage Acceleration", "Sub-2-second automated triage vs manual queue delay (synthetic estimate)", EMERALD_ACCENT),
    ]

    for idx, (stat, title_k, desc_k, col_k) in enumerate(kpis):
        left = Inches(0.8) + idx * (kpi_w + Inches(0.3))
        card = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, Inches(2.15), kpi_w, kpi_h)
        card.fill.solid()
        card.fill.fore_color.rgb = RGBColor(17, 24, 39)
        card.line.color.rgb = col_k
        card.line.width = Pt(1.5)
        
        tf = card.text_frame
        tf.word_wrap = True
        tf.margin_top = Inches(0.18)
        tf.margin_left = Inches(0.2)
        
        p = tf.paragraphs[0]
        p.text = stat
        p.font.size = Pt(32)
        p.font.bold = True
        p.font.color.rgb = col_k
        p.alignment = PP_ALIGN.CENTER
        
        p2 = tf.add_paragraph()
        p2.text = title_k
        p2.font.size = Pt(12)
        p2.font.bold = True
        p2.font.color.rgb = WHITE
        p2.alignment = PP_ALIGN.CENTER
        p2.space_before = Pt(2)

        p3 = tf.add_paragraph()
        p3.text = desc_k
        p3.font.size = Pt(9.5)
        p3.font.color.rgb = MUTED
        p3.alignment = PP_ALIGN.CENTER
        p3.space_before = Pt(2)

    # Bottom Section: 2 Wide Cards (Evaluation Dimensions & Future Roadmap)
    b_w = Inches(5.65)
    b_h = Inches(2.8)
    
    # Left: Evaluation Suite
    c_eval, tf_eval = add_card(s6, Inches(0.8), Inches(4.2), b_w, b_h,
                               "Built-in Empirical Evaluation Suite", "16 Synthetic Benchmark Dimensions", border_color=INDIGO_ACCENT)
    eval_dims = [
        "Category Classification Accuracy: Multi-class evaluation across 6 IT domains.",
        "ITIL Priority Matrix Precision: Verified mapping of impact and urgency parameters.",
        "Security Escalation Recall: Mandatory SecOps human review triggers tested against threat vectors (no automated device isolation).",
        "Critic Guardrail Pass/Fail: Robust detection of dangerous script injection and credential leaks.",
        "Synthetic Test Scope: Regression benchmark suite designed for safety auditing (not live production telemetry)."
    ]
    for pt in eval_dims:
        p = tf_eval.add_paragraph()
        p.text = f"• {pt}"
        p.font.size = Pt(10.5)
        p.font.color.rgb = LIGHT_TEXT
        p.space_before = Pt(3.5)

    # Right: Future Scope
    c_road, tf_road = add_card(s6, Inches(6.88), Inches(4.2), b_w, b_h,
                               "Future Scope & Enterprise Roadmap", "Next-Gen ITSM Evolutions", border_color=AMBER_ACCENT)
    roadmap_items = [
        ("Omnichannel Collaboration Bots", "Deploying native Slack and Microsoft Teams conversational interfaces for zero-friction user submission."),
        ("ITSM Platform Integrations", "Two-way webhook synchronization with ServiceNow, Jira Service Management, and Zendesk."),
        ("Automated Remediation Actions", "Safe execution of pre-approved remediation scripts (e.g. self-service AD account unlocking with approval)."),
        ("Dense Vector Embeddings RAG", "Future integration of dense vector embeddings (ChromaDB / Milvus) over dynamic intranet documentation.")
    ]
    for tag, desc in roadmap_items:
        p = tf_road.add_paragraph()
        p.text = f"• {tag}: "
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = WHITE
        p.space_before = Pt(3.5)
        
        run = p.add_run()
        run.text = desc
        run.font.bold = False
        run.font.color.rgb = LIGHT_TEXT

    s6.notes_slide.notes_text_frame.text = (
        "Finally, on slide 6, we review our empirical benchmarks and future roadmap. "
        "Through our built-in evaluation suite in evaluation.py, HelpDesk AI demonstrates 100% accuracy on our 16 synthetic benchmark cases "
        "and 100% recall on security incident human review escalation. These benchmarks provide deterministic regression prevention. "
        "Looking forward, our roadmap includes bidirectional Slack and Teams bots, ServiceNow synchronization, and dense vector embeddings. "
        "Thank you, and we'd love to take your questions!"
    )

    output_path = os.path.abspath("HelpDesk_AI_Presentation.pptx")
    prs.save(output_path)
    print(f"Presentation saved successfully to: {output_path}")

if __name__ == "__main__":
    create_deck()

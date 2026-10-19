# HelpDesk-AI: Enterprise IT Service Desk Copilot

An intelligent, privacy-preserving incident management copilot orchestrating **LangGraph** multi-agent workflows, local/cloud LLMs, deterministic **ITIL** matrices, and zero-trust safety guardrails.

---

## 🌟 Key Features & Architecture

### Multi-Agent Pipeline (`agents/`)
HelpDesk-AI executes a structured 5-stage incident triage and resolution graph built on **LangGraph**:

```
[Incident Submission]
        │
        ▼
   1. Triage Agent (Deterministic ITIL Priority & Category Classification)
        │
        ▼
   2. Retrieval Agent (Local Knowledge Base SOP Matching)
        │
        ▼
   3. Resolution Agent (Advisory Troubleshooting Steps Generation)
        │
        ▼
   4. Critic Agent (Zero-Trust Safety Audit & Compliance Guardrails)
        │
        ├─► [Safety/Compliance Failure] ──► (Bounded Feedback Revision Loop) ──┐
        │                                                                      │
        ▼                                                                      ▼
   5. Output Router (Policy Escalation Evaluation & Specialist Routing) ◄──────┘
```

1. **Triage Agent** (`agents/triage_agent.py`):
   - Categorizes incidents into `Network`, `Hardware`, `Software`, `Access`, `Security`, or `Other`.
   - Assigns priority (`Low`, `Medium`, `High`, `Critical`) strictly mapped to ITIL Impact × Urgency rules.
   - Enforces deterministic security triggers (e.g. phishing, compromised credentials, ransomware) that bypass LLM heuristics.

2. **Knowledge Retrieval Agent** (`agents/retrieval_agent.py`):
   - Queries the local approved IT Knowledge Base (`knowledge_base.py`) using weighted token relevance.
   - Filters results with a minimum confidence threshold to prevent hallucinated SOPs.

3. **Resolution Agent** (`agents/resolution_agent.py`):
   - Synthesizes clear, step-by-step advisory guidance citing verified Knowledge Base SOPs.
   - Operates in a bounded feedback loop with the Critic Agent when revisions are requested.
   - Gracefully falls back to deterministic SOP extraction if LLMs are offline.

4. **Critic Agent** (`agents/critic_agent.py`):
   - Audits proposed troubleshooting advice before delivery to users.
   - Rejects dangerous commands (`rm -rf`, `format c:`, security control disabling).
   - Rejects credential harvesting (e.g. asking users for passwords or PINs).
   - Rejects premature resolution claims (advisory steps only; tickets are never closed by AI).
   - Flags security incidents missing user network isolation or SecOps reporting guidance.

5. **Output Router** (`agents/orchestrator.py`):
   - Evaluates policy thresholds and routes incidents to internal specialist queues:
     - `SecOps Incident Response Team (Human Security Review Required)` for security threats.
     - `Priority Incident Command (Tier 2/3)` for critical business outages.
     - `Senior Service Desk Analyst (Human Review Required)` when safety checks reject automated advice.
     - `Tier 2 Technical Support (Specialized Review)` when approved KB evidence is insufficient.
     - `Tier 1 (Automated Guidance)` for standard approved SOP scenarios.

---

## 🔒 Security & Role-Based Access Control (RBAC)

- **Authentication (`auth.py`)**:
  - Compliant with NIST SP 800-132: PBKDF2-HMAC-SHA256 with 120,000 iterations.
  - Unique 16-byte cryptographically secure random salt per user.
  - Dynamic secret key management via `HELPDESK_AUTH_SECRET` environment variable or dynamically generated persistent `.auth_secret` (zero hard-coded fallback secrets).
  - Timing-safe password verification (`hmac.compare_digest`).
  - No automatic seeding of insecure demo accounts; databases start clean.
  - Server-side prevention of privileged role self-assignment: public registrations default strictly to unprivileged `Employee` access. Elevated privileges require administrative provisioning (`allow_privileged=True`).

- **Role Definitions (`rbac.py`)**:
  - **Employee (Incident Reporter)**: Strictly scoped to view and submit their own incidents and browse approved IT SOPs.
  - **IT Support (Service Desk Specialist)**: Operational incident queue oversight, triage workbench, interactive ticket resolution.
  - **Admin/SecOps (SecOps Incident Analyst / Administrator)**: Organization-wide metrics, active security incident containment queue, and synthetic benchmark evaluation.

- **Accurate Escalation & Resolution Representation**:
  - Advisory guidance is clearly distinguished from completed resolution.
  - AI never closes tickets automatically — resolution requires user or technician confirmation.
  - Internal human review escalations are accurately labeled without claiming external ticket dispatch (e.g. ServiceNow/Jira external dispatch is an unintegrated future roadmap item).

---

## 💻 Windows Setup & Run Instructions

### Prerequisites
- Windows 10 or 11 with PowerShell
- Python 3.10 to 3.12 installed and added to PATH
- (Optional) NVIDIA NIM API Key or local Ollama with `llama3.2:1b`

### 1. Open Project in PowerShell
Launch PowerShell and navigate to the project directory:
```powershell
Set-Location -Path "c:\Users\aakri\OneDrive\Desktop\HelpDesk-AI"
```

### 2. Create and Activate Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
> *Note:* If PowerShell script execution is restricted on your system, enable it for your current session:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> .\.venv\Scripts\Activate.ps1
> ```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure Environment Variables (Optional)
To use a custom authentication secret or enable cloud LLM acceleration:
```powershell
# Set custom authentication pepper (optional, a secure key is auto-generated if omitted)
$env:HELPDESK_AUTH_SECRET = "your-custom-secure-secret-key-here"

# Set NVIDIA NIM API key for cloud LLM inference (optional, falls back to Ollama or deterministic synthesis)
$env:NVIDIA_API_KEY = "nvapi-your-key-here"
```

### 5. Launch the Web Application
```powershell
streamlit run app.py
```
The application will open in your browser at `http://localhost:8501`.

---

## 🧪 Running Automated Tests & Benchmark Evaluation

### 1. Run All Automated Unit & Integration Tests
Execute the comprehensive test suite (60+ tests covering authentication, RBAC, multi-agent workflows, and safety guardrails):
```powershell
python -m unittest discover tests
```

### 2. Run Individual Test Modules
```powershell
# Authentication & security tests
python -m unittest tests.test_auth

# Multi-agent LangGraph workflow tests
python -m unittest tests.test_workflow

# RBAC & scoping tests
python -m unittest tests.test_rbac

# Core classification, KB retrieval, and safety tests
python -m unittest tests.test_helpdesk
```

### 3. Run the 16-Case Synthetic Benchmark Evaluation
Executes the deterministic regression benchmark:
```powershell
python evaluation.py
```

### 4. Generate the Executive Presentation Slide Deck
Generates the PowerPoint slide deck (`HelpDesk_AI_Presentation.pptx`):
```powershell
python generate_presentation.py
```

---

## 📁 Project Structure

```
HelpDesk-AI/
├── agents/                     # LangGraph Multi-Agent Package
│   ├── __init__.py             # Public agent interfaces and exports
│   ├── orchestrator.py         # StateGraph, node pipeline, bounded feedback, router
│   ├── triage_agent.py         # ITIL priority & deterministic category classification
│   ├── retrieval_agent.py      # Knowledge Base retrieval agent
│   ├── resolution_agent.py     # Advisory troubleshooting synthesis
│   └── critic_agent.py         # Zero-trust safety audit & policy enforcement
├── tests/                      # Automated Test Suite
│   ├── __init__.py             # Test package marker
│   ├── test_auth.py            # Authentication, PBKDF2 hashing, role security tests
│   ├── test_workflow.py        # LangGraph workflow, feedback loop, routing tests
│   ├── test_rbac.py            # Role-based scoping and UI sanitization tests
│   └── test_helpdesk.py        # Triage, ITIL matrices, KB retrieval, Critic tests
├── app.py                      # Streamlit SaaS web application
├── auth.py                     # PBKDF2 password hashing & user store
├── rbac.py                     # RBAC authorization & scoping logic
├── knowledge_base.py           # Approved IT Standard Operating Procedures (SOPs)
├── llm_client.py               # Multi-tier LLM client (NVIDIA NIM / Ollama / Fallback)
├── sample_tickets.py           # Demonstration tickets pool
├── evaluation.py               # 16-case synthetic regression benchmark
├── generate_presentation.py    # Presentation generation script
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git exclusions for secrets, DBs, and virtual envs
└── README.md                   # System documentation and Windows run guide
```

---

## 🛡️ Responsible AI & Safety Disclaimers

1. **Advisory Guidance Only**: HelpDesk-AI generates initial troubleshooting recommendations for human review. It does not perform autonomous device quarantine or system-altering actions without human authorization.
2. **Human-in-the-Loop Resolution**: Tickets are never closed or marked resolved by the AI. Resolution requires explicit confirmation from the incident reporter or an authorized IT technician.
3. **No Unimplemented Dispatch**: Escalated tickets route to internal human specialist queues within the application. External ITSM platform synchronization (e.g. ServiceNow, Jira Service Management) is documented as an unintegrated roadmap feature.

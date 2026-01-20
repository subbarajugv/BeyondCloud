# Commercial Strategy: Pricing & Licensing 💰

## The Architecture-Led Strategy
Because BeyondCloud is a **"Universal AI OS"** (BYO-LLM, No Vendor Lock-in), your pricing model must align with *where the compute happens*. Since the customer pays for the LLM (OpenAI keys or local GPUs), you cannot easily mark up the token usage.

**Recommendation**: Sell the **Orchestration**, not the Compute.

---

## 1. The Core Model: "Enterprise Self-Hosted" (Primary) 🏢
*Target*: Banks, Healthcare, Defense (High Compliance).*

*   **Deployment**: Customer installs on their VPC / On-Prem Kubernetes. Air-gapped.
*   **Pricing**: **Per Node / Per Core** + **Seat License**.
    *   **Platform Fee**: $25k/year per "Agent Cluster" (Control Plane + 5 Workers).
    *   **User Fee**: $50/user/month for the Dashboard access.
*   **Why**: Matches your value prop of "Data never leaves your environment."
*   **Technical Need**: A **Offline License Key** system (signed JWTs) that validates features without phoning home.

## 2. The Growth Model: "Managed Control Plane" (Hybrid) ☁️
*Target*: Tech Corps, Startups, Mid-Market.*

*   **Deployment**: 
    *   **Control Plane (Dashboard/DB)**: Hosted by You (SaaS).
    *   **Data Plane (Agents/RAG)**: Runs in Customer's Cloud (they give you a K8s namespace or run your Runner binary).
*   **Pricing**: **Usage-Based Platform Fee**.
    *   $0.10 per "Agent Run" or "RAG Query" (Orchestration fee).
    *   *Note*: They still pay their own OpenAI/Anthropic bills.
*   **Why**: Low friction. They don't want to manage Postgres/Redis, but they want to keep their data/code private.

## 3. The "OEM/Embed" Model 🔌
*Target*: SaaS companies wanting to add AI Agents to their product.*

*   **Deployment**: Library / API integration.
*   **Pricing**: **Revenue Share** or **High Volume API**.
    *   "Powered by BeyondCloud" License: Flat $50k/year + Volume discounts.

---

## Licensing Implementation Plan 🔐

To enable these models, we need a technical licensing layer (Future Phase 12).

### A. The License Key (JWT)
A signed text string containing:
```json
{
  "org": "Acme Corp",
  "plan": "enterprise",
  "expires": "2027-01-01",
  "features": ["rag", "agent", "sso"],
  "seats": 100,
  "nodes": 5
}
```
*The Backend validates this signature on startup. If invalid or expired, it moves to "Read Only" mode.*

### B. "Phone Home" (Optional)
For the Hybrid model, the backend sends daily telemetry (anonymized) to your billing server:
*   `active_users: 45`
*   `agent_runs: 1205`
*   `rag_queries: 5400`

---

## Proposal: The "AGPL Open Core" Strategy 🛡️
Given our Open Source roots (MIT fork), we should adopt **AGPL v3** for the project going forward.

1.  **Why AGPL v3?**
    *   **Virality**: If a competitor (like AWS/Microsoft) hosts our code as a service, they *must* release their modifications. This kills "Wrap and Resell" competitors.
    *   **Compatibility**: Legal to combine with our original MIT code.
    *   **Fair Use**: Users can still use it freely for internal use or personal projects.

2.  **Community Edition (Open Source - AGPL)**:
    *   Free.
    *   Full features (RAG/Agents), but stricter license.

3.  **Enterprise Edition (Commercial License)**:
    *   **License**: Proprietary (Dual License).
    *   **Benefit**: Customers pay to *escape* the AGPL obligations (so they can embed it in their closed-source products).
    *   **Features**: + RBAC, SSO, Audit Logs.
    *   Price: **Annual Contract ($50k+)**.

**Verdict**: Switch repo to **AGPL v3**. It safeguards your hard work while keeping the code open.

# Enterprise Hardening Roadmap 🛡️

## Current Status: "Functional Alpha"
We have a working product with Dual-Mode Agents, RAG, and Role-Based Access Control (RBAC). It works for teams, but needs "hardening" for large-scale enterprise deployment.

## Phase A: Security Hardening (The "Zero Trust" Layer)
**Goal:** Prove to a CISO that this is safe.

1.  **Secrets Management Strategy**
    *   **Current**: `.env` files (unsafe for production).
    *   **Enterprise**: Integrate HashiCorp Vault or AWS Secrets Manager.
    *   **Action**: Create a `SecretManager` interface in Python to abstract secret retrieval.

2.  **Audit Logging (Immutable)**
    *   **Current**: Database logs.
    *   **Enterprise**: Ship logs to SIEM (Splunk/Datadog).
    *   **Action**: Add a structured logger that pushes JSON events to an external collector.

3.  **Strict Content Security Policy (CSP)**
    *   **Action**: Harden `main.py` middleware to explicitly block inline scripts and restrict connections to known APIs.

## Phase B: Reliability & Observability (The "Mission Control")
**Goal:** Know it's broken before the customer does.

1.  **OpenTelemetry (OTel) Integration**
    *   **Action**: Instrument FastAPI and LangChain with OTel SDK.
    *   **Target**: Send traces to Jaeger (dev) or Honeycomb/Datadog (prod).
    *   **Why**: Visualize "Why did the Agent take 30 seconds?"

2.  **Health Checks & Probes**
    *   **Action**: Add deep health checks (`/health/deep`) that check DB connection, Vector DB status, and LLM API latency.
    *   **Why**: Required for Kubernetes liveness probes.

## Phase C: Scalability (The "Cloud Native" Layer)
**Goal:** Handle 10,000 users.

1.  **Stateless Agent Backend**
    *   **Action**: Ensure Agent State is *always* in Redis/Postgres, never in Python memory.
    *   **Verify**: Kill the python process mid-agent-loop, restart it, and ensure it resumes (using the DB state).

2.  **Docker Compose -> Kubernetes Helm Chart**
    *   **Action**: Create a Helm Chart for deploying:
        *   Backend (ReplicaSet)
        *   Frontend (ReplicaSet)
        *   Postgres + pgvector (StatefulSet)
        *   Redis (StatefulSet)

## Phase D: DevSecOps (The Pipeline)
**Goal:** Safe continuous delivery.

1.  **CI/CD Pipeline**
    *   **Action**: GitHub Actions workflow that runs:
        *   Linting (Ruff/Black)
        *   Type Checking (MyPy)
        *   Unit Tests (PyTest)
        *   Security Scan (Bandit/Trivy)

## Timeline Estimate

| Phase | Duration | Priority |
| :--- | :--- | :--- |
| **A. Security** | 2 Weeks | Critical |
| **B. Observability** | 1 Week | High |
| **C. Scalability** | 2 Weeks | Medium |
| **D. DevSecOps** | 1 Week | High |

# Future Enhancements & Hardening Roadmap

This document outlines planned improvements and security hardening steps for the BeyondCloud application.

## 🛡️ Security Hardening
- [ ] **Secure Cookies**: Move JWT from `localStorage` to `HttpOnly` / `SameSite=Strict` cookies to prevent XSS.
- [ ] **CORS Hardening**: Restrict API access to specific trusted domains.
- [ ] **Rate Limiting**: Implement per-IP and per-user request limits to prevent brute-force and DoS attacks.
- [ ] **File Sanitization**: Implement deeper inspection of uploaded files (PDF/Docx) to strip malicious macros or embedded scripts.

## 🚀 RAG & AI Improvements
- [ ] **Multi-Modal RAG**: Add support for images (OCR) and audio (transcription) as knowledge sources.
- [ ] **Advanced Reranking**: Integrate a Cross-Encoder reranking step (e.g., BGE-Reranker) to improve answer precision.
- [ ] **Audit Logging**: Implement a tamper-proof log of which users/admins accessed specific RAG sources.
- [ ] **Usage Quotas**: Add logic to limit the number of documents and vector tokens per user role.
- [ ] **Real-time Performance Monitoring**: Fully implement the OpenTelemetry tracing export for bottlenecks analysis.

## 📦 Deployment & Scaling
- [ ] **Full Dockerization**: Create a `docker-compose.yml` that orchestrates Node.js, Python, PostgreSQL, and Nginx.
- [ ] **Hybrid Search Optimization**: Fine-tune BM25 weights and vector weights based on user feedback.
- [ ] **Horizontal Scaling**: Ensure the Python backend can be scaled across multiple instances using a shared Redis cache if needed.

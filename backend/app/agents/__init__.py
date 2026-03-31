"""
Phase 6 — Multi-agent orchestration layer.

RouterAgent dispatches incoming requests to the appropriate specialist agent
based on the detected intent/category from the decision engine.

Specialist agents:
  - BillingAgent    — payment, subscription, invoice queries
  - TechnicalAgent  — app crashes, performance, data issues
  - AccountAgent    — password reset, login, 2FA, account locked

Falls back to the default SupportAgent when no specialist matches.
"""

from app.agents.router_agent import RouterAgent, router_agent

__all__ = ["RouterAgent", "router_agent"]

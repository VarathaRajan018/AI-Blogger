# ADR-001: Python + LangChain as AI Orchestration Layer

**Date**: 2026-07-07  
**Status**: Accepted  
**Deciders**: Platform Architect

---

## Context

The platform requires orchestrating calls to multiple LLM providers, managing prompt templates, handling structured output parsing, and building multi-step AI agent workflows (e.g., iterative content refinement). We need a framework that abstracts provider differences and supports agent-style workflows.

## Decision

Use **Python 3.11+** as the primary language with **LangChain** for LLM abstraction and **LangGraph** for stateful agent workflows.

## Rationale

| Factor | Rationale |
|--------|----------|
| **LangChain Provider Support** | Native support for Gemini, OpenAI, Claude, Groq — exactly our target providers |
| **Structured Output** | Built-in Pydantic output parsers ensure LLM JSON matches our domain models |
| **LangGraph** | Enables stateful, iterative agent workflows (e.g., write → evaluate → refine loop) |
| **Python Ecosystem** | Best-in-class libraries for NLP, trend analysis (Pytrends), web scraping |
| **Async Support** | Full async/await support aligns with FastAPI's async model |
| **Community** | Largest AI engineering community; extensive documentation and examples |

## Consequences

- **Positive**: Rapid development of complex AI workflows; easy provider swapping
- **Negative**: LangChain's API evolves frequently; pin to specific versions
- **Mitigation**: Keep LangChain isolated behind our own `BaseLLMProvider` interface so we can eject if needed

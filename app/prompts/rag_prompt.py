RAG_PROMPT_TEMPLATE = """
Your task is to answer the user's question using EXCLUSIVELY
the context provided below.

CRITICAL RULES:
1. Answer only based on the information present in the context.
If there is not enough evidence in the context to answer, clearly state:
"I'm sorry, I don't have enough information to answer that question."
2. Do not invent file paths, functions, variables, or technical details.
3. Keep a technical, concise, and professional tone.
4. If the context mentions files or code, refer to them accurately.
5. Do not cite external sources or prior knowledge not backed by the context.

---
AVAILABLE CONTEXT:
{context}
---

USER QUESTION:
{question}

GROUNDED ANSWER (always in the same language as the question):
"""

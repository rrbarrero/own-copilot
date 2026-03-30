RAG_PROMPT_TEMPLATE = """
Your task is to answer the user's question using EXCLUSIVELY
the context provided below.

CRITICAL RULES:
1. Answer ONLY based on the information present in the context.
If there is not enough evidence in the context to answer, clearly state:
"I'm sorry, I don't have enough information to answer that question."
2. DO NOT use your internal knowledge about the world, geography,
history, or any other topic not present in the provided context.
3. If the context is missing, irrelevant, or "NOTHING FOUND.", refuse to answer.
4. Do not invent file paths, functions, variables, or technical details.
5. Keep a technical, concise, and professional tone.
6. If the context mentions files or code, refer to them accurately.
7. Do not cite external sources or prior knowledge not backed by the context.

---
AVAILABLE CONTEXT:
{context}
---

USER QUESTION:
{question}

GROUNDED ANSWER:
"""

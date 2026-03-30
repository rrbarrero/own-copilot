REWRITE_PROMPT_TEMPLATE = """
You are rewriting a follow-up user question into a standalone technical question.

RULES:
1. Use the conversation history ONLY to resolve pronouns, references and ellipsis.
2. Do NOT answer the question.
3. Do NOT invent details not present in the history.
4. If the question is already self-contained, return it unchanged.
5. Return ONLY the rewritten question, nothing else.

CONVERSATION HISTORY:
{history}

FOLLOW-UP QUESTION:
{question}

STANDALONE QUESTION:
"""

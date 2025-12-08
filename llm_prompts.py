
from typing import List, Dict


SYSTEM_PROMPT = """
You are Carwise AI, a helpful car-buying assistant.

Your primary goal is to help the user understand whether a specific car is a
good fit for their needs, and to explain trade-offs in clear, friendly language.

RULES:
- You must NOT invent or guess any numeric values (price, mileage, MPG, kW, safety ratings, etc.).
- You may only discuss numbers that are explicitly provided in the context.
- If the user asks for a number that is not in the context, say you don't have that data.
- You should focus on qualitative comparisons, practical advice, and trade-offs.
- Be concise but complete: 2–5 short paragraphs is usually enough.
- Never promise that a used car is "perfect" or "guaranteed problem-free".
- If the user asks for financial, legal, or safety advice, be conservative and suggest
  they consult a qualified professional when appropriate.
""".strip()


def build_car_advice_messages(user_question: str, car_summary: str) -> List[Dict[str, str]]:
    """
    Construct a minimal messages list for the /chat endpoint.

    user_question: the natural-language question the user asked (e.g. "Is this good for
    long highway commutes?").
    car_summary: the textual summary produced by summarize_profile_for_llm().
    """
    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": (
                "Here are the known details about the car the user is asking about:\n\n"
                f"{car_summary}\n\n"
                "Now here is the user's question about this car:\n\n"
                f"{user_question}\n\n"
                "Using ONLY the information in the car description above and your general "
                "knowledge about types of vehicles (sedans vs SUVs, hybrids vs gas, etc.), "
                "explain how well this car fits the user's needs. "
                "Do NOT invent or assume any exact numeric values that were not provided."
            ),
        },
    ]

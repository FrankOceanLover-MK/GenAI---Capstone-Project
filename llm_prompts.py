from typing import List, Dict, Any


SYSTEM_PROMPT = """
You are Carwise AI, a helpful car buying assistant.

Your main job is to give grounded, practical advice about real cars and real listings.

Core rules:

1. Never invent or guess numeric values such as price, mileage, MPG, kilowatts, safety ratings, or similar.
2. Only use numbers that are explicitly provided in the context.
3. If the user asks for a number that is not in the context, say that you do not have that data.
4. Focus on qualitative comparisons, trade offs, and plain practical advice.
5. Use short paragraphs with clear sentences. Two to five short paragraphs is usually enough.
6. Never promise that a used car is perfect or guaranteed to have no problems.
7. If the user asks for financial, legal, or safety advice, stay conservative and suggest talking to a qualified professional when needed.
8. Write in plain text only. Do not use markdown, bullet lists, code blocks, or emojis.
9. Keep numbers together as normal numbers. Do not split numbers into separate digits or letters.
""".strip()


def build_car_advice_messages(user_question: str, car_summary: str) -> List[Dict[str, str]]:
    """
    Messages for VIN specific explanations.

    The LLM receives a short summary of the decoded car plus the user question.
    """
    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": (
                "You are helping a user understand a specific car.\n\n"
                "Here are the known details about the car:\n\n"
                f"{car_summary}\n\n"
                "Here is the user's question about this car:\n\n"
                f"{user_question}\n\n"
                "Using only the information in the car description above and your general "
                "knowledge about categories of vehicles, explain how well this car fits the "
                "user's needs. Do not invent or assume any exact numeric values that were "
                "not provided. Answer in two to four short paragraphs, plain text only."
            ),
        },
    ]


def build_filter_extraction_messages(user_query: str) -> List[Dict[str, str]]:
    """
    Messages for turning a free form request into structured filters.

    The model must return a single JSON object with four keys:

      budget        maximum budget in dollars
      max_distance  maximum acceptable distance in miles
      body_style    desired body style string
      fuel_type     desired fuel type string

    Values that are unknown must be null. No extra text is allowed.
    """
    return [
        {
            "role": "system",
            "content": (
                "You extract search filters for used car listings from free text.\n\n"
                "Return a single JSON object with these keys:\n"
                "  budget: number or null\n"
                "  max_distance: number or null\n"
                "  body_style: string or null\n"
                "  fuel_type: string or null\n\n"
                "Interpret amounts like '30k' or '~25 000' as dollar amounts. "
                "If the user sounds price flexible and does not give a clear maximum, "
                "set budget to null.\n\n"
                "If the user does not care about a field, set it to null.\n\n"
                "Output only JSON. No explanations, no markdown, no extra text."
            ),
        },
        {
            "role": "user",
            "content": (
                "User request:\n\n"
                f"{user_query}\n\n"
                "Return only the JSON object with the extracted filters."
            ),
        },
    ]


def build_recommendation_messages(
    user_query: str,
    filters: Dict[str, Any],
    listings: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """
    Messages for explaining a set of candidate listings.

    listings is a list of plain dicts with keys such as
    year, make, model, trim, price, mileage, distance_miles, fuel_type,
    body_style, city_mpg, highway_mpg, safety_rating.
    """
    if listings:
        lines = []
        for idx, car in enumerate(listings, start=1):
            year = car.get("year")
            make = car.get("make")
            model = car.get("model")
            trim = car.get("trim") or ""
            price = car.get("price")
            mileage = car.get("mileage")
            fuel = car.get("fuel_type") or ""
            body = car.get("body_style") or ""
            distance = car.get("distance_miles")

            name_parts = [str(p) for p in [year, make, model] if p]
            name = " ".join(name_parts) or "Unknown car"
            if trim:
                name = f"{name} {trim}"

            desc_bits = [name]
            if price is not None:
                desc_bits.append(f"price about {price} dollars")
            if mileage is not None:
                desc_bits.append(f"around {mileage} miles")
            if body:
                desc_bits.append(body)
            if fuel:
                desc_bits.append(fuel)
            if distance is not None:
                desc_bits.append(f"about {distance} miles away")

            line = f"{idx}) " + ", ".join(desc_bits) + "."
            lines.append(line)

        listing_block = "\n".join(lines)
    else:
        listing_block = "No matching listings were found."

    filter_parts = []
    b = filters.get("budget")
    if b is not None:
        filter_parts.append(f"budget up to about {b} dollars")
    md = filters.get("max_distance")
    if md is not None:
        filter_parts.append(f"distance within about {md} miles")
    bs = filters.get("body_style")
    if bs:
        filter_parts.append(f"body style {bs}")
    ft = filters.get("fuel_type")
    if ft:
        filter_parts.append(f"fuel type {ft}")

    filter_text = ", ".join(filter_parts) if filter_parts else "no strong filters."

    user_block = (
        "The user is looking for a car. Here is what they said:\n"
        f"{user_query}\n\n"
        f"Inferred filters: {filter_text}\n"
    )

    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": (
                user_block
                + "\nHere are the candidate listings:\n\n"
                + listing_block
                + "\n\n"
                "Explain which two or three cars you recommend and why. "
                "Mention concrete details like price, mileage, body style, fuel type, and distance, "
                "but do not invent any new numbers that are not in the list above. "
                "If no listings were found, explain that clearly and suggest how the user could adjust their request. "
                "Answer in plain text, using two to four short paragraphs. No markdown."
            ),
        },
    ]

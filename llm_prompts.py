from typing import List, Dict, Any


SYSTEM_PROMPT = """
You are Carwise AI, an expert car shopping assistant.

RULES YOU MUST FOLLOW:
1. **ABSOLUTELY NO MARKDOWN FORMATTING** - No asterisks, no bold, no italics, no underscores, no bullet points, no headers
2. Write in plain text only - use normal sentences with normal punctuation
3. Use dollar amounts like $30,000 (with comma) not $30000
4. Use line breaks between paragraphs but no extra blank lines
5. If you mention a price, always include the dollar sign and comma: $25,000 not 25000
6. If you don't know something, say "I don't have that information"

PERSONALITY:
- Friendly but professional
- Data-driven but conversational
- Honest about limitations

FORMATTING RULES:
- No special characters for emphasis
- No asterisks, no bold, no italics
- No markdown of any kind
- Just write normal English sentences

EXAMPLE OF GOOD FORMAT:
"I recommend the Toyota Camry. It's priced at $25,000 and gets 35 MPG. This is a good choice because..."

EXAMPLE OF BAD FORMAT:
**I recommend the Toyota Camry** *It's priced at $25000* and gets 35 mpg.
- Good choice
- Reliable

Remember: Plain text only, no exceptions.
""".strip()

def build_car_advice_messages(user_question: str, car_summary: str) -> List[Dict[str, str]]:
    """
    Messages for VIN-specific explanations with richer context.
    """
    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": (
                "A customer is asking about a specific vehicle. Here's what we know about it:\n\n"
                f"{car_summary}\n\n"
                "Customer's question: {user_question}\n\n"
                "Please provide a helpful, grounded response. Use the data above to inform your answer, "
                "but don't repeat the raw specs - instead explain what they mean for the customer. "
                "Consider factors like reliability, cost of ownership, typical use cases, and known "
                "issues for this make/model/year if relevant. Keep it conversational and focused "
                "on answering their specific question."
            ),
        },
    ]


def build_filter_extraction_messages(user_query: str) -> List[Dict[str, str]]:
    """
    Enhanced filter extraction with better interpretation of natural language.
    """
    return [
        {
            "role": "system",
            "content": (
                "You are a search filter extraction assistant. Your job is to convert natural "
                "language car shopping requests into structured search parameters.\n\n"
                "Extract these fields:\n"
                "- budget: max price in dollars (number or null)\n"
                "- max_distance: max distance in miles (number or null)\n"
                "- body_style: SUV, Sedan, Truck, Coupe, Hatchback, Wagon, Minivan (string or null)\n"
                "- fuel_type: Gasoline, Diesel, Hybrid, Electric, Plug-in Hybrid (string or null)\n\n"
                "Interpretation guidelines:\n"
                "- Budget: '30k' = 30000, 'around 25000' = 25000, 'under 20k' = 20000\n"
                "- If user says 'affordable' or 'budget-friendly' without a number, use null\n"
                "- Distance: 'nearby' = 50, 'local' = 30, 'within X miles' = X\n"
                "- Body style: Map 'family car' to SUV, 'commuter' to Sedan, 'work vehicle' to Truck\n"
                "- Fuel: 'good MPG' = null (let economy scoring handle it), 'electric' = Electric\n\n"
                "Output ONLY a JSON object. No explanations, no markdown, no extra text."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Extract search filters from this request:\n\n{user_query}\n\n"
                "Return only the JSON object."
            ),
        },
    ]


def build_recommendation_messages(
    user_query: str,
    filters: Dict[str, Any],
    listings: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """
    Enhanced recommendation messages with better context and structure.
    """
    
    # Build rich listing descriptions
    if listings:
        listing_descriptions = []
        for idx, car in enumerate(listings, start=1):
            year = car.get("year")
            make = car.get("make")
            model = car.get("model")
            trim = car.get("trim", "")
            
            # Build a natural description
            name = f"{year} {make} {model} {trim}".strip()
            
            details = []
            if car.get("price") is not None:
                details.append(f"priced at ${car['price']:,.0f}")
            if car.get("mileage") is not None:
                details.append(f"{car['mileage']:,.0f} miles")
            if car.get("body_style"):
                details.append(car["body_style"])
            if car.get("fuel_type"):
                details.append(car["fuel_type"])
            if car.get("distance_miles") is not None:
                details.append(f"{car['distance_miles']:.0f} miles away")
            
            # Add MPG if available
            mpg_parts = []
            if car.get("city_mpg"):
                mpg_parts.append(f"{car['city_mpg']:.0f} city")
            if car.get("highway_mpg"):
                mpg_parts.append(f"{car['highway_mpg']:.0f} highway MPG")
            if mpg_parts:
                details.append(" / ".join(mpg_parts))
            
            # Add safety rating if available
            if car.get("safety_rating"):
                details.append(f"{car['safety_rating']}-star safety rating")
            
            desc = f"{idx}. {name}: " + ", ".join(details)
            listing_descriptions.append(desc)
        
        listings_text = "\n".join(listing_descriptions)
    else:
        listings_text = "No matching vehicles were found in the current inventory."
    
    # Build filter summary
    filter_summary_parts = []
    if filters.get("budget"):
        filter_summary_parts.append(f"budget up to ${filters['budget']:,.0f}")
    if filters.get("max_distance"):
        filter_summary_parts.append(f"within {filters['max_distance']:.0f} miles")
    if filters.get("body_style"):
        filter_summary_parts.append(f"{filters['body_style']} body style")
    if filters.get("fuel_type"):
        filter_summary_parts.append(f"{filters['fuel_type']} fuel type")
    
    if filter_summary_parts:
        filter_summary = "Search criteria: " + ", ".join(filter_summary_parts)
    else:
        filter_summary = "Search criteria: General search with no specific constraints"
    
    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": (
                f"Customer request: {user_query}\n\n"
                f"{filter_summary}\n\n"
                f"Available vehicles:\n{listings_text}\n\n"
                "Please provide a helpful recommendation. Structure your response this way:\n\n"
                "1. Start with a direct recommendation (1-2 sentences naming specific vehicles)\n"
                "2. Explain why these vehicles fit the customer's needs (1-2 paragraphs covering key factors)\n"
                "3. Note any important trade-offs or considerations (1 paragraph)\n"
                "4. If no vehicles match, explain why and suggest how to adjust the search\n\n"
                "Focus on the 2-3 best options. Use the actual numbers from the data above, but present "
                "them naturally in context rather than listing them. Write in a friendly, consultative "
                "tone as if you're helping a friend make a smart purchase. Remember: plain text only, "
                "no markdown formatting."
            ),
        },
    ]
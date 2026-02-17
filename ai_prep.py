import json

import anthropic

client = anthropic.Anthropic()


def generate_prep_todos(event_data: dict) -> list[dict]:
    """
    Given event data, ask Claude to generate a preparation to-do list.
    Returns a list of dicts like [{"task": "...", "priority": "high/medium/low"}, ...]
    """
    attendees_str = ", ".join(event_data["attendees"]) if event_data["attendees"] else "None listed"

    prompt = f"""You are a helpful assistant that creates preparation to-do lists for calendar events.

Given this upcoming event, generate a concise, actionable to-do list of things the person should do to prepare.

Event details:
- Title: {event_data['summary']}
- Description: {event_data['description'] or 'None'}
- Location: {event_data['location'] or 'None'}
- Start: {event_data['start']}
- End: {event_data['end']}
- Attendees: {attendees_str}
- Organizer: {event_data['organizer'] or 'Unknown'}

Return your response as a JSON array of objects, each with "task" (string) and "priority" ("high", "medium", or "low") fields.
Only return the JSON array, no other text. Generate 3-7 actionable items."""

    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()

    try:
        todos = json.loads(response_text)
    except json.JSONDecodeError:
        # Fallback: Claude may wrap JSON in markdown code fences
        if "```" in response_text:
            json_str = response_text.split("```")[1]
            if json_str.startswith("json"):
                json_str = json_str[4:]
            todos = json.loads(json_str.strip())
        else:
            todos = [{"task": "Could not parse AI response. Please try regenerating.", "priority": "medium"}]

    return todos

import requests
import json

TONE_MAP = {
    "Platinum": "ultra-premium and exclusive — this person is a VIP",
    "Gold":     "premium and warm — they are a loyal valued customer",
    "Silver":   "friendly and encouraging — they are an engaged regular",
    "Bronze":   "welcoming and value-focused — highlight great deals"
}

def generate_email(customer: dict) -> dict:
    name      = customer.get('Name', 'there').split()[0]
    interest  = customer.get('Interest_Tag', 'our latest')
    tier      = customer.get('Membership_Tier', 'Silver')
    city      = customer.get('City', 'your city')
    purchases = customer.get('Past_Purchases', 0)
    tone      = TONE_MAP.get(tier, "friendly and professional")

    prompt = f"""You are an email copywriter for MailMagic.

Write a personalized marketing email for:
- Name: {name}
- Membership Tier: {tier}
- Interest: {interest}
- City: {city}
- Past Purchases: {purchases}
- Tone: {tone}

RULES:
1. Subject: max 60 characters, no spam words
2. Body: exactly 3 short paragraphs
3. CTA: max 5 words
4. quality_score: 0-100

RESPOND ONLY with valid JSON, no extra text, no markdown:
{{"subject": "...", "body": "...", "cta": "...", "quality_score": 85, "preview_text": "..."}}"""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model":  "llama3",
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )
        text = response.json()["response"].strip()

        # Clean any markdown fences if present
        text = text.replace("```json", "").replace("```", "").strip()

        return json.loads(text)

    except Exception as e:
        # Fallback if Ollama fails or returns malformed JSON
        print(f"Ollama fallback triggered. Error: {e}")
        return {
            "subject":       f"Exclusive {interest} deals for you, {name}!",
            "body":          f"Hi {name},\n\nAs a {tier} member from {city}, you get exclusive access to our best {interest} deals.\n\nWe've handpicked offers based on your preferences and past purchases.\n\nDon't miss out — these deals are available for a limited time only.",
            "cta":           "Claim My Deal",
            "quality_score": 78,
            "preview_text":  f"Your exclusive {interest} update is waiting..."
        }
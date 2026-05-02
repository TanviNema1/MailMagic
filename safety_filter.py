import re
import requests
import json

# ── Blocked Word Lists ────────────────────────────────────────────────────────

SPAM_WORDS = [
    "free", "urgent", "click now", "winner", "won", "prize", "guaranteed",
    "100%", "act now", "no cost", "risk free", "cash", "earn money",
    "make money", "work from home", "click here", "buy now", "order now",
    "call now", "apply now", "congratulations", "you have been selected",
    "claim now", "double your", "extra income", "fast cash", "get paid"
]

OFFENSIVE_WORDS = [
    "hate", "kill", "stupid", "idiot", "dumb", "loser",
    "worthless", "pathetic", "disgusting", "offensive"
]

FALSE_PROMISE_WORDS = [
    "you won", "you have won", "you are selected",
    "guaranteed winner", "100% guaranteed", "no risk",
    "get rich", "instant money", "free money"
]

LEGAL_RISK_WORDS = [
    "cure", "treat", "heal", "diagnose", "prevent disease",
    "lose weight guaranteed", "miracle", "magic solution"
]

# ── CTR Thresholds ────────────────────────────────────────────────────────────
CTR_POOR    = 0.02   # below 2%  → regenerate
CTR_AVERAGE = 0.035  # 2% - 3.5% → acceptable
# above 3.5% → good


# ── Safety Check ──────────────────────────────────────────────────────────────

def check_email_safety(email_content: dict, min_quality_score: int = 60) -> dict:
    issues     = []
    subject    = email_content.get("subject", "")
    body       = email_content.get("body", "")
    cta        = email_content.get("cta", "")
    quality    = email_content.get("quality_score", 0)
    full_text  = f"{subject} {body} {cta}".lower()

    found_spam      = [w for w in SPAM_WORDS          if w in full_text]
    found_offensive = [w for w in OFFENSIVE_WORDS     if w in full_text]
    found_false     = [w for w in FALSE_PROMISE_WORDS if w in full_text]
    found_legal     = [w for w in LEGAL_RISK_WORDS    if w in full_text]

    if found_spam:
        issues.append(f"Spam words found: {', '.join(found_spam)}")
    if found_offensive:
        issues.append(f"Offensive words found: {', '.join(found_offensive)}")
    if found_false:
        issues.append(f"False promises found: {', '.join(found_false)}")
    if found_legal:
        issues.append(f"Legal risk words found: {', '.join(found_legal)}")
    if quality < min_quality_score:
        issues.append(f"Quality score too low: {quality} (minimum: {min_quality_score})")
    if len(subject) > 60:
        issues.append(f"Subject too long: {len(subject)} chars (max: 60)")
    if not subject.strip():
        issues.append("Subject is empty")
    if not body.strip():
        issues.append("Body is empty")
    if not cta.strip():
        issues.append("CTA is empty")
    if subject.count("!") > 1:
        issues.append("Too many exclamation marks in subject")

    caps_words = [w for w in subject.split() if w.isupper() and len(w) > 2]
    if len(caps_words) > 2:
        issues.append(f"Too many ALL CAPS words: {caps_words}")

    is_safe = (
        len(found_offensive) == 0 and
        len(found_false) == 0 and
        len(issues) <= 2
    )

    return {
        "is_safe":    is_safe,
        "issues":     issues,
        "risk_level": "low" if len(issues) == 0 else "medium" if len(issues) <= 2 else "high"
    }


# ── CTR Level Helper ──────────────────────────────────────────────────────────

def get_ctr_level(ctr: float) -> str:
    if ctr < CTR_POOR:
        return "poor"
    elif ctr < CTR_AVERAGE:
        return "average"
    else:
        return "good"


# ── Regenerate for Safety ─────────────────────────────────────────────────────

def regenerate_for_safety(customer: dict, issues: list) -> dict:
    """Asks Ollama to fix safety issues."""
    name      = customer.get('Name', 'there').split()[0]
    interest  = customer.get('Interest_Tag', 'our latest')
    tier      = customer.get('Membership_Tier', 'Silver')
    city      = customer.get('City', 'your city')
    purchases = customer.get('Past_Purchases', 0)
    issues_str = "\n".join([f"- {issue}" for issue in issues])

    prompt = f"""You are a professional email copywriter for MailMagic.

Your previous email was REJECTED by our safety filter for these reasons:
{issues_str}

Please rewrite a SAFE, FORMAL, PROFESSIONAL marketing email for:
- Name: {name}
- Membership Tier: {tier}
- Interest: {interest}
- City: {city}
- Past Purchases: {purchases}

STRICT RULES:
1. NO spam words (free, urgent, winner, prize, guaranteed, claim, act now)
2. NO offensive language
3. NO false promises or misleading claims
4. Subject: max 60 characters, no exclamation marks, no ALL CAPS
5. Body: exactly 3 short professional paragraphs
6. CTA: max 5 words, professional tone
7. Tone: formal, respectful, value-focused
8. quality_score: 0-100

RESPOND ONLY with valid JSON, no extra text, no markdown:
{{"subject": "...", "body": "...", "cta": "...", "quality_score": 85, "preview_text": "..."}}"""

    return _call_ollama(prompt)


# ── Regenerate for CTR ────────────────────────────────────────────────────────

def regenerate_for_ctr(customer: dict, current_email: dict, current_ctr: float) -> dict:
    """Asks Ollama to improve email to boost CTR."""
    name      = customer.get('Name', 'there').split()[0]
    interest  = customer.get('Interest_Tag', 'our latest')
    tier      = customer.get('Membership_Tier', 'Silver')
    city      = customer.get('City', 'your city')
    purchases = customer.get('Past_Purchases', 0)
    ctr_pct   = round(current_ctr * 100, 2)

    prompt = f"""You are a professional email copywriter for MailMagic.

Your previous email had a LOW predicted click-through rate of {ctr_pct}% (target: above 2%).

Previous email:
- Subject: {current_email.get('subject')}
- CTA: {current_email.get('cta')}

Please rewrite a MORE COMPELLING email for:
- Name: {name}
- Membership Tier: {tier}
- Interest: {interest}
- City: {city}
- Past Purchases: {purchases}

FOCUS ON IMPROVING CTR:
1. Write a more intriguing, curiosity-driven subject line (max 60 chars)
2. Make the body more personalized and benefit-focused
3. Write a stronger, action-oriented CTA (max 5 words)
4. Reference their specific interest: {interest}
5. Mention their tier: {tier} — make them feel valued
6. NO spam words, NO false promises, NO ALL CAPS

RESPOND ONLY with valid JSON, no extra text, no markdown:
{{"subject": "...", "body": "...", "cta": "...", "quality_score": 85, "preview_text": "..."}}"""

    return _call_ollama(prompt)


# ── Ollama Caller ─────────────────────────────────────────────────────────────

def _call_ollama(prompt: str) -> dict | None:
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3", "prompt": prompt, "stream": False},
            timeout=60
        )
        text = response.json()["response"].strip()
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        print(f"Ollama call failed: {e}")
        return None


# ── Full Pipeline ─────────────────────────────────────────────────────────────

def safe_generate_email(customer: dict, initial_email: dict,
                        predict_ctr_fn, max_retries: int = 2) -> dict:
    """
    Full safety + CTR pipeline:

    1. Safety check → regenerate if unsafe (max 2 retries)
    2. CTR check    → regenerate if CTR < 2% (max 2 retries)
    3. Return best email with full audit trail

    Returns:
    {
        "email":             {...},
        "is_safe":           True/False,
        "ctr":               0.034,
        "ctr_level":         "good/average/poor",
        "attempts_safety":   1,
        "attempts_ctr":      1,
        "was_regenerated":   True/False,
        "final_issues":      [...]
    }
    """
    email            = initial_email
    was_regenerated  = False
    attempts_safety  = 0
    attempts_ctr     = 0

    # ── Phase 1: Safety Check ─────────────────────────────────────────────────
    for attempt in range(1, max_retries + 2):
        attempts_safety = attempt
        safety          = check_email_safety(email)

        if safety["is_safe"]:
            print(f"✅ Safety passed on attempt {attempt}")
            break

        print(f"⚠️  Safety failed attempt {attempt}: {safety['issues']}")

        if attempt <= max_retries:
            print("🔄 Regenerating for safety...")
            regenerated = regenerate_for_safety(customer, safety["issues"])
            if regenerated:
                email           = regenerated
                was_regenerated = True
            else:
                break
    else:
        final_safety = check_email_safety(email)
        if not final_safety["is_safe"]:
            print("❌ Email failed safety pipeline")
            return {
                "email":           email,
                "is_safe":         False,
                "ctr":             0,
                "ctr_level":       "poor",
                "attempts_safety": attempts_safety,
                "attempts_ctr":    0,
                "was_regenerated": was_regenerated,
                "final_issues":    final_safety["issues"]
            }

    # ── Phase 2: CTR Check ────────────────────────────────────────────────────
    predicted_hour = 10  # default — will be overridden by caller
    ctr = predict_ctr_fn(email, predicted_hour)

    for attempt in range(1, max_retries + 2):
        attempts_ctr = attempt
        ctr_level    = get_ctr_level(ctr)

        print(f"📊 CTR attempt {attempt}: {round(ctr*100,2)}% → {ctr_level}")

        if ctr_level != "poor":
            print(f"✅ CTR acceptable: {round(ctr*100,2)}%")
            break

        if attempt <= max_retries:
            print(f"🔄 CTR too low ({round(ctr*100,2)}%), asking Ollama to improve...")
            regenerated = regenerate_for_ctr(customer, email, ctr)
            if regenerated:
                # Safety check the new version too
                new_safety = check_email_safety(regenerated)
                if new_safety["is_safe"]:
                    email           = regenerated
                    was_regenerated = True
                    ctr             = predict_ctr_fn(email, predicted_hour)
                else:
                    print("⚠️  CTR regeneration failed safety — keeping previous")
                    break
            else:
                break

    return {
        "email":           email,
        "is_safe":         True,
        "ctr":             ctr,
        "ctr_level":       get_ctr_level(ctr),
        "attempts_safety": attempts_safety,
        "attempts_ctr":    attempts_ctr,
        "was_regenerated": was_regenerated,
        "final_issues":    []
    }
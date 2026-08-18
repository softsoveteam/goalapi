from datetime import date
import hashlib

NICHES = (
    "dinner",
    "breakfast",
    "water",
    "medicine",
    "take_care",
    "sleep",
    "walk",
    "miss_you",
    "periods",
    "custom",
)

NICHE_LABELS = {
    "dinner": "Dinner",
    "breakfast": "Breakfast",
    "water": "Water",
    "medicine": "Medicine",
    "take_care": "Take care",
    "sleep": "Sleep",
    "walk": "Walk",
    "miss_you": "Thinking of you",
    "periods": "Periods",
    "custom": "Custom",
}


def _combo(heads, tails):
    lines = []
    for head in heads:
        for tail in tails:
            text = "{0} {1}".format(head.strip(), tail.strip()).strip()
            if text not in lines:
                lines.append(text)
            if len(lines) >= 100:
                return lines[:100]
    raise RuntimeError("need 100 unique lines, got {0}".format(len(lines)))


MESSAGES = {
    "dinner": _combo(
        [
            "Have your dinner, love.",
            "Please eat a warm meal tonight.",
            "Sit down and finish dinner properly.",
            "Don't skip dinner today.",
            "A little food will make you feel better.",
            "Dinner time — I am thinking of you.",
            "Eat something nice before the night gets late.",
            "Your plate first, everything else can wait.",
            "Have dinner slowly, no rush.",
            "Please don't go to bed hungry.",
        ],
        [
            "Someone is taking care of you from here.",
            "I wish I could sit with you.",
            "You deserve a calm meal.",
            "Even a small plate is enough.",
            "Drink water with it too.",
            "Then rest, you did enough today.",
            "I hope it tastes like home.",
            "I am proud of you.",
            "Save a little sweetness if you can.",
            "Good night after that, okay?",
        ],
    ),
    "breakfast": _combo(
        [
            "Good morning — please have breakfast.",
            "Start the day with something to eat.",
            "Don't leave the house on an empty stomach.",
            "A little breakfast will carry you far.",
            "Tea is fine, but eat something too.",
            "Morning fuel, my love.",
            "Take ten minutes for breakfast.",
            "Eat before the rush begins.",
            "Your body needs a gentle start.",
            "Please don't skip the first meal.",
        ],
        [
            "I am with you in my thoughts.",
            "Make it warm if you can.",
            "You matter more than the clock.",
            "Then take on the day.",
            "Someone here is rooting for you.",
            "Have a sweet sip after.",
            "Go slow, you are safe.",
            "I hope the morning is kind.",
            "Send me a smile later.",
            "Have a beautiful day.",
        ],
    ),
    "water": _combo(
        [
            "Sip some water now.",
            "A full glass of water, please.",
            "Your body is asking for water.",
            "Pause and drink water.",
            "Hydrate, love.",
            "Water first, then the next task.",
            "Don't wait until you feel dizzy.",
            "Keep a bottle close today.",
            "Little sips through the day.",
            "One glass right now, okay?",
        ],
        [
            "I am looking after you from afar.",
            "It is a small kindness to yourself.",
            "You will feel lighter after.",
            "This is me taking care of you.",
            "Then continue, gently.",
            "I wish I could hand it to you.",
            "You deserve this pause.",
            "Stay fresh for the rest of the day.",
            "I am thinking of your health.",
            "Thank you for listening.",
        ],
    ),
    "medicine": _combo(
        [
            "Please take your medicine on time.",
            "Medicine reminder — don't skip it.",
            "Your tablet/time is now.",
            "A tiny pill, a big kindness to you.",
            "Take your medicine with water.",
            "Health first: medicine time.",
            "Don't wait for the ache to remind you.",
            "Your dose is due.",
            "Please take what the doctor asked.",
            "Medicine, then a slow breath.",
        ],
        [
            "I am here, even from a distance.",
            "You are not doing this alone.",
            "This is how we keep you well.",
            "I care about every small step.",
            "After that, rest a little.",
            "Proud of you for remembering.",
            "Your health is precious to me.",
            "Call me if you need anything.",
            "Gentle day after this.",
            "I love that you look after yourself.",
        ],
    ),
    "take_care": _combo(
        [
            "Take care of yourself today.",
            "Please be gentle with your heart.",
            "You are loved, so take care.",
            "Don't carry the whole world alone.",
            "Slow down if the day feels heavy.",
            "I am sending you a quiet hug.",
            "Look after my favourite person.",
            "Rest when you need rest.",
            "You matter more than the to-do list.",
            "Keep yourself safe and warm.",
        ],
        [
            "Someone is taking care of you.",
            "I wish I could be right there.",
            "I am proud of how strong you are.",
            "Let the evening be softer.",
            "You don't have to be perfect.",
            "I am thinking of you constantly.",
            "Save a little energy for yourself.",
            "If you need me, I am here.",
            "You are doing enough.",
            "Hold that thought: you are cherished.",
        ],
    ),
    "sleep": _combo(
        [
            "Please sleep on time tonight.",
            "The bed is waiting — go rest.",
            "Put the phone down and sleep.",
            "A good night's sleep is your gift.",
            "Close your eyes, the day is done.",
            "Don't fight sleep tonight.",
            "Lights low, heart calm, sleep.",
            "You have earned this rest.",
            "Sleep well, my love.",
            "Let tomorrow wait — sleep now.",
        ],
        [
            "I will be here in the morning.",
            "Dream something kind.",
            "You are safe.",
            "I am sending you peace.",
            "Rest is also productive.",
            "I wish I could tuck you in.",
            "Tomorrow will be lighter.",
            "Hold my care like a blanket.",
            "Good night from my side.",
            "Sleep, I am watching over you.",
        ],
    ),
    "walk": _combo(
        [
            "A short walk would be lovely.",
            "Stretch your legs for ten minutes.",
            "Step outside if you can.",
            "A little movement for your mood.",
            "Walk slowly, no race.",
            "Fresh air is a small medicine.",
            "Take a gentle stroll.",
            "Move a little, then rest.",
            "Your body wants a walk.",
            "Even a corridor walk counts.",
        ],
        [
            "I would walk beside you if I could.",
            "Notice one pretty thing outside.",
            "Come back and drink water.",
            "This is me looking after you.",
            "Don't overdo it, just enough.",
            "You will feel brighter after.",
            "I am cheering for you.",
            "Breathe in, breathe out.",
            "Then treat yourself kindly.",
            "I am proud of you.",
        ],
    ),
    "miss_you": _combo(
        [
            "I miss you.",
            "Just a note: I am thinking of you.",
            "You crossed my mind, so here I am.",
            "Distance is loud today, I miss you.",
            "A small hello from my heart.",
            "I wish I could see you right now.",
            "You are my favourite thought.",
            "Holding you in my mind.",
            "This is a hug in a message.",
            "I hope you felt me thinking of you.",
        ],
        [
            "Someone is taking care of you.",
            "Smile for me, even a tiny one.",
            "I love you in the quiet hours too.",
            "Can't wait to hear your voice.",
            "You are never far from me.",
            "Save a little story for later.",
            "I am yours, always.",
            "The day is better because of you.",
            "Keep this close.",
            "Until I see you again.",
        ],
    ),
    "periods": _combo(
        [
            "Be extra kind to your body today.",
            "If cramps visit, rest is allowed.",
            "Warmth, water, and slow movements.",
            "You don't have to be strong every minute.",
            "A heating pad and a soft blanket help.",
            "Eat something comforting if you can.",
            "Listen to your body, not the clock.",
            "This week, extra care is the plan.",
            "Pain is not something you have to hide.",
            "I am checking in because I care.",
        ],
        [
            "I am with you through this.",
            "Tell me if you need anything at all.",
            "No guilt for resting more.",
            "You are loved on hard days too.",
            "Chocolate, tea, and kindness are valid.",
            "I wish I could take the ache away.",
            "This is not medical advice — just care.",
            "Hold on, it will pass, and I am here.",
            "You are not a burden.",
            "Gentle hugs from my side.",
        ],
    ),
}


def pick_message(niche: str, person_id: int, on_date: date, custom_text: str = "") -> str:
    if niche == "custom":
        text = (custom_text or "").strip()
        return text or "I am thinking of you. Someone is taking care of you."
    bank = MESSAGES.get(niche) or MESSAGES["take_care"]
    key = "{0}:{1}:{2}".format(person_id, niche, on_date.isoformat())
    index = int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16) % len(bank)
    return bank[index]


def preview_message(niche: str, person_id: int = 0, custom_text: str = "") -> str:
    from app.services.ist import now_ist

    return pick_message(niche, person_id, now_ist().date(), custom_text)

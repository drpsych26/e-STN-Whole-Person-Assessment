"""Crisis resource register for the crisis panel.

Every number here must be verified against its owning service before display. Entries
are marked clinically_reviewed = False until a registered clinician has reviewed the panel
content (D-015). Hours that conflict between sources are recorded in `hours_note` and must
be resolved before release; they are not guessed.

Verified against the Mental Health Foundation helplines directory (updated June 2026) and
corroborating government and agency pages, checked during the Stage 2 review cycle.
"""
from __future__ import annotations

VERIFIED_ON = "2026-11-21"

CRISIS_RESOURCES: tuple[dict[str, str], ...] = (
    {"id": "emergency", "name": "Emergency services (Police, Fire, Ambulance)", "contact": "111",
     "hours": "24/7", "hours_note": "", "use": "If someone is in immediate danger or unconscious."},
    {"id": "need_to_talk", "name": "1737 Need to talk?", "contact": "1737 (call or text)",
     "hours": "24/7", "hours_note": "", "use": "Free call or text to a trained counsellor."},
    {"id": "lifeline", "name": "Lifeline", "contact": "0800 543 354 (or text 4357)",
     "hours": "unresolved", "hours_note": "Sources list both 24/7 and 7am to midnight.",
     "use": "Counselling and crisis support."},
    {"id": "suicide_crisis", "name": "Suicide Crisis Helpline", "contact": "0508 828 865 (or text 0508 TAUTOKO)",
     "hours": "unresolved", "hours_note": "Sources list both 24/7 and 7am to midnight.",
     "use": "For people thinking about suicide, and for those worried about someone."},
    {"id": "samaritans", "name": "Samaritans", "contact": "0800 726 666",
     "hours": "24/7", "hours_note": "", "use": "Support for loneliness, distress or suicidal feelings."},
    {"id": "healthline", "name": "Healthline", "contact": "0800 611 116",
     "hours": "24/7", "hours_note": "", "use": "Health advice from registered nurses."},
)

PANEL_STATUS = {"clinically_reviewed": False, "reason": "Pending clinical review of panel content and escalation pathway (D-015, D-016)."}

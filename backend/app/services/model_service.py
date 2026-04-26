import random


LABELS = [
    "ae_aegypti",
    "ae_albopictus",
    "an_dirus",
    "an_minimus",
    "cx_quinquefasciatus",
    "other",
]


def predict_stub(_: str) -> tuple[str, float]:
    label = random.choice(LABELS)
    confidence = round(random.uniform(0.6, 0.98), 3)
    return label, confidence

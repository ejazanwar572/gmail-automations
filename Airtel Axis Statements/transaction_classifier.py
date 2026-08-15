"""Evidence-backed classification for Airtel Payments transactions."""

from decimal import Decimal, ROUND_HALF_UP


MIN_CONFIDENCE = Decimal("0.95")
EVIDENCE_CATEGORIES = {"airtel", "utilities"}
PREFERRED_MERCHANTS = ("ZOMATO", "ETERNAL", "SWIGGY", "BIGBASKET")


def _cents(value):
    return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _evidence_index(evidence):
    index = {}
    for item in evidence if isinstance(evidence, list) else []:
        category = str(item.get("category", "")).strip().lower()
        source = str(item.get("evidence_source", "")).strip()
        try:
            confidence = Decimal(str(item.get("confidence", 0)))
            key = (str(item["date"]), _cents(item["amount"]))
        except (KeyError, TypeError, ValueError):
            continue
        if category in EVIDENCE_CATEGORIES and source and confidence >= MIN_CONFIDENCE:
            index[key] = {"category": category, "evidence_source": source}
    return index


def classify_transactions(transactions, evidence):
    """Classify each transaction exactly once, using strong evidence for Airtel Payments."""
    groups = {"airtel": [], "utilities": [], "merchants": [], "general": [], "unclassified": []}
    evidence_by_transaction = _evidence_index(evidence)

    for dt, amount, subject, merchant in transactions:
        item = {"date": dt.strftime("%b %d"), "amount": amount, "merchant": merchant}
        subject_upper = subject.upper()

        if any(name in subject_upper for name in PREFERRED_MERCHANTS):
            groups["merchants"].append(item)
            continue

        if "AIRTEL" not in subject_upper:
            groups["general"].append(item)
            continue

        match = evidence_by_transaction.get((dt.strftime("%d/%m/%Y"), _cents(amount)))
        if match:
            groups[match["category"]].append({**item, "evidence_source": match["evidence_source"]})
        else:
            groups["unclassified"].append(item)

    return groups

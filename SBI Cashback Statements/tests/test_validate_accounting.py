import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import validate_statements


def test_accounting_uses_total_outstanding_when_total_amount_due_excludes_emi_balance():
    fields = {
        "prev_balance": "68360.35",
        "payments": "90934.55",
        "purchases": "64822.70",
        "fees": "825.52",
        "total_due": "20001.00",
        "total_outstanding": "43074.00",
    }

    accounting, error = validate_statements.validate_accounting(fields)

    assert error is None
    assert accounting["stated_total_due"] == 43074.0
    assert accounting["computed_total_due"] == 43074.02
    assert accounting["match"] is True

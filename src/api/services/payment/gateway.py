"""Mock payment gateway, shaped like Stripe PaymentIntents.

Swap the body of `charge` for a real Stripe/SumUp/Viva call later; the
route contract (returns an id + status) stays the same.
"""
import secrets


def charge(amount, customer_name=None):
    """Pretend to charge `amount`. Always succeeds in mock mode."""
    intent_id = "pi_mock_" + secrets.token_hex(8)
    return {
        "id": intent_id,
        "amount": round(amount, 2),
        "status": "paid",
        "customer": customer_name,
    }

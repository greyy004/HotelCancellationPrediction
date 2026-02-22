HIGH_RISK_THRESHOLD = 0.7
MEDIUM_RISK_THRESHOLD = 0.4
CANCEL_LIKELY_THRESHOLD = 0.5


def risk_level_from_probability(probability):
    if probability > HIGH_RISK_THRESHOLD:
        return "High"
    if probability > MEDIUM_RISK_THRESHOLD:
        return "Medium"
    return "Low"


def prediction_label_from_probability(probability):
    if probability > CANCEL_LIKELY_THRESHOLD:
        return "Likely to Cancel"
    return "Likely to NOT Cancel"


def validate_hold_request(booking, model_available, probability):
    if not booking:
        return False, "Booking not found.", "danger"
    if booking["booking_status"] == "Canceled":
        return False, "Canceled bookings cannot be put on hold.", "warning"
    if int(booking["is_on_hold"] or 0) == 1:
        return False, "Booking is already on hold.", "info"
    if not model_available:
        return False, "Prediction model unavailable. Cannot auto-hold booking.", "danger"
    if probability <= HIGH_RISK_THRESHOLD:
        return False, "Only high-risk bookings can be put on hold.", "warning"
    return True, None, None

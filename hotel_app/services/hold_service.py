HIGH_RISK_THRESHOLD = 0.4
MEDIUM_RISK_THRESHOLD = 0.2
CANCEL_LIKELY_THRESHOLD = 0.3


def risk(probability):
    if probability > HIGH_RISK_THRESHOLD:
        return "High"
    if probability > MEDIUM_RISK_THRESHOLD:
        return "Medium"
    return "Low"


def label(probability):
    if probability > CANCEL_LIKELY_THRESHOLD:
        return "Likely to Cancel"
    return "Likely to NOT Cancel"


def can_hold(booking, probability):
    if not booking:
        return False, "Booking not found.", "danger"
    if int(booking["is_on_hold"] or 0) == 1:
        return False, "Booking is already on hold.", "info"
    if probability <= HIGH_RISK_THRESHOLD:
        return False, "Only high-risk bookings can be put on hold.", "warning"
    return True, None, None

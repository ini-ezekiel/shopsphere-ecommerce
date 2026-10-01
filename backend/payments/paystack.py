import hashlib
import hmac
from urllib.parse import quote

import requests
from django.conf import settings


class PaystackConfigurationError(Exception):
    pass


class PaystackAPIError(Exception):
    def __init__(
        self,
        message,
        *,
        status_code=None,
        response_data=None,
    ):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}

        super().__init__(message)


def _get_secret_key():
    secret_key = settings.PAYSTACK_SECRET_KEY

    if not secret_key:
        raise PaystackConfigurationError("Paystack secret key is not configured.")

    return secret_key


def _get_headers():
    return {
        "Authorization": f"Bearer {_get_secret_key()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _make_request(
    method,
    path,
    *,
    json_data=None,
):
    url = f"{settings.PAYSTACK_BASE_URL}" f"{path}"

    try:
        response = requests.request(
            method=method,
            url=url,
            headers=_get_headers(),
            json=json_data,
            timeout=settings.PAYSTACK_TIMEOUT,
        )
    except requests.Timeout as error:
        raise PaystackAPIError("Paystack did not respond in time.") from error
    except requests.RequestException as error:
        raise PaystackAPIError("Unable to connect to Paystack.") from error

    try:
        response_data = response.json()
    except ValueError as error:
        raise PaystackAPIError(
            "Paystack returned an invalid response.",
            status_code=response.status_code,
        ) from error

    if not response.ok or response_data.get("status") is not True:
        raise PaystackAPIError(
            response_data.get(
                "message",
                "Paystack rejected the request.",
            ),
            status_code=response.status_code,
            response_data=response_data,
        )

    return response_data


def initialize_transaction(
    *,
    email,
    amount_subunit,
    reference,
    callback_url=None,
    metadata=None,
):
    if not isinstance(amount_subunit, int):
        raise ValueError("Payment amount must be an integer subunit value.")

    if amount_subunit <= 0:
        raise ValueError("Payment amount must be greater than zero.")

    payload = {
        "email": email,
        "amount": amount_subunit,
        "reference": reference,
        "currency": "NGN",
        "callback_url": (callback_url or settings.PAYSTACK_CALLBACK_URL),
    }

    if metadata:
        payload["metadata"] = metadata

    return _make_request(
        "POST",
        "/transaction/initialize",
        json_data=payload,
    )


def verify_transaction(reference):
    safe_reference = quote(
        str(reference),
        safe="",
    )

    return _make_request(
        "GET",
        f"/transaction/verify/{safe_reference}",
    )


def create_refund(
    *,
    transaction_reference,
    amount_subunit,
    currency,
    customer_note,
    merchant_note,
):
    transaction_reference = str(
        transaction_reference,
    ).strip()

    if not transaction_reference:
        raise ValueError("A payment transaction reference is required.")

    if not isinstance(amount_subunit, int):
        raise ValueError("Refund amount must be an integer subunit value.")

    if amount_subunit <= 0:
        raise ValueError("Refund amount must be greater than zero.")

    currency = str(currency).strip().upper()

    if not currency:
        raise ValueError("Refund currency is required.")

    payload = {
        "transaction": transaction_reference,
        "amount": amount_subunit,
        "currency": currency,
        "customer_note": str(customer_note).strip(),
        "merchant_note": str(merchant_note).strip(),
    }

    return _make_request(
        "POST",
        "/refund",
        json_data=payload,
    )


def fetch_refund(provider_refund_id):
    safe_refund_id = quote(
        str(provider_refund_id),
        safe="",
    )

    return _make_request(
        "GET",
        f"/refund/{safe_refund_id}",
    )


def verify_webhook_signature(
    *,
    raw_body,
    signature,
):
    if not signature:
        return False

    secret_key = _get_secret_key()

    expected_signature = hmac.new(
        secret_key.encode("utf-8"),
        raw_body,
        hashlib.sha512,
    ).hexdigest()

    return hmac.compare_digest(
        expected_signature,
        signature,
    )
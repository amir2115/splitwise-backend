from __future__ import annotations

from dataclasses import dataclass

import httpx
from fastapi import status

from app.core.errors import DomainError

SMS_IR_VERIFY_URL = "https://api.sms.ir/v1/send/verify"
SMS_REQUEST_TIMEOUT_SECONDS = 10.0


@dataclass
class SmsVerifyResult:
    message_id: int | None
    cost: float | None


def send_template_sms(*, api_key: str, template_id: int, mobile: str, parameters: list[dict[str, str]]) -> SmsVerifyResult:
    payload = {
        "mobile": mobile,
        "templateId": template_id,
        "parameters": parameters,
    }
    headers = {"x-api-key": api_key}

    try:
        response = httpx.post(SMS_IR_VERIFY_URL, json=payload, headers=headers, timeout=SMS_REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        body = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise DomainError(
            code="sms_provider_error",
            message="SMS provider request failed",
            status_code=status.HTTP_502_BAD_GATEWAY,
        ) from exc

    if body.get("status") != 1:
        raise DomainError(
            code="sms_provider_error",
            message="SMS provider rejected verification request",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details={"provider_message": body.get("message")},
        )

    data = body.get("data") or {}
    return SmsVerifyResult(message_id=data.get("messageId"), cost=data.get("cost"))


def send_verify_sms(*, api_key: str, template_id: int, parameter_name: str, mobile: str, code: str) -> SmsVerifyResult:
    return send_template_sms(
        api_key=api_key,
        template_id=template_id,
        mobile=mobile,
        parameters=[{"name": parameter_name, "value": code}],
    )

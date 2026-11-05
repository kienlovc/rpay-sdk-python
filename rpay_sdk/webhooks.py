from __future__ import annotations
import hashlib
import hmac
import json
from typing import Any, Dict, Mapping, Optional, Tuple, Union


def _format_canonical_value(val: Any) -> str:
    if val is None:
        return "<nil>"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float, str)):
        return str(val).strip()
    return json.dumps(val, separators=(",", ":"), ensure_ascii=False).strip()


def build_canonical_payload_string(payload: Mapping[str, Any]) -> str:
    if not isinstance(payload, Mapping):
        return ""
    keys = sorted(k for k in payload.keys() if k != "signature")
    parts = [f"{k}={_format_canonical_value(payload[k])}" for k in keys]
    return "&".join(parts)


def hmac_sha256_hex(secret: str, message: Union[str, bytes]) -> str:
    key_bytes = str(secret or "").encode("utf-8")
    msg_bytes = message.encode("utf-8") if isinstance(message, str) else bytes(message)
    return hmac.new(key_bytes, msg_bytes, hashlib.sha256).hexdigest()


def safe_compare_signature(expected: str, received: str) -> bool:
    a = str(expected or "").strip().lower()
    b = str(received or "").strip().lower()
    if not a or not b or len(a) != len(b):
        return False
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def sign_canonical_payload(payload: Mapping[str, Any], secret: str) -> Tuple[str, str]:
    canonical = build_canonical_payload_string(payload)
    sig = hmac_sha256_hex(secret, canonical)
    return sig, canonical


def sign_raw_body(raw_body: Union[str, bytes], secret: str) -> str:
    return f"sha256={hmac_sha256_hex(secret, raw_body)}"


def normalize_headers(headers: Optional[Mapping[str, Any]]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not headers:
        return out
    for k, v in headers.items():
        if isinstance(v, (list, tuple)):
            out[str(k).lower()] = str(v[0] if v else "").strip()
        elif v is not None:
            out[str(k).lower()] = str(v).strip()
    return out


def _parse_json_payload(
    payload: Optional[Union[Mapping[str, Any], str, bytes]],
    raw_body: Optional[Union[str, bytes]],
) -> Optional[Dict[str, Any]]:
    if isinstance(payload, Mapping):
        return dict(payload)
    source = payload if payload is not None else raw_body
    if source is None:
        return None
    try:
        text = source.decode("utf-8") if isinstance(source, bytes) else str(source)
        parsed = json.loads(text)
        return dict(parsed) if isinstance(parsed, Mapping) else None
    except Exception:
        return None


def normalize_unified_webhook_event(base_result: Dict[str, Any]) -> Dict[str, Any]:
    p = base_result.get("payload") or {}
    event_name = str(base_result.get("event") or p.get("event") or "")

    if event_name.startswith("crypto.") or p.get("trans_id") or p.get("invoice_code") or p.get("network"):
        return {
            **base_result,
            "channel": "usdt",
            "event": event_name or "crypto.invoice.paid",
            "invoiceCode": str(p.get("invoice_code") or p.get("invoiceCode") or p.get("trans_id") or ""),
            "orderId": str(p.get("request_id") or p.get("orderId") or p.get("order_id") or ""),
            "status": "paid",
            "amount": float(p.get("amount") or p.get("amountUsdt") or 0),
            "paidAmount": float(p.get("received") or p.get("receivedUsdt") or p.get("amount") or 0),
            "currency": str(p.get("token") or "USDT").upper(),
            "networkOrBank": str(p.get("network") or "TRC20").upper(),
            "transactionId": str(p.get("transaction_id") or p.get("txHash") or p.get("trans_id") or ""),
            "transferContent": str(p.get("request_id") or p.get("orderId") or ""),
            "recipientAddress": str(p.get("to_address") or p.get("address") or ""),
            "senderAddress": str(p.get("from_address") or ""),
            "transactions": [],
        }

    if event_name == "bank.transactions" or isinstance(p.get("transactions"), list):
        return {
            **base_result,
            "channel": "bank",
            "event": "bank.transactions",
            "invoiceCode": "",
            "orderId": "",
            "status": "paid",
            "amount": 0.0,
            "paidAmount": 0.0,
            "currency": "VND",
            "networkOrBank": str(base_result.get("bank") or p.get("bank") or "BANK"),
            "transactionId": "",
            "transferContent": "",
            "recipientAddress": str(base_result.get("accountNumber") or p.get("accountNumber") or ""),
            "senderAddress": "",
            "transactions": list(p.get("transactions") or []),
        }

    amount_val = float(p.get("amountVnd") or p.get("amount") or 0)
    paid_val = float(p.get("paidAmountVnd") or amount_val)
    return {
        **base_result,
        "channel": "bank",
        "event": event_name or "bank.invoice.paid",
        "invoiceCode": str(p.get("invoiceCode") or p.get("invoice_code") or ""),
        "orderId": str(p.get("orderId") or p.get("order_id") or ""),
        "status": "paid",
        "amount": amount_val,
        "paidAmount": paid_val,
        "currency": "VND",
        "networkOrBank": str(p.get("bankCode") or p.get("bankKey") or "BANK"),
        "transactionId": str(p.get("transactionId") or p.get("matchedTransactionId") or ""),
        "transferContent": str(p.get("transferContent") or ""),
        "recipientAddress": str(p.get("accountNumber") or ""),
        "senderAddress": "",
        "transactions": [],
    }


def verify_webhook(
    *,
    payload: Optional[Union[Mapping[str, Any], str, bytes]] = None,
    raw_body: Optional[Union[str, bytes]] = None,
    headers: Optional[Mapping[str, Any]] = None,
    secret: str = "",
) -> Dict[str, Any]:
    hdrs = normalize_headers(headers)
    parsed = _parse_json_payload(payload, raw_body)
    clean_secret = str(secret or "").strip()

    if not clean_secret:
        return normalize_unified_webhook_event(
            {
                "verified": False,
                "reason": "MISSING_WEBHOOK_SECRET",
                "scheme": "none",
                "event": hdrs.get("x-rpay-event") or hdrs.get("x-stc-event") or "bank.invoice.paid",
                "payload": parsed,
            }
        )

    # 1. STC / Bank Transaction Webhook (`X-STC-HMAC-SHA256` / `X-STC-Signature`)
    if "x-stc-hmac-sha256" in hdrs or "x-stc-signature" in hdrs or "x-stc-event" in hdrs:
        raw = raw_body if raw_body is not None else (
            payload if isinstance(payload, (str, bytes)) else json.dumps(parsed or {}, separators=(",", ":"))
        )
        stc_hmac = hdrs.get("x-stc-hmac-sha256", "")
        if stc_hmac:
            expected = hmac_sha256_hex(clean_secret, raw)
            ok = safe_compare_signature(expected, stc_hmac)
            return normalize_unified_webhook_event(
                {
                    "verified": ok,
                    "reason": "OK" if ok else "STC_HMAC_MISMATCH",
                    "scheme": "x-stc-hmac-sha256",
                    "event": hdrs.get("x-stc-event") or "bank.transactions",
                    "bank": hdrs.get("x-stc-bank") or "",
                    "accountNumber": hdrs.get("x-stc-account") or "",
                    "payload": parsed,
                }
            )
        plain_sig = hdrs.get("x-stc-signature") or hdrs.get("signature") or ""
        ok = safe_compare_signature(clean_secret, plain_sig)
        return normalize_unified_webhook_event(
            {
                "verified": ok,
                "reason": "OK" if ok else "STC_SIGNATURE_KEY_MISMATCH",
                "scheme": "x-stc-signature",
                "event": hdrs.get("x-stc-event") or "bank.transactions",
                "bank": hdrs.get("x-stc-bank") or "",
                "accountNumber": hdrs.get("x-stc-account") or "",
                "payload": parsed,
            }
        )

    # 2. Raw Body Signature (`X-RPay-Body-Signature`: `sha256=<hex>`)
    body_sig = hdrs.get("x-rpay-body-signature", "")
    if body_sig and (raw_body is not None or isinstance(payload, (str, bytes))):
        raw = raw_body if raw_body is not None else payload  # type: ignore[assignment]
        expected_body_sig = sign_raw_body(raw, clean_secret)  # type: ignore[arg-type]
        norm_received = body_sig if body_sig.startswith("sha256=") else f"sha256={body_sig}"
        ok = safe_compare_signature(expected_body_sig, norm_received)
        return normalize_unified_webhook_event(
            {
                "verified": ok,
                "reason": "OK" if ok else "BODY_SIGNATURE_MISMATCH",
                "scheme": "x-rpay-body-signature",
                "event": hdrs.get("x-rpay-event") or (parsed or {}).get("event") or "bank.invoice.paid",
                "payload": parsed,
            }
        )

    # 3. Canonical Sorted Key-Value Signature (`X-RPay-Signature` or `payload.signature`)
    if parsed is not None:
        candidate_sig = hdrs.get("x-rpay-signature") or str(parsed.get("signature") or "")
        if not candidate_sig:
            return normalize_unified_webhook_event(
                {
                    "verified": False,
                    "reason": "MISSING_SIGNATURE",
                    "scheme": "canonical-hmac-sha256",
                    "event": hdrs.get("x-rpay-event") or str(parsed.get("event") or "bank.invoice.paid"),
                    "payload": parsed,
                }
            )
        expected_sig, canonical = sign_canonical_payload(parsed, clean_secret)
        ok = safe_compare_signature(expected_sig, candidate_sig)
        return normalize_unified_webhook_event(
            {
                "verified": ok,
                "reason": "OK" if ok else "CANONICAL_SIGNATURE_MISMATCH",
                "scheme": "canonical-hmac-sha256",
                "canonicalPayload": canonical,
                "event": hdrs.get("x-rpay-event") or str(parsed.get("event") or "bank.invoice.paid"),
                "payload": parsed,
            }
        )

    return normalize_unified_webhook_event(
        {
            "verified": False,
            "reason": "EMPTY_PAYLOAD",
            "scheme": "none",
            "event": hdrs.get("x-rpay-event") or "bank.invoice.paid",
            "payload": None,
        }
    )

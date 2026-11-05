from __future__ import annotations
import json
import unittest
from typing import Any, Dict, List, Optional

import rpay_sdk as rpay
from rpay_sdk import (
    RPAY_BANKS,
    RPAY_USDT_NETWORKS,
    RPayClient,
    hmac_sha256_hex,
    resolve_bank_spec,
    resolve_usdt_network_spec,
    sign_canonical_payload,
    sign_raw_body,
)


class TestRPayPythonSDK(unittest.TestCase):
    def test_catalogs_and_router(self) -> None:
        self.assertEqual(len(RPAY_BANKS), 15)
        self.assertEqual(len(RPAY_USDT_NETWORKS), 18)
        self.assertEqual(resolve_bank_spec("VCB")["bin"], "970436")  # type: ignore[index]
        self.assertEqual(resolve_bank_spec("vtm")["key"], "viettelpay")  # type: ignore[index]
        self.assertEqual(resolve_usdt_network_spec("tron")["network"], "TRC20")  # type: ignore[index]

        res = rpay.route(provider="9ROUTER", security="HMAC_256", coalesced="498.310 req")
        self.assertTrue(res["ok"])
        self.assertEqual(res["badge"], "10/15 BANK")

    def test_multi_domain_and_unified_bank_usdt_pay_and_lsgd(self) -> None:
        calls: List[Dict[str, Any]] = []

        def mock_transport(
            method: str,
            url: str,
            headers: Dict[str, str],
            body: Optional[bytes],
            timeout: float,
        ) -> Any:
            parsed_body = json.loads(body.decode("utf-8")) if body else None
            calls.append({"method": method, "url": url, "headers": headers, "body": parsed_body})
            if url.endswith("/api/public/bank-invoices"):
                return {
                    "isSuccess": True,
                    "success": True,
                    "status": 201,
                    "data": {
                        "invoiceCode": "RPINV1001",
                        "orderId": parsed_body["orderId"],
                        "status": "pending",
                        "amountVnd": parsed_body["amountVnd"],
                        "currency": "VND",
                        "transferContent": "RPAY1001",
                        "beneficiary": {"bankCode": "VCB", "accountNumber": "0123456789", "accountHolder": "NGUYEN VAN A"},
                        "qr": {"imageUrl": "https://pay.shopa.vn/qr.png"},
                        "paymentUrl": "https://pay.shopa.vn/pay/RPINV1001",
                    },
                }
            if url.endswith("/api/public/usdt-invoices"):
                return {
                    "isSuccess": True,
                    "success": True,
                    "status": 201,
                    "data": {
                        "invoiceCode": "USINV2002",
                        "txCode": "USTX2002",
                        "orderId": parsed_body["orderId"],
                        "status": "pending",
                        "amountUsdt": parsed_body["amountUsdt"],
                        "token": "USDT",
                        "network": "TRC20",
                        "walletAddress": "TXYZ999",
                        "paymentUrl": "https://pay.shopb.com/pay/usdt/USTX2002",
                    },
                }
            if "/historyapivcbv2" in url:
                return {
                    "status": "success",
                    "transactions": [
                        {
                            "transactionID": "FT_PY_01",
                            "amount": "250000",
                            "description": "Thanh toan DH 1001",
                            "transactionDate": "05/11/2026 20:00:00",
                            "type": "IN",
                        }
                    ],
                }
            if url.endswith("/api/GetInvoiceHistory"):
                return {
                    "status": "success",
                    "data": {
                        "items": [
                            {
                                "trans_id": "USTX_PY_02",
                                "invoice_code": "USINV2002",
                                "request_id": "DH1002",
                                "status": "completed",
                                "token": "USDT",
                                "network": "TRC20",
                                "amount": "50.00",
                                "received": "50.00",
                                "transaction_id": "0xhash_py",
                            }
                        ]
                    },
                }
            return {"isSuccess": True, "success": True, "data": {}}

        client = RPayClient(
            bank_token="rpay_vcb_live_123456_abcdef",
            merchant_id="MRCH-01",
            usdt_key="ukey_01",
            transport=mock_transport,
        )

        shop_a = client.for_domain("pay.shopa.vn", site_id="site_a")
        bank_inv = shop_a.pay(channel="bank", amount=250000, orderId="DH1001")
        self.assertEqual(bank_inv["channel"], "bank")
        self.assertEqual(bank_inv["invoiceCode"], "RPINV1001")
        self.assertEqual(calls[0]["headers"]["X-Site-Domain"], "pay.shopa.vn")
        self.assertEqual(calls[0]["headers"]["X-Site-ID"], "site_a")

        usdt_inv = client.pay(domain="pay.shopb.com", channel="usdt", network="TRC20", amount=50, orderId="DH1002")
        self.assertEqual(usdt_inv["channel"], "usdt")
        self.assertEqual(usdt_inv["invoiceCode"], "USINV2002")
        self.assertEqual(calls[1]["headers"]["X-Site-Domain"], "pay.shopb.com")

        # V3 URL builder encodes `#` as `%23` and handles Viettel Money phone/pin
        vcb_url = shop_a.build_v3_get_url(bank="VCB", password="Pass#2026", account_number="0123456789")
        self.assertTrue("Pass%232026" in vcb_url)

        # Unified LSGD (`channel="all"`)
        history = shop_a.lsgd(channel="all", bank="VCB")
        self.assertEqual(history["count"], 2)

        processed = set()
        matched_b = shop_a.match_payment(
            history["transactions"],
            order_code="DH1001",
            expected_amount=250000,
            processed_ids=processed,
            mutate_processed_ids=True,
        )
        self.assertEqual(len(matched_b), 1)
        self.assertEqual(matched_b[0]["transactionID"], "FT_PY_01")

        matched_u = shop_a.match_payment(
            history["transactions"],
            order_code="DH1002",
            expected_amount=50,
            processed_ids=processed,
            mutate_processed_ids=True,
        )
        self.assertEqual(len(matched_u), 1)
        self.assertEqual(matched_u[0]["txHash"], "0xhash_py")

    def test_webhooks_verification(self) -> None:
        secret = "whsec_python_2026"
        payload = {
            "event": "bank.invoice.paid",
            "invoiceCode": "RPINV99",
            "orderId": "DH99",
            "amountVnd": 300000,
            "paidAmountVnd": 300000,
            "status": "paid",
        }
        sig, _ = sign_canonical_payload(payload, secret)
        signed_payload = {**payload, "signature": sig}
        raw_body = json.dumps(signed_payload)
        body_sig = sign_raw_body(raw_body, secret)

        client = RPayClient(secret=secret)
        ev1 = client.verify_webhook(
            payload=signed_payload,
            headers={"X-RPay-Event": "bank.invoice.paid", "X-RPay-Signature": sig},
        )
        self.assertTrue(ev1["verified"])
        self.assertEqual(ev1["orderId"], "DH99")
        self.assertEqual(ev1["paidAmount"], 300000.0)

        ev2 = client.verify_webhook(
            raw_body=raw_body,
            headers={"X-RPay-Event": "bank.invoice.paid", "X-RPay-Body-Signature": body_sig},
        )
        self.assertTrue(ev2["verified"])

        stc_raw = json.dumps({"event": "bank.transactions", "bank": "vcb", "transactions": [{"transactionID": "1"}]})
        stc_sig = hmac_sha256_hex(secret, stc_raw)
        ev3 = client.verify_webhook(
            raw_body=stc_raw,
            headers={"X-STC-Event": "bank.transactions", "X-STC-HMAC-SHA256": stc_sig},
        )
        self.assertTrue(ev3["verified"])
        self.assertEqual(ev3["event"], "bank.transactions")


if __name__ == "__main__":
    unittest.main()

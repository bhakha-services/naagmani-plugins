"""
Unit tests for Indian PII and Credential Recognizers.
Tests true positives, format validation (Verhoeff, PAN, GSTIN, IFSC), and false positive rejection.
"""
import pytest
from shield.engine import PrivacyEngine
from shield.policy import PrivacyPolicy, PolicyAction
from shield.recognizers.verhoeff import calculate_verhoeff, validate_verhoeff


def test_verhoeff_checksum_algorithm():
    # Valid Aadhaar numbers with correct Verhoeff checksum
    # Example: 11-digit base 23456789012 + checksum
    base = "23456789012"
    check = calculate_verhoeff(base)
    valid_aadhaar = base + str(check)
    assert validate_verhoeff(valid_aadhaar) is True

    # Tampered single digit must fail
    tampered = valid_aadhaar[:-1] + str((int(valid_aadhaar[-1]) + 1) % 10)
    assert validate_verhoeff(tampered) is False

    # Transposition error (adjacent swap) must fail
    transposed = valid_aadhaar[:3] + valid_aadhaar[4] + valid_aadhaar[3] + valid_aadhaar[5:]
    assert validate_verhoeff(transposed) is False


def test_indian_aadhaar_recognition():
    engine = PrivacyEngine()
    policy = PrivacyPolicy("org", "proj", "production", confidence_threshold=0.6)

    # Valid Aadhaar with Verhoeff checksum
    base = "98765432109"
    check = calculate_verhoeff(base)
    valid_aadhaar = f"{base[:4]} {base[4:8]} {base[8:]}{check}"

    text = f"Customer UID is {valid_aadhaar}."
    results = engine.analyze(text, policy)
    aadhaar_results = [r for r in results if r.entity_type == "IN_AADHAAR"]
    assert len(aadhaar_results) == 1
    assert text[aadhaar_results[0].start : aadhaar_results[0].end] == valid_aadhaar

    # Invalid Aadhaar: first digit is '0' or '1'
    invalid_start = "0123 4567 8901"
    res_invalid = [r for r in engine.analyze(invalid_start, policy) if r.entity_type == "IN_AADHAAR"]
    assert len(res_invalid) == 0

    # Invalid Aadhaar: incorrect checksum
    bad_checksum = "2345 6789 0120"
    res_bad = [r for r in engine.analyze(bad_checksum, policy) if r.entity_type == "IN_AADHAAR"]
    assert len(res_bad) == 0


def test_indian_pan_recognition():
    engine = PrivacyEngine()
    policy = PrivacyPolicy("org", "proj", "production", confidence_threshold=0.6)

    # Valid PAN for an individual (4th char 'P')
    valid_pan = "ABCPE1234F"
    text = f"TDS deduction on PAN {valid_pan} confirmed"
    results = [r for r in engine.analyze(text, policy) if r.entity_type == "IN_PAN"]
    assert len(results) == 1
    assert text[results[0].start : results[0].end] == valid_pan

    # Valid PAN for a company (4th char 'C')
    valid_company_pan = "XYZCA9876Z"
    text_c = f"Vendor PAN is {valid_company_pan}"
    results_c = [r for r in engine.analyze(text_c, policy) if r.entity_type == "IN_PAN"]
    assert len(results_c) == 1

    # Invalid PAN: 4th char 'X' is not a recognized Indian PAN entity type
    invalid_pan = "ABCXE1234F"
    res_inv = [r for r in engine.analyze(f"PAN: {invalid_pan}", policy) if r.entity_type == "IN_PAN"]
    assert len(res_inv) == 0


def test_indian_gstin_recognition():
    engine = PrivacyEngine()
    policy = PrivacyPolicy("org", "proj", "production", confidence_threshold=0.6)

    # Valid GSTIN: State code 27 (Maharashtra) + valid PAN + 1Z5
    valid_gstin = "27ABCPE1234F1Z5"
    text = f"GST Invoice under {valid_gstin} issued"
    results = [r for r in engine.analyze(text, policy) if r.entity_type == "IN_GSTIN"]
    assert len(results) == 1
    assert text[results[0].start : results[0].end] == valid_gstin

    # Invalid GSTIN: State code 99 is other territory, 00 is invalid
    invalid_gstin = "00ABCDE1234F1Z5"
    res_inv = [r for r in engine.analyze(f"GSTIN: {invalid_gstin}", policy) if r.entity_type == "IN_GSTIN"]
    assert len(res_inv) == 0


def test_indian_ifsc_recognition():
    engine = PrivacyEngine()
    policy = PrivacyPolicy("org", "proj", "production", confidence_threshold=0.6)

    # Valid IFSC
    valid_ifsc = "HDFC0001234"
    text = f"Remit funds via IFSC {valid_ifsc}"
    results = [r for r in engine.analyze(text, policy) if r.entity_type == "IN_IFSC"]
    assert len(results) == 1
    assert text[results[0].start : results[0].end] == valid_ifsc

    # Invalid IFSC: 5th char must be '0'
    invalid_ifsc = "HDFC1001234"
    res_inv = [r for r in engine.analyze(f"IFSC: {invalid_ifsc}", policy) if r.entity_type == "IN_IFSC"]
    assert len(res_inv) == 0


def test_indian_upi_recognition():
    engine = PrivacyEngine()
    policy = PrivacyPolicy("org", "proj", "production", confidence_threshold=0.6)

    # Valid popular UPI handle
    text = "Send payment to rahul.sharma@okhdfcbank or merchant@paytm"
    results = [r for r in engine.analyze(text, policy) if r.entity_type == "IN_UPI"]
    assert len(results) == 2
    matched = {text[r.start : r.end] for r in results}
    assert "rahul.sharma@okhdfcbank" in matched
    assert "merchant@paytm" in matched


def test_credentials_recognition():
    engine = PrivacyEngine()
    policy = PrivacyPolicy("org", "proj", "production", confidence_threshold=0.6)

    text = (
        "OpenAI key: sk-proj-1234567890abcdef1234567890abcdef1234567890\n"
        "AWS key: AKIAIOSFODNN7EXAMPLE\n"
        "GitHub token: ghp_1234567890abcdef1234567890abcdef1234"
    )
    results = [r for r in engine.analyze(text, policy) if r.entity_type == "API_KEY"]
    assert len(results) >= 3

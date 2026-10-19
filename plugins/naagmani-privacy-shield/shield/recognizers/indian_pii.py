import re
from typing import List, Optional
from presidio_analyzer import Pattern, PatternRecognizer
from .verhoeff import validate_verhoeff

# Valid Indian State/UT Codes for GSTIN
VALID_GSTIN_STATE_CODES = {
    "01", "02", "03", "04", "05", "06", "07", "08", "09", "10",
    "11", "12", "13", "14", "15", "16", "17", "18", "19", "20",
    "21", "22", "23", "24", "25", "26", "27", "28", "29", "30",
    "31", "32", "33", "34", "35", "36", "37", "38", "97", "99"
}

# Valid 4th character entity types in Indian PAN
VALID_PAN_TYPES = {"P", "C", "H", "F", "A", "T", "B", "L", "J", "G"}


class IndianAadhaarRecognizer(PatternRecognizer):
    """
    Recognizes 12-digit Indian Aadhaar numbers with Verhoeff checksum validation.
    First digit cannot be 0 or 1.
    """
    ENTITY = "IN_AADHAAR"

    PATTERNS = [
        Pattern(
            "Aadhaar (spaced)",
            r"\b[2-9]\d{3}\s\d{4}\s\d{4}\b",
            0.95,
        ),
        Pattern(
            "Aadhaar (unspaced)",
            r"\b[2-9]\d{11}\b",
            0.90,
        ),
    ]

    CONTEXT = [
        "aadhaar", "aadhar", "uidai", "uid", "identity number", "national id",
        "mera aadhaar", "aadhaar card", "aadhar card", "aadhaar no", "aadhaar sankhya",
        "aadhar sankhya", "pehchan patra"
    ]

    def __init__(self):
        super().__init__(
            supported_entity=self.ENTITY,
            name="IndianAadhaarRecognizer",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="en",
        )

    def validate_result(self, pattern_text: str) -> bool:
        clean = pattern_text.replace(" ", "").replace("-", "")
        if len(clean) != 12 or not clean.isdigit():
            return False
        if clean[0] in ("0", "1"):
            return False
        return validate_verhoeff(clean)


class IndianPanRecognizer(PatternRecognizer):
    """
    Recognizes Indian Permanent Account Numbers (PAN).
    Format: 5 uppercase letters, 4 digits, 1 uppercase letter (e.g. ABCDE1234F).
    Validates 4th character entity type.
    """
    ENTITY = "IN_PAN"

    PATTERNS = [
        Pattern(
            "PAN (standard)",
            r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b",
            0.85,
        ),
    ]

    CONTEXT = [
        "pan", "pan card", "permanent account number", "income tax", "tax id", "pan no",
        "mera pan", "pan sankhya", "pan number", "pan vivaran"
    ]

    def __init__(self):
        super().__init__(
            supported_entity=self.ENTITY,
            name="IndianPanRecognizer",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="en",
        )

    def validate_result(self, pattern_text: str) -> bool:
        clean = pattern_text.strip().upper()
        if len(clean) != 10:
            return False
        return clean[3] in VALID_PAN_TYPES


class IndianGstinRecognizer(PatternRecognizer):
    """
    Recognizes Indian Goods and Services Tax Identification Number (GSTIN).
    Format: 15 alphanumeric characters: 2-digit state code + 10-char PAN + 1 entity code + 'Z' + 1 checksum char.
    """
    ENTITY = "IN_GSTIN"

    PATTERNS = [
        Pattern(
            "GSTIN (standard)",
            r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b",
            0.90,
        ),
    ]

    CONTEXT = [
        "gst", "gstin", "goods and services tax", "tax invoice", "gst number", "gst no",
        "mera gstin", "vyapar gst", "gst sankhya"
    ]

    def __init__(self):
        super().__init__(
            supported_entity=self.ENTITY,
            name="IndianGstinRecognizer",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="en",
        )

    def validate_result(self, pattern_text: str) -> bool:
        clean = pattern_text.strip().upper()
        if len(clean) != 15:
            return False
        state_code = clean[:2]
        if state_code not in VALID_GSTIN_STATE_CODES:
            return False
        pan_part = clean[2:12]
        return pan_part[3] in VALID_PAN_TYPES


class IndianIfscRecognizer(PatternRecognizer):
    """
    Recognizes Indian Financial System Code (IFSC) used for electronic funds transfer.
    Format: 4 alphabetic characters (bank code) + '0' + 6 alphanumeric characters (branch code).
    """
    ENTITY = "IN_IFSC"

    PATTERNS = [
        Pattern(
            "IFSC (standard)",
            r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
            0.85,
        ),
    ]

    CONTEXT = [
        "ifsc", "ifsc code", "bank code", "neft", "rtgs", "imps", "branch code", "bank branch",
        "khata", "bank ifsc", "shakha code"
    ]

    def __init__(self):
        super().__init__(
            supported_entity=self.ENTITY,
            name="IndianIfscRecognizer",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="en",
        )

    def validate_result(self, pattern_text: str) -> bool:
        clean = pattern_text.strip().upper()
        if len(clean) != 11:
            return False
        return clean[4] == "0"


class IndianUpiRecognizer(PatternRecognizer):
    """
    Recognizes Indian Unified Payments Interface (UPI) Virtual Payment Addresses (VPA).
    Format: username@bankhandle (e.g. user@okhdfcbank, merchant@paytm).
    """
    ENTITY = "IN_UPI"

    POPULAR_UPI_HANDLES = (
        "okhdfcbank|okaxis|oksbi|okicici|paytm|ybl|ibl|axl|upi|apl|"
        "allbank|federal|barodampay|pnb|unionbank|idfcbank|freecharge|"
        "airtel|postbank|jupiteraxis|fbl|indus|kotak|sliceaxis"
    )

    PATTERNS = [
        Pattern(
            "UPI (known handles)",
            rf"\b[a-zA-Z0-9.\-_]{{2,64}}@({POPULAR_UPI_HANDLES})\b",
            0.90,
        ),
        Pattern(
            "UPI (generic with context)",
            r"\b[a-zA-Z0-9.\-_]{2,64}@[a-zA-Z]{2,32}\b",
            0.30,
        ),
    ]

    CONTEXT = [
        "upi", "vpa", "bhim", "gpay", "phonepe", "paytm", "payment id", "send money to", "upi id",
        "paisa", "bhejo", "bhejiye", "transfer karo"
    ]

    def __init__(self):
        super().__init__(
            supported_entity=self.ENTITY,
            name="IndianUpiRecognizer",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="en",
        )

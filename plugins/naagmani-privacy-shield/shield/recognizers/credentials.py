from presidio_analyzer import Pattern, PatternRecognizer

class ApiKeyRecognizer(PatternRecognizer):
    """
    Recognizes high-risk enterprise credentials and API keys:
    OpenAI, Anthropic, AWS Access Keys, GitHub PATs, and JWTs.
    """
    ENTITY = "API_KEY"

    PATTERNS = [
        Pattern(
            "OpenAI API Key (legacy)",
            r"\bsk-[a-zA-Z0-9]{32,}\b",
            0.95,
        ),
        Pattern(
            "OpenAI Project Key",
            r"\bsk-proj-[a-zA-Z0-9_\-]{40,}\b",
            0.95,
        ),
        Pattern(
            "Anthropic API Key",
            r"\bsk-ant-[a-zA-Z0-9_\-]{32,}\b",
            0.95,
        ),
        Pattern(
            "AWS Access Key ID",
            r"\b(AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b",
            0.95,
        ),
        Pattern(
            "GitHub Personal Access Token",
            r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,255}\b",
            0.95,
        ),
        Pattern(
            "JSON Web Token (JWT)",
            r"\beyJ[a-zA-Z0-9_\-]{10,}\.eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}\b",
            0.90,
        ),
    ]

    CONTEXT = [
        "api key", "apikey", "secret", "token", "auth", "bearer",
        "access key", "private key", "credential", "password",
    ]

    def __init__(self):
        super().__init__(
            supported_entity=self.ENTITY,
            name="ApiKeyRecognizer",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="en",
        )

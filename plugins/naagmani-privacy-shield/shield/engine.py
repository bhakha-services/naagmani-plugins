"""
Core Privacy Engine for Naagmani Privacy Shield.
Orchestrates Presidio Analyzer, custom Indian PII recognizers, format validators,
and 128-bit CSPRNG placeholder generation.
"""
import os
import secrets
from typing import Dict, List, Optional, Set, Tuple

from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider

from .policy import PolicyAction, PrivacyPolicy
from .recognizers.credentials import ApiKeyRecognizer
from .recognizers.indian_pii import (
    IndianAadhaarRecognizer,
    IndianGstinRecognizer,
    IndianIfscRecognizer,
    IndianPanRecognizer,
    IndianUpiRecognizer,
)


def create_analyzer() -> AnalyzerEngine:
    """
    Initializes a fast, self-contained Presidio AnalyzerEngine using en_core_web_sm.
    Registers official Naagmani custom recognizers for Indian PII and API credentials.
    """
    model_name = "en_core_web_sm"
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bundled_model_dir = os.path.join(here, "vendor", "en_core_web_sm", "en_core_web_sm-3.8.0")
    if os.path.isdir(bundled_model_dir):
        model_name = bundled_model_dir

    nlp_config = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": model_name}],
    }
    provider = NlpEngineProvider(nlp_configuration=nlp_config)
    nlp_engine = provider.create_engine()
    analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])

    # Remove UK-specific NHS recognizer to avoid false positives on standard 10-digit phone numbers
    analyzer.registry.recognizers = [
        r for r in analyzer.registry.recognizers if "UK_NHS" not in r.supported_entities
    ]

    # Register custom Indian & Cloud Credential recognizers
    analyzer.registry.add_recognizer(IndianAadhaarRecognizer())
    analyzer.registry.add_recognizer(IndianPanRecognizer())
    analyzer.registry.add_recognizer(IndianGstinRecognizer())
    analyzer.registry.add_recognizer(IndianIfscRecognizer())
    analyzer.registry.add_recognizer(IndianUpiRecognizer())
    analyzer.registry.add_recognizer(ApiKeyRecognizer())

    return analyzer


class PrivacyEngine:
    """
    Stateful privacy engine per plugin runtime.
    Maintains analyzer instance and collision-checked 128-bit placeholder generator.
    """
    def __init__(self, analyzer: Optional[AnalyzerEngine] = None):
        self.analyzer = analyzer or create_analyzer()
        self._generated_placeholders: Set[str] = set()

    def generate_placeholder(self, entity_type: str) -> str:
        """
        Generates a cryptographically random 128-bit opaque placeholder:
        [<ENTITY_TAG>_<32hex_id>] (e.g. [PERSON_9f8b2c4e1a0d3f5e7b9c1a3d5e7f9a1b])
        With in-memory collision check.
        """
        clean_tag = entity_type.upper().replace(" ", "_")
        for _ in range(100):
            token_id = secrets.token_hex(16)  # 16 bytes = 128 bits of CSPRNG entropy
            placeholder = f"[{clean_tag}_{token_id}]"
            if placeholder not in self._generated_placeholders:
                self._generated_placeholders.add(placeholder)
                return placeholder

        raise RuntimeError("failed to generate unique placeholder after 100 collision attempts")

    def analyze(self, text: str, policy: PrivacyPolicy) -> List[RecognizerResult]:
        """
        Analyze text for protected entities, filtering by tenant policy confidence threshold
        and allow-list.
        """
        if not text or not text.strip():
            return []

        results = self.analyzer.analyze(
            text=text,
            language="en",
            score_threshold=policy.confidence_threshold,
        )

        filtered: List[RecognizerResult] = []
        for r in results:
            span_text = text[r.start : r.end]
            # Check tenant allow-list
            if policy.is_allowed(span_text):
                continue
            filtered.append(r)

        return filtered

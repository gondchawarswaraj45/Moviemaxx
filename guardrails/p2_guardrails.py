import re
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class GuardrailResult:
    is_safe: bool
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    violation_type: Optional[str] = None
    warning_message: Optional[str] = None
    sanitized_prompt: str = ""
    detected_patterns: List[str] = field(default_factory=list)

class P2GuardrailEngine:
    """
    Harness Engineering & P2 Guardrails Layer.
    Detects and blocks prompt injection, jailbreak attempts, Cypher/SQL injection,
    and out-of-scope system manipulation queries before reaching LLMs or database execution.
    """
    
    JAILBREAK_PATTERNS = [
        r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
        r"(?i)disregard\s+(all\s+)?(system|safety|guardrail|prior)\s+rules?",
        r"(?i)act\s+as\s+(an?\s+)?unrestricted|dan|jailbroken|developer\s+mode",
        r"(?i)system\s+prompt\s*(reveal|leak|show|print|output|display)",
        r"(?i)forget\s+(your|the)\s+(system\s+)?instructions?",
        r"(?i)you\s+are\s+now\s+in\s+(developer|god|unrestricted)\s+mode",
        r"(?i)bypass\s+(safety|content|guardrail|filtering)\s+filters?",
        r"(?i)override\s+system\s+prompt",
        r"(?i)pretend\s+you\s+have\s+no\s+rules",
        r"(?i)do\s+anything\s+now",
        r"(?i)reveal\s+your\s+(internal|secret|hidden)\s+prompt"
    ]

    CYPHER_INJECTION_PATTERNS = [
        r"(?i)DETACH\s+DELETE",
        r"(?i)DROP\s+DATABASE",
        r"(?i)DROP\s+INDEX",
        r"(?i)DROP\s+CONSTRAINT",
        r"(?i)CREATE\s+USER",
        r"(?i)ALTER\s+USER",
        r"(?i)MATCH\s*\([^)]*\)\s*DELETE",
        r"(?i)REMOVE\s+[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+",
        r"(?i)CALL\s+dbms\.",
        r"(?i)CALL\s+apoc\.trigger",
        r";\s*MATCH",
        r";\s*DROP",
        r";\s*CREATE",
        r";\s*DELETE"
    ]

    HARMFUL_PATTERNS = [
        r"(?i)how\s+to\s+(build|make|create)\s+(a\s+)?(bomb|explosive|weapon|virus)",
        r"(?i)execute\s+arbitrary\s+code",
        r"(?i)eval\s*\(",
        r"(?i)import\s+os\s*;\s*os\.system"
    ]

    def evaluate(self, prompt: str) -> GuardrailResult:
        if not prompt or not prompt.strip():
            return GuardrailResult(
                is_safe=False,
                risk_level="HIGH",
                violation_type="EMPTY_PROMPT",
                warning_message="Query string cannot be empty.",
                sanitized_prompt=""
            )

        sanitized = self._sanitize_input(prompt)
        detected_jailbreaks = []
        detected_cypher = []
        detected_harmful = []

        # 1. Check Jailbreak Patterns
        for pattern in self.JAILBREAK_PATTERNS:
            if re.search(pattern, prompt):
                detected_jailbreaks.append(pattern)

        # 2. Check Cypher Injection Patterns
        for pattern in self.CYPHER_INJECTION_PATTERNS:
            if re.search(pattern, prompt):
                detected_cypher.append(pattern)

        # 3. Check Harmful Patterns
        for pattern in self.HARMFUL_PATTERNS:
            if re.search(pattern, prompt):
                detected_harmful.append(pattern)

        # Violation Evaluation
        if detected_jailbreaks:
            return GuardrailResult(
                is_safe=False,
                risk_level="CRITICAL",
                violation_type="JAILBREAK_PROMPT_INJECTION",
                warning_message="[P2 Guardrail Triggered] Prompt contains system override or jailbreak instructions.",
                sanitized_prompt=sanitized,
                detected_patterns=detected_jailbreaks
            )

        if detected_cypher:
            return GuardrailResult(
                is_safe=False,
                risk_level="HIGH",
                violation_type="CYPHER_INJECTION_ATTEMPT",
                warning_message="[P2 Guardrail Triggered] Query contains unauthorized database manipulation syntax.",
                sanitized_prompt=sanitized,
                detected_patterns=detected_cypher
            )

        if detected_harmful:
            return GuardrailResult(
                is_safe=False,
                risk_level="CRITICAL",
                violation_type="HARMFUL_CONTENT_ATTEMPT",
                warning_message="[P2 Guardrail Triggered] Query contains restricted or unsafe commands.",
                sanitized_prompt=sanitized,
                detected_patterns=detected_harmful
            )

        # Check for subtle instruction escaping techniques (e.g. repeated quotes or unicode trickery)
        if len(prompt) > 1500:
            return GuardrailResult(
                is_safe=False,
                risk_level="MEDIUM",
                violation_type="EXCESSIVE_LENGTH",
                warning_message="[P2 Guardrail Triggered] Query length exceeds maximum permitted limit of 1500 characters.",
                sanitized_prompt=sanitized[:1500]
            )

        return GuardrailResult(
            is_safe=True,
            risk_level="LOW",
            violation_type=None,
            warning_message=None,
            sanitized_prompt=sanitized
        )

    def _sanitize_input(self, text: str) -> str:
        # Strip potential null bytes and control characters
        cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
        return cleaned.strip()

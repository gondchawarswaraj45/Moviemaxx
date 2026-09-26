from typing import Any, Dict
from .base_agent import BaseAgent
from guardrails import P2GuardrailEngine, GuardrailResult

class GuardrailAgent(BaseAgent):
    """
    Sub-Agent 1: P2 Guardrail & Safety Auditor Agent.
    Intercepts user query and evaluates harness engineering & safety policies.
    """
    def __init__(self):
        super().__init__(
            name="GuardrailAgent",
            role="Harness Engineering & P2 Safety Auditor"
        )
        self.engine = P2GuardrailEngine()

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = input_data.get("question", "")
        res: GuardrailResult = self.engine.evaluate(prompt)
        return {
            "agent": self.name,
            "is_safe": res.is_safe,
            "risk_level": res.risk_level,
            "violation_type": res.violation_type,
            "warning_message": res.warning_message,
            "sanitized_prompt": res.sanitized_prompt
        }

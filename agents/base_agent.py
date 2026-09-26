from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseAgent(ABC):
    """Abstract Base Class for Multi-Agent System."""
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role

    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

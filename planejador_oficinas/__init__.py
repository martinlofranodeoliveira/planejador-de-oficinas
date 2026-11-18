"""Planejamento offline de viabilidade para oficinas comunitárias."""
from .core import plan
from .errors import InputError

__all__ = ["plan", "InputError"]

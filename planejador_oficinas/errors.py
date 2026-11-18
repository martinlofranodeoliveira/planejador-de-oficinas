"""Exceção pública estável para entradas fora do contrato."""


class InputError(ValueError):
    """A entrada não pertence ao perfil finito documentado."""

"""Re-export of the canonical behavioural flags in engine/flags.py (one implementation).
The generator passes its own frozen flag thresholds from generator/config.yaml."""
from engine.flags import compute_flags  # noqa: F401

# presets.py
from __future__ import annotations
from dataclasses import dataclass, asdict
import json
from typing import Any


@dataclass
class Params:
    # Découpage (en ms)
    grain_ms_min: int = 80
    grain_ms_max: int = 220

    # Randomisation
    shuffle_amount: float = 0.70          # 0..1
    reverse_prob: float = 0.15            # 0..1
    gain_db_min: float = -6.0
    gain_db_max: float = 3.0
    keep_original_ratio: float = 0.25     # 0..1 (portion de segments gardés à leur place)

    # Intensité globale (multiplie l'effet, tout en restant borné)
    intensity: float = 1.00               # 0..2 (par ex)

    # Seed (reproductibilité)
    seed: int = 123456

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Params":
        p = Params()
        for k, v in d.items():
            if hasattr(p, k):
                setattr(p, k, v)
        return p


def save_preset(path: str, params: Params) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(params.to_dict(), f, ensure_ascii=False, indent=2)


def load_preset(path: str) -> Params:
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    return Params.from_dict(d)

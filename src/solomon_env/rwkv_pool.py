from __future__ import annotations
from typing import Optional, Dict
import threading

from rwkv.model import RWKV
from rwkv.utils import PIPELINE

TOKENIZER_X070 = "rwkv_vocab_v202502"   # x070 tokenizer
# If you temporarily use v5 models, switch to: "rwkv_vocab_v20230424"

class RWKVEngine:
    def __init__(self, model_path: str, strategy: str = "cuda fp16"):
        self.model_path = model_path
        self.strategy = strategy
        self._pipeline: Optional[PIPELINE] = None
        self._lock = threading.Lock()

    def ensure_loaded(self):
        if self._pipeline is None:
            with self._lock:
                if self._pipeline is None:
                    m = RWKV(model=self.model_path, strategy=self.strategy)
                    self._pipeline = PIPELINE(m, TOKENIZER_X070)

    def generate(self, prompt: str, max_tokens: int, temperature: float = 0.4, top_p: float = 0.9) -> str:
        self.ensure_loaded()
        return self._pipeline.generate(prompt, token_count=max_tokens, temperature=temperature, top_p=top_p).strip()


class RWKVPool:
    """Holds multiple engines. Load-on-first-use to save VRAM."""
    def __init__(self,
                 path_fast: str = "S:/Solomon/models/rwkv/RWKV-x070-World-1.5B-v3-20250127-ctx4096.pth",
                 path_deep: str = "S:/Solomon/models/rwkv/RWKV-x070-World-2.9B-v3-20250211-ctx4096.pth",
                 path_contemplate: Optional[str] = None,          # optional 7B (v5) or future x080
                 strategy_fast: str = "cuda fp16",
                 strategy_deep: str = "cuda fp16",
                 strategy_contemplate: str = "cuda fp16i8"):       # use mixed-precision for big model
        self.fast = RWKVEngine(path_fast, strategy_fast)
        self.deep = RWKVEngine(path_deep, strategy_deep)
        self.contemplate = RWKVEngine(path_contemplate, strategy_contemplate) if path_contemplate else None

    def pick_for_task(self, meta: dict) -> RWKVEngine:
        """
        meta: { "intent": "...", "complexity": 0..1, "needs_reflection": bool, "force_fast": bool }
        very simple rule-set; we can improve later.
        """
        if meta.get("force_fast"):
            return self.fast
        if meta.get("needs_reflection") or meta.get("complexity", 0) >= 0.6:
            return self.deep
        return self.fast

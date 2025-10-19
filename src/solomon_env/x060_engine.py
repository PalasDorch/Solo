from __future__ import annotations
import os, torch
from typing import Any, Optional, List
from tokenizers import Tokenizer

def _get_env(name: str, default: str = "") -> str:
    v = os.environ.get(name, default)
    return v.strip() if isinstance(v, str) else default

def _load_tokenizer(path_hint: Optional[str]) -> Tokenizer:
    cands: List[str] = []
    if path_hint:
        cands.append(path_hint)
    cands.extend([
        r"S:\Solomon\models\rwkv\20B_tokenizer.json",
        r"S:\Solomon\models\rwkv\rwkv_vocab_v20230424.json",
    ])
    for p in cands:
        if p and os.path.exists(p):
            return Tokenizer.from_file(p)
    raise FileNotFoundError("Tokenizer JSON not found. Set RWKV_TOKENIZER_PATH.")

def _get_v6_class():
    import importlib
    m = importlib.import_module("vendor.rwkv_x060")
    cls = getattr(m, "RWKV_RNN", None)
    if cls is None:
        cls = getattr(m, "RWKV", None)
    if cls is None:
        raise ImportError("vendor.rwkv_x060 has no RWKV_RNN or RWKV")
    return cls


# =============================================================
#                     X060Engine (RNN runner)
# =============================================================
class X060Engine:
    def __init__(self,
                 model_path: Optional[str] = None,
                 device: Optional[str] = None,
                 dtype: str = "float16",
                 tok_path: Optional[str] = None):
        self.model_path = model_path or _get_env("RWKV_MODEL_PATH")
        self.device     = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.dtype      = dtype
        self.tok_path   = tok_path or _get_env("RWKV_TOKENIZER_PATH")
        if not self.model_path:
            raise RuntimeError("RWKV_MODEL_PATH not set")

        self._model = None
        self._tok   = None

    # ---------------- Core ----------------
    def load(self):
        from types import SimpleNamespace
        RWKV_RNN = _get_v6_class()

        m = self.model_path[:-4] if self.model_path.lower().endswith(".pth") else self.model_path
        float_mode = "fp16" if "16" in str(self.dtype).lower() else "fp32"
        args = SimpleNamespace(MODEL_NAME=m, RUN_DEVICE=self.device, FLOAT_MODE=float_mode)
        self._model = RWKV_RNN(args)
        self._tok = _load_tokenizer(self.tok_path)
        return self

    # ---------------- Token Helpers ----------------
    def encode(self, text: str) -> list[int]:
        return self._tok.encode(text).ids

    def decode(self, ids: list[int]) -> str:
        return self._tok.decode(ids)

    # ---------------- RNN Forward Loop ----------------
    @torch.inference_mode()
    def _prime(self, ids: list[int]):
        state = None
        logits = None
        for tid in ids:
            logits, state = self._model.forward(int(tid), state)
        return logits, state

    @staticmethod
    def _sample_top_p(logits: torch.Tensor, temperature: float, top_p: float) -> int:
        if temperature <= 0:
            return int(torch.argmax(logits).item())
        logits = logits.float() / max(1e-6, float(temperature))
        probs  = torch.softmax(logits, dim=-1)
        vals, idx = torch.sort(probs, descending=True)
        cdf = torch.cumsum(vals, dim=-1)
        mask = cdf <= top_p
        if not torch.any(mask):
            mask[0] = True
        vals = vals[mask]; idx = idx[mask]
        pick = torch.multinomial(vals, 1)[0]
        return int(idx[pick].item())

    # ---------------- Generation ----------------
    @torch.inference_mode()
    def generate(self, prompt: str, max_tokens: int = 128,
                 temperature: float = 0.7, top_p: float = 0.9) -> str:
        if self._model is None:
            self.load()

        in_ids = self.encode(prompt)
        logits, state = self._prime(in_ids) if in_ids else (None, None)
        out_ids: list[int] = []

        for _ in range(max(1, int(max_tokens))):
            if logits is None:
                space_id = self.encode(" ")[0]
                logits, state = self._model.forward(int(space_id), state)

            token = self._sample_top_p(
                logits[0] if logits.ndim == 2 else logits,
                temperature, top_p
            )
            out_ids.append(token)
            logits, state = self._model.forward(int(token), state)

        return self.decode(out_ids)
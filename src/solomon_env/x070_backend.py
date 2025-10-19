from __future__ import annotations
import os
import torch

class X070NotInstalled(RuntimeError):
    pass

class X070Backend:
    """
    Thin wrapper around an RWKV-x070 runner.
    Tries these imports (provide one of them):
      - import rwkv_x070  (expects class RWKV)
      - from rwkv_x070.runner import RWKV
      - from vendor.rwkv_x070.runner import RWKV
    """
    def __init__(self, model_path: str,
                 device: str = "cuda" if torch.cuda.is_available() else "cpu",
                 dtype: str = "float16"):
        self.model_path = model_path
        self.device = device
        self.dtype = dtype
        self._runner_cls = None
        self._model = None
        self._import_runner()

    def _import_runner(self) -> None:
        tried = []
        try:
            import rwkv_x070 as mod  # type: ignore
            self._runner_cls = getattr(mod, "RWKV", None)
            if self._runner_cls is not None:
                return
            tried.append("rwkv_x070.RWKV")
        except Exception:
            tried.append("rwkv_x070 (module)")
        try:
            from rwkv_x070.runner import RWKV as Runner  # type: ignore
            self._runner_cls = Runner
            return
        except Exception:
            tried.append("rwkv_x070.runner.RWKV")
        try:
            from vendor.rwkv_x070.runner import RWKV as Runner  # type: ignore
            self._runner_cls = Runner
            return
        except Exception:
            tried.append("vendor.rwkv_x070.runner.RWKV")

        where = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        raise X070NotInstalled(
            "RWKV-x070 runner not found. Expected one of:\n"
            "  - import rwkv_x070 (with class RWKV)\n"
            "  - from rwkv_x070.runner import RWKV\n"
            "  - from vendor.rwkv_x070.runner import RWKV\n\n"
            f"Place the x070 runner in your PYTHONPATH (e.g. under {where}\\vendor\\rwkv_x070) "
            "and ensure it exposes a `RWKV` class compatible with token-step forward."
        )

    def load(self):
        if self._runner_cls is None:
            self._import_runner()
        try:
            self._model = self._runner_cls(self.model_path, self.device, self.dtype)  # type: ignore
        except TypeError:
            self._model = self._runner_cls(model_path=self.model_path, device=self.device, dtype=self.dtype)  # type: ignore
        return self

    @torch.inference_mode()
    def forward_token(self, token_id: int, state):
        if self._model is None:
            raise RuntimeError("x070 backend is not loaded. Call .load() first.")
        t = torch.tensor([token_id], dtype=torch.long, device=self.device)
        logits, new_state = self._model.forward(t, state)  # type: ignore
        if logits.dim() == 2:
            logits = logits[0]
        return logits, new_state

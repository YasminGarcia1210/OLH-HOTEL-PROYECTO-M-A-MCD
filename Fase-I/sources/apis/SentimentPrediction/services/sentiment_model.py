"""
Carga del checkpoint p91 (encoder.* + cabezal MLP) y predicción por lotes.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
from pathlib import Path

import torch
import torch.nn as nn
from huggingface_hub import snapshot_download
from safetensors.torch import load_file
from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer

logger = logging.getLogger(__name__)

_load_lock = threading.Lock()
_tokenizer = None
_model = None
_device: torch.device | None = None


class P91ClassificationHead(nn.Module):
    """Cabezal MLP alineado al checkpoint (768→512→128→3); usa solo el token CLS."""

    def __init__(self) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(768, 512),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(512, 128),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(128, 3),
        )

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        return self.layers(hidden_states[:, 0])


def _map_checkpoint_to_model(ckpt: dict, model: nn.Module) -> None:
    sd = model.state_dict()
    with torch.no_grad():
        for k, v in ckpt.items():
            if k == "class_weights":
                continue
            if k.startswith("encoder."):
                nk = "roberta." + k[8:]
            elif k.startswith("classifier."):
                nk = "classifier.layers." + k.split(".", 1)[1]
            else:
                nk = k
            if nk not in sd:
                continue
            if sd[nk].shape == v.shape:
                sd[nk].copy_(v)
            elif nk == "roberta.embeddings.position_embeddings.weight":
                n = v.shape[0]
                sd[nk][:n].copy_(v)
            else:
                logger.warning("Omitiendo clave por forma incompatible: %s", nk)


def _resolve_model_ref_to_dir(ref: str) -> str:
    """Ruta local existente, o id `org/repo` de Hugging Face descargado a caché."""
    path = Path(ref).expanduser()
    if path.is_dir():
        return str(path.resolve())
    # Un solo `/` evita rutas absolutas tipo `/tmp/...` y coincide con ids HF habituales.
    if ref.count("/") == 1 and not ref.startswith(("/", "\\")):
        logger.info("Descargando snapshot del Hub: %s", ref)
        # Windows sin modo desarrollador no permite symlinks en el caché del Hub.
        if sys.platform == "win32":
            os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")
        return snapshot_download(repo_id=ref)
    return str(path)


def load_engine(model_dir: str, device_str: str):
    """
    Carga tokenizer y modelo una vez. thread-safe.
    """
    global _tokenizer, _model, _device

    with _load_lock:
        if _model is not None and _tokenizer is not None:
            return _tokenizer, _model, _device

        _device = torch.device(device_str if torch.cuda.is_available() and device_str == "cuda" else "cpu")
        model_dir = _resolve_model_ref_to_dir(model_dir)
        logger.info("Cargando modelo de sentimiento desde %s (device=%s)", model_dir, _device)

        ckpt_path = f"{model_dir}/model.safetensors"
        ckpt = load_file(ckpt_path)

        config = AutoConfig.from_pretrained(model_dir, local_files_only=True)
        model = AutoModelForSequenceClassification.from_config(config)
        model.classifier = P91ClassificationHead()
        _map_checkpoint_to_model(ckpt, model)
        model.to(_device)
        model.eval()

        tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)

        _tokenizer = tokenizer
        _model = model

        logger.info("Modelo de sentimiento listo.")
        return tokenizer, model, _device


def _normalize_sentimiento_label(raw) -> str:
    label = str(raw).strip().lower()
    if label not in ("negativo", "neutro", "positivo"):
        return "neutro"
    return label


def _probs_por_clase(
    id2label: dict | None, probs_row: torch.Tensor
) -> dict[str, float]:
    """Acumula softmax por etiqueta canónica (negativo / neutro / positivo)."""
    acum = {"negativo": 0.0, "neutro": 0.0, "positivo": 0.0}
    if id2label is None:
        n = int(probs_row.shape[0])
        if n == 3:
            acum["negativo"] = float(probs_row[0].item())
            acum["neutro"] = float(probs_row[1].item())
            acum["positivo"] = float(probs_row[2].item())
        return acum
    for j in range(probs_row.shape[0]):
        raw = id2label.get(j)
        if raw is None and isinstance(id2label, dict):
            raw = id2label.get(str(j))
        key = _normalize_sentimiento_label(raw) if raw is not None else "neutro"
        acum[key] += float(probs_row[j].item())
    return acum


@torch.inference_mode()
def predict_batch(
    tokenizer,
    model: nn.Module,
    device: torch.device,
    texts: list[str],
    max_length: int = 128,
) -> list[tuple[str, float, dict[str, float]]]:
    enc = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=max_length,
        return_tensors="pt",
    )
    enc = {k: v.to(device) for k, v in enc.items()}
    logits = model(**enc).logits
    probs = torch.softmax(logits, dim=-1)
    conf, pred_ids = probs.max(dim=-1)
    id2label = model.config.id2label
    out: list[tuple[str, float, dict[str, float]]] = []
    for i in range(len(texts)):
        pred_idx = int(pred_ids[i].item())
        if id2label is not None:
            raw = id2label.get(pred_idx)
            if raw is None:
                raw = id2label.get(str(pred_idx))
            if raw is None:
                raw = "neutro"
        else:
            raw = "neutro"
        label = _normalize_sentimiento_label(raw)
        prob_map = _probs_por_clase(id2label, probs[i])
        out.append((label, float(conf[i].item()), prob_map))
    return out

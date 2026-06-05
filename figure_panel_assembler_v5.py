# -*- coding: utf-8 -*-
r"""
figure_panel_assembler_v4.py
============================
Armado de figuras compuestas / multipanel para publicación.

Reescritura de v3 enfocada en los puntos débiles reales:

  1. Motor de layout anti-solapamiento (constrained_layout para grillas;
     layout manual para el caso del inserto, que pelea con constrained_layout).
     Honra width/height_ratios. Resuelve "que entre bien sin pisar los nombres
     de los ejes" sin depender de wspace/hspace a ojo.
  2. Round-trip fiel con figure_editor3: el guardado reconstruible delega en
     figure_editor3.save_figure_data y congela posiciones absolutas marcando
     layout_engine.serialize_positions=True, de modo que el editor recargue el
     panel idéntico (sin re-correr un layout que rompa los ratios).
  3. Sin duplicar la serialización: se reutilizan los helpers probados de
     figure_editor3 (con fallback mínimo si el módulo no está disponible).
  4. Menú dedicado de rótulos: a) / (a) / a. / A) / i) / I) / 1), posición en
     cualquiera de los 9 puntos interiores, exterior arriba-izquierda u offset
     numérico, override por panel, control de tipografía.
  5. Inserto con piso de legibilidad: en vez de un multiplicador ciego, se fija
     un tamaño mínimo de fuente (pt) y se reduce la densidad de ticks para que
     el inserto reducido se lea (cf. Rougier, Droettboom & Bourne 2014,
     PLoS Comput Biol 10(9):e1003833, "Ten Simple Rules for Better Figures").
  6. GUI ligera (matplotlib.widgets) para acomodar ratios/espaciado/fuente en
     vivo, portable a cualquier backend interactivo (Qt/Tk), sin dependencias
     nuevas.

Fuentes aceptadas por panel:
  * raíz del editor:    "raiz"        -> raiz.json (+ raiz.csv)
  * JSON del editor:    "raiz.json"
  * CSV:                "raiz.csv"    (si existe raiz.json usa el JSON)
  * raster:             .png .jpg .jpeg .tif .tiff .bmp .webp
  * vectorial:          .pdf (PyMuPDF)  .svg (cairosvg)  .eps (PIL+Ghostscript)

Si no se indica path, se busca en el directorio de trabajo actual.

Guardado:
  * Si TODAS las fuentes son JSON/CSV reconstruibles -> JSON + CSV + PNG + PDF
    (recargable en figure_editor3).
  * Si hay raster/vectorial -> PNG + PDF + <base>_panel_meta.json con la receta.

Dependencias opcionales:
    pip install pymupdf      # PDF
    pip install cairosvg     # SVG
    (EPS: requiere Ghostscript instalado en el sistema)

Uso interactivo:
    python figure_panel_assembler_v4.py

Uso programático:
    from figure_panel_assembler_v4 import create_composite_figure_from_files, save_composite_figure
    fig = create_composite_figure_from_files(["fig1", "fig2.pdf"], layout="1x2", show=False)
    save_composite_figure(fig, "panel_final")
"""
from __future__ import annotations

import csv
import sys
import json
import time
import queue
import string
import threading
import importlib
import importlib.util
import warnings
from collections import OrderedDict
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import collections as mcoll
from matplotlib.patches import Rectangle
from matplotlib.ticker import MaxNLocator

_FORMAT_VERSION = 110

# ─────────────────────────────────────────────────────────────────────────────
#  Acoplamiento con figure_editor3 (DRY) con fallback mínimo
# ─────────────────────────────────────────────────────────────────────────────
def _import_figure_editor():
    """Importa figure_editor3 desde sys.path o desde el directorio del script.

    Devuelve el módulo o None. No es un error duro: si no está, se usan helpers
    locales mínimos (fidelidad reducida, con aviso)."""
    for name in ("figure_editor3", "figure_editor"):
        try:
            return importlib.import_module(name)
        except Exception:
            pass
    here = Path(__file__).resolve().parent
    for cand in ("figure_editor3.py", "figure_editor.py"):
        p = here / cand
        if p.exists():
            try:
                spec = importlib.util.spec_from_file_location(p.stem, str(p))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore[union-attr]
                return mod
            except Exception as exc:  # pragma: no cover
                warnings.warn(f"No se pudo cargar {cand}: {exc}")
    return None


_FE = _import_figure_editor()
_HAS_FE = _FE is not None
if not _HAS_FE:
    warnings.warn(
        "figure_editor3 no está disponible: se usan reconstructores locales mínimos. "
        "El guardado JSON/CSV reconstruible y la máxima fidelidad cosmética requieren "
        "figure_editor3.py en el path o junto a este script."
    )


def _fe_call(name, *args, **kwargs):
    fn = getattr(_FE, name, None) if _HAS_FE else None
    if fn is None:
        raise RuntimeError(f"figure_editor3.{name} no disponible.")
    return fn(*args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers de bajo nivel (espejo de figure_editor3; se delega si está)
# ─────────────────────────────────────────────────────────────────────────────
def _to_float(x: Any, default: Any = None) -> Any:
    try:
        return float(x)
    except Exception:
        return x if default is None else default


def _jsonable(obj: Any) -> Any:
    if _HAS_FE and hasattr(_FE, "_jsonable"):
        return _FE._jsonable(obj)
    if obj is None:
        return None
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (tuple, list)):
        return [_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    return obj


def _base_path(filename: str | Path) -> Path:
    return Path(filename).with_suffix("")


def _safe_marker(m):
    if m is None:
        return ""
    s = str(m).strip().lower()
    return "" if s in {"none", "null", "nan"} else m


def _safe_linestyle(ls):
    if ls is None:
        return "-"
    s = str(ls).strip().lower()
    return "None" if s in {"none", "null", "nan"} else ls


def _float_or_none(v):
    try:
        f = float(v)
        return f if np.isfinite(f) else None
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
#  Layouts soportados
# ─────────────────────────────────────────────────────────────────────────────
_PANEL_LAYOUTS = OrderedDict([
    ("1x1",             {"rows": 1, "cols": 1, "n": 1, "label": "1x1: figura simple"}),
    ("1x1_inset",       {"rows": 1, "cols": 1, "n": 2, "label": "1x1: figura 1 con inserto de figura 2"}),
    ("1x2",             {"rows": 1, "cols": 2, "n": 2, "label": "1x2: 1 fila x 2 columnas"}),
    ("2x1",             {"rows": 2, "cols": 1, "n": 2, "label": "2x1: 2 filas x 1 columna"}),
    ("1x3",             {"rows": 1, "cols": 3, "n": 3, "label": "1x3: 1 fila x 3 columnas"}),
    ("3x1",             {"rows": 3, "cols": 1, "n": 3, "label": "3x1: 3 filas x 1 columna"}),
    ("2x2",             {"rows": 2, "cols": 2, "n": 4, "label": "2x2"}),
    ("3x2",             {"rows": 3, "cols": 2, "n": 6, "label": "3x2: 3 filas x 2 columnas"}),
    ("2x3",             {"rows": 2, "cols": 3, "n": 6, "label": "2x3: 2 filas x 3 columnas"}),
    ("3x3",             {"rows": 3, "cols": 3, "n": 9, "label": "3x3"}),
    ("1x2_split_left",  {"rows": 2, "cols": 2, "n": 3, "label": "Split (apiladas): 2 medias APILADAS a la IZQUIERDA + entera a la DERECHA"}),
    ("1x2_split_right", {"rows": 2, "cols": 2, "n": 3, "label": "Split (apiladas): entera a la IZQUIERDA + 2 medias APILADAS a la DERECHA"}),
    ("1x2_split_top",   {"rows": 2, "cols": 2, "n": 3, "label": "Split (lado a lado): 2 medias LADO A LADO ARRIBA + entera ABAJO"}),
    ("1x2_split_bottom",{"rows": 2, "cols": 2, "n": 3, "label": "Split (lado a lado): entera ARRIBA + 2 medias LADO A LADO ABAJO"}),
])

_RASTER_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
_VECTOR_EXTS = {".pdf", ".eps", ".svg"}
_DATA_EXTS = {".json", ".csv"}

_INSET_PRESETS = OrderedDict([
    ("arriba_derecha", (0.55, 0.55, 0.42, 0.40)),
    ("arriba_izquierda", (0.08, 0.55, 0.42, 0.40)),
    ("abajo_derecha", (0.55, 0.10, 0.42, 0.40)),
    ("abajo_izquierda", (0.08, 0.10, 0.42, 0.40)),
    ("centro", (0.32, 0.32, 0.40, 0.40)),
])


def list_panel_layouts() -> dict[str, dict[str, Any]]:
    return {k: dict(v) for k, v in _PANEL_LAYOUTS.items()}


def _layout_rows_cols(layout: str) -> tuple[int, int]:
    info = _PANEL_LAYOUTS[layout]
    return int(info["rows"]), int(info["cols"])


# ─────────────────────────────────────────────────────────────────────────────
#  Resolución y clasificación de fuentes
# ─────────────────────────────────────────────────────────────────────────────
def _source_path_from_user_text(text: str | Path) -> Path:
    raw = str(text).strip().strip('"').strip("'")
    p = Path(raw).expanduser()
    if not p.suffix:
        for ext in (".json", ".csv", ".png", ".pdf", ".svg", ".eps",
                    ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"):
            q = p.with_suffix(ext)
            if q.exists():
                return q
        return p
    if p.suffix.lower() == ".csv":
        q = p.with_suffix(".json")
        if q.exists():
            return q
    return p


def _classify_panel_source(path: str | Path) -> tuple[str, Path]:
    """Devuelve ('json'|'csv'|'raster'|'vector'|'missing', path_resuelto)."""
    p = _source_path_from_user_text(path)
    ext = p.suffix.lower()
    if ext == ".json":
        return "json", p
    if ext == ".csv":
        return ("json", p.with_suffix(".json")) if p.with_suffix(".json").exists() else ("csv", p)
    if ext in _RASTER_EXTS:
        return "raster", p
    if ext in _VECTOR_EXTS:
        return "vector", p
    for cand_ext, kind in ((".json", "json"), (".csv", "csv"), (".png", "raster"), (".pdf", "vector")):
        if p.with_suffix(cand_ext).exists():
            return kind, p.with_suffix(cand_ext)
    return "missing", p


def _load_json(path: str | Path) -> tuple[dict, Path]:
    p = _source_path_from_user_text(path)
    if p.suffix.lower() != ".json":
        p = p.with_suffix(".json")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f), p


# ─────────────────────────────────────────────────────────────────────────────
#  Caché de fuentes (evita re-rasterizar PDF/imagenes al re-ajustar ratios)
# ─────────────────────────────────────────────────────────────────────────────
def _file_cache_token(path: str | Path) -> tuple[str, float, int]:
    p = Path(path)
    try:
        st = p.stat()
        return (str(p.resolve()), float(st.st_mtime), int(st.st_size))
    except Exception:
        return (str(p), 0.0, 0)


def _cache_get(cache: dict | None, key):
    return None if cache is None else cache.get(key)


def _cache_set(cache: dict | None, key, value):
    if cache is not None:
        cache[key] = value
    return value


# ─────────────────────────────────────────────────────────────────────────────
#  Lectura raster / vectorial -> ndarray RGB
# ─────────────────────────────────────────────────────────────────────────────
def _crop_white_margins_array(arr: np.ndarray, tol: int = 250, pad_px: int = 6) -> np.ndarray:
    a = arr[..., :3] if arr.ndim == 3 and arr.shape[2] >= 3 else arr
    mask = np.any(a < tol, axis=2) if a.ndim == 3 else (a < tol)
    if not mask.any():
        return arr
    ys, xs = np.where(mask)
    y0, y1 = max(int(ys.min()) - pad_px, 0), min(int(ys.max()) + pad_px + 1, arr.shape[0])
    x0, x1 = max(int(xs.min()) - pad_px, 0), min(int(xs.max()) + pad_px + 1, arr.shape[1])
    return arr[y0:y1, x0:x1]


def _read_raster_image(path: str | Path, crop_white: bool = True,
                       crop_tol: int = 250, crop_pad_px: int = 6) -> np.ndarray:
    from PIL import Image
    img = Image.open(path)
    if img.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        bg.alpha_composite(img.convert("RGBA"))
        img = bg.convert("RGB")
    else:
        img = img.convert("RGB")
    arr = np.asarray(img)
    return _crop_white_margins_array(arr, tol=crop_tol, pad_px=crop_pad_px) if crop_white else arr


def _render_pdf_to_array(path: str | Path, page: int = 0, dpi: int = 300,
                         crop_white: bool = True, crop_tol: int = 250, crop_pad_px: int = 6) -> np.ndarray:
    try:
        import fitz  # PyMuPDF
    except Exception as e:
        raise RuntimeError("Para insertar PDF instalá PyMuPDF: pip install pymupdf") from e
    doc = fitz.open(str(Path(path)))
    try:
        if len(doc) == 0:
            raise ValueError(f"PDF sin páginas: {path}")
        page = max(0, min(int(page), len(doc) - 1))
        pg = doc.load_page(page)
        zoom = float(dpi) / 72.0
        pix = pg.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n > 3:
            arr = arr[:, :, :3]
        return _crop_white_margins_array(arr, tol=crop_tol, pad_px=crop_pad_px) if crop_white else arr
    finally:
        doc.close()


def _read_vector_or_raster(path: str | Path, dpi: int = 300, crop_white: bool = True,
                           crop_tol: int = 250, crop_pad_px: int = 6) -> np.ndarray:
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".pdf":
        return _render_pdf_to_array(p, dpi=dpi, crop_white=crop_white, crop_tol=crop_tol, crop_pad_px=crop_pad_px)
    if ext == ".svg":
        try:
            import cairosvg
        except Exception as e:
            raise RuntimeError("Para insertar SVG instalá cairosvg: pip install cairosvg") from e
        import io
        from PIL import Image
        png_bytes = cairosvg.svg2png(url=str(p), dpi=dpi)
        arr = np.asarray(Image.open(io.BytesIO(png_bytes)).convert("RGB"))
        return _crop_white_margins_array(arr, tol=crop_tol, pad_px=crop_pad_px) if crop_white else arr
    if ext == ".eps":
        try:
            return _read_raster_image(p, crop_white=crop_white, crop_tol=crop_tol, crop_pad_px=crop_pad_px)
        except Exception as e:
            raise RuntimeError("No se pudo rasterizar EPS (suele requerir Ghostscript instalado).") from e
    return _read_raster_image(p, crop_white=crop_white, crop_tol=crop_tol, crop_pad_px=crop_pad_px)


def _read_image_cached(path, *, dpi=300, crop_white=True, cache=None) -> np.ndarray:
    key = ("image",) + _file_cache_token(path) + (int(dpi), bool(crop_white))
    hit = _cache_get(cache, key)
    if hit is not None:
        return hit
    return _cache_set(cache, key, _read_vector_or_raster(path, dpi=dpi, crop_white=crop_white))


def _load_json_cached(path, cache=None):
    key = ("json",) + _file_cache_token(path)
    hit = _cache_get(cache, key)
    if hit is not None:
        return hit
    return _cache_set(cache, key, _load_json(path))


def _draw_image_array_into(ax, arr: np.ndarray):
    ax.imshow(arr)
    ax.set_xticks([])
    ax.set_yticks([])
    try:
        ax.set_axis_off()
    except Exception:
        pass
    return ax


# ─────────────────────────────────────────────────────────────────────────────
#  Aplicadores cosméticos: se delega en figure_editor3 si está; si no, mínimos
# ─────────────────────────────────────────────────────────────────────────────
def _apply_text(target, spec):
    if _HAS_FE and hasattr(_FE, "_apply_text"):
        return _FE._apply_text(target, spec)
    if target is None or spec is None:
        return
    if isinstance(spec, str):
        try:
            target.set_text(spec)
        except Exception:
            pass
        return
    if not isinstance(spec, dict):
        return
    for setter, key in [(target.set_text, "text"), (target.set_fontsize, "fontsize"),
                        (target.set_fontweight, "fontweight"), (target.set_fontstyle, "fontstyle"),
                        (target.set_color, "color")]:
        if spec.get(key) is not None:
            try:
                setter(spec[key])
            except Exception:
                pass
    if spec.get("visible") is not None:
        try:
            target.set_visible(bool(spec["visible"]))
        except Exception:
            pass


def _apply_ticks(ax, spec, axis="x"):
    if _HAS_FE and hasattr(_FE, "_apply_ticks"):
        return _FE._apply_ticks(ax, spec, axis)


def _apply_spines(ax, spines):
    if _HAS_FE and hasattr(_FE, "_apply_spines"):
        return _FE._apply_spines(ax, spines)
    if not isinstance(spines, dict):
        return
    for name, sp in spines.items():
        if name in ax.spines and isinstance(sp, dict) and sp.get("visible") is not None:
            try:
                ax.spines[name].set_visible(bool(sp["visible"]))
            except Exception:
                pass


def _apply_grid(ax, grid):
    if _HAS_FE and hasattr(_FE, "_apply_grid"):
        return _FE._apply_grid(ax, grid)
    if isinstance(grid, dict) and grid.get("visible"):
        try:
            ax.grid(True)
        except Exception:
            pass


def _apply_annotation_bbox(txt, spec):
    if _HAS_FE and hasattr(_FE, "_apply_annotation_bbox"):
        return _FE._apply_annotation_bbox(txt, spec)


def _rebuild_legend(ax, leginfo):
    if _HAS_FE and hasattr(_FE, "_rebuild_legend"):
        return _FE._rebuild_legend(ax, leginfo)
    if isinstance(leginfo, dict) and (leginfo.get("entries") or leginfo.get("visible")):
        try:
            ax.legend()
        except Exception:
            pass


def _normalize_axd(axd):
    if _HAS_FE and hasattr(_FE, "_normalize_axd"):
        return _FE._normalize_axd(axd)
    return dict(axd)


def _auto_reposition_legend(ax, leginfo, policy="auto_if_overlap"):
    if _HAS_FE and hasattr(_FE, "_auto_reposition_legend"):
        try:
            return _FE._auto_reposition_legend(ax, leginfo, policy=policy)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
#  Escalado de fuentes y piso de legibilidad (insertos)
# ─────────────────────────────────────────────────────────────────────────────
def _iter_axis_text_objs(ax, include_panel_label=False):
    objs = [ax.title, ax.xaxis.label, ax.yaxis.label]
    try:
        objs += list(ax.get_xticklabels()) + list(ax.get_yticklabels())
    except Exception:
        pass
    leg = ax.get_legend()
    if leg is not None:
        try:
            objs += [leg.get_title()] + list(leg.get_texts())
        except Exception:
            pass
    for t in getattr(ax, "texts", []):
        if (not include_panel_label) and getattr(t, "_pa_panel_label", False):
            continue
        objs.append(t)
    return [o for o in objs if o is not None]


def _scale_axis_fonts(ax, scale=1.0):
    try:
        scale = float(scale)
    except Exception:
        return
    if abs(scale - 1.0) < 1e-9:
        return
    for o in _iter_axis_text_objs(ax):
        try:
            fs = o.get_fontsize()
            if fs:
                o.set_fontsize(float(fs) * scale)
        except Exception:
            pass


def _make_inset_legible(inset_ax, *, min_pt=7.0, label_pt=8.0, max_ticks=4,
                        thin_legend=True):
    """Garantiza legibilidad del inserto reducido: piso de fuente + menos ticks.

    En vez de escalar todo por un factor ciego, fija tamaños absolutos legibles
    y reduce la densidad de ticks (que es lo que vuelve ilegible un inserto)."""
    try:
        inset_ax.xaxis.label.set_fontsize(label_pt)
        inset_ax.yaxis.label.set_fontsize(label_pt)
    except Exception:
        pass
    try:
        inset_ax.tick_params(labelsize=min_pt)
        for lb in list(inset_ax.get_xticklabels()) + list(inset_ax.get_yticklabels()):
            if lb.get_fontsize() < min_pt:
                lb.set_fontsize(min_pt)
    except Exception:
        pass
    try:
        if inset_ax.get_xscale() == "linear":
            inset_ax.xaxis.set_major_locator(MaxNLocator(nbins=max_ticks, prune="both"))
        if inset_ax.get_yscale() == "linear":
            inset_ax.yaxis.set_major_locator(MaxNLocator(nbins=max_ticks, prune="both"))
    except Exception:
        pass
    if thin_legend:
        leg = inset_ax.get_legend()
        if leg is not None:
            try:
                for t in leg.get_texts():
                    if t.get_fontsize() < min_pt:
                        t.set_fontsize(min_pt)
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
#  Leyendas: detección de solapamiento, reubicación y política
# ─────────────────────────────────────────────────────────────────────────────
_LEGEND_LOCS = ["best", "upper right", "upper left", "lower left", "lower right",
                "right", "center left", "center right", "lower center",
                "upper center", "center"]


def _renderer(fig):
    try:
        fig.canvas.draw()
        return fig.canvas.get_renderer()
    except Exception:
        return None


def _legend_overlaps_data(ax, frac: float = 0.12) -> bool:
    """True si la leyenda tapa una fracción apreciable de los datos del panel."""
    leg = ax.get_legend()
    if leg is None or not leg.get_visible():
        return False
    rend = _renderer(ax.figure)
    if rend is None:
        return False
    try:
        lbb = leg.get_window_extent(rend)
    except Exception:
        return False
    if lbb.width <= 0 or lbb.height <= 0:
        return False
    inter = 0.0
    for art in list(ax.get_lines()) + list(ax.collections) + list(ax.patches):
        try:
            if not art.get_visible():
                continue
            bb = art.get_window_extent(rend)
        except Exception:
            continue
        x0, y0 = max(lbb.x0, bb.x0), max(lbb.y0, bb.y0)
        x1, y1 = min(lbb.x1, bb.x1), min(lbb.y1, bb.y1)
        if x1 > x0 and y1 > y0:
            inter += (x1 - x0) * (y1 - y0)
    return bool((inter / (lbb.width * lbb.height)) > frac)


def _legend_style_snapshot(leg):
    snap = {"title": "", "title_fs": None, "label_fs": None, "frameon": True, "ncol": 1}
    if leg is None:
        return snap
    try:
        t = leg.get_title()
        if t is not None and t.get_text():
            snap["title"] = t.get_text()
            snap["title_fs"] = t.get_fontsize()
    except Exception:
        pass
    try:
        texts = leg.get_texts()
        if texts:
            snap["label_fs"] = texts[0].get_fontsize()
    except Exception:
        pass
    try:
        snap["frameon"] = bool(leg.get_frame_on())
    except Exception:
        pass
    try:
        snap["ncol"] = int(getattr(leg, "_ncols", getattr(leg, "_ncol", 1)) or 1)
    except Exception:
        pass
    return snap


def _set_legend_loc(ax, loc="best"):
    """Recrea la leyenda del eje en `loc` preservando contenido y estilo."""
    leg = ax.get_legend()
    if leg is None:
        return None
    snap = _legend_style_snapshot(leg)
    handles, labels = ax.get_legend_handles_labels()
    if not handles:
        return leg
    kw = {"loc": loc, "frameon": snap["frameon"], "ncol": max(1, snap["ncol"])}
    if snap["title"]:
        kw["title"] = snap["title"]
    if snap["label_fs"]:
        kw["fontsize"] = snap["label_fs"]
    try:
        newleg = ax.legend(handles, labels, **kw)
    except Exception:
        newleg = ax.legend(handles, labels, loc=loc)
    if newleg is not None and snap["title_fs"] and newleg.get_title():
        try:
            newleg.get_title().set_fontsize(snap["title_fs"])
        except Exception:
            pass
    return newleg


def _make_legends_draggable(fig, on=True):
    for ax in fig.axes:
        leg = ax.get_legend()
        if leg is not None:
            try:
                leg.set_draggable(bool(on))
            except Exception:
                pass


def _apply_legend_policy(fig, axes=None, policy="auto_if_overlap", draggable=True):
    """Aplica la política de leyendas al tamaño FINAL de cada panel.

    policy: 'auto_if_overlap' (reubica a 'best' solo si tapa datos),
            'best_always' (siempre 'best'), 'preserve' (no toca), 'hide'.
    Además deja las leyendas arrastrables para ajuste fino con el mouse.
    """
    axes = list(fig.axes) if axes is None else list(axes)
    pol = str(policy).lower()
    if pol == "auto":
        pol = "best_always"
    for ax in axes:
        leg = ax.get_legend()
        if leg is None:
            continue
        if pol == "hide":
            leg.set_visible(False)
            continue
        if not leg.get_visible():
            leg.set_visible(True)
        if pol == "best_always":
            leg = _set_legend_loc(ax, "best")
        elif pol == "auto_if_overlap":
            if _legend_overlaps_data(ax):
                leg = _set_legend_loc(ax, "best")
        # 'preserve' -> sin cambios
        if leg is not None and draggable:
            try:
                leg.set_draggable(True)
            except Exception:
                pass
    return fig


# ─────────────────────────────────────────────────────────────────────────────
#  Dibujar un eje serializado (axd) dentro de un eje destino
# ─────────────────────────────────────────────────────────────────────────────
def _draw_axd_into(target_ax, axd: dict, source_fig_data: dict | None = None,
                   font_scale: float = 1.0, keep_source_suptitle: bool = True,
                   legend_policy: str = "auto_if_overlap"):
    """Reconstruye el primer eje de un JSON del editor dentro de target_ax."""
    axd = _normalize_axd(axd)
    ax = target_ax
    for fn, key, default in [(ax.set_xscale, "xscale", "linear"), (ax.set_yscale, "yscale", "linear")]:
        try:
            fn(axd.get(key, default))
        except Exception:
            pass

    for img in axd.get("images", []) or []:
        try:
            arr = np.asarray(img.get("array", img.get("data", [])))
            if arr.size == 0:
                continue
            kw = {k: img[k] for k in ("origin", "interpolation", "cmap", "alpha") if img.get(k) is not None}
            for k in ("extent", "vmin", "vmax"):
                if img.get(k) is not None:
                    kw[k] = img[k]
            ax.imshow(arr, **kw)
        except Exception as e:
            print(f"  Aviso: imagen del JSON no reconstruida: {e}")

    for line in axd.get("lines", []) or []:
        try:
            kw = {
                "label": line.get("label", ""),
                "color": line.get("color"),
                "linewidth": line.get("linewidth", 1.5),
                "linestyle": _safe_linestyle(line.get("linestyle", "-")),
                "marker": _safe_marker(line.get("marker", "")),
                "markersize": line.get("markersize", 6.0),
                "markerfacecolor": line.get("markerfacecolor"),
                "markeredgecolor": line.get("markeredgecolor"),
                "markeredgewidth": line.get("markeredgewidth", 1.0),
            }
            kw = {k: v for k, v in kw.items() if v is not None}
            ln, = ax.plot(line.get("x", []), line.get("y", []), **kw)
            if line.get("alpha") is not None:
                ln.set_alpha(line["alpha"])
            if line.get("visible") is not None:
                ln.set_visible(bool(line["visible"]))
            if line.get("zorder") is not None:
                ln.set_zorder(float(line["zorder"]))
        except Exception as e:
            print(f"  Aviso: línea del JSON no reconstruida: {e}")

    for sc in axd.get("scatters", []) or []:
        try:
            kw = {}
            if sc.get("s") is not None:
                kw["s"] = sc["s"]
            if sc.get("color") is not None:
                kw["c"] = sc["color"]
            if sc.get("edgecolors") is not None:
                kw["edgecolors"] = sc["edgecolors"]
            if sc.get("alpha") is not None:
                kw["alpha"] = sc["alpha"]
            if sc.get("label"):
                kw["label"] = sc["label"]
            ax.scatter(sc.get("x", []), sc.get("y", []), **kw)
        except Exception as e:
            print(f"  Aviso: scatter del JSON no reconstruido: {e}")

    for bc in axd.get("bars", []) or []:
        for p in (bc.get("patches", []) if isinstance(bc, dict) else []):
            try:
                rect = Rectangle((p.get("x", 0), p.get("y", 0)), p.get("width", 1), p.get("height", 1),
                                 angle=p.get("angle", 0.0), facecolor=p.get("facecolor", "C0"),
                                 edgecolor=p.get("edgecolor", "black"), linewidth=p.get("linewidth", 1.0),
                                 linestyle=p.get("linestyle", "-"), hatch=p.get("hatch"),
                                 label=p.get("label", ""))
                if p.get("alpha") is not None:
                    rect.set_alpha(p["alpha"])
                if p.get("zorder") is not None:
                    rect.set_zorder(float(p["zorder"]))
                rect.set_visible(bool(p.get("visible", True)))
                ax.add_patch(rect)
            except Exception as e:
                print(f"  Aviso: barra del JSON no reconstruida: {e}")

    for lcd in axd.get("line_collections", []) or []:
        try:
            coll = mcoll.LineCollection(lcd.get("segments"), colors=lcd.get("colors"),
                                        linewidths=lcd.get("linewidths"), linestyles=lcd.get("linestyles"))
            if lcd.get("alpha") is not None:
                coll.set_alpha(lcd["alpha"])
            if lcd.get("zorder") is not None:
                coll.set_zorder(lcd["zorder"])
            if lcd.get("label"):
                coll.set_label(lcd["label"])
            ax.add_collection(coll)
        except Exception:
            pass

    for vl in axd.get("vlines", []) or []:
        try:
            ax.axvline(vl.get("x", vl.get("value", 0)), color=vl.get("color", "k"),
                       linewidth=vl.get("linewidth", 1.0),
                       linestyle=_safe_linestyle(vl.get("linestyle", "--")), alpha=vl.get("alpha"))
        except Exception:
            pass
    for hl in axd.get("hlines", []) or []:
        try:
            ax.axhline(hl.get("y", hl.get("value", 0)), color=hl.get("color", "k"),
                       linewidth=hl.get("linewidth", 1.0),
                       linestyle=_safe_linestyle(hl.get("linestyle", "--")), alpha=hl.get("alpha"))
        except Exception:
            pass

    import copy as _copy
    title_spec = _copy.deepcopy(axd.get("title", {}))
    if keep_source_suptitle and source_fig_data:
        st = source_fig_data.get("suptitle_obj") or {"text": source_fig_data.get("suptitle", "")}
        if isinstance(st, dict) and st.get("text") and not (title_spec or {}).get("text"):
            title_spec = _copy.deepcopy(st)
    _apply_text(ax.title, title_spec)
    _apply_text(ax.xaxis.label, axd.get("xlabel", {}))
    _apply_text(ax.yaxis.label, axd.get("ylabel", {}))

    for setter, key in [(ax.set_xlim, "xlim"), (ax.set_ylim, "ylim")]:
        try:
            if axd.get(key) is not None:
                setter(axd[key])
        except Exception:
            pass
    try:
        if axd.get("facecolor") is not None:
            ax.set_facecolor(axd["facecolor"])
    except Exception:
        pass
    _apply_spines(ax, axd.get("spines", {}))
    _apply_grid(ax, axd.get("grid"))
    try:
        _apply_ticks(ax, (axd.get("ticks", {}) or {}).get("x", {}), "x")
        _apply_ticks(ax, (axd.get("ticks", {}) or {}).get("y", {}), "y")
    except Exception:
        pass
    try:
        asp = axd.get("aspect", "auto")
        if asp is not None:
            ax.set_aspect(asp)
    except Exception:
        pass

    for td in axd.get("texts", []) or []:
        try:
            kw = {k: td[k] for k in ("fontsize", "color", "ha", "va", "rotation", "alpha", "fontweight", "fontstyle")
                  if td.get(k) is not None}
            txt = ax.text(td.get("x", 0.5), td.get("y", 0.5), td.get("text", ""),
                          transform=ax.transAxes if td.get("transform", "axes") == "axes" else ax.transData, **kw)
            if td.get("bbox") is not None:
                _apply_annotation_bbox(txt, td["bbox"])
        except Exception:
            pass

    try:
        _rebuild_legend(ax, axd.get("legend"))
        _auto_reposition_legend(ax, axd.get("legend"), policy=legend_policy)
    except Exception as e:
        print(f"  Aviso: leyenda no reconstruida/reubicada: {e}")

    _scale_axis_fonts(ax, font_scale)
    return ax


# ─────────────────────────────────────────────────────────────────────────────
#  Fallback CSV (sin JSON): grafica datos básicos
# ─────────────────────────────────────────────────────────────────────────────
def _draw_csv_axis_into(ax, path: str | Path, font_scale: float = 1.0):
    p = Path(path)
    with open(p, "r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t ") if sample.strip() else csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        rows = list(reader)
        fieldnames = reader.fieldnames or []
    if not rows:
        raise ValueError(f"CSV vacío o sin encabezado: {p}")
    lower = {name.lower().strip(): name for name in fieldnames}
    if {"x", "y"}.issubset(lower):  # formato del editor
        xname, yname = lower["x"], lower["y"]
        label_name = lower.get("label")
        groups: dict[str, tuple[list, list]] = {}
        for r in rows:
            x, y = _float_or_none(r.get(xname)), _float_or_none(r.get(yname))
            if x is None or y is None:
                continue
            lab = str(r.get(label_name, "data") if label_name else "data") or "data"
            groups.setdefault(lab, ([], []))
            groups[lab][0].append(x)
            groups[lab][1].append(y)
        for lab, (xs, ys) in groups.items():
            ax.plot(xs, ys, marker="o", linestyle="-", label=lab)
        if len(groups) > 1:
            ax.legend()
        ax.set_xlabel(xname)
        ax.set_ylabel(yname)
    else:  # CSV genérico: dos primeras columnas numéricas
        numeric = []
        for name in fieldnames:
            vals = [_float_or_none(r.get(name)) for r in rows]
            if sum(v is not None for v in vals) >= max(2, len(rows) // 3):
                numeric.append((name, vals))
        if len(numeric) < 2:
            raise ValueError(f"No pude inferir 2 columnas numéricas en: {p}")
        (xname, xs), (yname, ys) = numeric[0], numeric[1]
        xy = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
        ax.plot([a for a, _ in xy], [b for _, b in xy], marker="o", linestyle="-", label=p.stem)
        ax.set_xlabel(xname)
        ax.set_ylabel(yname)
    ax.set_title(p.stem)
    _scale_axis_fonts(ax, font_scale)
    return ax


# ─────────────────────────────────────────────────────────────────────────────
#  Despachador de fuente -> eje
# ─────────────────────────────────────────────────────────────────────────────
def _draw_source_into(ax, source, panel_idx, *, font_scale, dpi, raster_crop_white,
                      keep_source_suptitle, source_records, all_data_flag,
                      cache=None, legend_policy="auto_if_overlap"):
    typ, p = _classify_panel_source(source)
    if typ == "missing" or not Path(p).exists():
        searched = str(_source_path_from_user_text(source))
        raise FileNotFoundError(
            f"No se encontró la fuente del panel {panel_idx + 1}: {source}  (busqué: {searched})")
    source_records.append({"panel_index": int(panel_idx), "input": str(source),
                           "resolved_path": str(p), "type": typ})
    if typ == "json":
        data, jp = _load_json_cached(p, cache)
        axes = data.get("axes", []) or []
        if not axes:
            raise ValueError(f"El JSON no contiene ejes reconstruibles: {jp}")
        _draw_axd_into(ax, axes[0], source_fig_data=data, font_scale=font_scale,
                       keep_source_suptitle=keep_source_suptitle, legend_policy=legend_policy)
        return ax, "json"
    if typ == "csv":
        all_data_flag["all_reconstructible"] = False
        _draw_csv_axis_into(ax, p, font_scale=font_scale)
        return ax, "csv"
    all_data_flag["all_reconstructible"] = False
    arr = _read_image_cached(p, dpi=max(150, int(dpi) * 2), crop_white=raster_crop_white, cache=cache)
    _draw_image_array_into(ax, arr)
    return ax, "image"


# ═════════════════════════════════════════════════════════════════════════════
#  GEOMETRÍA: ratios, construcción de ejes, motor de layout
# ═════════════════════════════════════════════════════════════════════════════
def ratios_equipartition_boost(n: int, boost_index: int, boost_percent: float) -> list[float]:
    """Pesos para que el panel `boost_index` ocupe (1+boost%)x su parte equipartita.

    Ej.: n=2, boost_index=0, boost_percent=30  ->  el panel 0 ocupa el 65% del
    ancho (30% más que el 50% equipartito) y el resto se reparte: [0.65, 0.35].
    Esto implementa literalmente "X% mayor que la distribución equipartita".
    """
    n = int(n)
    if n < 1 or not (0 <= boost_index < n):
        raise ValueError("boost_index fuera de rango.")
    base = 1.0 / n
    boosted = base * (1.0 + float(boost_percent) / 100.0)
    if boosted >= 1.0:
        raise ValueError("El boost deja sin espacio a los demás paneles (>100%).")
    if boosted <= 0:
        raise ValueError("El boost vuelve nulo o negativo al panel.")
    rest = (1.0 - boosted) / (n - 1) if n > 1 else 0.0
    w = [rest] * n
    w[boost_index] = boosted
    return w


def sanitize_ratios(values: Iterable[float] | None, expected: int, *, name: str) -> list[float] | None:
    if values is None:
        return None
    vals = [float(v) for v in values]
    if len(vals) != int(expected):
        raise ValueError(f"{name} debe tener {expected} valor(es); recibí {len(vals)}.")
    if any((not np.isfinite(v)) or v <= 0 for v in vals):
        raise ValueError(f"{name} sólo admite valores positivos y finitos.")
    return vals


def _gridspec_kw(rows, cols, width_ratios=None, height_ratios=None) -> dict:
    kw = {}
    wr = sanitize_ratios(width_ratios, cols, name="width_ratios")
    hr = sanitize_ratios(height_ratios, rows, name="height_ratios")
    if wr is not None:
        kw["width_ratios"] = wr
    if hr is not None:
        kw["height_ratios"] = hr
    return kw


def _build_axes_for_layout(fig, layout: str, width_ratios=None, height_ratios=None):
    """Crea los ejes del layout y los devuelve EN EL ORDEN DE LAS FUENTES."""
    layout = layout.lower().replace("×", "x")
    if layout == "1x2_split_left":
        # Columna izquierda subdividida (2 medias apiladas) + columna derecha entera.
        kw = _gridspec_kw(2, 2, width_ratios, height_ratios)
        gs = fig.add_gridspec(2, 2, **kw)
        return [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[:, 1])]
    if layout == "1x2_split_right":
        kw = _gridspec_kw(2, 2, width_ratios, height_ratios)
        gs = fig.add_gridspec(2, 2, **kw)
        return [fig.add_subplot(gs[:, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, 1])]
    if layout == "1x2_split_top":
        # 2 medias lado a lado arriba + entera abajo
        kw = _gridspec_kw(2, 2, width_ratios, height_ratios)
        gs = fig.add_gridspec(2, 2, **kw)
        return [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, :])]
    if layout == "1x2_split_bottom":
        # entera arriba + 2 medias lado a lado abajo
        kw = _gridspec_kw(2, 2, width_ratios, height_ratios)
        gs = fig.add_gridspec(2, 2, **kw)
        return [fig.add_subplot(gs[0, :]), fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])]
    rows, cols = _layout_rows_cols(layout)
    gs_kw = _gridspec_kw(rows, cols, width_ratios, height_ratios)
    axs = fig.subplots(rows, cols, squeeze=False, gridspec_kw=gs_kw or None)
    return [ax for row in axs for ax in row]


# ─────────────────────────────────────────────────────────────────────────────
#  Motor de layout anti-solapamiento (híbrido)
# ─────────────────────────────────────────────────────────────────────────────
def _apply_layout_engine(fig, layout: str, *, engine: str = "auto",
                         wspace: float = 0.06, hspace: float = 0.10,
                         pad: float = 0.4, w_pad: float = 0.10, h_pad: float = 0.10):
    """Aplica el motor de layout.

    - 'auto'/'constrained': constrained_layout para grillas (resuelve solapes
      honrando ratios). Para 1x1_inset usa layout manual (constrained_layout
      pelea con inset_axes y puede descolocarlo).
    - 'manual': subplots_adjust con wspace/hspace.
    """
    eng = str(engine).lower().strip()
    is_inset = (layout == "1x1_inset")
    use_constrained = (eng in {"auto", "constrained"}) and not is_inset
    if use_constrained:
        try:
            fig.set_layout_engine("constrained",
                                  w_pad=w_pad, h_pad=h_pad, wspace=wspace, hspace=hspace)
        except TypeError:
            try:
                fig.set_layout_engine("constrained")
            except Exception:
                fig.subplots_adjust(wspace=max(wspace, 0.2), hspace=max(hspace, 0.25))
        except Exception:
            fig.subplots_adjust(wspace=max(wspace, 0.2), hspace=max(hspace, 0.25))
    else:
        try:
            fig.set_layout_engine("none")
        except Exception:
            pass
        fig.subplots_adjust(left=0.12, right=0.97, bottom=0.12, top=0.90,
                            wspace=max(wspace, 0.25), hspace=max(hspace, 0.30))
    return fig


def _freeze_positions(fig):
    """Dibuja para fijar posiciones del motor de layout y luego lo desactiva,
    dejando posiciones absolutas (necesario para serializar el round-trip)."""
    try:
        fig.canvas.draw()
    except Exception:
        try:
            fig.draw_without_rendering()
        except Exception:
            pass
    try:
        fig.set_layout_engine("none")
    except Exception:
        pass
    return fig


# ═════════════════════════════════════════════════════════════════════════════
#  RÓTULOS DE PANEL
# ═════════════════════════════════════════════════════════════════════════════
_LABEL_KINDS = OrderedDict([
    ("alpha_lower", "a, b, c"),
    ("alpha_upper", "A, B, C"),
    ("roman_lower", "i, ii, iii"),
    ("roman_upper", "I, II, III"),
    ("arabic",      "1, 2, 3"),
])
_LABEL_WRAPS = OrderedDict([
    ("paren_right", "x)"),
    ("paren_both",  "(x)"),
    ("dot",         "x."),
    ("bare",        "x"),
])

# 9 puntos interiores + exterior + custom
_LABEL_POSITIONS = OrderedDict([
    ("inside_top_left",     (0.030, 0.965, "left", "top")),
    ("inside_top_center",   (0.500, 0.965, "center", "top")),
    ("inside_top_right",    (0.970, 0.965, "right", "top")),
    ("inside_center_left",  (0.030, 0.500, "left", "center")),
    ("inside_center",       (0.500, 0.500, "center", "center")),
    ("inside_center_right", (0.970, 0.500, "right", "center")),
    ("inside_bottom_left",  (0.030, 0.035, "left", "bottom")),
    ("inside_bottom_center",(0.500, 0.035, "center", "bottom")),
    ("inside_bottom_right", (0.970, 0.035, "right", "bottom")),
    ("outside_top_left",    (-0.12, 1.04, "left", "bottom")),
])


def _int_to_roman(num: int) -> str:
    if num <= 0:
        return str(num)
    vals = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"),
            (90, "xc"), (50, "l"), (40, "xl"), (10, "x"), (9, "ix"),
            (5, "v"), (4, "iv"), (1, "i")]
    out = []
    for v, s in vals:
        while num >= v:
            out.append(s)
            num -= v
    return "".join(out)


def format_panel_label(idx: int, kind: str = "alpha_lower", wrap: str = "paren_right") -> str:
    """idx 0-based -> rótulo, p.ej. (0,'alpha_lower','paren_right') -> 'a)'."""
    if kind == "alpha_lower":
        core = string.ascii_lowercase[idx] if idx < 26 else str(idx + 1)
    elif kind == "alpha_upper":
        core = string.ascii_uppercase[idx] if idx < 26 else str(idx + 1)
    elif kind == "roman_lower":
        core = _int_to_roman(idx + 1)
    elif kind == "roman_upper":
        core = _int_to_roman(idx + 1).upper()
    elif kind == "arabic":
        core = str(idx + 1)
    else:
        core = string.ascii_lowercase[idx] if idx < 26 else str(idx + 1)
    if wrap == "paren_right":
        return f"{core})"
    if wrap == "paren_both":
        return f"({core})"
    if wrap == "dot":
        return f"{core}."
    return core


def _sort_axes_visual_order(axes: Iterable) -> list:
    """Orden de lectura: arriba->abajo, izquierda->derecha."""
    def key(ax):
        try:
            bb = ax.get_position()
            return (-round(bb.y1, 4), round(bb.x0, 4))
        except Exception:
            return (0.0, 0.0)
    return sorted(list(axes), key=key)


def default_label_spec() -> dict:
    return {
        "enabled": True,
        "kind": "alpha_lower",
        "wrap": "paren_right",
        "position": "outside_top_left",
        "custom_xy": None,        # (x, y) en fracción de ejes si position == 'custom'
        "fontsize": 12.0,
        "fontweight": "bold",
        "color": "black",
        "label_inset": False,
        "overrides": {},          # {panel_visual_index: "texto"} para forzar un rótulo
    }


def apply_panel_labels(fig, axes: Iterable, spec: dict | None = None):
    """Rotula los ejes según `spec` en orden de lectura. Quita rótulos previos."""
    spec = {**default_label_spec(), **(spec or {})}
    # limpiar rótulos previos
    for ax in fig.axes:
        for t in list(getattr(ax, "texts", [])):
            if getattr(t, "_pa_panel_label", False):
                try:
                    t.remove()
                except Exception:
                    pass
    if not spec.get("enabled", True):
        return []
    pos_key = spec.get("position", "outside_top_left")
    if pos_key == "custom" and spec.get("custom_xy"):
        x, y = spec["custom_xy"]
        ha, va = "left", "bottom"
        bbox = None
    else:
        x, y, ha, va = _LABEL_POSITIONS.get(pos_key, _LABEL_POSITIONS["outside_top_left"])
        bbox = (dict(facecolor="white", edgecolor="none", alpha=0.75, pad=1.5)
                if str(pos_key).startswith("inside") else None)
    out = []
    ordered = _sort_axes_visual_order(axes)
    for i, ax in enumerate(ordered):
        text = spec.get("overrides", {}).get(i) or format_panel_label(i, spec["kind"], spec["wrap"])
        t = ax.text(x, y, text, transform=ax.transAxes, ha=ha, va=va,
                    fontsize=spec["fontsize"], fontweight=spec["fontweight"],
                    color=spec["color"], clip_on=False, bbox=bbox)
        try:
            t._pa_panel_label = True
        except Exception:
            pass
        out.append(t)
    return out


# ═════════════════════════════════════════════════════════════════════════════
#  API PRINCIPAL: construir la figura compuesta
# ═════════════════════════════════════════════════════════════════════════════
def create_composite_figure_from_files(
    sources: list[str | Path],
    layout: str = "2x2",
    output_base: str | Path | None = None,
    save: bool = False,
    *,
    panel_width: float = 3.6,
    panel_height: float = 3.0,
    width_ratios: Iterable[float] | None = None,
    height_ratios: Iterable[float] | None = None,
    dpi: int = 150,
    font_scale: float = 0.9,
    layout_engine: str = "auto",
    wspace: float = 0.06,
    hspace: float = 0.10,
    label_spec: dict | None = None,
    raster_crop_white: bool = True,
    keep_source_suptitle: bool = True,
    suptitle: str | None = None,
    inset_rect: tuple[float, float, float, float] = (0.55, 0.55, 0.42, 0.40),
    inset_legible: bool = True,
    inset_drop_title: bool = True,
    inset_min_pt: float = 7.0,
    inset_label_pt: float = 8.0,
    inset_max_ticks: int = 4,
    legend_policy: str = "auto_if_overlap",
    cache: dict | None = None,
    show: bool = True,
):
    """Arma una figura compuesta desde raíces JSON/CSV, imágenes o PDF/EPS/SVG."""
    layout = str(layout).strip().lower().replace("×", "x")
    if layout not in _PANEL_LAYOUTS:
        raise ValueError(f"Layout no soportado: {layout}. Opciones: {', '.join(_PANEL_LAYOUTS)}")
    info = _PANEL_LAYOUTS[layout]
    n_needed = int(info["n"])
    if len(sources) < n_needed:
        raise ValueError(f"El layout {layout} requiere {n_needed} fuente(s); recibí {len(sources)}.")

    rows, cols = int(info["rows"]), int(info["cols"])
    fig_w = max(2.0, float(panel_width) * cols)
    fig_h = max(2.0, float(panel_height) * rows)
    fig = plt.figure(figsize=(fig_w, fig_h), dpi=dpi)

    axes_in_source_order = _build_axes_for_layout(fig, layout, width_ratios, height_ratios)
    if suptitle:
        fig.suptitle(str(suptitle))

    source_records: list[dict] = []
    all_data_flag = {"all_reconstructible": True}
    drawn_axes = []
    label_spec = {**default_label_spec(), **(label_spec or {})}

    main_ax = None
    inset_ax = None
    if layout == "1x1_inset":
        main_ax = axes_in_source_order[0]
        _draw_source_into(main_ax, sources[0], 0, font_scale=font_scale, dpi=dpi,
                          raster_crop_white=raster_crop_white, keep_source_suptitle=keep_source_suptitle,
                          source_records=source_records, all_data_flag=all_data_flag,
                          cache=cache, legend_policy=legend_policy)
        drawn_axes = [main_ax]
    else:
        for i, ax in enumerate(axes_in_source_order[:n_needed]):
            _draw_source_into(ax, sources[i], i, font_scale=font_scale, dpi=dpi,
                              raster_crop_white=raster_crop_white, keep_source_suptitle=keep_source_suptitle,
                              source_records=source_records, all_data_flag=all_data_flag,
                              cache=cache, legend_policy=legend_policy)
            drawn_axes.append(ax)

    _apply_layout_engine(fig, layout, engine=layout_engine, wspace=wspace, hspace=hspace)
    try:
        fig.align_labels()
    except Exception:
        pass
    # Congelar posiciones del motor de layout ANTES de crear el inserto, para
    # ubicarlo respecto de la posición final del eje principal.
    _freeze_positions(fig)

    if layout == "1x1_inset":
        # El inserto se crea con fig.add_axes() en posición ABSOLUTA (no con
        # ax.inset_axes(): en mpl>=3.8 ese eje hijo NO entra en fig.axes y el
        # editor no lo serializaría, perdiéndose en el round-trip). Posición
        # fija calculada a partir de la posición congelada del eje principal.
        mb = main_ax.get_position()
        l, b, w, h = inset_rect
        abs_rect = [mb.x0 + l * mb.width, mb.y0 + b * mb.height, w * mb.width, h * mb.height]
        inset_ax = fig.add_axes(abs_rect)
        _draw_source_into(inset_ax, sources[1], 1, font_scale=font_scale, dpi=dpi,
                          raster_crop_white=raster_crop_white, keep_source_suptitle=keep_source_suptitle,
                          source_records=source_records, all_data_flag=all_data_flag,
                          cache=cache, legend_policy=legend_policy)
        if inset_drop_title:
            try:
                inset_ax.set_title("")
            except Exception:
                pass
        if inset_legible:
            _make_inset_legible(inset_ax, min_pt=inset_min_pt, label_pt=inset_label_pt,
                                max_ticks=inset_max_ticks)
        try:
            inset_ax._pa_is_inset = True
        except Exception:
            pass
        try:
            fig.canvas.draw()
        except Exception:
            pass
        if label_spec.get("label_inset"):
            drawn_axes = [main_ax, inset_ax]

    # Rótulos: tras el layout/freeze, para que el orden de lectura use posiciones finales.
    apply_panel_labels(fig, drawn_axes, label_spec)

    # Leyendas: reubicar al tamaño FINAL (cuando recién se sabe si tapan datos)
    # y dejarlas arrastrables para ajuste fino con el mouse sobre la figura viva.
    try:
        _apply_legend_policy(fig, list(fig.axes), policy=legend_policy, draggable=True)
        fig.canvas.draw()
    except Exception:
        pass

    metadata = {
        "format_version": _FORMAT_VERSION,
        "generator": "figure_panel_assembler_v4.py",
        "layout": layout,
        "layout_label": info.get("label", layout),
        "sources": source_records,
        "panel_width": float(panel_width),
        "panel_height": float(panel_height),
        "width_ratios": _jsonable(width_ratios),
        "height_ratios": _jsonable(height_ratios),
        "dpi": int(dpi),
        "font_scale": float(font_scale),
        "layout_engine": str(layout_engine),
        "wspace": float(wspace),
        "hspace": float(hspace),
        "legend_policy": str(legend_policy),
        "label_spec": _jsonable(label_spec),
        "inset_rect": list(inset_rect) if layout == "1x1_inset" else None,
        "inset_drop_title": bool(inset_drop_title) if layout == "1x1_inset" else None,
        "all_sources_reconstructible": bool(all_data_flag["all_reconstructible"]),
    }
    try:
        fig._pa_panel_metadata = metadata
        fig._pa_all_panels_from_data = bool(all_data_flag["all_reconstructible"])
        fig._pa_subplot_layout = [rows, cols]
        # Flags que figure_editor3 lee para preservar el panel exacto al recargar:
        fig._serialize_axes_positions = True
        fig._save_subplots_adjust_none = True
        fig._apply_tight_layout_on_load = False
    except Exception:
        pass

    if show:
        _show_figure_nonblocking(fig)
    if save:
        save_composite_figure(fig, output_base or "figura_compuesta",
                              include_json="auto", save_png=True, save_pdf=True, dpi=max(300, int(dpi)))
    return fig


# ─────────────────────────────────────────────────────────────────────────────
#  Exportación de imagen (recorte por content-bbox vía editor si está)
# ─────────────────────────────────────────────────────────────────────────────
def _export_image(fig, path, dpi=300):
    if _HAS_FE and hasattr(_FE, "export_image"):
        try:
            return _FE.export_image(fig, str(path), dpi=dpi, bbox_mode="content")
        except Exception:
            pass
    fig.savefig(str(path), dpi=dpi, bbox_inches="tight", pad_inches=0.03)
    return Path(path)


def save_panel_metadata(fig, filename: str | Path) -> Path:
    base = _base_path(filename)
    meta_path = base.with_name(base.name + "_panel_meta").with_suffix(".json")
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(_jsonable(getattr(fig, "_pa_panel_metadata", {}) or {}), f, indent=4, ensure_ascii=False)
    return meta_path


def save_composite_figure(fig, filename: str | Path, include_json: str | bool = "auto",
                          save_png: bool = True, save_pdf: bool = True, dpi: int = 300) -> list[str]:
    """Guarda la figura compuesta.

    include_json: 'auto' = JSON+CSV sólo si todas las fuentes son reconstruibles;
    True = forzar; False = sólo imagen + metadatos.

    El JSON/CSV reconstruible se delega en figure_editor3.save_figure_data, que
    escribe el formato que tu editor recarga sin re-layout (posiciones absolutas).
    """
    base = _base_path(filename)
    base.parent.mkdir(parents=True, exist_ok=True)
    all_data = bool(getattr(fig, "_pa_all_panels_from_data", False))
    do_json = all_data if str(include_json).lower() == "auto" else bool(include_json)
    saved: list[str] = [str(save_panel_metadata(fig, base))]

    if do_json:
        if not _HAS_FE:
            print("  Aviso: figure_editor3 no disponible; no puedo escribir JSON/CSV reconstruible.")
            do_json = False
        else:
            try:
                _freeze_positions(fig)
                fig._serialize_axes_positions = True
                fig._save_subplots_adjust_none = True
                fig._apply_tight_layout_on_load = False
                _FE.save_figure_data(fig, str(base), save_png=save_png)  # escribe .json/.csv (+.png)
                saved += [str(base.with_suffix(".json")), str(base.with_suffix(".csv"))]
                if save_png:
                    saved.append(str(base.with_suffix(".png")))
            except Exception as e:
                print(f"  Aviso: fallo el guardado reconstruible vía figure_editor3 ({e}); paso a PNG/PDF.")
                do_json = False

    if not do_json and save_png:
        _export_image(fig, base.with_suffix(".png"), dpi=dpi)
        saved.append(str(base.with_suffix(".png")))
    if save_pdf:
        _export_image(fig, base.with_suffix(".pdf"), dpi=dpi)
        saved.append(str(base.with_suffix(".pdf")))

    print("  Archivos guardados:")
    for s in dict.fromkeys(saved):
        try:
            p = Path(s)
            print(f"    - {p}  ({p.stat().st_size} bytes)")
        except Exception:
            print(f"    - {s}")
    return list(dict.fromkeys(saved))


# ─────────────────────────────────────────────────────────────────────────────
#  Mostrar sin bloquear el menú de texto
# ─────────────────────────────────────────────────────────────────────────────
def _show_figure_nonblocking(fig):
    if fig is None:
        return None
    try:
        plt.ion()
    except Exception:
        pass
    try:
        fig.canvas.draw()
    except Exception:
        pass
    try:
        backend = str(plt.get_backend()).lower()
        if backend.endswith("agg") or backend in {"pdf", "svg", "ps", "template"}:
            return fig
    except Exception:
        pass
    try:
        mgr = getattr(fig.canvas, "manager", None)
        if mgr is not None:
            try:
                mgr.set_window_title("Panel Assembler v4 — preview")
            except Exception:
                pass
            mgr.show()
    except Exception:
        pass
    try:
        plt.show(block=False)
    except Exception:
        pass
    for _ in range(4):
        try:
            fig.canvas.draw_idle()
            fig.canvas.flush_events()
            plt.pause(0.06)
        except Exception:
            break
    return fig


# ═════════════════════════════════════════════════════════════════════════════
#  GUI LIGERA (matplotlib.widgets) para acomodar tamaños/ratios en vivo
# ═════════════════════════════════════════════════════════════════════════════
def _backend_is_interactive() -> bool:
    try:
        b = str(plt.get_backend()).lower()
        return not (b.endswith("agg") or b in {"pdf", "svg", "ps", "template"})
    except Exception:
        return False


def launch_size_gui(cfg: dict, state: dict):
    """Ventana de control con sliders/botones para ajustar geometría en vivo.

    cfg: configuración de la sesión (se muta in situ).
    state: {'fig': <figura compuesta actual>} (se actualiza al regenerar).
    Requiere un backend interactivo (Qt/Tk). Bajo Agg no hace nada.
    """
    if not _backend_is_interactive():
        print("  La GUI requiere un backend interactivo (en Spyder: %matplotlib qt). "
              "Usá el ajuste por menú de texto.")
        return state.get("fig")

    from matplotlib.widgets import Slider, Button, TextBox

    rows, cols = _layout_rows_cols(cfg["layout"])
    ctrl = plt.figure(figsize=(4.6, 5.2))
    try:
        ctrl.canvas.manager.set_window_title("Acomodar tamaños — Panel Assembler v4")
    except Exception:
        pass
    ctrl.subplots_adjust(left=0.32, right=0.94, top=0.96, bottom=0.06, hspace=0.9)

    def _row(y, h=0.035):
        return ctrl.add_axes([0.32, y, 0.60, h])

    s_w = Slider(_row(0.90), "ancho/panel", 1.5, 7.0, valinit=float(cfg["panel_width"]))
    s_h = Slider(_row(0.83), "alto/panel", 1.5, 7.0, valinit=float(cfg["panel_height"]))
    s_ws = Slider(_row(0.76), "wspace", 0.0, 0.6, valinit=float(cfg.get("wspace", 0.06)))
    s_hs = Slider(_row(0.69), "hspace", 0.0, 0.6, valinit=float(cfg.get("hspace", 0.10)))
    s_fs = Slider(_row(0.62), "fuente x", 0.55, 1.4, valinit=float(cfg.get("font_scale", 0.9)))

    s_cb = Slider(_row(0.50), "boost col %", -60.0, 200.0, valinit=0.0)
    tb_col_ax = _row(0.43, 0.04)
    tb_col = TextBox(tb_col_ax, "col (1..%d)  " % cols, initial="1")
    s_rb = Slider(_row(0.34), "boost fila %", -60.0, 200.0, valinit=0.0)
    tb_row_ax = _row(0.27, 0.04)
    tb_row = TextBox(tb_row_ax, "fila (1..%d)  " % rows, initial="1")

    msg_ax = ctrl.add_axes([0.04, 0.155, 0.92, 0.06]); msg_ax.axis("off")
    msg = msg_ax.text(0.0, 0.5, "Ajustá y tocá «Regenerar».", va="center", fontsize=9)

    b_regen = Button(ctrl.add_axes([0.06, 0.075, 0.42, 0.06]), "Regenerar")
    b_save = Button(ctrl.add_axes([0.52, 0.075, 0.42, 0.06]), "Guardar")
    b_close = Button(ctrl.add_axes([0.06, 0.005, 0.88, 0.055]), "Cerrar GUI")

    def _read_ratios():
        # Boost equipartito sobre una columna y/o fila, según los sliders.
        wr = hr = None
        try:
            cb = float(s_cb.val)
            if abs(cb) > 1e-6 and cols > 1:
                ci = max(1, min(cols, int(float(tb_col.text or "1")))) - 1
                wr = ratios_equipartition_boost(cols, ci, cb)
        except Exception as e:
            msg.set_text(f"col: {e}")
        try:
            rb = float(s_rb.val)
            if abs(rb) > 1e-6 and rows > 1:
                ri = max(1, min(rows, int(float(tb_row.text or "1")))) - 1
                hr = ratios_equipartition_boost(rows, ri, rb)
        except Exception as e:
            msg.set_text(f"fila: {e}")
        return wr, hr

    def _regen(_evt=None):
        cfg["panel_width"] = float(s_w.val)
        cfg["panel_height"] = float(s_h.val)
        cfg["wspace"] = float(s_ws.val)
        cfg["hspace"] = float(s_hs.val)
        cfg["font_scale"] = float(s_fs.val)
        wr, hr = _read_ratios()
        cfg["width_ratios"] = wr
        cfg["height_ratios"] = hr
        try:
            state["fig"] = _build_panel_from_config(cfg, state.get("fig"), close_previous=True)
            msg.set_text("Figura regenerada.")
        except Exception as e:
            msg.set_text(f"Error: {e}")
        ctrl.canvas.draw_idle()

    def _save(_evt=None):
        fig = state.get("fig")
        if fig is None:
            msg.set_text("No hay figura para guardar.")
        else:
            out = cfg.get("output_base", "figura_compuesta")
            try:
                save_composite_figure(fig, out, include_json="auto", save_png=True, save_pdf=True,
                                      dpi=max(300, int(cfg.get("dpi", 150))))
                msg.set_text(f"Guardado: {out} (.json/.csv/.png/.pdf según fuentes)")
            except Exception as e:
                msg.set_text(f"Error al guardar: {e}")
        ctrl.canvas.draw_idle()

    def _close(_evt=None):
        try:
            plt.close(ctrl)
        except Exception:
            pass

    b_regen.on_clicked(_regen)
    b_save.on_clicked(_save)
    b_close.on_clicked(_close)
    # guardar refs para que no las recolecte el GC
    ctrl._pa_widgets = [s_w, s_h, s_ws, s_hs, s_fs, s_cb, s_rb, tb_col, tb_row,
                        b_regen, b_save, b_close]
    _show_figure_nonblocking(ctrl)
    print("  GUI abierta. Ajustá los sliders y tocá «Regenerar». «Cerrar GUI» para volver.")
    return state.get("fig")


# ═════════════════════════════════════════════════════════════════════════════
#  MENÚ INTERACTIVO
# ═════════════════════════════════════════════════════════════════════════════
def _responsive_input(prompt: str = "") -> str:
    """input() que mantiene viva la figura: bombea el loop de eventos de la GUI
    mientras espera lo que tipeás en consola, así la figura ensamblada queda
    interactiva (pan/zoom, leyenda arrastrable) en lugar de congelarse.

    Bajo backend no interactivo (Agg/PDF/…) usa input() normal. Si el esquema
    con hilo falla (algún IDE con stdin atípico), cae a input() plano."""
    if not _backend_is_interactive():
        return input(prompt)
    try:
        if prompt:
            print(prompt, end="", flush=True)
        q: "queue.Queue[str | None]" = queue.Queue()

        def _worker():
            try:
                q.put(sys.stdin.readline())
            except Exception:
                q.put(None)

        th = threading.Thread(target=_worker, daemon=True)
        th.start()
        while True:
            try:
                line = q.get_nowait()
                return "" if line is None else line.rstrip("\n")
            except queue.Empty:
                pass
            try:
                plt.pause(0.05)        # bombea eventos GUI (pan/zoom/drag)
            except Exception:
                time.sleep(0.05)
                if not th.is_alive():
                    return q.get() or ""
    except Exception:
        return input(prompt)


def _prompt(msg, default=""):
    v = _responsive_input(f"  {msg} [{default}]: ").strip()
    return v if v else str(default)


def _prompt_float(msg, default=0.0):
    v = _responsive_input(f"  {msg} [{default}]: ").strip()
    if not v:
        return float(default)
    try:
        return float(v.replace(",", "."))
    except Exception:
        print(f"  Valor inválido; mantengo {default}")
        return float(default)


def _prompt_int(msg, default=0):
    v = _responsive_input(f"  {msg} [{default}]: ").strip()
    try:
        return int(v) if v else int(default)
    except Exception:
        print(f"  Valor inválido; mantengo {default}")
        return int(default)


def _prompt_yesno(msg, default=True):
    d = "s" if default else "n"
    v = _responsive_input(f"  {msg} (s/n) [{d}]: ").strip().lower()
    return default if not v else v in {"s", "si", "sí", "y", "yes", "1", "true"}


def _choose_from(title, options, default_idx=0):
    """options: lista de (clave, etiqueta). Devuelve la clave o None."""
    print(f"\n  ── {title} ──")
    for i, (_, lab) in enumerate(options, 1):
        mark = " (def)" if i - 1 == default_idx else ""
        print(f"   {i:2d}. {lab}{mark}")
    raw = _responsive_input(f"  Opción [{default_idx + 1}]: ").strip()
    if not raw:
        return options[default_idx][0]
    try:
        idx = int(raw)
        if 1 <= idx <= len(options):
            return options[idx - 1][0]
    except Exception:
        pass
    print("  Opción inválida.")
    return None


def _choose_layout():
    keys = list(_PANEL_LAYOUTS.keys())
    opts = [(k, f"{_PANEL_LAYOUTS[k]['label']}  [{k}]") for k in keys]
    while True:
        k = _choose_from("Tipo de panel", opts, default_idx=0)
        if k:
            return k


def _source_labels(layout):
    if layout == "1x1_inset":
        return ["Figura principal", "Figura inserta"]
    if layout == "1x2_split_left":
        return ["Media IZQUIERDA superior", "Media IZQUIERDA inferior", "Figura entera DERECHA"]
    if layout == "1x2_split_right":
        return ["Figura entera IZQUIERDA", "Media DERECHA superior", "Media DERECHA inferior"]
    if layout == "1x2_split_top":
        return ["Media ARRIBA izquierda", "Media ARRIBA derecha", "Figura entera ABAJO"]
    if layout == "1x2_split_bottom":
        return ["Figura entera ARRIBA", "Media ABAJO izquierda", "Media ABAJO derecha"]
    n = int(_PANEL_LAYOUTS[layout]["n"])
    return [f"Panel {i + 1}" for i in range(n)]


def _collect_sources(layout):
    labels = _source_labels(layout)
    print("\n  Fuentes: raíz JSON/CSV del editor, .json, .csv, .png/.jpg/.tif, .pdf, .eps, .svg")
    print("  Sin path => se busca en el directorio de trabajo actual.")
    sources = []
    for lab in labels:
        while True:
            s = _responsive_input(f"  {lab} — ruta o raíz: ").strip().strip('"')
            if s:
                sources.append(s)
                break
            print("  Indicá una ruta o raíz.")
    return sources


def _choose_ratios(layout, current_w=None, current_h=None):
    """Devuelve (width_ratios, height_ratios) en pesos relativos o None (equipartito)."""
    rows, cols = _layout_rows_cols(layout)
    if rows == 1 and cols == 1 and layout != "1x1_inset":
        return None, None
    mode = _choose_from(
        "Proporciones de paneles",
        [("equal", "Equipartito (todos iguales)"),
         ("boost", "Destacar un panel: «+X% respecto del equipartito»"),
         ("absolute", "Anchos/altos relativos absolutos por columna/fila")],
        default_idx=0,
    )
    if mode == "equal" or mode is None:
        return None, None

    wr, hr = current_w, current_h
    if mode == "boost":
        if cols > 1:
            ci = _prompt_int(f"Columna a destacar (1..{cols}, izq→der)", 1)
            pct = _prompt_float("Cuánto más que el equipartito (%)", 30.0)
            try:
                wr = ratios_equipartition_boost(cols, max(1, min(cols, ci)) - 1, pct)
                print(f"  → anchos relativos: {[round(v,3) for v in wr]}")
            except Exception as e:
                print(f"  {e}; queda equipartito en columnas.")
                wr = None
        if rows > 1 and _prompt_yesno("¿También destacar una fila?", False):
            ri = _prompt_int(f"Fila a destacar (1..{rows}, arriba→abajo)", 1)
            pct = _prompt_float("Cuánto más que el equipartito (%)", 30.0)
            try:
                hr = ratios_equipartition_boost(rows, max(1, min(rows, ri)) - 1, pct)
                print(f"  → altos relativos: {[round(v,3) for v in hr]}")
            except Exception as e:
                print(f"  {e}; queda equipartito en filas.")
                hr = None
        return wr, hr

    # absolute
    if cols > 1:
        raw = _prompt(f"Anchos relativos por columna ({cols} valores, coma)", ",".join(["1"] * cols))
        try:
            wr = [float(v.replace(",", ".")) for v in raw.replace(";", ",").split(",") if v.strip()]
            wr = sanitize_ratios(wr, cols, name="width_ratios")
        except Exception as e:
            print(f"  {e}; equipartito en columnas.")
            wr = None
    if rows > 1:
        raw = _prompt(f"Altos relativos por fila ({rows} valores, coma, arriba→abajo)", ",".join(["1"] * rows))
        try:
            hr = [float(v.replace(",", ".")) for v in raw.replace(";", ",").split(",") if v.strip()]
            hr = sanitize_ratios(hr, rows, name="height_ratios")
        except Exception as e:
            print(f"  {e}; equipartito en filas.")
            hr = None
    return wr, hr


def _choose_inset(default_rect=(0.55, 0.55, 0.42, 0.40)):
    keys = list(_INSET_PRESETS.keys())
    opts = [(k, f"{k}: {tuple(round(x,2) for x in _INSET_PRESETS[k])}") for k in keys]
    opts.append(("custom", "Numérico: left,bottom,width,height (fracción del eje principal)"))
    sel = _choose_from("Posición FIJA del inserto", opts, default_idx=0)
    if sel == "custom":
        raw = _responsive_input(f"  left,bottom,width,height [{','.join(map(str, default_rect))}]: ").strip()
        if raw:
            try:
                vals = [float(v.replace(",", ".")) for v in raw.replace(";", ",").split(",")]
                if len(vals) == 4:
                    return tuple(vals)
            except Exception:
                print("  Valor inválido; uso el preset por defecto.")
        return default_rect
    return _INSET_PRESETS.get(sel, default_rect)


def _label_menu(spec=None):
    """Submenú dedicado de rótulos. Devuelve un label_spec."""
    spec = {**default_label_spec(), **(spec or {})}
    while True:
        print("\n  ── Rótulos de panel ──")
        print(f"   1. ¿Rotular?: {'sí' if spec['enabled'] else 'no'}")
        print(f"   2. Formato: {spec['kind']} ({_LABEL_KINDS.get(spec['kind'],'')})")
        print(f"   3. Envoltura: {spec['wrap']} (ej. {format_panel_label(0, spec['kind'], spec['wrap'])})")
        print(f"   4. Posición: {spec['position']}")
        print(f"   5. Tamaño/peso/color: {spec['fontsize']}pt / {spec['fontweight']} / {spec['color']}")
        print(f"   6. Rótulo del inserto: {'sí' if spec['label_inset'] else 'no'}")
        print(f"   7. Override manual por panel: {spec['overrides'] or '(ninguno)'}")
        print("   8. Vista del orden actual (a, b, c…)")
        print("   9. Listo")
        op = _responsive_input("  Opción: ").strip()
        if op == "1":
            spec["enabled"] = _prompt_yesno("¿Rotular paneles?", spec["enabled"])
        elif op == "2":
            k = _choose_from("Formato", list(_LABEL_KINDS.items()),
                             default_idx=list(_LABEL_KINDS).index(spec["kind"]))
            if k:
                spec["kind"] = k
        elif op == "3":
            w = _choose_from("Envoltura", list(_LABEL_WRAPS.items()),
                             default_idx=list(_LABEL_WRAPS).index(spec["wrap"]))
            if w:
                spec["wrap"] = w
        elif op == "4":
            pos_opts = [(k, k.replace("_", " ")) for k in _LABEL_POSITIONS] + [("custom", "custom (x,y)")]
            keys = [k for k, _ in pos_opts]
            di = keys.index(spec["position"]) if spec["position"] in keys else 0
            p = _choose_from("Posición", pos_opts, default_idx=di)
            if p == "custom":
                raw = _prompt("x,y en fracción de ejes (0..1)", "0.02,1.02")
                try:
                    xy = [float(v.replace(",", ".")) for v in raw.replace(";", ",").split(",")]
                    if len(xy) == 2:
                        spec["position"] = "custom"
                        spec["custom_xy"] = (xy[0], xy[1])
                except Exception:
                    print("  Valor inválido.")
            elif p:
                spec["position"] = p
        elif op == "5":
            spec["fontsize"] = _prompt_float("Tamaño (pt)", spec["fontsize"])
            spec["fontweight"] = _prompt("Peso (normal/bold)", spec["fontweight"]) or spec["fontweight"]
            spec["color"] = _prompt("Color (nombre o #hex)", spec["color"]) or spec["color"]
        elif op == "6":
            spec["label_inset"] = _prompt_yesno("¿Rotular también el inserto?", spec["label_inset"])
        elif op == "7":
            raw = _prompt("Overrides como idx:texto separados por coma (ej. 0:a*,2:c')", "")
            ov = {}
            for chunk in raw.split(","):
                if ":" in chunk:
                    k, v = chunk.split(":", 1)
                    try:
                        ov[int(k.strip())] = v.strip()
                    except Exception:
                        pass
            spec["overrides"] = ov
        elif op == "8":
            seq = [format_panel_label(i, spec["kind"], spec["wrap"]) for i in range(9)]
            print("   Secuencia:", ", ".join(seq))
        elif op == "9" or op.lower() in {"q", "listo", "ok"}:
            return spec
        else:
            print("  Opción inválida.")


def _default_panel_height(layout):
    if layout in {"3x1", "3x2", "3x3"}:
        return 2.7
    if layout in {"1x3", "2x3"}:
        return 3.0
    return 3.2


def _collect_config(layout, base_filename="figura_compuesta"):
    sources = _collect_sources(layout)
    pw = _prompt_float("Ancho base por panel (pulgadas)", 3.6)
    ph = _prompt_float("Alto base por panel (pulgadas)", _default_panel_height(layout))
    wr, hr = _choose_ratios(layout)
    fs = _prompt_float("Escala global de fuentes dentro de cada panel", 0.9)
    eng = _choose_from("Motor de layout",
                       [("auto", "Auto: anti-solapamiento (recomendado)"),
                        ("manual", "Manual: yo controlo wspace/hspace")],
                       default_idx=0) or "auto"
    wspace = _prompt_float("wspace", 0.06)
    hspace = _prompt_float("hspace", 0.10)
    crop = _prompt_yesno("¿Recortar márgenes blancos en imágenes insertadas?", True)
    keep_st = _prompt_yesno("¿Promover suptitle de la fuente a título del panel si no hay título local?", True)
    suptitle = _responsive_input("  Suptitle global [Enter=ninguno]: ").strip() or None

    inset_rect = _INSET_PRESETS["arriba_derecha"]
    inset_legible = True
    inset_drop_title = True
    inset_min_pt, inset_label_pt, inset_max_ticks = 7.0, 8.0, 4
    if layout == "1x1_inset":
        inset_rect = _choose_inset(default_rect=inset_rect)
        inset_drop_title = _prompt_yesno("¿Quitar el título de la figura inserta?", True)
        print("\n  Al reducir la figura como inserto, lo que la vuelve ilegible es la")
        print("  densidad de ticks y el tamaño relativo de labels, no el tamaño de fuente.")
        inset_legible = _prompt_yesno("¿Forzar legibilidad del inserto (piso de fuente + menos ticks)?", True)
        if inset_legible:
            inset_min_pt = _prompt_float("Tamaño mínimo de números/ticks (pt)", 7.0)
            inset_label_pt = _prompt_float("Tamaño de nombres de ejes del inserto (pt)", 8.0)
            inset_max_ticks = _prompt_int("Máximo de ticks por eje en el inserto", 4)

    leg_pol = _choose_from(
        "Leyendas (cómo ubicarlas al achicar la figura en el panel)",
        [("auto_if_overlap", "Reubicar a «mejor lugar» solo si tapan datos (recomendado)"),
         ("best_always", "Siempre al «mejor lugar»"),
         ("preserve", "Dejar como en la figura original"),
         ("hide", "Ocultar leyendas")],
        default_idx=0) or "auto_if_overlap"

    print("\n  ── Rótulos ──  (podés afinar todo en el submenú)")
    label_spec = _label_menu(default_label_spec()) if _prompt_yesno("¿Configurar rótulos ahora?", True) else default_label_spec()

    out_default = str(_base_path(base_filename)) + f"_{layout}"
    out = _responsive_input(f"  Nombre base de salida [{out_default}]: ").strip().strip('"') or out_default

    return {
        "sources": sources, "layout": layout, "output_base": out,
        "panel_width": pw, "panel_height": ph, "width_ratios": wr, "height_ratios": hr,
        "font_scale": fs, "layout_engine": eng, "wspace": wspace, "hspace": hspace,
        "raster_crop_white": crop, "keep_source_suptitle": keep_st, "suptitle": suptitle,
        "inset_rect": inset_rect, "inset_legible": inset_legible, "inset_drop_title": inset_drop_title,
        "inset_min_pt": inset_min_pt, "inset_label_pt": inset_label_pt, "inset_max_ticks": inset_max_ticks,
        "label_spec": label_spec, "legend_policy": leg_pol, "dpi": 150,
    }


def _build_panel_from_config(cfg, previous_fig=None, *, close_previous=True):
    cache = cfg.setdefault("_cache", {})
    print("\n  Reconstruyendo la figura compuesta…")
    new_fig = create_composite_figure_from_files(
        cfg["sources"], layout=cfg["layout"], output_base=None, save=False,
        panel_width=cfg["panel_width"], panel_height=cfg["panel_height"],
        width_ratios=cfg.get("width_ratios"), height_ratios=cfg.get("height_ratios"),
        dpi=cfg.get("dpi", 150), font_scale=cfg["font_scale"],
        layout_engine=cfg.get("layout_engine", "auto"),
        wspace=cfg.get("wspace", 0.06), hspace=cfg.get("hspace", 0.10),
        label_spec=cfg.get("label_spec"),
        raster_crop_white=cfg["raster_crop_white"], keep_source_suptitle=cfg["keep_source_suptitle"],
        suptitle=cfg.get("suptitle"),
        inset_rect=cfg.get("inset_rect", _INSET_PRESETS["arriba_derecha"]),
        inset_legible=cfg.get("inset_legible", True), inset_drop_title=cfg.get("inset_drop_title", True),
        inset_min_pt=cfg.get("inset_min_pt", 7.0),
        inset_label_pt=cfg.get("inset_label_pt", 8.0), inset_max_ticks=cfg.get("inset_max_ticks", 4),
        legend_policy=cfg.get("legend_policy", "auto_if_overlap"),
        cache=cache, show=False,
    )
    if close_previous and previous_fig is not None:
        try:
            plt.close(previous_fig)
        except Exception:
            pass
    _show_figure_nonblocking(new_fig)
    print("  Previsualización lista (no se guardó nada todavía).")
    return new_fig


def _edit_geometry(cfg):
    print("\n  ── Tamaño, espaciado y proporciones ──")
    cfg["panel_width"] = _prompt_float("Ancho base por panel (in)", cfg["panel_width"])
    cfg["panel_height"] = _prompt_float("Alto base por panel (in)", cfg["panel_height"])
    cfg["layout_engine"] = _choose_from("Motor de layout",
                                        [("auto", "Auto anti-solapamiento"), ("manual", "Manual")],
                                        default_idx=0 if cfg.get("layout_engine", "auto") == "auto" else 1) or "auto"
    cfg["wspace"] = _prompt_float("wspace", cfg.get("wspace", 0.06))
    cfg["hspace"] = _prompt_float("hspace", cfg.get("hspace", 0.10))
    wr, hr = _choose_ratios(cfg["layout"], cfg.get("width_ratios"), cfg.get("height_ratios"))
    cfg["width_ratios"], cfg["height_ratios"] = wr, hr
    if cfg["layout"] == "1x1_inset" and _prompt_yesno("¿Cambiar posición del inserto?", False):
        cfg["inset_rect"] = _choose_inset(default_rect=cfg.get("inset_rect", _INSET_PRESETS["arriba_derecha"]))


def _edit_style(cfg):
    print("\n  ── Fuentes y opciones visuales ──")
    cfg["font_scale"] = _prompt_float("Escala global de fuentes", cfg["font_scale"])
    cfg["raster_crop_white"] = _prompt_yesno("¿Recortar blancos en imágenes?", cfg["raster_crop_white"])
    cfg["keep_source_suptitle"] = _prompt_yesno("¿Promover suptitle a título de panel?", cfg["keep_source_suptitle"])
    lp = _choose_from("Política de leyendas",
                      [("auto_if_overlap", "Reubicar solo si tapan datos"),
                       ("best_always", "Siempre al mejor lugar"),
                       ("preserve", "No tocar"),
                       ("hide", "Ocultar")],
                      default_idx=0) or "auto_if_overlap"
    cfg["legend_policy"] = lp
    st = _responsive_input(f"  Suptitle global [{cfg.get('suptitle') or ''}]: ").strip()
    cfg["suptitle"] = st or cfg.get("suptitle")
    if cfg["layout"] == "1x1_inset":
        cfg["inset_legible"] = _prompt_yesno("¿Forzar legibilidad del inserto?", cfg.get("inset_legible", True))
        if cfg["inset_legible"]:
            cfg["inset_min_pt"] = _prompt_float("Mínimo ticks (pt)", cfg.get("inset_min_pt", 7.0))
            cfg["inset_label_pt"] = _prompt_float("Nombres de ejes (pt)", cfg.get("inset_label_pt", 8.0))
            cfg["inset_max_ticks"] = _prompt_int("Máx. ticks por eje", cfg.get("inset_max_ticks", 4))


def _save_interactive(fig, cfg):
    if fig is None:
        print("  No hay figura para guardar.")
        return
    out = _responsive_input(f"  Nombre base [{cfg.get('output_base', 'figura_compuesta')}]: ").strip().strip('"') or cfg.get("output_base", "figura_compuesta")
    cfg["output_base"] = out
    all_data = bool(getattr(fig, "_pa_all_panels_from_data", False))
    if all_data:
        print("  Todas las fuentes son reconstruibles → puedo guardar JSON + CSV + PNG + PDF (recargable en el editor).")
    else:
        print("  Hay fuentes raster/vectoriales o CSV sin JSON → JSON/CSV reconstruible no es confiable.")
    inc = _prompt_yesno("¿Guardar JSON + CSV reconstruible?", all_data)
    png = _prompt_yesno("¿Guardar PNG?", True)
    pdf = _prompt_yesno("¿Guardar PDF?", True)
    dpi = _prompt_int("DPI de exportación", 300)
    save_composite_figure(fig, out, include_json=inc, save_png=png, save_pdf=pdf, dpi=dpi)


def _legend_menu(fig, cfg):
    """Maneja leyendas sobre la figura VIVA (sin reconstruir): reubicar, fijar
    posición, ocultar/mostrar y arrastrar con el mouse."""
    if fig is None:
        print("  No hay figura activa.")
        return
    while True:
        axes = _sort_axes_visual_order([a for a in fig.axes])
        print("\n  ── Leyendas ──")
        for i, ax in enumerate(axes):
            leg = ax.get_legend()
            estado = "sin leyenda" if leg is None else ("oculta" if not leg.get_visible() else "visible")
            tapa = " (tapa datos)" if (leg is not None and leg.get_visible() and _legend_overlaps_data(ax)) else ""
            print(f"   panel {i}: {estado}{tapa}")
        print("   a. Reubicar TODAS al mejor lugar")
        print("   b. Mejor lugar para un panel")
        print("   c. Posición específica para un panel")
        print("   d. Ocultar/mostrar leyenda de un panel")
        print("   e. Activar arrastre con el mouse (todas)")
        print(f"   f. Política por defecto para regenerar: {cfg.get('legend_policy','auto_if_overlap')}")
        print("   g. Volver")
        op = _responsive_input("  Opción: ").strip().lower()
        try:
            if op == "a":
                for ax in axes:
                    _set_legend_loc(ax, "best")
                _make_legends_draggable(fig, True)
            elif op in {"b", "c"}:
                idx = _prompt_int(f"Panel (0..{len(axes)-1})", 0)
                if not (0 <= idx < len(axes)):
                    print("  Índice fuera de rango."); continue
                if op == "b":
                    _set_legend_loc(axes[idx], "best")
                else:
                    loc = _choose_from("Posición", [(l, l) for l in _LEGEND_LOCS], default_idx=0)
                    if loc:
                        _set_legend_loc(axes[idx], loc)
                _make_legends_draggable(fig, True)
            elif op == "d":
                idx = _prompt_int(f"Panel (0..{len(axes)-1})", 0)
                if 0 <= idx < len(axes):
                    leg = axes[idx].get_legend()
                    if leg is not None:
                        leg.set_visible(not leg.get_visible())
                    else:
                        print("  Ese panel no tiene leyenda.")
            elif op == "e":
                _make_legends_draggable(fig, True)
                print("  Arrastrá las leyendas con el mouse sobre la figura.")
            elif op == "f":
                lp = _choose_from("Política por defecto",
                                  [("auto_if_overlap", "Reubicar solo si tapan"),
                                   ("best_always", "Siempre mejor lugar"),
                                   ("preserve", "No tocar"), ("hide", "Ocultar")],
                                  default_idx=0)
                if lp:
                    cfg["legend_policy"] = lp
            elif op in {"g", "q", "volver"}:
                return
            else:
                print("  Opción inválida.")
            try:
                fig.canvas.draw_idle()
                fig.canvas.flush_events()
            except Exception:
                pass
            _show_figure_nonblocking(fig)
        except Exception as e:
            print(f"  Error: {e}")


def _session_loop(cfg, fig):
    state = {"fig": fig}
    while True:
        print("\n  ── Sesión de figura compuesta ──")
        print("   1. Regenerar / refrescar")
        print("   2. Tamaño, espaciado y proporciones")
        print("   3. Fuentes y opciones visuales")
        print("   4. Rótulos de panel (submenú)")
        print("   5. Leyendas (reubicar / arrastrar / ocultar)")
        print("   6. Cambiar archivos fuente")
        print("   7. Acomodar tamaños con GUI")
        print("   8. Guardar figura actual")
        print("   9. Ver configuración")
        print("  10. Volver al menú principal")
        op = _responsive_input("  Opción: ").strip()
        try:
            if op == "1":
                state["fig"] = _build_panel_from_config(cfg, state["fig"])
            elif op == "2":
                _edit_geometry(cfg); state["fig"] = _build_panel_from_config(cfg, state["fig"])
            elif op == "3":
                _edit_style(cfg); state["fig"] = _build_panel_from_config(cfg, state["fig"])
            elif op == "4":
                cfg["label_spec"] = _label_menu(cfg.get("label_spec"))
                state["fig"] = _build_panel_from_config(cfg, state["fig"])
            elif op == "5":
                _legend_menu(state["fig"], cfg)
            elif op == "6":
                labels = _source_labels(cfg["layout"])
                new = []
                for i, lab in enumerate(labels):
                    old = cfg["sources"][i] if i < len(cfg["sources"]) else ""
                    s = _responsive_input(f"  {lab} [{old}]: ").strip().strip('"')
                    new.append(s or old)
                cfg["sources"] = new
                state["fig"] = _build_panel_from_config(cfg, state["fig"])
            elif op == "7":
                launch_size_gui(cfg, state)
            elif op == "8":
                _save_interactive(state["fig"], cfg)
            elif op == "9":
                view = {k: v for k, v in cfg.items() if not k.startswith("_")}
                print(json.dumps(_jsonable(view), indent=2, ensure_ascii=False))
            elif op == "10" or op.lower() in {"q", "volver", "salir"}:
                return state["fig"]
            else:
                print("  Opción inválida.")
        except Exception as e:
            print(f"  Error: {e}")


def menu_armar_figuras_compuestas(base_filename="figura_compuesta"):
    layout = _choose_layout()
    if not layout:
        return None
    cfg = _collect_config(layout, base_filename=base_filename)
    try:
        fig = _build_panel_from_config(cfg, previous_fig=None, close_previous=False)
    except Exception as e:
        print(f"\n  Error armando la figura: {e}")
        return None
    return _session_loop(cfg, fig)


def menu_rotular_paneles(fig=None):
    """Menú standalone de rótulos sobre una figura ya cargada en memoria."""
    if fig is None:
        print("  No hay figura activa. Armá primero una figura compuesta (opción 1).")
        return None
    axes = [ax for ax in fig.axes if not getattr(ax, "_pa_is_inset", False)]
    spec = _label_menu(getattr(fig, "_pa_label_spec", None))
    apply_panel_labels(fig, axes, spec)
    try:
        fig._pa_label_spec = spec
        fig.canvas.draw_idle()
    except Exception:
        pass
    _show_figure_nonblocking(fig)
    print("  Rótulos aplicados a la figura activa.")
    return fig


def main():
    last_fig = None
    while True:
        print("\n" + "═" * 72)
        print("  ARMADOR DE FIGURAS COMPUESTAS / PANELES  (v4)")
        print("═" * 72)
        print("  1. Armar figuras compuestas")
        print("  2. Rotular paneles de la figura activa")
        print("  3. Acomodar tamaños con GUI (figura activa)")
        print("  4. Listar layouts soportados")
        print("  5. Salir")
        op = _responsive_input("  Opción: ").strip()
        if op == "1":
            try:
                last_fig = menu_armar_figuras_compuestas() or last_fig
            except Exception as e:
                print(f"\n  Error: {e}")
        elif op == "2":
            menu_rotular_paneles(last_fig)
        elif op == "3":
            if last_fig is None:
                print("  No hay figura activa.")
            else:
                launch_size_gui({"layout": getattr(last_fig, "_pa_panel_metadata", {}).get("layout", "1x1"),
                                 "output_base": "figura_compuesta"}, {"fig": last_fig})
        elif op == "4":
            print("\n  Layouts:")
            for k, v in _PANEL_LAYOUTS.items():
                print(f"   - {k}: {v['label']}  (n={v['n']})")
        elif op == "5" or op.lower() in {"q", "salir", "quit"}:
            break
        else:
            print("  Opción inválida.")


__all__ = [
    "create_composite_figure_from_files", "save_composite_figure", "save_panel_metadata",
    "apply_panel_labels", "format_panel_label", "default_label_spec",
    "ratios_equipartition_boost", "sanitize_ratios", "list_panel_layouts",
    "launch_size_gui", "menu_armar_figuras_compuestas", "menu_rotular_paneles", "main",
]

if __name__ == "__main__":
    main()

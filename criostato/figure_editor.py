# -*- coding: utf-8 -*-
"""
figure_editor21.py
==================
Versión limpia, sin capas heredadas. Guarda, carga y edita figuras de matplotlib.
Uso rápido
----------
    from figure_editor21 import save_figure_data, load_figure, edit_cosmetics
    fig = plt.figure(1)
    save_figure_data(fig, "mi_figura")      # → mi_figura.json / .csv / .png
    fig = load_figure("mi_figura")
    fig = edit_cosmetics(fig)
Compatibilidad
--------------
Compatible con JSONs generados por versiones 3, 15, 17 y 20.
═══════════════════════════════════════════════════════════════════
CORRECCIONES Y NOVEDADES RESPECTO A figure_editor20
═══════════════════════════════════════════════════════════════════
BUG LEYENDA (principal):
  La causa raíz era que bba._bbox.bounds después de canvas.draw() contiene
  las coordenadas de figura del subplot (ej. (0.125, 0.11, 0.775, 0.77)),
  no coordenadas del axes (0,0,1,1). El chequeo _is_axis_bbox_v15 fallaba
  siempre, guardando el bbox incorrecto y produciendo una posición
  desplazada al cargar.
  FIX: se distinguen los casos por ancho del bbox:
    • bbox_to_anchor estándar (area): w > 0 → no guardar bbox, solo loc
    • bbox_to_anchor punto custom: w ≈ 0 → guardar el punto en coords Axes
  Además se guarda 'loc' siempre como STRING (no entero) usando una tabla
  de conversión, lo que elimina ambigüedades entre versiones de matplotlib.
TIGHT LAYOUT:
  • Nuevo menú en "Config general" → "Aplicar tight_layout".
  • Captura automáticamente los márgenes resultantes para que se guarden.
  • También existe opción para aplicar tight_layout al CARGAR una figura.
TEXTOS / ANOTACIONES CON RECUADRO (bbox):
  • Se guarda y restaura el recuadro (boxstyle, facecolor, edgecolor, lw, alpha).
  • El editor de textos permite agregar/quitar/editar el recuadro de cada texto.
  • Los textos también guardan fontweight y fontstyle.
  • Lugar en el menú: Subplot → 10. Textos/anotaciones (ya existía, ahora completo).
OTROS:
  • Archivo de ~900 líneas, sin las 4 capas de override de la versión 20.
  • Retrocompatible: campos ausentes en JSON viejos se ignoran silenciosamente.
"""
from __future__ import annotations
import json, csv, warnings
import copy
import tempfile
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import collections as mcoll
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle, Patch
from matplotlib.container import BarContainer
# ─────────────────────────────────────────────────────────────
#  Constantes
# ─────────────────────────────────────────────────────────────
_FORMAT_VERSION = 32
# Tabla entero → string para loc de leyenda (estándar matplotlib)
_LOC_INT_TO_STR: dict[int, str] = {
    0: "best",        1: "upper right",  2: "upper left",
    3: "lower left",  4: "lower right",  5: "right",
    6: "center left", 7: "center right", 8: "lower center",
    9: "upper center",10: "center",
}
_TEXT_PRESET_ANCHORS: dict[str, tuple[float, float, str, str]] = {
    "upper left":    (0.02, 0.98, "left",   "top"),
    "upper center":  (0.50, 0.98, "center", "top"),
    "upper right":   (0.98, 0.98, "right",  "top"),
    "center left":   (0.02, 0.50, "left",   "center"),
    "center":        (0.50, 0.50, "center", "center"),
    "center right":  (0.98, 0.50, "right",  "center"),
    "lower left":    (0.02, 0.02, "left",   "bottom"),
    "lower center":  (0.50, 0.02, "center", "bottom"),
    "lower right":   (0.98, 0.02, "right",  "bottom"),
}

_DEFAULT_FRAME_PRESET = {
    "left": 0.11,
    "right": 0.98,
    "bottom": 0.11,
    "top": 0.98,
}
# ─────────────────────────────────────────────────────────────
#  Helpers de serialización
# ─────────────────────────────────────────────────────────────
def _to_float(x, default=None):
    try:
        return float(x)
    except Exception:
        return x if default is None else default
def _jsonable(obj):
    if obj is None: return None
    if isinstance(obj, (np.integer,)): return int(obj)
    if isinstance(obj, (np.floating,)): return float(obj)
    if isinstance(obj, np.ndarray):  return obj.tolist()
    if isinstance(obj, (tuple, list)): return [_jsonable(x) for x in obj]
    if isinstance(obj, dict): return {str(k): _jsonable(v) for k, v in obj.items()}
    return obj
def _rgba(color):
    """Devuelve lista [R,G,B,A] o el valor original si falla."""
    try:
        from matplotlib.colors import to_rgba
        return [float(c) for c in to_rgba(color)]
    except Exception:
        return _jsonable(color)
def _base_path(filename: str) -> Path:
    return Path(filename).with_suffix("")
def _data_axes(fig) -> list:
    axes = list(getattr(fig, "axes", []))
    filtered = [ax for ax in axes
                if ax.get_position().width > 0.12 and ax.get_position().height > 0.12]
    return filtered if filtered else axes
_DEFAULT_EXPORT_PREFS = {
    "bbox_mode": "content",        # exact | tight | content
    "pad_inches": 0.02,             # para bbox_inches="tight"
    "autocrop_white": False,        # recorte adicional post-save en PNG
    "autocrop_tol": 250,            # umbral 0-255 para detectar blanco
    "autocrop_pad_px": 2,           # margen residual en px tras recorte
    "content_include_suptitle": True,# incluir suptitle/textos de figura en bbox "content"
}
def _get_export_prefs(fig, json_prefs=None) -> dict:
    """Resuelve preferencias de exportación con precedencia correcta.
    Orden: defaults < atributos de la figura < override explícito recibido.
    Así, una exportación puntual puede sobrescribir temporalmente lo guardado en la figura.
    """
    prefs = dict(_DEFAULT_EXPORT_PREFS)
    src = {}
    for k in _DEFAULT_EXPORT_PREFS:
        v = getattr(fig, f"_fe_{k}", None)
        if v is not None:
            src[k] = v
    if isinstance(json_prefs, dict):
        src.update(json_prefs)
    prefs.update(src)
    try:
        prefs["pad_inches"] = float(prefs.get("pad_inches", 0.02))
    except Exception:
        prefs["pad_inches"] = 0.02
    try:
        prefs["autocrop_tol"] = int(prefs.get("autocrop_tol", 250))
    except Exception:
        prefs["autocrop_tol"] = 250
    try:
        prefs["autocrop_pad_px"] = int(prefs.get("autocrop_pad_px", 2))
    except Exception:
        prefs["autocrop_pad_px"] = 2
    prefs["bbox_mode"] = str(prefs.get("bbox_mode", "content")).lower().strip()
    if prefs["bbox_mode"] not in {"exact", "tight", "content"}:
        prefs["bbox_mode"] = "content"
    prefs["autocrop_white"] = bool(prefs.get("autocrop_white", False))
    prefs["content_include_suptitle"] = bool(prefs.get("content_include_suptitle", True))
    return prefs
def _set_export_prefs(fig, prefs: dict):
    """Aplica preferencias saneadas a la figura.
    Importante: NO debe reinyectar primero los attrs ya guardados en fig,
    porque eso impediría cambiar valores cargados desde un JSON anterior.
    """
    sane = dict(_DEFAULT_EXPORT_PREFS)
    if isinstance(prefs, dict):
        sane.update(prefs)
    try:
        sane["pad_inches"] = float(sane.get("pad_inches", 0.02))
    except Exception:
        sane["pad_inches"] = 0.02
    try:
        sane["autocrop_tol"] = int(sane.get("autocrop_tol", 250))
    except Exception:
        sane["autocrop_tol"] = 250
    try:
        sane["autocrop_pad_px"] = int(sane.get("autocrop_pad_px", 2))
    except Exception:
        sane["autocrop_pad_px"] = 2
    sane["bbox_mode"] = str(sane.get("bbox_mode", "content")).lower().strip()
    if sane["bbox_mode"] not in {"exact", "tight", "content"}:
        sane["bbox_mode"] = "content"
    sane["autocrop_white"] = bool(sane.get("autocrop_white", False))
    sane["content_include_suptitle"] = bool(sane.get("content_include_suptitle", True))
    for k, v in sane.items():
        try:
            setattr(fig, f"_fe_{k}", v)
        except Exception:
            pass
def _crop_white_margins_array(arr, tol=250, pad_px=2):
    arr = np.asarray(arr)
    if arr.ndim not in (2, 3):
        return arr
    if np.issubdtype(arr.dtype, np.floating):
        work = np.clip(arr * 255.0, 0, 255).astype(np.uint8)
    else:
        work = arr.astype(np.uint8, copy=False)
    if work.ndim == 2:
        mask = work < tol
    else:
        rgb = work[..., :3]
        mask = np.any(rgb < tol, axis=2)
        if work.shape[2] >= 4:
            alpha = work[..., 3]
            mask = mask | (alpha > 0)
    coords = np.argwhere(mask)
    if coords.size == 0:
        return arr
    y0, x0 = coords.min(axis=0)[:2]
    y1, x1 = coords.max(axis=0)[:2] + 1
    y0 = max(0, int(y0) - int(pad_px))
    x0 = max(0, int(x0) - int(pad_px))
    y1 = min(arr.shape[0], int(y1) + int(pad_px))
    x1 = min(arr.shape[1], int(x1) + int(pad_px))
    return arr[y0:y1, x0:x1]
def _crop_saved_png_inplace(path, tol=250, pad_px=2):
    from PIL import Image
    p = Path(path)
    img = Image.open(p)
    arr = np.array(img)
    cropped = _crop_white_margins_array(arr, tol=tol, pad_px=pad_px)
    Image.fromarray(cropped).save(p)
    return p
def _compute_content_bbox_inches(fig, pad_inches=0.02, include_suptitle=True):
    """Devuelve un bbox en pulgadas basado en el contenido real de los axes.
    Usa get_tightbbox(renderer) de cada axes (incluyendo labels/ticks/leyendas cuando Matplotlib
    las reporta), y opcionalmente textos a nivel figura como suptitle.
    No depende de tight_layout().
    """
    try:
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
    except Exception:
        return None
    boxes = []
    for ax in _data_axes(fig):
        try:
            extra = []
            try:
                extra = list(ax.get_default_bbox_extra_artists())
            except Exception:
                extra = []
            bb = ax.get_tightbbox(renderer, bbox_extra_artists=extra)
            if bb is None:
                bb = ax.get_window_extent(renderer)
            if bb is not None and bb.width > 1 and bb.height > 1:
                boxes.append(bb)
        except Exception:
            try:
                bb = ax.get_window_extent(renderer)
                if bb is not None and bb.width > 1 and bb.height > 1:
                    boxes.append(bb)
            except Exception:
                pass
    if include_suptitle:
        fig_level_artists = []
        try:
            st = getattr(fig, '_suptitle', None)
            if st is not None and st.get_visible() and (st.get_text() or '').strip():
                fig_level_artists.append(st)
        except Exception:
            pass
        try:
            fig_level_artists.extend([t for t in getattr(fig, 'texts', []) if getattr(t, 'axes', None) is None and t.get_visible() and (t.get_text() or '').strip()])
        except Exception:
            pass
        try:
            fig_level_artists.extend([lg for lg in getattr(fig, 'legends', []) if lg.get_visible()])
        except Exception:
            pass
        for art in fig_level_artists:
            try:
                bb = art.get_window_extent(renderer)
                if bb is not None and bb.width > 1 and bb.height > 1:
                    boxes.append(bb)
            except Exception:
                pass
    if not boxes:
        return None
    from matplotlib.transforms import Bbox
    ub = Bbox.union(boxes)
    try:
        ub_in = ub.transformed(fig.dpi_scale_trans.inverted())
    except Exception:
        dpi = float(getattr(fig, 'dpi', 100.0) or 100.0)
        ub_in = Bbox.from_extents(ub.x0 / dpi, ub.y0 / dpi, ub.x1 / dpi, ub.y1 / dpi)
    pad_inches = max(0.0, float(pad_inches))
    if pad_inches:
        ub_in = ub_in.expanded((ub_in.width + 2*pad_inches) / max(ub_in.width, 1e-9),
                               (ub_in.height + 2*pad_inches) / max(ub_in.height, 1e-9))
    return ub_in

def _save_figure_image(fig, out_path, fmt=None, dpi=300, prefs=None):
    out = Path(out_path)
    prefs = _get_export_prefs(fig, prefs)
    if fmt is None:
        fmt = out.suffix.lower().lstrip('.')
    save_kw = {"dpi": dpi}
    mode = prefs.get("bbox_mode", "content")
    if mode == "tight":
        save_kw["bbox_inches"] = "tight"
        save_kw["pad_inches"] = prefs["pad_inches"]
    elif mode == "content":
        bb_in = _compute_content_bbox_inches(fig, pad_inches=prefs.get("pad_inches", 0.02), include_suptitle=prefs.get("content_include_suptitle", True))
        if bb_in is not None:
            save_kw["bbox_inches"] = bb_in
        else:
            save_kw["bbox_inches"] = "tight"
            save_kw["pad_inches"] = prefs["pad_inches"]
    fig.savefig(out, **save_kw)
    if out.suffix.lower() == '.png' and prefs.get("autocrop_white", False):
        _crop_saved_png_inplace(out, tol=prefs.get("autocrop_tol", 250), pad_px=prefs.get("autocrop_pad_px", 2))
    return out
def _content_bbox_fraction(fig):
    try:
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
    except Exception:
        return None
    boxes = []
    for ax in _data_axes(fig):
        try:
            bb = ax.get_tightbbox(renderer)
            if bb is not None and bb.width > 1 and bb.height > 1:
                boxes.append(bb)
        except Exception:
            pass
    if not boxes:
        return None
    from matplotlib.transforms import Bbox
    ub = Bbox.union(boxes)
    wpx, hpx = fig.canvas.get_width_height()
    return {
        "width_fraction": float(ub.width / max(wpx, 1)),
        "height_fraction": float(ub.height / max(hpx, 1)),
        "bbox_pixels": [float(ub.x0), float(ub.y0), float(ub.x1), float(ub.y1)],
        "canvas_pixels": [int(wpx), int(hpx)],
    }
# ─────────────────────────────────────────────────────────────
#  Serialización de textos (título, labels, anotaciones)
# ─────────────────────────────────────────────────────────────
def _ser_text(t) -> dict:
    """Serializa un objeto matplotlib.Text a dict."""
    if t is None:
        return {"text": "", "fontsize": None, "fontweight": None,
                "fontstyle": None, "color": None, "visible": True}
    if isinstance(t, dict):
        return t  # ya serializado
    try:
        return {
            "text":       t.get_text(),
            "fontsize":   _to_float(t.get_fontsize()),
            "fontweight": t.get_fontweight(),
            "fontstyle":  t.get_fontstyle(),
            "color":      _rgba(t.get_color()),
            "visible":    bool(t.get_visible()),
        }
    except Exception:
        return {"text": str(t), "fontsize": None, "fontweight": None,
                "fontstyle": None, "color": None, "visible": True}
def _apply_text(target, spec):
    """Aplica propiedades de fuente a un Text. spec puede ser dict o str."""
    if target is None:
        return
    if isinstance(spec, str):
        try: target.set_text(spec)
        except Exception: pass
        return
    if not isinstance(spec, dict):
        return
    for setter, key in [
        (target.set_text,       "text"),
        (target.set_fontsize,   "fontsize"),
        (target.set_fontweight, "fontweight"),
        (target.set_fontstyle,  "fontstyle"),
        (target.set_color,      "color"),
    ]:
        if spec.get(key) is not None:
            try: setter(spec[key])
            except Exception: pass
    if spec.get("visible") is not None:
        try: target.set_visible(bool(spec["visible"]))
        except Exception: pass
def _ser_annotation_bbox(txt) -> dict | None:
    """Serializa el recuadro (bbox) de un texto de anotación."""
    try:
        bp = txt.get_bbox_patch()
        if bp is None or not bp.get_visible():
            return None
        bs = bp.get_boxstyle()
        # Extraer nombre del boxstyle
        try:
            bsname = bs.stylename  # disponible en algunas versiones
        except AttributeError:
            bsname = type(bs).__name__.lower()  # Round→round, Square→square
        return {
            "boxstyle":  bsname,
            "facecolor": _rgba(bp.get_facecolor()),
            "edgecolor": _rgba(bp.get_edgecolor()),
            "linewidth": _to_float(bp.get_linewidth()),
            "alpha":     _to_float(bp.get_alpha()) if bp.get_alpha() is not None else None,
            "pad":       _to_float(getattr(bs, "pad", 0.3)),
        }
    except Exception:
        return None
def _apply_annotation_bbox(txt, spec: dict | None):
    """Aplica (o quita) el recuadro de un texto."""
    if spec is None:
        try: txt.set_bbox(None)
        except Exception: pass
        return
    try:
        boxstyle = f"{spec.get('boxstyle','round')},pad={spec.get('pad', 0.3)}"
        txt.set_bbox({
            "boxstyle":  boxstyle,
            "facecolor": spec.get("facecolor", "lightyellow"),
            "edgecolor": spec.get("edgecolor", "black"),
            "linewidth": spec.get("linewidth", 1.0),
            "alpha":     spec.get("alpha", 1.0),
        })
    except Exception:
        pass
# ─────────────────────────────────────────────────────────────
#  Serialización de ticks
# ─────────────────────────────────────────────────────────────
def _ser_ticks(ax, axis: str = "x") -> dict:
    axis_obj = ax.xaxis if axis == "x" else ax.yaxis
    labels = axis_obj.get_ticklabels()
    first = next((t for t in labels if t.get_text() or t.get_visible()), labels[0] if labels else None)
    direction = "out"
    try:
        kw = getattr(axis_obj, "_major_tick_kw", {}) or {}
        direction = kw.get("tickdir", kw.get("direction", "out"))
    except Exception:
        pass
    return {
        "fontsize":  _to_float(first.get_fontsize())  if first else None,
        "rotation":  _to_float(first.get_rotation())  if first else None,
        "color":     _rgba(first.get_color())         if first else None,
        "direction": direction,
    }
def _apply_ticks(ax, spec: dict, axis: str = "x"):
    if not isinstance(spec, dict):
        return
    params = {}
    if spec.get("fontsize")  is not None: params["labelsize"]  = spec["fontsize"]
    if spec.get("color")     is not None:
        params["labelcolor"] = spec["color"]
        params["colors"]     = spec["color"]
    if spec.get("direction") in {"in", "out", "inout"}:
        params["direction"] = spec["direction"]
    try:
        if params: ax.tick_params(axis=axis, **params)
    except Exception:
        pass
    if spec.get("rotation") is not None:
        try:
            lbs = ax.get_xticklabels() if axis == "x" else ax.get_yticklabels()
            for lb in lbs:
                lb.set_rotation(spec["rotation"])
        except Exception:
            pass
# ─────────────────────────────────────────────────────────────
#  Serialización de leyenda (CORREGIDA)
# ─────────────────────────────────────────────────────────────
def _ser_legend(ax) -> dict | None:
    """
    Serializa la leyenda del subplot.
    CORRECCIÓN PRINCIPAL:
    Después de canvas.draw(), leg.get_bbox_to_anchor()._bbox.bounds contiene
    las coordenadas de FIGURA del subplot (ej. (0.125, 0.11, 0.775, 0.77)),
    NO las coordenadas del Axes (0,0,1,1). Por eso el chequeo _is_axis_bbox
    fallaba siempre y guardaba un bbox incorrecto.
    Solución: discriminar por el ANCHO del bbox interno:
    • Ancho > 0 → bbox estándar del subplot (area): NO guardar bbox_to_anchor
    • Ancho ≈ 0 → punto de anclaje custom: GUARDAR el punto
    """
    leg = ax.get_legend()
    if leg is None:
        return None
    # ── handles y labels ──────────────────────────────────────
    handles = None
    for attr in ("legend_handles", "legendHandles"):
        handles = getattr(leg, attr, None)
        if handles is not None:
            break
    if handles is None:
        try:
            handles, _ = ax.get_legend_handles_labels()
        except Exception:
            handles = []
    labels = [t.get_text() for t in leg.get_texts()] if leg.get_texts() else []
    entries = []
    for h, lab in zip(handles, labels):
        if isinstance(h, Line2D):
            hdict = {
                "kind": "Line2D",
                "color":          _rgba(h.get_color()),
                "linewidth":      _to_float(h.get_linewidth()),
                "linestyle":      h.get_linestyle(),
                "marker":         h.get_marker(),
                "markersize":     _to_float(h.get_markersize()),
                "markerfacecolor": _rgba(h.get_markerfacecolor()),
                "markeredgecolor": _rgba(h.get_markeredgecolor()),
                "alpha":          _to_float(h.get_alpha()) if h.get_alpha() is not None else None,
            }
        elif isinstance(h, Patch):
            hdict = {
                "kind":      "Patch",
                "facecolor": _jsonable(h.get_facecolor()),
                "edgecolor": _jsonable(h.get_edgecolor()),
                "linewidth": _to_float(h.get_linewidth()),
                "linestyle": h.get_linestyle(),
                "hatch":     h.get_hatch(),
                "alpha":     _to_float(h.get_alpha()) if h.get_alpha() is not None else None,
            }
        else:
            try:
                col = _rgba(h.get_color())
            except Exception:
                col = _rgba("k")
            hdict = {"kind": "Line2D", "color": col, "linewidth": 2.0,
                     "linestyle": "-", "marker": "", "markersize": 0.0,
                     "markerfacecolor": col, "markeredgecolor": col, "alpha": None}
        entries.append({"label": lab, "handle": hdict})
    title = ""
    try:
        title = leg.get_title().get_text()
    except Exception:
        pass
    if not entries and not title:
        return None
    # ── loc como STRING (no entero) ───────────────────────────
    loc_str = "best"
    try:
        loc_int = int(leg._loc)
        loc_str = _LOC_INT_TO_STR.get(loc_int, "best")
    except Exception:
        try:
            loc_str = str(leg.get_loc())
        except Exception:
            loc_str = "best"
    # ── bbox_to_anchor: solo si es un punto custom ─────────────
    # Se guarda ÚNICAMENTE cuando el usuario usó bbox_to_anchor explícito
    # (punto fuera o dentro del axes). Para loc estándar, el bbox interno
    # tiene w > 0 (son las coords de figura del subplot), y NO se guarda.
    bba_point = None
    try:
        bba = leg.get_bbox_to_anchor()
        if bba is not None:
            b = bba._bbox.bounds          # x0, y0, w, h
            w_inner, h_inner = float(b[2]), float(b[3])
            is_point_anchor = (abs(w_inner) < 0.01 and abs(h_inner) < 0.01)
            if is_point_anchor:
                # Guardar el punto en coordenadas del Axes
                bba_point = [float(b[0]), float(b[1])]
    except Exception:
        pass
    # ── estilo del marco ──────────────────────────────────────
    style: dict = {
        "loc":                   loc_str,
        "bbox_to_anchor_point":  bba_point,   # [x, y] en coords Axes, o None
    }
    try:
        style["frameon"]       = bool(leg.get_frame_on())
        frame = leg.get_frame()
        style["framealpha"]     = _to_float(frame.get_alpha()) if frame.get_alpha() is not None else None
        style["frameedgecolor"] = _rgba(frame.get_edgecolor())
        style["framefacecolor"] = _rgba(frame.get_facecolor())
    except Exception:
        style.update({"frameon": None, "framealpha": None,
                      "frameedgecolor": None, "framefacecolor": None})
    try:
        style["title_fontsize"] = _to_float(leg.get_title().get_fontsize())
    except Exception:
        style["title_fontsize"] = None
    try:
        texts = leg.get_texts()
        style["label_fontsize"] = _to_float(texts[0].get_fontsize()) if texts else None
    except Exception:
        style["label_fontsize"] = None
    for attr in ("columnspacing", "labelspacing", "handlelength",
                 "handletextpad", "borderpad", "borderaxespad"):
        try:
            style[attr] = _to_float(getattr(leg, attr))
        except Exception:
            style[attr] = None
    try:
        style["ncol"] = int(getattr(leg, "_ncols", getattr(leg, "_ncol", 1)))
    except Exception:
        style["ncol"] = 1
    return {"title": title, "entries": entries, "style": style}
def _rebuild_legend(ax, leginfo: dict | None):
    """Reconstruye la leyenda desde el JSON guardado.
    Compatible con JSONs de versiones 3, 15, 17, 20 y 21.
    """
    if not leginfo or not isinstance(leginfo, dict):
        return None
    title   = leginfo.get("title", "") or ""
    entries = leginfo.get("entries", []) or []
    style   = leginfo.get("style", {})  or {}
    if not entries and not title:
        return None
    # Construir handles
    prefer_axis_handles = bool(style.get("prefer_axis_handles", False) or leginfo.get("prefer_axis_handles", False))
    if prefer_axis_handles:
        handles, labels = _match_axis_handles_to_legend(ax, leginfo)
    else:
        handles = [_legend_handle_from_spec((e or {}).get("handle", {})) for e in entries]
        labels = [e.get("label","") for e in entries]
    # Construir kwargs — loc siempre como string
    loc = style.get("loc", "best")
    # Retrocompatibilidad: si loc es entero (JSONs viejos)
    try:
        loc_int = int(loc)
        loc = _LOC_INT_TO_STR.get(loc_int, "best")
    except (TypeError, ValueError):
        pass
    kwargs: dict = {}
    if loc: kwargs["loc"] = loc
    # bbox_to_anchor solo si es un punto custom guardado con v21
    bba_pt = style.get("bbox_to_anchor_point")
    if bba_pt is not None:
        try:
            kwargs["bbox_to_anchor"] = (float(bba_pt[0]), float(bba_pt[1]))
        except Exception:
            pass
    else:
        # Retrocompatibilidad con JSONs v15/17/20 que guardaban bbox_to_anchor_bounds
        bba_old = style.get("bbox_to_anchor_bounds")
        if bba_old is not None:
            try:
                x0, y0, w, h = [float(v) for v in bba_old]
                # Solo aplicar si es un punto (w≈0, h≈0) — no si es el bbox del axes
                if abs(w) < 0.05 and abs(h) < 0.05:
                    kwargs["bbox_to_anchor"] = (x0, y0)
                # Si w y h son grandes, era el bbox de figura guardado por error → ignorar
            except Exception:
                pass
    if style.get("frameon") is not None:
        kwargs["frameon"] = bool(style["frameon"])
    ncol = style.get("ncol", style.get("ncols"))
    if ncol is not None:
        try: kwargs["ncol"] = int(ncol)
        except Exception: pass
    for k in ("columnspacing","labelspacing","handlelength","handletextpad","borderpad","borderaxespad"):
        if style.get(k) is not None:
            kwargs[k] = style[k]
    try:
        leg = ax.legend(handles, labels, title=title, **kwargs)
    except TypeError:
        leg = ax.legend(handles, labels, title=title,
                        loc=kwargs.get("loc","best"),
                        frameon=kwargs.get("frameon",True))
    if leg is None:
        return None
    try:
        if style.get("title_fontsize") is not None:
            leg.get_title().set_fontsize(style["title_fontsize"])
    except Exception: pass
    try:
        if style.get("label_fontsize") is not None:
            for t in leg.get_texts():
                t.set_fontsize(style["label_fontsize"])
    except Exception: pass
    try:
        frame = leg.get_frame()
        if style.get("framealpha")     is not None: frame.set_alpha(style["framealpha"])
        if style.get("frameedgecolor") is not None: frame.set_edgecolor(style["frameedgecolor"])
        if style.get("framefacecolor") is not None: frame.set_facecolor(style["framefacecolor"])
    except Exception: pass

    return leg

# ─────────────────────────────────────────────────────────────
#  Leyenda compartida entre subplots
# ─────────────────────────────────────────────────────────────
def _norm_marker_value(m):
    if m is None:
        return ""
    s = str(m).strip().lower()
    if s in {"none", "null", "nan"}:
        return ""
    return str(m)

def _norm_linestyle_value(ls):
    if ls is None:
        return "-"
    s = str(ls).strip().lower()
    if not s:
        return "-"
    return s

def _legend_handle_from_spec(h: dict):
    h = h or {}
    if h.get("kind") == "Patch":
        p = Patch(facecolor=h.get("facecolor", "none"),
                  edgecolor=h.get("edgecolor", "k"),
                  linewidth=h.get("linewidth", 1.0),
                  linestyle=h.get("linestyle", "-"),
                  hatch=h.get("hatch") or None)
        if h.get("alpha") is not None:
            try:
                p.set_alpha(h["alpha"])
            except Exception:
                pass
        return p
    ln = Line2D([0], [0],
                color=h.get("color", "k"),
                linewidth=h.get("linewidth", 1.5),
                linestyle=h.get("linestyle", "-"),
                marker=h.get("marker", ""),
                markersize=h.get("markersize", 0.0),
                markerfacecolor=h.get("markerfacecolor", h.get("color", "k")),
                markeredgecolor=h.get("markeredgecolor", h.get("color", "k")))
    if h.get("alpha") is not None:
        try:
            ln.set_alpha(h["alpha"])
        except Exception:
            pass
    return ln

def _style_distance_line_to_handle_spec(line, hspec: dict) -> float:
    hspec = hspec or {}
    score = 0.0
    try:
        lc = np.asarray(_rgba(line.get_color()), dtype=float)
        hc = np.asarray(_rgba(hspec.get("color", "k")), dtype=float)
        score += float(np.sum((lc - hc) ** 2)) * 25.0
    except Exception:
        score += 10.0
    try:
        lls = _norm_linestyle_value(line.get_linestyle())
        hls = _norm_linestyle_value(hspec.get("linestyle", "-"))
        if lls != hls:
            score += 6.0
    except Exception:
        score += 2.0
    try:
        lm = _norm_marker_value(line.get_marker())
        hm = _norm_marker_value(hspec.get("marker", ""))
        if lm != hm:
            score += 8.0
    except Exception:
        score += 2.0
    try:
        llw = float(line.get_linewidth() or 0.0)
        hlw = float(hspec.get("linewidth", 0.0) or 0.0)
        score += min(3.0, abs(llw - hlw))
    except Exception:
        score += 1.0
    try:
        lms = float(line.get_markersize() or 0.0)
        hms = float(hspec.get("markersize", 0.0) or 0.0)
        score += min(2.0, 0.2 * abs(lms - hms))
    except Exception:
        pass
    if getattr(line, "_fe_refline", None):
        score += 1000.0
    return score

def _match_axis_handles_to_legend(ax, leginfo: dict):
    entries = leginfo.get("entries", []) if isinstance(leginfo, dict) else []
    lines = [ln for ln in ax.get_lines() if not getattr(ln, "_fe_refline", None)]
    used = set()
    out_handles, out_labels = [], []
    for e in entries:
        label = e.get("label", "")
        hspec = e.get("handle", {}) or {}
        best = None
        best_score = float("inf")
        # 1) preferir match exacto por label si existe en el eje
        if label:
            for ln in lines:
                if id(ln) in used:
                    continue
                if str(ln.get_label()) == str(label):
                    best = ln
                    best_score = -1.0
                    break
        # 2) si no hay label útil, matchear por estilo
        if best is None:
            for ln in lines:
                if id(ln) in used:
                    continue
                sc = _style_distance_line_to_handle_spec(ln, hspec)
                if sc < best_score:
                    best = ln
                    best_score = sc
        if best is not None and best_score < 50.0:
            out_handles.append(best)
            out_labels.append(label)
            used.add(id(best))
        else:
            out_handles.append(_legend_handle_from_spec(hspec))
            out_labels.append(label)
    return out_handles, out_labels

def _shared_legend_spec_from_info(shared_info):
    if isinstance(shared_info, dict) and isinstance(shared_info.get("legend"), dict):
        leginfo = copy.deepcopy(shared_info.get("legend"))
    elif isinstance(shared_info, dict):
        leginfo = copy.deepcopy(shared_info)
    else:
        leginfo = None
    if isinstance(leginfo, dict):
        style = leginfo.setdefault("style", {})
        style.setdefault("prefer_axis_handles", True)
    return leginfo

def _rebuild_shared_legend(ax, shared_info: dict | None):
    leginfo = _shared_legend_spec_from_info(shared_info)
    if not leginfo:
        return None
    return _rebuild_legend(ax, leginfo)

def _infer_shared_legend_for_axis(fig_props: dict, axis_index: int):
    axes = (fig_props or {}).get("axes", []) or []
    if axis_index < 0 or axis_index >= len(axes):
        return None
    target = axes[axis_index] or {}
    if target.get("legend"):
        return None
    n_target_lines = len((target.get("lines") or []))
    if n_target_lines <= 0:
        return None
    candidates = []
    for j, src in enumerate(axes):
        if j == axis_index:
            continue
        leg = (src or {}).get("legend")
        if not isinstance(leg, dict):
            continue
        entries = leg.get("entries") or []
        if not entries:
            continue
        # Heurística simple: el eje destino debe tener al menos tantas curvas útiles
        # como entradas de leyenda. Esto evita adjuntar metadata absurda.
        if n_target_lines < len(entries):
            continue
        score = abs(j - axis_index)
        candidates.append((score, j, leg))
    if not candidates:
        return None
    _, src_idx, leg = sorted(candidates, key=lambda t: (t[0], t[1]))[0]
    return {
        "source_axis_index": int(src_idx),
        "source_axis_title": ((axes[src_idx] or {}).get("title") or {}).get("text", ""),
        "mode": "shared_from_sibling",
        "show_by_default": False,
        "legend": copy.deepcopy(leg),
    }

# ─────────────────────────────────────────────────────────────
#  Otros serializadores
# ─────────────────────────────────────────────────────────────
def _ser_spines(ax) -> dict:
    out = {}
    for name, sp in ax.spines.items():
        try:
            out[name] = {
                "visible":   bool(sp.get_visible()),
                "color":     _rgba(sp.get_edgecolor()),
                "linewidth": _to_float(sp.get_linewidth()),
            }
        except Exception:
            out[name] = {"visible": True, "color": None, "linewidth": None}
    return out
def _apply_spines(ax, spines: dict):
    if not spines:
        return
    for name, props in spines.items():
        if name not in ax.spines:
            continue
        sp = ax.spines[name]
        if props.get("visible") is not None:
            try: sp.set_visible(bool(props["visible"]))
            except Exception: pass
        if props.get("color") is not None:
            try: sp.set_edgecolor(props["color"])
            except Exception: pass
        if props.get("linewidth") is not None:
            try: sp.set_linewidth(float(props["linewidth"]))
            except Exception: pass
def _ser_grid(ax) -> dict:
    gl = [ln for ln in (ax.get_xgridlines() + ax.get_ygridlines()) if ln.get_visible()]
    props: dict = {"visible": len(gl) > 0, "color": None, "linestyle": None,
                   "linewidth": None, "alpha": None}
    if gl:
        try:
            ln = gl[0]
            props["color"]     = _rgba(ln.get_color())
            props["linestyle"] = ln.get_linestyle()
            props["linewidth"] = _to_float(ln.get_linewidth())
            props["alpha"]     = _to_float(ln.get_alpha()) if ln.get_alpha() is not None else None
        except Exception:
            pass
    return props
def _apply_grid(ax, grid):
    if grid is True:
        ax.grid(True); return
    if grid in (False, None):
        ax.grid(False); return
    if isinstance(grid, bool):
        ax.grid(bool(grid)); return
    visible = bool(grid.get("visible", False))
    kw = {k: grid[k] for k in ("color","linestyle","linewidth","alpha") if grid.get(k) is not None}
    ax.grid(visible, **kw)
def _apply_rect_props(p: Rectangle, props: dict):
    for setter, key in [
        (p.set_facecolor, "facecolor"), (p.set_edgecolor, "edgecolor"),
        (p.set_linewidth, "linewidth"), (p.set_linestyle, "linestyle"),
        (p.set_alpha,     "alpha"),     (p.set_hatch,     "hatch"),
        (p.set_zorder,    "zorder"),    (p.set_label,     "label"),
    ]:
        if props.get(key) is not None:
            try: setter(props[key])
            except Exception: pass
    if props.get("visible") is not None:
        try: p.set_visible(bool(props["visible"]))
        except Exception: pass
def _is_refline(ax, line) -> str | None:
    """Retorna 'v', 'h', o None."""
    tag = getattr(line, "_fe_refline", None)
    if tag in {"v", "h"}:
        return tag
    try:
        xd = list(line.get_xdata())
        yd = list(line.get_ydata())
        if len(xd) < 2 or len(yd) < 2:
            return None
        is_data_tf = (line.get_transform() == ax.transData)
        const_x = all(float(v) == float(xd[0]) for v in xd)
        const_y = all(float(v) == float(yd[0]) for v in yd)
        if const_x and not is_data_tf:
            return "v"
        if const_y and not is_data_tf:
            return "h"
    except Exception:
        pass
    return None
def _ser_line(line) -> dict:
    return {
        "label":           line.get_label() if line.get_label() and not str(line.get_label()).startswith("_") else "",
        "color":           _jsonable(line.get_color()),
        "linewidth":       _to_float(line.get_linewidth()),
        "linestyle":       line.get_linestyle(),
        "marker":          line.get_marker(),
        "markersize":      _to_float(line.get_markersize()),
        "markerfacecolor": _jsonable(line.get_markerfacecolor()),
        "markeredgecolor": _jsonable(line.get_markeredgecolor()),
        "markeredgewidth": _to_float(line.get_markeredgewidth()),
        "alpha":           _to_float(line.get_alpha()) if line.get_alpha() is not None else None,
        "visible":         bool(line.get_visible()),
        "zorder":          _to_float(line.get_zorder()) if line.get_zorder() is not None else None,
    }
# ─────────────────────────────────────────────────────────────
#  GUARDAR FIGURA
# ─────────────────────────────────────────────────────────────
def save_figure_data(fig, filename, save_png: bool = True, colorbar_labels=None):
    """Guarda cosmética completa (.json), datos numéricos (.csv) y miniatura (.png).
    Parámetros
    ----------
    fig            : matplotlib.figure.Figure
    filename       : str  nombre base sin extensión
    save_png       : bool (default True)
    colorbar_labels: dict opcional {panel_index: label}
    """
    base      = _base_path(filename)
    data_axes = _data_axes(fig)
    try:
        fig.canvas.draw()
    except Exception:
        pass
    # Layout ─────────────────────────────────────────────────
    raw_positions = [list(map(float, ax.get_position().bounds)) for ax in data_axes]
    serialize_positions = bool(getattr(fig, "_serialize_axes_positions", True))
    positions = raw_positions if serialize_positions else [None for _ in raw_positions]
    layout    = (1, len(data_axes))
    try:
        ys = sorted({round(p[1], 3) for p in positions}, reverse=True)
        xs = sorted({round(p[0], 3) for p in positions})
        if len(ys) * len(xs) >= len(data_axes):
            layout = (len(ys), len(xs))
    except Exception:
        pass
    # Suptitle ───────────────────────────────────────────────
    st = getattr(fig, "_suptitle", None)
    suptitle_spec = _ser_text(st) if st is not None and st.get_text() else {"text": ""}
    # subplots_adjust ────────────────────────────────────────
    save_subplots_adjust_none = bool(getattr(fig, "_save_subplots_adjust_none", False))
    try:
        sp = fig.subplotpars
        adj = {"left": _to_float(sp.left),   "right":  _to_float(sp.right),
               "top":  _to_float(sp.top),    "bottom": _to_float(sp.bottom),
               "wspace": _to_float(sp.wspace),"hspace": _to_float(sp.hspace)}
        if save_subplots_adjust_none:
            adj = None
    except Exception:
        adj = None if save_subplots_adjust_none else {}
    fig_props = {
        "format_version":   _FORMAT_VERSION,
        "size":             _jsonable(fig.get_size_inches()),
        "dpi":              _to_float(fig.dpi) if hasattr(fig, "dpi") else None,
        "figure_facecolor": _rgba(fig.get_facecolor()),
        "subplot_layout":   _jsonable(layout),
        "subplots_adjust":  adj,
        "suptitle":         suptitle_spec.get("text",""),
        "suptitle_obj":     suptitle_spec,
        "export_prefs":     _jsonable(_get_export_prefs(fig)),
        "layout_engine":    {
            "serialize_positions": serialize_positions,
            "apply_tight_layout_on_load": bool(getattr(fig, "_apply_tight_layout_on_load", False)),
            "save_subplots_adjust_none": save_subplots_adjust_none,
        },
        "axes":             [],
    }
    csv_rows   = []
    csv_header = ["axis_index","artist_type","label","x","y"]
    for idx, ax in enumerate(data_axes):
        ax_props: dict = {
            # textos con propiedades de fuente
            "title":  _ser_text(ax.title),
            "xlabel": _ser_text(ax.xaxis.label),
            "ylabel": _ser_text(ax.yaxis.label),
            # ejes
            "xlim":  _jsonable(ax.get_xlim()),
            "ylim":  _jsonable(ax.get_ylim()),
            "xscale": ax.get_xscale(),
            "yscale": ax.get_yscale(),
            # cosmética subplot
            "facecolor": _rgba(ax.get_facecolor()),
            "position":  _jsonable(positions[idx]),
            "aspect":    ax.get_aspect(),
            "spines":    _ser_spines(ax),
            "grid":      _ser_grid(ax),
            # ticks
            "ticks": {"x": _ser_ticks(ax, "x"), "y": _ser_ticks(ax, "y")},
            # artistas
            "lines": [], "scatters": [], "vlines": [], "hlines": [],
            "bars": [], "line_collections": [], "images": [],
            "texts": [],
            "legend": _ser_legend(ax),
            "shared_legend": copy.deepcopy(getattr(ax, "_fe_shared_legend", None)),
        }
        # ── Líneas ───────────────────────────────────────────
        line_count = 0
        for line in ax.get_lines():
            try:
                xd = _jsonable(line.get_xdata())
                yd = _jsonable(line.get_ydata())
            except Exception:
                continue
            if xd is None or yd is None or len(xd) == 0:
                continue
            entry = _ser_line(line)
            kind  = _is_refline(ax, line)
            if kind == "v":
                entry["x"] = _to_float(xd[0], 0.0)
                ax_props["vlines"].append(entry)
            elif kind == "h":
                entry["y"] = _to_float(yd[0], 0.0)
                ax_props["hlines"].append(entry)
            else:
                line_count += 1
                if not entry["label"]:
                    entry["label"] = f"line{line_count}"
                entry["x"] = xd
                entry["y"] = yd
                ax_props["lines"].append(entry)
                for x, y in zip(xd, yd):
                    csv_rows.append([idx, "line", entry["label"], x, y])
        # ── Barras ───────────────────────────────────────────
        seen_patch_ids: set = set()
        for cont in [c for c in getattr(ax, "containers", []) if isinstance(c, BarContainer)]:
            ci = {"label": cont.get_label() if hasattr(cont, "get_label") else "", "patches": []}
            for p in getattr(cont, "patches", []):
                seen_patch_ids.add(id(p))
                ci["patches"].append({
                    "x": _to_float(p.get_x()),       "y":      _to_float(p.get_y()),
                    "width": _to_float(p.get_width()),"height": _to_float(p.get_height()),
                    "angle": _to_float(getattr(p, "angle", 0.0)),
                    "facecolor": _jsonable(p.get_facecolor()),
                    "edgecolor": _jsonable(p.get_edgecolor()),
                    "linewidth": _to_float(p.get_linewidth()),
                    "linestyle": p.get_linestyle(),
                    "hatch":     p.get_hatch(),
                    "alpha":     _to_float(p.get_alpha()) if p.get_alpha() is not None else None,
                    "label":     p.get_label() if p.get_label() and not str(p.get_label()).startswith("_") else "",
                    "visible":   bool(p.get_visible()),
                    "zorder":    _to_float(p.get_zorder()) if p.get_zorder() is not None else None,
                })
            if ci["patches"]:
                ax_props["bars"].append(ci)
        for p in ax.patches:  # loose rectangles
            if id(p) in seen_patch_ids or not isinstance(p, Rectangle):
                continue
            ax_props["bars"].append({
                "label": p.get_label() if p.get_label() and not str(p.get_label()).startswith("_") else "",
                "patches": [{"x": _to_float(p.get_x()), "y": _to_float(p.get_y()),
                              "width": _to_float(p.get_width()), "height": _to_float(p.get_height()),
                              "angle": _to_float(getattr(p,"angle",0.0)),
                              "facecolor": _jsonable(p.get_facecolor()),
                              "edgecolor": _jsonable(p.get_edgecolor()),
                              "linewidth": _to_float(p.get_linewidth()),
                              "linestyle": p.get_linestyle(), "hatch": p.get_hatch(),
                              "alpha": _to_float(p.get_alpha()) if p.get_alpha() is not None else None,
                              "label": "", "visible": bool(p.get_visible()),
                              "zorder": _to_float(p.get_zorder()) if p.get_zorder() is not None else None}]
            })
        # ── Imágenes ─────────────────────────────────────────
        for im in getattr(ax, "images", []):
            try:
                arr = np.asarray(im.get_array())
                ax_props["images"].append({
                    "array":         _jsonable(arr),
                    "extent":        _jsonable(im.get_extent()) if hasattr(im,"get_extent") else None,
                    "origin":        getattr(im,"origin","upper"),
                    "interpolation": im.get_interpolation() if hasattr(im,"get_interpolation") else None,
                    "cmap":          im.get_cmap().name if getattr(im,"get_cmap",None) and im.get_cmap() else None,
                    "alpha":         _to_float(im.get_alpha()) if im.get_alpha() is not None else None,
                    "vmin":          _to_float(getattr(im.norm,"vmin",None)),
                    "vmax":          _to_float(getattr(im.norm,"vmax",None)),
                })
            except Exception:
                pass
        # ── Scatters y LineCollections ────────────────────────
        for coll in ax.collections:
            if isinstance(coll, mcoll.PathCollection):
                try:
                    offs = np.asarray(coll.get_offsets())
                    x = offs[:,0].tolist() if offs.size else []
                    y = offs[:,1].tolist() if offs.size else []
                    fc = coll.get_facecolors()
                    ec = coll.get_edgecolors()
                    lab = coll.get_label() if coll.get_label() and not str(coll.get_label()).startswith("_") else ""
                    ax_props["scatters"].append({
                        "x": _jsonable(x), "y": _jsonable(y),
                        "s":          _jsonable(coll.get_sizes().tolist()) if hasattr(coll,"get_sizes") else None,
                        "color":      _jsonable(fc.tolist()) if getattr(fc,"size",0) else None,
                        "edgecolors": _jsonable(ec.tolist()) if getattr(ec,"size",0) else None,
                        "alpha":      _to_float(coll.get_alpha()) if coll.get_alpha() is not None else None,
                        "label":      lab,
                        "cmap":       coll.get_cmap().name if getattr(coll,"get_cmap",None) and coll.get_cmap() else None,
                        "vmin":       _to_float(getattr(coll.norm,"vmin",None)) if getattr(coll,"norm",None) else None,
                        "vmax":       _to_float(getattr(coll.norm,"vmax",None)) if getattr(coll,"norm",None) else None,
                    })
                    for xi, yi in zip(x, y):
                        csv_rows.append([idx, "scatter", lab, xi, yi])
                except Exception:
                    pass
            elif isinstance(coll, mcoll.LineCollection):
                try:
                    ax_props["line_collections"].append({
                        "segments":   _jsonable(coll.get_segments()),
                        "colors":     _jsonable(coll.get_colors()),
                        "linewidths": _jsonable(coll.get_linewidths()),
                        "linestyles": _jsonable(coll.get_linestyles()),
                        "alpha":      _to_float(coll.get_alpha()) if coll.get_alpha() is not None else None,
                        "zorder":     _to_float(coll.get_zorder()) if coll.get_zorder() is not None else None,
                        "label":      coll.get_label() if coll.get_label() and not str(coll.get_label()).startswith("_") else "",
                    })
                except Exception:
                    pass
        # ── Textos / anotaciones (CON bbox) ──────────────────
        skip = {ax.title, ax.xaxis.label, ax.yaxis.label}
        for txt in ax.texts:
            if txt in skip:
                continue
            try:
                preset_name = _infer_text_preset_name(txt)
                ax_props["texts"].append({
                    "text":       txt.get_text(),
                    "x":          _to_float(txt.get_position()[0]),
                    "y":          _to_float(txt.get_position()[1]),
                    "transform":  "axes" if txt.get_transform() == ax.transAxes else "data",
                    "placement_mode": "preset" if preset_name else ("axes" if txt.get_transform() == ax.transAxes else "data"),
                    "preset_name": preset_name,
                    "fontsize":   _to_float(txt.get_fontsize()),
                    "fontweight": txt.get_fontweight(),
                    "fontstyle":  txt.get_fontstyle(),
                    "color":      _rgba(txt.get_color()),
                    "ha":         txt.get_ha(),
                    "va":         txt.get_va(),
                    "rotation":   _to_float(txt.get_rotation()),
                    "alpha":      _to_float(txt.get_alpha()) if txt.get_alpha() is not None else None,
                    "bbox":       _ser_annotation_bbox(txt),   # NUEVO: recuadro
                })
            except Exception:
                pass
        fig_props["axes"].append(ax_props)
    with open(base.with_suffix(".json"), "w", encoding="utf-8") as f:
        json.dump(_jsonable(fig_props), f, indent=4, ensure_ascii=False)
    with open(base.with_suffix(".csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(csv_header)
        w.writerows(csv_rows)
    if save_png:
        try:
            _save_figure_image(fig, base.with_suffix(".png"), dpi=300, prefs=_get_export_prefs(fig))
        except Exception:
            pass
    try:
        fig._fe_base_filename = str(base)
    except Exception:
        pass
    print(f"Guardado: {base}.json / .csv" + (" / .png" if save_png else ""))
# ─────────────────────────────────────────────────────────────
#  CARGAR FIGURA
# ─────────────────────────────────────────────────────────────
def _normalize_axd(axd: dict) -> dict:
    """Retrocompatibilidad: normaliza campos de JSONs viejos (v3/v15/v17/v20)."""
    axd = dict(axd or {})
    # title/xlabel/ylabel como string → convertir a dict
    for key in ("title","xlabel","ylabel"):
        v = axd.get(key)
        if isinstance(v, str):
            axd[key] = {"text": v, "fontsize": None, "fontweight": None,
                        "fontstyle": None, "color": None, "visible": True}
    # ticks: soporte formato viejo (xticks/yticks) y nuevo (ticks.x / ticks.y)
    if "ticks" not in axd:
        axd["ticks"] = {
            "x": axd.get("xticks", {}),
            "y": axd.get("yticks", {}),
        }
    # images / heatmaps alias
    if "images" not in axd and "heatmaps" in axd:
        axd["images"] = axd.get("heatmaps", [])
    # Limpiar leyendas vacías
    leg = axd.get("legend")
    if isinstance(leg, dict):
        entries = leg.get("entries") or []
        title   = leg.get("title") or ""
        if not entries and not title:
            axd["legend"] = None
    return axd
def load_figure(filename, show: bool = True):
    """Carga y reconstruye la figura desde un archivo JSON.
    Compatible con JSONs de versiones 3, 15, 17, 20 y 21.
    Parámetros
    ----------
    filename : str  nombre base (con o sin .json)
    show     : bool muestra la figura al terminar (default True)
    """
    print('gm')
    json_path = Path(filename)
    if json_path.suffix.lower() != ".json":
        json_path = json_path.with_suffix(".json")
    with open(json_path, "r", encoding="utf-8") as f:
        fig_props = json.load(f)
    axes_data = [_normalize_axd(axd) for axd in fig_props.get("axes", [])]
    # ── Crear figura ─────────────────────────────────────────
    fig = plt.figure(figsize=fig_props.get("size", (8,4)))
    if fig_props.get("dpi") is not None:
        try: fig.set_dpi(fig_props["dpi"])
        except Exception: pass
    if fig_props.get("figure_facecolor") is not None:
        try: fig.patch.set_facecolor(fig_props["figure_facecolor"])
        except Exception: pass
    # ── suptitle ─────────────────────────────────────────────
    st_spec = fig_props.get("suptitle_obj", fig_props.get("suptitle", ""))
    st_spec = _ser_text(st_spec) if isinstance(st_spec, str) else (st_spec or {})
    if st_spec.get("text"):
        try:
            fig.suptitle(st_spec["text"])
            _apply_text(getattr(fig, "_suptitle", None), st_spec)
        except Exception:
            pass
    # ── Crear ejes ───────────────────────────────────────────
    positions = [axd.get("position") for axd in axes_data]
    le = fig_props.get("layout_engine", {}) if isinstance(fig_props.get("layout_engine"), dict) else {}
    serialize_positions = bool(le.get("serialize_positions", True))
    apply_tight_layout_on_load = bool(le.get("apply_tight_layout_on_load", False))
    save_subplots_adjust_none = bool(le.get("save_subplots_adjust_none", False))
    fig._serialize_axes_positions = serialize_positions
    fig._apply_tight_layout_on_load = apply_tight_layout_on_load
    fig._save_subplots_adjust_none = save_subplots_adjust_none
    use_positions = serialize_positions and all(isinstance(p, (list,tuple)) and len(p) == 4 for p in positions)
    axes = []
    if use_positions:
        for pos in positions:
            axes.append(fig.add_axes(pos))
    else:
        nrows, ncols = fig_props.get("subplot_layout", (1, max(1, len(axes_data))))
        try: nrows, ncols = int(nrows), int(ncols)
        except Exception: nrows, ncols = 1, max(1, len(axes_data))
        sub  = fig.subplots(nrows, ncols)
        axes = np.atleast_1d(sub).ravel().tolist()
    for i, axd in enumerate(axes_data):
        ax = axes[i]
        # Escala antes de trazar
        for fn, key in [(ax.set_xscale,"xscale"),(ax.set_yscale,"yscale")]:
            if axd.get(key):
                try: fn(axd[key])
                except Exception: pass
        # Labels y título
        _apply_text(ax.title,       axd.get("title",{}))
        _apply_text(ax.xaxis.label, axd.get("xlabel",{}))
        _apply_text(ax.yaxis.label, axd.get("ylabel",{}))
        # Límites
        if axd.get("xlim") is not None:
            ax.set_xlim(axd["xlim"])
        if axd.get("ylim") is not None:
            ax.set_ylim(axd["ylim"])
        # Fondo, spines, grid
        if axd.get("facecolor") is not None:
            try: ax.set_facecolor(axd["facecolor"])
            except Exception: pass
        _apply_spines(ax, axd.get("spines", {}))
        _apply_grid(ax, axd.get("grid"))
        if axd.get("position") is not None:
            try: ax.set_position(axd["position"])
            except Exception: pass
        # Imágenes
        for img in axd.get("images",[]) or []:
            arr = np.asarray(img.get("array", img.get("data",[])))
            if arr.size == 0: continue
            kw = {k: img[k] for k in ("origin","interpolation","cmap","alpha")
                  if img.get(k) is not None}
            if img.get("extent") is not None: kw["extent"] = img["extent"]
            if img.get("vmin")   is not None: kw["vmin"]   = img["vmin"]
            if img.get("vmax")   is not None: kw["vmax"]   = img["vmax"]
            try: ax.imshow(arr, **kw)
            except Exception: pass
        # Líneas
        for line in axd.get("lines",[]) or []:
            try:
                ln, = ax.plot(line.get("x",[]), line.get("y",[]),
                              label=line.get("label",""),
                              color=line.get("color"),
                              linewidth=line.get("linewidth",1.5),
                              linestyle=line.get("linestyle","-"),
                              marker=line.get("marker",""),
                              markersize=line.get("markersize",6.0))
                for setter, key in [
                    (ln.set_markerfacecolor,"markerfacecolor"),
                    (ln.set_markeredgecolor,"markeredgecolor"),
                    (ln.set_markeredgewidth,"markeredgewidth"),
                    (ln.set_alpha,          "alpha"),
                    (ln.set_zorder,         "zorder"),
                ]:
                    if line.get(key) is not None:
                        try: setter(line[key])
                        except Exception: pass
                if line.get("visible") is not None:
                    ln.set_visible(bool(line["visible"]))
            except Exception:
                pass
        # Vlines / Hlines
        for vline in axd.get("vlines",[]) or []:
            try:
                ln = ax.axvline(x=vline.get("x",vline.get("value",0)),
                                color=vline.get("color","k"),
                                linewidth=vline.get("linewidth",1),
                                linestyle=vline.get("linestyle","-"),
                                alpha=vline.get("alpha",1.0))
                setattr(ln, "_fe_refline", "v")
                if vline.get("label"): ln.set_label(vline["label"])
                if vline.get("visible") is not None: ln.set_visible(bool(vline["visible"]))
            except Exception: pass
        for hline in axd.get("hlines",[]) or []:
            try:
                ln = ax.axhline(y=hline.get("y",hline.get("value",0)),
                                color=hline.get("color","k"),
                                linewidth=hline.get("linewidth",1),
                                linestyle=hline.get("linestyle","-"),
                                alpha=hline.get("alpha",1.0))
                setattr(ln, "_fe_refline", "h")
                if hline.get("label"): ln.set_label(hline["label"])
                if hline.get("visible") is not None: ln.set_visible(bool(hline["visible"]))
            except Exception: pass
        # Barras
        for cont in axd.get("bars",[]) or []:
            patches = []
            for bp in cont.get("patches",[]) or []:
                rect = Rectangle((bp.get("x",0),bp.get("y",0)),
                                  bp.get("width",0),bp.get("height",0),
                                  angle=bp.get("angle",0))
                _apply_rect_props(rect, bp)
                ax.add_patch(rect); patches.append(rect)
            if patches:
                try: ax.add_container(BarContainer(patches,errorbar=None,label=cont.get("label")))
                except Exception: pass
        # Scatters
        print('ry=')
        for scd in axd.get("scatters",[]) or []:
            x, y = scd.get("x",[]), scd.get("y",[])
            print('errer')
            if len(x) != len(y): continue
            print('errer')
            try:
                c_data = scd.get("color")
                cmap   = plt.get_cmap(scd["cmap"]) if scd.get("cmap") else None
                kw: dict = {}
                if scd.get("alpha") is not None: kw["alpha"] = scd["alpha"]
                if scd.get("label"):              kw["label"] = scd["label"]
                if scd.get("s")    is not None:   kw["s"]    = scd["s"]
                if c_data is not None:
                    c_arr = np.asarray(c_data)
                    if c_arr.ndim == 2 and c_arr.shape[1] in (3,4):
                        kw["c"] = c_data  # RGBA directo, sin cmap
                    else:
                        kw["c"] = c_data
                        if cmap             is not None: kw["cmap"] = cmap
                        if scd.get("vmin") is not None: kw["vmin"] = scd["vmin"]
                        if scd.get("vmax") is not None: kw["vmax"] = scd["vmax"]
                ax.scatter(x, y, **kw)
            except Exception as errer:
                print(errer)
                pass
        # LineCollections
        for lcd in axd.get("line_collections",[]) or []:
            try:
                coll = mcoll.LineCollection(lcd.get("segments"),
                                            colors=lcd.get("colors"),
                                            linewidths=lcd.get("linewidths"),
                                            linestyles=lcd.get("linestyles"))
                if lcd.get("alpha")  is not None: coll.set_alpha(lcd["alpha"])
                if lcd.get("zorder") is not None: coll.set_zorder(lcd["zorder"])
                if lcd.get("label"):               coll.set_label(lcd["label"])
                ax.add_collection(coll)
            except Exception:
                pass
        # Textos (CON bbox)
        for td in axd.get("texts",[]) or []:
            try:
                tr  = ax.transAxes if td.get("transform") == "axes" else ax.transData
                kw = {k: td[k] for k in ("fontsize","color","ha","va","rotation","alpha")
                      if td.get(k) is not None}
                t = ax.text(td.get("x",0), td.get("y",0), td.get("text",""),
                            transform=tr, **kw)
                if td.get("fontweight") is not None:
                    try: t.set_fontweight(td["fontweight"])
                    except Exception: pass
                if td.get("fontstyle") is not None:
                    try: t.set_fontstyle(td["fontstyle"])
                    except Exception: pass
                _apply_annotation_bbox(t, td.get("bbox"))   # NUEVO
            except Exception:
                pass
        # Metadata de leyenda compartida
        try:
            ax._fe_shared_legend = copy.deepcopy(axd.get("shared_legend"))
        except Exception:
            pass
        # Leyenda (al final, cuando el canvas está construido)
        _rebuild_legend(ax, axd.get("legend"))
        if ax.get_legend() is None:
            shared_leg = getattr(ax, "_fe_shared_legend", None)
            if isinstance(shared_leg, dict) and bool(shared_leg.get("show_by_default", False)):
                _rebuild_shared_legend(ax, shared_leg)
        # Ticks (al final para que afecten los artistas ya pintados)
        ticks = axd.get("ticks", {}) if isinstance(axd.get("ticks"), dict) else {}
        _apply_ticks(ax, ticks.get("x",{}), "x")
        _apply_ticks(ax, ticks.get("y",{}), "y")
    # ── subplots_adjust (DESPUÉS de crear ejes y artistas) ───
    # Si los ejes se crearon con fig.add_axes(), subplots_adjust no tiene efecto,
    # lo que es correcto porque sus posiciones ya están codificadas.
    adj = fig_props.get("subplots_adjust")
    if adj and isinstance(adj, dict) and any(v is not None for v in adj.values()):
        try:
            fig.subplots_adjust(**{k: v for k, v in adj.items() if v is not None})
        except Exception:
            pass
    if apply_tight_layout_on_load and not use_positions:
        try:
            fig.tight_layout()
        except Exception:
            pass
    try:
        _set_export_prefs(fig, fig_props.get("export_prefs", {}))
    except Exception:
        pass
    try:
        fig._fe_base_filename = str(json_path.with_suffix(""))
    except Exception:
        pass
    if show:
        try:
            if _can_show_interactive(fig):
                plt.show(block=False)
                fig.canvas.draw()
                fig.canvas.flush_events()
                plt.pause(0.05)
        except Exception:
            try:
                if _can_show_interactive(fig):
                    plt.show()
            except Exception:
                pass
    return fig
# ─────────────────────────────────────────────────────────────
#  Helpers del editor interactivo
# ─────────────────────────────────────────────────────────────
def _prompt(msg: str, default="") -> str:
    v = input(f"  {msg} [{default}]: ").strip()
    return v if v else str(default)
def _prompt_float(msg: str, default: float = 0.0) -> float:
    v = input(f"  {msg} [{default}]: ").strip()
    if not v: return default
    try:    return float(v)
    except: print(f"  Valor inválido; se mantiene {default}"); return default
def _prompt_int(msg: str, default: int = 0) -> int:
    v = input(f"  {msg} [{default}]: ").strip()
    if not v: return int(default)
    try:    return int(v)
    except: print(f"  Valor inválido; se mantiene {default}"); return int(default)
def _prompt_bool(msg: str, default: bool = True) -> bool:
    d = "s" if default else "n"
    v = input(f"  {msg} (s/n) [{d}]: ").strip().lower()
    return default if not v else (v in ("s","si","sí","y","yes","1","true"))

def _can_show_interactive(fig=None) -> bool:
    """Devuelve True sólo si el backend/canvas parece interactivo.
    Evita warnings con Agg/PDF/SVG durante pruebas o uso batch.
    """
    try:
        import matplotlib
        backend = str(matplotlib.get_backend()).lower()
    except Exception:
        backend = ""
    noninteractive = {"agg", "pdf", "ps", "svg", "template", "cairo"}
    if backend in noninteractive:
        return False
    try:
        canvas = fig.canvas if fig is not None else None
        if canvas is not None and getattr(canvas, "manager", None) is None:
            return False
    except Exception:
        pass
    return True

def _refresh(fig, pause: float = 0.08, force_show: bool = True):
    """Refresca la ventana de Matplotlib de forma robusta para Spyder/Qt."""
    try:
        plt.ion()
    except Exception:
        pass
    try:
        if fig is not None:
            try:
                fig.canvas.manager.show()
            except Exception:
                pass
            try:
                fig.canvas.draw_idle()
            except Exception:
                pass
            try:
                fig.canvas.draw()
            except Exception:
                pass
            try:
                fig.canvas.flush_events()
            except Exception:
                pass
        if force_show and _can_show_interactive(fig):
            try:
                plt.show(block=False)
            except Exception:
                pass
        try:
            plt.pause(float(pause))
        except Exception:
            pass
    except Exception:
        try:
            plt.draw()
            plt.pause(float(pause))
        except Exception:
            pass

def _enable_interactive_mode_for_editor():
    """Activa ajustes seguros para edición interactiva en Spyder/Qt."""
    try:
        plt.ion()
    except Exception:
        pass
    return True
def _pick_axis(fig):
    axes = _data_axes(fig)
    if len(axes) == 1:
        return axes[0], 0
    print("\n  Subplots:")
    for i, ax in enumerate(axes):
        print(f"    {i}: título='{ax.get_title()}' | x='{ax.get_xlabel()}' | y='{ax.get_ylabel()}'")
    val = input("  Índice de subplot (Enter=actual): ").strip()
    try:
        idx = int(val)
        if 0 <= idx < len(axes):
            return axes[idx], idx
    except Exception: pass
    return axes[0], 0
def _recreate_legend(ax, leg, **overrides):
    """Recrea la leyenda preservando handles existentes. Evita el bug de ax.legend(loc=...)."""
    if leg is None: return None
    handles = []
    for attr in ("legend_handles","legendHandles"):
        h = getattr(leg, attr, None)
        if h is not None: handles = list(h); break
    if not handles:
        try: handles, _ = ax.get_legend_handles_labels()
        except Exception: handles = []
    labels  = [t.get_text() for t in leg.get_texts()]
    title   = leg.get_title().get_text() if leg.get_title() else ""
    loc_int = getattr(leg, "_loc", 1)
    loc_str = _LOC_INT_TO_STR.get(int(loc_int) if isinstance(loc_int,int) else 1, "best")
    loc     = overrides.pop("loc", loc_str)
    frameon = overrides.pop("frameon", leg.get_frame_on())
    try:
        new_leg = ax.legend(handles, labels, title=title, loc=loc, frameon=frameon, **overrides)
    except Exception:
        new_leg = ax.legend(handles, labels, title=title, loc=loc, frameon=frameon)
    if new_leg is None: return leg
    try:
        if leg.get_title(): new_leg.get_title().set_fontsize(leg.get_title().get_fontsize())
    except Exception: pass
    try:
        for ot, nt in zip(leg.get_texts(), new_leg.get_texts()):
            nt.set_fontsize(ot.get_fontsize())
    except Exception: pass
    try:
        old_fr = leg.get_frame(); new_fr = new_leg.get_frame()
        new_fr.set_alpha(old_fr.get_alpha())
        new_fr.set_facecolor(old_fr.get_facecolor())
        new_fr.set_edgecolor(old_fr.get_edgecolor())
    except Exception: pass
    return new_leg
def _list_reflines(ax) -> list:
    result = []
    for ln in ax.get_lines():
        kind = _is_refline(ax, ln)
        if kind in {"v","h"}:
            result.append((ln, kind))
    return result
# ─────────────────────────────────────────────────────────────
#  Sub-menús del editor
# ─────────────────────────────────────────────────────────────
def _menu_labels(ax, fig):
    """Editar texto + fuente de título, xlabel, ylabel."""
    objs = [
        ("título",  ax.title,       ax.set_title),
        ("X-label", ax.xaxis.label, ax.set_xlabel),
        ("Y-label", ax.yaxis.label, ax.set_ylabel),
    ]
    while True:
        print("\n  ── Título y Labels ──")
        for i,(name,obj,_) in enumerate(objs):
            print(f"  {i+1}. {name}: '{obj.get_text()}' fs={obj.get_fontsize():.0f} fw={obj.get_fontweight()}")
        print("  4. Volver")
        op = input("  Opción: ").strip()
        if op in ("1","2","3"):
            name, obj, setter = objs[int(op)-1]
            txt = _prompt(f"Nuevo {name}", obj.get_text())
            setter(txt)
            obj = (ax.title if op=="1" else ax.xaxis.label if op=="2" else ax.yaxis.label)
            fs  = input(f"  Fontsize [{obj.get_fontsize():.0f}]: ").strip()
            fw  = _prompt("Fontweight (normal/bold)", obj.get_fontweight())
            col = input("  Color (Enter=mantener): ").strip()
            if fs:
                try: obj.set_fontsize(float(fs))
                except Exception: pass
            try:   obj.set_fontweight(fw)
            except Exception: pass
            if col:
                try: obj.set_color(col)
                except Exception as e: print(f"  Error color: {e}")
            _refresh(fig)
        elif op == "4":
            break
        else:
            print("  Opción inválida.")
def _menu_limits_scales(ax, fig):
    while True:
        print(f"\n  ── Ejes: escala/límites ──")
        print(f"  Escala X: {ax.get_xscale()} | xlim: {[round(v,4) for v in ax.get_xlim()]}")
        print(f"  Escala Y: {ax.get_yscale()} | ylim: {[round(v,4) for v in ax.get_ylim()]}")
        print("  1. Escala X   2. Escala Y   3. xlim   4. ylim   5. Volver")
        op = input("  Opción: ").strip()
        if op == "1":
            sc = _prompt("Escala X (linear/log/symlog)", ax.get_xscale())
            try: ax.set_xscale(sc)
            except Exception as e: print(f"  Error: {e}")
        elif op == "2":
            sc = _prompt("Escala Y (linear/log/symlog)", ax.get_yscale())
            try: ax.set_yscale(sc)
            except Exception as e: print(f"  Error: {e}")
        elif op == "3":
            xl = ax.get_xlim()
            ax.set_xlim(_prompt_float("xlim inferior", xl[0]),
                        _prompt_float("xlim superior", xl[1]))
        elif op == "4":
            yl = ax.get_ylim()
            ax.set_ylim(_prompt_float("ylim inferior", yl[0]),
                        _prompt_float("ylim superior", yl[1]))
        elif op == "5":
            break
        else:
            print("  Opción inválida.")
        _refresh(fig)
def _menu_ticks(ax, fig):
    while True:
        xt = ax.xaxis.get_ticklabels()
        yt = ax.yaxis.get_ticklabels()
        print("\n  ── Ticks ──")
        print(f"  X: fs={xt[0].get_fontsize():.0f} rot={xt[0].get_rotation():.0f}°" if xt else "  X: (sin ticks)")
        print(f"  Y: fs={yt[0].get_fontsize():.0f} rot={yt[0].get_rotation():.0f}°" if yt else "  Y: (sin ticks)")
        print("  1. Editar X   2. Editar Y   3. Dirección (in/out/inout)   4. Volver")
        op = input("  Opción: ").strip()
        if op in ("1","2"):
            axis = "x" if op == "1" else "y"
            tls = ax.get_xticklabels() if axis == "x" else ax.get_yticklabels()
            cur_fs  = tls[0].get_fontsize() if tls else 10
            cur_rot = tls[0].get_rotation() if tls else 0
            fs  = input(f"  Fontsize [{cur_fs:.0f}] (Enter=mantener): ").strip()
            rot = input(f"  Rotación [{cur_rot:.0f}°] (Enter=mantener): ").strip()
            col = input("  Color (Enter=mantener): ").strip()
            for t in tls:
                if fs:
                    try: t.set_fontsize(float(fs))
                    except Exception: pass
                if rot:
                    try: t.set_rotation(float(rot))
                    except Exception: pass
                if col:
                    try: t.set_color(col)
                    except Exception: pass
        elif op == "3":
            d = _prompt("Dirección (in/out/inout)", "out")
            try: ax.tick_params(which="both", direction=d)
            except Exception as e: print(f"  Error: {e}")
        elif op == "4":
            break
        else:
            print("  Opción inválida.")
        _refresh(fig)

def _menu_legend(ax, fig):
    """Editor de leyenda por subplot.
    Ahora también puede materializar una leyenda "compartida" heredada desde
    otro subplot, sin perder esa metadata al guardar el panel individual.
    """
    while True:
        leg = ax.get_legend()
        shared = getattr(ax, "_fe_shared_legend", None)
        shared_state = "sí" if isinstance(shared, dict) else "no"
        print(f"\n  ── Leyenda ── ({'presente' if leg else 'no presente'} | metadata compartida: {shared_state})")
        print("  1. Crear/mostrar desde labels del eje")
        print("  2. Quitar leyenda visible")
        print("  3. Título y fontsize")
        print("  4. Posición (loc)")
        print("  5. Marco")
        print("  6. Fontsize etiquetas")
        print("  7. Usar / configurar leyenda compartida")
        print("  8. Volver")
        op = input("  Opción: ").strip()
        if op == "1":
            handles, labels = ax.get_legend_handles_labels()
            pairs = [(h, l) for h, l in zip(handles, labels) if l and not str(l).startswith("_")]
            if not pairs:
                print("  No hay handles/labels válidos.")
                continue
            h_list, l_list = zip(*pairs)
            loc = _prompt("loc (best/upper right/upper left/...)", "best")
            ax.legend(list(h_list), list(l_list), loc=loc)
        elif op == "2":
            if leg is None:
                print("  No hay leyenda visible.")
                continue
            try:
                leg.remove()
            except Exception:
                pass
        elif op == "3":
            if leg is None:
                print("  No hay leyenda visible.")
                continue
            cur_title = leg.get_title().get_text() if leg.get_title() else ""
            t = _prompt("Título (-- para borrar)", cur_title)
            if t == "--":
                t = ""
            try:
                leg.set_title(t)
            except Exception:
                pass
            cur_fs = leg.get_title().get_fontsize() if leg.get_title() else 10
            fs = input(f"  Fontsize título [{cur_fs:.0f}]: ").strip()
            if fs:
                try:
                    leg.get_title().set_fontsize(float(fs))
                except Exception:
                    pass
        elif op == "4":
            if leg is None:
                print("  No hay leyenda visible.")
                continue
            print("  Locs: best, upper right, upper left, lower left, lower right,")
            print("        right, center left, center right, lower center, upper center, center")
            loc_raw = getattr(leg, "_loc", "best")
            if isinstance(loc_raw, int):
                cur_loc = _LOC_INT_TO_STR.get(int(loc_raw), "best")
            else:
                cur_loc = str(loc_raw)
            new_loc = _prompt("Nueva posición", cur_loc)
            _recreate_legend(ax, leg, loc=new_loc)
        elif op == "5":
            if leg is None:
                print("  No hay leyenda visible.")
                continue
            frame = leg.get_frame()
            on = _prompt_bool("Mostrar marco", leg.get_frame_on())
            fc = input("  Color fondo marco (Enter=mantener): ").strip()
            ec = input("  Color borde marco (Enter=mantener): ").strip()
            al = input(f"  Alpha [{frame.get_alpha()}] (Enter=mantener): ").strip()
            new_leg = _recreate_legend(ax, leg, frameon=on)
            if new_leg is not None:
                try:
                    fr = new_leg.get_frame()
                    if fc:
                        fr.set_facecolor(fc)
                    if ec:
                        fr.set_edgecolor(ec)
                    if al:
                        fr.set_alpha(float(al))
                except Exception:
                    pass
        elif op == "6":
            if leg is None:
                print("  No hay leyenda visible.")
                continue
            texts = leg.get_texts()
            cur = texts[0].get_fontsize() if texts else 10
            fs = input(f"  Fontsize etiquetas [{cur:.0f}]: ").strip()
            if fs:
                try:
                    new_fs = float(fs)
                    for t in texts:
                        t.set_fontsize(new_fs)
                except Exception:
                    pass
        elif op == "7":
            shared = getattr(ax, "_fe_shared_legend", None)
            if not isinstance(shared, dict):
                print("  Este subplot no tiene metadata de leyenda compartida.")
                continue
            while True:
                src_idx = shared.get("source_axis_index", "?")
                title = ""
                try:
                    title = (((shared.get("legend") or {}).get("title")) or "")
                except Exception:
                    title = ""
                nent = len(((shared.get("legend") or {}).get("entries")) or [])
                print(f"\n    ── Leyenda compartida ── origen axis={src_idx}, entradas={nent}, título='{title}'")
                print(f"    show_by_default = {bool(shared.get('show_by_default', False))}")
                print("    1. Mostrar ahora en este subplot")
                print("    2. Marcar para mostrar por defecto al cargar")
                print("    3. Marcar para mantener oculta por defecto")
                print("    4. Eliminar metadata compartida")
                print("    5. Volver")
                op2 = input("    Opción: ").strip()
                if op2 == "1":
                    _rebuild_shared_legend(ax, shared)
                elif op2 == "2":
                    shared["show_by_default"] = True
                    try:
                        ax._fe_shared_legend = copy.deepcopy(shared)
                    except Exception:
                        pass
                    if ax.get_legend() is None:
                        _rebuild_shared_legend(ax, shared)
                elif op2 == "3":
                    shared["show_by_default"] = False
                    try:
                        ax._fe_shared_legend = copy.deepcopy(shared)
                    except Exception:
                        pass
                elif op2 == "4":
                    try:
                        ax._fe_shared_legend = None
                    except Exception:
                        pass
                    shared = None
                    print("    Metadata eliminada.")
                    break
                elif op2 == "5":
                    break
                else:
                    print("    Opción inválida.")
                _refresh(fig)
        elif op == "8":
            break
        else:
            print("  Opción inválida.")
        _refresh(fig)

def _menu_reflines(ax, fig):

    """Agregar/editar/eliminar líneas de referencia verticales y horizontales."""
    while True:
        refs = _list_reflines(ax)
        print(f"\n  ── Líneas de referencia ── ({len(refs)} total)")
        for i,(ln,kind) in enumerate(refs):
            pos = list(ln.get_xdata())[0] if kind == "v" else list(ln.get_ydata())[0]
            print(f"    {i}: {'▕' if kind=='v' else '─'} pos={pos:.5g} "
                  f"color={ln.get_color()} ls='{ln.get_linestyle()}' lw={ln.get_linewidth():.1f}")
        print("  1. Agregar vertical   2. Agregar horizontal")
        print("  3. Editar una         4. Eliminar una   5. Eliminar todas   6. Volver")
        op = input("  Opción: ").strip()
        def ask_style(ref=None):
            return {
                "color":     _prompt("color",    "k"   if not ref else ref.get_color()),
                "linestyle": _prompt("linestyle (- -- -. :)", "--" if not ref else ref.get_linestyle()),
                "linewidth": _prompt_float("linewidth", 1.5 if not ref else ref.get_linewidth()),
                "alpha":     _prompt_float("alpha",     1.0 if not ref else (ref.get_alpha() or 1.0)),
                "label":     _prompt("label",    ""    if not ref else (ref.get_label() if not str(ref.get_label()).startswith("_") else "")),
            }
        if op == "1":
            x  = _prompt_float("x", 0.0)
            st = ask_style()
            ln = ax.axvline(x=x,color=st["color"],linestyle=st["linestyle"],
                            linewidth=st["linewidth"],alpha=st["alpha"])
            setattr(ln,"_fe_refline","v")
            if st["label"]: ln.set_label(st["label"])
        elif op == "2":
            y  = _prompt_float("y", 0.0)
            st = ask_style()
            ln = ax.axhline(y=y,color=st["color"],linestyle=st["linestyle"],
                            linewidth=st["linewidth"],alpha=st["alpha"])
            setattr(ln,"_fe_refline","h")
            if st["label"]: ln.set_label(st["label"])
        elif op == "3":
            if not refs: print("  No hay líneas."); continue
            sel = input("  Índice: ").strip()
            try:
                ln, kind = refs[int(sel)]
            except Exception: print("  Índice inválido."); continue
            if kind == "v":
                x  = _prompt_float("Nueva x", list(ln.get_xdata())[0])
                ln.set_xdata([x,x])
            else:
                y  = _prompt_float("Nueva y", list(ln.get_ydata())[0])
                ln.set_ydata([y,y])
            st = ask_style(ref=ln)
            try: ln.set_color(st["color"]); ln.set_linestyle(st["linestyle"])
            except Exception: pass
            ln.set_linewidth(st["linewidth"]); ln.set_alpha(st["alpha"])
            if st["label"]: ln.set_label(st["label"])
        elif op == "4":
            if not refs: print("  No hay líneas."); continue
            sel = input("  Índice: ").strip()
            try:
                ln, _ = refs[int(sel)]
                ln.remove()
            except Exception: print("  Índice inválido.")
        elif op == "5":
            for ln, _ in refs:
                try: ln.remove()
                except Exception: pass
        elif op == "6":
            break
        else:
            print("  Opción inválida.")
        _refresh(fig)
def _menu_grid_spines_bg(ax, fig):
    while True:
        print("\n  ── Grid / Spines / Fondo ──")
        print("  1. Editar grid   2. Editar spines   3. Fondo del subplot   4. Volver")
        op = input("  Opción: ").strip()
        if op == "1":
            g = _ser_grid(ax)
            vis = _prompt_bool("Mostrar grid", g.get("visible", False))
            col = _prompt("Color", g.get("color") or "0.8")
            ls  = _prompt("Linestyle (- -- -. :)", g.get("linestyle") or "--")
            lw  = _prompt_float("Linewidth", g.get("linewidth") or 0.8)
            al  = _prompt_float("Alpha", g.get("alpha") or 1.0)
            ax.grid(vis, color=col, linestyle=ls, linewidth=lw, alpha=al)
        elif op == "2":
            name = _prompt("Spine (left/right/top/bottom/all)", "all")
            targets = list(ax.spines.keys()) if name == "all" else [name]
            vis = _prompt_bool("Visible", True)
            col = _prompt("Color", "black")
            lw  = _prompt_float("Linewidth", 1.0)
            for nm in targets:
                sp = ax.spines.get(nm)
                if sp:
                    sp.set_visible(vis); sp.set_edgecolor(col); sp.set_linewidth(lw)
        elif op == "3":
            col = input(f"  Color fondo [{ax.get_facecolor()}] (Enter=mantener): ").strip()
            if col:
                try: ax.set_facecolor(col)
                except Exception as e: print(f"  Error: {e}")
        elif op == "4":
            break
        else:
            print("  Opción inválida.")
        _refresh(fig)
def _menu_lines(ax, fig):
    """Editar trazas de datos (excluye vlines/hlines)."""
    ref_set = {id(l) for l, _ in _list_reflines(ax)}
    lines   = [l for l in ax.get_lines() if id(l) not in ref_set]
    if not lines:
        print("  No hay trazas de datos en este subplot.")
        return
    while True:
        print("\n  ── Trazas ──")
        for i,l in enumerate(lines):
            print(f"  {i}: '{l.get_label()}' color={l.get_color()} "
                  f"lw={l.get_linewidth():.1f} mk='{l.get_marker()}' "
                  f"ms={l.get_markersize():.1f} mew={l.get_markeredgewidth():.1f} α={l.get_alpha()}")
        print(f"  {len(lines)}. Volver")
        sel = input("  Seleccione índice: ").strip()
        if sel == str(len(lines)) or sel.lower() == "v" or sel == "":
            break
        try:
            line = lines[int(sel)]
        except Exception:
            print("  Índice inválido."); continue
        for msg, getter, setter, is_num in [
            ("color",          line.get_color,          line.set_color,          False),
            ("linewidth",      line.get_linewidth,       line.set_linewidth,      True),
            ("linestyle",      line.get_linestyle,       line.set_linestyle,      False),
            ("marker",         line.get_marker,          line.set_marker,         False),
            ("markersize",     line.get_markersize,      line.set_markersize,     True),
            ("markeredgewidth",line.get_markeredgewidth, line.set_markeredgewidth,True),
        ]:
            curr = getter()
            val  = input(f"  {msg} [{curr}] (Enter=mantener): ").strip()
            if val:
                try: setter(float(val) if is_num else val)
                except Exception as e: print(f"  Error: {e}")
        alp = input(f"  alpha [{line.get_alpha()}] (Enter=mantener): ").strip()
        if alp:
            try: line.set_alpha(float(alp))
            except Exception: pass
        lab = input(f"  label ['{line.get_label()}'] (Enter=mantener): ").strip()
        if lab: line.set_label(lab)
        vis = input(f"  visible (s/n) [{'s' if line.get_visible() else 'n'}] (Enter=mantener): ").strip().lower()
        if vis: line.set_visible(vis in ("s","si","y","yes","1","true"))
        _refresh(fig)
def _menu_bars(ax, fig):
    containers = [c for c in getattr(ax,"containers",[]) if isinstance(c,BarContainer)]
    if not containers:
        print("  No hay barras en este subplot."); return
    print("  Contenedores de barras:")
    for i,c in enumerate(containers):
        print(f"    {i}: label='{c.get_label() if hasattr(c,'get_label') else ''}', n_barras={len(getattr(c,'patches',[]))}")
    s = input("  Índice (Enter=cancelar): ").strip()
    if not s: return
    try:
        cont = containers[int(s)]
    except Exception:
        print("  Índice inválido."); return
    patches = list(getattr(cont,"patches",[]))
    if not patches: print("  Contenedor sin patches."); return
    mode = _prompt("Editar una barra (1) o todas (2)", "2")
    if mode == "1":
        s2 = input(f"  Índice de barra (0..{len(patches)-1}): ").strip()
        try: targets = [patches[int(s2)]]
        except Exception: print("  Inválido."); return
    else:
        targets = patches
    ref = targets[0]
    fc  = _prompt("Facecolor", ref.get_facecolor())
    ec  = _prompt("Edgecolor", ref.get_edgecolor())
    lw  = _prompt_float("Linewidth", ref.get_linewidth())
    ls  = _prompt("Linestyle", ref.get_linestyle())
    al  = _prompt_float("Alpha", ref.get_alpha() if ref.get_alpha() is not None else 1.0)
    ht  = _prompt("Hatch", ref.get_hatch() or "")
    for p in targets:
        try: p.set_facecolor(fc)
        except Exception: pass
        try: p.set_edgecolor(ec)
        except Exception: pass
        try: p.set_linewidth(lw)
        except Exception: pass
        try: p.set_linestyle(ls)
        except Exception: pass
        try: p.set_alpha(al)
        except Exception: pass
        try: p.set_hatch(ht)
        except Exception: pass
    _refresh(fig)
def _menu_scatters(ax, fig):
    scatters = [c for c in ax.collections if isinstance(c, mcoll.PathCollection)]
    if not scatters:
        print("  No hay scatters."); return
    print("  Scatters:")
    for i,sc in enumerate(scatters):
        print(f"    {i}: label='{sc.get_label()}' n={len(sc.get_offsets())} α={sc.get_alpha()}")
    s = input("  Índice (Enter=cancelar): ").strip()
    if not s: return
    try: sc = scatters[int(s)]
    except Exception: print("  Inválido."); return
    fc   = sc.get_facecolors()
    cur_fc = fc[0].tolist() if getattr(fc,"size",0) else "C0"
    face = _prompt("Facecolor", cur_fc)
    alpha= _prompt_float("Alpha", sc.get_alpha() or 1.0)
    sizes= sc.get_sizes()
    sz   = _prompt_float("Tamaño s", float(sizes[0]) if len(sizes) else 20.0)
    try: sc.set_facecolor(face)
    except Exception: print("  No pude aplicar facecolor.")
    try: sc.set_alpha(alpha)
    except Exception: pass
    try: sc.set_sizes(np.full(len(sc.get_offsets()), sz))
    except Exception: pass
    _refresh(fig)
def _infer_text_preset_name(txt, tol: float = 0.035) -> str | None:
    """Intenta inferir si el texto coincide con una posición estándar en coords Axes."""
    try:
        if txt.get_transform() != txt.axes.transAxes:
            return None
        x, y = txt.get_position()
        ha, va = txt.get_ha(), txt.get_va()
        for name, (px, py, pha, pva) in _TEXT_PRESET_ANCHORS.items():
            if abs(float(x) - px) <= tol and abs(float(y) - py) <= tol and ha == pha and va == pva:
                return name
    except Exception:
        return None
    return None
def _prompt_text_placement(existing=None):
    """
    Retorna dict con placement_mode/preset_name/x/y/transform/ha/va.
    existing: dict opcional con claves x,y,transform,ha,va,preset_name
    """
    cur = existing or {}
    cur_transform = cur.get("transform", "axes")
    cur_preset = cur.get("preset_name") or None
    cur_x = cur.get("x", 0.5)
    cur_y = cur.get("y", 0.5)
    cur_ha = cur.get("ha", "left")
    cur_va = cur.get("va", "baseline")
    if cur_preset:
        default_mode = "preset"
    elif str(cur_transform).startswith("a"):
        default_mode = "axes"
    else:
        default_mode = "data"
    print("  Posición del texto:")
    print("    - preset : posiciones estándar en coordenadas Axes")
    print("    - axes   : coordenadas manuales normalizadas (0..1)")
    print("    - data   : coordenadas de datos")
    mode = _prompt("Modo (preset/axes/data)", default_mode).strip().lower()
    if mode.startswith("p"):
        print("  Presets disponibles: " + ", ".join(_TEXT_PRESET_ANCHORS))
        preset = _prompt("Preset", cur_preset or "upper left")
        preset = preset if preset in _TEXT_PRESET_ANCHORS else "upper left"
        x, y, ha, va = _TEXT_PRESET_ANCHORS[preset]
        return {
            "placement_mode": "preset",
            "preset_name": preset,
            "x": x,
            "y": y,
            "transform": "axes",
            "ha": ha,
            "va": va,
        }
    x = _prompt_float("x", cur_x)
    y = _prompt_float("y", cur_y)
    if mode.startswith("a"):
        ha = _prompt("Alineación H (left/center/right)", cur_ha if cur_transform == "axes" else "left")
        va = _prompt("Alineación V (top/center/bottom/baseline)", cur_va if cur_transform == "axes" else "baseline")
        return {
            "placement_mode": "axes",
            "preset_name": None,
            "x": x,
            "y": y,
            "transform": "axes",
            "ha": ha,
            "va": va,
        }
    ha = _prompt("Alineación H (left/center/right)", cur_ha)
    va = _prompt("Alineación V (top/center/bottom/baseline)", cur_va)
    return {
        "placement_mode": "data",
        "preset_name": None,
        "x": x,
        "y": y,
        "transform": "data",
        "ha": ha,
        "va": va,
    }
def _prompt_bbox(existing_bbox: dict | None = None) -> dict | None:
    """Pide al usuario si quiere recuadro y sus propiedades. Retorna dict o None."""
    if existing_bbox is not None:
        print(f"  Recuadro actual: boxstyle={existing_bbox.get('boxstyle','round')} "
              f"fc={existing_bbox.get('facecolor')} ec={existing_bbox.get('edgecolor')}")
        en = _prompt_bool("¿Mantener/editar recuadro", True)
    else:
        en = _prompt_bool("¿Agregar recuadro al texto", False)
    if not en:
        return None
    cur = existing_bbox or {}
    print("  Estilos disponibles: round, square, round4, roundtooth, sawtooth")
    bs  = _prompt("Boxstyle",  cur.get("boxstyle","round"))
    pad = _prompt_float("Padding",    cur.get("pad",0.3))
    fc  = _prompt("Facecolor",  cur.get("facecolor","lightyellow"))
    ec  = _prompt("Edgecolor",  cur.get("edgecolor","black"))
    lw  = _prompt_float("Linewidth", cur.get("linewidth",1.0))
    al  = _prompt_float("Alpha",     cur.get("alpha", 1.0))
    return {"boxstyle": bs, "pad": pad, "facecolor": fc, "edgecolor": ec,
            "linewidth": lw, "alpha": al}
def _menu_texts(ax, fig):
    """
    Editor de textos/anotaciones.
    Permite: agregar, editar (texto + fuente + posición estándar/custom + recuadro), eliminar.
    """
    skip = {ax.title, ax.xaxis.label, ax.yaxis.label}
    while True:
        texts = [t for t in ax.texts if t not in skip and t is not None]
        print(f"\n  ── Textos / Anotaciones ({len(texts)}) ──")
        for i, t in enumerate(texts):
            pos = t.get_position()
            tr = "axes" if t.get_transform() == ax.transAxes else "data"
            has_bbox = _ser_annotation_bbox(t) is not None
            preset = _infer_text_preset_name(t)
            preset_txt = f" preset={preset}" if preset else ""
            print(f"  {i}: '{t.get_text()[:30]}' @ ({pos[0]:.3f},{pos[1]:.3f}) "
                  f"[{tr}] fs={t.get_fontsize():.0f}{preset_txt} "
                  f"{'[recuadro]' if has_bbox else ''}")
        print("  a. Agregar   e. Editar   d. Eliminar   v. Volver")
        op = input("  Opción: ").strip().lower()
        if op == "a":
            txt_str = _prompt("Texto", "anotación")
            placement = _prompt_text_placement({"transform": "axes", "x": 0.5, "y": 0.5, "preset_name": "upper left"})
            tr = ax.transAxes if placement["transform"] == "axes" else ax.transData
            fs = _prompt_float("Fontsize", 10)
            fw = _prompt("Fontweight (normal/bold)", "normal")
            fs_sty = _prompt("Fontstyle (normal/italic)", "normal")
            col = _prompt("Color", "black")
            rot = _prompt_float("Rotación °", 0.0)
            alpha = _prompt_float("Alpha", 1.0)
            bbox_spec = _prompt_bbox(None)
            t = ax.text(placement["x"], placement["y"], txt_str, transform=tr, fontsize=fs,
                        color=col, ha=placement["ha"], va=placement["va"], rotation=rot)
            try: t.set_fontweight(fw)
            except Exception: pass
            try: t.set_fontstyle(fs_sty)
            except Exception: pass
            try: t.set_alpha(alpha)
            except Exception: pass
            _apply_annotation_bbox(t, bbox_spec)
        elif op == "e":
            if not texts:
                print("  No hay textos.")
                continue
            sel = input("  Índice: ").strip()
            try:
                t = texts[int(sel)]
            except Exception:
                print("  Inválido.")
                continue
            t.set_text(_prompt("Texto", t.get_text()))
            placement_existing = {
                "x": t.get_position()[0],
                "y": t.get_position()[1],
                "transform": "axes" if t.get_transform() == ax.transAxes else "data",
                "ha": t.get_ha(),
                "va": t.get_va(),
                "preset_name": _infer_text_preset_name(t),
            }
            placement = _prompt_text_placement(placement_existing)
            t.set_position((placement["x"], placement["y"]))
            try: t.set_transform(ax.transAxes if placement["transform"] == "axes" else ax.transData)
            except Exception: pass
            try: t.set_ha(placement["ha"])
            except Exception: pass
            try: t.set_va(placement["va"])
            except Exception: pass
            fs = input(f"  Fontsize [{t.get_fontsize():.0f}] (Enter=mantener): ").strip()
            fw = input(f"  Fontweight [{t.get_fontweight()}] (Enter=mantener): ").strip()
            fst = input(f"  Fontstyle [{t.get_fontstyle()}] (Enter=mantener): ").strip()
            col = input("  Color (Enter=mantener): ").strip()
            rot = input(f"  Rotación [{t.get_rotation():.0f}°] (Enter=mantener): ").strip()
            alp = input(f"  Alpha [{t.get_alpha()}] (Enter=mantener): ").strip()
            if fs:
                try: t.set_fontsize(float(fs))
                except Exception: pass
            if fw:
                try: t.set_fontweight(fw)
                except Exception: pass
            if fst:
                try: t.set_fontstyle(fst)
                except Exception: pass
            if col:
                try: t.set_color(col)
                except Exception: pass
            if rot:
                try: t.set_rotation(float(rot))
                except Exception: pass
            if alp:
                try: t.set_alpha(float(alp))
                except Exception: pass
            cur_bbox = _ser_annotation_bbox(t)
            bbox_spec = _prompt_bbox(cur_bbox)
            _apply_annotation_bbox(t, bbox_spec)
        elif op == "d":
            if not texts:
                print("  No hay textos.")
                continue
            sel = input("  Índice (o 'all'): ").strip()
            if sel.lower() == "all":
                targets = texts
            else:
                try:
                    targets = [texts[int(sel)]]
                except Exception:
                    print("  Inválido.")
                    continue
            for t in targets:
                try: t.remove()
                except Exception: pass
        elif op == "v":
            break
        else:
            print("  Opción inválida.")
        _refresh(fig)
def _boxed_menu(title, lines, width=72, indent="  "):
    """Render a simple ASCII boxed menu with aligned vertical bars."""
    clean = []
    for line in lines:
        s = str(line).replace("\n", " ").replace("\r", " ").strip()
        if len(s) > width - 4:
            s = s[:width - 7] + "..."
        clean.append(s)
    inner = max([len(title)] + [len(s) for s in clean] + [0])
    inner = max(inner, min(width - 4, 24))
    top = indent + "+-" + "-" * inner + "-+"
    print(top)
    print(f"{indent}| {title.ljust(inner)} |")
    print(indent + "+-" + "-" * inner + "-+")
    for s in clean:
        print(f"{indent}| {s.ljust(inner)} |")
    print(top)
def _compute_normalized_positions_via_tight_clone(fig):
    """Clona temporalmente la figura en modo subplots y devuelve posiciones de axes tras tight_layout().
    Se usa para convertir figuras con add_axes/position explícita a un layout normalizable.
    """
    data_axes = _data_axes(fig)
    if not data_axes:
        return []
    with tempfile.TemporaryDirectory(prefix="figedit_norm_") as td:
        base = Path(td) / "probe"
        save_figure_data(fig, str(base), save_png=False)
        jpath = base.with_suffix('.json')
        with open(jpath, 'r', encoding='utf-8') as f:
            props = json.load(f)
        # Forzar reconstrucción por subplots y sin ajustes manuales persistentes
        props['layout_engine'] = {
            'serialize_positions': False,
            'apply_tight_layout_on_load': False,
            'save_subplots_adjust_none': True,
        }
        props['subplots_adjust'] = None
        for axd in props.get('axes', []):
            axd['position'] = None
        with open(jpath, 'w', encoding='utf-8') as f:
            json.dump(props, f, ensure_ascii=False, indent=2)
        tfig = load_figure(str(jpath), show=False)
        try:
            tfig.tight_layout()
        except Exception:
            pass
        try:
            tfig.canvas.draw()
        except Exception:
            pass
        pos = [list(map(float, ax.get_position().bounds)) for ax in _data_axes(tfig)]
        try:
            plt.close(tfig)
        except Exception:
            pass
        return pos

def _load_reference_layout_from_json(path):
    path = Path(path)
    if path.suffix.lower() != ".json":
        path = path.with_suffix('.json')
    with open(path, 'r', encoding='utf-8') as f:
        ref = json.load(f)
    return ref
def _apply_reference_layout(fig, ref_props, copy_figsize=True, copy_subplotpars=True,
                            copy_axes_positions=True, copy_export_prefs=True,
                            convert_to_normalizable_when_reference_has_no_positions=True):
    axes = _data_axes(fig)
    ref_axes = [_normalize_axd(axd) for axd in ref_props.get('axes', [])]
    changes = []
    ref_positions = [axd.get('position') for axd in ref_axes]
    ref_has_positions = bool(ref_axes) and all(isinstance(pos, (list, tuple)) and len(pos) == 4 for pos in ref_positions)
    if copy_figsize and ref_props.get('size') is not None:
        try:
            size = ref_props.get('size')
            fig.set_size_inches(float(size[0]), float(size[1]), forward=True)
            changes.append('figsize')
        except Exception:
            pass
    if copy_subplotpars:
        adj = ref_props.get('subplots_adjust', None)
        try:
            if isinstance(adj, dict) and any(v is not None for v in adj.values()):
                valid = {k: float(adj[k]) for k in ('left','right','top','bottom','wspace','hspace') if k in adj and adj[k] is not None}
                if valid:
                    fig.subplots_adjust(**valid)
                    fig._save_subplots_adjust_none = False
                    changes.append('subplotpars')
            elif adj is None and convert_to_normalizable_when_reference_has_no_positions:
                fig._save_subplots_adjust_none = True
                changes.append('subplotpars_cleared')
        except Exception:
            pass
    if copy_axes_positions and len(ref_axes) == len(axes):
        if ref_has_positions:
            for ax, axd in zip(axes, ref_axes):
                try:
                    ax.set_position(axd['position'])
                except Exception:
                    pass
            fig._serialize_axes_positions = True
            fig._apply_tight_layout_on_load = False
            fig._save_subplots_adjust_none = False if ref_props.get('subplots_adjust') is not None else getattr(fig, '_save_subplots_adjust_none', False)
            changes.append('axes_positions')
        elif convert_to_normalizable_when_reference_has_no_positions:
            try:
                new_positions = _compute_normalized_positions_via_tight_clone(fig)
            except Exception:
                new_positions = []
            if len(new_positions) == len(axes):
                for ax, pos in zip(axes, new_positions):
                    try:
                        ax.set_position(pos)
                    except Exception:
                        pass
                changes.append('axes_positions_tight_clone')
            fig._serialize_axes_positions = False
            fig._apply_tight_layout_on_load = True
            fig._save_subplots_adjust_none = True
            changes.append('layout_normalizable')
    if copy_export_prefs and ref_props.get('export_prefs'):
        try:
            _set_export_prefs(fig, ref_props.get('export_prefs', {}))
            changes.append('export_prefs')
        except Exception:
            pass
    try:
        fig.canvas.draw_idle()
    except Exception:
        pass
    return changes, len(axes), len(ref_axes), ref_has_positions


def _style_only_text_spec(spec):
    d = _ser_text(spec) if not isinstance(spec, dict) else dict(spec)
    d.pop("text", None)
    return _jsonable(d)

def _legend_style_only_spec(leginfo):
    if not isinstance(leginfo, dict):
        return None
    return {
        "title": leginfo.get("title", "") or "",
        "style": _jsonable(leginfo.get("style", {}) or {}),
    }

def _json_eq(a, b) -> bool:
    try:
        return json.dumps(_jsonable(a), sort_keys=True, ensure_ascii=False) == json.dumps(_jsonable(b), sort_keys=True, ensure_ascii=False)
    except Exception:
        return a == b

def _short_repr(v, maxlen: int = 120) -> str:
    try:
        s = json.dumps(_jsonable(v), ensure_ascii=False, sort_keys=True)
    except Exception:
        s = repr(v)
    s = s.replace("\n", " ")
    return s if len(s) <= maxlen else s[:maxlen-3] + "..."

def _build_cosmetic_diffs(fig, ref_props):
    diffs = []
    axes = _data_axes(fig)
    ref_axes = [_normalize_axd(axd) for axd in ref_props.get('axes', [])]
    # figura
    cur_fc = _rgba(fig.get_facecolor())
    ref_fc = ref_props.get('figure_facecolor')
    if ref_fc is not None and not _json_eq(cur_fc, ref_fc):
        diffs.append({
            'kind': 'figure_facecolor',
            'label': 'Figura → facecolor',
            'current': cur_fc, 'reference': ref_fc,
        })
    cur_st = _style_only_text_spec(getattr(fig, '_suptitle', None))
    ref_st = _style_only_text_spec((ref_props.get('suptitle_obj') or {'text': ref_props.get('suptitle', '')}))
    if ref_st and not _json_eq(cur_st, ref_st):
        diffs.append({
            'kind': 'suptitle_style',
            'label': 'Figura → estilo de suptitle',
            'current': cur_st, 'reference': ref_st,
        })
    # por axes
    n = min(len(axes), len(ref_axes))
    for i in range(n):
        ax = axes[i]
        axd = ref_axes[i]
        items = [
            ('ax_facecolor', f'Axis {i} → facecolor', _rgba(ax.get_facecolor()), axd.get('facecolor')),
            ('title_style',  f'Axis {i} → estilo de título', _style_only_text_spec(ax.title), _style_only_text_spec(axd.get('title', {}))),
            ('xlabel_style', f'Axis {i} → estilo de xlabel', _style_only_text_spec(ax.xaxis.label), _style_only_text_spec(axd.get('xlabel', {}))),
            ('ylabel_style', f'Axis {i} → estilo de ylabel', _style_only_text_spec(ax.yaxis.label), _style_only_text_spec(axd.get('ylabel', {}))),
            ('spines',       f'Axis {i} → spines', _ser_spines(ax), axd.get('spines', {})),
            ('grid',         f'Axis {i} → grid', _ser_grid(ax), axd.get('grid')),
            ('ticks_x',      f'Axis {i} → ticks X', _ser_ticks(ax, 'x'), (axd.get('ticks', {}) or {}).get('x', {})),
            ('ticks_y',      f'Axis {i} → ticks Y', _ser_ticks(ax, 'y'), (axd.get('ticks', {}) or {}).get('y', {})),
            ('legend_style', f'Axis {i} → leyenda (estilo/posición)', _legend_style_only_spec(_ser_legend(ax)), _legend_style_only_spec(axd.get('legend'))),
        ]
        for kind, label, curv, refv in items:
            if refv is not None and not _json_eq(curv, refv):
                diffs.append({
                    'kind': kind, 'axis_index': i, 'label': label, 'current': curv, 'reference': refv,
                })
    return diffs

def _apply_single_cosmetic_diff(fig, ref_props, diff: dict) -> bool:
    axes = _data_axes(fig)
    kind = diff.get('kind')

    if kind == 'figure_facecolor':
        try:
            fig.patch.set_facecolor(diff.get('reference'))
            return True
        except Exception:
            return False

    if kind == 'suptitle_style':
        st = getattr(fig, '_suptitle', None)
        if st is None:
            return False
        try:
            cur = _ser_text(st)
            merged = dict(cur)
            merged.update(diff.get('reference') or {})
            merged.pop('text', None)
            merged['text'] = cur.get('text', '')
            _apply_text(st, merged)
            return True
        except Exception:
            return False

    i = diff.get('axis_index')
    if i is None or i >= len(axes):
        return False
    ax = axes[i]
    ref_axes = [_normalize_axd(axd) for axd in ref_props.get('axes', [])]
    if i >= len(ref_axes):
        return False
    axd = ref_axes[i]

    if kind == 'ax_facecolor':
        try:
            ax.set_facecolor(axd.get('facecolor'))
            return True
        except Exception:
            return False
    if kind in {'title_style', 'xlabel_style', 'ylabel_style'}:
        try:
            if kind == 'title_style':
                target = ax.title
                cur = _ser_text(target)
                refspec = _style_only_text_spec(axd.get('title', {}))
            elif kind == 'xlabel_style':
                target = ax.xaxis.label
                cur = _ser_text(target)
                refspec = _style_only_text_spec(axd.get('xlabel', {}))
            else:
                target = ax.yaxis.label
                cur = _ser_text(target)
                refspec = _style_only_text_spec(axd.get('ylabel', {}))
            merged = dict(cur)
            merged.update(refspec or {})
            merged['text'] = cur.get('text', '')
            _apply_text(target, merged)
            return True
        except Exception:
            return False
    if kind == 'spines':
        try:
            _apply_spines(ax, axd.get('spines', {}))
            return True
        except Exception:
            return False
    if kind == 'grid':
        try:
            _apply_grid(ax, axd.get('grid'))
            return True
        except Exception:
            return False
    if kind == 'ticks_x':
        try:
            _apply_ticks(ax, (axd.get('ticks', {}) or {}).get('x', {}), 'x')
            return True
        except Exception:
            return False
    if kind == 'ticks_y':
        try:
            _apply_ticks(ax, (axd.get('ticks', {}) or {}).get('y', {}), 'y')
            return True
        except Exception:
            return False
    if kind == 'legend_style':
        ref_leg = axd.get('legend')
        if not isinstance(ref_leg, dict):
            return False
        try:
            cur_leg = _ser_legend(ax) or {}
            entries = cur_leg.get('entries') or []
            if not entries:
                handles, labels = ax.get_legend_handles_labels()
                if handles and labels:
                    tmp_leg = ax.legend(handles, labels)
                    tmp_info = _ser_legend(ax) or {}
                    try:
                        if tmp_leg is not None:
                            tmp_leg.remove()
                    except Exception:
                        pass
                    entries = tmp_info.get('entries') or []
            merged = {
                'title': ref_leg.get('title', ''),
                'entries': entries,
                'style': copy.deepcopy(ref_leg.get('style', {}) or {}),
            }
            leg = _rebuild_legend(ax, merged)
            return leg is not None
        except Exception:
            return False
    return False

def _apply_cosmetic_diffs(fig, ref_props, diffs_to_apply):
    applied = []
    for d in diffs_to_apply:
        if _apply_single_cosmetic_diff(fig, ref_props, d):
            applied.append(d.get('label', d.get('kind', '?')))
    try:
        fig.canvas.draw_idle()
    except Exception:
        pass
    return applied
def _menu_normalize_against_reference(fig):
    _boxed_menu('Normalizar contra figura de referencia', [
        'Usa un archivo JSON generado por este editor como referencia.',
        'Puede copiar: figsize, subplotpars, posiciones exactas de ejes y export_prefs.',
        'Adicionalmente puede igualar parámetros cosméticos (sin tocar curvas ni datos).',
        'Si la referencia es un JSON viejo sin posiciones, el editor convierte la figura actual a un layout normalizable.',
    ], width=104)
    ref_path = input('  Ruta al JSON de referencia (Enter = cancelar): ').strip().strip('"')
    if not ref_path:
        print('  Operación cancelada.')
        return
    try:
        ref = _load_reference_layout_from_json(ref_path)
    except Exception as e:
        print(f'  No se pudo leer la referencia: {e}')
        return

    copy_figsize       = _prompt_bool('Copiar figsize', True)
    copy_subplotpars   = _prompt_bool('Copiar subplots_adjust / subplotpars', True)
    same_n = len(ref.get('axes', [])) == len(_data_axes(fig))
    copy_axes_positions = _prompt_bool('Copiar posiciones exactas de ejes', same_n)
    copy_export_prefs  = _prompt_bool('Copiar preferencias de exportación PNG', True)

    changes, n_cur, n_ref, ref_has_positions = _apply_reference_layout(
        fig, ref,
        copy_figsize=copy_figsize,
        copy_subplotpars=copy_subplotpars,
        copy_axes_positions=copy_axes_positions,
        copy_export_prefs=copy_export_prefs,
    )
    if copy_axes_positions and n_cur != n_ref:
        print(f'  Aviso: no se copiaron posiciones de ejes porque la figura actual tiene {n_cur} subplot(s) y la referencia {n_ref}.')
    elif copy_axes_positions and n_cur == n_ref and not ref_has_positions:
        print('  Referencia sin posiciones explícitas: se convirtió la figura actual a un layout normalizable y se estimó una geometría compacta con tight_layout().')

    diffs = _build_cosmetic_diffs(fig, ref)
    if diffs:
        print(f'  Se detectaron {len(diffs)} diferencia(s) cosmética(s) relevantes (sin tocar curvas ni límites de datos).')
        apply_all = _prompt_bool('Igualar todos los parámetros cosméticos diferentes', True)
        selected = []
        if apply_all:
            selected = diffs
        else:
            print('  Responde por cada parámetro si querés adoptar el valor de la figura de referencia.')
            for d in diffs:
                print(f"    - {d['label']}")
                print(f"      actual: { _short_repr(d.get('current')) }")
                print(f"      ref   : { _short_repr(d.get('reference')) }")
                if _prompt_bool('      Aplicar valor de referencia', True):
                    selected.append(d)
        applied_cos = _apply_cosmetic_diffs(fig, ref, selected) if selected else []
        if applied_cos:
            changes.extend([f'cosmetic:{lab}' for lab in applied_cos])
            print(f'  Se aplicaron {len(applied_cos)} ajuste(s) cosmético(s).')
        else:
            print('  No se aplicaron ajustes cosméticos.')
    else:
        print('  No se detectaron diferencias cosméticas relevantes.')

    if changes:
        print('  Se aplicó: ' + ', '.join(changes))
    else:
        print('  No se aplicaron cambios.')

def _axes_union_box(fig):
    """BBox unión de los axes de datos en coords de figura: [l,b,r,t]."""
    axes = _data_axes(fig)
    if not axes:
        return None
    try:
        boxes = [ax.get_position().bounds for ax in axes]
        x0 = min(b[0] for b in boxes)
        y0 = min(b[1] for b in boxes)
        x1 = max(b[0] + b[2] for b in boxes)
        y1 = max(b[1] + b[3] for b in boxes)
        return [float(x0), float(y0), float(x1), float(y1)]
    except Exception:
        return None

def _remap_axes_to_target_box(fig, target_left, target_bottom, target_right, target_top):
    """Reescala y traslada todos los axes de datos para que su caja unión
    pase al rectángulo objetivo, preservando la geometría relativa interna.
    Funciona tanto para figuras creadas con subplots como con add_axes().
    """
    axes = _data_axes(fig)
    if not axes:
        raise ValueError("La figura no tiene subplots de datos.")
    cur = _axes_union_box(fig)
    if cur is None:
        raise ValueError("No se pudo determinar la caja actual de axes.")
    x0, y0, x1, y1 = cur
    cw = max(1e-9, x1 - x0)
    ch = max(1e-9, y1 - y0)
    tw = max(1e-9, float(target_right) - float(target_left))
    th = max(1e-9, float(target_top) - float(target_bottom))
    sx = tw / cw
    sy = th / ch
    for ax in axes:
        l, b, w, h = ax.get_position().bounds
        nl = float(target_left) + (l - x0) * sx
        nb = float(target_bottom) + (b - y0) * sy
        nw = w * sx
        nh = h * sy
        ax.set_position([nl, nb, nw, nh])
    return {
        "current_box": [x0, y0, x1, y1],
        "target_box": [float(target_left), float(target_bottom), float(target_right), float(target_top)],
        "scale_x": float(sx),
        "scale_y": float(sy),
        "n_axes": len(axes),
    }

def _menu_compact_visible_frame(fig):
    """Compacta el marco visible (márgenes exteriores de los axes) sin tocar xlim/ylim."""
    cur = _axes_union_box(fig)
    if cur is None:
        print("  No se pudo determinar la caja actual de los subplots.")
        return
    x0, y0, x1, y1 = cur
    print("\n  Compactar marco visible / márgenes exteriores")
    print(f"  Caja actual de axes: left={x0:.4f} right={x1:.4f} bottom={y0:.4f} top={y1:.4f}")
    print("  1. Preset compacto recomendado")
    print("  2. Compactar sólo margen superior")
    print("  3. Ajuste manual de left/right/bottom/top")
    print("  4. Volver")
    op = input("  Opción: ").strip()
    if op == "1":
        d = dict(_DEFAULT_FRAME_PRESET)
        l = _prompt_float("left", d["left"])
        r = _prompt_float("right", d["right"])
        b = _prompt_float("bottom", d["bottom"])
        t = _prompt_float("top", d["top"])
    elif op == "2":
        d = dict(_DEFAULT_FRAME_PRESET)
        l = x0
        r = x1
        b = y0
        t = _prompt_float("top", d["top"])
    elif op == "3":
        l = _prompt_float("left", x0)
        r = _prompt_float("right", x1)
        b = _prompt_float("bottom", y0)
        t = _prompt_float("top", y1)
    else:
        return
    try:
        l, r, b, t = float(l), float(r), float(b), float(t)
    except Exception:
        print("  Parámetros inválidos.")
        return
    if not (0 <= l < r <= 1 and 0 <= b < t <= 1):
        print("  Error: se requiere 0 <= left < right <= 1 y 0 <= bottom < top <= 1.")
        return
    info = _remap_axes_to_target_box(fig, l, b, r, t)
    print("  Marco visible actualizado.")
    print(f"    target_box = {info['target_box']}")
    print(f"    scale_x={info['scale_x']:.4f}  scale_y={info['scale_y']:.4f}")
def _menu_general(fig):
    """Configuración general de la figura: tamaño, fondo, suptitle, márgenes, tight_layout."""
    while True:
        sz = fig.get_size_inches()
        st = getattr(fig, "_suptitle", None)
        info1 = f"Tamaño: {sz[0]:.2f} × {sz[1]:.2f} pulgadas"
        info2 = f"Fondo: {fig.get_facecolor()}"
        st_txt = (st.get_text() if st else "").replace("\n", " ").strip()
        if not st_txt:
            st_txt = "(vacío)"
        prefs = _get_export_prefs(fig)
        crop_state = "sí" if prefs["autocrop_white"] else "no"
        _boxed_menu("Configuración general de la figura", [
            info1,
            info2,
            f"Suptitle: '{st_txt}'",
            f"PNG/export: bbox={prefs['bbox_mode']} | pad={prefs['pad_inches']:.3f} | autocrop={crop_state} | tol={prefs['autocrop_tol']}",
            "1. Tamaño de figura",
            "2. Color de fondo de la figura",
            "3. Suptitle (texto + fuente)",
            "4. Márgenes globales (subplots_adjust manual)",
            "5. Compactar marco visible (sin tocar ejes de datos)",
            "6. Aplicar tight_layout automático",
            "7. Layout / posición de subplots",
            "8. Diagnóstico de layout / tamaños",
            "9. Preferencias de guardado/exportación PNG",
            "10. Normalizar contra figura de referencia (.json)",
            "11. Volver",
        ], width=100)
        op = input("  Opción: ").strip()
        if op == "1":
            w = _prompt_float("Ancho (pulgadas)", sz[0])
            h = _prompt_float("Alto (pulgadas)",  sz[1])
            fig.set_size_inches(w, h, forward=True)
        elif op == "2":
            col = input("  Nuevo color (Enter=mantener): ").strip()
            if col:
                try:
                    fig.patch.set_facecolor(col)
                except Exception as e:
                    print(f"  Error: {e}")
        elif op == "3":
            st  = getattr(fig, "_suptitle", None)
            cur = {"text": st.get_text() if st else "",
                   "fontsize": st.get_fontsize() if st else 14,
                   "fontweight": st.get_fontweight() if st else "normal",
                   "color": st.get_color() if st else "black"}
            txt = _prompt("Suptitle (-- para quitar)", cur["text"])
            if txt == "--":
                if st:
                    try:
                        st.set_text("")
                        st.set_visible(False)
                    except Exception:
                        pass
            else:
                fs  = _prompt_float("Fontsize", cur["fontsize"])
                fw  = _prompt("Fontweight (normal/bold)", cur["fontweight"])
                col = input("  Color (Enter=mantener): ").strip()
                kw  = {"fontsize": fs, "fontweight": fw}
                if col:
                    kw["color"] = col
                try:
                    fig.suptitle(txt, **kw)
                except Exception:
                    try:
                        fig.suptitle(txt)
                    except Exception:
                        pass
        elif op == "4":
            try:
                sp = fig.subplotpars
                print(f"  Actual: left={sp.left:.3f} right={sp.right:.3f} top={sp.top:.3f} bottom={sp.bottom:.3f} wspace={sp.wspace:.3f} hspace={sp.hspace:.3f}")
            except Exception:
                pass
            kw = {k: _prompt_float(k, getattr(fig.subplotpars, k, 0.1))
                  for k in ("left","right","top","bottom","wspace","hspace")}
            try:
                fig.subplots_adjust(**kw)
            except Exception as e:
                print(f"  Error: {e}")
        elif op == "5":
            _menu_compact_visible_frame(fig)
        elif op == "6":
            try:
                fig.tight_layout()
                _refresh(fig)
                try:
                    sp = fig.subplotpars
                    print("  tight_layout aplicado. Márgenes resultantes:")
                    print(f"    left={sp.left:.3f}  right={sp.right:.3f}  top={sp.top:.3f}  bottom={sp.bottom:.3f}  wspace={sp.wspace:.3f}  hspace={sp.hspace:.3f}")
                    print("  Estos márgenes se guardarán automáticamente con 'Guardar'.")
                except Exception:
                    pass
            except Exception as e:
                print(f"  No se pudo aplicar tight_layout: {e}")
                print("  (Puede ocurrir si los ejes se crearon con fig.add_axes() en lugar de subplots.)")
            continue
        elif op == "7":
            axes = _data_axes(fig)
            print("\n  Layout:")
            print("  1. Posición exacta de un subplot")
            print("  2. Distribuir 2 paneles horizontales  3. Distribuir 2 paneles verticales")
            print("  4. Volver")
            op2 = input("  Opción: ").strip()
            if op2 == "1":
                ax, idx = _pick_axis(fig)
                pos = list(ax.get_position().bounds)
                print(f"  Actual ax[{idx}]: left={pos[0]:.4f} bottom={pos[1]:.4f} w={pos[2]:.4f} h={pos[3]:.4f}")
                l = _prompt_float("left",   pos[0])
                b = _prompt_float("bottom", pos[1])
                w = _prompt_float("width",  pos[2])
                h = _prompt_float("height", pos[3])
                ax.set_position([l,b,w,h])
            elif op2 == "2" and len(axes) == 2:
                axes[0].set_position([0.10,0.12,0.38,0.80])
                axes[1].set_position([0.58,0.12,0.38,0.80])
            elif op2 == "3" and len(axes) == 2:
                axes[0].set_position([0.12,0.56,0.80,0.34])
                axes[1].set_position([0.12,0.12,0.80,0.34])
        elif op == "8":
            try:
                sp = fig.subplotpars
                print("\n  Diagnóstico de layout:")
                print(f"    figsize = ({sz[0]:.3f}, {sz[1]:.3f}) in")
                print(f"    dpi     = {fig.dpi}")
                print(f"    subplotpars: left={sp.left:.4f} right={sp.right:.4f} top={sp.top:.4f} bottom={sp.bottom:.4f} wspace={sp.wspace:.4f} hspace={sp.hspace:.4f}")
                frac = _content_bbox_fraction(fig)
                if frac is not None:
                    print(f"    ocupación estimada del contenido: width={100*frac[0]:.1f}%  height={100*frac[1]:.1f}%")
                for i, ax in enumerate(_data_axes(fig), start=1):
                    pos = ax.get_position().bounds
                    print(f"    Ax {i}: left={pos[0]:.4f} bottom={pos[1]:.4f} w={pos[2]:.4f} h={pos[3]:.4f}")
                print("    Consejo: para igualar tamaños aparentes entre figuras, usá el mismo figsize, subplotpars")
                print("    y, si hace falta, las mismas posiciones de ejes. Para reducir blanco por arriba del marco, usá")
                print("    la opción \"Compactar marco visible\"; eso sí cambia la figura editable, no solo el PNG.")
            except Exception as e:
                print(f"  No se pudo generar el diagnóstico: {e}")
        elif op == "9":
            prefs = _get_export_prefs(fig)
            print("\n  Preferencias de guardado/exportación PNG")
            mode = _prompt("  bbox_mode (exact/tight/content)", prefs["bbox_mode"]).strip().lower()
            if mode not in {"exact", "tight", "content"}:
                mode = prefs["bbox_mode"]
            pad  = _prompt_float("  pad_inches (si bbox=tight/content)", prefs["pad_inches"])
            ac   = _prompt("  autocrop_white (on/off)", "on" if prefs["autocrop_white"] else "off").strip().lower()
            tol  = _prompt_int("  autocrop_tol [0..255]", prefs["autocrop_tol"])
            ppx  = _prompt_int("  autocrop_pad_px", prefs["autocrop_pad_px"])
            prefs.update({
                "bbox_mode": mode,
                "pad_inches": pad,
                "autocrop_white": (ac == "on"),
                "autocrop_tol": max(0, min(255, int(tol))),
                "autocrop_pad_px": max(0, int(ppx)),
            })
            _set_export_prefs(fig, prefs)
            print("  Preferencias actualizadas.")
        elif op == "10":
            _menu_normalize_against_reference(fig)
        elif op == "11":
            break
        else:
            print("  Opción inválida.")
        _refresh(fig)
def _menu_subplot(fig, active_ax, active_idx):
    while True:
        print(f"\n  ── Subplot activo: {active_idx} ──  '{active_ax.get_title()}'")
        print("   1. Título/xlabel/ylabel (texto + fuente)")
        print("   2. Límites y escalas")
        print("   3. Ticks (fontsize, rotación, dirección)")
        print("   4. Leyenda")
        print("   5. Líneas de referencia (vlines/hlines)")
        print("   6. Grid / Spines / Fondo")
        print("   7. Trazas (líneas de datos)")
        print("   8. Barras")
        print("   9. Scatters")
        print("  10. Textos / Anotaciones (+ recuadros)")
        print("  11. Redibujar   12. Volver")
        op = input("  Opción: ").strip()
        if   op == "1":  _menu_labels(active_ax, fig)
        elif op == "2":  _menu_limits_scales(active_ax, fig)
        elif op == "3":  _menu_ticks(active_ax, fig)
        elif op == "4":  _menu_legend(active_ax, fig)
        elif op == "5":  _menu_reflines(active_ax, fig)
        elif op == "6":  _menu_grid_spines_bg(active_ax, fig)
        elif op == "7":  _menu_lines(active_ax, fig)
        elif op == "8":  _menu_bars(active_ax, fig)
        elif op == "9":  _menu_scatters(active_ax, fig)
        elif op == "10": _menu_texts(active_ax, fig)
        elif op == "11": _refresh(fig)
        elif op == "12": return
        else: print("  Opción inválida.")
# ─────────────────────────────────────────────────────────────
#  EDITOR PRINCIPAL
# ─────────────────────────────────────────────────────────────
def _box_line(text: str, width: int = 60) -> str:
    s = str(text)
    if len(s) > width:
        s = s[:max(0, width-3)] + '...'
    return f"| {s:<{width}} |"
def _box_sep(width: int = 60) -> str:
    return '+' + '-' * (width + 2) + '+'
def _render_main_banner(active_idx, active_ax, base_filename: str) -> str:
    width = 60
    ttl = (active_ax.get_title() or '').replace('\n', ' / ')
    base = str(base_filename).replace('\n', ' ')
    lines = [
        _box_sep(width),
        _box_line('EDITOR DE COSMETICA DE FIGURA (v32)', width),
        _box_sep(width),
        _box_line(f'Subplot activo: {active_idx}  Titulo: {ttl}', width),
        _box_sep(width),
        _box_line('1. Configuracion general de la figura', width),
        _box_line('2. Elegir subplot activo', width),
        _box_line('3. Editar subplot activo (trazas, ejes, textos, etc.)', width),
        _box_sep(width),
        _box_line('4. Redibujar figura', width),
        _box_line(f'5. Guardar (JSON + CSV + PNG) [{base}]', width),
        _box_line('6. Exportar imagen (png/eps/pdf/svg)', width),
        _box_line('7. Salir', width),
        _box_sep(width),
    ]
    return '\n'.join(lines)
def edit_cosmetics(fig, base_filename: str = "figure"):
    _enable_interactive_mode_for_editor()
    _refresh(fig, pause=0.05)
    """Editor interactivo de cosmética (v32).
    Parámetros
    ----------
    fig           : matplotlib.figure.Figure
    base_filename : str  nombre base para guardar (sin extensión)
    """
    base_filename  = str(getattr(fig, "_fe_base_filename", base_filename))
    axes0 = _data_axes(fig)
    if axes0:
        saved_idx = getattr(fig, "_fe_active_idx", 0)
        try:
            saved_idx = int(saved_idx)
        except Exception:
            saved_idx = 0
        if saved_idx < 0 or saved_idx >= len(axes0):
            saved_idx = 0
        active_idx = saved_idx
        active_ax = axes0[active_idx]
    else:
        active_ax = None
        active_idx = None
    while True:
        axes = _data_axes(fig)
        if axes:
            if active_idx is None or active_idx >= len(axes):
                active_idx = 0
            active_ax = axes[active_idx]
        else:
            active_ax  = None
            active_idx = None
        ttl  = ((active_ax.get_title() if active_ax else 'ninguno') or 'sin titulo')[:28]
        base = Path(base_filename).name[:20]
        print(_render_main_banner(active_idx, active_ax, base_filename))
        op = input("  Opción: ").strip()
        if op == "1":
            _menu_general(fig)
        elif op == "2":
            if not axes:
                print("  No hay subplots editables.")
            else:
                active_ax, active_idx = _pick_axis(fig)
                try:
                    fig._fe_active_idx = active_idx
                except Exception:
                    pass
        elif op == "3":
            if not axes or active_ax is None:
                print("  No hay subplots editables.")
            else:
                _menu_subplot(fig, active_ax, active_idx)
        elif op == "4":
            _refresh(fig)
            print("  Figura redibujada.")
        elif op == "5":
            nb = input(f"  Nombre base [{base_filename}] (Enter=mantener): ").strip()
            if nb:
                base_filename = str(_base_path(nb))
            save_figure_data(fig, base_filename, save_png=True)
            paths = [Path(str(_base_path(base_filename)) + ext) for ext in (".json", ".csv", ".png")]
            missing = [str(p) for p in paths if not p.exists()]
            if missing:
                print("  Advertencia: faltan archivos tras guardar:")
                for p in missing:
                    print(f"    - {p}")
            else:
                prefs = _get_export_prefs(fig)
                print("  Verificación OK:")
                for p in paths:
                    print(f"    - {p.name} ({p.stat().st_size} bytes)")
                print(f"  PNG guardado con bbox={prefs['bbox_mode']} | autocrop={'on' if prefs['autocrop_white'] else 'off'}")
            try:
                fig._fe_base_filename = base_filename
            except Exception:
                pass
        elif op == "6":
            fmt = _prompt("Formato (png/eps/pdf/svg)", "png")
            dpi = _prompt_float("DPI (solo raster)", 300)
            prefs = _get_export_prefs(fig)
            bbox_mode = _prompt("Borde exportado (exact/tight/content)", prefs["bbox_mode"]).strip().lower()
            pad_inches = _prompt_float("pad_inches (si bbox=tight/content)", prefs["pad_inches"])
            autocrop = prefs["autocrop_white"]
            if fmt.lower() == "png":
                ac = _prompt("autocrop_white PNG (on/off)", "on" if prefs["autocrop_white"] else "off").strip().lower()
                autocrop = (ac == "on")
            nb  = input(f"  Nombre base [{base_filename}] (Enter=mantener): ").strip()
            if nb:
                base_filename = str(_base_path(nb))
            out = str(_base_path(base_filename)) + "." + fmt
            try:
                local_prefs = dict(prefs)
                if bbox_mode.startswith("t"):
                    _mode = "tight"
                elif bbox_mode.startswith("c"):
                    _mode = "content"
                elif bbox_mode.startswith("e"):
                    _mode = "exact"
                else:
                    _mode = prefs.get("bbox_mode", "content")
                local_prefs.update({"bbox_mode": _mode, "pad_inches": pad_inches, "autocrop_white": autocrop})
                _save_figure_image(fig, out, dpi=dpi, prefs=local_prefs)
                print(f"  Exportado: {out}")
                if local_prefs["bbox_mode"] in {"tight", "content"}:
                    print(f"  Nota: bbox_mode={local_prefs['bbox_mode']} + pad={local_prefs['pad_inches']}")
                if fmt.lower() == "png" and local_prefs.get("autocrop_white", False):
                    print(f"  Nota: PNG recortado automáticamente (tol={local_prefs['autocrop_tol']}, pad_px={local_prefs['autocrop_pad_px']}).")
            except Exception as e:
                print(f"  Error: {e}")
        elif op == "7":
            _refresh(fig)
            print("  Saliendo del editor.")
            return fig
        else:
            print("  Opción inválida.")


# ============================================================================
#  V36 - separación / recomposición con leyenda compartida
# ============================================================================
_FORMAT_VERSION = 36

def _safe_stem(pathlike):
    try:
        return Path(pathlike).with_suffix("")
    except Exception:
        return Path(str(pathlike))

def _ensure_json_path(pathlike):
    p = Path(pathlike)
    if p.suffix.lower() != ".json":
        p = p.with_suffix(".json")
    return p

def _read_figprops(pathlike):
    p = _ensure_json_path(pathlike)
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f), p

def _default_single_panel_position(frame_preset=None):
    fr = dict(_DEFAULT_FRAME_PRESET)
    if isinstance(frame_preset, dict):
        fr.update({k: float(v) for k, v in frame_preset.items() if k in fr and v is not None})
    left = float(fr['left']); right = float(fr['right'])
    bottom = float(fr['bottom']); top = float(fr['top'])
    return [left, bottom, max(1e-6, right-left), max(1e-6, top-bottom)]

def _estimate_single_figsize(fig_size, axis_pos, frame_preset=None, min_size=(3.0, 2.4)):
    try:
        fw, fh = [float(v) for v in fig_size]
        l,b,w,h = [float(v) for v in axis_pos]
        target = _default_single_panel_position(frame_preset)
        tw, th = float(target[2]), float(target[3])
        out_w = fw * w / max(tw, 1e-6)
        out_h = fh * h / max(th, 1e-6)
        return [max(float(min_size[0]), out_w), max(float(min_size[1]), out_h)]
    except Exception:
        return [max(float(min_size[0]), float(fig_size[0]) if isinstance(fig_size, (list, tuple)) and len(fig_size) > 0 else 6.0),
                max(float(min_size[1]), float(fig_size[1]) if isinstance(fig_size, (list, tuple)) and len(fig_size) > 1 else 4.0)]

def _normalize_panel_json(fig_props, axis_index=0, size_mode='autosize', frame_preset=None,
                          include_suptitle=False, suptitle_mode='blank',
                          attach_shared_legend=True, show_shared_legend=False):
    axes = fig_props.get('axes', []) or []
    if not axes:
        raise ValueError('La figura no contiene ejes serializados.')
    if axis_index < 0 or axis_index >= len(axes):
        raise IndexError(f'axis_index fuera de rango: {axis_index}')
    out = copy.deepcopy(fig_props)
    axd = copy.deepcopy(axes[axis_index])
    orig_size = fig_props.get('size', [8, 4])
    orig_pos = axd.get('position') or [0.125, 0.11, 0.775, 0.77]
    if str(size_mode).lower().strip() == 'keep_size':
        out['size'] = _jsonable(orig_size)
    else:
        out['size'] = _jsonable(_estimate_single_figsize(orig_size, orig_pos, frame_preset=frame_preset))
    axd['position'] = _jsonable(_default_single_panel_position(frame_preset=frame_preset))
    if attach_shared_legend and not axd.get('legend'):
        shared_leg = _infer_shared_legend_for_axis(fig_props, axis_index)
        if shared_leg is not None:
            shared_leg['show_by_default'] = bool(show_shared_legend)
            axd['shared_legend'] = shared_leg
    out['axes'] = [axd]
    out['subplot_layout'] = [1, 1]
    out['subplots_adjust'] = None
    out['layout_engine'] = {
        'serialize_positions': True,
        'apply_tight_layout_on_load': False,
        'save_subplots_adjust_none': True,
    }
    if not include_suptitle:
        out['suptitle'] = ''
        out['suptitle_obj'] = {'text': ''}
    elif suptitle_mode == 'axis_title':
        ttl = ''
        try:
            ttl = axd.get('title', {}).get('text', '')
        except Exception:
            ttl = ''
        out['suptitle'] = ttl
        out['suptitle_obj'] = {'text': ttl}
    return out

def split_json_figure_files(pathlike, output_dir=None, prefix=None, which=None, size_mode='autosize',
                           frame_preset=None, include_suptitle=False, save_png=True,
                           attach_shared_legend=True, show_shared_legend=False):
    fig_props, p = _read_figprops(pathlike)
    axes = fig_props.get('axes', []) or []
    if not axes:
        raise ValueError('El JSON no contiene subplots para separar.')
    out_dir = Path(output_dir) if output_dir else p.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = prefix or p.stem
    if which is None:
        which = list(range(len(axes)))
    results = []
    for idx0 in which:
        idx = int(idx0)
        panel_props = _normalize_panel_json(fig_props, axis_index=idx, size_mode=size_mode,
                                            frame_preset=frame_preset, include_suptitle=include_suptitle,
                                            attach_shared_legend=attach_shared_legend,
                                            show_shared_legend=show_shared_legend)
        out_base = out_dir / f"{stem}_ax{idx+1}"
        with open(out_base.with_suffix('.json'), 'w', encoding='utf-8') as f:
            json.dump(panel_props, f, ensure_ascii=False, indent=2)
        fig_panel = load_figure(str(out_base.with_suffix('.json')), show=False)
        save_figure_data(fig_panel, str(out_base), save_png=save_png)
        try:
            plt.close(fig_panel)
        except Exception:
            pass
        results.append(str(out_base))
    return results

def _grid_positions(n_panels, arrangement='horizontal', nrows=None, ncols=None,
                    frame=None, wspace=0.08, hspace=0.08):
    frame = dict(_DEFAULT_FRAME_PRESET if frame is None else frame)
    left = float(frame.get('left', 0.11))
    right = float(frame.get('right', 0.98))
    bottom = float(frame.get('bottom', 0.11))
    top = float(frame.get('top', 0.98))
    avail_w = max(1e-6, right-left)
    avail_h = max(1e-6, top-bottom)
    arr = str(arrangement).lower().strip()
    if arr == 'vertical':
        nrows = n_panels if not nrows else int(nrows)
        ncols = 1 if not ncols else int(ncols)
    elif arr == 'grid':
        if not ncols and not nrows:
            ncols = int(np.ceil(np.sqrt(n_panels)))
            nrows = int(np.ceil(n_panels / ncols))
        elif ncols and not nrows:
            ncols = int(ncols); nrows = int(np.ceil(n_panels / ncols))
        elif nrows and not ncols:
            nrows = int(nrows); ncols = int(np.ceil(n_panels / nrows))
        else:
            nrows = int(nrows); ncols = int(ncols)
    else:
        nrows = 1 if not nrows else int(nrows)
        ncols = n_panels if not ncols else int(ncols)
    nrows = max(1, int(nrows)); ncols = max(1, int(ncols))
    gap_x = float(wspace) * avail_w
    gap_y = float(hspace) * avail_h
    cell_w = (avail_w - gap_x * (ncols - 1)) / max(1, ncols)
    cell_h = (avail_h - gap_y * (nrows - 1)) / max(1, nrows)
    if cell_w <= 0 or cell_h <= 0:
        raise ValueError('wspace/hspace demasiado grandes para el marco elegido.')
    positions = []
    for i in range(n_panels):
        r = i // ncols
        c = i % ncols
        if r >= nrows:
            break
        x = left + c * (cell_w + gap_x)
        y = top - (r + 1) * cell_h - r * gap_y
        positions.append([x, y, cell_w, cell_h])
    return positions, (nrows, ncols)

def _compose_figsize_from_parts(parts, arrangement='horizontal', nrows=None, ncols=None):
    sizes = []
    for fp in parts:
        sz = fp.get('size', [6,4])
        try:
            sizes.append((float(sz[0]), float(sz[1])))
        except Exception:
            sizes.append((6.0,4.0))
    widths = [s[0] for s in sizes] or [6.0]
    heights = [s[1] for s in sizes] or [4.0]
    n = len(sizes)
    arr = str(arrangement).lower().strip()
    if arr == 'vertical':
        return [max(widths), sum(heights)]
    if arr == 'grid':
        if not ncols and not nrows:
            ncols = int(np.ceil(np.sqrt(n)))
            nrows = int(np.ceil(n / ncols))
        elif ncols and not nrows:
            ncols = int(ncols); nrows = int(np.ceil(n / ncols))
        elif nrows and not ncols:
            nrows = int(nrows); ncols = int(np.ceil(n / nrows))
        else:
            nrows = int(nrows); ncols = int(ncols)
        row_heights = []
        col_widths = []
        for r in range(nrows):
            row = heights[r*ncols:(r+1)*ncols]
            if row:
                row_heights.append(max(row))
        for c in range(ncols):
            col = widths[c::ncols]
            if col:
                col_widths.append(max(col))
        return [sum(col_widths) if col_widths else max(widths), sum(row_heights) if row_heights else max(heights)]
    return [sum(widths), max(heights)]

def recompose_json_figures(json_files, output_base=None, arrangement='horizontal', nrows=None, ncols=None,
                           wspace=0.08, hspace=0.08, frame=None, panel_positions=None,
                           inherit_global=True, reference_json=None, open_editor=False,
                           save_png=True, shared_legend_panels=None):
    if not json_files:
        raise ValueError('No se proporcionaron archivos JSON para recomponer.')
    parts = []
    for jf in json_files:
        fp, path = _read_figprops(jf)
        axes = fp.get('axes', []) or []
        if len(axes) != 1:
            raise ValueError(f'Cada JSON de entrada debe contener exactamente 1 subplot: {path.name}')
        parts.append((fp, path))
    ref_props = None
    if reference_json:
        ref_props, _ = _read_figprops(reference_json)
    elif inherit_global:
        ref_props = copy.deepcopy(parts[0][0])
    fig_props = copy.deepcopy(ref_props) if ref_props is not None else copy.deepcopy(parts[0][0])
    if not inherit_global and ref_props is None:
        fig_props['suptitle'] = ''
        fig_props['suptitle_obj'] = {'text': ''}
    new_axes = [copy.deepcopy(fp['axes'][0]) for fp, _ in parts]
    n = len(new_axes)
    if panel_positions is None:
        panel_positions, layout = _grid_positions(n, arrangement=arrangement, nrows=nrows, ncols=ncols,
                                                  frame=frame, wspace=wspace, hspace=hspace)
    else:
        layout = (1, n)
        if len(panel_positions) != n:
            raise ValueError('La cantidad de posiciones exactas no coincide con la cantidad de paneles.')
    if len(panel_positions) < n:
        raise ValueError('No alcanzan las posiciones calculadas para todos los paneles.')
    for axd, pos in zip(new_axes, panel_positions):
        axd['position'] = _jsonable([float(v) for v in pos])
    shared_legend_panels = [] if shared_legend_panels is None else list(shared_legend_panels)
    for idx in shared_legend_panels:
        try:
            idx = int(idx)
        except Exception:
            continue
        if 0 <= idx < len(new_axes):
            sh = new_axes[idx].get('shared_legend')
            if isinstance(sh, dict):
                sh['show_by_default'] = True
    fig_props['axes'] = new_axes
    fig_props['subplot_layout'] = [int(layout[0]), int(layout[1])]
    fig_props['subplots_adjust'] = None
    fig_props['layout_engine'] = {
        'serialize_positions': True,
        'apply_tight_layout_on_load': False,
        'save_subplots_adjust_none': True,
    }
    fig_props['size'] = _jsonable(_compose_figsize_from_parts([fp for fp, _ in parts], arrangement=arrangement,
                                                              nrows=nrows, ncols=ncols))
    if output_base is None:
        parent = parts[0][1].parent
        output_base = parent / 'recomposed_figure'
    out_base = _safe_stem(output_base)
    with open(out_base.with_suffix('.json'), 'w', encoding='utf-8') as f:
        json.dump(fig_props, f, ensure_ascii=False, indent=2)
    fig = load_figure(str(out_base.with_suffix('.json')), show=False)
    save_figure_data(fig, str(out_base), save_png=save_png)
    if open_editor:
        try:
            fig._fe_base_filename = str(out_base)
        except Exception:
            pass
        return fig, str(out_base)
    try:
        plt.close(fig)
    except Exception:
        pass
    return None, str(out_base)

def _prompt_yesno(msg, default=True):
    d = 's' if default else 'n'
    raw = input(f"{msg} [{'S/n' if default else 's/N'}]: ").strip().lower()
    if not raw:
        return default
    return raw.startswith('s') or raw.startswith('y')

def _prompt_path_list(msg):
    raw = input(msg).strip()
    if not raw:
        return []
    parts = [p.strip().strip('"').strip("'") for p in raw.replace(';', ',').split(',')]
    return [p for p in parts if p]

def _save_subplot_as_individual(fig, active_idx, base_filename='figure', size_mode='autosize',
                                frame_preset=None, include_suptitle=False,
                                attach_shared_legend=True, show_shared_legend=False):
    tmp_json = None
    try:
        with tempfile.TemporaryDirectory() as td:
            tmp_base = Path(td) / 'temp_split_source'
            save_figure_data(fig, str(tmp_base), save_png=False)
            out_default = str(_safe_stem(base_filename)) + f'_ax{active_idx+1}'
            out = input(f"  Nombre base para este subplot [{out_default}] (Enter=mantener): ").strip()
            out_base = _safe_stem(out or out_default)
            res = split_json_figure_files(str(tmp_base.with_suffix('.json')), output_dir=out_base.parent,
                                          prefix=out_base.name, which=[active_idx],
                                          size_mode=size_mode, frame_preset=frame_preset,
                                          include_suptitle=include_suptitle, save_png=True,
                                          attach_shared_legend=attach_shared_legend,
                                          show_shared_legend=show_shared_legend)
            return res[0] if res else None
    finally:
        if tmp_json:
            pass

def _menu_split_recompose(fig, base_filename='figure'):
    while True:
        print("\n  ── Separar / recomponer figuras ──")
        print("   1. Separar figura actual en figuras individuales")
        print("   2. Recomponer figura compuesta a partir de JSON individuales")
        print("   3. Volver")
        op = input("  Opción: ").strip()
        if op == '1':
            axes = _data_axes(fig)
            if not axes:
                print('  No hay subplots editables para separar.')
                continue
            which_raw = input(f"  Índices a separar 1..{len(axes)} [Enter=todos]: ").strip()
            if which_raw:
                try:
                    which = [max(1, int(v.strip()))-1 for v in which_raw.replace(';', ',').split(',') if v.strip()]
                    which = [i for i in which if 0 <= i < len(axes)]
                except Exception:
                    which = list(range(len(axes)))
            else:
                which = list(range(len(axes)))
            size_mode = _prompt("  size_mode (autosize/keep_size)", "autosize").strip().lower()
            include_suptitle = _prompt_yesno("  ¿Conservar suptitle global en cada figura individual?", default=False)
            attach_shared_legend = _prompt_yesno("  ¿Adjuntar metadata de leyenda compartida a paneles sin leyenda propia?", default=True)
            show_shared_legend = False
            if attach_shared_legend:
                show_shared_legend = _prompt_yesno("  ¿Mostrar esa leyenda heredada por defecto en los paneles exportados?", default=False)
            out_default = str(_safe_stem(base_filename))
            out = input(f"  Prefijo de salida [{out_default}] (Enter=mantener): ").strip()
            out_base = _safe_stem(out or out_default)
            with tempfile.TemporaryDirectory() as td:
                tmp_base = Path(td) / 'current_figure'
                save_figure_data(fig, str(tmp_base), save_png=False)
                res = split_json_figure_files(str(tmp_base.with_suffix('.json')), output_dir=out_base.parent,
                                             prefix=out_base.name, which=which, size_mode=size_mode,
                                             include_suptitle=include_suptitle, save_png=True,
                                             attach_shared_legend=attach_shared_legend,
                                             show_shared_legend=show_shared_legend)
            print('  Subplots guardados:')
            for r in res:
                print(f'    - {r}.json / .csv / .png')
        elif op == '2':
            files = _prompt_path_list("  JSONs individuales (separados por coma): ")
            if not files:
                print('  No se ingresaron archivos.')
                continue
            arrangement = _prompt("  Disposición (horizontal/vertical/grid)", "horizontal").strip().lower()
            nrows = None; ncols = None
            if arrangement == 'grid':
                nrows_raw = input('  nrows [auto]: ').strip()
                ncols_raw = input('  ncols [auto]: ').strip()
                nrows = int(nrows_raw) if nrows_raw else None
                ncols = int(ncols_raw) if ncols_raw else None
            exact = _prompt_yesno('  ¿Definir posiciones exactas de paneles?', default=False)
            positions = None
            wspace = 0.08; hspace = 0.08
            if exact:
                positions = []
                print('  Ingresar left,bottom,width,height para cada panel (coords figura 0..1).')
                for i, jf in enumerate(files, start=1):
                    raw = input(f'    Panel {i} [{Path(jf).stem}]: ').strip()
                    vals = [float(v.strip()) for v in raw.split(',')]
                    if len(vals) != 4:
                        raise ValueError('Cada panel exacto requiere 4 valores: left,bottom,width,height')
                    positions.append(vals)
            else:
                wspace = _prompt_float('  wspace fraccional', 0.08)
                hspace = _prompt_float('  hspace fraccional', 0.08)
            inherit = _prompt_yesno('  ¿Heredar estilo global de una figura de referencia o del primer panel?', default=True)
            ref_json = None
            if inherit:
                ref_json_in = input('  JSON de referencia [Enter=usar el primero]: ').strip()
                ref_json = ref_json_in or None
            out_default = str(_safe_stem(base_filename)) + '_recomposed'
            out = input(f"  Nombre base de salida [{out_default}] (Enter=mantener): ").strip()
            out_base = _safe_stem(out or out_default)
            shared_raw = input('  Panel(es) que deben mostrar leyenda compartida [Enter=ninguno; ej. 1 o 1,3]: ').strip()
            shared_panels = []
            if shared_raw:
                try:
                    shared_panels = [max(1, int(v.strip())) - 1 for v in shared_raw.replace(';', ',').split(',') if v.strip()]
                except Exception:
                    shared_panels = []
            open_now = _prompt_yesno('  ¿Abrir la figura recompuesta en el editor?', default=True)
            fig_new, out_base_str = recompose_json_figures(files, output_base=out_base,
                                                           arrangement=arrangement, nrows=nrows, ncols=ncols,
                                                           wspace=wspace, hspace=hspace, panel_positions=positions,
                                                           inherit_global=inherit, reference_json=ref_json,
                                                           open_editor=open_now, save_png=True,
                                                           shared_legend_panels=shared_panels)
            print(f'  Figura recompuesta guardada en: {out_base_str}.json / .csv / .png')
            if open_now and fig_new is not None:
                return edit_cosmetics(fig_new, base_filename=out_base_str)
        elif op == '3':
            return fig
        else:
            print('  Opción inválida.')



# ─────────────────────────────────────────────────────────────
#  PRESETS COSMÉTICOS EDITORIALES (v37)
# ─────────────────────────────────────────────────────────────
# Estilos de fantasía inspirados en usos editoriales frecuentes.
_FIGURE_STYLE_PRESETS = {
    "nature_minimal": {"label": "Nature-like Minimal", "description": "Limpio, mucho blanco, líneas finas y leyenda sin marco.", "figsize": (3.35, 2.55), "dpi": 300, "facecolor": "white", "axes_facecolor": "white", "fontfamily": "DejaVu Sans", "title_size": 9.0, "label_size": 8.5, "tick_size": 7.5, "legend_size": 7.2, "legend_title_size": 7.5, "line_width": 1.15, "marker_size": 4.0, "spine_width": 0.75, "tick_width": 0.75, "tick_length": 3.0, "tick_direction": "out", "grid": {"visible": False}, "legend_frame": False, "palette": ["#222222", "#0072B2", "#D55E00", "#009E73", "#CC79A7", "#56B4E9"], "margins": {"left": 0.18, "right": 0.97, "bottom": 0.18, "top": 0.92, "wspace": 0.28, "hspace": 0.28}, "export": {"bbox_mode": "content", "pad_inches": 0.015, "autocrop_white": False}},
    "prl_compact": {"label": "PRL Compact", "description": "Compacto, sobrio, ticks hacia adentro y alto aprovechamiento del espacio.", "figsize": (3.40, 2.35), "dpi": 300, "facecolor": "white", "axes_facecolor": "white", "fontfamily": "DejaVu Serif", "title_size": 8.5, "label_size": 8.2, "tick_size": 7.2, "legend_size": 6.8, "legend_title_size": 7.0, "line_width": 1.05, "marker_size": 3.6, "spine_width": 0.85, "tick_width": 0.85, "tick_length": 3.2, "tick_direction": "in", "grid": {"visible": False}, "legend_frame": False, "palette": ["#000000", "#4D4D4D", "#1F77B4", "#D62728", "#2CA02C", "#9467BD"], "margins": {"left": 0.17, "right": 0.98, "bottom": 0.17, "top": 0.94, "wspace": 0.22, "hspace": 0.22}, "export": {"bbox_mode": "content", "pad_inches": 0.012, "autocrop_white": False}},
    "prb_technical": {"label": "PRB Technical", "description": "Técnico, legible, spines completos y grilla tenue opcional.", "figsize": (3.55, 2.75), "dpi": 300, "facecolor": "white", "axes_facecolor": "white", "fontfamily": "DejaVu Serif", "title_size": 9.5, "label_size": 9.0, "tick_size": 8.0, "legend_size": 7.5, "legend_title_size": 8.0, "line_width": 1.35, "marker_size": 4.4, "spine_width": 0.95, "tick_width": 0.9, "tick_length": 3.6, "tick_direction": "in", "grid": {"visible": True, "color": "0.86", "linestyle": ":", "linewidth": 0.55, "alpha": 0.75}, "legend_frame": True, "legend_framealpha": 0.90, "palette": ["#1B1B1B", "#005AB5", "#DC3220", "#009E73", "#E69F00", "#7B3294"], "margins": {"left": 0.18, "right": 0.97, "bottom": 0.18, "top": 0.92, "wspace": 0.30, "hspace": 0.30}, "export": {"bbox_mode": "content", "pad_inches": 0.018, "autocrop_white": False}},
    "apl_modern": {"label": "APL Modern", "description": "Sans-serif moderno, paleta viva, líneas medianas y buena lectura rápida.", "figsize": (3.60, 2.70), "dpi": 300, "facecolor": "white", "axes_facecolor": "#FBFBFB", "fontfamily": "DejaVu Sans", "title_size": 10.0, "label_size": 9.2, "tick_size": 8.0, "legend_size": 7.6, "legend_title_size": 8.0, "line_width": 1.55, "marker_size": 4.8, "spine_width": 0.90, "tick_width": 0.85, "tick_length": 3.4, "tick_direction": "out", "grid": {"visible": True, "color": "0.88", "linestyle": "-", "linewidth": 0.45, "alpha": 0.65}, "legend_frame": True, "legend_framealpha": 0.85, "palette": ["#263238", "#0077BB", "#EE7733", "#33BBEE", "#CC3311", "#009988"], "margins": {"left": 0.17, "right": 0.97, "bottom": 0.17, "top": 0.91, "wspace": 0.30, "hspace": 0.30}, "export": {"bbox_mode": "content", "pad_inches": 0.018, "autocrop_white": False}},
    "review_bold": {"label": "Graphical Abstract / Review Bold", "description": "Más visual: tipografía grande, líneas gruesas y contraste alto.", "figsize": (4.20, 3.15), "dpi": 300, "facecolor": "white", "axes_facecolor": "white", "fontfamily": "DejaVu Sans", "title_size": 12.0, "label_size": 11.0, "tick_size": 9.2, "legend_size": 8.8, "legend_title_size": 9.2, "line_width": 2.05, "marker_size": 6.0, "spine_width": 1.15, "tick_width": 1.05, "tick_length": 4.2, "tick_direction": "out", "grid": {"visible": True, "color": "0.82", "linestyle": "--", "linewidth": 0.65, "alpha": 0.70}, "legend_frame": True, "legend_framealpha": 0.95, "palette": ["#111111", "#0072B2", "#D55E00", "#009E73", "#CC79A7", "#F0E442", "#56B4E9"], "margins": {"left": 0.16, "right": 0.97, "bottom": 0.16, "top": 0.90, "wspace": 0.32, "hspace": 0.32}, "export": {"bbox_mode": "content", "pad_inches": 0.020, "autocrop_white": False}},
}

def list_cosmetic_presets():
    return {k: {"label": v.get("label", k), "description": v.get("description", "")} for k, v in _FIGURE_STYLE_PRESETS.items()}

def _apply_font_to_text(txt, fontsize=None, fontfamily=None, fontweight=None):
    if txt is None: return
    try:
        if fontsize is not None: txt.set_fontsize(float(fontsize))
        if fontfamily: txt.set_fontfamily(fontfamily)
        if fontweight: txt.set_fontweight(fontweight)
    except Exception: pass

def _apply_preset_to_legend(ax, preset):
    leg = ax.get_legend()
    if leg is None: return
    try:
        leg.set_frame_on(bool(preset.get("legend_frame", False)))
        frame = leg.get_frame()
        if preset.get("legend_framealpha") is not None: frame.set_alpha(float(preset.get("legend_framealpha")))
        frame.set_linewidth(float(preset.get("spine_width", 0.8)))
        frame.set_edgecolor("0.25"); frame.set_facecolor("white")
    except Exception: pass
    for t in leg.get_texts(): _apply_font_to_text(t, preset.get("legend_size"), preset.get("fontfamily"))
    try: _apply_font_to_text(leg.get_title(), preset.get("legend_title_size"), preset.get("fontfamily"))
    except Exception: pass

def apply_cosmetic_preset(fig, preset_name="prb_technical", apply_colors=True, apply_layout=True, apply_linewidths=True, apply_marker_sizes=True, apply_legend=True):
    key = str(preset_name).strip().lower()
    if key not in _FIGURE_STYLE_PRESETS:
        raise ValueError(f"Preset desconocido: {preset_name}. Opciones: {', '.join(_FIGURE_STYLE_PRESETS)}")
    preset = _FIGURE_STYLE_PRESETS[key]; palette = list(preset.get("palette", []))
    try: fig.set_size_inches(*preset.get("figsize", fig.get_size_inches()), forward=True)
    except Exception: pass
    try: fig.set_dpi(float(preset.get("dpi", fig.dpi)))
    except Exception: pass
    try: fig.patch.set_facecolor(preset.get("facecolor", "white"))
    except Exception: pass
    _apply_font_to_text(getattr(fig, "_suptitle", None), preset.get("title_size"), preset.get("fontfamily"), "bold")
    for ax in _data_axes(fig):
        try: ax.set_facecolor(preset.get("axes_facecolor", "white"))
        except Exception: pass
        _apply_font_to_text(ax.title, preset.get("title_size"), preset.get("fontfamily"), "bold")
        _apply_font_to_text(ax.xaxis.label, preset.get("label_size"), preset.get("fontfamily"))
        _apply_font_to_text(ax.yaxis.label, preset.get("label_size"), preset.get("fontfamily"))
        try:
            ax.tick_params(axis="both", which="both", labelsize=float(preset.get("tick_size", 8)), width=float(preset.get("tick_width", 0.8)), length=float(preset.get("tick_length", 3.0)), direction=preset.get("tick_direction", "out"))
        except Exception: pass
        for lab in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
            _apply_font_to_text(lab, preset.get("tick_size"), preset.get("fontfamily"))
        for sp in ax.spines.values():
            try:
                sp.set_linewidth(float(preset.get("spine_width", 0.8))); sp.set_color("0.15"); sp.set_visible(True)
            except Exception: pass
        _apply_grid(ax, preset.get("grid", {"visible": False}))
        data_lines = [ln for ln in ax.get_lines() if not getattr(ln, "_fe_refline", None)]
        for i, ln in enumerate(data_lines):
            try:
                if apply_colors and palette:
                    col = palette[i % len(palette)]; ln.set_color(col); ln.set_markerfacecolor(col); ln.set_markeredgecolor(col)
                if apply_linewidths: ln.set_linewidth(float(preset.get("line_width", 1.3)))
                if apply_marker_sizes:
                    ln.set_markersize(float(preset.get("marker_size", 4.0)))
                    ln.set_markeredgewidth(max(0.6, float(preset.get("line_width", 1.3))*0.65))
            except Exception: pass
        if apply_colors and palette:
            for i, patch in enumerate(list(getattr(ax, "patches", []))):
                try:
                    patch.set_facecolor(palette[i % len(palette)]); patch.set_edgecolor("0.15"); patch.set_linewidth(float(preset.get("spine_width", 0.8)))
                except Exception: pass
        if apply_legend: _apply_preset_to_legend(ax, preset)
    if apply_layout:
        try: fig.subplots_adjust(**(preset.get("margins", {}) or {}))
        except Exception: pass
    try:
        prefs = _get_export_prefs(fig); prefs.update(preset.get("export", {}) or {}); _set_export_prefs(fig, prefs)
    except Exception: pass
    try: fig._fe_cosmetic_preset = key
    except Exception: pass
    _refresh(fig)
    return fig

def _menu_cosmetic_presets(fig):
    keys = list(_FIGURE_STYLE_PRESETS.keys())
    while True:
        print("\n  ── Formatos editoriales / presets cosméticos ──")
        for i, k in enumerate(keys, start=1):
            pr = _FIGURE_STYLE_PRESETS[k]
            print(f"   {i}. {pr.get('label', k)}  [{k}]")
            print(f"      {pr.get('description', '')}")
        print(f"   {len(keys)+1}. Volver")
        op = input("  Opción: ").strip()
        if not op: return fig
        try: idx = int(op)
        except Exception:
            print("  Opción inválida."); continue
        if idx == len(keys) + 1: return fig
        if not (1 <= idx <= len(keys)):
            print("  Opción inválida."); continue
        key = keys[idx-1]
        apply_colors = _prompt_yesno("  ¿Aplicar también paleta de colores del preset?", default=True)
        apply_layout = _prompt_yesno("  ¿Aplicar tamaño/márgenes del preset?", default=True)
        try:
            apply_cosmetic_preset(fig, key, apply_colors=apply_colors, apply_layout=apply_layout)
            print(f"  Preset aplicado: {_FIGURE_STYLE_PRESETS[key].get('label', key)}")
        except Exception as e:
            print(f"  Error aplicando preset: {e}")
        return fig

def _render_main_banner(active_idx, active_ax, base_filename: str) -> str:
    width = 66
    ttl = (active_ax.get_title() or '').replace('\n', ' / ') if active_ax is not None else 'ninguno'
    base = str(base_filename).replace('\n', ' ')
    lines = [
        _box_sep(width),
        _box_line('EDITOR DE COSMETICA DE FIGURA (v37 + presets)', width),
        _box_sep(width),
        _box_line(f'Subplot activo: {active_idx}  Titulo: {ttl}', width),
        _box_sep(width),
        _box_line('1. Configuracion general de la figura', width),
        _box_line('2. Elegir subplot activo', width),
        _box_line('3. Editar subplot activo (trazas, ejes, textos, etc.)', width),
        _box_sep(width),
        _box_line('4. Redibujar figura', width),
        _box_line(f'5. Guardar (JSON + CSV + PNG) [{base}]', width),
        _box_line('6. Exportar imagen (png/eps/pdf/svg)', width),
        _box_line('7. Aplicar formato editorial / preset cosmetico', width),
        _box_line('8. Separar / recomponer figuras', width),
        _box_line('9. Salir', width),
        _box_sep(width),
    ]
    return '\n'.join(lines)

def _menu_subplot(fig, active_ax, active_idx):
    while True:
        print(f"\n  ── Subplot activo: {active_idx} ──  '{active_ax.get_title()}'")
        print('   1. Título/xlabel/ylabel (texto + fuente)')
        print('   2. Límites y escalas')
        print('   3. Ticks (fontsize, rotación, dirección)')
        print('   4. Leyenda')
        print('   5. Líneas de referencia (vlines/hlines)')
        print('   6. Grid / Spines / Fondo')
        print('   7. Trazas (líneas de datos)')
        print('   8. Barras')
        print('   9. Scatters')
        print('  10. Textos / Anotaciones (+ recuadros)')
        print('  11. Guardar este subplot como figura individual')
        print('  12. Redibujar   13. Volver')
        op = input('  Opción: ').strip()
        if   op == '1':  _menu_labels(active_ax, fig)
        elif op == '2':  _menu_limits_scales(active_ax, fig)
        elif op == '3':  _menu_ticks(active_ax, fig)
        elif op == '4':  _menu_legend(active_ax, fig)
        elif op == '5':  _menu_reflines(active_ax, fig)
        elif op == '6':  _menu_grid_spines_bg(active_ax, fig)
        elif op == '7':  _menu_lines(active_ax, fig)
        elif op == '8':  _menu_bars(active_ax, fig)
        elif op == '9':  _menu_scatters(active_ax, fig)
        elif op == '10': _menu_texts(active_ax, fig)
        elif op == '11':
            base_filename = str(getattr(fig, '_fe_base_filename', 'figure'))
            size_mode = _prompt('  size_mode (autosize/keep_size)', 'autosize').strip().lower()
            include_suptitle = _prompt_yesno('  ¿Conservar suptitle global?', default=False)
            attach_shared_legend = _prompt_yesno('  ¿Adjuntar metadata de leyenda compartida si este subplot no la tiene?', default=True)
            show_shared_legend = False
            if attach_shared_legend:
                show_shared_legend = _prompt_yesno('  ¿Mostrar esa leyenda heredada por defecto al cargar la figura individual?', default=False)
            res = _save_subplot_as_individual(fig, active_idx, base_filename=base_filename,
                                              size_mode=size_mode, include_suptitle=include_suptitle,
                                              attach_shared_legend=attach_shared_legend,
                                              show_shared_legend=show_shared_legend)
            if res:
                print(f'  Subplot guardado: {res}.json / .csv / .png')
        elif op == '12': _refresh(fig)
        elif op == '13': return
        else: print('  Opción inválida.')

def edit_cosmetics(fig, base_filename: str = 'figure'):
    _enable_interactive_mode_for_editor()
    _refresh(fig, pause=0.05)
    base_filename  = str(getattr(fig, '_fe_base_filename', base_filename))
    axes0 = _data_axes(fig)
    if axes0:
        saved_idx = getattr(fig, '_fe_active_idx', 0)
        try:
            saved_idx = int(saved_idx)
        except Exception:
            saved_idx = 0
        if saved_idx < 0 or saved_idx >= len(axes0):
            saved_idx = 0
        active_idx = saved_idx
        active_ax = axes0[active_idx]
    else:
        active_ax = None
        active_idx = None
    while True:
        axes = _data_axes(fig)
        if axes:
            if active_idx is None or active_idx >= len(axes):
                active_idx = 0
            active_ax = axes[active_idx]
        else:
            active_ax = None
            active_idx = None
        print(_render_main_banner(active_idx, active_ax, base_filename))
        op = input('  Opción: ').strip()
        if op == '1':
            _menu_general(fig)
        elif op == '2':
            if not axes:
                print('  No hay subplots editables.')
            else:
                active_ax, active_idx = _pick_axis(fig)
                try:
                    fig._fe_active_idx = active_idx
                except Exception:
                    pass
        elif op == '3':
            if not axes or active_ax is None:
                print('  No hay subplots editables.')
            else:
                _menu_subplot(fig, active_ax, active_idx)
        elif op == '4':
            _refresh(fig)
            print('  Figura redibujada.')
        elif op == '5':
            nb = input(f'  Nombre base [{base_filename}] (Enter=mantener): ').strip()
            if nb:
                base_filename = str(_base_path(nb))
            save_figure_data(fig, base_filename, save_png=True)
            paths = [Path(str(_base_path(base_filename)) + ext) for ext in ('.json', '.csv', '.png')]
            missing = [str(p) for p in paths if not p.exists()]
            if missing:
                print('  Advertencia: faltan archivos tras guardar:')
                for p in missing:
                    print(f'    - {p}')
            else:
                prefs = _get_export_prefs(fig)
                print('  Verificación OK:')
                for p in paths:
                    print(f'    - {p.name} ({p.stat().st_size} bytes)')
                print(f"  PNG guardado con bbox={prefs['bbox_mode']} | autocrop={'on' if prefs['autocrop_white'] else 'off'}")
            try:
                fig._fe_base_filename = base_filename
            except Exception:
                pass
        elif op == '6':
            fmt = _prompt('Formato (png/eps/pdf/svg)', 'png')
            dpi = _prompt_float('DPI (solo raster)', 300)
            prefs = _get_export_prefs(fig)
            bbox_mode = _prompt('Borde exportado (exact/tight/content)', prefs['bbox_mode']).strip().lower()
            pad_inches = _prompt_float('pad_inches (si bbox=tight/content)', prefs['pad_inches'])
            autocrop = prefs['autocrop_white']
            if fmt.lower() == 'png':
                ac = _prompt('autocrop_white PNG (on/off)', 'on' if prefs['autocrop_white'] else 'off').strip().lower()
                autocrop = (ac == 'on')
            nb = input(f'  Nombre base [{base_filename}] (Enter=mantener): ').strip()
            if nb:
                base_filename = str(_base_path(nb))
            out = str(_base_path(base_filename)) + '.' + fmt
            try:
                local_prefs = dict(prefs)
                if bbox_mode.startswith('t'):
                    _mode = 'tight'
                elif bbox_mode.startswith('c'):
                    _mode = 'content'
                elif bbox_mode.startswith('e'):
                    _mode = 'exact'
                else:
                    _mode = prefs.get('bbox_mode', 'content')
                local_prefs.update({'bbox_mode': _mode, 'pad_inches': pad_inches, 'autocrop_white': autocrop})
                _save_figure_image(fig, out, dpi=dpi, prefs=local_prefs)
                print(f'  Exportado: {out}')
            except Exception as e:
                print(f'  Error: {e}')
        elif op == '7':
            _menu_cosmetic_presets(fig)
        elif op == '8':
            maybe_fig = _menu_split_recompose(fig, base_filename=base_filename)
            if maybe_fig is not None and maybe_fig is not fig:
                return maybe_fig
        elif op == '9':
            _refresh(fig)
            print('  Saliendo del editor.')
            return fig
        else:
            print('  Opción inválida.')

# ============================================================================
#  V38 - presets robustos: leyenda automática, restaurar original y referencia
# ============================================================================
_FORMAT_VERSION = 38

def _legend_entry_count(ax):
    leg = ax.get_legend()
    if leg is None:
        return 0
    try:
        return len(leg.get_texts())
    except Exception:
        return 0

def _legend_data_overlap_score(ax, leg=None):
    try:
        fig = ax.figure
        if leg is None:
            leg = ax.get_legend()
        if leg is None:
            return 0
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        bbox = leg.get_window_extent(renderer=renderer).expanded(1.02, 1.08)
        score = 0
        for ln in ax.get_lines():
            if getattr(ln, '_fe_refline', None) or not ln.get_visible():
                continue
            x = np.asarray(ln.get_xdata(), dtype=float)
            y = np.asarray(ln.get_ydata(), dtype=float)
            if x.size == 0 or y.size == 0:
                continue
            pts = ax.transData.transform(np.column_stack([x, y]))
            inside = ((pts[:,0] >= bbox.x0) & (pts[:,0] <= bbox.x1) &
                      (pts[:,1] >= bbox.y0) & (pts[:,1] <= bbox.y1))
            score += int(np.count_nonzero(inside))
        return score
    except Exception:
        return 999999

def _set_legend_outside_right(ax, preset=None, ncol=1):
    leg = ax.get_legend()
    if leg is None:
        return None
    handles, labels = ax.get_legend_handles_labels()
    old_labels = [t.get_text() for t in leg.get_texts()]
    if old_labels:
        pairs = [(h, l) for h, l in zip(handles, labels) if l in old_labels]
        if pairs:
            handles, labels = zip(*pairs)
    title = ''
    try:
        title = leg.get_title().get_text()
    except Exception:
        pass
    try:
        leg.remove()
    except Exception:
        pass
    new_leg = ax.legend(handles, labels, title=title, loc='center left',
                        bbox_to_anchor=(1.02, 0.5), borderaxespad=0.0,
                        frameon=bool((preset or {}).get('legend_frame', True)),
                        ncol=int(ncol))
    try:
        ax._fe_legend_placement = 'outside_right_auto'
    except Exception:
        pass
    if preset is not None:
        _apply_preset_to_legend(ax, preset)
    return new_leg

def _auto_fix_legends_after_preset(fig, preset=None, mode='auto'):
    mode = str(mode or 'auto').lower().strip()
    if mode in {'none', 'off', 'no'}:
        return fig
    axes = _data_axes(fig)
    any_outside = False
    for ax in axes:
        leg = ax.get_legend()
        if leg is None:
            continue
        n_entries = _legend_entry_count(ax)
        initial_score = _legend_data_overlap_score(ax, leg)
        loaded = n_entries >= 6
        if mode in {'outside', 'outside_right'} or loaded or initial_score > 0:
            any_outside = True
            _set_legend_outside_right(ax, preset=preset, ncol=1)
    if any_outside:
        try:
            w, h = fig.get_size_inches()
            fig.set_size_inches(max(float(w) + 1.15, 4.6), h, forward=True)
        except Exception:
            pass
        try:
            sp = fig.subplotpars
            left = max(0.10, min(float(getattr(sp, 'left', 0.16)), 0.22))
            bottom = max(0.12, min(float(getattr(sp, 'bottom', 0.16)), 0.22))
            top = min(0.95, max(float(getattr(sp, 'top', 0.92)), 0.90))
            fig.subplots_adjust(left=left, right=0.74, bottom=bottom, top=top)
        except Exception:
            pass
    _refresh(fig)
    return fig

_apply_cosmetic_preset_v37 = apply_cosmetic_preset

def apply_cosmetic_preset(fig, preset_name='prb_technical', apply_colors=True, apply_layout=True,
                          apply_linewidths=True, apply_marker_sizes=True, apply_legend=True,
                          legend_policy='auto'):
    key = str(preset_name).strip().lower()
    preset = _FIGURE_STYLE_PRESETS.get(key)
    fig = _apply_cosmetic_preset_v37(fig, preset_name=preset_name, apply_colors=apply_colors,
                                     apply_layout=apply_layout, apply_linewidths=apply_linewidths,
                                     apply_marker_sizes=apply_marker_sizes, apply_legend=apply_legend)
    if apply_legend:
        _auto_fix_legends_after_preset(fig, preset=preset, mode=legend_policy)
    return fig

def _apply_reference_json_all_cosmetics(fig, ref_path):
    ref = _load_reference_layout_from_json(ref_path)
    _apply_reference_layout(fig, ref, copy_figsize=True, copy_subplotpars=True,
                            copy_axes_positions=True, copy_export_prefs=True)
    diffs = _build_cosmetic_diffs(fig, ref)
    _apply_cosmetic_diffs(fig, ref, diffs)
    _refresh(fig)
    return fig

def restore_original_format(fig):
    ref = getattr(fig, '_fe_original_json_path', None) or getattr(fig, '_fe_source_json_path', None)
    if not ref:
        raise RuntimeError('No encuentro el JSON original asociado a esta figura. Cargala con load_figure(...) o indicá una referencia externa.')
    return _apply_reference_json_all_cosmetics(fig, ref)

def apply_format_from_saved_figure(fig, reference_json_path):
    return _apply_reference_json_all_cosmetics(fig, reference_json_path)

def _menu_cosmetic_presets(fig):
    keys = list(_FIGURE_STYLE_PRESETS.keys())
    while True:
        print('\n  ── Formatos editoriales / presets cosméticos ──')
        for i, k in enumerate(keys, start=1):
            pr = _FIGURE_STYLE_PRESETS[k]
            print(f'   {i}. {pr.get("label", k)}  [{k}]')
            print(f'      {pr.get("description", "")}')
        print(f'   {len(keys)+1}. Restaurar formato ORIGINAL cargado')
        print(f'   {len(keys)+2}. Cargar formato desde otra figura guardada (.json)')
        print(f'   {len(keys)+3}. Volver')
        op = input('  Opción: ').strip()
        if not op:
            return fig
        try:
            idx = int(op)
        except Exception:
            print('  Opción inválida.'); continue
        if 1 <= idx <= len(keys):
            key = keys[idx-1]
            apply_colors = _prompt_yesno('  ¿Aplicar también paleta de colores del preset?', default=True)
            apply_layout = _prompt_yesno('  ¿Aplicar tamaño/márgenes del preset?', default=True)
            legend_policy = _prompt('  Política de leyenda (auto/outside/none)', 'auto').strip().lower()
            try:
                apply_cosmetic_preset(fig, key, apply_colors=apply_colors, apply_layout=apply_layout,
                                      legend_policy=legend_policy)
                print(f'  Preset aplicado: {_FIGURE_STYLE_PRESETS[key].get("label", key)}')
            except Exception as e:
                print(f'  Error aplicando preset: {e}')
            return fig
        elif idx == len(keys)+1:
            try:
                restore_original_format(fig)
                print('  Formato original restaurado desde el JSON cargado.')
            except Exception as e:
                print(f'  No se pudo restaurar el original: {e}')
            return fig
        elif idx == len(keys)+2:
            ref = input('  Ruta al JSON de referencia: ').strip().strip('"')
            if not ref:
                print('  Operación cancelada.'); return fig
            try:
                apply_format_from_saved_figure(fig, ref)
                print('  Formato copiado desde la figura de referencia.')
            except Exception as e:
                print(f'  No se pudo copiar el formato: {e}')
            return fig
        elif idx == len(keys)+3:
            return fig
        else:
            print('  Opción inválida.')


# ============================================================================
#  V39 - presets más diferenciados + colores consistentes línea/símbolo
# ============================================================================
_FORMAT_VERSION = 39

_FIGURE_STYLE_PRESETS.update({
    "nature_minimal": {"label": "Nature-like Minimal Air", "description": "Muy blanco, sin grilla, sans fina; paleta Okabe-Ito limpia.", "figsize": (4.20, 3.15), "dpi": 300, "facecolor": "white", "axes_facecolor": "white", "fontfamily": "DejaVu Sans", "title_size": 9.0, "label_size": 9.2, "tick_size": 7.8, "legend_size": 7.2, "legend_title_size": 7.6, "line_width": 1.45, "marker_size": 4.8, "spine_width": 0.65, "tick_width": 0.65, "tick_length": 3.0, "tick_direction": "out", "grid": {"visible": False}, "legend_frame": False, "palette": ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00", "#56B4E9", "#000000", "#F0E442"], "margins": {"left": 0.16, "right": 0.97, "bottom": 0.16, "top": 0.94, "wspace": 0.28, "hspace": 0.28}, "export": {"bbox_mode": "content", "pad_inches": 0.018, "autocrop_white": False}, "marker_alpha": 0.48, "line_alpha": 1.0},
    "prl_compact": {"label": "PRL Compact Mono", "description": "Compacto, serif, casi monocromo; diferencias por linestyle/marker más que por color.", "figsize": (4.05, 2.85), "dpi": 300, "facecolor": "white", "axes_facecolor": "white", "fontfamily": "DejaVu Serif", "title_size": 8.2, "label_size": 8.6, "tick_size": 7.2, "legend_size": 6.8, "legend_title_size": 7.1, "line_width": 1.15, "marker_size": 4.0, "spine_width": 0.85, "tick_width": 0.85, "tick_length": 3.5, "tick_direction": "in", "grid": {"visible": False}, "legend_frame": False, "palette": ["#000000", "#555555", "#888888", "#222222", "#6B6B6B", "#A0A0A0", "#333333", "#777777"], "linestyles_cycle": ["-", "--", "-.", ":", (0, (5, 1)), (0, (3, 1, 1, 1)), (0, (1, 1)), (0, (4, 2))], "margins": {"left": 0.16, "right": 0.98, "bottom": 0.17, "top": 0.95, "wspace": 0.22, "hspace": 0.22}, "export": {"bbox_mode": "content", "pad_inches": 0.012, "autocrop_white": False}, "marker_alpha": 0.45, "line_alpha": 1.0},
    "prb_technical": {"label": "PRB Technical Grid", "description": "Serif técnico, caja completa, ticks internos y grilla punteada muy tenue.", "figsize": (4.45, 3.35), "dpi": 300, "facecolor": "white", "axes_facecolor": "#FFFFFF", "fontfamily": "DejaVu Serif", "title_size": 9.8, "label_size": 9.8, "tick_size": 8.2, "legend_size": 7.6, "legend_title_size": 8.2, "line_width": 1.55, "marker_size": 5.0, "spine_width": 1.0, "tick_width": 0.95, "tick_length": 4.0, "tick_direction": "in", "grid": {"visible": True, "color": "0.82", "linestyle": ":", "linewidth": 0.55, "alpha": 0.80}, "legend_frame": True, "legend_framealpha": 0.92, "palette": ["#1B4F72", "#A04000", "#117A65", "#6C3483", "#922B21", "#4D5656", "#9A7D0A", "#148F77"], "margins": {"left": 0.16, "right": 0.97, "bottom": 0.16, "top": 0.93, "wspace": 0.30, "hspace": 0.30}, "export": {"bbox_mode": "content", "pad_inches": 0.018, "autocrop_white": False}, "marker_alpha": 0.50, "line_alpha": 1.0},
    "apl_modern": {"label": "APL Modern Light", "description": "Sans moderno, fondo levemente gris, grilla blanca suave, colores vivos.", "figsize": (4.60, 3.30), "dpi": 300, "facecolor": "white", "axes_facecolor": "#F7F8FA", "fontfamily": "DejaVu Sans", "title_size": 10.6, "label_size": 10.2, "tick_size": 8.5, "legend_size": 7.9, "legend_title_size": 8.4, "line_width": 1.85, "marker_size": 5.4, "spine_width": 0.9, "tick_width": 0.85, "tick_length": 3.3, "tick_direction": "out", "grid": {"visible": True, "color": "white", "linestyle": "-", "linewidth": 1.05, "alpha": 1.0}, "legend_frame": True, "legend_framealpha": 0.96, "palette": ["#0077BB", "#EE7733", "#33BBEE", "#CC3311", "#009988", "#AA4499", "#BBBBBB", "#4477AA"], "margins": {"left": 0.15, "right": 0.97, "bottom": 0.15, "top": 0.91, "wspace": 0.30, "hspace": 0.30}, "export": {"bbox_mode": "content", "pad_inches": 0.018, "autocrop_white": False}, "marker_alpha": 0.42, "line_alpha": 1.0},
    "review_bold": {"label": "Review Bold Wide", "description": "Muy visual: formato ancho, labels grandes, líneas gruesas y alto contraste.", "figsize": (5.80, 3.75), "dpi": 300, "facecolor": "white", "axes_facecolor": "white", "fontfamily": "DejaVu Sans", "title_size": 13.0, "label_size": 12.2, "tick_size": 9.8, "legend_size": 9.0, "legend_title_size": 9.6, "line_width": 2.45, "marker_size": 6.5, "spine_width": 1.25, "tick_width": 1.1, "tick_length": 4.5, "tick_direction": "out", "grid": {"visible": True, "color": "0.86", "linestyle": "--", "linewidth": 0.75, "alpha": 0.80}, "legend_frame": True, "legend_framealpha": 0.97, "palette": ["#005F73", "#CA6702", "#0A9396", "#AE2012", "#6A4C93", "#4D908E", "#9B2226", "#577590"], "margins": {"left": 0.13, "right": 0.97, "bottom": 0.15, "top": 0.89, "wspace": 0.32, "hspace": 0.32}, "export": {"bbox_mode": "content", "pad_inches": 0.020, "autocrop_white": False}, "marker_alpha": 0.40, "line_alpha": 1.0},
})

_load_figure_v38 = load_figure

def load_figure(filename, show: bool = True):
    fig = _load_figure_v38(filename, show=show)
    try:
        jp = Path(filename)
        if jp.suffix.lower() != '.json': jp = jp.with_suffix('.json')
        fig._fe_source_json_path = str(jp)
        fig._fe_original_json_path = str(jp)
    except Exception: pass
    return fig

def _is_marker_only_line(ln):
    try:
        ls = str(ln.get_linestyle()).lower(); mk = str(ln.get_marker()).lower()
        return ls in {'none', ' ', ''} and mk not in {'none', '', ' ', 'null'}
    except Exception: return False

def _is_model_curve_line(ln):
    try: return str(ln.get_linestyle()).lower() not in {'none', ' ', ''}
    except Exception: return True

def _paired_data_line_groups(ax):
    lines = [ln for ln in ax.get_lines() if not getattr(ln, '_fe_refline', None)]
    groups = []; i = 0
    while i < len(lines):
        if _is_marker_only_line(lines[i]) and i + 1 < len(lines) and _is_model_curve_line(lines[i+1]):
            groups.append([lines[i], lines[i+1]]); i += 2
        else:
            groups.append([lines[i]]); i += 1
    return groups

def _apply_group_color_and_style(ax, preset, apply_colors=True, apply_linewidths=True, apply_marker_sizes=True):
    palette = list(preset.get('palette', [])); linestyles = list(preset.get('linestyles_cycle', []))
    for gi, group in enumerate(_paired_data_line_groups(ax)):
        color = palette[gi % len(palette)] if (apply_colors and palette) else None
        linestyle = linestyles[gi % len(linestyles)] if linestyles else None
        for ln in group:
            try:
                if color is not None:
                    ln.set_color(color); ln.set_markerfacecolor(color); ln.set_markeredgecolor(color)
                if apply_linewidths and _is_model_curve_line(ln):
                    ln.set_linewidth(float(preset.get('line_width', 1.3)))
                    if linestyle is not None: ln.set_linestyle(linestyle)
                elif apply_linewidths and _is_marker_only_line(ln):
                    ln.set_linewidth(0.0)
                if apply_marker_sizes:
                    ln.set_markersize(float(preset.get('marker_size', 4.0)))
                    ln.set_markeredgewidth(max(0.6, float(preset.get('line_width', 1.3))*0.55))
                if _is_marker_only_line(ln) and preset.get('marker_alpha') is not None:
                    ln.set_alpha(float(preset.get('marker_alpha')))
                elif _is_model_curve_line(ln) and preset.get('line_alpha') is not None:
                    ln.set_alpha(float(preset.get('line_alpha')))
            except Exception: pass

def _rebuild_legend_preserving_visible_labels(ax, preset=None):
    leg = ax.get_legend()
    if leg is None: return None
    old_labels = [t.get_text() for t in leg.get_texts()]
    title = ''
    try: title = leg.get_title().get_text()
    except Exception: pass
    handles, labels = ax.get_legend_handles_labels()
    label_to_handle = {}
    for h, l in zip(handles, labels):
        sl = str(l or '')
        if sl.startswith('_') or sl.lower().startswith('line') or not sl: continue
        label_to_handle[sl] = h
    ordered = old_labels if old_labels else list(label_to_handle.keys())
    new_pairs = [(label_to_handle[l], l) for l in ordered if l in label_to_handle]
    if not new_pairs: return leg
    outside = bool(getattr(ax, '_fe_legend_placement', '') == 'outside_right_auto')
    try: leg.remove()
    except Exception: pass
    hs, ls = zip(*new_pairs)
    if outside:
        new_leg = ax.legend(list(hs), list(ls), title=title, loc='center left', bbox_to_anchor=(1.02, 0.5), borderaxespad=0.0, frameon=bool((preset or {}).get('legend_frame', True)))
    else:
        new_leg = ax.legend(list(hs), list(ls), title=title, frameon=bool((preset or {}).get('legend_frame', True)))
    if preset is not None: _apply_preset_to_legend(ax, preset)
    return new_leg

def _set_legend_outside_right(ax, preset=None, ncol=1):
    leg = ax.get_legend()
    if leg is None: return None
    try: ax._fe_legend_placement = 'outside_right_auto'
    except Exception: pass
    return _rebuild_legend_preserving_visible_labels(ax, preset=preset)

_apply_cosmetic_preset_v38 = apply_cosmetic_preset

def apply_cosmetic_preset(fig, preset_name='prb_technical', apply_colors=True, apply_layout=True,
                          apply_linewidths=True, apply_marker_sizes=True, apply_legend=True,
                          legend_policy='auto'):
    key = str(preset_name).strip().lower()
    if key not in _FIGURE_STYLE_PRESETS:
        raise ValueError(f"Preset desconocido: {preset_name}. Opciones: {', '.join(_FIGURE_STYLE_PRESETS)}")
    preset = _FIGURE_STYLE_PRESETS[key]
    fig = _apply_cosmetic_preset_v37(fig, preset_name=key, apply_colors=False, apply_layout=apply_layout, apply_linewidths=False, apply_marker_sizes=False, apply_legend=apply_legend)
    for ax in _data_axes(fig):
        _apply_group_color_and_style(ax, preset, apply_colors=apply_colors, apply_linewidths=apply_linewidths, apply_marker_sizes=apply_marker_sizes)
        if apply_legend: _rebuild_legend_preserving_visible_labels(ax, preset=preset)
    if apply_legend:
        _auto_fix_legends_after_preset(fig, preset=preset, mode=legend_policy)
        for ax in _data_axes(fig): _rebuild_legend_preserving_visible_labels(ax, preset=preset)
    try: fig._fe_cosmetic_preset = key
    except Exception: pass
    _refresh(fig)
    return fig

# ============================================================================
#  V40 - presets realmente diferenciados + combinaciones color/marcador únicas
# ============================================================================
_FORMAT_VERSION = 40

# Paletas largas y marcadores diferenciados. La intención es que incluso con 8-12
# series no se repita la combinación color+marker+linestyle.
_DISTINCT_PALETTE_12 = [
    "#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9",
    "#000000", "#A6761D", "#1B9E77", "#D95F02", "#7570B3", "#E7298A",
]
_BOLD_PALETTE_14 = [
    "#005F73", "#CA6702", "#0A9396", "#AE2012", "#6A4C93", "#4D908E",
    "#9B2226", "#577590", "#264653", "#F4A261", "#2A9D8F", "#E76F51",
    "#3A0CA3", "#7209B7",
]
_MARKERS_12 = ["o", "s", "^", "D", "v", "P", "X", "<", ">", "h", "*", "8"]
_LINESTYLES_10 = ["-", "--", "-.", ":", (0, (5, 1)), (0, (3, 1, 1, 1)), (0, (1, 1)), (0, (6, 2)), (0, (2, 2)), (0, (8, 2, 2, 2))]

_FIGURE_STYLE_PRESETS.update({
    "nature_minimal": {
        "label": "Nature-like Square Air",
        "description": "Casi cuadrado, mucho blanco, sin grilla, sans fina; pensado para panel limpio de una columna.",
        "figsize": (3.55, 3.45), "dpi": 300,
        "facecolor": "white", "axes_facecolor": "white", "fontfamily": "DejaVu Sans",
        "title_size": 8.5, "label_size": 9.0, "tick_size": 7.6,
        "legend_size": 7.0, "legend_title_size": 7.4,
        "line_width": 1.25, "marker_size": 4.4, "spine_width": 0.65,
        "tick_width": 0.65, "tick_length": 2.8, "tick_direction": "out",
        "grid": {"visible": False}, "legend_frame": False,
        "palette": _DISTINCT_PALETTE_12, "markers_cycle": _MARKERS_12,
        "linestyles_cycle": ["-"],
        "margins": {"left": 0.18, "right": 0.96, "bottom": 0.17, "top": 0.94, "wspace": 0.28, "hspace": 0.28},
        "export": {"bbox_mode": "content", "pad_inches": 0.015, "autocrop_white": False},
        "marker_alpha": 0.42, "line_alpha": 1.0, "legend_policy_default": "outside_right",
    },
    "prl_compact": {
        "label": "PRL Compact Horizontal",
        "description": "Muy horizontal y sobrio; serif, ticks internos, alta densidad; combina color discreto + linestyle.",
        "figsize": (4.65, 2.55), "dpi": 300,
        "facecolor": "white", "axes_facecolor": "white", "fontfamily": "DejaVu Serif",
        "title_size": 8.0, "label_size": 8.4, "tick_size": 7.0,
        "legend_size": 6.5, "legend_title_size": 6.9,
        "line_width": 1.05, "marker_size": 3.6, "spine_width": 0.85,
        "tick_width": 0.85, "tick_length": 3.8, "tick_direction": "in",
        "grid": {"visible": False}, "legend_frame": False,
        "palette": ["#000000", "#4D4D4D", "#0072B2", "#D55E00", "#009E73", "#CC79A7", "#666666", "#E69F00", "#56B4E9", "#A6761D"],
        "markers_cycle": ["o", "s", "^", "D", "v", "P", "X", "<", ">", "h"],
        "linestyles_cycle": _LINESTYLES_10,
        "margins": {"left": 0.13, "right": 0.98, "bottom": 0.20, "top": 0.94, "wspace": 0.18, "hspace": 0.18},
        "export": {"bbox_mode": "content", "pad_inches": 0.010, "autocrop_white": False},
        "marker_alpha": 0.45, "line_alpha": 1.0, "legend_policy_default": "outside_right",
    },
    "prb_technical": {
        "label": "PRB Technical Box",
        "description": "Relación intermedia, caja completa, ticks internos, grilla punteada: estilo técnico para datos densos.",
        "figsize": (4.25, 3.35), "dpi": 300,
        "facecolor": "white", "axes_facecolor": "#FFFFFF", "fontfamily": "DejaVu Serif",
        "title_size": 9.4, "label_size": 9.6, "tick_size": 8.0,
        "legend_size": 7.3, "legend_title_size": 7.9,
        "line_width": 1.45, "marker_size": 4.8, "spine_width": 1.0,
        "tick_width": 0.95, "tick_length": 4.0, "tick_direction": "in",
        "grid": {"visible": True, "color": "0.82", "linestyle": ":", "linewidth": 0.55, "alpha": 0.75},
        "legend_frame": True, "legend_framealpha": 0.90,
        "palette": _DISTINCT_PALETTE_12, "markers_cycle": _MARKERS_12,
        "linestyles_cycle": ["-", "-", "-", "-", "-", "-", "-", "-", "--", "--", "--", "--"],
        "margins": {"left": 0.16, "right": 0.96, "bottom": 0.16, "top": 0.92, "wspace": 0.30, "hspace": 0.30},
        "export": {"bbox_mode": "content", "pad_inches": 0.018, "autocrop_white": False},
        "marker_alpha": 0.46, "line_alpha": 1.0, "legend_policy_default": "outside_right",
    },
    "apl_modern": {
        "label": "APL Modern Vertical Light",
        "description": "Más vertical, fondo gris suave, grilla blanca y sans moderna; muy distinto del PRL/PRB.",
        "figsize": (3.55, 4.55), "dpi": 300,
        "facecolor": "white", "axes_facecolor": "#F4F6F8", "fontfamily": "DejaVu Sans",
        "title_size": 10.5, "label_size": 10.2, "tick_size": 8.4,
        "legend_size": 7.7, "legend_title_size": 8.2,
        "line_width": 1.75, "marker_size": 5.3, "spine_width": 0.85,
        "tick_width": 0.8, "tick_length": 3.2, "tick_direction": "out",
        "grid": {"visible": True, "color": "white", "linestyle": "-", "linewidth": 1.15, "alpha": 1.0},
        "legend_frame": True, "legend_framealpha": 0.96,
        "palette": ["#0077BB", "#EE7733", "#33BBEE", "#CC3311", "#009988", "#AA4499", "#BBBBBB", "#4477AA", "#228833", "#EE3377", "#66CCEE", "#CCBB44"],
        "markers_cycle": ["o", "s", "^", "D", "v", "P", "X", "<", ">", "h", "*", "8"],
        "linestyles_cycle": ["-"],
        "margins": {"left": 0.19, "right": 0.95, "bottom": 0.12, "top": 0.94, "wspace": 0.30, "hspace": 0.30},
        "export": {"bbox_mode": "content", "pad_inches": 0.018, "autocrop_white": False},
        "marker_alpha": 0.40, "line_alpha": 1.0, "legend_policy_default": "outside_right",
    },
    "review_bold": {
        "label": "Review Bold Wide Poster",
        "description": "Muy ancho y visual; letras grandes, líneas gruesas, grilla marcada y combinaciones color+marker únicas.",
        "figsize": (6.40, 3.65), "dpi": 300,
        "facecolor": "white", "axes_facecolor": "#FFFFFF", "fontfamily": "DejaVu Sans",
        "title_size": 13.5, "label_size": 12.5, "tick_size": 10.0,
        "legend_size": 9.0, "legend_title_size": 9.8,
        "line_width": 2.35, "marker_size": 6.7, "spine_width": 1.25,
        "tick_width": 1.1, "tick_length": 4.6, "tick_direction": "out",
        "grid": {"visible": True, "color": "0.84", "linestyle": "--", "linewidth": 0.75, "alpha": 0.82},
        "legend_frame": True, "legend_framealpha": 0.97,
        "palette": _BOLD_PALETTE_14, "markers_cycle": _MARKERS_12,
        "linestyles_cycle": ["-", "-", "-", "-", "--", "--", "-.", "-.", ":", ":", (0, (5, 1)), (0, (3, 1, 1, 1))],
        "margins": {"left": 0.11, "right": 0.97, "bottom": 0.17, "top": 0.88, "wspace": 0.32, "hspace": 0.32},
        "export": {"bbox_mode": "content", "pad_inches": 0.020, "autocrop_white": False},
        "marker_alpha": 0.38, "line_alpha": 1.0, "legend_policy_default": "outside_right",
    },
})

def _safe_linestyle_value(ls):
    # Matplotlib acepta strings y tuplas offset-pattern. JSON/save suele tolerarlo via _jsonable.
    return ls

def _set_legend_handle_style(leg, label_to_line, label_to_marker, preset):
    if leg is None:
        return
    # Soporta versiones con legend_handles y legendHandles.
    handles = getattr(leg, 'legend_handles', None)
    if handles is None:
        handles = getattr(leg, 'legendHandles', [])
    texts = leg.get_texts() if hasattr(leg, 'get_texts') else []
    for h, t in zip(handles, texts):
        lab = t.get_text()
        src = label_to_line.get(lab) or label_to_marker.get(lab)
        if src is None:
            continue
        try:
            col = src.get_color()
            h.set_color(col)
            if hasattr(h, 'set_markerfacecolor'): h.set_markerfacecolor(col)
            if hasattr(h, 'set_markeredgecolor'): h.set_markeredgecolor(col)
            if hasattr(h, 'set_marker'): h.set_marker(src.get_marker() if hasattr(src, 'get_marker') else '')
            if hasattr(h, 'set_linestyle'): h.set_linestyle(src.get_linestyle() if hasattr(src, 'get_linestyle') else '-')
            if hasattr(h, 'set_linewidth'): h.set_linewidth(float(preset.get('line_width', 1.3)))
            if hasattr(h, 'set_markersize'): h.set_markersize(float(preset.get('marker_size', 4.0)) * 0.85)
        except Exception:
            pass

def _paired_data_series(ax):
    """Agrupa datos crudos marcador-only + curva asociada cuando aparecen en pares.
    Devuelve [{'marker': ln|None, 'curve': ln|None, 'label': str}, ...].
    """
    lines = [ln for ln in ax.get_lines() if not getattr(ln, '_fe_refline', None)]
    out = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if _is_marker_only_line(ln) and i + 1 < len(lines) and _is_model_curve_line(lines[i+1]):
            curve = lines[i+1]
            label = str(curve.get_label() or ln.get_label() or f"series{len(out)+1}")
            out.append({'marker': ln, 'curve': curve, 'label': label})
            i += 2
        else:
            label = str(ln.get_label() or f"series{len(out)+1}")
            if _is_marker_only_line(ln):
                out.append({'marker': ln, 'curve': None, 'label': label})
            else:
                out.append({'marker': None, 'curve': ln, 'label': label})
            i += 1
    return out

def _apply_series_style(ax, preset, apply_colors=True, apply_linewidths=True, apply_marker_sizes=True):
    palette = list(preset.get('palette', []))
    markers = list(preset.get('markers_cycle', _MARKERS_12))
    linestyles = list(preset.get('linestyles_cycle', ['-']))
    label_to_line = {}
    label_to_marker = {}
    for si, s in enumerate(_paired_data_series(ax)):
        color = palette[si % len(palette)] if (apply_colors and palette) else None
        marker = markers[si % len(markers)] if markers else None
        linestyle = _safe_linestyle_value(linestyles[si % len(linestyles)]) if linestyles else '-'
        for role in ('marker', 'curve'):
            ln = s.get(role)
            if ln is None:
                continue
            try:
                if color is not None:
                    ln.set_color(color)
                    ln.set_markerfacecolor(color)
                    ln.set_markeredgecolor(color)
                if marker is not None:
                    # Para curvas continuas, no agregamos marker si no lo tenían; para marker-only sí lo cambiamos.
                    if role == 'marker' or str(ln.get_marker()).lower() not in {'none', '', ' '}:
                        ln.set_marker(marker)
                if apply_linewidths:
                    if role == 'curve':
                        ln.set_linewidth(float(preset.get('line_width', 1.3)))
                        ln.set_linestyle(linestyle)
                    else:
                        ln.set_linestyle('None')
                        ln.set_linewidth(0.0)
                if apply_marker_sizes:
                    ln.set_markersize(float(preset.get('marker_size', 4.0)))
                    ln.set_markeredgewidth(max(0.55, float(preset.get('line_width', 1.3))*0.50))
                if role == 'marker' and preset.get('marker_alpha') is not None:
                    ln.set_alpha(float(preset.get('marker_alpha')))
                elif role == 'curve' and preset.get('line_alpha') is not None:
                    ln.set_alpha(float(preset.get('line_alpha')))
                if s.get('label') and not str(s.get('label')).lower().startswith('line'):
                    if role == 'curve': label_to_line[s['label']] = ln
                    if role == 'marker': label_to_marker[s['label']] = ln
            except Exception:
                pass
    return label_to_line, label_to_marker

def _build_legend_for_series(ax, preset=None, outside=False):
    # Orden y etiquetas: preferir etiquetas de curvas; eliminar line1/line3 de datos crudos.
    pairs = []
    for s in _paired_data_series(ax):
        label = str(s.get('label') or '')
        if not label or label.startswith('_') or label.lower().startswith('line'):
            continue
        h = s.get('curve') or s.get('marker')
        if h is not None:
            pairs.append((h, label))
    if not pairs:
        return ax.get_legend()
    old_title = ''
    old = ax.get_legend()
    if old is not None:
        try: old_title = old.get_title().get_text()
        except Exception: old_title = ''
        try: old.remove()
        except Exception: pass
    frameon = bool((preset or {}).get('legend_frame', True))
    ncol = int((preset or {}).get('legend_ncol', 1))
    if outside:
        leg = ax.legend([p[0] for p in pairs], [p[1] for p in pairs], title=old_title,
                        loc='center left', bbox_to_anchor=(1.02, 0.5), borderaxespad=0.0,
                        frameon=frameon, ncol=ncol)
        try: ax._fe_legend_placement = 'outside_right_auto'
        except Exception: pass
    else:
        leg = ax.legend([p[0] for p in pairs], [p[1] for p in pairs], title=old_title,
                        loc='best', frameon=frameon, ncol=ncol)
    if preset is not None:
        _apply_preset_to_legend(ax, preset)
    return leg

_apply_cosmetic_preset_v39 = apply_cosmetic_preset

def apply_cosmetic_preset(fig, preset_name='prb_technical', apply_colors=True, apply_layout=True,
                          apply_linewidths=True, apply_marker_sizes=True, apply_legend=True,
                          legend_policy='auto'):
    key = str(preset_name).strip().lower()
    if key not in _FIGURE_STYLE_PRESETS:
        raise ValueError(f"Preset desconocido: {preset_name}. Opciones: {', '.join(_FIGURE_STYLE_PRESETS)}")
    preset = _FIGURE_STYLE_PRESETS[key]
    # Primero aplica tipografías, tamaños, fondo, ticks, spines, grilla, export, etc.,
    # pero NO colores/linewidths para evitar coloreado línea-por-línea.
    fig = _apply_cosmetic_preset_v37(fig, preset_name=key, apply_colors=False, apply_layout=apply_layout,
                                     apply_linewidths=False, apply_marker_sizes=False, apply_legend=False)
    if apply_layout:
        try:
            fig.subplots_adjust(**(preset.get('margins', {}) or {}))
        except Exception:
            pass
    for ax in _data_axes(fig):
        label_to_line, label_to_marker = _apply_series_style(ax, preset, apply_colors=apply_colors,
                                                             apply_linewidths=apply_linewidths,
                                                             apply_marker_sizes=apply_marker_sizes)
        # La leyenda se reconstruye DESPUÉS de cambiar curvas/símbolos, para evitar handles viejos.
        if apply_legend:
            n_entries = len([s for s in _paired_data_series(ax) if not str(s.get('label','')).lower().startswith('line')])
            pol = str(legend_policy or 'auto').lower().strip()
            default_pol = str(preset.get('legend_policy_default', 'auto')).lower().strip()
            outside = pol in {'outside', 'outside_right'} or (pol == 'auto' and (default_pol in {'outside', 'outside_right'} or n_entries >= 5))
            _build_legend_for_series(ax, preset=preset, outside=outside)
            _set_legend_handle_style(ax.get_legend(), label_to_line, label_to_marker, preset)
    if apply_legend:
        # Ajuste de layout final para leyendas externas. Más generoso en formatos cargados.
        any_outside = any(bool(getattr(ax, '_fe_legend_placement', '') == 'outside_right_auto') for ax in _data_axes(fig))
        if any_outside and apply_layout:
            try:
                w, h = fig.get_size_inches()
                # No destruir la intención del preset: cada preset ya tiene aspecto distinto, solo sumar columna de leyenda.
                fig.set_size_inches(float(w) + max(0.95, 0.12 * len(_paired_data_series(_data_axes(fig)[0]))), float(h), forward=True)
            except Exception:
                pass
            try:
                sp = fig.subplotpars
                left = max(0.08, float(getattr(sp, 'left', 0.16)))
                bottom = max(0.10, float(getattr(sp, 'bottom', 0.16)))
                top = min(0.96, max(0.86, float(getattr(sp, 'top', 0.92))))
                fig.subplots_adjust(left=left, right=0.74, bottom=bottom, top=top)
            except Exception:
                pass
    try:
        prefs = _get_export_prefs(fig); prefs.update(preset.get('export', {}) or {}); _set_export_prefs(fig, prefs)
    except Exception: pass
    try: fig._fe_cosmetic_preset = key
    except Exception: pass
    _refresh(fig)
    return fig

# Menú v40: default de leyenda según preset, y recordatorio explícito de restauración/copia.
def _menu_cosmetic_presets(fig):
    keys = list(_FIGURE_STYLE_PRESETS.keys())
    while True:
        print('\n  ── Formatos editoriales / presets cosméticos ──')
        for i, k in enumerate(keys, start=1):
            pr = _FIGURE_STYLE_PRESETS[k]
            print(f'   {i}. {pr.get("label", k)}  [{k}]')
            print(f'      {pr.get("description", "")}')
        print(f'   {len(keys)+1}. Restaurar formato ORIGINAL cargado')
        print(f'   {len(keys)+2}. Cargar formato desde otra figura guardada (.json)')
        print(f'   {len(keys)+3}. Volver')
        op = input('  Opción: ').strip()
        if not op:
            return fig
        try: idx = int(op)
        except Exception:
            print('  Opción inválida.'); continue
        if 1 <= idx <= len(keys):
            key = keys[idx-1]
            default_pol = _FIGURE_STYLE_PRESETS[key].get('legend_policy_default', 'auto')
            apply_colors = _prompt_yesno('  ¿Aplicar también paleta de colores y marcadores del preset?', default=True)
            apply_layout = _prompt_yesno('  ¿Aplicar tamaño/márgenes/aspecto del preset?', default=True)
            legend_policy = _prompt('  Política de leyenda (auto/outside/none)', default_pol).strip().lower()
            try:
                apply_cosmetic_preset(fig, key, apply_colors=apply_colors, apply_layout=apply_layout,
                                      legend_policy=legend_policy)
                print(f'  Preset aplicado: {_FIGURE_STYLE_PRESETS[key].get("label", key)}')
            except Exception as e:
                print(f'  Error aplicando preset: {e}')
            return fig
        elif idx == len(keys)+1:
            try:
                restore_original_format(fig)
                print('  Formato original restaurado desde el JSON cargado.')
            except Exception as e:
                print(f'  No se pudo restaurar el original: {e}')
            return fig
        elif idx == len(keys)+2:
            ref = input('  Ruta al JSON de referencia: ').strip().strip('"')
            if not ref:
                print('  Operación cancelada.'); return fig
            try:
                apply_format_from_saved_figure(fig, ref)
                print('  Formato copiado desde la figura de referencia.')
            except Exception as e:
                print(f'  No se pudo copiar el formato: {e}')
            return fig
        elif idx == len(keys)+3:
            return fig
        else:
            print('  Opción inválida.')



# ============================================================================
#  V6 - motor de estilos editoriales robusto
#  - Leyenda con línea + símbolo
#  - Leyenda auto inside/outside según carga y colisión
#  - 7 presets claramente diferenciados
#  - Fondos suaves/dark y marcadores sólidos/abiertos
#  - Preserva menús y funciones previas
# ============================================================================
_FORMAT_VERSION = 40

from matplotlib.lines import Line2D as _FE_Line2D

# Paletas pensadas para mantener contraste y evitar colores iguales al fondo.
_FE_PALETTE_OKABE12 = [
    "#0072B2", "#D55E00", "#009E73", "#CC79A7",
    "#E69F00", "#56B4E9", "#000000", "#F0E442",
    "#882255", "#44AA99", "#999933", "#AA4499",
]
_FE_PALETTE_BOLD14 = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#9467bd",
    "#8c564b", "#7f7f7f", "#bcbd22", "#17becf",
    "#d62728", "#e377c2", "#393b79", "#637939",
    "#8c6d31", "#843c39",
]
_FE_PALETTE_PASTEL12 = [
    "#2E6F9E", "#D47A2A", "#579E55", "#8E63B6",
    "#A7655B", "#6C7074", "#B7A531", "#4FA7B7",
    "#C65F8A", "#5E8C6A", "#A17942", "#6D77B6",
]
_FE_PALETTE_DARK12 = [
    "#66D9EF", "#FFB86C", "#A6E22E", "#FF79C6",
    "#BD93F9", "#F1FA8C", "#8BE9FD", "#FF5555",
    "#50FA7B", "#C792EA", "#F78C6C", "#B2CCD6",
]
_FE_MARKERS_14 = ["o", "s", "^", "D", "v", "P", "X", "<", ">", "h", "*", "8", "p", "d"]
_FE_LINESTYLES_10 = ["-", "--", "-.", ":", (0, (5, 1)), (0, (3, 1, 1, 1)), (0, (1, 1)), (0, (4, 2)), (0, (6, 2, 1, 2)), (0, (2, 2, 6, 2))]
_FE_FILLS_SOLID = ["full"]
_FE_FILLS_OPEN = ["none"]
_FE_FILLS_MIXED = ["full", "none", "full", "none", "full", "none", "full", "none"]

_FIGURE_STYLE_PRESETS.update({
    "nature_minimal": {
        "label": "Nature-like Square Air",
        "description": "Cuadrado, mucho blanco, sin grilla, tipografía sans fina, símbolos abiertos.",
        "figsize": (4.25, 4.05), "dpi": 300,
        "facecolor": "white", "axes_facecolor": "white",
        "fontfamily": "DejaVu Sans",
        "title_size": 9.2, "label_size": 10.0, "tick_size": 8.0,
        "legend_size": 7.6, "legend_title_size": 8.0,
        "line_width": 1.45, "marker_size": 5.0, "spine_width": 0.75,
        "tick_width": 0.75, "tick_length": 3.2, "tick_direction": "out",
        "grid": {"visible": False},
        "legend_frame": False, "legend_framealpha": 0.0,
        "legend_facecolor": "white", "legend_edgecolor": "none", "legend_textcolor": "black",
        "palette": _FE_PALETTE_OKABE12, "markers_cycle": _FE_MARKERS_14,
        "linestyles_cycle": ["-"], "fillstyles_cycle": _FE_FILLS_OPEN,
        "marker_alpha": 0.82, "line_alpha": 1.0,
        "spine_color": "0.12", "text_color": "0.05", "tick_color": "0.05",
        "margins": {"left": 0.18, "right": 0.95, "bottom": 0.15, "top": 0.95, "wspace": 0.25, "hspace": 0.25},
        "export": {"bbox_mode": "content", "pad_inches": 0.018, "autocrop_white": False},
        "legend_policy_default": "auto",
    },
    "prl_compact": {
        "label": "PRL Compact Horizontal",
        "description": "Horizontal y sobrio; serif, ticks internos, alta densidad; mezcla color discreto + linestyle.",
        "figsize": (5.15, 2.75), "dpi": 300,
        "facecolor": "white", "axes_facecolor": "white",
        "fontfamily": "DejaVu Serif",
        "title_size": 8.0, "label_size": 8.8, "tick_size": 7.1,
        "legend_size": 6.7, "legend_title_size": 7.0,
        "line_width": 1.05, "marker_size": 3.8, "spine_width": 0.9,
        "tick_width": 0.9, "tick_length": 4.0, "tick_direction": "in",
        "grid": {"visible": False},
        "legend_frame": False, "legend_facecolor": "white", "legend_edgecolor": "none", "legend_textcolor": "black",
        "palette": ["#000000", "#595959", "#0072B2", "#D55E00", "#009E73", "#CC79A7", "#7A7A7A", "#E69F00", "#56B4E9", "#882255"],
        "markers_cycle": ["o", "s", "^", "D", "v", "<", ">", "h", "p", "X"],
        "linestyles_cycle": _FE_LINESTYLES_10, "fillstyles_cycle": _FE_FILLS_OPEN,
        "marker_alpha": 0.75, "line_alpha": 1.0,
        "spine_color": "0.0", "text_color": "0.0", "tick_color": "0.0",
        "margins": {"left": 0.12, "right": 0.98, "bottom": 0.20, "top": 0.95, "wspace": 0.18, "hspace": 0.18},
        "export": {"bbox_mode": "content", "pad_inches": 0.010, "autocrop_white": False},
        "legend_policy_default": "auto",
    },
    "prb_technical": {
        "label": "PRB Technical Box",
        "description": "Caja completa, serif, ticks internos, grilla punteada tenue; robusto para datos densos.",
        "figsize": (4.65, 3.65), "dpi": 300,
        "facecolor": "white", "axes_facecolor": "#FFFFFF",
        "fontfamily": "DejaVu Serif",
        "title_size": 9.6, "label_size": 10.0, "tick_size": 8.2,
        "legend_size": 7.6, "legend_title_size": 8.2,
        "line_width": 1.55, "marker_size": 5.1, "spine_width": 1.05,
        "tick_width": 0.95, "tick_length": 4.1, "tick_direction": "in",
        "grid": {"visible": True, "color": "0.82", "linestyle": ":", "linewidth": 0.58, "alpha": 0.78},
        "legend_frame": True, "legend_framealpha": 0.92,
        "legend_facecolor": "white", "legend_edgecolor": "0.35", "legend_textcolor": "black",
        "palette": ["#1B4F72", "#A04000", "#117A65", "#6C3483", "#922B21", "#4D5656", "#9A7D0A", "#148F77", "#7D3C98", "#B03A2E"],
        "markers_cycle": _FE_MARKERS_14,
        "linestyles_cycle": ["-", "-", "-", "-", "-", "-", "-", "-", "--", "--", "--", "--"],
        "fillstyles_cycle": _FE_FILLS_MIXED,
        "marker_alpha": 0.74, "line_alpha": 1.0,
        "spine_color": "0.10", "text_color": "0.05", "tick_color": "0.05",
        "margins": {"left": 0.16, "right": 0.96, "bottom": 0.16, "top": 0.93, "wspace": 0.30, "hspace": 0.30},
        "export": {"bbox_mode": "content", "pad_inches": 0.018, "autocrop_white": False},
        "legend_policy_default": "auto",
    },
    "apl_modern": {
        "label": "APL Modern Vertical Light",
        "description": "Más vertical, sans moderna, fondo gris muy suave, grilla blanca; estilo claramente distinto.",
        "figsize": (3.75, 4.85), "dpi": 300,
        "facecolor": "white", "axes_facecolor": "#F4F6F8",
        "fontfamily": "DejaVu Sans",
        "title_size": 10.8, "label_size": 10.5, "tick_size": 8.5,
        "legend_size": 7.9, "legend_title_size": 8.4,
        "line_width": 1.80, "marker_size": 5.5, "spine_width": 0.85,
        "tick_width": 0.85, "tick_length": 3.4, "tick_direction": "out",
        "grid": {"visible": True, "color": "white", "linestyle": "-", "linewidth": 1.15, "alpha": 1.0},
        "legend_frame": True, "legend_framealpha": 0.96,
        "legend_facecolor": "white", "legend_edgecolor": "0.80", "legend_textcolor": "black",
        "palette": ["#0077BB", "#EE7733", "#33BBEE", "#CC3311", "#009988", "#AA4499", "#BBBBBB", "#4477AA", "#228833", "#EE3377", "#66CCEE", "#CCBB44"],
        "markers_cycle": ["o", "s", "^", "D", "v", "P", "X", "<", ">", "h", "*", "8"],
        "linestyles_cycle": ["-"], "fillstyles_cycle": _FE_FILLS_SOLID,
        "marker_alpha": 0.72, "line_alpha": 1.0,
        "spine_color": "0.25", "text_color": "0.07", "tick_color": "0.10",
        "margins": {"left": 0.20, "right": 0.95, "bottom": 0.12, "top": 0.94, "wspace": 0.30, "hspace": 0.30},
        "export": {"bbox_mode": "content", "pad_inches": 0.018, "autocrop_white": False},
        "legend_policy_default": "auto",
    },
    "review_bold": {
        "label": "Review Bold Wide Poster",
        "description": "Muy ancho y visual; letras grandes, líneas gruesas, símbolos sólidos y alto contraste.",
        "figsize": (6.60, 3.75), "dpi": 300,
        "facecolor": "white", "axes_facecolor": "#FFFFFF",
        "fontfamily": "DejaVu Sans",
        "title_size": 13.5, "label_size": 12.8, "tick_size": 10.2,
        "legend_size": 9.2, "legend_title_size": 10.0,
        "line_width": 2.40, "marker_size": 6.9, "spine_width": 1.25,
        "tick_width": 1.15, "tick_length": 4.8, "tick_direction": "out",
        "grid": {"visible": True, "color": "0.84", "linestyle": "--", "linewidth": 0.78, "alpha": 0.82},
        "legend_frame": True, "legend_framealpha": 0.97,
        "legend_facecolor": "white", "legend_edgecolor": "0.40", "legend_textcolor": "black",
        "palette": _FE_PALETTE_BOLD14, "markers_cycle": _FE_MARKERS_14,
        "linestyles_cycle": ["-", "-", "-", "-", "--", "--", "-.", "-.", ":", ":", (0, (5, 1)), (0, (3, 1, 1, 1))],
        "fillstyles_cycle": _FE_FILLS_SOLID,
        "marker_alpha": 0.70, "line_alpha": 1.0,
        "spine_color": "0.06", "text_color": "0.02", "tick_color": "0.02",
        "margins": {"left": 0.11, "right": 0.97, "bottom": 0.17, "top": 0.88, "wspace": 0.32, "hspace": 0.32},
        "export": {"bbox_mode": "content", "pad_inches": 0.020, "autocrop_white": False},
        "legend_policy_default": "auto",
    },
    "soft_pastel": {
        "label": "Soft Pastel Warm",
        "description": "Fondo beige muy suave, grilla clara, colores desaturados y símbolos sólidos; legible para papers largos.",
        "figsize": (4.80, 3.65), "dpi": 300,
        "facecolor": "#FFF9EC", "axes_facecolor": "#FFF7E6",
        "fontfamily": "DejaVu Sans",
        "title_size": 10.5, "label_size": 10.3, "tick_size": 8.5,
        "legend_size": 7.9, "legend_title_size": 8.5,
        "line_width": 1.65, "marker_size": 5.3, "spine_width": 0.85,
        "tick_width": 0.85, "tick_length": 3.4, "tick_direction": "out",
        "grid": {"visible": True, "color": "#D8CDB8", "linestyle": ":", "linewidth": 0.75, "alpha": 0.75},
        "legend_frame": True, "legend_framealpha": 0.92,
        "legend_facecolor": "#FFF9EC", "legend_edgecolor": "#C7B99D", "legend_textcolor": "#2B2418",
        "palette": _FE_PALETTE_PASTEL12, "markers_cycle": _FE_MARKERS_14,
        "linestyles_cycle": ["-"], "fillstyles_cycle": _FE_FILLS_SOLID,
        "marker_alpha": 0.76, "line_alpha": 1.0,
        "spine_color": "#6A6252", "text_color": "#2B2418", "tick_color": "#2B2418",
        "margins": {"left": 0.16, "right": 0.95, "bottom": 0.15, "top": 0.92, "wspace": 0.30, "hspace": 0.30},
        "export": {"bbox_mode": "content", "pad_inches": 0.018, "autocrop_white": False},
        "legend_policy_default": "auto",
    },
    "dark_mode": {
        "label": "Dark Mode Presentation",
        "description": "Fondo oscuro no negro, colores brillantes, texto claro y símbolos con borde; pensado para charlas/slides.",
        "figsize": (5.30, 3.65), "dpi": 300,
        "facecolor": "#15202B", "axes_facecolor": "#1B2836",
        "fontfamily": "DejaVu Sans",
        "title_size": 11.0, "label_size": 10.6, "tick_size": 8.8,
        "legend_size": 9.2, "legend_title_size": 9.8,
        "line_width": 1.95, "marker_size": 5.8, "spine_width": 0.9,
        "tick_width": 0.85, "tick_length": 3.6, "tick_direction": "out",
        "grid": {"visible": True, "color": "#FFFFFF", "linestyle": ":", "linewidth": 0.55, "alpha": 0.22},
        "legend_frame": True, "legend_framealpha": 1.0,
        "legend_facecolor": "#0B1117", "legend_edgecolor": "#E5EEF8", "legend_textcolor": "#FFFFFF",
        "palette": _FE_PALETTE_DARK12, "markers_cycle": _FE_MARKERS_14,
        "linestyles_cycle": ["-"], "fillstyles_cycle": _FE_FILLS_SOLID,
        "marker_alpha": 0.88, "line_alpha": 1.0,
        "spine_color": "#DCE6F1", "text_color": "#F1F5F9", "tick_color": "#E4EDF7",
        "marker_edge_override": "#F1F5F9",
        "margins": {"left": 0.15, "right": 0.95, "bottom": 0.15, "top": 0.91, "wspace": 0.30, "hspace": 0.30},
        "export": {"bbox_mode": "content", "pad_inches": 0.018, "autocrop_white": False},
        "legend_policy_default": "auto",
    },
})

def _fe_cycle_value(seq, idx, default=None):
    try:
        if seq:
            return seq[idx % len(seq)]
    except Exception:
        pass
    return default

def _fe_is_visible_data_line(ln):
    try:
        return (not getattr(ln, "_fe_refline", None)) and bool(ln.get_visible())
    except Exception:
        return False

def _fe_style_text_color(fig, preset):
    color = preset.get("text_color", "black")
    for ax in _data_axes(fig):
        for txt in [ax.title, ax.xaxis.label, ax.yaxis.label]:
            try: txt.set_color(color)
            except Exception: pass
        for lab in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
            try: lab.set_color(preset.get("tick_color", color))
            except Exception: pass
    st = getattr(fig, "_suptitle", None)
    if st is not None:
        try: st.set_color(color)
        except Exception: pass

def _fe_apply_font_and_axes_style(fig, preset):
    try: fig.set_size_inches(*preset.get("figsize", fig.get_size_inches()), forward=True)
    except Exception: pass
    try: fig.set_dpi(float(preset.get("dpi", fig.dpi)))
    except Exception: pass
    try: fig.patch.set_facecolor(preset.get("facecolor", "white"))
    except Exception: pass
    _apply_font_to_text(getattr(fig, "_suptitle", None), preset.get("title_size"), preset.get("fontfamily"), "bold")
    for ax in _data_axes(fig):
        try: ax.set_facecolor(preset.get("axes_facecolor", "white"))
        except Exception: pass
        _apply_font_to_text(ax.title, preset.get("title_size"), preset.get("fontfamily"), "bold")
        _apply_font_to_text(ax.xaxis.label, preset.get("label_size"), preset.get("fontfamily"))
        _apply_font_to_text(ax.yaxis.label, preset.get("label_size"), preset.get("fontfamily"))
        try:
            ax.tick_params(axis="both", which="both",
                           labelsize=float(preset.get("tick_size", 8)),
                           width=float(preset.get("tick_width", 0.8)),
                           length=float(preset.get("tick_length", 3.0)),
                           direction=preset.get("tick_direction", "out"),
                           colors=preset.get("tick_color", preset.get("text_color", "black")))
        except Exception: pass
        for lab in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
            _apply_font_to_text(lab, preset.get("tick_size"), preset.get("fontfamily"))
        for sp in ax.spines.values():
            try:
                sp.set_linewidth(float(preset.get("spine_width", 0.8)))
                sp.set_color(preset.get("spine_color", "0.15"))
                sp.set_visible(True)
            except Exception: pass
        _apply_grid(ax, preset.get("grid", {"visible": False}))
    _fe_style_text_color(fig, preset)

def _fe_apply_one_series_style(series, idx, preset, apply_colors=True,
                               apply_linewidths=True, apply_marker_sizes=True):
    palette = list(preset.get("palette", []))
    markers = list(preset.get("markers_cycle", _FE_MARKERS_14))
    linestyles = list(preset.get("linestyles_cycle", ["-"]))
    fillstyles = list(preset.get("fillstyles_cycle", _FE_FILLS_SOLID))
    color = _fe_cycle_value(palette, idx, None) if apply_colors else None
    marker = _fe_cycle_value(markers, idx, "o")
    linestyle = _fe_cycle_value(linestyles, idx, "-")
    fill = _fe_cycle_value(fillstyles, idx, "full")
    line_width = float(preset.get("line_width", 1.4))
    marker_size = float(preset.get("marker_size", 4.8))
    marker_edge = preset.get("marker_edge_override", color if color is not None else None)
    marker_face = "none" if str(fill).lower() in {"none", "open", "hollow"} else color
    for role in ("marker", "curve"):
        ln = series.get(role)
        if ln is None:
            continue
        try:
            if color is not None:
                ln.set_color(color)
            if role == "curve":
                if apply_linewidths:
                    ln.set_linewidth(line_width)
                    ln.set_linestyle(linestyle)
                # Curvas de ajuste/modelo sin marker para evitar sobrecargar la figura.
                if str(ln.get_marker()).lower() not in {"none", "", " "}:
                    ln.set_marker("")
                if preset.get("line_alpha") is not None:
                    ln.set_alpha(float(preset.get("line_alpha")))
            else:
                ln.set_linestyle("None")
                ln.set_linewidth(0.0)
                if marker is not None:
                    ln.set_marker(marker)
                if color is not None:
                    ln.set_markeredgecolor(marker_edge or color)
                    ln.set_markerfacecolor(marker_face)
                try:
                    ln.set_fillstyle("none" if marker_face == "none" else "full")
                except Exception:
                    pass
                if preset.get("marker_alpha") is not None:
                    ln.set_alpha(float(preset.get("marker_alpha")))
            if apply_marker_sizes:
                ln.set_markersize(marker_size)
                ln.set_markeredgewidth(max(0.55, line_width * 0.48))
        except Exception:
            pass
    return {
        "color": color, "marker": marker, "linestyle": linestyle,
        "markerfacecolor": marker_face, "markeredgecolor": marker_edge or color,
        "linewidth": line_width, "markersize": marker_size,
        "fillstyle": fill,
    }

def _fe_style_all_series(ax, preset, apply_colors=True, apply_linewidths=True, apply_marker_sizes=True):
    styles_by_label = {}
    for idx, s in enumerate(_paired_data_series(ax)):
        lab = str(s.get("label", f"series{idx+1}"))
        st = _fe_apply_one_series_style(s, idx, preset, apply_colors=apply_colors,
                                        apply_linewidths=apply_linewidths,
                                        apply_marker_sizes=apply_marker_sizes)
        if lab and not lab.lower().startswith("line"):
            styles_by_label[lab] = st
    return styles_by_label

def _fe_legend_labels_and_styles(ax, styles_by_label):
    labels = []
    styles = []
    # Preferir el orden físico de pares experimentales/modelo.
    for s in _paired_data_series(ax):
        lab = str(s.get("label", ""))
        if lab and not lab.lower().startswith("line") and lab in styles_by_label and lab not in labels:
            labels.append(lab)
            styles.append(styles_by_label[lab])
    # Si la leyenda original tiene entradas adicionales, preservar orden donde sea posible.
    try:
        leg = ax.get_legend()
        if leg is not None:
            for t in leg.get_texts():
                lab = t.get_text()
                if lab and lab not in labels and lab in styles_by_label:
                    labels.append(lab)
                    styles.append(styles_by_label[lab])
    except Exception:
        pass
    return labels, styles

def _fe_make_legend_handle(style, preset):
    col = style.get("color") or "black"
    mfc = style.get("markerfacecolor", col)
    mec = style.get("markeredgecolor", col)
    # En fondos oscuros, borde blanco opcional, pero mantener color en línea.
    return _FE_Line2D(
        [0], [0],
        color=col,
        linestyle=style.get("linestyle", "-"),
        linewidth=float(style.get("linewidth", preset.get("line_width", 1.4))),
        marker=style.get("marker", "o"),
        markersize=float(style.get("markersize", preset.get("marker_size", 4.8))) * 0.88,
        markerfacecolor=mfc,
        markeredgecolor=mec,
        markeredgewidth=max(0.55, float(style.get("linewidth", preset.get("line_width", 1.4))) * 0.48),
    )

def _fe_apply_legend_cosmetics(leg, preset):
    if leg is None:
        return
    try:
        leg.set_frame_on(bool(preset.get("legend_frame", False)))
        fr = leg.get_frame()
        fr.set_alpha(float(preset.get("legend_framealpha", 1.0)))
        fr.set_facecolor(preset.get("legend_facecolor", "white"))
        fr.set_edgecolor(preset.get("legend_edgecolor", "0.35"))
        fr.set_linewidth(max(0.5, float(preset.get("spine_width", 0.8))*0.75))
    except Exception:
        pass
    for t in leg.get_texts():
        _apply_font_to_text(t, preset.get("legend_size"), preset.get("fontfamily"))
        try: t.set_color(preset.get("legend_textcolor", preset.get("text_color", "black")))
        except Exception: pass
    try:
        _apply_font_to_text(leg.get_title(), preset.get("legend_title_size"), preset.get("fontfamily"))
        leg.get_title().set_color(preset.get("legend_textcolor", preset.get("text_color", "black")))
    except Exception:
        pass

def _fe_legend_overlap_score(ax, leg):
    # Reusa la función existente y agrega una penalización suave por cantidad de puntos tapados.
    return _legend_data_overlap_score(ax, leg)

def _fe_build_legend(ax, preset, styles_by_label, placement="auto", verbose=False):
    labels, styles = _fe_legend_labels_and_styles(ax, styles_by_label)
    if not labels:
        return None, "none"
    old_title = ""
    try:
        old_leg = ax.get_legend()
        if old_leg is not None:
            old_title = old_leg.get_title().get_text()
            old_leg.remove()
    except Exception:
        pass
    handles = [_fe_make_legend_handle(st, preset) for st in styles]
    n = len(labels)
    mode = str(placement or "auto").lower().strip()
    if mode in {"none", "off", "no"}:
        return None, "none"
    frameon = bool(preset.get("legend_frame", False))

    def _inside(loc="best"):
        leg = ax.legend(handles, labels, title=old_title, loc=loc, frameon=frameon,
                        ncol=1, borderaxespad=0.6, handlelength=2.1,
                        handletextpad=0.55, labelspacing=0.42)
        _fe_apply_legend_cosmetics(leg, preset)
        try: ax._fe_legend_placement = "inside_auto"
        except Exception: pass
        return leg

    def _outside():
        # 2 columnas si hay muchas entradas y el preset es ancho; 1 columna por defecto.
        ncol = 1
        if n >= 10 and str(preset.get("label", "")).lower().find("wide") >= 0:
            ncol = 2
        leg = ax.legend(handles, labels, title=old_title, loc="center left",
                        bbox_to_anchor=(1.02, 0.5), borderaxespad=0.0,
                        frameon=frameon, ncol=ncol, handlelength=2.1,
                        handletextpad=0.55, labelspacing=0.42)
        _fe_apply_legend_cosmetics(leg, preset)
        try: ax._fe_legend_placement = "outside_right_auto"
        except Exception: pass
        return leg

    if mode in {"inside", "in"}:
        return _inside("best"), "inside"
    if mode in {"outside", "outside_right", "out"}:
        return _outside(), "outside"

    # AUTO: para pocas curvas intentamos dentro; para muchas, afuera.
    if n <= 4:
        leg = _inside("best")
        score = _fe_legend_overlap_score(ax, leg)
        if score <= 0:
            if verbose: print(f"  Leyenda interna: n={n}, overlap={score}")
            return leg, "inside"
        try: leg.remove()
        except Exception: pass
        if verbose: print(f"  Leyenda externa: n={n}, overlap interno={score}")
        return _outside(), "outside"

    if n <= 6:
        # Probar esquinas explícitas: si ninguna sirve, afuera.
        candidate_locs = ["upper right", "upper left", "lower right", "lower left", "best"]
        best = None
        best_score = 10**9
        best_loc = None
        for loc in candidate_locs:
            leg = _inside(loc)
            score = _fe_legend_overlap_score(ax, leg)
            if score < best_score:
                best_score = score; best_loc = loc
            try: leg.remove()
            except Exception: pass
            if score <= 0:
                leg = _inside(loc)
                if verbose: print(f"  Leyenda interna: n={n}, loc={loc}, overlap={score}")
                return leg, "inside"
        if verbose: print(f"  Leyenda externa: n={n}, mejor loc interna={best_loc}, overlap={best_score}")
        return _outside(), "outside"

    if verbose: print(f"  Leyenda externa: n={n} entradas.")
    return _outside(), "outside"

def _fe_adjust_layout_for_external_legends(fig, preset, apply_layout=True):
    if not apply_layout:
        return
    axes = _data_axes(fig)
    any_out = any(getattr(ax, "_fe_legend_placement", "") == "outside_right_auto" for ax in axes)
    if not any_out:
        # Si la leyenda quedó interna, conservar bien el preset.
        try:
            margins = preset.get("margins", {}) or {}
            if margins:
                fig.subplots_adjust(**margins)
        except Exception:
            pass
        return
    try:
        w, h = fig.get_size_inches()
        # Agregar una columna de leyenda sin destruir el aspecto original del preset.
        fig.set_size_inches(float(w) + 1.25, float(h), forward=True)
    except Exception:
        pass
    try:
        sp = fig.subplotpars
        left = float((preset.get("margins", {}) or {}).get("left", getattr(sp, "left", 0.16)))
        bottom = float((preset.get("margins", {}) or {}).get("bottom", getattr(sp, "bottom", 0.16)))
        top = float((preset.get("margins", {}) or {}).get("top", getattr(sp, "top", 0.92)))
        fig.subplots_adjust(left=left, right=0.73, bottom=bottom, top=top)
    except Exception:
        pass

def apply_full_style(fig, style_name="prb_technical", options=None, **kwargs):
    """Aplica un preset editorial completo.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
    style_name : str
        Uno de list_cosmetic_presets().keys().
    options : dict, optional
        Opciones: apply_colors, apply_layout, apply_linewidths, apply_marker_sizes,
        apply_legend, legend_policy ('auto'|'inside'|'outside'|'none'), verbose.
    **kwargs :
        Sobrescribe keys de options.

    Notes
    -----
    Esta función no modifica datos, escalas ni límites. Solo cosmética.
    """
    opts = dict(options or {})
    opts.update(kwargs)
    apply_colors = bool(opts.get("apply_colors", True))
    apply_layout = bool(opts.get("apply_layout", True))
    apply_linewidths = bool(opts.get("apply_linewidths", True))
    apply_marker_sizes = bool(opts.get("apply_marker_sizes", True))
    apply_legend = bool(opts.get("apply_legend", True))
    verbose = bool(opts.get("verbose", False))
    key = str(style_name).strip().lower()
    if key not in _FIGURE_STYLE_PRESETS:
        raise ValueError(f"Preset desconocido: {style_name}. Opciones: {', '.join(_FIGURE_STYLE_PRESETS)}")
    preset = _FIGURE_STYLE_PRESETS[key]

    _fe_apply_font_and_axes_style(fig, preset)

    if apply_layout:
        try:
            fig.subplots_adjust(**(preset.get("margins", {}) or {}))
        except Exception:
            pass

    for ax in _data_axes(fig):
        styles_by_label = _fe_style_all_series(ax, preset,
                                               apply_colors=apply_colors,
                                               apply_linewidths=apply_linewidths,
                                               apply_marker_sizes=apply_marker_sizes)
        if apply_legend:
            pol = str(opts.get("legend_policy", preset.get("legend_policy_default", "auto"))).lower().strip()
            _fe_build_legend(ax, preset, styles_by_label, placement=pol, verbose=verbose)

    if apply_legend:
        _fe_adjust_layout_for_external_legends(fig, preset, apply_layout=apply_layout)

    try:
        prefs = _get_export_prefs(fig)
        prefs.update(preset.get("export", {}) or {})
        _set_export_prefs(fig, prefs)
    except Exception:
        pass
    try: fig._fe_cosmetic_preset = key
    except Exception: pass
    _refresh(fig)
    return fig

# Nombre histórico preservado.
def apply_cosmetic_preset(fig, preset_name="prb_technical", apply_colors=True, apply_layout=True,
                          apply_linewidths=True, apply_marker_sizes=True, apply_legend=True,
                          legend_policy="auto", verbose=False):
    return apply_full_style(fig, preset_name, {
        "apply_colors": apply_colors,
        "apply_layout": apply_layout,
        "apply_linewidths": apply_linewidths,
        "apply_marker_sizes": apply_marker_sizes,
        "apply_legend": apply_legend,
        "legend_policy": legend_policy,
        "verbose": verbose,
    })

def list_cosmetic_presets():
    return {k: {"label": v.get("label", k), "description": v.get("description", "")}
            for k, v in _FIGURE_STYLE_PRESETS.items()}

def _menu_cosmetic_presets(fig):
    keys = list(_FIGURE_STYLE_PRESETS.keys())
    while True:
        print("\n  ── Formatos editoriales / presets cosméticos (v6) ──")
        for i, k in enumerate(keys, start=1):
            pr = _FIGURE_STYLE_PRESETS[k]
            print(f"   {i}. {pr.get('label', k)}  [{k}]")
            print(f"      {pr.get('description', '')}")
        print(f"   {len(keys)+1}. Restaurar formato ORIGINAL cargado")
        print(f"   {len(keys)+2}. Cargar formato desde otra figura guardada (.json)")
        print(f"   {len(keys)+3}. Volver")
        op = input("  Opción: ").strip()
        if not op:
            return fig
        try: idx = int(op)
        except Exception:
            print("  Opción inválida."); continue
        if 1 <= idx <= len(keys):
            key = keys[idx-1]
            default_pol = _FIGURE_STYLE_PRESETS[key].get("legend_policy_default", "auto")
            apply_colors = _prompt_yesno("  ¿Aplicar también paleta de colores + marcadores del preset?", default=True)
            apply_layout = _prompt_yesno("  ¿Aplicar tamaño/márgenes/aspecto del preset?", default=True)
            legend_policy = _prompt("  Política de leyenda (auto/inside/outside/none)", default_pol).strip().lower()
            verbose = _prompt_yesno("  ¿Mostrar diagnóstico de ubicación de leyenda?", default=False)
            try:
                apply_full_style(fig, key, apply_colors=apply_colors,
                                 apply_layout=apply_layout,
                                 legend_policy=legend_policy,
                                 verbose=verbose)
                print(f"  Preset aplicado: {_FIGURE_STYLE_PRESETS[key].get('label', key)}")
            except Exception as e:
                print(f"  Error aplicando preset: {e}")
            return fig
        elif idx == len(keys)+1:
            try:
                restore_original_format(fig)
                print("  Formato original restaurado desde el JSON cargado.")
            except Exception as e:
                print(f"  No se pudo restaurar el original: {e}")
            return fig
        elif idx == len(keys)+2:
            ref = input("  Ruta al JSON de referencia: ").strip().strip('"')
            if not ref:
                print("  Operación cancelada."); return fig
            try:
                apply_format_from_saved_figure(fig, ref)
                print("  Formato copiado desde la figura de referencia.")
            except Exception as e:
                print(f"  No se pudo copiar el formato: {e}")
            return fig
        elif idx == len(keys)+3:
            return fig
        else:
            print("  Opción inválida.")

# ═════════════════════════════════════════════════════════════════════════════
# v7 PATCH — leyenda externa robusta con ejes serializados via add_axes
# ═════════════════════════════════════════════════════════════════════════════
# Motivo: en figuras cargadas desde JSON con posiciones absolutas de axes,
# fig.subplots_adjust() no modifica la posición real del axes. En v6 la leyenda
# externa podía quedar parcialmente fuera del canvas: aparecían los handles, pero
# no los textos. Esta capa no toca datos, límites ni escalas; solo reserva espacio
# geométrico real para la leyenda y reconstruye la leyenda luego de mover el axes.

def _fe_external_legend_required(fig):
    try:
        return any(getattr(ax, "_fe_legend_placement", "") == "outside_right_auto" for ax in _data_axes(fig))
    except Exception:
        return False


def _fe_reserve_right_legend_column(fig, preset=None, min_right=0.66, max_right=0.78):
    """Reserva espacio real a la derecha para leyendas externas.

    Funciona tanto para subplots normales como para ejes creados con add_axes()
    desde posiciones serializadas. Devuelve True si modificó posiciones.
    """
    preset = preset or {}
    axes = _data_axes(fig)
    out_axes = [ax for ax in axes if getattr(ax, "_fe_legend_placement", "") == "outside_right_auto"]
    if not out_axes:
        return False

    # Derecho objetivo dependiente del tamaño y número de entradas.
    # Para leyendas largas conviene dejar una columna generosa.
    max_entries = 0
    for ax in out_axes:
        try:
            max_entries = max(max_entries, _legend_entry_count(ax))
        except Exception:
            pass
    target_right = 0.74 if max_entries <= 8 else 0.70
    target_right = min(max_right, max(min_right, target_right))

    changed = False
    for ax in out_axes:
        try:
            pos = ax.get_position()
            left, bottom, width, height = pos.x0, pos.y0, pos.width, pos.height
            # Si el axes ya termina antes del target, no achicarlo de más.
            new_right = min(float(pos.x1), target_right)
            # Pero si originalmente ocupa casi todo el ancho, forzar columna.
            if float(pos.x1) > target_right + 0.03:
                new_width = max(0.30, new_right - left)
                ax.set_position([left, bottom, new_width, height])
                changed = True
        except Exception:
            pass
    return changed


def _fe_reanchor_external_legends(fig, preset=None):
    """Reancla leyendas externas después de cambiar posiciones de axes."""
    preset = preset or {}
    for ax in _data_axes(fig):
        if getattr(ax, "_fe_legend_placement", "") != "outside_right_auto":
            continue
        leg = ax.get_legend()
        if leg is None:
            continue
        try:
            # Mantiene el anclaje fuera del axes, pero ahora dentro del canvas
            # porque _fe_reserve_right_legend_column redujo el ancho real del axes.
            leg.set_bbox_to_anchor((1.025, 0.5), transform=ax.transAxes)
            leg._loc = 6  # center left en Matplotlib clásico
        except Exception:
            pass
        try:
            _fe_apply_legend_cosmetics(leg, preset)
        except Exception:
            pass


def _fe_adjust_layout_for_external_legends(fig, preset, apply_layout=True):
    """v7: ajusta layout aun cuando los axes fueron creados por add_axes()."""
    if not apply_layout:
        return
    axes = _data_axes(fig)
    any_out = any(getattr(ax, "_fe_legend_placement", "") == "outside_right_auto" for ax in axes)
    if not any_out:
        try:
            margins = preset.get("margins", {}) or {}
            if margins:
                fig.subplots_adjust(**margins)
        except Exception:
            pass
        return

    # 1) Aumentar canvas de manera moderada según cantidad de entradas.
    try:
        max_entries = max([_legend_entry_count(ax) for ax in axes] or [0])
    except Exception:
        max_entries = 0
    try:
        w, h = fig.get_size_inches()
        extra = 1.10 if max_entries <= 8 else 1.45
        # Evita aumentos acumulativos si se aplica el preset varias veces.
        base_w = float((preset.get("figsize") or (w, h))[0])
        base_h = float((preset.get("figsize") or (w, h))[1])
        fig.set_size_inches(base_w + extra, base_h, forward=True)
    except Exception:
        pass

    # 2) Para subplots normales, subplots_adjust ayuda; para add_axes no alcanza.
    try:
        sp = fig.subplotpars
        left = float((preset.get("margins", {}) or {}).get("left", getattr(sp, "left", 0.16)))
        bottom = float((preset.get("margins", {}) or {}).get("bottom", getattr(sp, "bottom", 0.16)))
        top = float((preset.get("margins", {}) or {}).get("top", getattr(sp, "top", 0.92)))
        fig.subplots_adjust(left=left, right=0.72, bottom=bottom, top=top)
    except Exception:
        pass

    # 3) Ajuste real de posiciones absolutas guardadas en JSON.
    _fe_reserve_right_legend_column(fig, preset=preset)
    _fe_reanchor_external_legends(fig, preset=preset)
    try:
        fig.canvas.draw_idle()
    except Exception:
        pass


# Re-definimos apply_full_style para asegurar que use el ajuste v7 anterior.
def apply_full_style(fig, style_name="prb_technical", options=None, **kwargs):
    """Aplica un preset editorial completo (v7, con leyenda externa robusta)."""
    opts = dict(options or {})
    opts.update(kwargs)
    apply_colors = bool(opts.get("apply_colors", True))
    apply_layout = bool(opts.get("apply_layout", True))
    apply_linewidths = bool(opts.get("apply_linewidths", True))
    apply_marker_sizes = bool(opts.get("apply_marker_sizes", True))
    apply_legend = bool(opts.get("apply_legend", True))
    verbose = bool(opts.get("verbose", False))
    key = str(style_name).strip().lower()
    if key not in _FIGURE_STYLE_PRESETS:
        raise ValueError(f"Preset desconocido: {style_name}. Opciones: {', '.join(_FIGURE_STYLE_PRESETS)}")
    preset = _FIGURE_STYLE_PRESETS[key]

    _fe_apply_font_and_axes_style(fig, preset)

    if apply_layout:
        try:
            fig.subplots_adjust(**(preset.get("margins", {}) or {}))
        except Exception:
            pass

    for ax in _data_axes(fig):
        styles_by_label = _fe_style_all_series(
            ax, preset,
            apply_colors=apply_colors,
            apply_linewidths=apply_linewidths,
            apply_marker_sizes=apply_marker_sizes,
        )
        if apply_legend:
            pol = str(opts.get("legend_policy", preset.get("legend_policy_default", "auto"))).lower().strip()
            _fe_build_legend(ax, preset, styles_by_label, placement=pol, verbose=verbose)

    if apply_legend:
        _fe_adjust_layout_for_external_legends(fig, preset, apply_layout=apply_layout)

    try:
        prefs = _get_export_prefs(fig)
        prefs.update(preset.get("export", {}) or {})
        _set_export_prefs(fig, prefs)
    except Exception:
        pass
    try:
        fig._fe_cosmetic_preset = key
    except Exception:
        pass
    _refresh(fig)
    return fig


def apply_cosmetic_preset(fig, preset_name="prb_technical", apply_colors=True, apply_layout=True,
                          apply_linewidths=True, apply_marker_sizes=True, apply_legend=True,
                          legend_policy="auto", verbose=False):
    return apply_full_style(fig, preset_name, {
        "apply_colors": apply_colors,
        "apply_layout": apply_layout,
        "apply_linewidths": apply_linewidths,
        "apply_marker_sizes": apply_marker_sizes,
        "apply_legend": apply_legend,
        "legend_policy": legend_policy,
        "verbose": verbose,
    })

# Alias informativo para poder verificar desde consola.
_FIGURE_EDITOR_VERSION_NOTE = "figure_editor7: v6 + fix leyenda externa con axes serializados"


# ═══════════════════════════════════════════════════════════════════════════════
#  V9 - Refresco interactivo más agresivo para Spyder/Qt
# ═══════════════════════════════════════════════════════════════════════════════
# Nota: esta redefinición reemplaza _refresh globalmente. Todas las funciones
# anteriores que llaman _refresh usarán esta versión en tiempo de ejecución.

def _fe_detect_backend_name():
    try:
        import matplotlib
        return str(matplotlib.get_backend())
    except Exception:
        return "unknown"

def _fe_force_window_geometry(fig, extra_pad_px: int = 40):
    """Sincroniza tamaño lógico de la figura con el tamaño real de la ventana Qt."""
    if fig is None:
        return
    try:
        fig.canvas.draw()
    except Exception:
        pass
    try:
        w_in, h_in = fig.get_size_inches()
        dpi = float(getattr(fig, "dpi", 100.0) or 100.0)
        w_px = max(300, int(round(float(w_in) * dpi)) + int(extra_pad_px))
        h_px = max(240, int(round(float(h_in) * dpi)) + int(extra_pad_px))
        mgr = getattr(fig.canvas, "manager", None)
        if mgr is not None:
            try:
                mgr.resize(w_px, h_px)
            except Exception:
                pass
            try:
                win = getattr(mgr, "window", None)
                if win is not None:
                    try:
                        win.resize(w_px, h_px)
                    except Exception:
                        pass
                    try:
                        win.update()
                    except Exception:
                        pass
                    try:
                        win.raise_()
                    except Exception:
                        pass
                    try:
                        win.activateWindow()
                    except Exception:
                        pass
            except Exception:
                pass
    except Exception:
        pass

def _fe_full_event_pump(fig, cycles: int = 3, pause: float = 0.08):
    """Bombea eventos de GUI varias veces; útil cuando input() bloquea Spyder."""
    for _ in range(max(1, int(cycles))):
        try:
            if fig is not None:
                try: fig.canvas.draw_idle()
                except Exception: pass
                try: fig.canvas.draw()
                except Exception: pass
                try: fig.canvas.flush_events()
                except Exception: pass
            try:
                plt.pause(float(pause))
            except Exception:
                pass
        except Exception:
            pass

def _refresh(fig, pause: float = 0.10, force_show: bool = True, aggressive: bool = True):
    """Refresco robusto v9 para figuras editadas en Spyder/Qt.

    Diferencia con v8:
      - fuerza tamaño real de la ventana cuando el preset cambia figsize;
      - bombea eventos varias veces antes de volver al menú input();
      - advierte si el backend es inline, donde no hay refresco interactivo real.
    """
    backend = _fe_detect_backend_name().lower()
    try:
        plt.ion()
    except Exception:
        pass

    # En backends inline no hay actualización interactiva real durante input().
    # No lanzamos error: solo dejamos una marca para que el menú pueda informar si hace falta.
    try:
        if fig is not None:
            setattr(fig, "_fe_backend_name", _fe_detect_backend_name())
            setattr(fig, "_fe_backend_is_inline", ("inline" in backend))
    except Exception:
        pass

    if aggressive:
        _fe_force_window_geometry(fig)

    try:
        if fig is not None:
            try: fig.show()
            except Exception: pass
            try:
                mgr = getattr(fig.canvas, "manager", None)
                if mgr is not None:
                    try: mgr.show()
                    except Exception: pass
            except Exception:
                pass
        if force_show and ("inline" not in backend):
            try:
                plt.show(block=False)
            except Exception:
                pass
    except Exception:
        pass

    _fe_full_event_pump(fig, cycles=4 if aggressive else 2, pause=pause)

def _fe_print_backend_warning_once(fig):
    try:
        if getattr(fig, "_fe_backend_warning_printed", False):
            return
        backend = _fe_detect_backend_name()
        if "inline" in backend.lower():
            print("\n  AVISO: Matplotlib está usando backend INLINE.")
            print("  En Spyder, el backend inline no refresca bien figuras durante menús con input().")
            print("  Recomendado: ejecutar en la consola:  %matplotlib qt")
            print("  o ir a Tools > Preferences > IPython console > Graphics > Backend = Qt5/QtAgg.")
        setattr(fig, "_fe_backend_warning_printed", True)
    except Exception:
        pass

# Envolvemos edit_cosmetics para avisar sobre backend y refrescar antes del primer input.
_edit_cosmetics_v9_base = edit_cosmetics
def edit_cosmetics(fig, *args, **kwargs):
    _refresh(fig, pause=0.12, aggressive=True)
    _fe_print_backend_warning_once(fig)
    return _edit_cosmetics_v9_base(fig, *args, **kwargs)

# ═══════════════════════════════════════════════════════════════════════════════
#  V10 - refresco duro opcional: reconstruir ventana desde JSON temporal
# ═══════════════════════════════════════════════════════════════════════════════
# Motivo: en algunas configuraciones de Spyder/Qt la ventana Matplotlib no refleja
# cambios de tamaño/leyenda mientras el menú con input() sigue activo. En esos
# casos no basta con draw()/flush_events(): la figura queda visualmente vieja hasta
# salir. Este modo reconstruye la ventana completa desde el estado actual.

def _fe_hard_rebuild_figure_window(fig, close_old: bool = True, verbose: bool = False):
    """Reconstruye una figura en una ventana nueva usando la serialización del editor.

    No cambia datos ni cosmética: guarda un JSON/CSV temporal del estado actual,
    recarga con load_figure() y devuelve el nuevo objeto Figure. Es más lento que
    _refresh(), pero evita fallas de refresco de ventanas Qt/Spyder.
    """
    if fig is None:
        return fig
    import tempfile as _tempfile
    import os as _os
    from pathlib import Path as _Path
    old_base = getattr(fig, '_fe_base_filename', None)
    old_active_idx = getattr(fig, '_fe_active_idx', 0)
    old_hard = bool(getattr(fig, '_fe_hard_refresh_after_preset', False))
    tmpdir = _tempfile.mkdtemp(prefix='fe_hard_refresh_')
    base = _Path(tmpdir) / '_fe_current_state'
    try:
        save_figure_data(fig, str(base), save_png=False)
        if close_old:
            try:
                plt.close(fig)
            except Exception:
                pass
        new_fig = load_figure(str(base), show=True)
        try:
            if old_base is not None:
                new_fig._fe_base_filename = old_base
        except Exception:
            pass
        try:
            new_fig._fe_active_idx = old_active_idx
        except Exception:
            pass
        try:
            new_fig._fe_hard_refresh_after_preset = old_hard
        except Exception:
            pass
        _refresh(new_fig, pause=0.15, aggressive=True)
        if verbose:
            print('  Refresh duro OK: figura reconstruida en una ventana nueva.')
        return new_fig
    except Exception as e:
        if verbose:
            print(f'  Refresh duro falló; conservo la figura actual. Detalle: {e}')
        try:
            _refresh(fig, pause=0.15, aggressive=True)
        except Exception:
            pass
        return fig
    finally:
        # Limpieza de temporales. En Windows puede fallar si algún handle quedó abierto;
        # no es crítico y no debe romper el editor.
        try:
            for ext in ('.json', '.csv', '.png'):
                p = base.with_suffix(ext)
                if p.exists():
                    p.unlink()
            _os.rmdir(tmpdir)
        except Exception:
            pass


def hard_refresh_figure_window(fig, verbose: bool = True):
    """Función pública para forzar reconstrucción visual desde la consola."""
    return _fe_hard_rebuild_figure_window(fig, close_old=True, verbose=verbose)


# Reemplazo del menú principal: idéntico flujo que v9, pero luego del menú de
# presets reconstruye la ventana si fig._fe_hard_refresh_after_preset=True.
def edit_cosmetics(fig, base_filename: str = 'figure'):
    _enable_interactive_mode_for_editor()
    # Por defecto activamos refresh duro tras presets, porque es la ruta robusta
    # para Spyder cuando la ventana no actualiza leyendas externas.
    try:
        if not hasattr(fig, '_fe_hard_refresh_after_preset'):
            fig._fe_hard_refresh_after_preset = False
    except Exception:
        pass
    _refresh(fig, pause=0.05)
    base_filename  = str(getattr(fig, '_fe_base_filename', base_filename))
    axes0 = _data_axes(fig)
    if axes0:
        saved_idx = getattr(fig, '_fe_active_idx', 0)
        try:
            saved_idx = int(saved_idx)
        except Exception:
            saved_idx = 0
        if saved_idx < 0 or saved_idx >= len(axes0):
            saved_idx = 0
        active_idx = saved_idx
        active_ax = axes0[active_idx]
    else:
        active_ax = None
        active_idx = None
    while True:
        axes = _data_axes(fig)
        if axes:
            if active_idx is None or active_idx >= len(axes):
                active_idx = 0
            active_ax = axes[active_idx]
        else:
            active_ax = None
            active_idx = None
        print(_render_main_banner(active_idx, active_ax, base_filename))
        op = input('  Opción: ').strip()
        if op == '1':
            _menu_general(fig)
        elif op == '2':
            if not axes:
                print('  No hay subplots editables.')
            else:
                active_ax, active_idx = _pick_axis(fig)
                try: fig._fe_active_idx = active_idx
                except Exception: pass
        elif op == '3':
            if not axes or active_ax is None:
                print('  No hay subplots editables.')
            else:
                _menu_subplot(fig, active_ax, active_idx)
        elif op == '4':
            fig = _fe_hard_rebuild_figure_window(fig, close_old=True, verbose=True)
            try:
                fig._fe_base_filename = base_filename
            except Exception:
                pass
        elif op == '5':
            nb = input(f'  Nombre base [{base_filename}] (Enter=mantener): ').strip()
            if nb:
                base_filename = str(_base_path(nb))
            save_figure_data(fig, base_filename, save_png=True)
            paths = [Path(str(_base_path(base_filename)) + ext) for ext in ('.json', '.csv', '.png')]
            missing = [str(p) for p in paths if not p.exists()]
            if missing:
                print('  Advertencia: faltan archivos tras guardar:')
                for p in missing:
                    print(f'    - {p}')
            else:
                prefs = _get_export_prefs(fig)
                print('  Verificación OK:')
                for p in paths:
                    print(f'    - {p.name} ({p.stat().st_size} bytes)')
                print(f"  PNG guardado con bbox={prefs['bbox_mode']} | autocrop={'on' if prefs['autocrop_white'] else 'off'}")
            try: fig._fe_base_filename = base_filename
            except Exception: pass
        elif op == '6':
            fmt = _prompt('Formato (png/eps/pdf/svg)', 'png')
            dpi = _prompt_float('DPI (solo raster)', 300)
            prefs = _get_export_prefs(fig)
            bbox_mode = _prompt('Borde exportado (exact/tight/content)', prefs['bbox_mode']).strip().lower()
            pad_inches = _prompt_float('pad_inches (si bbox=tight/content)', prefs['pad_inches'])
            autocrop = prefs['autocrop_white']
            if fmt.lower() == 'png':
                ac = _prompt('autocrop_white PNG (on/off)', 'on' if prefs['autocrop_white'] else 'off').strip().lower()
                autocrop = (ac == 'on')
            nb = input(f'  Nombre base [{base_filename}] (Enter=mantener): ').strip()
            if nb:
                base_filename = str(_base_path(nb))
            out = str(_base_path(base_filename)) + '.' + fmt
            try:
                local_prefs = dict(prefs)
                if bbox_mode.startswith('t'):
                    _mode = 'tight'
                elif bbox_mode.startswith('c'):
                    _mode = 'content'
                elif bbox_mode.startswith('e'):
                    _mode = 'exact'
                else:
                    _mode = prefs.get('bbox_mode', 'content')
                local_prefs.update({'bbox_mode': _mode, 'pad_inches': pad_inches, 'autocrop_white': autocrop})
                _save_figure_image(fig, out, dpi=dpi, prefs=local_prefs)
                print(f'  Exportado: {out}')
            except Exception as e:
                print(f'  Error: {e}')
        elif op == '7':
            before_id = id(fig)
            maybe = _menu_cosmetic_presets(fig)
            if maybe is not None:
                fig = maybe
            if bool(getattr(fig, '_fe_hard_refresh_after_preset', False)):
                fig = _fe_hard_rebuild_figure_window(fig, close_old=True, verbose=True)
                try: fig._fe_base_filename = base_filename
                except Exception: pass
        elif op == '8':
            maybe_fig = _menu_split_recompose(fig, base_filename=base_filename)
            if maybe_fig is not None and maybe_fig is not fig:
                return maybe_fig
        elif op == '9':
            _refresh(fig)
            print('  Saliendo del editor.')
            return fig
        else:
            print('  Opción inválida.')

_FIGURE_EDITOR_VERSION_NOTE = 'figure_editor10: v9 + hard rebuild window refresh after presets'


# ═══════════════════════════════════════════════════════════════════════════════
#  V12 - input() reemplazado por diálogo Qt real
# ═══════════════════════════════════════════════════════════════════════════════
# Diagnóstico raíz:
#   input() bloquea el hilo principal. En Spyder/Qt ese mismo hilo necesita correr
#   el event loop de Qt para repintar ventanas Matplotlib. Por eso draw(), pause()
#   o flush_events() antes/después del prompt no son una solución estructural.
#
# Solución v12:
#   Durante edit_cosmetics(), se intercepta temporalmente builtins.input y se lo
#   reemplaza por _fe_qt_input_dialog(). QInputDialog.getText() corre un event
#   loop modal interno de Qt mientras espera texto; por lo tanto las ventanas de
#   Matplotlib siguen recibiendo eventos paint/resize mientras el usuario escribe.
#   Si Qt no está disponible, se vuelve al input() clásico como fallback.

_edit_cosmetics_console_base = edit_cosmetics


def _fe_get_qt_widgets():
    """Devuelve un módulo QtWidgets disponible o None."""
    try:
        from qtpy import QtWidgets  # type: ignore
        return QtWidgets
    except Exception:
        pass
    for modname in ("PyQt5", "PySide6", "PySide2", "PyQt6"):
        try:
            module = __import__(modname, fromlist=["QtWidgets"])
            return module.QtWidgets
        except Exception:
            continue
    return None


def _fe_qt_parent_from_fig(fig=None):
    """Intenta usar la ventana Matplotlib como parent del diálogo Qt."""
    candidates = []
    if fig is not None:
        candidates.append(fig)
    try:
        active = plt.gcf()
        if active is not None and active not in candidates:
            candidates.append(active)
    except Exception:
        pass
    try:
        for num in reversed(list(plt.get_fignums())):
            f = plt.figure(num)
            if f not in candidates:
                candidates.append(f)
    except Exception:
        pass

    for f in candidates:
        try:
            mgr = getattr(getattr(f, "canvas", None), "manager", None)
            win = getattr(mgr, "window", None)
            if win is not None:
                return win
        except Exception:
            pass
    return None


def _fe_qt_input_dialog(prompt: str = "", *, fig=None, original_input=None) -> str:
    """Entrada de texto vía Qt, con fallback a input().

    Retorna siempre str. Si el usuario cancela, retorna "" para respetar la
    semántica de Enter/cancelar de los menús existentes.
    """
    prompt = str(prompt or "")
    QtWidgets = _fe_get_qt_widgets()

    if QtWidgets is None:
        if original_input is not None:
            return original_input(prompt)
        return input(prompt)

    app = QtWidgets.QApplication.instance()
    if app is None:
        try:
            app = QtWidgets.QApplication([])
        except Exception:
            if original_input is not None:
                return original_input(prompt)
            return input(prompt)

    # Asegurar que las figuras existentes se dibujen antes de mostrar el diálogo.
    try:
        for num in list(plt.get_fignums()):
            f = plt.figure(num)
            try: f.canvas.draw_idle()
            except Exception: pass
            try: f.canvas.flush_events()
            except Exception: pass
    except Exception:
        pass
    try:
        app.processEvents()
    except Exception:
        pass

    title = "Editor de figura - entrada"
    label = prompt.rstrip() or "Ingrese valor:"
    parent = _fe_qt_parent_from_fig(fig)
    try:
        text, ok = QtWidgets.QInputDialog.getText(parent, title, label)
        if not ok:
            return ""
        return str(text)
    except Exception:
        if original_input is not None:
            return original_input(prompt)
        return input(prompt)
    finally:
        try:
            app.processEvents()
        except Exception:
            pass


def _fe_enable_qt_input_for_editor(fig):
    """Context manager: reemplaza builtins.input por diálogo Qt durante el editor."""
    import builtins as _builtins

    class _InputPatch:
        def __enter__(self_inner):
            self_inner.original_input = _builtins.input
            def _patched_input(prompt=""):
                return _fe_qt_input_dialog(prompt, fig=fig, original_input=self_inner.original_input)
            _builtins.input = _patched_input
            return self_inner
        def __exit__(self_inner, exc_type, exc, tb):
            _builtins.input = self_inner.original_input
            return False
    return _InputPatch()


def edit_cosmetics(fig, *args, **kwargs):
    """Editor v12: conserva menús y funciones, pero evita input() bloqueante.

    Cambio estructural frente a v8-v11:
      - No se intenta arreglar el repaint con más draw()/pause().
      - Se reemplaza input() por QInputDialog.getText() durante el editor.
      - QInputDialog mantiene vivo el event loop Qt mientras espera el texto.

    Fallback:
      - Si Qt no está disponible, usa input() clásico.
    """
    try:
        plt.ion()
    except Exception:
        pass
    try:
        if fig is not None:
            try: fig.canvas.draw_idle()
            except Exception: pass
            try: fig.canvas.flush_events()
            except Exception: pass
    except Exception:
        pass

    with _fe_enable_qt_input_for_editor(fig):
        return _edit_cosmetics_console_base(fig, *args, **kwargs)


_FIGURE_EDITOR_VERSION_NOTE = 'figure_editor12: v11 + QInputDialog input replacement to keep Qt event loop alive'

# ═══════════════════════════════════════════════════════════════════════════════
#  V13 - Diagnóstico aplicado: sin JSON temporal automático + entrada Qt no modal
# ═══════════════════════════════════════════════════════════════════════════════
_FE_QT_PROMPT_PREVIEW_SECONDS = 0.35
_FE_QT_INITIAL_PREVIEW_SECONDS = 5.0
_FE_AUTO_MAXIMIZE_FIGURES = True
_FE_QT_DIALOG_NONMODAL = False


def _fe_get_qt_modules():
    try:
        from qtpy import QtWidgets, QtCore  # type: ignore
        return QtWidgets, QtCore
    except Exception:
        pass
    for modname in ("PyQt5", "PySide6", "PySide2", "PyQt6"):
        try:
            module = __import__(modname, fromlist=["QtWidgets", "QtCore"])
            return module.QtWidgets, module.QtCore
        except Exception:
            continue
    return None, None


def _fe_arrange_figure_windows(fig=None, maximize=True, preview_seconds=None):
    QtWidgets, QtCore = _fe_get_qt_modules()
    app = None
    if QtWidgets is not None:
        try:
            app = QtWidgets.QApplication.instance()
            if app is None:
                app = QtWidgets.QApplication([])
        except Exception:
            app = None
    figs = []
    if fig is not None:
        figs.append(fig)
    try:
        for num in list(plt.get_fignums()):
            f = plt.figure(num)
            if f not in figs:
                figs.append(f)
    except Exception:
        pass
    for f in figs:
        for meth in ("draw_idle", "draw"):
            try: getattr(f.canvas, meth)()
            except Exception: pass
        try: f.canvas.flush_events()
        except Exception: pass
        try:
            mgr = getattr(f.canvas, "manager", None)
            win = getattr(mgr, "window", None)
            if win is not None:
                try: win.show()
                except Exception: pass
                if maximize:
                    try: win.showMaximized()
                    except Exception: pass
                try: win.raise_()
                except Exception: pass
                try: win.activateWindow()
                except Exception: pass
        except Exception:
            pass
    try: plt.show(block=False)
    except Exception: pass
    if app is not None:
        try: app.processEvents()
        except Exception: pass
        import time as _time
        dt = _FE_QT_PROMPT_PREVIEW_SECONDS if preview_seconds is None else float(preview_seconds)
        t0 = _time.time()
        while _time.time() - t0 < max(0.0, dt):
            try: app.processEvents()
            except Exception: pass
            try: plt.pause(0.02)
            except Exception: pass
            _time.sleep(0.02)
    else:
        try: plt.pause(0.10)
        except Exception: pass


def _fe_qt_input_dialog(prompt: str = "", *, fig=None, original_input=None) -> str:
    prompt = str(prompt or "")
    QtWidgets, QtCore = _fe_get_qt_modules()
    if QtWidgets is None:
        return original_input(prompt) if original_input is not None else input(prompt)
    try:
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication([])
    except Exception:
        return original_input(prompt) if original_input is not None else input(prompt)
    _fe_arrange_figure_windows(fig, maximize=_FE_AUTO_MAXIMIZE_FIGURES)
    title = "Editor de figura - entrada"
    label = prompt.rstrip() or "Ingrese valor:"
    if not _FE_QT_DIALOG_NONMODAL:
        try:
            text, ok = QtWidgets.QInputDialog.getText(None, title, label)
            return str(text) if ok else ""
        except Exception:
            return original_input(prompt) if original_input is not None else input(prompt)
    try:
        dlg = QtWidgets.QInputDialog(None)
        dlg.setWindowTitle(title)
        dlg.setLabelText(label)
        dlg.setInputMode(QtWidgets.QInputDialog.TextInput)
        try: dlg.setWindowModality(QtCore.Qt.NonModal)
        except Exception: pass
        try: dlg.resize(520, dlg.sizeHint().height())
        except Exception: pass
        dlg.show()
        try: dlg.raise_()
        except Exception: pass
        try: dlg.activateWindow()
        except Exception: pass
        import time as _time
        while bool(dlg.isVisible()):
            try: app.processEvents()
            except Exception: pass
            try: plt.pause(0.015)
            except Exception: pass
            _time.sleep(0.015)
        try:
            accepted = (dlg.result() == QtWidgets.QDialog.Accepted)
        except Exception:
            accepted = False
        if not accepted:
            return ""
        try: return str(dlg.textValue())
        except Exception: return ""
    except Exception:
        return original_input(prompt) if original_input is not None else input(prompt)
    finally:
        try: app.processEvents()
        except Exception: pass


def edit_cosmetics(fig, *args, **kwargs):
    try: plt.ion()
    except Exception: pass
    try:
        if fig is not None:
            fig._fe_hard_refresh_after_preset = False
    except Exception:
        pass
    _fe_arrange_figure_windows(fig, maximize=_FE_AUTO_MAXIMIZE_FIGURES, preview_seconds=_FE_QT_INITIAL_PREVIEW_SECONDS)
    with _fe_enable_qt_input_for_editor(fig):
        return _edit_cosmetics_console_base(fig, *args, **kwargs)


_FIGURE_EDITOR_VERSION_NOTE = 'figure_editor14: modal Qt input after preview; no nonmodal focus bug; no automatic temp-JSON rebuild'


# ═════════════════════════════════════════════════════════════════════════════
# v15 - paletas de color y esquemas de marcadores separados del estilo editorial
#       + 10 s de previsualización antes/después de aplicar formatos o colores
# ═════════════════════════════════════════════════════════════════════════════

_FE_QT_INITIAL_PREVIEW_SECONDS = 10.0
_FE_APPLY_PREVIEW_SECONDS = 10.0

_FIGURE_COLOR_PALETTES = {
    "okabe_ito_safe": {
        "label": "Okabe-Ito / colorblind safe",
        "description": "Alta diferenciación y muy segura para papers.",
        "colors": ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#000000", "#F0E442", "#999999", "#332288"],
    },
    "muted_journal": {
        "label": "Muted journal",
        "description": "Sobria, desaturada y paper-friendly.",
        "colors": ["#1F3A5F", "#8B4513", "#2F6B5A", "#6C4A7E", "#7A2E2E", "#4C5C68", "#A16B2A", "#468189", "#5D576B", "#A26769"],
    },
    "soft_pastel": {
        "label": "Soft pastel",
        "description": "Suave y agradable, con contraste suficiente.",
        "colors": ["#6C8EBF", "#D98E73", "#74B49B", "#A184C1", "#D17B88", "#7FA8A3", "#D6B656", "#82A0D8", "#C38D9E", "#8BB174"],
    },
    "warm_earth": {
        "label": "Warm earth",
        "description": "Tonos tierra discretos, útiles para figuras sobrias.",
        "colors": ["#7F4F24", "#936639", "#A68A64", "#BC6C25", "#6F1D1B", "#99582A", "#5F6F52", "#8A5A44", "#B08968", "#6B705C"],
    },
    "cool_blues_greens": {
        "label": "Cool blues & greens",
        "description": "Paleta fría, técnica y limpia.",
        "colors": ["#005F73", "#0A9396", "#94D2BD", "#3A86FF", "#457B9D", "#2A9D8F", "#264653", "#48CAE4", "#1D3557", "#52B69A"],
    },
    "dark_contrast": {
        "label": "Dark contrast",
        "description": "Pensada para fondos oscuros o presentaciones.",
        "colors": ["#4CC9F0", "#F72585", "#B8F2E6", "#FFD166", "#90BE6D", "#C77DFF", "#FF8FA3", "#00F5D4", "#F4A261", "#E9FF70"],
    },
    "mono_accent": {
        "label": "Monochrome + accent",
        "description": "Mayormente monocroma con un acento controlado.",
        "colors": ["#111111", "#555555", "#888888", "#B0B0B0", "#0072B2", "#444444", "#777777", "#A0A0A0", "#D55E00", "#666666"],
    },
}

_FIGURE_MARKER_SCHEMES = {
    "solid_classic": {
        "label": "Sólidos clásicos",
        "description": "Marcadores sólidos variados con líneas continuas.",
        "markers_cycle": ["o", "s", "^", "D", "v", "P", "X", "<", ">", "h"],
        "linestyles_cycle": ["-"],
        "fillstyles_cycle": ["full"],
    },
    "open_classic": {
        "label": "Abiertos clásicos",
        "description": "Marcadores abiertos, útiles para figuras densas.",
        "markers_cycle": ["o", "s", "^", "D", "v", "<", ">", "h", "p", "d"],
        "linestyles_cycle": ["-"],
        "fillstyles_cycle": ["none"],
    },
    "mixed_review": {
        "label": "Mixtos review",
        "description": "Combina sólidos y abiertos para máximo contraste visual.",
        "markers_cycle": ["o", "s", "^", "D", "v", "P", "X", "<", ">", "h"],
        "linestyles_cycle": ["-", "--", "-.", ":", (0, (5, 1)), (0, (3, 1, 1, 1))],
        "fillstyles_cycle": ["full", "none", "full", "none", "full", "none", "full", "none"],
    },
    "prl_mono": {
        "label": "PRL mono",
        "description": "Pensado para una estética compacta y casi monocroma.",
        "markers_cycle": ["o", "s", "^", "D", "v", "<", ">", "p"],
        "linestyles_cycle": ["-", "--", "-.", ":", (0, (1, 1)), (0, (4, 2))],
        "fillstyles_cycle": ["none"],
    },
    "bold_presentation": {
        "label": "Bold presentation",
        "description": "Marcadores grandes y bien diferenciados.",
        "markers_cycle": ["o", "s", "D", "^", "v", "P", "X", "*", "h", "8"],
        "linestyles_cycle": ["-", "--", "-.", ":"],
        "fillstyles_cycle": ["full"],
        "marker_size_scale": 1.18,
        "line_width_scale": 1.08,
    },
}


def list_color_palettes():
    return {k: {"label": v.get("label", k), "description": v.get("description", "")}
            for k, v in _FIGURE_COLOR_PALETTES.items()}


def list_marker_schemes():
    return {k: {"label": v.get("label", k), "description": v.get("description", "")}
            for k, v in _FIGURE_MARKER_SCHEMES.items()}


def _fe_active_style_preset(fig):
    key = getattr(fig, "_fe_cosmetic_preset", None)
    if isinstance(key, str) and key in _FIGURE_STYLE_PRESETS:
        return _FIGURE_STYLE_PRESETS[key]
    return _FIGURE_STYLE_PRESETS.get("prb_technical", next(iter(_FIGURE_STYLE_PRESETS.values())))


def _fe_current_legend_policy(ax):
    place = str(getattr(ax, "_fe_legend_placement", "") or "").lower().strip()
    if "outside" in place:
        return "outside"
    if "inside" in place:
        return "inside"
    return "auto"


def _fe_preview_after_style_change(fig):
    try:
        _refresh(fig)
    except Exception:
        pass
    try:
        _fe_arrange_figure_windows(fig, maximize=_FE_AUTO_MAXIMIZE_FIGURES,
                                   preview_seconds=_FE_APPLY_PREVIEW_SECONDS)
    except Exception:
        pass


def apply_color_palette(fig, palette_name="okabe_ito_safe", rebuild_legend=True,
                        legend_policy="auto", verbose=False):
    key = str(palette_name).strip().lower()
    if key not in _FIGURE_COLOR_PALETTES:
        raise ValueError(f"Paleta desconocida: {palette_name}. Opciones: {', '.join(_FIGURE_COLOR_PALETTES)}")
    palette = _FIGURE_COLOR_PALETTES[key]
    preset = dict(_fe_active_style_preset(fig))
    preset["palette"] = list(palette.get("colors", []))
    for ax in _data_axes(fig):
        styles_by_label = _fe_style_all_series(ax, preset,
                                               apply_colors=True,
                                               apply_linewidths=False,
                                               apply_marker_sizes=False)
        if rebuild_legend:
            pol = legend_policy if str(legend_policy).strip().lower() not in {"", "auto"} else _fe_current_legend_policy(ax)
            _fe_build_legend(ax, preset, styles_by_label, placement=pol, verbose=verbose)
    try:
        fig._fe_color_palette = key
    except Exception:
        pass
    _fe_preview_after_style_change(fig)
    return fig


def apply_marker_scheme(fig, scheme_name="solid_classic", rebuild_legend=True,
                        legend_policy="auto", verbose=False):
    key = str(scheme_name).strip().lower()
    if key not in _FIGURE_MARKER_SCHEMES:
        raise ValueError(f"Esquema desconocido: {scheme_name}. Opciones: {', '.join(_FIGURE_MARKER_SCHEMES)}")
    scheme = _FIGURE_MARKER_SCHEMES[key]
    preset = dict(_fe_active_style_preset(fig))
    preset["markers_cycle"] = list(scheme.get("markers_cycle", preset.get("markers_cycle", _FE_MARKERS_14)))
    preset["linestyles_cycle"] = list(scheme.get("linestyles_cycle", preset.get("linestyles_cycle", ["-"])))
    preset["fillstyles_cycle"] = list(scheme.get("fillstyles_cycle", preset.get("fillstyles_cycle", ["full"])))
    if scheme.get("marker_size_scale") is not None:
        preset["marker_size"] = float(preset.get("marker_size", 4.8)) * float(scheme["marker_size_scale"])
    if scheme.get("line_width_scale") is not None:
        preset["line_width"] = float(preset.get("line_width", 1.4)) * float(scheme["line_width_scale"])
    for ax in _data_axes(fig):
        styles_by_label = _fe_style_all_series(ax, preset,
                                               apply_colors=False,
                                               apply_linewidths=True,
                                               apply_marker_sizes=True)
        if rebuild_legend:
            pol = legend_policy if str(legend_policy).strip().lower() not in {"", "auto"} else _fe_current_legend_policy(ax)
            _fe_build_legend(ax, preset, styles_by_label, placement=pol, verbose=verbose)
    try:
        fig._fe_marker_scheme = key
    except Exception:
        pass
    _fe_preview_after_style_change(fig)
    return fig


def _menu_choose_from_mapping(title, mapping):
    keys = list(mapping.keys())
    while True:
        print(f"\n  ── {title} ──")
        for i, k in enumerate(keys, start=1):
            it = mapping[k]
            print(f"   {i}. {it.get('label', k)}  [{k}]")
            print(f"      {it.get('description', '')}")
        print(f"   {len(keys)+1}. Volver")
        op = input("  Opción: ").strip()
        if not op:
            return None
        try:
            idx = int(op)
        except Exception:
            print("  Opción inválida.")
            continue
        if 1 <= idx <= len(keys):
            return keys[idx-1]
        if idx == len(keys)+1:
            return None
        print("  Opción inválida.")


def _menu_cosmetic_presets(fig):
    while True:
        print("\n  ── Presets y estilos (v15) ──")
        print("   1. Aplicar estilo editorial completo")
        print("   2. Aplicar paleta de colores / tonalidades")
        print("   3. Aplicar esquema de marcadores + linestyles")
        print("   4. Restaurar formato ORIGINAL cargado")
        print("   5. Cargar formato desde otra figura guardada (.json)")
        print("   6. Volver")
        op = input("  Opción: ").strip()
        if not op:
            return fig
        if op == "1":
            key = _menu_choose_from_mapping("Formatos editoriales", list_cosmetic_presets())
            if not key:
                continue
            default_pol = _FIGURE_STYLE_PRESETS[key].get("legend_policy_default", "auto")
            apply_colors = _prompt_yesno("  ¿Aplicar también paleta de colores + marcadores del preset?", default=True)
            apply_layout = _prompt_yesno("  ¿Aplicar tamaño/márgenes/aspecto del preset?", default=True)
            legend_policy = _prompt("  Política de leyenda (auto/inside/outside/none)", default_pol).strip().lower()
            verbose = _prompt_yesno("  ¿Mostrar diagnóstico de ubicación de leyenda?", default=False)
            try:
                apply_full_style(fig, key, apply_colors=apply_colors,
                                 apply_layout=apply_layout,
                                 legend_policy=legend_policy,
                                 verbose=verbose)
                _fe_preview_after_style_change(fig)
                print(f"  Estilo aplicado: {_FIGURE_STYLE_PRESETS[key].get('label', key)}")
            except Exception as e:
                print(f"  Error aplicando estilo: {e}")
            return fig
        elif op == "2":
            key = _menu_choose_from_mapping("Paletas de color / tonalidades", list_color_palettes())
            if not key:
                continue
            rebuild_legend = _prompt_yesno("  ¿Reconstruir la leyenda con la nueva paleta?", default=True)
            verbose = _prompt_yesno("  ¿Mostrar diagnóstico de ubicación de leyenda?", default=False)
            pol_default = "auto"
            try:
                first_ax = _data_axes(fig)[0]
                pol_default = _fe_current_legend_policy(first_ax)
            except Exception:
                pass
            legend_policy = _prompt("  Política de leyenda (auto/inside/outside/none)", pol_default).strip().lower()
            try:
                apply_color_palette(fig, key, rebuild_legend=rebuild_legend,
                                    legend_policy=legend_policy, verbose=verbose)
                print(f"  Paleta aplicada: {_FIGURE_COLOR_PALETTES[key].get('label', key)}")
            except Exception as e:
                print(f"  Error aplicando paleta: {e}")
            return fig
        elif op == "3":
            key = _menu_choose_from_mapping("Esquemas de marcadores + linestyles", list_marker_schemes())
            if not key:
                continue
            rebuild_legend = _prompt_yesno("  ¿Reconstruir la leyenda con el nuevo esquema?", default=True)
            verbose = _prompt_yesno("  ¿Mostrar diagnóstico de ubicación de leyenda?", default=False)
            pol_default = "auto"
            try:
                first_ax = _data_axes(fig)[0]
                pol_default = _fe_current_legend_policy(first_ax)
            except Exception:
                pass
            legend_policy = _prompt("  Política de leyenda (auto/inside/outside/none)", pol_default).strip().lower()
            try:
                apply_marker_scheme(fig, key, rebuild_legend=rebuild_legend,
                                    legend_policy=legend_policy, verbose=verbose)
                print(f"  Esquema aplicado: {_FIGURE_MARKER_SCHEMES[key].get('label', key)}")
            except Exception as e:
                print(f"  Error aplicando esquema: {e}")
            return fig
        elif op == "4":
            try:
                restore_original_format(fig)
                _fe_preview_after_style_change(fig)
                print("  Formato original restaurado desde el JSON cargado.")
            except Exception as e:
                print(f"  No se pudo restaurar el original: {e}")
            return fig
        elif op == "5":
            ref = input("  Ruta al JSON de referencia: ").strip().strip('"')
            if not ref:
                print("  Operación cancelada.")
                return fig
            try:
                apply_format_from_saved_figure(fig, ref)
                _fe_preview_after_style_change(fig)
                print("  Formato copiado desde la figura de referencia.")
            except Exception as e:
                print(f"  No se pudo copiar el formato: {e}")
            return fig
        elif op == "6":
            return fig
        else:
            print("  Opción inválida.")


_FIGURE_EDITOR_VERSION_NOTE = 'figure_editor15: palettes + marker schemes separated from editorial styles; 10 s preview for style/palette application'

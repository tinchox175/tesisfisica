# -*- coding: utf-8 -*-
r"""
figure_editor.py  —  v5 (format 43)  (edición por rol dato/ajuste + leyenda combinada)
================================================
Guardado, recuperación y EDICIÓN EN VIVO de figuras de Matplotlib.

Arquitectura en capas (una sola definición de cada cosa, sin shadowing):

    1. Serialización        figura  <->  dict JSON-able   (una única fuente de verdad)
    2. I/O                   load_figure / save_figure_data  (compatibles v3..v41)
    3. Exportación          PNG/PDF/SVG con bbox de contenido
    4. Controlador          FigureEditor  (toda la lógica de edición; cada cambio redibuja)
    5. UI en vivo           panel Qt acoplado (edit_cosmetics) + API programática

Compatibilidad: lee JSON de las versiones 3, 15, 17, 20, 21, 32, 36..40 producidas
por la versión anterior del script (datos inline en el JSON; el CSV es redundante
y se conserva por conveniencia). Escribe SIEMPRE format_version = 41 (superset).

API pública estable (no cambia respecto de la versión previa):
    save_figure_data(fig, filename, save_png=True, colorbar_labels=None)
    load_figure(filename, show=True)            -> Figure
    edit_cosmetics(fig, base_filename="figure") -> Figure

Nuevo (programático, totalmente testeable y reproducible):
    ed = FigureEditor(fig)
    ed.line(0, 0).set(color="C0", lw=1.4, marker="o", ms=5)
    ed.xlabel(0, r"Re$(Z)$ ($\Omega$)"); ed.legend(0, loc="upper right", ncol=2)
    ed.apply_palette("okabe_ito_safe"); ed.undo(); ed.save("figura")

@author: reescritura para Charly
"""
from __future__ import annotations

import json
import csv
import copy
import warnings
from pathlib import Path

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import collections as mcoll
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle, Patch
from matplotlib.container import BarContainer
from matplotlib.transforms import Bbox

# =============================================================================
#  Constantes
# =============================================================================
_FORMAT_VERSION = 43

_LOC_INT_TO_STR = {
    0: "best", 1: "upper right", 2: "upper left", 3: "lower left",
    4: "lower right", 5: "right", 6: "center left", 7: "center right",
    8: "lower center", 9: "upper center", 10: "center",
}

_DEFAULT_EXPORT_PREFS = {
    "bbox_mode": "content",          # exact | tight | content
    "pad_inches": 0.02,
    "autocrop_white": False,
    "autocrop_tol": 250,
    "autocrop_pad_px": 2,
    "content_include_suptitle": True,
}

# Atributos que el editor cuelga de la figura/artistas (con prefijo _fe_)
_REFLINE_TAG = "_fe_refline"

# Rol semántico de cada curva (persistente, sobrevive a la edición y al .json):
#   "data" = puntos experimentales (marcadores, sin línea de unión)
#   "fit"  = ajuste / modelo (línea, sin marcadores)
#   "mixed"= ambas cosas (ambiguo)
_ROLE_TAG = "_fe_role"
_ROLES = ("data", "fit", "mixed")
import re as _re
_AUTO_LABEL_RE = _re.compile(r"^(line|_line|_child)\d+$")


def _has_marker(ln):
    return ln.get_marker() not in (None, "", "None", " ")


def _has_line(ln):
    return str(ln.get_linestyle()) not in (None, "", "None", " ", "none")


def _classify_role(ln):
    """Devuelve el rol almacenado, o lo infiere del estado visual actual.

    La inferencia se usa SOLO la primera vez (ensure_roles la fija como tag);
    a partir de ahí el rol es estable aunque el usuario cambie marcador/línea."""
    tag = getattr(ln, _ROLE_TAG, None)
    if tag in _ROLES:
        return tag
    hm, hl = _has_marker(ln), _has_line(ln)
    if hm and not hl:
        return "data"
    if hl and not hm:
        return "fit"
    return "mixed"


def ensure_roles(ax_or_fig, hide_auto_labels=True):
    """Fija (una sola vez) el rol de cada curva no-refline de un eje o figura.

    Si `hide_auto_labels`, oculta de la leyenda las etiquetas autogeneradas
    de los datos experimentales (p.ej. 'line1', 'line3') anteponiendo '_',
    para que la leyenda no se multiplique al regenerarla."""
    axes = [ax_or_fig] if hasattr(ax_or_fig, "get_lines") else _data_axes(ax_or_fig)
    for ax in axes:
        for ln in ax.get_lines():
            if _is_refline(ax, ln) is not None:
                continue
            if getattr(ln, _ROLE_TAG, None) not in _ROLES:
                role = _classify_role(ln)
                setattr(ln, _ROLE_TAG, role)
                if (hide_auto_labels and role == "data"):
                    lab = str(ln.get_label() or "")
                    if _AUTO_LABEL_RE.match(lab):
                        ln.set_label("_" + lab)


def role_groups(ax):
    """{'data': [...], 'fit': [...], 'mixed': [...]} respetando el orden de trazado."""
    groups = {"data": [], "fit": [], "mixed": []}
    for ln in axis_inventory(ax)["lines"]:
        groups[_classify_role(ln)].append(ln)
    return groups


_PAIR_MODE_TAG = "_fe_pair_mode"   # 'order' (default) | 'proximity'
_COMBINED_LEG_TAG = "_fe_combined_legend"   # bool: handle marcador+línea por curva


def _line_points(ln):
    import numpy as _np
    x = _np.asarray(ln.get_xdata(), float)
    y = _np.asarray(ln.get_ydata(), float)
    m = _np.isfinite(x) & _np.isfinite(y)
    return x[m], y[m]


def _chamfer_norm(d, f, ax):
    """Distancia media (normalizada por el rango de cada eje) de cada punto de
    `d` a su vecino más cercano en `f`. Asimétrica pero suficiente para emparejar."""
    import numpy as _np
    xd, yd = _line_points(d)
    xf, yf = _line_points(f)
    if len(xd) == 0 or len(xf) == 0:
        return _np.inf
    (x0, x1) = ax.get_xlim(); (y0, y1) = ax.get_ylim()
    sx = abs(x1 - x0) or 1.0
    sy = abs(y1 - y0) or 1.0
    pd = _np.column_stack([(xd - x0) / sx, (yd - y0) / sy])
    pf = _np.column_stack([(xf - x0) / sx, (yf - y0) / sy])
    # vecino más cercano punto a punto (n*m, ok para ~40x40)
    dmin = _np.empty(len(pd))
    for i, p in enumerate(pd):
        dmin[i] = _np.min(_np.hypot(pf[:, 0] - p[0], pf[:, 1] - p[1]))
    return float(_np.mean(dmin))


def _pair_proximity(ax, data, fit):
    """Empareja datos con ajustes minimizando la distancia chamfer, de forma
    greedy (cada ajuste se usa una sola vez)."""
    pairs = []
    used = set()
    for d in data:
        best, bj = None, None
        for j, f in enumerate(fit):
            if j in used:
                continue
            dist = _chamfer_norm(d, f, ax)
            if best is None or dist < best:
                best, bj = dist, j
        if bj is not None:
            used.add(bj)
            pairs.append((d, fit[bj]))
        else:
            pairs.append((d, None))
    for j, f in enumerate(fit):
        if j not in used:
            pairs.append((None, f))
    return pairs


def pair_data_fit(ax):
    """Empareja dato↔ajuste. Modo según `ax._fe_pair_mode`:
       'order' (default): k-ésimo dato con k-ésimo ajuste (orden de trazado).
       'proximity': por cercanía de las curvas (distancia chamfer normalizada).
    Devuelve lista de (data_line | None, fit_line | None). Las 'mixed' van como (mixed, None)."""
    g = role_groups(ax)
    mode = getattr(ax, _PAIR_MODE_TAG, "order")
    if mode == "proximity" and g["data"] and g["fit"]:
        pairs = _pair_proximity(ax, g["data"], g["fit"])
    else:
        pairs = []
        n = max(len(g["data"]), len(g["fit"]))
        for k in range(n):
            d = g["data"][k] if k < len(g["data"]) else None
            f = g["fit"][k] if k < len(g["fit"]) else None
            pairs.append((d, f))
    for m in g["mixed"]:
        pairs.append((m, None))
    return pairs


def _partner_of(ax, ln):
    """Devuelve la curva emparejada con `ln` (su ajuste si es dato, o su dato si
    es ajuste), o None si no tiene pareja."""
    for d, f in pair_data_fit(ax):
        if d is ln:
            return f
        if f is ln:
            return d
    return None


def _target_lines(ax, target):
    """target in {'data','fit','both','all'} -> lista de líneas a tocar."""
    g = role_groups(ax)
    if target == "data":
        return g["data"] + g["mixed"]
    if target == "fit":
        return g["fit"] + g["mixed"]
    return g["data"] + g["fit"] + g["mixed"]  # both / all

# Marco por defecto para paneles individuales (split/recompose)
_DEFAULT_FRAME_PRESET = {"left": 0.11, "right": 0.98, "bottom": 0.11, "top": 0.98}


# =============================================================================
#  Helpers de bajo nivel
# =============================================================================
def _to_float(x, default=None):
    try:
        return float(x)
    except Exception:
        return x if default is None else default


def _jsonable(obj):
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


def _rgba(color):
    """[R,G,B,A] o el valor original si la conversión falla."""
    try:
        from matplotlib.colors import to_rgba
        return [float(c) for c in to_rgba(color)]
    except Exception:
        return _jsonable(color)


def _base_path(filename) -> Path:
    return Path(filename).with_suffix("")


def _data_axes(fig) -> list:
    """Ejes 'de datos' (descarta ejes diminutos, p.ej. colorbars sueltas)."""
    axes = list(getattr(fig, "axes", []))
    filtered = [ax for ax in axes
                if ax.get_position().width > 0.12 and ax.get_position().height > 0.12]
    return filtered if filtered else axes


def _linestyle_to_jsonable(ls):
    """linestyle puede ser str o tupla (offset,(on,off,...)). Lo hacemos JSON-able."""
    if isinstance(ls, (list, tuple)):
        return _jsonable(ls)
    return ls


# =============================================================================
#  Preferencias de exportación (colgadas de la figura)
# =============================================================================
def _get_export_prefs(fig, override=None) -> dict:
    prefs = dict(_DEFAULT_EXPORT_PREFS)
    for k in _DEFAULT_EXPORT_PREFS:
        v = getattr(fig, f"_fe_{k}", None)
        if v is not None:
            prefs[k] = v
    if override:
        prefs.update({k: v for k, v in override.items() if v is not None})
    return prefs


def _set_export_prefs(fig, prefs: dict):
    if not isinstance(prefs, dict):
        return
    for k in _DEFAULT_EXPORT_PREFS:
        if k in prefs and prefs[k] is not None:
            try:
                setattr(fig, f"_fe_{k}", prefs[k])
            except Exception:
                pass


# =============================================================================
#  SERIALIZACIÓN  (artista -> dict).  Nombres de campo idénticos a v40.
# =============================================================================
def _ser_text(t) -> dict:
    if t is None:
        return {"text": "", "fontsize": None, "fontweight": None,
                "fontstyle": None, "color": None, "visible": True}
    if isinstance(t, dict):
        return t
    try:
        return {
            "text": t.get_text(),
            "fontsize": _to_float(t.get_fontsize()),
            "fontweight": t.get_fontweight(),
            "fontstyle": t.get_fontstyle(),
            "color": _rgba(t.get_color()),
            "fontfamily": (t.get_fontfamily()[0] if t.get_fontfamily() else None),  # v41
            "visible": bool(t.get_visible()),
        }
    except Exception:
        return {"text": str(t), "fontsize": None, "fontweight": None,
                "fontstyle": None, "color": None, "visible": True}


def _apply_text(target, spec):
    if target is None:
        return
    if isinstance(spec, str):
        try:
            target.set_text(spec)
        except Exception:
            pass
        return
    if not isinstance(spec, dict):
        return
    for setter, key in [
        (target.set_text, "text"),
        (target.set_fontsize, "fontsize"),
        (target.set_fontweight, "fontweight"),
        (target.set_fontstyle, "fontstyle"),
        (target.set_color, "color"),
        (target.set_fontfamily, "fontfamily"),  # v41 (ignora si None)
    ]:
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


def _ser_annotation_bbox(txt):
    try:
        bp = txt.get_bbox_patch()
        if bp is None or not bp.get_visible():
            return None
        bs = bp.get_boxstyle()
        try:
            bsname = bs.stylename
        except AttributeError:
            bsname = type(bs).__name__.lower()
        return {
            "boxstyle": bsname,
            "facecolor": _rgba(bp.get_facecolor()),
            "edgecolor": _rgba(bp.get_edgecolor()),
            "linewidth": _to_float(bp.get_linewidth()),
            "alpha": _to_float(bp.get_alpha()) if bp.get_alpha() is not None else None,
            "pad": _to_float(getattr(bs, "pad", 0.3)),
        }
    except Exception:
        return None


def _apply_annotation_bbox(txt, spec):
    if spec is None:
        try:
            txt.set_bbox(None)
        except Exception:
            pass
        return
    try:
        boxstyle = f"{spec.get('boxstyle', 'round')},pad={spec.get('pad', 0.3)}"
        txt.set_bbox({
            "boxstyle": boxstyle,
            "facecolor": spec.get("facecolor", "white"),
            "edgecolor": spec.get("edgecolor", "black"),
            "linewidth": spec.get("linewidth", 1.0),
            "alpha": spec.get("alpha", 1.0),
        })
    except Exception:
        pass


def _ser_ticks(ax, axis="x") -> dict:
    axis_obj = ax.xaxis if axis == "x" else ax.yaxis
    labels = axis_obj.get_ticklabels()
    first = next((t for t in labels if t.get_text() or t.get_visible()),
                 labels[0] if labels else None)
    direction = "out"
    try:
        kw = getattr(axis_obj, "_major_tick_kw", {}) or {}
        direction = kw.get("tickdir", kw.get("direction", "out"))
    except Exception:
        pass
    # v41: longitud/grosor y minor ticks
    length = width = None
    try:
        ticks = axis_obj.get_major_ticks()
        if ticks:
            tk = ticks[0]
            length = _to_float(getattr(tk, "_size", None))
            width = _to_float(getattr(tk, "_width", None))
    except Exception:
        pass
    minor_on = False
    try:
        minor_on = len(axis_obj.get_minorticklocs()) > 0
    except Exception:
        pass
    return {
        "fontsize": _to_float(first.get_fontsize()) if first else None,
        "rotation": _to_float(first.get_rotation()) if first else None,
        "color": _rgba(first.get_color()) if first else None,
        "direction": direction,
        "length": length,      # v41
        "width": width,        # v41
        "minor": bool(minor_on),  # v41
    }


def _apply_ticks(ax, spec, axis="x"):
    if not isinstance(spec, dict):
        return
    params = {}
    if spec.get("fontsize") is not None:
        params["labelsize"] = spec["fontsize"]
    if spec.get("color") is not None:
        params["labelcolor"] = spec["color"]
        params["colors"] = spec["color"]
    if spec.get("direction") in {"in", "out", "inout"}:
        params["direction"] = spec["direction"]
    if spec.get("length") is not None:
        params["length"] = spec["length"]
    if spec.get("width") is not None:
        params["width"] = spec["width"]
    try:
        if params:
            ax.tick_params(axis=axis, **params)
    except Exception:
        pass
    if spec.get("minor"):
        try:
            ax.minorticks_on()
        except Exception:
            pass
    if spec.get("rotation") is not None:
        try:
            lbs = ax.get_xticklabels() if axis == "x" else ax.get_yticklabels()
            for lb in lbs:
                lb.set_rotation(spec["rotation"])
        except Exception:
            pass


def _ser_spines(ax) -> dict:
    out = {}
    for name, sp in ax.spines.items():
        try:
            out[name] = {
                "visible": bool(sp.get_visible()),
                "color": _rgba(sp.get_edgecolor()),
                "linewidth": _to_float(sp.get_linewidth()),
            }
        except Exception:
            out[name] = {"visible": True, "color": None, "linewidth": None}
    return out


def _apply_spines(ax, spines):
    if not spines:
        return
    for name, props in spines.items():
        if name not in ax.spines:
            continue
        sp = ax.spines[name]
        if props.get("visible") is not None:
            try:
                sp.set_visible(bool(props["visible"]))
            except Exception:
                pass
        if props.get("color") is not None:
            try:
                sp.set_edgecolor(props["color"])
            except Exception:
                pass
        if props.get("linewidth") is not None:
            try:
                sp.set_linewidth(float(props["linewidth"]))
            except Exception:
                pass


def _ser_grid(ax) -> dict:
    gl = [ln for ln in (ax.get_xgridlines() + ax.get_ygridlines()) if ln.get_visible()]
    props = {"visible": len(gl) > 0, "color": None, "linestyle": None,
             "linewidth": None, "alpha": None}
    if gl:
        try:
            ln = gl[0]
            props["color"] = _rgba(ln.get_color())
            props["linestyle"] = _linestyle_to_jsonable(ln.get_linestyle())
            props["linewidth"] = _to_float(ln.get_linewidth())
            props["alpha"] = _to_float(ln.get_alpha()) if ln.get_alpha() is not None else None
        except Exception:
            pass
    return props


def _apply_grid(ax, grid):
    if grid is True:
        ax.grid(True)
        return
    if grid in (False, None):
        ax.grid(False)
        return
    if isinstance(grid, bool):
        ax.grid(bool(grid))
        return
    visible = bool(grid.get("visible", False))
    kw = {k: grid[k] for k in ("color", "linestyle", "linewidth", "alpha")
          if grid.get(k) is not None}
    ax.grid(visible, **kw)


def _apply_rect_props(p: Rectangle, props: dict):
    for setter, key in [
        (p.set_facecolor, "facecolor"), (p.set_edgecolor, "edgecolor"),
        (p.set_linewidth, "linewidth"), (p.set_linestyle, "linestyle"),
        (p.set_alpha, "alpha"), (p.set_hatch, "hatch"),
        (p.set_zorder, "zorder"), (p.set_label, "label"),
    ]:
        if props.get(key) is not None:
            try:
                setter(props[key])
            except Exception:
                pass
    if props.get("visible") is not None:
        try:
            p.set_visible(bool(props["visible"]))
        except Exception:
            pass


def _is_refline(ax, line):
    """'v', 'h', o None."""
    tag = getattr(line, _REFLINE_TAG, None)
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
    lab = line.get_label()
    return {
        "label": lab if lab and not str(lab).startswith("_") else "",
        "color": _jsonable(line.get_color()),
        "linewidth": _to_float(line.get_linewidth()),
        "linestyle": _linestyle_to_jsonable(line.get_linestyle()),
        "marker": line.get_marker(),
        "markersize": _to_float(line.get_markersize()),
        "markerfacecolor": _jsonable(line.get_markerfacecolor()),
        "markeredgecolor": _jsonable(line.get_markeredgecolor()),
        "markeredgewidth": _to_float(line.get_markeredgewidth()),
        "alpha": _to_float(line.get_alpha()) if line.get_alpha() is not None else None,
        "visible": bool(line.get_visible()),
        "zorder": _to_float(line.get_zorder()) if line.get_zorder() is not None else None,
        # v41
        "drawstyle": line.get_drawstyle(),
        "fillstyle": line.get_fillstyle(),
        # v42: rol semántico persistente (data / fit / mixed)
        "role": _classify_role(line),
    }


def _ser_legend(ax):
    leg = ax.get_legend()
    if leg is None:
        return None
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
                "color": _rgba(h.get_color()),
                "linewidth": _to_float(h.get_linewidth()),
                "linestyle": _linestyle_to_jsonable(h.get_linestyle()),
                "marker": h.get_marker(),
                "markersize": _to_float(h.get_markersize()),
                "markerfacecolor": _rgba(h.get_markerfacecolor()),
                "markeredgecolor": _rgba(h.get_markeredgecolor()),
                "alpha": _to_float(h.get_alpha()) if h.get_alpha() is not None else None,
            }
        elif isinstance(h, Patch):
            hdict = {
                "kind": "Patch",
                "facecolor": _jsonable(h.get_facecolor()),
                "edgecolor": _jsonable(h.get_edgecolor()),
                "linewidth": _to_float(h.get_linewidth()),
                "linestyle": _linestyle_to_jsonable(h.get_linestyle()),
                "hatch": h.get_hatch(),
                "alpha": _to_float(h.get_alpha()) if h.get_alpha() is not None else None,
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
    loc_str = "best"
    try:
        loc_str = _LOC_INT_TO_STR.get(int(leg._loc), "best")
    except Exception:
        try:
            loc_str = str(leg.get_loc())
        except Exception:
            loc_str = "best"
    bba_point = None
    try:
        bba = leg.get_bbox_to_anchor()
        if bba is not None:
            b = bba._bbox.bounds
            if abs(float(b[2])) < 0.01 and abs(float(b[3])) < 0.01:
                bba_point = [float(b[0]), float(b[1])]
    except Exception:
        pass
    style = {"loc": loc_str, "bbox_to_anchor_point": bba_point}
    try:
        style["frameon"] = bool(leg.get_frame_on())
        frame = leg.get_frame()
        style["framealpha"] = _to_float(frame.get_alpha()) if frame.get_alpha() is not None else None
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
    style["combined"] = bool(getattr(ax, _COMBINED_LEG_TAG, False))
    return {"title": title, "entries": entries, "style": style}


def _legend_handle_from_spec(h: dict):
    h = h or {}
    kind = h.get("kind", "Line2D")
    if kind == "Patch":
        return Patch(facecolor=h.get("facecolor", "C0"),
                     edgecolor=h.get("edgecolor", "k"),
                     linewidth=h.get("linewidth", 1.0),
                     linestyle=h.get("linestyle", "-"),
                     hatch=h.get("hatch"),
                     alpha=h.get("alpha"))
    return Line2D([0], [0],
                  color=h.get("color", "C0"),
                  linewidth=h.get("linewidth", 1.5),
                  linestyle=h.get("linestyle", "-"),
                  marker=h.get("marker", ""),
                  markersize=h.get("markersize", 6.0),
                  markerfacecolor=h.get("markerfacecolor", h.get("color", "C0")),
                  markeredgecolor=h.get("markeredgecolor", h.get("color", "C0")),
                  alpha=h.get("alpha"))


def _rebuild_legend(ax, leginfo):
    if not leginfo or not isinstance(leginfo, dict):
        return None
    title = leginfo.get("title", "") or ""
    entries = leginfo.get("entries", []) or []
    style = leginfo.get("style", {}) or {}
    if not entries and not title:
        return None
    handles = [_legend_handle_from_spec((e or {}).get("handle", {})) for e in entries]
    labels = [e.get("label", "") for e in entries]
    loc = style.get("loc", "best")
    try:
        loc = _LOC_INT_TO_STR.get(int(loc), "best")
    except (TypeError, ValueError):
        pass
    kwargs = {}
    if loc:
        kwargs["loc"] = loc
    bba_pt = style.get("bbox_to_anchor_point")
    if bba_pt is not None:
        try:
            kwargs["bbox_to_anchor"] = (float(bba_pt[0]), float(bba_pt[1]))
        except Exception:
            pass
    else:
        bba_old = style.get("bbox_to_anchor_bounds")
        if bba_old is not None:
            try:
                x0, y0, w, h = [float(v) for v in bba_old]
                if abs(w) < 0.05 and abs(h) < 0.05:
                    kwargs["bbox_to_anchor"] = (x0, y0)
            except Exception:
                pass
    if style.get("frameon") is not None:
        kwargs["frameon"] = bool(style["frameon"])
    ncol = style.get("ncol", style.get("ncols"))
    if ncol is not None:
        try:
            kwargs["ncol"] = int(ncol)
        except Exception:
            pass
    for k in ("columnspacing", "labelspacing", "handlelength",
              "handletextpad", "borderpad", "borderaxespad"):
        if style.get(k) is not None:
            kwargs[k] = style[k]
    try:
        leg = ax.legend(handles, labels, title=title, **kwargs)
    except TypeError:
        leg = ax.legend(handles, labels, title=title,
                        loc=kwargs.get("loc", "best"),
                        frameon=kwargs.get("frameon", True))
    if leg is None:
        return None
    try:
        if style.get("title_fontsize") is not None:
            leg.get_title().set_fontsize(style["title_fontsize"])
    except Exception:
        pass
    try:
        if style.get("label_fontsize") is not None:
            for t in leg.get_texts():
                t.set_fontsize(style["label_fontsize"])
    except Exception:
        pass
    try:
        frame = leg.get_frame()
        if style.get("framealpha") is not None:
            frame.set_alpha(style["framealpha"])
        if style.get("frameedgecolor") is not None:
            frame.set_edgecolor(style["frameedgecolor"])
        if style.get("framefacecolor") is not None:
            frame.set_facecolor(style["framefacecolor"])
    except Exception:
        pass
    return leg


# =============================================================================
#  Leyenda a nivel FIGURA (compartida entre subplots)
# =============================================================================
def _ser_figure_legend(fig):
    legs = list(getattr(fig, "legends", []) or [])
    if not legs:
        return None
    leg = legs[0]
    handles = None
    for attr in ("legend_handles", "legendHandles"):
        handles = getattr(leg, attr, None)
        if handles is not None:
            break
    handles = handles or []
    labels = [t.get_text() for t in leg.get_texts()] if leg.get_texts() else []
    entries = []
    for h, lab in zip(handles, labels):
        if isinstance(h, Patch):
            hd = {"kind": "Patch", "facecolor": _jsonable(h.get_facecolor()),
                  "edgecolor": _jsonable(h.get_edgecolor()),
                  "linewidth": _to_float(h.get_linewidth()),
                  "hatch": h.get_hatch()}
        else:
            try:
                hd = {"kind": "Line2D", "color": _rgba(h.get_color()),
                      "linewidth": _to_float(h.get_linewidth()),
                      "linestyle": _linestyle_to_jsonable(h.get_linestyle()),
                      "marker": h.get_marker(),
                      "markersize": _to_float(h.get_markersize()),
                      "markerfacecolor": _rgba(h.get_markerfacecolor()),
                      "markeredgecolor": _rgba(h.get_markeredgecolor())}
            except Exception:
                hd = {"kind": "Line2D", "color": _rgba("k")}
        entries.append({"label": lab, "handle": hd})
    title = ""
    try:
        title = leg.get_title().get_text()
    except Exception:
        pass
    bbox = None
    try:
        bb = leg.get_bbox_to_anchor()
        if bb is not None:
            b = bb._bbox.bounds
            if abs(float(b[2])) < 0.01 and abs(float(b[3])) < 0.01:
                bbox = [float(b[0]), float(b[1])]
    except Exception:
        pass
    loc = "upper right"
    try:
        loc = _LOC_INT_TO_STR.get(int(leg._loc), "upper right")
    except Exception:
        pass
    style = {"loc": loc, "bbox_to_anchor": bbox,
             "ncol": int(getattr(leg, "_ncols", getattr(leg, "_ncol", 1))),
             "frameon": bool(leg.get_frame_on()),
             "title_fontsize": None, "label_fontsize": None}
    try:
        style["label_fontsize"] = _to_float(leg.get_texts()[0].get_fontsize()) if leg.get_texts() else None
        style["title_fontsize"] = _to_float(leg.get_title().get_fontsize())
    except Exception:
        pass
    return {"title": title, "entries": entries, "style": style}


def _rebuild_figure_legend(fig, info):
    if not info or not isinstance(info, dict):
        return None
    entries = info.get("entries", []) or []
    if not entries:
        return None
    style = info.get("style", {}) or {}
    handles = [_legend_handle_from_spec((e or {}).get("handle", {})) for e in entries]
    labels = [e.get("label", "") for e in entries]
    kw = {"loc": style.get("loc", "upper right"),
          "ncol": int(style.get("ncol", 1) or 1),
          "frameon": bool(style.get("frameon", True))}
    if style.get("bbox_to_anchor"):
        kw["bbox_to_anchor"] = tuple(style["bbox_to_anchor"])
    if style.get("label_fontsize"):
        kw["fontsize"] = style["label_fontsize"]
    try:
        leg = fig.legend(handles, labels, title=info.get("title", "") or None, **kw)
    except Exception:
        try:
            leg = fig.legend(handles, labels)
        except Exception:
            return None
    try:
        if style.get("title_fontsize") and leg.get_title():
            leg.get_title().set_fontsize(style["title_fontsize"])
    except Exception:
        pass
    return leg


# =============================================================================
#  figura  ->  dict   (serializador completo, una sola fuente de verdad)
# =============================================================================
def figure_to_props(fig) -> dict:
    """Serializa una Figure completa a un dict JSON-able (format_version 41)."""
    data_axes = _data_axes(fig)
    try:
        fig.canvas.draw()
    except Exception:
        pass

    serialize_positions = bool(getattr(fig, "_serialize_axes_positions", True))
    positions = [list(map(float, ax.get_position().bounds)) for ax in data_axes]
    if not serialize_positions:
        positions = [None for _ in positions]

    layout = (1, len(data_axes))
    try:
        ys = sorted({round(p[1], 3) for p in positions}, reverse=True)
        xs = sorted({round(p[0], 3) for p in positions})
        if len(ys) * len(xs) >= len(data_axes):
            layout = (len(ys), len(xs))
    except Exception:
        pass

    st = getattr(fig, "_suptitle", None)
    suptitle_spec = _ser_text(st) if st is not None and st.get_text() else {"text": ""}

    save_subplots_adjust_none = bool(getattr(fig, "_save_subplots_adjust_none", False))
    try:
        sp = fig.subplotpars
        adj = {"left": _to_float(sp.left), "right": _to_float(sp.right),
               "top": _to_float(sp.top), "bottom": _to_float(sp.bottom),
               "wspace": _to_float(sp.wspace), "hspace": _to_float(sp.hspace)}
        if save_subplots_adjust_none:
            adj = None
    except Exception:
        adj = None if save_subplots_adjust_none else {}

    # textos a nivel figura (no pertenecientes a un axes) — v41
    fig_texts = []
    try:
        for t in getattr(fig, "texts", []):
            if t is st:
                continue
            if not (t.get_text() or "").strip():
                continue
            fig_texts.append({
                "text": t.get_text(),
                "x": _to_float(t.get_position()[0]),
                "y": _to_float(t.get_position()[1]),
                "fontsize": _to_float(t.get_fontsize()),
                "fontweight": t.get_fontweight(),
                "fontstyle": t.get_fontstyle(),
                "color": _rgba(t.get_color()),
                "ha": t.get_ha(), "va": t.get_va(),
                "rotation": _to_float(t.get_rotation()),
                "fontfamily": (t.get_fontfamily()[0] if t.get_fontfamily() else None),  # parche v8: round-trip de familia
            })
    except Exception:
        pass

    props = {
        "format_version": _FORMAT_VERSION,
        "size": _jsonable(fig.get_size_inches()),
        "dpi": _to_float(fig.dpi) if hasattr(fig, "dpi") else None,
        "figure_facecolor": _rgba(fig.get_facecolor()),
        "subplot_layout": _jsonable(layout),
        "subplots_adjust": adj,
        "suptitle": suptitle_spec.get("text", ""),
        "suptitle_obj": suptitle_spec,
        "figure_texts": fig_texts,                       # v41
        "figure_legend": _ser_figure_legend(fig),        # v42
        "export_prefs": _jsonable(_get_export_prefs(fig)),
        "layout_engine": {
            "serialize_positions": serialize_positions,
            "apply_tight_layout_on_load": bool(getattr(fig, "_apply_tight_layout_on_load", False)),
            "save_subplots_adjust_none": save_subplots_adjust_none,
        },
        "axes": [],
    }

    for idx, ax in enumerate(data_axes):
        axp = {
            "title": _ser_text(ax.title),
            "xlabel": _ser_text(ax.xaxis.label),
            "ylabel": _ser_text(ax.yaxis.label),
            "xlim": _jsonable(ax.get_xlim()),
            "ylim": _jsonable(ax.get_ylim()),
            "xscale": ax.get_xscale(),
            "yscale": ax.get_yscale(),
            "facecolor": _rgba(ax.get_facecolor()),
            "position": _jsonable(positions[idx]),
            "aspect": ax.get_aspect(),
            "spines": _ser_spines(ax),
            "grid": _ser_grid(ax),
            "ticks": {"x": _ser_ticks(ax, "x"), "y": _ser_ticks(ax, "y")},
            "lines": [], "scatters": [], "vlines": [], "hlines": [],
            "bars": [], "line_collections": [], "images": [], "texts": [],
            "legend": _ser_legend(ax),
            "shared_legend": copy.deepcopy(getattr(ax, "_fe_shared_legend", None)),
            "pair_mode": getattr(ax, _PAIR_MODE_TAG, "order"),
        }
        # líneas / reflines
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
            kind = _is_refline(ax, line)
            if kind == "v":
                entry["x"] = _to_float(xd[0], 0.0)
                axp["vlines"].append(entry)
            elif kind == "h":
                entry["y"] = _to_float(yd[0], 0.0)
                axp["hlines"].append(entry)
            else:
                line_count += 1
                if not entry["label"]:
                    # Etiqueta de relleno OCULTA (prefijo '_'): identifica la curva
                    # en el árbol/CSV pero no aparece en la leyenda automática.
                    entry["label"] = f"_line{line_count}"
                entry["x"] = xd
                entry["y"] = yd
                axp["lines"].append(entry)
        # barras
        seen = set()
        for cont in [c for c in getattr(ax, "containers", []) if isinstance(c, BarContainer)]:
            ci = {"label": cont.get_label() if hasattr(cont, "get_label") else "", "patches": []}
            for p in getattr(cont, "patches", []):
                seen.add(id(p))
                ci["patches"].append(_ser_bar_patch(p))
            if ci["patches"]:
                axp["bars"].append(ci)
        for p in ax.patches:
            if id(p) in seen or not isinstance(p, Rectangle):
                continue
            axp["bars"].append({"label": "", "patches": [_ser_bar_patch(p, loose=True)]})
        # imágenes
        for im in getattr(ax, "images", []):
            try:
                arr = np.asarray(im.get_array())
                axp["images"].append({
                    "array": _jsonable(arr),
                    "extent": _jsonable(im.get_extent()) if hasattr(im, "get_extent") else None,
                    "origin": getattr(im, "origin", "upper"),
                    "interpolation": im.get_interpolation() if hasattr(im, "get_interpolation") else None,
                    "cmap": im.get_cmap().name if getattr(im, "get_cmap", None) and im.get_cmap() else None,
                    "alpha": _to_float(im.get_alpha()) if im.get_alpha() is not None else None,
                    "vmin": _to_float(getattr(im.norm, "vmin", None)),
                    "vmax": _to_float(getattr(im.norm, "vmax", None)),
                })
            except Exception:
                pass
        # scatters / line_collections
        for coll in ax.collections:
            if isinstance(coll, mcoll.PathCollection):
                try:
                    offs = np.asarray(coll.get_offsets())
                    x = offs[:, 0].tolist() if offs.size else []
                    y = offs[:, 1].tolist() if offs.size else []
                    fc = coll.get_facecolors()
                    ec = coll.get_edgecolors()
                    lab = coll.get_label() if coll.get_label() and not str(coll.get_label()).startswith("_") else ""
                    axp["scatters"].append({
                        "x": _jsonable(x), "y": _jsonable(y),
                        "s": _jsonable(coll.get_sizes().tolist()) if hasattr(coll, "get_sizes") else None,
                        "color": _jsonable(fc.tolist()) if getattr(fc, "size", 0) else None,
                        "edgecolors": _jsonable(ec.tolist()) if getattr(ec, "size", 0) else None,
                        "alpha": _to_float(coll.get_alpha()) if coll.get_alpha() is not None else None,
                        "label": lab,
                        "cmap": coll.get_cmap().name if getattr(coll, "get_cmap", None) and coll.get_cmap() else None,
                        "vmin": _to_float(getattr(coll.norm, "vmin", None)) if getattr(coll, "norm", None) else None,
                        "vmax": _to_float(getattr(coll.norm, "vmax", None)) if getattr(coll, "norm", None) else None,
                    })
                except Exception:
                    pass
            elif isinstance(coll, mcoll.LineCollection):
                try:
                    axp["line_collections"].append({
                        "segments": _jsonable(coll.get_segments()),
                        "colors": _jsonable(coll.get_colors()),
                        "linewidths": _jsonable(coll.get_linewidths()),
                        "linestyles": _jsonable(coll.get_linestyles()),
                        "alpha": _to_float(coll.get_alpha()) if coll.get_alpha() is not None else None,
                        "zorder": _to_float(coll.get_zorder()) if coll.get_zorder() is not None else None,
                        "label": coll.get_label() if coll.get_label() and not str(coll.get_label()).startswith("_") else "",
                    })
                except Exception:
                    pass
        # textos / anotaciones
        skip = {ax.title, ax.xaxis.label, ax.yaxis.label}
        for txt in ax.texts:
            if txt in skip:
                continue
            try:
                axp["texts"].append({
                    "text": txt.get_text(),
                    "x": _to_float(txt.get_position()[0]),
                    "y": _to_float(txt.get_position()[1]),
                    "transform": "axes" if txt.get_transform() == ax.transAxes else "data",
                    "fontsize": _to_float(txt.get_fontsize()),
                    "fontweight": txt.get_fontweight(),
                    "fontstyle": txt.get_fontstyle(),
                    "color": _rgba(txt.get_color()),
                    "ha": txt.get_ha(),
                    "va": txt.get_va(),
                    "rotation": _to_float(txt.get_rotation()),
                    "alpha": _to_float(txt.get_alpha()) if txt.get_alpha() is not None else None,
                    "bbox": _ser_annotation_bbox(txt),
                })
            except Exception:
                pass
        props["axes"].append(axp)
    return props


def _ser_bar_patch(p, loose=False):
    return {
        "x": _to_float(p.get_x()), "y": _to_float(p.get_y()),
        "width": _to_float(p.get_width()), "height": _to_float(p.get_height()),
        "angle": _to_float(getattr(p, "angle", 0.0)),
        "facecolor": _jsonable(p.get_facecolor()),
        "edgecolor": _jsonable(p.get_edgecolor()),
        "linewidth": _to_float(p.get_linewidth()),
        "linestyle": p.get_linestyle(),
        "hatch": p.get_hatch(),
        "alpha": _to_float(p.get_alpha()) if p.get_alpha() is not None else None,
        "label": "" if loose else (p.get_label() if p.get_label() and not str(p.get_label()).startswith("_") else ""),
        "visible": bool(p.get_visible()),
        "zorder": _to_float(p.get_zorder()) if p.get_zorder() is not None else None,
    }


# =============================================================================
#  Normalización (retrocompatibilidad v3..v40)
# =============================================================================
def _normalize_axd(axd: dict) -> dict:
    axd = dict(axd or {})
    for key in ("title", "xlabel", "ylabel"):
        v = axd.get(key)
        if isinstance(v, str):
            axd[key] = {"text": v, "fontsize": None, "fontweight": None,
                        "fontstyle": None, "color": None, "visible": True}
    if "ticks" not in axd:
        axd["ticks"] = {"x": axd.get("xticks", {}), "y": axd.get("yticks", {})}
    if "images" not in axd and "heatmaps" in axd:
        axd["images"] = axd.get("heatmaps", [])
    leg = axd.get("legend")
    if isinstance(leg, dict):
        if not (leg.get("entries") or []) and not (leg.get("title") or ""):
            axd["legend"] = None
    return axd


# =============================================================================
#  dict  ->  figura   (constructor; sirve para load_figure y para undo/redo)
# =============================================================================
def apply_props_to_figure(props: dict, fig=None, show=False):
    """Construye (o repuebla) una figura desde un dict de propiedades.

    Si fig is None crea una nueva. Si se pasa una figura, la limpia y la repuebla
    (se usa para undo/redo manteniendo la misma ventana)."""
    axes_data = [_normalize_axd(a) for a in props.get("axes", [])]

    if fig is None:
        fig = plt.figure(figsize=props.get("size", (8, 4)))
    else:
        fig.clf()
        try:
            fig.set_size_inches(props.get("size", fig.get_size_inches()))
        except Exception:
            pass

    if props.get("dpi") is not None:
        try:
            fig.set_dpi(props["dpi"])
        except Exception:
            pass
    if props.get("figure_facecolor") is not None:
        try:
            fig.patch.set_facecolor(props["figure_facecolor"])
        except Exception:
            pass

    st_spec = props.get("suptitle_obj", props.get("suptitle", ""))
    st_spec = _ser_text(st_spec) if isinstance(st_spec, str) else (st_spec or {})
    if st_spec.get("text"):
        try:
            fig.suptitle(st_spec["text"])
            _apply_text(getattr(fig, "_suptitle", None), st_spec)
        except Exception:
            pass

    positions = [a.get("position") for a in axes_data]
    le = props.get("layout_engine", {}) if isinstance(props.get("layout_engine"), dict) else {}
    serialize_positions = bool(le.get("serialize_positions", True))
    apply_tl = bool(le.get("apply_tight_layout_on_load", False))
    fig._serialize_axes_positions = serialize_positions
    fig._apply_tight_layout_on_load = apply_tl
    fig._save_subplots_adjust_none = bool(le.get("save_subplots_adjust_none", False))

    use_pos = serialize_positions and all(
        isinstance(p, (list, tuple)) and len(p) == 4 for p in positions) and len(positions) > 0
    if use_pos:
        axes = [fig.add_axes(p) for p in positions]
    else:
        nrows, ncols = props.get("subplot_layout", (1, max(1, len(axes_data))))
        try:
            nrows, ncols = int(nrows), int(ncols)
        except Exception:
            nrows, ncols = 1, max(1, len(axes_data))
        sub = fig.subplots(nrows, ncols)
        axes = np.atleast_1d(sub).ravel().tolist()

    for i, axd in enumerate(axes_data):
        ax = axes[i]
        for fn, key in [(ax.set_xscale, "xscale"), (ax.set_yscale, "yscale")]:
            if axd.get(key):
                try:
                    fn(axd[key])
                except Exception:
                    pass
        _apply_text(ax.title, axd.get("title", {}))
        _apply_text(ax.xaxis.label, axd.get("xlabel", {}))
        _apply_text(ax.yaxis.label, axd.get("ylabel", {}))
        if axd.get("xlim") is not None:
            ax.set_xlim(axd["xlim"])
        if axd.get("ylim") is not None:
            ax.set_ylim(axd["ylim"])
        if axd.get("facecolor") is not None:
            try:
                ax.set_facecolor(axd["facecolor"])
            except Exception:
                pass
        _apply_spines(ax, axd.get("spines", {}))
        _apply_grid(ax, axd.get("grid"))
        if axd.get("position") is not None:
            try:
                ax.set_position(axd["position"])
            except Exception:
                pass
        # imágenes
        for img in axd.get("images", []) or []:
            arr = np.asarray(img.get("array", img.get("data", [])))
            if arr.size == 0:
                continue
            kw = {k: img[k] for k in ("origin", "interpolation", "cmap", "alpha")
                  if img.get(k) is not None}
            if img.get("extent") is not None:
                kw["extent"] = img["extent"]
            if img.get("vmin") is not None:
                kw["vmin"] = img["vmin"]
            if img.get("vmax") is not None:
                kw["vmax"] = img["vmax"]
            try:
                ax.imshow(arr, **kw)
            except Exception:
                pass
        # líneas
        for line in axd.get("lines", []) or []:
            try:
                ln, = ax.plot(line.get("x", []), line.get("y", []),
                              label=line.get("label", ""),
                              color=line.get("color"),
                              linewidth=line.get("linewidth", 1.5),
                              linestyle=line.get("linestyle", "-"),
                              marker=line.get("marker", ""),
                              markersize=line.get("markersize", 6.0))
                for setter, key in [
                    (ln.set_markerfacecolor, "markerfacecolor"),
                    (ln.set_markeredgecolor, "markeredgecolor"),
                    (ln.set_markeredgewidth, "markeredgewidth"),
                    (ln.set_alpha, "alpha"),
                    (ln.set_zorder, "zorder"),
                    (ln.set_drawstyle, "drawstyle"),
                    (ln.set_fillstyle, "fillstyle"),
                ]:
                    if line.get(key) is not None:
                        try:
                            setter(line[key])
                        except Exception:
                            pass
                if line.get("visible") is not None:
                    ln.set_visible(bool(line["visible"]))
                if line.get("role") in _ROLES:
                    setattr(ln, _ROLE_TAG, line["role"])
            except Exception:
                pass
        # vlines / hlines
        for v in axd.get("vlines", []) or []:
            try:
                ln = ax.axvline(x=v.get("x", v.get("value", 0)),
                                color=v.get("color", "k"),
                                linewidth=v.get("linewidth", 1),
                                linestyle=v.get("linestyle", "-"),
                                alpha=v.get("alpha", 1.0))
                setattr(ln, _REFLINE_TAG, "v")
                if v.get("label"):
                    ln.set_label(v["label"])
                if v.get("visible") is not None:
                    ln.set_visible(bool(v["visible"]))
            except Exception:
                pass
        for hh in axd.get("hlines", []) or []:
            try:
                ln = ax.axhline(y=hh.get("y", hh.get("value", 0)),
                                color=hh.get("color", "k"),
                                linewidth=hh.get("linewidth", 1),
                                linestyle=hh.get("linestyle", "-"),
                                alpha=hh.get("alpha", 1.0))
                setattr(ln, _REFLINE_TAG, "h")
                if hh.get("label"):
                    ln.set_label(hh["label"])
                if hh.get("visible") is not None:
                    ln.set_visible(bool(hh["visible"]))
            except Exception:
                pass
        # barras
        for cont in axd.get("bars", []) or []:
            patches = []
            for bp in cont.get("patches", []) or []:
                rect = Rectangle((bp.get("x", 0), bp.get("y", 0)),
                                 bp.get("width", 0), bp.get("height", 0),
                                 angle=bp.get("angle", 0))
                _apply_rect_props(rect, bp)
                ax.add_patch(rect)
                patches.append(rect)
            if patches:
                try:
                    ax.add_container(BarContainer(patches, errorbar=None, label=cont.get("label")))
                except Exception:
                    pass
        # scatters
        for scd in axd.get("scatters", []) or []:
            x, y = scd.get("x", []), scd.get("y", [])
            if len(x) != len(y):
                continue
            try:
                cmap = plt.get_cmap(scd["cmap"]) if scd.get("cmap") else None
                kw = {}
                if scd.get("alpha") is not None:
                    kw["alpha"] = scd["alpha"]
                if scd.get("label"):
                    kw["label"] = scd["label"]
                if scd.get("s") is not None:
                    kw["s"] = scd["s"]
                c_data = scd.get("color")
                if c_data is not None:
                    c_arr = np.asarray(c_data)
                    kw["c"] = c_data
                    if not (c_arr.ndim == 2 and c_arr.shape[1] in (3, 4)):
                        if cmap is not None:
                            kw["cmap"] = cmap
                        if scd.get("vmin") is not None:
                            kw["vmin"] = scd["vmin"]
                        if scd.get("vmax") is not None:
                            kw["vmax"] = scd["vmax"]
                ax.scatter(x, y, **kw)
            except Exception:
                pass
        # line collections
        for lcd in axd.get("line_collections", []) or []:
            try:
                coll = mcoll.LineCollection(lcd.get("segments"),
                                            colors=lcd.get("colors"),
                                            linewidths=lcd.get("linewidths"),
                                            linestyles=lcd.get("linestyles"))
                if lcd.get("alpha") is not None:
                    coll.set_alpha(lcd["alpha"])
                if lcd.get("zorder") is not None:
                    coll.set_zorder(lcd["zorder"])
                if lcd.get("label"):
                    coll.set_label(lcd["label"])
                ax.add_collection(coll)
            except Exception:
                pass
        # textos
        for td in axd.get("texts", []) or []:
            try:
                tr = ax.transAxes if td.get("transform") == "axes" else ax.transData
                kw = {k: td[k] for k in ("fontsize", "color", "ha", "va", "rotation", "alpha")
                      if td.get(k) is not None}
                t = ax.text(td.get("x", 0), td.get("y", 0), td.get("text", ""),
                            transform=tr, **kw)
                if td.get("fontweight") is not None:
                    t.set_fontweight(td["fontweight"])
                if td.get("fontstyle") is not None:
                    t.set_fontstyle(td["fontstyle"])
                _apply_annotation_bbox(t, td.get("bbox"))
            except Exception:
                pass
        try:
            ax._fe_shared_legend = copy.deepcopy(axd.get("shared_legend"))
        except Exception:
            pass
        try:
            setattr(ax, _PAIR_MODE_TAG, axd.get("pair_mode", "order") or "order")
            _leg = axd.get("legend") or {}
            setattr(ax, _COMBINED_LEG_TAG,
                    bool((_leg.get("style") or {}).get("combined", False)))
        except Exception:
            pass
        _rebuild_legend(ax, axd.get("legend"))
        ticks = axd.get("ticks", {}) if isinstance(axd.get("ticks"), dict) else {}
        _apply_ticks(ax, ticks.get("x", {}), "x")
        _apply_ticks(ax, ticks.get("y", {}), "y")

    # textos a nivel figura (v41)
    for ft in props.get("figure_texts", []) or []:
        try:
            kw = {k: ft[k] for k in ("fontsize", "color", "ha", "va", "rotation")
                  if ft.get(k) is not None}
            t = fig.text(ft.get("x", 0.5), ft.get("y", 0.5), ft.get("text", ""), **kw)
            if ft.get("fontweight") is not None:
                t.set_fontweight(ft["fontweight"])
            if ft.get("fontstyle") is not None:
                t.set_fontstyle(ft["fontstyle"])
            if ft.get("fontfamily") is not None:        # parche v8: restaura familia
                try:
                    t.set_fontfamily(ft["fontfamily"])
                except Exception:
                    pass
        except Exception:
            pass

    # leyenda a nivel figura (v42) — después de construir todos los ejes
    try:
        _rebuild_figure_legend(fig, props.get("figure_legend"))
    except Exception:
        pass

    adj = props.get("subplots_adjust")
    if adj and isinstance(adj, dict) and any(v is not None for v in adj.values()):
        try:
            fig.subplots_adjust(**{k: v for k, v in adj.items() if v is not None})
        except Exception:
            pass
    if apply_tl and not use_pos:
        try:
            fig.tight_layout()
        except Exception:
            pass
    try:
        _set_export_prefs(fig, props.get("export_prefs", {}))
    except Exception:
        pass

    if show:
        _show_nonblocking(fig)
    return fig


# =============================================================================
#  I/O público
# =============================================================================
def load_figure(filename, show=True):
    """Carga y reconstruye una figura desde su JSON (v3..v41)."""
    json_path = Path(filename)
    if json_path.suffix.lower() != ".json":
        json_path = json_path.with_suffix(".json")
    with open(json_path, "r", encoding="utf-8") as f:
        props = json.load(f)
    fig = apply_props_to_figure(props, fig=None, show=False)
    try:
        ensure_roles(fig)  # fija roles y oculta etiquetas auto antes de cualquier leyenda
    except Exception:
        pass
    try:
        fig._fe_base_filename = str(json_path.with_suffix(""))
        fig._fe_source_json_path = str(json_path)
    except Exception:
        pass
    if show:
        _show_nonblocking(fig)
    return fig


def save_figure_data(fig, filename, save_png=True, colorbar_labels=None):
    """Guarda cosmética+datos (.json), datos numéricos (.csv) y miniatura (.png).

    Mantiene el CSV por compatibilidad: una fila por punto con columnas
    axis_index, artist_type, label, x, y (líneas y scatters)."""
    base = _base_path(filename)
    props = figure_to_props(fig)

    with open(base.with_suffix(".json"), "w", encoding="utf-8") as f:
        json.dump(_jsonable(props), f, indent=4, ensure_ascii=False)

    # CSV (redundante, conveniencia)
    rows = []
    for idx, axp in enumerate(props["axes"]):
        for ln in axp.get("lines", []):
            for x, y in zip(ln.get("x", []), ln.get("y", [])):
                rows.append([idx, "line", ln.get("label", ""), x, y])
        for sc in axp.get("scatters", []):
            for x, y in zip(sc.get("x", []), sc.get("y", [])):
                rows.append([idx, "scatter", sc.get("label", ""), x, y])
    with open(base.with_suffix(".csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["axis_index", "artist_type", "label", "x", "y"])
        w.writerows(rows)

    if save_png:
        try:
            _save_figure_image(fig, base.with_suffix(".png"), dpi=300,
                               prefs=_get_export_prefs(fig))
        except Exception:
            pass
    try:
        fig._fe_base_filename = str(base)
    except Exception:
        pass
    print(f"Guardado: {base}.json / .csv" + (" / .png" if save_png else ""))
    return str(base)


# =============================================================================
#  Exportación de imagen (bbox de contenido)
# =============================================================================
def _compute_content_bbox_inches(fig, pad_inches=0.02, include_suptitle=True):
    try:
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
    except Exception:
        return None
    boxes = []
    for ax in _data_axes(fig):
        try:
            extra = list(ax.get_default_bbox_extra_artists())
        except Exception:
            extra = []
        try:
            bb = ax.get_tightbbox(renderer, bbox_extra_artists=extra)
            if bb is None:
                bb = ax.get_window_extent(renderer)
            if bb is not None and bb.width > 1 and bb.height > 1:
                boxes.append(bb)
        except Exception:
            pass
    if include_suptitle:
        extra_artists = []
        st = getattr(fig, "_suptitle", None)
        if st is not None and st.get_visible() and (st.get_text() or "").strip():
            extra_artists.append(st)
        extra_artists += [t for t in getattr(fig, "texts", [])
                          if getattr(t, "axes", None) is None and t.get_visible()
                          and (t.get_text() or "").strip()]
        for art in extra_artists:
            try:
                bb = art.get_window_extent(renderer)
                if bb is not None and bb.width > 1 and bb.height > 1:
                    boxes.append(bb)
            except Exception:
                pass
    if not boxes:
        return None
    ub = Bbox.union(boxes)
    try:
        ub_in = ub.transformed(fig.dpi_scale_trans.inverted())
    except Exception:
        dpi = float(getattr(fig, "dpi", 100.0) or 100.0)
        ub_in = Bbox.from_extents(ub.x0 / dpi, ub.y0 / dpi, ub.x1 / dpi, ub.y1 / dpi)
    pad_inches = max(0.0, float(pad_inches))
    if pad_inches:
        ub_in = ub_in.expanded((ub_in.width + 2 * pad_inches) / max(ub_in.width, 1e-9),
                               (ub_in.height + 2 * pad_inches) / max(ub_in.height, 1e-9))
    return ub_in


def _crop_white_margins_array(arr, tol=250, pad_px=2):
    a = arr[..., :3] if arr.ndim == 3 and arr.shape[2] >= 3 else arr
    mask = np.any(a < tol, axis=2) if a.ndim == 3 else (a < tol)
    if not mask.any():
        return arr
    ys, xs = np.where(mask)
    y0, y1 = max(ys.min() - pad_px, 0), min(ys.max() + pad_px + 1, arr.shape[0])
    x0, x1 = max(xs.min() - pad_px, 0), min(xs.max() + pad_px + 1, arr.shape[1])
    return arr[y0:y1, x0:x1]


def _crop_saved_png_inplace(path, tol=250, pad_px=2):
    try:
        import matplotlib.image as mpimg
        arr = mpimg.imread(str(path))
        arr8 = (arr * 255).astype(np.uint8) if arr.dtype.kind == "f" else arr
        cropped = _crop_white_margins_array(arr8, tol=tol, pad_px=pad_px)
        mpimg.imsave(str(path), cropped)
    except Exception:
        pass


def _save_figure_image(fig, out_path, fmt=None, dpi=300, prefs=None):
    out = Path(out_path)
    prefs = _get_export_prefs(fig, prefs)
    save_kw = {"dpi": dpi}
    mode = prefs.get("bbox_mode", "content")
    if mode == "tight":
        save_kw["bbox_inches"] = "tight"
        save_kw["pad_inches"] = prefs["pad_inches"]
    elif mode == "content":
        bb = _compute_content_bbox_inches(fig, pad_inches=prefs.get("pad_inches", 0.02),
                                          include_suptitle=prefs.get("content_include_suptitle", True))
        if bb is not None:
            save_kw["bbox_inches"] = bb
        else:
            save_kw["bbox_inches"] = "tight"
            save_kw["pad_inches"] = prefs["pad_inches"]
    fig.savefig(out, **save_kw)
    if out.suffix.lower() == ".png" and prefs.get("autocrop_white", False):
        _crop_saved_png_inplace(out, tol=prefs.get("autocrop_tol", 250),
                                pad_px=prefs.get("autocrop_pad_px", 2))
    return out


def export_image(fig, path, dpi=300, bbox_mode=None, pad_inches=None):
    """Exporta a PNG/PDF/SVG. bbox_mode: 'content' (default), 'tight' o 'exact'."""
    override = {}
    if bbox_mode is not None:
        override["bbox_mode"] = bbox_mode
    if pad_inches is not None:
        override["pad_inches"] = pad_inches
    prefs = _get_export_prefs(fig, override)
    return _save_figure_image(fig, path, dpi=dpi, prefs=prefs)


# =============================================================================
#  Backend / refresco
# =============================================================================
def _is_interactive_backend() -> bool:
    try:
        return matplotlib.get_backend().lower() not in ("agg", "pdf", "ps", "svg", "cairo", "template")
    except Exception:
        return False


def _show_nonblocking(fig):
    if not _is_interactive_backend():
        return
    try:
        plt.show(block=False)
        fig.canvas.draw_idle()
        fig.canvas.flush_events()
    except Exception:
        try:
            plt.show()
        except Exception:
            pass

# =============================================================================
#  PALETAS DE COLOR  (variadas, de fuentes reconocidas)
# =============================================================================
#  Fuentes:
#   - Okabe & Ito (2008), "Color Universal Design" (colorblind-safe).
#   - Paul Tol (2021), "Colour schemes" technical note SRON/v3.2 (bright, vibrant,
#     muted, high-contrast, light) — pensadas para ciencia y daltonismo.
#   - Tableau 10 / Tableau 20 (categóricas clásicas, alta variedad).
#   - ColorBrewer (Harrower & Brewer 2003): Set1/Set2/Set3/Dark2/Paired/Accent.
#   - Matplotlib qualitative cmaps: tab10/tab20/tab20b/tab20c.
#  Para >10 series usá una paleta con muchos colores (tab20, Set3, Paired,
#  distinct_20) para evitar repeticiones.

_PAL_HARDCODED = {
    "okabe_ito": ("Okabe-Ito (colorblind-safe, 8)",
                  ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#56B4E9",
                   "#CC79A7", "#F0E442", "#000000"]),
    "tol_bright": ("Tol bright (7, CB-safe)",
                   ["#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE",
                    "#AA3377", "#BBBBBB"]),
    "tol_vibrant": ("Tol vibrant (7, CB-safe)",
                    ["#0077BB", "#EE7733", "#009988", "#CC3311", "#33BBEE",
                     "#EE3377", "#BBBBBB"]),
    "tol_muted": ("Tol muted (10, CB-safe)",
                  ["#332288", "#88CCEE", "#44AA99", "#117733", "#999933",
                   "#DDCC77", "#CC6677", "#882255", "#AA4499", "#DDDDDD"]),
    "tol_high_contrast": ("Tol high-contrast (4, CB-safe)",
                          ["#004488", "#DDAA33", "#BB5566", "#000000"]),
    "tol_light": ("Tol light (9, CB-safe)",
                  ["#77AADD", "#EE8866", "#EEDD88", "#FFAABB", "#99DDFF",
                   "#44BB99", "#BBCC33", "#AAAA00", "#DDDDDD"]),
    "tableau10": ("Tableau 10 (variada)",
                  ["#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F",
                   "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC"]),
    "tableau20": ("Tableau 20 (muy variada)",
                  ["#4E79A7", "#A0CBE8", "#F28E2B", "#FFBE7D", "#59A14F",
                   "#8CD17D", "#B6992D", "#F1CE63", "#499894", "#86BCB6",
                   "#E15759", "#FF9D9A", "#79706E", "#BAB0AC", "#D37295",
                   "#FABFD2", "#B07AA1", "#D4A6C8", "#9D7660", "#D7B5A6"]),
    "distinct_20": ("20 colores máx. distintos",
                    ["#E6194B", "#3CB44B", "#4363D8", "#F58231", "#911EB4",
                     "#46F0F0", "#F032E6", "#BCF60C", "#FABEBE", "#008080",
                     "#E6BEFF", "#9A6324", "#800000", "#AAFFC3", "#808000",
                     "#FFD8B1", "#000075", "#808080", "#FFE119", "#000000"]),
}

# ColorBrewer / matplotlib qualitative: se extraen del cmap (evita errores de tipeo)
_PAL_FROM_CMAP = {
    "brewer_set1": ("ColorBrewer Set1 (9)", "Set1", 9),
    "brewer_set2": ("ColorBrewer Set2 (8, suave)", "Set2", 8),
    "brewer_set3": ("ColorBrewer Set3 (12)", "Set3", 12),
    "brewer_dark2": ("ColorBrewer Dark2 (8)", "Dark2", 8),
    "brewer_paired": ("ColorBrewer Paired (12)", "Paired", 12),
    "brewer_accent": ("ColorBrewer Accent (8)", "Accent", 8),
    "tab10": ("Matplotlib tab10", "tab10", 10),
    "tab20": ("Matplotlib tab20 (20)", "tab20", 20),
    "tab20b": ("Matplotlib tab20b (20)", "tab20b", 20),
    "tab20c": ("Matplotlib tab20c (20)", "tab20c", 20),
}


def _hex_from_cmap(cmap_name, n):
    from matplotlib.colors import to_hex
    cmap = plt.get_cmap(cmap_name)
    cols = getattr(cmap, "colors", None)
    if cols is not None:
        return [to_hex(c) for c in cols[:n]]
    return [to_hex(cmap(i / max(1, n - 1))) for i in range(n)]


def _build_palettes():
    pals = {}
    for key, (label, colors) in _PAL_HARDCODED.items():
        pals[key] = {"label": label, "colors": list(colors)}
    for key, (label, cmap_name, n) in _PAL_FROM_CMAP.items():
        try:
            pals[key] = {"label": label, "colors": _hex_from_cmap(cmap_name, n)}
        except Exception:
            pass
    return pals


COLOR_PALETTES = _build_palettes()


# =============================================================================
#  MARCADORES  (llenos, vacíos, mixtos)  y combos de estilo de línea
# =============================================================================
# Ciclo amplio de formas (todas soportan relleno full/none)
_MARKER_CYCLE = ["o", "s", "^", "D", "v", "p", "h", "<", ">", "*", "P", "X", "d", "8"]

MARKER_SCHEMES = {
    "filled_varied": {"label": "Llenos variados",
                      "markers": _MARKER_CYCLE, "fillstyles": ["full"]},
    "open_varied": {"label": "Vacíos variados",
                    "markers": _MARKER_CYCLE, "fillstyles": ["none"]},
    "mixed_fill_open": {"label": "Mixto: alterna lleno/vacío",
                        "markers": _MARKER_CYCLE, "fillstyles": ["full", "none"]},
    "filled_then_open": {"label": "Llenos y luego vacíos (misma forma)",
                         "markers": _MARKER_CYCLE,
                         "fillstyles": ["full"] * len(_MARKER_CYCLE) + ["none"] * len(_MARKER_CYCLE),
                         "double": True},
    "solid_classic": {"label": "Sólidos clásicos",
                      "markers": ["o", "s", "^", "D", "v", "P", "X", "<", ">", "h"],
                      "fillstyles": ["full"]},
    "open_classic": {"label": "Abiertos clásicos",
                     "markers": ["o", "s", "^", "D", "v", "<", ">", "h", "p", "d"],
                     "fillstyles": ["none"]},
    "prl_mono": {"label": "PRL mono (abiertos)",
                 "markers": ["o", "s", "^", "D", "v", "<", ">", "p"],
                 "fillstyles": ["none"]},
}

LINESTYLES = {"sólida": "-", "discontinua": "--", "punto-raya": "-.",
              "punteada": ":", "ninguna": "None"}

# Esquemas de LÍNEA para edición masiva por grupo (análogo a MARKER_SCHEMES).
# 'styles' se cicla dentro del grupo destino.
LINE_SCHEMES = {
    "solid_all":    {"label": "Todas sólidas",            "styles": ["-"]},
    "dashed_all":   {"label": "Todas discontinuas",       "styles": ["--"]},
    "dashdot_all":  {"label": "Todas punto-raya",         "styles": ["-."]},
    "dotted_all":   {"label": "Todas punteadas",          "styles": [":"]},
    "varied":       {"label": "Estilos variados",         "styles": ["-", "--", "-.", ":"]},
    "varied_solid_dash": {"label": "Alterna sólida/discontinua", "styles": ["-", "--"]},
    "none_all":     {"label": "Sin línea (solo marcadores)", "styles": ["None"]},
}

# Etiqueta -> valor matplotlib (combo de marcador en edición de línea)
MARKERS = {
    "ninguno": "None", "círculo ●": "o", "cuadrado ■": "s",
    "triángulo ▲": "^", "triángulo ▼": "v", "triángulo ◀": "<",
    "triángulo ▶": ">", "diamante ◆": "D", "diamante fino": "d",
    "estrella ★": "*", "más (relleno)": "P", "x (relleno)": "X",
    "pentágono ⬟": "p", "hexágono ⬡": "h", "hexágono2": "H",
    "octágono": "8", "más +": "+", "x ✕": "x", "punto ·": ".",
    "vline |": "|", "hline _": "_",
}
FILLSTYLES = {"lleno": "full", "vacío": "none", "izq": "left",
              "der": "right", "arriba": "top", "abajo": "bottom"}
FONTWEIGHTS = {"normal": "normal", "negrita": "bold", "ligera": "light",
               "seminegrita": "semibold"}
FONTSTYLES = {"normal": "normal", "itálica": "italic", "oblicua": "oblique"}


# =============================================================================
#  PRESETS DE ESTILO EDITORIAL  (transparentes: solo tamaños/anchos/grilla)
# =============================================================================
STYLE_PRESETS = {
    "prb_technical": {"label": "Physical Review B (técnico, compacto)",
                      "label_size": 10.0, "title_size": 11.0, "tick_size": 8.5,
                      "legend_size": 8.0, "legend_title_size": 9.0,
                      "line_width": 1.4, "marker_size": 5.0, "spine_width": 0.8,
                      "tick_width": 0.8, "tick_length": 3.5, "tick_direction": "in",
                      "grid": {"visible": False}},
    "prl_compact": {"label": "PRL (una columna, muy compacto)",
                    "label_size": 9.0, "title_size": 9.5, "tick_size": 7.5,
                    "legend_size": 7.0, "legend_title_size": 7.5,
                    "line_width": 1.2, "marker_size": 4.2, "spine_width": 0.7,
                    "tick_width": 0.7, "tick_length": 3.0, "tick_direction": "in",
                    "grid": {"visible": False}},
    "rmp_review": {"label": "Rev. Mod. Phys. (review, legible)",
                   "label_size": 11.0, "title_size": 12.0, "tick_size": 9.5,
                   "legend_size": 9.0, "legend_title_size": 10.0,
                   "line_width": 1.5, "marker_size": 5.5, "spine_width": 0.9,
                   "tick_width": 0.9, "tick_length": 4.0, "tick_direction": "in",
                   "grid": {"visible": False}},
    "nature_minimal": {"label": "Nature-like (aireado, sin grilla)",
                       "label_size": 10.0, "title_size": 9.5, "tick_size": 8.0,
                       "legend_size": 7.6, "legend_title_size": 8.0,
                       "line_width": 1.45, "marker_size": 5.0, "spine_width": 0.75,
                       "tick_width": 0.75, "tick_length": 3.2, "tick_direction": "out",
                       "grid": {"visible": False}},
    "science_aaas": {"label": "Science/AAAS (limpio)",
                     "label_size": 9.5, "title_size": 10.0, "tick_size": 8.0,
                     "legend_size": 8.0, "legend_title_size": 8.5,
                     "line_width": 1.3, "marker_size": 4.8, "spine_width": 0.8,
                     "tick_width": 0.8, "tick_length": 3.0, "tick_direction": "out",
                     "grid": {"visible": False}},
    "thesis": {"label": "Tesis (cómodo de leer)",
               "label_size": 12.0, "title_size": 13.0, "tick_size": 10.0,
               "legend_size": 10.0, "legend_title_size": 11.0,
               "line_width": 1.6, "marker_size": 6.0, "spine_width": 1.0,
               "tick_width": 1.0, "tick_length": 4.0, "tick_direction": "out",
               "grid": {"visible": True, "alpha": 0.25, "linestyle": "--", "linewidth": 0.6}},
    "presentation": {"label": "Presentación 16:9 (grande)",
                     "label_size": 15.0, "title_size": 17.0, "tick_size": 13.0,
                     "legend_size": 13.0, "legend_title_size": 14.0,
                     "line_width": 2.4, "marker_size": 8.0, "spine_width": 1.3,
                     "tick_width": 1.3, "tick_length": 5.0, "tick_direction": "out",
                     "grid": {"visible": True, "alpha": 0.3, "linestyle": "--", "linewidth": 0.8}},
    "poster": {"label": "Póster (muy grande)",
               "label_size": 20.0, "title_size": 24.0, "tick_size": 17.0,
               "legend_size": 17.0, "legend_title_size": 18.0,
               "line_width": 3.2, "marker_size": 11.0, "spine_width": 1.8,
               "tick_width": 1.8, "tick_length": 7.0, "tick_direction": "out",
               "grid": {"visible": False}},
    "grayscale_print": {"label": "Impresión B/N (líneas gruesas)",
                        "label_size": 11.0, "title_size": 12.0, "tick_size": 9.5,
                        "legend_size": 9.0, "legend_title_size": 10.0,
                        "line_width": 1.8, "marker_size": 5.5, "spine_width": 1.0,
                        "tick_width": 1.0, "tick_length": 4.0, "tick_direction": "in",
                        "grid": {"visible": False}},
    "minimal_no_grid": {"label": "Minimal (solo spines izq/abajo)",
                        "label_size": 10.5, "title_size": 11.0, "tick_size": 9.0,
                        "legend_size": 8.5, "legend_title_size": 9.0,
                        "line_width": 1.4, "marker_size": 5.0, "spine_width": 0.9,
                        "tick_width": 0.9, "tick_length": 3.5, "tick_direction": "out",
                        "grid": {"visible": False}, "hide_top_right_spines": True},
}


def list_color_palettes():
    return {k: v["label"] for k, v in COLOR_PALETTES.items()}


def list_marker_schemes():
    return {k: v["label"] for k, v in MARKER_SCHEMES.items()}


def list_line_schemes():
    return {k: v["label"] for k, v in LINE_SCHEMES.items()}


def list_style_presets():
    return {k: v["label"] for k, v in STYLE_PRESETS.items()}


def _cycle(seq, i, default=None):
    if not seq:
        return default
    return seq[i % len(seq)]


# =============================================================================
#  Inventario de elementos editables
# =============================================================================
def axis_inventory(ax):
    lines = [ln for ln in ax.get_lines() if _is_refline(ax, ln) is None]
    reflines = [ln for ln in ax.get_lines() if _is_refline(ax, ln) is not None]
    scatters = [c for c in ax.collections if isinstance(c, mcoll.PathCollection)]
    bars = [c for c in getattr(ax, "containers", []) if isinstance(c, BarContainer)]
    texts = [t for t in ax.texts if t not in {ax.title, ax.xaxis.label, ax.yaxis.label}]
    return {"lines": lines, "reflines": reflines, "scatters": scatters,
            "bars": bars, "texts": texts}


def available_fontfamilies():
    """Familias instaladas, ordenadas; antepone las más usadas si están."""
    try:
        from matplotlib import font_manager
        fams = sorted({f.name for f in font_manager.fontManager.ttflist})
    except Exception:
        fams = []
    preferred = ["DejaVu Sans", "DejaVu Serif", "Arial", "Helvetica",
                 "Times New Roman", "Computer Modern Roman", "CMU Serif"]
    head = [p for p in preferred if p in fams]
    rest = [f for f in fams if f not in head]
    return (head + rest) or ["DejaVu Sans"]


# =============================================================================
#  Controlador de edición
# =============================================================================
class FigureEditor:
    """Controla la edición de una figura. Cada método aplica un cambio y redibuja.

    Usable programáticamente y detrás del panel gráfico. Pila de undo/redo
    basada en snapshots del dict de propiedades (una sola fuente de verdad)."""

    def __init__(self, fig):
        self.fig = fig
        self._undo, self._redo = [], []
        self._suspend_snapshot = False
        try:
            ensure_roles(fig)
        except Exception:
            pass

    # ---- infraestructura ----------------------------------------------------
    @property
    def axes(self):
        return _data_axes(self.fig)

    def ax(self, i=0):
        return self.axes[i]

    def refresh(self):
        try:
            self.fig.canvas.draw_idle()
            self.fig.canvas.flush_events()
        except Exception:
            try:
                self.fig.canvas.draw()
            except Exception:
                pass

    def snapshot(self):
        if self._suspend_snapshot:
            return
        try:
            self._undo.append(figure_to_props(self.fig))
            if len(self._undo) > 80:
                self._undo.pop(0)
            self._redo.clear()
        except Exception:
            pass

    def _restore(self, props):
        self._suspend_snapshot = True
        try:
            apply_props_to_figure(props, fig=self.fig, show=False)
        finally:
            self._suspend_snapshot = False
        self.refresh()

    def undo(self):
        if not self._undo:
            print("Nada para deshacer.")
            return False
        self._redo.append(figure_to_props(self.fig))
        self._restore(self._undo.pop())
        return True

    def redo(self):
        if not self._redo:
            print("Nada para rehacer.")
            return False
        self._undo.append(figure_to_props(self.fig))
        self._restore(self._redo.pop())
        return True

    # ---- accesos a artistas -------------------------------------------------
    def line(self, ax_i=0, line_i=0):
        return _LineHandle(self, axis_inventory(self.ax(ax_i))["lines"][line_i])

    def lines(self, ax_i=0):
        return [_LineHandle(self, ln) for ln in axis_inventory(self.ax(ax_i))["lines"]]

    def text(self, ax_i=0, text_i=0):
        return _TextHandle(self, axis_inventory(self.ax(ax_i))["texts"][text_i])

    # ---- ejes / etiquetas ---------------------------------------------------
    def title(self, ax_i, text=None, **font):
        self.snapshot(); _apply_text(self.ax(ax_i).title, _merge_text(text, font)); self.refresh()

    def xlabel(self, ax_i, text=None, **font):
        self.snapshot(); _apply_text(self.ax(ax_i).xaxis.label, _merge_text(text, font)); self.refresh()

    def ylabel(self, ax_i, text=None, **font):
        self.snapshot(); _apply_text(self.ax(ax_i).yaxis.label, _merge_text(text, font)); self.refresh()

    def suptitle(self, text=None, **font):
        self.snapshot()
        if text is not None:
            self.fig.suptitle(text)
        st = getattr(self.fig, "_suptitle", None)
        if st is not None and font:
            _apply_text(st, font)
        self.refresh()

    def xlim(self, ax_i, lo=None, hi=None):
        self.snapshot(); cur = self.ax(ax_i).get_xlim()
        self.ax(ax_i).set_xlim(lo if lo is not None else cur[0], hi if hi is not None else cur[1]); self.refresh()

    def ylim(self, ax_i, lo=None, hi=None):
        self.snapshot(); cur = self.ax(ax_i).get_ylim()
        self.ax(ax_i).set_ylim(lo if lo is not None else cur[0], hi if hi is not None else cur[1]); self.refresh()

    def xscale(self, ax_i, scale):
        self.snapshot(); self.ax(ax_i).set_xscale(scale); self.refresh()

    def yscale(self, ax_i, scale):
        self.snapshot(); self.ax(ax_i).set_yscale(scale); self.refresh()

    def ticks(self, ax_i, axis="both", **kw):
        self.snapshot()
        for a in (("x", "y") if axis == "both" else (axis,)):
            _apply_ticks(self.ax(ax_i), kw, a)
        self.refresh()

    def grid(self, ax_i, visible=True, **kw):
        self.snapshot(); g = {"visible": visible}; g.update(kw); _apply_grid(self.ax(ax_i), g); self.refresh()

    def spine(self, ax_i, name, visible=None, color=None, linewidth=None):
        self.snapshot(); spec = {}
        if visible is not None: spec["visible"] = visible
        if color is not None: spec["color"] = color
        if linewidth is not None: spec["linewidth"] = linewidth
        _apply_spines(self.ax(ax_i), {name: spec}); self.refresh()

    def facecolor(self, ax_i, color):
        self.snapshot(); self.ax(ax_i).set_facecolor(color); self.refresh()

    # ---- leyenda de subplot -------------------------------------------------
    def legend(self, ax_i, **kw):
        self.snapshot()
        ax = self.ax(ax_i)
        cur = _ser_legend(ax) or {"title": "", "entries": [], "style": {}}
        style = dict(cur.get("style", {}))
        for k in ("loc", "ncol", "frameon", "framealpha", "columnspacing",
                  "labelspacing", "handlelength", "handletextpad",
                  "borderpad", "borderaxespad", "title_fontsize"):
            if k in kw:
                style[k] = kw[k]
        if "fontsize" in kw:
            style["label_fontsize"] = kw["fontsize"]
        if "bbox_to_anchor" in kw and kw["bbox_to_anchor"] is not None:
            style["bbox_to_anchor_point"] = list(kw["bbox_to_anchor"])
        entries = cur.get("entries", [])
        if not entries:
            h, l = ax.get_legend_handles_labels()
            entries = [{"label": lab, "handle": {"kind": "Line2D"}} for lab in l]
        leginfo = {"title": kw.get("title", cur.get("title", "")), "entries": entries, "style": style}
        if entries:
            _rebuild_legend(ax, leginfo)
        self.refresh()

    def legend_off(self, ax_i):
        self.snapshot()
        leg = self.ax(ax_i).get_legend()
        if leg is not None:
            leg.remove()
        self.refresh()

    # ---- leyenda compartida (nivel figura) ----------------------------------
    def shared_legend(self, position="outside right", ncol=None, fontsize=None,
                      title="", frameon=True, dedupe=True):
        """Crea/recrea UNA leyenda a nivel figura juntando las series de todos los
        subplots. position ∈ {'outside right','bottom','top','upper right',...}."""
        self.snapshot()
        self.shared_legend_off(_snap=False)
        handles, labels = [], []
        seen = set()
        for ax in self.axes:
            h, l = ax.get_legend_handles_labels()
            for hi, li in zip(h, l):
                if dedupe and li in seen:
                    continue
                seen.add(li); handles.append(hi); labels.append(li)
        if not handles:
            print("No hay series con label para una leyenda compartida.")
            return None
        presets = {
            "outside right": dict(loc="center left", bbox_to_anchor=(1.0, 0.5)),
            "bottom": dict(loc="lower center", bbox_to_anchor=(0.5, 0.0),
                           ncol=ncol or len(labels)),
            "top": dict(loc="upper center", bbox_to_anchor=(0.5, 1.0),
                        ncol=ncol or len(labels)),
        }
        kw = presets.get(position, dict(loc=position))
        if ncol:
            kw["ncol"] = ncol
        kw["frameon"] = frameon
        if fontsize:
            kw["fontsize"] = fontsize
        leg = self.fig.legend(handles, labels, title=title or None, **kw)
        if position == "outside right":
            try:
                self.fig.subplots_adjust(right=0.80)
            except Exception:
                pass
        self.refresh()
        return leg

    def shared_legend_off(self, _snap=True):
        if _snap:
            self.snapshot()
        for leg in list(getattr(self.fig, "legends", []) or []):
            try:
                leg.remove()
            except Exception:
                pass
        self.refresh()

    # ---- reflines / anotaciones (AGREGAR / editar / borrar) -----------------
    def add_hline(self, ax_i, y=0.0, color="k", linestyle="--", linewidth=1.5, alpha=1.0, label=""):
        self.snapshot()
        ln = self.ax(ax_i).axhline(y=y, color=color, linestyle=linestyle, linewidth=linewidth, alpha=alpha)
        setattr(ln, _REFLINE_TAG, "h")
        if label:
            ln.set_label(label)
        self.refresh()
        return ln

    def add_vline(self, ax_i, x=0.0, color="k", linestyle="--", linewidth=1.5, alpha=1.0, label=""):
        self.snapshot()
        ln = self.ax(ax_i).axvline(x=x, color=color, linestyle=linestyle, linewidth=linewidth, alpha=alpha)
        setattr(ln, _REFLINE_TAG, "v")
        if label:
            ln.set_label(label)
        self.refresh()
        return ln

    def add_text(self, ax_i, x=0.5, y=0.5, s="texto", transform="axes", **kw):
        self.snapshot()
        ax = self.ax(ax_i)
        tr = ax.transAxes if transform == "axes" else ax.transData
        t = ax.text(x, y, s, transform=tr, **kw)
        self.refresh()
        return _TextHandle(self, t)

    def remove_artist(self, artist):
        self.snapshot()
        try:
            artist.remove()
        except Exception:
            pass
        self.refresh()

    # ---- figura -------------------------------------------------------------
    def figsize(self, w, h):
        self.snapshot(); self.fig.set_size_inches(w, h); self.refresh()

    def subplots_adjust(self, **kw):
        self.snapshot(); self.fig.subplots_adjust(**kw); self.refresh()

    def figure_facecolor(self, color):
        self.snapshot(); self.fig.patch.set_facecolor(color); self.refresh()

    # ---- estilos masivos ----------------------------------------------------
    def apply_palette(self, name, respect_fillstyle=True, pair=True):
        """Aplica una paleta de colores.

        Con `pair=True` (default) el k-ésimo dato experimental y el k-ésimo
        ajuste comparten color, de modo que cada curva física (p.ej. cada T)
        queda de un solo color y la leyenda no se descoordina. Si no hay
        emparejado posible, colorea cada curva por orden."""
        if name not in COLOR_PALETTES:
            raise ValueError(f"Paleta desconocida: {name}. Opciones: {list(COLOR_PALETTES)}")
        self.snapshot()
        colors = COLOR_PALETTES[name]["colors"]

        def _paint(ln, c):
            ln.set_color(c)
            if _has_marker(ln):
                open_marker = respect_fillstyle and ln.get_fillstyle() == "none"
                ln.set_markeredgecolor(c)
                ln.set_markerfacecolor("none" if open_marker else c)

        for ax in self.axes:
            ensure_roles(ax)
            if pair:
                for k, (d, f) in enumerate(pair_data_fit(ax)):
                    c = _cycle(colors, k)
                    if d is not None:
                        _paint(d, c)
                    if f is not None:
                        _paint(f, c)
            else:
                for i, ln in enumerate(axis_inventory(ax)["lines"]):
                    _paint(ln, _cycle(colors, i))
            i0 = len(pair_data_fit(ax)) if pair else len(axis_inventory(ax)["lines"])
            for j, sc in enumerate(axis_inventory(ax)["scatters"]):
                try:
                    sc.set_color(_cycle(colors, i0 + j))
                except Exception:
                    pass
            self._restyle_legend_handles(ax)
        self.refresh()

    def apply_marker_scheme(self, name, target="data"):
        """Aplica un esquema de marcadores SOLO al grupo `target`.

        target: 'data' (experimentales, default) | 'fit' (ajustes) |
                'both'/'all' (ambos).
        Cicla los marcadores DENTRO del grupo elegido (no por índice global),
        así no se contaminan los ajustes ni se barajan los experimentales."""
        if name not in MARKER_SCHEMES:
            raise ValueError(f"Esquema desconocido: {name}. Opciones: {list(MARKER_SCHEMES)}")
        self.snapshot()
        sch = MARKER_SCHEMES[name]
        markers = sch["markers"]
        fills = sch.get("fillstyles", ["full"])
        double = sch.get("double", False)
        for ax in self.axes:
            ensure_roles(ax)
            for i, ln in enumerate(_target_lines(ax, target)):
                m = _cycle(markers, i)
                fs = (fills[i] if (double and i < len(fills)) else _cycle(fills, i))
                ln.set_marker(m)
                try:
                    ln.set_fillstyle(fs)
                    if fs == "none":
                        ln.set_markerfacecolor("none")
                        ln.set_markeredgecolor(ln.get_color())
                    else:
                        ln.set_markerfacecolor(ln.get_color())
                except Exception:
                    pass
            self._restyle_legend_handles(ax)
        self.refresh()

    def set_role_line_props(self, target="fit", linewidth=None, linestyle=None,
                            color=None, marker=None, markersize=None):
        """Edición masiva de propiedades de línea/marcador para un grupo.

        Pensado para, p.ej., fijar grosor/estilo/color de todos los AJUSTES de
        una sola pasada (target='fit'), o el tamaño de marcador de todos los
        EXPERIMENTALES (target='data'). Sólo aplica los kwargs no-None."""
        self.snapshot()
        for ax in self.axes:
            ensure_roles(ax)
            for ln in _target_lines(ax, target):
                if linewidth is not None:
                    ln.set_linewidth(linewidth)
                if linestyle is not None:
                    ln.set_linestyle(linestyle)
                if color is not None:
                    ln.set_color(color)
                    if _has_marker(ln):
                        ln.set_markeredgecolor(color)
                        if ln.get_fillstyle() != "none":
                            ln.set_markerfacecolor(color)
                if marker is not None:
                    ln.set_marker(marker)
                if markersize is not None:
                    ln.set_markersize(markersize)
            self._restyle_legend_handles(ax)
        self.refresh()

    def apply_line_scheme(self, name, target="fit"):
        """Aplica un esquema de ESTILO de línea SOLO al grupo `target`.

        target: 'fit' (ajustes, default) | 'data' (experimentales) | 'both'/'all'.
        Cicla los estilos del esquema DENTRO del grupo elegido."""
        if name not in LINE_SCHEMES:
            raise ValueError(f"Esquema de línea desconocido: {name}. Opciones: {list(LINE_SCHEMES)}")
        self.snapshot()
        styles = LINE_SCHEMES[name]["styles"]
        for ax in self.axes:
            ensure_roles(ax)
            for i, ln in enumerate(_target_lines(ax, target)):
                ln.set_linestyle(_cycle(styles, i))
            self._restyle_legend_handles(ax)
        self.refresh()

    def apply_style(self, preset):
        if preset not in STYLE_PRESETS:
            raise ValueError(f"Preset desconocido: {preset}. Opciones: {list(STYLE_PRESETS)}")
        self.snapshot()
        p = STYLE_PRESETS[preset]
        for ax in self.axes:
            _apply_text(ax.xaxis.label, {"fontsize": p["label_size"]})
            _apply_text(ax.yaxis.label, {"fontsize": p["label_size"]})
            if ax.title.get_text():
                _apply_text(ax.title, {"fontsize": p["title_size"]})
            ax.tick_params(axis="both", labelsize=p["tick_size"], width=p["tick_width"],
                           length=p["tick_length"], direction=p["tick_direction"])
            for sp in ax.spines.values():
                sp.set_linewidth(p["spine_width"])
            if p.get("hide_top_right_spines"):
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
            for ln in axis_inventory(ax)["lines"]:
                if ln.get_linestyle() not in ("None", None, ""):
                    ln.set_linewidth(p["line_width"])
                if ln.get_marker() not in (None, "None", ""):
                    ln.set_markersize(p["marker_size"])
            _apply_grid(ax, p.get("grid"))
            leg = ax.get_legend()
            if leg is not None:
                try:
                    for t in leg.get_texts():
                        t.set_fontsize(p["legend_size"])
                    if leg.get_title():
                        leg.get_title().set_fontsize(p["legend_title_size"])
                except Exception:
                    pass
        self.refresh()

    def _restyle_legend_handles(self, ax):
        leg = ax.get_legend()
        if leg is None:
            return
        cur = _ser_legend(ax)
        if not cur:
            return
        combined = bool(getattr(ax, _COMBINED_LEG_TAG, False))
        label_to_line = {}
        for ln in axis_inventory(ax)["lines"]:
            lab = ln.get_label()
            if lab and not str(lab).startswith("_"):
                label_to_line[lab] = ln
        for e in cur["entries"]:
            ln = label_to_line.get(e["label"])
            if ln is None:
                continue
            # base: propiedades de la curva que posee la entrada de leyenda
            line_src = ln
            mark_src = ln
            if combined:
                partner = _partner_of(ax, ln)
                if partner is not None:
                    # línea de quien tenga línea; marcador de quien tenga marcador
                    if _has_line(ln) and not _has_line(partner):
                        line_src, mark_src = ln, partner
                    elif _has_line(partner) and not _has_line(ln):
                        line_src, mark_src = partner, ln
                    else:
                        line_src = ln if _has_line(ln) else partner
                        mark_src = ln if _has_marker(ln) else partner
            e["handle"] = {
                "kind": "Line2D", "color": _rgba(line_src.get_color()),
                "linewidth": _to_float(line_src.get_linewidth()),
                "linestyle": _linestyle_to_jsonable(line_src.get_linestyle()),
                "marker": mark_src.get_marker(),
                "markersize": _to_float(mark_src.get_markersize()),
                "markerfacecolor": _rgba(mark_src.get_markerfacecolor()),
                "markeredgecolor": _rgba(mark_src.get_markeredgecolor()), "alpha": None}
        cur.setdefault("style", {})["combined"] = combined
        _rebuild_legend(ax, cur)

    def set_pair_mode(self, mode="order"):
        """Cambia el criterio de emparejado dato↔ajuste ('order' | 'proximity')."""
        if mode not in ("order", "proximity"):
            raise ValueError("mode debe ser 'order' o 'proximity'")
        self.snapshot()
        for ax in self.axes:
            ensure_roles(ax)
            setattr(ax, _PAIR_MODE_TAG, mode)
            self._restyle_legend_handles(ax)
        self.refresh()

    def combine_legend_handles(self, on=True):
        """Activa/desactiva la leyenda combinada: una entrada por curva física,
        cuyo handle muestra el marcador (del dato) y la línea (del ajuste) juntos.
        No agrega entradas nuevas: reusa la etiqueta visible de cada par."""
        self.snapshot()
        for ax in self.axes:
            ensure_roles(ax)
            setattr(ax, _COMBINED_LEG_TAG, bool(on))
            if ax.get_legend() is None and on:
                # crear leyenda mínima desde las curvas etiquetadas
                handles, labels = ax.get_legend_handles_labels()
                if handles:
                    ax.legend(handles, labels)
            self._restyle_legend_handles(ax)
        self.refresh()

    # ---- guardar / exportar / paneles ---------------------------------------
    def save(self, filename, save_png=True):
        return save_figure_data(self.fig, filename, save_png=save_png)

    def export(self, path, dpi=300, bbox_mode=None):
        return export_image(self.fig, path, dpi=dpi, bbox_mode=bbox_mode)

    def split_panels(self, output_base=None, which=None, save_png=True):
        """Guarda cada subplot como figura individual (.json/.csv/.png)."""
        return split_figure(self.fig, output_base=output_base, which=which, save_png=save_png)


def _merge_text(text, font):
    spec = dict(font)
    if text is not None:
        spec["text"] = text
    return spec


class _LineHandle:
    _ALIASES = {"lw": "linewidth", "ls": "linestyle", "c": "color", "ms": "markersize",
                "mfc": "markerfacecolor", "mec": "markeredgecolor", "mew": "markeredgewidth"}

    def __init__(self, ed, line):
        self.ed = ed
        self.line = line

    def set(self, **kw):
        self.ed.snapshot()
        for k, v in kw.items():
            key = self._ALIASES.get(k, k)
            setter = getattr(self.line, f"set_{key}", None)
            if setter is not None:
                try:
                    setter(v)
                except Exception:
                    pass
        self.ed.refresh()
        return self

    def get(self, key):
        key = self._ALIASES.get(key, key)
        getter = getattr(self.line, f"get_{key}", None)
        return getter() if getter else None


class _TextHandle:
    def __init__(self, ed, txt):
        self.ed = ed
        self.txt = txt

    def set(self, text=None, **kw):
        self.ed.snapshot()
        if text is not None:
            self.txt.set_text(text)
        for k, v in kw.items():
            setter = getattr(self.txt, f"set_{k}", None)
            if setter is not None:
                try:
                    setter(v)
                except Exception:
                    pass
        self.ed.refresh()
        return self

    def position(self, x, y):
        self.ed.snapshot(); self.txt.set_position((x, y)); self.ed.refresh(); return self


# Conveniencia a nivel módulo
def apply_palette(fig, name, pair=True):
    FigureEditor(fig).apply_palette(name, pair=pair); return fig


def apply_marker_scheme(fig, name, target="data"):
    FigureEditor(fig).apply_marker_scheme(name, target=target); return fig


def set_role_line_props(fig, target="fit", **kw):
    FigureEditor(fig).set_role_line_props(target=target, **kw); return fig


def apply_line_scheme(fig, name, target="fit"):
    FigureEditor(fig).apply_line_scheme(name, target=target); return fig


def combine_legend_handles(fig, on=True):
    FigureEditor(fig).combine_legend_handles(on=on); return fig


def set_pair_mode(fig, mode="order"):
    FigureEditor(fig).set_pair_mode(mode); return fig


def apply_style(fig, preset):
    FigureEditor(fig).apply_style(preset); return fig

# =============================================================================
#  SEPARAR (split) y RECOMPONER (recompose) figuras multipanel
# =============================================================================
import tempfile as _tempfile


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
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f), p


def _default_single_panel_position(frame_preset=None):
    fr = dict(_DEFAULT_FRAME_PRESET)
    if isinstance(frame_preset, dict):
        fr.update({k: float(v) for k, v in frame_preset.items() if k in fr and v is not None})
    left, right = float(fr["left"]), float(fr["right"])
    bottom, top = float(fr["bottom"]), float(fr["top"])
    return [left, bottom, max(1e-6, right - left), max(1e-6, top - bottom)]


def _estimate_single_figsize(fig_size, axis_pos, frame_preset=None, min_size=(3.0, 2.4)):
    try:
        fw, fh = [float(v) for v in fig_size]
        l, b, w, h = [float(v) for v in axis_pos]
        target = _default_single_panel_position(frame_preset)
        tw, th = float(target[2]), float(target[3])
        out_w = fw * w / max(tw, 1e-6)
        out_h = fh * h / max(th, 1e-6)
        return [max(float(min_size[0]), out_w), max(float(min_size[1]), out_h)]
    except Exception:
        return [6.0, 4.0]


def _infer_shared_legend_for_axis(fig_props, axis_index):
    """Compat: si un panel no tiene leyenda, hereda la metadata de un hermano
    que sí la tenga (para reconstruirla con prefer_axis_handles)."""
    axes = (fig_props or {}).get("axes", []) or []
    if axis_index < 0 or axis_index >= len(axes):
        return None
    target = axes[axis_index] or {}
    if target.get("legend"):
        return None
    n_target = len(target.get("lines") or [])
    if n_target <= 0:
        return None
    candidates = []
    for j, src in enumerate(axes):
        if j == axis_index:
            continue
        leg = (src or {}).get("legend")
        if not isinstance(leg, dict) or not (leg.get("entries") or []):
            continue
        if n_target < len(leg["entries"]):
            continue
        candidates.append((abs(j - axis_index), j, leg))
    if not candidates:
        return None
    _, src_idx, leg = sorted(candidates, key=lambda t: (t[0], t[1]))[0]
    return {"source_axis_index": int(src_idx), "mode": "shared_from_sibling",
            "show_by_default": False, "legend": copy.deepcopy(leg)}


def _normalize_panel_json(fig_props, axis_index=0, size_mode="autosize", frame_preset=None,
                          include_suptitle=False, suptitle_mode="blank",
                          attach_shared_legend=True, show_shared_legend=False):
    axes = fig_props.get("axes", []) or []
    if not axes:
        raise ValueError("La figura no contiene ejes serializados.")
    if axis_index < 0 or axis_index >= len(axes):
        raise IndexError(f"axis_index fuera de rango: {axis_index}")
    out = copy.deepcopy(fig_props)
    axd = copy.deepcopy(axes[axis_index])
    orig_size = fig_props.get("size", [8, 4])
    orig_pos = axd.get("position") or [0.125, 0.11, 0.775, 0.77]
    if str(size_mode).lower().strip() == "keep_size":
        out["size"] = _jsonable(orig_size)
    else:
        out["size"] = _jsonable(_estimate_single_figsize(orig_size, orig_pos, frame_preset=frame_preset))
    axd["position"] = _jsonable(_default_single_panel_position(frame_preset=frame_preset))
    if attach_shared_legend and not axd.get("legend"):
        sh = _infer_shared_legend_for_axis(fig_props, axis_index)
        if sh is not None:
            sh["show_by_default"] = bool(show_shared_legend)
            axd["shared_legend"] = sh
    out["axes"] = [axd]
    out["subplot_layout"] = [1, 1]
    out["subplots_adjust"] = None
    out["figure_legend"] = None
    out["layout_engine"] = {"serialize_positions": True,
                            "apply_tight_layout_on_load": False,
                            "save_subplots_adjust_none": True}
    if not include_suptitle:
        out["suptitle"] = ""
        out["suptitle_obj"] = {"text": ""}
    elif suptitle_mode == "axis_title":
        ttl = (axd.get("title", {}) or {}).get("text", "")
        out["suptitle"] = ttl
        out["suptitle_obj"] = {"text": ttl}
    return out


def split_json_figure_files(pathlike, output_dir=None, prefix=None, which=None,
                            size_mode="autosize", frame_preset=None,
                            include_suptitle=False, save_png=True,
                            attach_shared_legend=True, show_shared_legend=False):
    """Separa un JSON multipanel en JSON/CSV/PNG individuales (uno por subplot)."""
    fig_props, p = _read_figprops(pathlike)
    axes = fig_props.get("axes", []) or []
    if not axes:
        raise ValueError("El JSON no contiene subplots para separar.")
    out_dir = Path(output_dir) if output_dir else p.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = prefix or p.stem
    which = list(range(len(axes))) if which is None else which
    results = []
    for idx0 in which:
        idx = int(idx0)
        panel = _normalize_panel_json(fig_props, axis_index=idx, size_mode=size_mode,
                                      frame_preset=frame_preset, include_suptitle=include_suptitle,
                                      attach_shared_legend=attach_shared_legend,
                                      show_shared_legend=show_shared_legend)
        out_base = out_dir / f"{stem}_ax{idx + 1}"
        with open(out_base.with_suffix(".json"), "w", encoding="utf-8") as f:
            json.dump(panel, f, ensure_ascii=False, indent=2)
        fp = load_figure(str(out_base.with_suffix(".json")), show=False)
        save_figure_data(fp, str(out_base), save_png=save_png)
        try:
            plt.close(fp)
        except Exception:
            pass
        results.append(str(out_base))
    return results


def split_figure(fig, output_base=None, which=None, save_png=True, size_mode="autosize"):
    """Separa una FIGURA en memoria (no un archivo) en paneles individuales."""
    base = output_base or getattr(fig, "_fe_base_filename", None) or "figura"
    base = _safe_stem(base)
    with _tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "split_src"
        save_figure_data(fig, str(tmp), save_png=False)
        return split_json_figure_files(str(tmp.with_suffix(".json")),
                                       output_dir=base.parent, prefix=base.name,
                                       which=which, size_mode=size_mode, save_png=save_png)


def _grid_positions(n, arrangement="horizontal", nrows=None, ncols=None,
                    frame=None, wspace=0.08, hspace=0.08):
    frame = dict(_DEFAULT_FRAME_PRESET if frame is None else frame)
    left, right = float(frame.get("left", 0.11)), float(frame.get("right", 0.98))
    bottom, top = float(frame.get("bottom", 0.11)), float(frame.get("top", 0.98))
    avail_w, avail_h = max(1e-6, right - left), max(1e-6, top - bottom)
    arr = str(arrangement).lower().strip()
    if arr == "vertical":
        nrows = n if not nrows else int(nrows)
        ncols = 1 if not ncols else int(ncols)
    elif arr == "grid":
        if not ncols and not nrows:
            ncols = int(np.ceil(np.sqrt(n))); nrows = int(np.ceil(n / ncols))
        elif ncols and not nrows:
            ncols = int(ncols); nrows = int(np.ceil(n / ncols))
        elif nrows and not ncols:
            nrows = int(nrows); ncols = int(np.ceil(n / nrows))
        else:
            nrows, ncols = int(nrows), int(ncols)
    else:
        nrows = 1 if not nrows else int(nrows)
        ncols = n if not ncols else int(ncols)
    nrows, ncols = max(1, int(nrows)), max(1, int(ncols))
    gap_x, gap_y = float(wspace) * avail_w, float(hspace) * avail_h
    cell_w = (avail_w - gap_x * (ncols - 1)) / max(1, ncols)
    cell_h = (avail_h - gap_y * (nrows - 1)) / max(1, nrows)
    if cell_w <= 0 or cell_h <= 0:
        raise ValueError("wspace/hspace demasiado grandes para el marco.")
    positions = []
    for i in range(n):
        r, c = i // ncols, i % ncols
        if r >= nrows:
            break
        x = left + c * (cell_w + gap_x)
        y = top - (r + 1) * cell_h - r * gap_y
        positions.append([x, y, cell_w, cell_h])
    return positions, (nrows, ncols)


def _compose_figsize_from_parts(parts, arrangement="horizontal", nrows=None, ncols=None):
    sizes = []
    for fp in parts:
        sz = fp.get("size", [6, 4])
        try:
            sizes.append((float(sz[0]), float(sz[1])))
        except Exception:
            sizes.append((6.0, 4.0))
    widths = [s[0] for s in sizes] or [6.0]
    heights = [s[1] for s in sizes] or [4.0]
    n = len(sizes)
    arr = str(arrangement).lower().strip()
    if arr == "vertical":
        return [max(widths), sum(heights)]
    if arr == "grid":
        if not ncols and not nrows:
            ncols = int(np.ceil(np.sqrt(n))); nrows = int(np.ceil(n / ncols))
        elif ncols and not nrows:
            ncols = int(ncols); nrows = int(np.ceil(n / ncols))
        elif nrows and not ncols:
            nrows = int(nrows); ncols = int(np.ceil(n / nrows))
        else:
            nrows, ncols = int(nrows), int(ncols)
        row_heights = [max(heights[r * ncols:(r + 1) * ncols]) for r in range(nrows)
                       if heights[r * ncols:(r + 1) * ncols]]
        col_widths = [max(widths[c::ncols]) for c in range(ncols) if widths[c::ncols]]
        return [sum(col_widths) if col_widths else max(widths),
                sum(row_heights) if row_heights else max(heights)]
    return [sum(widths), max(heights)]


def recompose_figures(json_files, output_base=None, arrangement="horizontal",
                      nrows=None, ncols=None, wspace=0.08, hspace=0.08, frame=None,
                      inherit_global=True, reference_json=None, open_editor=False, save_png=True):
    """Recompone varios JSON de 1 panel en una sola figura multipanel.

    arrangement: 'horizontal' | 'vertical' | 'grid'. Devuelve (fig|None, base)."""
    if not json_files:
        raise ValueError("No se proporcionaron archivos JSON para recomponer.")
    parts = []
    for jf in json_files:
        fp, path = _read_figprops(jf)
        if len(fp.get("axes", []) or []) != 1:
            raise ValueError(f"Cada JSON de entrada debe tener exactamente 1 subplot: {path.name}")
        parts.append((fp, path))
    ref = None
    if reference_json:
        ref, _ = _read_figprops(reference_json)
    elif inherit_global:
        ref = copy.deepcopy(parts[0][0])
    fig_props = copy.deepcopy(ref) if ref is not None else copy.deepcopy(parts[0][0])
    new_axes = [copy.deepcopy(fp["axes"][0]) for fp, _ in parts]
    n = len(new_axes)
    positions, layout = _grid_positions(n, arrangement=arrangement, nrows=nrows, ncols=ncols,
                                        frame=frame, wspace=wspace, hspace=hspace)
    for axd, pos in zip(new_axes, positions):
        axd["position"] = _jsonable([float(v) for v in pos])
    fig_props["axes"] = new_axes
    fig_props["subplot_layout"] = [int(layout[0]), int(layout[1])]
    fig_props["subplots_adjust"] = None
    fig_props["figure_legend"] = None
    fig_props["layout_engine"] = {"serialize_positions": True,
                                  "apply_tight_layout_on_load": False,
                                  "save_subplots_adjust_none": True}
    fig_props["size"] = _jsonable(_compose_figsize_from_parts(
        [fp for fp, _ in parts], arrangement=arrangement, nrows=nrows, ncols=ncols))
    if output_base is None:
        output_base = parts[0][1].parent / "recomposed_figure"
    out_base = _safe_stem(output_base)
    try:
        out_base.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    with open(out_base.with_suffix(".json"), "w", encoding="utf-8") as f:
        json.dump(fig_props, f, ensure_ascii=False, indent=2)
    fig = load_figure(str(out_base.with_suffix(".json")), show=False)
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


# alias de familiaridad con la versión anterior
recompose_json_figures = recompose_figures
split_figure_files = split_json_figure_files

# =============================================================================
#  PANEL DE EDICIÓN EN VIVO  (Qt)
# =============================================================================
def _qt():
    try:
        from matplotlib.backends.qt_compat import QtWidgets, QtCore, QtGui
        return QtWidgets, QtCore, QtGui
    except Exception:
        return None


def _rgba_to_qcolor(rgba, QtGui):
    try:
        from matplotlib.colors import to_rgba
        r, g, b, a = to_rgba(rgba)
        return QtGui.QColor(int(r * 255), int(g * 255), int(b * 255), int(a * 255))
    except Exception:
        return QtGui.QColor(0, 0, 0, 255)


def _qcolor_to_hex(c):
    return f"#{c.red():02x}{c.green():02x}{c.blue():02x}"


_ITEMDATA = 256  # Qt.UserRole


class _PropertyPanel:
    """Ventana Qt de edición en vivo (no modal), junto a la figura."""

    def __init__(self, fig, base_filename="figure"):
        q = _qt()
        if q is None:
            raise RuntimeError("Qt no disponible")
        self.QtWidgets, self.QtCore, self.QtGui = q
        self.fig = fig
        self.ed = FigureEditor(fig)
        self.base_filename = base_filename
        self._artist_to_item = {}
        self._building = False
        self._cur_ai = 0
        self._fontfams = available_fontfamilies()
        self._build_ui()
        self._populate_tree()
        self._connect_pick()

    # ---- ventana ------------------------------------------------------------
    def _build_ui(self):
        QtWidgets, QtCore, QtGui = self.QtWidgets, self.QtCore, self.QtGui
        self.win = QtWidgets.QWidget()
        self.win.setWindowTitle("Editor de figura — en vivo")
        self.win.resize(500, 760)
        try:
            self.win.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, True)
        except Exception:
            pass

        root = QtWidgets.QVBoxLayout(self.win)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # barra: undo/redo + paneles
        bar = QtWidgets.QHBoxLayout()
        self.btn_undo = QtWidgets.QToolButton(); self.btn_undo.setText("↶ Deshacer")
        self.btn_redo = QtWidgets.QToolButton(); self.btn_redo.setText("↷ Rehacer")
        self.btn_undo.clicked.connect(self._on_undo)
        self.btn_redo.clicked.connect(self._on_redo)
        bar.addWidget(self.btn_undo); bar.addWidget(self.btn_redo)
        bar.addStretch(1)
        self.btn_panels = QtWidgets.QToolButton()
        self.btn_panels.setText("Paneles ▾")
        self.btn_panels.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        menu = QtWidgets.QMenu(self.btn_panels)
        menu.addAction("Guardar panel actual como figura…", self._on_split_current)
        menu.addAction("Dividir TODOS los paneles…", self._on_split_all)
        menu.addAction("Recomponer JSONs en multipanel…", self._on_recompose)
        self.btn_panels.setMenu(menu)
        bar.addWidget(self.btn_panels)
        root.addLayout(bar)

        # estilos masivos
        styles = QtWidgets.QHBoxLayout()
        self.cmb_target = QtWidgets.QComboBox()
        for lab, val in [("Aplicar a: Experimentales", "data"),
                         ("Aplicar a: Ajustes", "fit"),
                         ("Aplicar a: Ambos", "both")]:
            self.cmb_target.addItem(lab, val)
        self.cmb_target.setToolTip(
            "Grupo destino de Marcadores y Paleta.\n"
            "Experimentales = curvas con marcadores (puntos).\n"
            "Ajustes = curvas de línea (modelos).")
        self.cmb_palette = QtWidgets.QComboBox(); self.cmb_palette.addItem("Paleta…", None)
        for k, lab in list_color_palettes().items():
            self.cmb_palette.addItem(lab, k)
        self.cmb_palette.activated.connect(self._on_palette)
        self.cmb_markers = QtWidgets.QComboBox(); self.cmb_markers.addItem("Marcadores…", None)
        for k, lab in list_marker_schemes().items():
            self.cmb_markers.addItem(lab, k)
        self.cmb_markers.activated.connect(self._on_markers)
        self.cmb_style = QtWidgets.QComboBox(); self.cmb_style.addItem("Estilo…", None)
        for k, lab in list_style_presets().items():
            self.cmb_style.addItem(lab, k)
        self.cmb_style.activated.connect(self._on_style)
        styles.addWidget(self.cmb_target)
        styles.addWidget(self.cmb_palette); styles.addWidget(self.cmb_markers); styles.addWidget(self.cmb_style)
        root.addLayout(styles)

        # --- segunda fila: edición de LÍNEAS por grupo + leyenda/emparejado ---
        styles2 = QtWidgets.QHBoxLayout()
        self.cmb_lines = QtWidgets.QComboBox(); self.cmb_lines.addItem("Líneas…", None)
        for k, lab in list_line_schemes().items():
            self.cmb_lines.addItem(lab, k)
        self.cmb_lines.setToolTip("Estilo de línea (tipo) aplicado al grupo elegido en 'Aplicar a'.")
        self.cmb_lines.activated.connect(self._on_lines)

        self.spin_lw = QtWidgets.QDoubleSpinBox()
        self.spin_lw.setRange(0.0, 12.0); self.spin_lw.setSingleStep(0.25)
        self.spin_lw.setDecimals(2); self.spin_lw.setValue(1.50)
        self.spin_lw.setPrefix("grosor ")
        self.spin_lw.setToolTip("Grosor de línea del grupo elegido.")
        self.btn_lw = QtWidgets.QPushButton("Aplicar grosor")
        self.btn_lw.clicked.connect(self._on_linewidth)

        self.btn_groupcolor = QtWidgets.QPushButton("Color grupo…")
        self.btn_groupcolor.setToolTip("Un único color para todo el grupo elegido.")
        self.btn_groupcolor.clicked.connect(self._on_group_color)

        self.chk_combined = QtWidgets.QCheckBox("Leyenda combinada")
        self.chk_combined.setToolTip(
            "Una entrada por curva física: muestra el marcador (dato) y la línea\n"
            "(ajuste) juntos, sin agregar entradas a la leyenda.")
        self.chk_combined.toggled.connect(self._on_combined_legend)

        self.btn_proximity = QtWidgets.QPushButton("Emparejar por proximidad")
        self.btn_proximity.setCheckable(True)
        self.btn_proximity.setToolTip(
            "Empareja dato↔ajuste por cercanía de las curvas en vez de por orden\n"
            "de trazado. Útil si datos y ajustes no se graficaron intercalados.")
        self.btn_proximity.toggled.connect(self._on_proximity)

        styles2.addWidget(self.cmb_lines)
        styles2.addWidget(self.spin_lw); styles2.addWidget(self.btn_lw)
        styles2.addWidget(self.btn_groupcolor)
        styles2.addWidget(self.chk_combined)
        styles2.addWidget(self.btn_proximity)
        root.addLayout(styles2)

        # splitter árbol / propiedades
        split = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.tree = QtWidgets.QTreeWidget(); self.tree.setHeaderHidden(True)
        self.tree.currentItemChanged.connect(self._on_tree_select)
        split.addWidget(self.tree)

        self.scroll = QtWidgets.QScrollArea(); self.scroll.setWidgetResizable(True)
        self.prop_host = QtWidgets.QWidget()
        self.prop_layout = QtWidgets.QFormLayout(self.prop_host)
        # >>> FIX truncado: la etiqueta nunca queda tapada por el campo
        self.prop_layout.setRowWrapPolicy(QtWidgets.QFormLayout.WrapLongRows)
        self.prop_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.ExpandingFieldsGrow)
        self.prop_layout.setLabelAlignment(QtCore.Qt.AlignLeft)
        self.prop_layout.setFormAlignment(QtCore.Qt.AlignTop)
        self.prop_layout.setHorizontalSpacing(12)
        self.prop_layout.setVerticalSpacing(5)
        self.scroll.setWidget(self.prop_host)
        split.addWidget(self.scroll)
        split.setSizes([300, 460])
        root.addWidget(split, 1)

        # guardar / exportar
        sv = QtWidgets.QHBoxLayout()
        self.btn_save = QtWidgets.QPushButton("💾 Guardar (.json/.csv/.png)")
        self.btn_save.clicked.connect(self._on_save)
        self.btn_export = QtWidgets.QPushButton("🖼 Exportar imagen…")
        self.btn_export.clicked.connect(self._on_export)
        sv.addWidget(self.btn_save); sv.addWidget(self.btn_export)
        root.addLayout(sv)

        self.status = QtWidgets.QLabel("Listo. Click en un elemento del árbol, o sobre "
                                       "una curva/texto en la figura.")
        self.status.setWordWrap(True)
        self.status.setStyleSheet("color:#555; font-size:11px;")
        root.addWidget(self.status)

    # ---- árbol --------------------------------------------------------------
    def _populate_tree(self):
        QtWidgets = self.QtWidgets
        self.tree.blockSignals(True)
        self.tree.clear()
        self._artist_to_item.clear()

        fig_item = QtWidgets.QTreeWidgetItem(["Figura"])
        fig_item.setData(0, _ITEMDATA, {"kind": "figure"})
        self.tree.addTopLevelItem(fig_item)
        nax = len(self.ed.axes)
        sl = QtWidgets.QTreeWidgetItem(["⚖ Leyenda compartida (figura)"])
        sl.setData(0, _ITEMDATA, {"kind": "shared_legend"})
        fig_item.addChild(sl)

        for ai, ax in enumerate(self.ed.axes):
            ax_item = QtWidgets.QTreeWidgetItem([f"Eje {ai + 1}"])
            ax_item.setData(0, _ITEMDATA, {"kind": "axes", "ai": ai})
            self.tree.addTopLevelItem(ax_item)
            for name, kind in [("Ejes y escalas", "axes_scales"),
                               ("Etiquetas y título", "labels"),
                               ("Ticks", "ticks"), ("Grilla", "grid"),
                               ("Bordes (spines)", "spines"), ("Leyenda", "legend"),
                               ("➕ Agregar elemento…", "add")]:
                it = QtWidgets.QTreeWidgetItem([name])
                it.setData(0, _ITEMDATA, {"kind": kind, "ai": ai})
                ax_item.addChild(it)
            inv = axis_inventory(ax)
            for li, ln in enumerate(inv["lines"]):
                lab = ln.get_label() or f"línea {li + 1}"
                _role = _classify_role(ln)
                _disp = lab[1:] if str(lab).startswith("_") else lab
                _tag = {"data": "exp", "fit": "fit", "mixed": "mix"}.get(_role, "")
                it = QtWidgets.QTreeWidgetItem([f"◾ [{_tag}] {_disp}"])
                it.setData(0, _ITEMDATA, {"kind": "line", "ai": ai, "li": li})
                ax_item.addChild(it); self._artist_to_item[id(ln)] = it
            for ri, ln in enumerate(inv["reflines"]):
                tag = getattr(ln, _REFLINE_TAG, "?")
                it = QtWidgets.QTreeWidgetItem([f"┄ ref {tag} {ri + 1}"])
                it.setData(0, _ITEMDATA, {"kind": "refline", "ai": ai, "ri": ri})
                ax_item.addChild(it); self._artist_to_item[id(ln)] = it
            for si, sc in enumerate(inv["scatters"]):
                it = QtWidgets.QTreeWidgetItem([f"• scatter {si + 1}"])
                it.setData(0, _ITEMDATA, {"kind": "scatter", "ai": ai, "si": si})
                ax_item.addChild(it)
            for bi, bc in enumerate(inv["bars"]):
                it = QtWidgets.QTreeWidgetItem([f"▮ barras {bi + 1}"])
                it.setData(0, _ITEMDATA, {"kind": "bars", "ai": ai, "bi": bi})
                ax_item.addChild(it)
            for ti, t in enumerate(inv["texts"]):
                it = QtWidgets.QTreeWidgetItem([f"T “{(t.get_text() or '')[:18]}”"])
                it.setData(0, _ITEMDATA, {"kind": "text", "ai": ai, "ti": ti})
                ax_item.addChild(it); self._artist_to_item[id(t)] = it
            ax_item.setExpanded(True)
        fig_item.setExpanded(True)
        self.tree.blockSignals(False)

    def _refresh_tree(self, select_meta=None):
        self._populate_tree()
        self._connect_pick()
        if select_meta:
            self._select_by_meta(select_meta)

    def _select_by_meta(self, meta):
        def walk(it):
            if it.data(0, _ITEMDATA) == meta:
                return it
            for i in range(it.childCount()):
                r = walk(it.child(i))
                if r:
                    return r
            return None
        for i in range(self.tree.topLevelItemCount()):
            r = walk(self.tree.topLevelItem(i))
            if r:
                self.tree.setCurrentItem(r); return

    # ---- widgets reutilizables ----------------------------------------------
    def _clear_props(self):
        # removeRow es la forma correcta: borra label+field y decrementa rowCount
        while self.prop_layout.rowCount() > 0:
            try:
                self.prop_layout.removeRow(0)
            except Exception:
                break

    def _commit(self, fn):
        if self._building:
            return
        self.ed.snapshot()
        try:
            fn()
        except Exception as e:
            self.status.setText(f"⚠ {e}")
        self.ed.refresh()

    def _row_float(self, label, value, setter, lo=-1e12, hi=1e12, step=0.1, dec=3):
        sb = self.QtWidgets.QDoubleSpinBox()
        sb.setRange(lo, hi); sb.setDecimals(dec); sb.setSingleStep(step)
        sb.setValue(float(value) if value is not None else 0.0)
        sb.setKeyboardTracking(False)
        sb.editingFinished.connect(lambda: self._commit(lambda: setter(sb.value())))
        self.prop_layout.addRow(label, sb); return sb

    def _row_int(self, label, value, setter, lo=0, hi=999):
        sb = self.QtWidgets.QSpinBox(); sb.setRange(lo, hi)
        sb.setValue(int(value) if value is not None else 0)
        sb.editingFinished.connect(lambda: self._commit(lambda: setter(sb.value())))
        self.prop_layout.addRow(label, sb); return sb

    def _row_text(self, label, value, setter):
        le = self.QtWidgets.QLineEdit(str(value) if value is not None else "")
        le.editingFinished.connect(lambda: self._commit(lambda: setter(le.text())))
        self.prop_layout.addRow(label, le); return le

    def _row_combo(self, label, options, current, setter, editable=False):
        cmb = self.QtWidgets.QComboBox()
        cmb.setEditable(editable)
        items = list(options.items()) if isinstance(options, dict) else [(str(o), o) for o in options]
        idx = 0
        for i, (lab, val) in enumerate(items):
            cmb.addItem(lab, val)
            if val == current or str(val) == str(current):
                idx = i
        cmb.setCurrentIndex(idx)
        cmb.activated.connect(lambda: self._commit(lambda: setter(cmb.currentData())))
        self.prop_layout.addRow(label, cmb); return cmb

    def _row_bool(self, label, value, setter):
        cb = self.QtWidgets.QCheckBox(); cb.setChecked(bool(value))
        cb.toggled.connect(lambda v: self._commit(lambda: setter(bool(v))))
        self.prop_layout.addRow(label, cb); return cb

    def _row_color(self, label, rgba, setter):
        QtWidgets, QtGui = self.QtWidgets, self.QtGui
        btn = QtWidgets.QPushButton()
        col = _rgba_to_qcolor(rgba if rgba is not None else "black", QtGui)
        btn.setStyleSheet(f"background:{_qcolor_to_hex(col)}; min-height:20px; border:1px solid #888;")
        btn._color = col

        def pick():
            c = QtWidgets.QColorDialog.getColor(btn._color, self.win, label,
                                                QtWidgets.QColorDialog.ShowAlphaChannel)
            if c.isValid():
                btn._color = c
                btn.setStyleSheet(f"background:{_qcolor_to_hex(c)}; min-height:20px; border:1px solid #888;")
                rgba_new = [c.redF(), c.greenF(), c.blueF(), c.alphaF()]
                self._commit(lambda: setter(rgba_new))
        btn.clicked.connect(pick)
        self.prop_layout.addRow(label, btn); return btn

    def _row_button(self, text, fn, color=None):
        b = self.QtWidgets.QPushButton(text)
        if color:
            b.setStyleSheet(f"color:{color};")
        b.clicked.connect(fn)
        self.prop_layout.addRow(b); return b

    def _section(self, title):
        lab = self.QtWidgets.QLabel(title)
        lab.setStyleSheet("font-weight:bold; margin-top:8px; color:#1b3a5b;")
        self.prop_layout.addRow(lab)

    def _font_rows(self, obj):
        """Tamaño + familia + peso + estilo + color de un objeto Text."""
        self._row_float("tamaño", obj.get_fontsize(), obj.set_fontsize, 1, 80, 0.5)
        fam = obj.get_fontfamily()
        cur = fam[0] if fam else "DejaVu Sans"
        self._row_combo("familia", self._fontfams, cur,
                        lambda v: obj.set_fontfamily(v), editable=True)
        self._row_combo("peso", FONTWEIGHTS, obj.get_fontweight(), obj.set_fontweight)
        self._row_combo("estilo", FONTSTYLES, obj.get_fontstyle(), obj.set_fontstyle)
        self._row_color("color", obj.get_color(), obj.set_color)

    # ---- selección de árbol -------------------------------------------------
    def _on_tree_select(self, cur, _prev):
        if cur is None:
            return
        meta = cur.data(0, _ITEMDATA)
        if not meta:
            return
        if "ai" in meta:
            self._cur_ai = meta["ai"]
        self._building = True
        self._clear_props()
        try:
            self._build_props(meta)
        except Exception as e:
            self.status.setText(f"⚠ {e}")
        self._building = False

    def _build_props(self, meta):
        kind = meta["kind"]
        if kind == "figure":
            return self._props_figure()
        if kind == "shared_legend":
            return self._props_shared_legend()
        ax = self.ed.ax(meta["ai"])
        dispatch = {
            "axes": lambda: self.status.setText("Eje seleccionado. Expandí sus sub-elementos."),
            "axes_scales": lambda: self._props_scales(ax),
            "labels": lambda: self._props_labels(ax),
            "ticks": lambda: self._props_ticks(ax),
            "grid": lambda: self._props_grid(ax),
            "spines": lambda: self._props_spines(ax),
            "legend": lambda: self._props_legend(meta["ai"], ax),
            "add": lambda: self._props_add(meta["ai"], ax),
            "line": lambda: self._props_line(axis_inventory(ax)["lines"][meta["li"]], meta, refline=False),
            "refline": lambda: self._props_refline(ax, axis_inventory(ax)["reflines"][meta["ri"]], meta),
            "scatter": lambda: self._props_scatter(axis_inventory(ax)["scatters"][meta["si"]]),
            "bars": lambda: self._props_bars(axis_inventory(ax)["bars"][meta["bi"]]),
            "text": lambda: self._props_text(ax, axis_inventory(ax)["texts"][meta["ti"]], meta),
        }
        fn = dispatch.get(kind)
        if fn:
            fn()

    # ---- formularios --------------------------------------------------------
    def _props_figure(self):
        fig = self.fig
        w, h = fig.get_size_inches()
        self._section("Figura")
        self._row_float("ancho (in)", w, lambda v: fig.set_size_inches(v, fig.get_size_inches()[1]), 1, 40, 0.1)
        self._row_float("alto (in)", h, lambda v: fig.set_size_inches(fig.get_size_inches()[0], v), 1, 40, 0.1)
        self._row_color("color de fondo", fig.get_facecolor(), lambda c: fig.patch.set_facecolor(c))
        st = getattr(fig, "_suptitle", None)
        self._row_text("suptítulo", st.get_text() if st else "", lambda s: fig.suptitle(s))
        if st is not None and st.get_text():
            self._row_float("tamaño suptítulo", st.get_fontsize(),
                            lambda v: getattr(fig, "_suptitle").set_fontsize(v), 1, 60, 0.5)
        sp = fig.subplotpars
        self._section("Márgenes (subplots_adjust)")
        for nm in ("left", "right", "bottom", "top", "wspace", "hspace"):
            self._row_float(nm, getattr(sp, nm),
                            lambda v, nm=nm: fig.subplots_adjust(**{nm: v}), 0, 1, 0.01)

    def _props_shared_legend(self):
        self._section("Leyenda compartida (nivel figura)")
        has = bool(getattr(self.fig, "legends", []))
        self.prop_layout.addRow(self.QtWidgets.QLabel(
            "Junta las series de TODOS los subplots en una sola leyenda."))
        self.pos_cmb = self._row_combo("posición",
            {"fuera, derecha": "outside right", "abajo (centrada)": "bottom",
             "arriba (centrada)": "top", "arriba der.": "upper right",
             "arriba izq.": "upper left", "abajo der.": "lower right",
             "abajo izq.": "lower left", "centro": "center"},
            "outside right", lambda v: None)
        self.sl_ncol = self._row_int("columnas", 1, lambda v: None, 1, 12)
        self.sl_fs = self._row_float("tamaño etiquetas", 9.0, lambda v: None, 1, 40, 0.5)
        self.sl_title = self._row_text("título", "", lambda s: None)
        self.sl_frame = self._row_bool("marco", True, lambda v: None)
        self._row_button("✅ Crear / actualizar leyenda compartida", self._apply_shared_legend, color="#0a7")
        if has:
            self._row_button("🗑 Quitar leyenda compartida",
                             lambda: (self.ed.shared_legend_off(), self.status.setText("Leyenda compartida quitada.")),
                             color="#a00")

    def _apply_shared_legend(self):
        try:
            self.ed.shared_legend(position=self.pos_cmb.currentData(),
                                  ncol=self.sl_ncol.value(),
                                  fontsize=self.sl_fs.value(),
                                  title=self.sl_title.text(),
                                  frameon=self.sl_frame.isChecked())
            self.status.setText("Leyenda compartida creada/actualizada.")
        except Exception as e:
            self.status.setText(f"⚠ {e}")

    def _props_scales(self, ax):
        self._section("Límites y escalas")
        x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
        self._row_float("x mín", x0, lambda v: ax.set_xlim(left=v))
        self._row_float("x máx", x1, lambda v: ax.set_xlim(right=v))
        self._row_float("y mín", y0, lambda v: ax.set_ylim(bottom=v))
        self._row_float("y máx", y1, lambda v: ax.set_ylim(top=v))
        self._row_combo("escala x", ["linear", "log", "symlog"], ax.get_xscale(), ax.set_xscale)
        self._row_combo("escala y", ["linear", "log", "symlog"], ax.get_yscale(), ax.set_yscale)
        self._row_color("fondo del eje", ax.get_facecolor(), ax.set_facecolor)

    def _props_labels(self, ax):
        for name, obj in [("Título", ax.title), ("Etiqueta X", ax.xaxis.label),
                          ("Etiqueta Y", ax.yaxis.label)]:
            self._section(name)
            self._row_text("texto", obj.get_text(), obj.set_text)
            self._font_rows(obj)

    def _props_ticks(self, ax):
        for axis in ("x", "y"):
            self._section(f"Ticks {axis.upper()}")
            spec = _ser_ticks(ax, axis)
            self._row_float("tamaño etiqueta", spec.get("fontsize"),
                            lambda v, a=axis: ax.tick_params(axis=a, labelsize=v), 1, 40, 0.5)
            self._row_float("rotación", spec.get("rotation") or 0,
                            lambda v, a=axis: _apply_ticks(ax, {"rotation": v}, a), -90, 90, 5)
            self._row_color("color", spec.get("color"),
                            lambda c, a=axis: ax.tick_params(axis=a, colors=c))
            self._row_combo("dirección", ["out", "in", "inout"], spec.get("direction"),
                            lambda d, a=axis: ax.tick_params(axis=a, direction=d))
            self._row_float("longitud", spec.get("length") or 3.5,
                            lambda v, a=axis: ax.tick_params(axis=a, length=v), 0, 20, 0.5)
            self._row_float("grosor", spec.get("width") or 0.8,
                            lambda v, a=axis: ax.tick_params(axis=a, width=v), 0, 10, 0.1)
        self._row_bool("minor ticks", len(ax.xaxis.get_minorticklocs()) > 0,
                       lambda v: (ax.minorticks_on() if v else ax.minorticks_off()))

    def _props_grid(self, ax):
        g = _ser_grid(ax)
        self._section("Grilla")
        self._row_bool("visible", g.get("visible"),
                       lambda v: _apply_grid(ax, {"visible": v, "color": g.get("color"),
                                                  "linestyle": g.get("linestyle"),
                                                  "linewidth": g.get("linewidth"), "alpha": g.get("alpha")}))
        self._row_combo("estilo", LINESTYLES, g.get("linestyle") or "--", lambda ls: ax.grid(True, linestyle=ls))
        self._row_float("grosor", g.get("linewidth") or 0.8, lambda v: ax.grid(True, linewidth=v), 0, 5, 0.1)
        self._row_float("alpha", g.get("alpha") or 0.4, lambda v: ax.grid(True, alpha=v), 0, 1, 0.05)
        self._row_color("color", g.get("color") or "gray", lambda c: ax.grid(True, color=c))

    def _props_spines(self, ax):
        for name in ("left", "right", "top", "bottom"):
            sp = ax.spines.get(name)
            if sp is None:
                continue
            self._section(f"Spine {name}")
            self._row_bool("visible", sp.get_visible(), sp.set_visible)
            self._row_float("grosor", sp.get_linewidth(), sp.set_linewidth, 0, 10, 0.1)
            self._row_color("color", sp.get_edgecolor(), sp.set_edgecolor)

    def _props_legend(self, ai, ax):
        self._section("Leyenda del subplot")
        leg = ax.get_legend()
        self._row_bool("visible", leg is not None, lambda v: self._toggle_legend(ai, v))
        if leg is None:
            return
        cur = _ser_legend(ax) or {"style": {}, "title": ""}
        style = cur.get("style", {})
        self._row_combo("ubicación (loc)",
                        ["best", "upper right", "upper left", "lower left", "lower right",
                         "right", "center left", "center right", "lower center",
                         "upper center", "center"],
                        style.get("loc", "best"), lambda v: self.ed.legend(ai, loc=v))
        self._row_int("columnas (ncol)", style.get("ncol", 1), lambda v: self.ed.legend(ai, ncol=v), 1, 10)
        self._row_float("tamaño etiquetas", style.get("label_fontsize") or 8,
                        lambda v: self.ed.legend(ai, fontsize=v), 1, 40, 0.5)
        self._row_text("título", cur.get("title", ""), lambda s: self.ed.legend(ai, title=s))
        self._row_float("tamaño título", style.get("title_fontsize") or 9,
                        lambda v: self.ed.legend(ai, title_fontsize=v), 1, 40, 0.5)
        self._row_bool("marco", style.get("frameon", True), lambda v: self.ed.legend(ai, frameon=v))
        self._row_float("alpha marco", style.get("framealpha") or 0.8,
                        lambda v: self.ed.legend(ai, framealpha=v), 0, 1, 0.05)

    def _toggle_legend(self, ai, visible):
        ax = self.ed.ax(ai)
        if visible:
            if ax.get_legend() is None:
                h, l = ax.get_legend_handles_labels()
                if h:
                    ax.legend()
        elif ax.get_legend() is not None:
            ax.get_legend().remove()

    def _props_add(self, ai, ax):
        self._section("Agregar elemento al eje")
        self._row_button("➕ Línea horizontal (axhline)",
                         lambda: self._add_and_select(ai, "h"))
        self._row_button("➕ Línea vertical (axvline)",
                         lambda: self._add_and_select(ai, "v"))
        self._row_button("➕ Texto / anotación",
                         lambda: self._add_and_select(ai, "text"))

    def _add_and_select(self, ai, what):
        ax = self.ed.ax(ai)
        if what == "h":
            y = sum(ax.get_ylim()) / 2.0
            self.ed.add_hline(ai, y=y)
            meta = {"kind": "refline", "ai": ai, "ri": len(axis_inventory(ax)["reflines"]) - 1}
        elif what == "v":
            x = sum(ax.get_xlim()) / 2.0
            self.ed.add_vline(ai, x=x)
            meta = {"kind": "refline", "ai": ai, "ri": len(axis_inventory(ax)["reflines"]) - 1}
        else:
            self.ed.add_text(ai, 0.5, 0.5, "nuevo texto", transform="axes", fontsize=11)
            meta = {"kind": "text", "ai": ai, "ti": len(axis_inventory(ax)["texts"]) - 1}
        self.status.setText("Elemento agregado.")
        self._refresh_tree(select_meta=meta)

    def _props_line(self, ln, meta, refline=False):
        self._section("Curva")
        self._row_combo("rol", {"experimental (datos)": "data",
                                "ajuste (línea)": "fit",
                                "mixto": "mixed"},
                        _classify_role(ln),
                        lambda v: (setattr(ln, _ROLE_TAG, v), self._refresh_tree()))
        self._row_text("label", ln.get_label(), ln.set_label)
        self._row_color("color", ln.get_color(), ln.set_color)
        self._row_float("grosor línea", ln.get_linewidth(), ln.set_linewidth, 0, 20, 0.1)
        self._row_combo("estilo línea", LINESTYLES, ln.get_linestyle(), ln.set_linestyle)
        self._row_combo("marcador", MARKERS, ln.get_marker(), ln.set_marker)
        self._row_combo("relleno marcador", FILLSTYLES, ln.get_fillstyle(), ln.set_fillstyle)
        self._row_float("tamaño marcador", ln.get_markersize(), ln.set_markersize, 0, 40, 0.5)
        self._row_color("color relleno marc.", ln.get_markerfacecolor(), ln.set_markerfacecolor)
        self._row_color("color borde marc.", ln.get_markeredgecolor(), ln.set_markeredgecolor)
        self._row_float("grosor borde marc.", ln.get_markeredgewidth(), ln.set_markeredgewidth, 0, 10, 0.1)
        self._row_float("alpha", ln.get_alpha() if ln.get_alpha() is not None else 1.0, ln.set_alpha, 0, 1, 0.05)
        self._row_float("zorder", ln.get_zorder(), ln.set_zorder, -10, 100, 1)
        self._row_bool("visible", ln.get_visible(), ln.set_visible)

    def _props_refline(self, ax, ln, meta):
        kind = getattr(ln, _REFLINE_TAG, "h")
        self._section(f"Línea de referencia ({'vertical' if kind == 'v' else 'horizontal'})")
        if kind == "v":
            pos = list(ln.get_xdata())[0]
            self._row_float("posición x", pos, lambda v: ln.set_xdata([v, v]))
        else:
            pos = list(ln.get_ydata())[0]
            self._row_float("posición y", pos, lambda v: ln.set_ydata([v, v]))
        self._row_color("color", ln.get_color(), ln.set_color)
        self._row_combo("estilo", LINESTYLES, ln.get_linestyle(), ln.set_linestyle)
        self._row_float("grosor", ln.get_linewidth(), ln.set_linewidth, 0, 20, 0.1)
        self._row_float("alpha", ln.get_alpha() if ln.get_alpha() is not None else 1.0, ln.set_alpha, 0, 1, 0.05)
        self._row_text("label", ln.get_label() if not str(ln.get_label()).startswith("_") else "", ln.set_label)
        self._row_button("🗑 Eliminar esta línea", lambda: self._delete_artist(ln), color="#a00")

    def _props_scatter(self, sc):
        self._section("Scatter")
        self._row_float("alpha", sc.get_alpha() if sc.get_alpha() is not None else 1.0, sc.set_alpha, 0, 1, 0.05)
        self._row_color("color", "C0", lambda c: sc.set_color(c))
        self._row_color("borde", "k", lambda c: sc.set_edgecolor(c))
        self._row_float("zorder", sc.get_zorder(), sc.set_zorder, -10, 100, 1)
        self._row_bool("visible", sc.get_visible(), sc.set_visible)

    def _props_bars(self, bc):
        self._section("Barras")
        patches = list(getattr(bc, "patches", []))
        if not patches:
            return
        self._row_color("relleno (todas)", patches[0].get_facecolor(), lambda c: [p.set_facecolor(c) for p in patches])
        self._row_color("borde (todas)", patches[0].get_edgecolor(), lambda c: [p.set_edgecolor(c) for p in patches])
        self._row_float("grosor borde", patches[0].get_linewidth(),
                        lambda v: [p.set_linewidth(v) for p in patches], 0, 10, 0.1)
        self._row_combo("hatch", {"(ninguno)": "", "/": "/", "\\\\": "\\", "x": "x",
                                  "..": ".", "+": "+", "o": "o", "*": "*"},
                        patches[0].get_hatch() or "", lambda h: [p.set_hatch(h or None) for p in patches])
        self._row_float("alpha", patches[0].get_alpha() if patches[0].get_alpha() is not None else 1.0,
                        lambda v: [p.set_alpha(v) for p in patches], 0, 1, 0.05)

    def _props_text(self, ax, t, meta):
        self._section("Texto / anotación")
        self._row_text("texto", t.get_text(), t.set_text)
        self._font_rows(t)
        self._row_float("x", t.get_position()[0], lambda v: t.set_position((v, t.get_position()[1])), -1e9, 1e9, 0.01)
        self._row_float("y", t.get_position()[1], lambda v: t.set_position((t.get_position()[0], v)), -1e9, 1e9, 0.01)
        self._row_combo("coordenadas", {"ejes (0–1)": "axes", "datos": "data"},
                        "axes" if t.get_transform() == ax.transAxes else "data",
                        lambda m: t.set_transform(ax.transAxes if m == "axes" else ax.transData))
        self._row_float("rotación", t.get_rotation(), t.set_rotation, -180, 180, 5)
        self._row_combo("align H", ["left", "center", "right"], t.get_ha(), t.set_horizontalalignment)
        self._row_combo("align V", ["top", "center", "bottom", "baseline"], t.get_va(), t.set_verticalalignment)
        has_box = _ser_annotation_bbox(t) is not None
        self._row_bool("recuadro", has_box,
                       lambda v: _apply_annotation_bbox(t, {"boxstyle": "round", "facecolor": "white",
                                                            "edgecolor": "black", "pad": 0.3} if v else None))
        self._row_button("🗑 Eliminar este texto", lambda: self._delete_artist(t), color="#a00")

    def _delete_artist(self, artist):
        self.ed.remove_artist(artist)
        self.status.setText("Elemento eliminado.")
        self._refresh_tree()
        self._clear_props()

    # ---- pick en figura -----------------------------------------------------
    def _connect_pick(self):
        for ax in self.ed.axes:
            inv = axis_inventory(ax)
            for ln in inv["lines"] + inv["reflines"]:
                try:
                    ln.set_picker(5)
                except Exception:
                    pass
            for t in inv["texts"]:
                try:
                    t.set_picker(True)
                except Exception:
                    pass
        try:
            self.fig.canvas.mpl_connect("pick_event", self._on_pick)
        except Exception:
            pass

    def _on_pick(self, event):
        art = getattr(event, "artist", None)
        if art is None:
            return
        item = self._artist_to_item.get(id(art))
        if item is not None:
            self.tree.setCurrentItem(item)
            self.status.setText("Seleccionado desde la figura.")

    # ---- barra: undo/redo ---------------------------------------------------
    def _on_undo(self):
        self.ed.undo(); self._reattach()

    def _on_redo(self):
        self.ed.redo(); self._reattach()

    def _reattach(self):
        self.fig = self.ed.fig
        self._refresh_tree()
        self._clear_props()

    def _on_palette(self, _i):
        key = self.cmb_palette.currentData()
        if key:
            self.ed.apply_palette(key)   # paleta empareja dato/ajuste por color
            self.status.setText(f"Paleta: {COLOR_PALETTES[key]['label']}")
            self._refresh_tree()
        self.cmb_palette.setCurrentIndex(0)

    def _on_markers(self, _i):
        key = self.cmb_markers.currentData()
        if key:
            target = self.cmb_target.currentData() or "data"
            self.ed.apply_marker_scheme(key, target=target)
            _tlabel = {"data": "experimentales", "fit": "ajustes", "both": "ambos"}[target]
            self.status.setText(
                f"Marcadores ({_tlabel}): {MARKER_SCHEMES[key]['label']}")
            self._refresh_tree()
        self.cmb_markers.setCurrentIndex(0)

    def _on_style(self, _i):
        key = self.cmb_style.currentData()
        if key:
            self.ed.apply_style(key)
            self.status.setText(f"Estilo: {STYLE_PRESETS[key]['label']}")
        self.cmb_style.setCurrentIndex(0)

    def _tlabel(self):
        return {"data": "experimentales", "fit": "ajustes",
                "both": "ambos"}[self.cmb_target.currentData() or "data"]

    def _on_lines(self, _i):
        key = self.cmb_lines.currentData()
        if key:
            # default razonable: las líneas se editan sobre los AJUSTES salvo
            # que el usuario haya elegido otro grupo en 'Aplicar a'.
            target = self.cmb_target.currentData() or "fit"
            self.ed.apply_line_scheme(key, target=target)
            self.status.setText(f"Líneas ({self._tlabel()}): {LINE_SCHEMES[key]['label']}")
            self._refresh_tree()
        self.cmb_lines.setCurrentIndex(0)

    def _on_linewidth(self):
        target = self.cmb_target.currentData() or "fit"
        self.ed.set_role_line_props(target=target, linewidth=float(self.spin_lw.value()))
        self.status.setText(f"Grosor {self.spin_lw.value():.2f} ({self._tlabel()})")
        self._refresh_tree()

    def _on_group_color(self):
        QtWidgets = self.QtWidgets
        col = QtWidgets.QColorDialog.getColor(parent=self.win)
        if not col.isValid():
            return
        target = self.cmb_target.currentData() or "fit"
        self.ed.set_role_line_props(target=target, color=col.name())
        self.status.setText(f"Color {col.name()} ({self._tlabel()})")
        self._refresh_tree()

    def _on_combined_legend(self, on):
        self.ed.combine_legend_handles(on=bool(on))
        self.status.setText("Leyenda combinada: " + ("ON" if on else "OFF"))

    def _on_proximity(self, on):
        self.ed.set_pair_mode("proximity" if on else "order")
        self.btn_proximity.setText(
            "Emparejado: proximidad" if on else "Emparejar por proximidad")
        self.status.setText("Emparejado: " + ("proximidad" if on else "orden"))

    # ---- barra: paneles -----------------------------------------------------
    def _on_split_current(self):
        QtWidgets = self.QtWidgets
        base, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.win, "Nombre base de salida", f"{self.base_filename}", "JSON base (*)")
        if not base:
            return
        try:
            res = split_figure(self.fig, output_base=base, which=[self._cur_ai], save_png=True)
            self.status.setText(f"Panel guardado: {res[0]}")
        except Exception as e:
            self.status.setText(f"⚠ {e}")

    def _on_split_all(self):
        QtWidgets = self.QtWidgets
        base, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.win, "Nombre base de salida", f"{self.base_filename}", "JSON base (*)")
        if not base:
            return
        try:
            res = split_figure(self.fig, output_base=base, which=None, save_png=True)
            self.status.setText(f"{len(res)} paneles guardados (…_ax1, _ax2, …).")
        except Exception as e:
            self.status.setText(f"⚠ {e}")

    def _on_recompose(self):
        QtWidgets = self.QtWidgets
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self.win, "Elegí JSONs de 1 panel (en orden)", "", "JSON (*.json)")
        if not files:
            return
        arr, ok = QtWidgets.QInputDialog.getItem(
            self.win, "Disposición", "Arreglo:", ["horizontal", "vertical", "grid"], 0, False)
        if not ok:
            return
        out, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.win, "Nombre base de la figura recompuesta", "recomposed_figure", "JSON base (*)")
        if not out:
            return
        try:
            fig, base = recompose_figures(files, output_base=out, arrangement=arr,
                                          open_editor=True, save_png=True)
            self.status.setText(f"Recompuesto: {base}.json (abierto en ventana nueva).")
            if fig is not None:
                _show_nonblocking(fig)
        except Exception as e:
            self.status.setText(f"⚠ {e}")

    # ---- barra: guardar / exportar ------------------------------------------
    def _on_save(self):
        name = getattr(self.fig, "_fe_base_filename", None) or self.base_filename
        try:
            self.ed.save(name, save_png=True)
            self.status.setText(f"Guardado: {name}.json / .csv / .png")
        except Exception as e:
            self.status.setText(f"⚠ {e}")

    def _on_export(self):
        QtWidgets = self.QtWidgets
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.win, "Exportar imagen", f"{self.base_filename}.png",
            "PNG (*.png);;PDF (*.pdf);;SVG (*.svg)")
        if path:
            try:
                self.ed.export(path)
                self.status.setText(f"Exportado: {path}")
            except Exception as e:
                self.status.setText(f"⚠ {e}")

    def show(self):
        self.win.show()
        try:
            self.win.raise_()
        except Exception:
            pass


# =============================================================================
#  Fallback en consola (sin Qt)
# =============================================================================
def _edit_cosmetics_console(fig, base_filename="figure"):
    print("\n[figure_editor] Qt no está disponible en este backend.")
    print("El panel gráfico requiere backend Qt (en Spyder: %matplotlib qt).")
    print("Edición programática disponible con FigureEditor:\n")
    print("    from figure_editor import FigureEditor")
    print("    ed = FigureEditor(fig)")
    print("    ed.line(0,0).set(color='C0', lw=1.4, marker='o', ms=5)")
    print("    ed.apply_palette('tol_muted'); ed.shared_legend('bottom'); ed.save('figura')\n")
    return fig


# =============================================================================
#  edit_cosmetics  —  punto de entrada (API estable)
# =============================================================================
_OPEN_PANELS = []


def edit_cosmetics(fig, base_filename="figure"):
    """Abre el panel de edición EN VIVO de la figura (backend Qt)."""
    try:
        plt.ion()
    except Exception:
        pass
    base = getattr(fig, "_fe_base_filename", None) or base_filename
    if _qt() is None:
        return _edit_cosmetics_console(fig, base)
    try:
        _show_nonblocking(fig)
        panel = _PropertyPanel(fig, base_filename=base)
        panel.show()
        _OPEN_PANELS.append(panel)
        if not matplotlib.is_interactive():
            try:
                plt.show()
            except Exception:
                pass
        return fig
    except Exception as e:
        print(f"[figure_editor] No se pudo abrir el panel Qt ({e}).")
        return _edit_cosmetics_console(fig, base)


def open_editor(fig, base_filename="figure"):
    return edit_cosmetics(fig, base_filename)


__all__ = [
    "save_figure_data", "load_figure", "edit_cosmetics", "open_editor",
    "FigureEditor", "figure_to_props", "apply_props_to_figure", "export_image",
    "apply_palette", "apply_marker_scheme", "apply_style",
    "list_color_palettes", "list_marker_schemes", "list_style_presets",
    "COLOR_PALETTES", "MARKER_SCHEMES", "STYLE_PRESETS",
    "available_fontfamilies",
    "split_figure", "split_json_figure_files", "split_figure_files",
    "recompose_figures", "recompose_json_figures",
]

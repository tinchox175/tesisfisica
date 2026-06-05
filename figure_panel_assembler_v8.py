# -*- coding: utf-8 -*-
r"""
figure_panel_assembler_v8.py
============================
Ensamblador de figuras compuestas con MODO GRÁFICO INTERACTIVO.

Novedades v8 (snap de viñetas + textos libres + resolución de versiones)
------------------------------------------------------------------------
* SNAP DE VIÑETAS: al arrastrar una viñeta con el mouse, si "Imantar" está
  activo la viñeta se engancha al punto de anclaje (de los 9 interiores + 8
  exteriores) más cercano dentro de una tolerancia. Así todas las viñetas
  quedan alineadas idénticamente entre paneles sin trabajo fino. El ancla
  enganchada se guarda POR PANEL (label_anchor) y viaja en la receta.
* TEXTOS LIBRES ARRASTRABLES: se pueden agregar textos y colocarlos
  arrastrándolos por cualquier lado del lienzo, eligiendo tipo de letra,
  tamaño, negrita, itálica y color. Se serializan como textos a nivel figura,
  de modo que SOBREVIVEN el round-trip y quedan EDITABLES en figure_editor
  (ver nota sobre fontfamily más abajo).
* RESOLUCIÓN AUTOMÁTICA DE VERSIONES: la v8 elige el mejor backend de render
  disponible (figure_panel_assembler v5→v4, validando que exponga el pipeline)
  y le inyecta el mejor editor disponible (figure_editor v5→v4→v3). Ya no hay
  nombres de versión hardcodeados que se queden viejos al renombrar archivos.
  Se puede forzar con launch_free_assembler(..., backend=mod, editor=mod).
* MENÚ MÁS CÓMODO: panel de control más ancho y dentro de un área con scroll,
  para que ningún grupo se superponga aunque crezca el contenido.

Nota sobre fontfamily y el round-trip al editor
------------------------------------------------
figure_editor (hasta v5) serializa los textos a nivel figura con texto, x, y,
tamaño, peso (negrita), estilo (itálica), color, alineación y rotación, pero su
cargador NO restaura `fontfamily`. Por eso, al reabrir el .json en el editor el
tipo de letra de los textos libres vuelve al default; TODO lo demás se conserva.
La receta .free.json del ensamblador sí preserva la familia. Si querés que la
familia también sobreviva en el editor, usá el editor parcheado que viaja junto
a este archivo (agrega 2 líneas aditivas y retrocompatibles al round-trip de
figure_texts); la v8 lo detecta y lo usa automáticamente.

Heredado de v7 (rótulos / viñetas)
----------------------------------
* Las viñetas se asignan SIEMPRE en orden de lectura: izquierda→derecha,
  arriba→abajo (independiente del orden de creación; se reasignan al mover
  paneles). Ver reading_order_indices().
* Posiciones de rótulo completas: 9 interiores + 8 exteriores (espejo del
  perímetro; el "centro exterior" es degenerado y se omite). Ver _LABEL_POS.
* Rótulos reubicables a mano: arrastralos (con snap opcional) o fijá las
  coordenadas exactas (fracción de ejes) en el panel de control.

Motivación
----------
La modalidad de consola de v5 (`_responsive_input`: hilo en `sys.stdin.readline()`
+ `plt.pause` en el hilo principal) congela la figura dentro de Spyder. La causa:
en Spyder el código corre en el kernel IPython, que ya es dueño del event loop de
Qt vía su inputhook; mientras el bucle de menú está clavado en `plt.pause`, los
eventos GUI no se bombean hasta que la pila de Python vuelve al kernel (al "Salir").
`figure_editor3` no sufre esto porque construye un QWidget real que vive en el loop
de Qt y nunca bloquea stdin. v8 replica esa modalidad y agrega ensamble libre.

Qué hace v8
-----------
1. LIENZO INTERACTIVO (figura matplotlib): cada subfigura es un Axes en posición
   absoluta. Se ARRASTRA para mover y se ESTIRA de bordes/esquinas (8 manijas) para
   redimensionar. Snapping opcional a grilla y a bordes de paneles vecinos. Flechas
   = nudge, Supr = borrar, doble click = ajustar imagen a su contenido. Las viñetas
   y los textos libres se arrastran haciéndoles click directamente.
2. PANEL DE CONTROL Qt (modalidad figure_editor3, con listas desplegables):
   agregar/quitar figuras, presets de grilla como punto de partida, rect exacto de
   la selección (x/y/ancho/alto), alinear/distribuir, mantener-proporción por panel,
   escala de fuente, rótulos (a/(a)/A)/…), textos libres, suptitle y guardar.

Reutilización (DRY): todo el render por fuente y el guardado se delegan en el mejor
figure_panel_assembler disponible (v5/v4), que a su vez delega en el mejor
figure_editor disponible (v5/v4/v3) para el round-trip JSON/CSV reconstruible con
posiciones absolutas. v8 NO duplica ese pipeline.

El ensamble libre usa SIEMPRE posiciones absolutas, que es exactamente lo que el
pipeline de guardado ya congela (`_serialize_axes_positions = True`), de modo que la
figura recompuesta recarga idéntica en figure_editor.

Uso (en Spyder, con backend interactivo):
    %matplotlib qt
    from figure_panel_assembler_v8 import launch_free_assembler
    asm = launch_free_assembler()                       # arranca vacío; agregás desde el panel
    asm = launch_free_assembler(["fig1", "fig2.pdf"])   # arranca con fuentes

Uso programático (headless, p.ej. para tests/batch):
    from figure_panel_assembler_v8 import FreeCanvasAssembler
    asm = FreeCanvasAssembler()
    asm.add_source("fig1"); asm.add_source("fig2.png")
    asm.apply_grid_preset(1, 2)
    asm.add_text("(*)", xy=(0.5, 0.5), fontfamily="DejaVu Serif", fontsize=14, bold=True)
    asm.save("panel_final")

Referencias de diseño de figuras multipanel:
  * Rougier, Droettboom & Bourne (2014), "Ten Simple Rules for Better Figures",
    PLoS Comput Biol 10(9):e1003833. (legibilidad, no distorsionar, alineación)
  * Hunter (2007), "Matplotlib: A 2D graphics environment", CSE 9(3):90-95.
    (manejo de Axes en coordenadas de figura vía set_position / transFigure)
"""
from __future__ import annotations

import sys
import json
import importlib
import importlib.util
import warnings
from pathlib import Path
from typing import Any, Callable

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D


# ─────────────────────────────────────────────────────────────────────────────
#  Resolución de versiones (DRY) — backend de render/guardado + editor
# ─────────────────────────────────────────────────────────────────────────────
#  La v8 NO duplica el pipeline: toma el motor de render/guardado del mejor
#  figure_panel_assembler disponible (v5/v4) y le inyecta el mejor figure_editor
#  disponible (v5/v4/v3). Todo es overrideable pasando los módulos explícitos.

# Símbolos que un módulo debe exponer para servir de backend de render/guardado:
_BACKEND_REQUIRED = ("_draw_source_into", "_PANEL_LAYOUTS", "format_panel_label",
                     "_freeze_positions", "save_composite_figure")
# Candidatos en orden de preferencia (más nuevo primero):
_BACKEND_CANDIDATES = ("figure_panel_assembler_v5", "figure_panel_assembler_v4",
                       "figure_panel_assembler")
_EDITOR_CANDIDATES = ("figure_editor5", "figure_editor4", "figure_editor3",
                      "figure_editor")


def _try_import_named(names):
    """Importa el primer módulo de `names` que cargue (por nombre o por archivo
    junto a este script). Devuelve el módulo o None."""
    here = Path(__file__).resolve().parent
    for name in names:
        try:
            return importlib.import_module(name)
        except Exception:
            pass
        p = here / (name + ".py")
        if p.exists():
            try:
                spec = importlib.util.spec_from_file_location(p.stem, str(p))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore[union-attr]
                return mod
            except Exception as exc:  # pragma: no cover
                warnings.warn(f"No se pudo cargar {name}.py: {exc}")
    return None


def _import_assembler_backend(candidates=_BACKEND_CANDIDATES):
    """Devuelve el primer assembler que exponga el pipeline de render/guardado."""
    here = Path(__file__).resolve().parent
    for name in candidates:
        mod = None
        try:
            mod = importlib.import_module(name)
        except Exception:
            p = here / (name + ".py")
            if p.exists():
                try:
                    spec = importlib.util.spec_from_file_location(p.stem, str(p))
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)  # type: ignore[union-attr]
                except Exception as exc:  # pragma: no cover
                    warnings.warn(f"No se pudo cargar {name}.py: {exc}")
                    mod = None
        if mod is not None and all(hasattr(mod, s) for s in _BACKEND_REQUIRED):
            return mod
    return None


def _resolve_editor(candidates=_EDITOR_CANDIDATES):
    """Devuelve el mejor figure_editor disponible (v5/v4/v3) o None."""
    return _try_import_named(candidates)


def _inject_editor_into_backend(backend, editor):
    """Hace que el backend use `editor` para el round-trip reconstruible, sin
    tocar su código fuente. El backend referencia el editor vía las globales
    `_FE`/`_HAS_FE` (resueltas en tiempo de llamada), así que reescribirlas
    redirige toda su delegación al editor elegido."""
    if backend is None or editor is None:
        return None
    try:
        cur = getattr(backend, "_FE", None)
        # Solo reinyectamos si el editor elegido es distinto al que el backend
        # auto-cargó (p. ej. el backend halló editor3 pero hay editor5).
        if cur is not editor:
            setattr(backend, "_FE", editor)
            setattr(backend, "_HAS_FE", True)
        return editor
    except Exception as exc:  # pragma: no cover
        warnings.warn(f"No pude inyectar el editor en el backend: {exc}")
        return getattr(backend, "_FE", None)


# Backend por defecto (se puede sobreescribir vía configure_backend()).
_V5 = _import_assembler_backend()
if _V5 is None:
    raise ImportError(
        "figure_panel_assembler_v8 requiere un backend de render/guardado "
        "(figure_panel_assembler_v5.py o v4) en el path o junto a este archivo: "
        "de ahí toma el render por fuente y el guardado reconstruible."
    )
_EDITOR = _resolve_editor()
_inject_editor_into_backend(_V5, _EDITOR)


def configure_backend(backend=None, editor=None):
    """Fuerza el backend de render/guardado y/o el editor a usar.

    Parámetros (cualquiera de los dos opcional):
      backend : módulo tipo figure_panel_assembler_v5 (expone el pipeline).
      editor  : módulo tipo figure_editor5 (round-trip reconstruible).
    Devuelve (backend, editor) efectivos.
    """
    global _V5, _EDITOR
    if backend is not None:
        if not all(hasattr(backend, s) for s in _BACKEND_REQUIRED):
            raise ValueError(
                "El backend no expone el pipeline requerido: "
                + ", ".join(_BACKEND_REQUIRED))
        _V5 = backend
    if editor is not None:
        _EDITOR = editor
    _inject_editor_into_backend(_V5, _EDITOR)
    return _V5, _EDITOR


def backend_info():
    """Texto legible de qué backend/editor quedaron resueltos (para diagnóstico)."""
    bname = getattr(_V5, "__name__", "?")
    ename = getattr(_EDITOR, "__name__", None) or getattr(
        getattr(_V5, "_FE", None), "__name__", "ninguno")
    return f"backend={bname}  editor={ename}"


_FORMAT_VERSION = 140
_HANDLE_PX = 9.0          # tamaño de manija en px (radio de captura)
_MIN_FRAC = 0.04          # ancho/alto mínimo de un panel en fracción de figura
_LABEL_SNAP_TOL = 0.07    # tolerancia (fracción de ejes) para imantar viñetas
_HANDLES = ("sw", "se", "nw", "ne", "w", "e", "s", "n")
_RASTER_EXTS = getattr(_V5, "_RASTER_EXTS", {".png", ".jpg", ".jpeg", ".tif",
                                             ".tiff", ".bmp", ".webp"})
_VECTOR_EXTS = getattr(_V5, "_VECTOR_EXTS", {".pdf", ".eps", ".svg"})


# ═════════════════════════════════════════════════════════════════════════════
#  GEOMETRÍA PURA (testeable sin GUI) — coords de figura, origen abajo-izquierda
# ═════════════════════════════════════════════════════════════════════════════
def clamp01(v: float) -> float:
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else float(v))


def normalize_rect(rect, min_w=_MIN_FRAC, min_h=_MIN_FRAC):
    """Devuelve (l, b, w, h) válido dentro de [0,1] con tamaños mínimos."""
    l, b, w, h = (float(x) for x in rect)
    w = max(min_w, min(w, 1.0))
    h = max(min_h, min(h, 1.0))
    l = clamp01(min(l, 1.0 - w))
    b = clamp01(min(b, 1.0 - h))
    return (l, b, w, h)


def hit_test_rect(rect, fx, fy, tol_x, tol_y):
    """¿Qué parte del rect toca (fx,fy)?  Devuelve una de _HANDLES, 'body' o None.

    tol_x/tol_y: tolerancia (en fracción de figura) equivalente a _HANDLE_PX px.
    Prioriza esquinas > bordes > cuerpo.
    """
    l, b, w, h = rect
    r, t = l + w, b + h
    near_l = abs(fx - l) <= tol_x
    near_r = abs(fx - r) <= tol_x
    near_b = abs(fy - b) <= tol_y
    near_t = abs(fy - t) <= tol_y
    inside_x = (l - tol_x) <= fx <= (r + tol_x)
    inside_y = (b - tol_y) <= fy <= (t + tol_y)
    if not (inside_x and inside_y):
        return None
    # esquinas
    if near_l and near_b:
        return "sw"
    if near_r and near_b:
        return "se"
    if near_l and near_t:
        return "nw"
    if near_r and near_t:
        return "ne"
    # bordes
    if near_l and (b <= fy <= t):
        return "w"
    if near_r and (b <= fy <= t):
        return "e"
    if near_b and (l <= fx <= r):
        return "s"
    if near_t and (l <= fx <= r):
        return "n"
    # cuerpo
    if l <= fx <= r and b <= fy <= t:
        return "body"
    return None


def resize_rect(rect, handle, fx, fy, min_w=_MIN_FRAC, min_h=_MIN_FRAC):
    """Reubica el borde/esquina `handle` al puntero (fx,fy). Coords absolutas."""
    l, b, w, h = rect
    r, t = l + w, b + h
    if handle in ("w", "nw", "sw"):
        new_l = clamp01(min(fx, r - min_w))
        l, w = new_l, r - new_l
    if handle in ("e", "ne", "se"):
        new_r = clamp01(max(fx, l + min_w))
        w = new_r - l
    if handle in ("s", "sw", "se"):
        new_b = clamp01(min(fy, t - min_h))
        b, h = new_b, t - new_b
    if handle in ("n", "nw", "ne"):
        new_t = clamp01(max(fy, b + min_h))
        h = new_t - b
    return normalize_rect((l, b, w, h), min_w, min_h)


def snap_value(v: float, step: float, tol: float) -> float:
    if step <= 0:
        return v
    nearest = round(v / step) * step
    return nearest if abs(nearest - v) <= tol else v


def snap_rect_to_grid(rect, step, tol):
    """Snap de los 4 bordes a múltiplos de `step` si caen dentro de `tol`."""
    l, b, w, h = rect
    r, t = l + w, b + h
    l2, r2 = snap_value(l, step, tol), snap_value(r, step, tol)
    b2, t2 = snap_value(b, step, tol), snap_value(t, step, tol)
    return normalize_rect((l2, b2, max(_MIN_FRAC, r2 - l2), max(_MIN_FRAC, t2 - b2)))


def snap_rect_to_edges(rect, others, tol):
    """Snap de bordes a bordes (l/r/b/t) de los rects vecinos en `others`."""
    l, b, w, h = rect
    r, t = l + w, b + h
    xs, ys = [], []
    for (ol, ob, ow, oh) in others:
        xs += [ol, ol + ow]
        ys += [ob, ob + oh]
    for cand in xs:
        if abs(l - cand) <= tol:
            l = cand
        if abs(r - cand) <= tol:
            r = cand
    for cand in ys:
        if abs(b - cand) <= tol:
            b = cand
        if abs(t - cand) <= tol:
            t = cand
    return normalize_rect((l, b, max(_MIN_FRAC, r - l), max(_MIN_FRAC, t - b)))


# ── Posiciones de rótulo: 9 interiores + 8 exteriores (en coords de ejes) ─────
# (x, y, ha, va). Interiores con margen 0.03; exteriores justo fuera del marco.
_LABEL_POS = {
    # interiores (9 puntos)
    "inside_top_left":      (0.030, 0.965, "left",   "top"),
    "inside_top_center":    (0.500, 0.965, "center", "top"),
    "inside_top_right":     (0.970, 0.965, "right",  "top"),
    "inside_center_left":   (0.030, 0.500, "left",   "center"),
    "inside_center":        (0.500, 0.500, "center", "center"),
    "inside_center_right":  (0.970, 0.500, "right",  "center"),
    "inside_bottom_left":   (0.030, 0.035, "left",   "bottom"),
    "inside_bottom_center": (0.500, 0.035, "center", "bottom"),
    "inside_bottom_right":  (0.970, 0.035, "right",  "bottom"),
    # exteriores (8 puntos del perímetro; el "centro exterior" no existe)
    "outside_top_left":      (0.000, 1.045, "left",   "bottom"),
    "outside_top_center":    (0.500, 1.045, "center", "bottom"),
    "outside_top_right":     (1.000, 1.045, "right",  "bottom"),
    "outside_center_left":   (-0.045, 0.500, "right",  "center"),
    "outside_center_right":  (1.045, 0.500, "left",   "center"),
    "outside_bottom_left":   (0.000, -0.055, "left",   "top"),
    "outside_bottom_center": (0.500, -0.055, "center", "top"),
    "outside_bottom_right":  (1.000, -0.055, "right",  "top"),
}


def snap_label_to_anchor(x: float, y: float, tol: float = _LABEL_SNAP_TOL):
    """Imanta una posición de viñeta (x,y en fracción de ejes) al punto de
    anclaje más cercano de _LABEL_POS, si cae dentro de `tol`.

    Devuelve (anchor_key, x, y, ha, va) si engancha; (None, x, y, 'center',
    'center') si no hay ancla suficientemente cerca. Usar la clave devuelta
    permite que TODAS las viñetas enganchadas al mismo anclaje queden alineadas
    de forma idéntica entre paneles.
    """
    best_key, best_d2 = None, tol * tol
    for key, (ax, ay, ha, va) in _LABEL_POS.items():
        d2 = (ax - x) ** 2 + (ay - y) ** 2
        if d2 <= best_d2:
            best_key, best_d2 = key, d2
    if best_key is None:
        return None, float(x), float(y), "center", "center"
    ax, ay, ha, va = _LABEL_POS[best_key]
    return best_key, float(ax), float(ay), ha, va


def reading_order_indices(rects):
    """Índices de paneles en orden de lectura: izquierda→derecha, arriba→abajo.

    Agrupa en filas por el borde SUPERIOR (b+h) con tolerancia de media altura
    mediana (robusto a desalineaciones leves), luego ordena cada fila por el
    borde izquierdo. Devuelve la permutación de índices.
    """
    items = list(enumerate(rects))
    if not items:
        return []
    heights = [h for _, (l, b, w, h) in items]
    tol = 0.5 * float(np.median(heights)) if heights else 0.05
    items.sort(key=lambda t: -(t[1][1] + t[1][3]))   # borde superior, desc
    rows: list[dict] = []
    for idx, (l, b, w, h) in items:
        top = b + h
        for row in rows:
            if abs(row["top"] - top) <= tol:
                row["items"].append((idx, l))
                break
        else:
            rows.append({"top": top, "items": [(idx, l)]})
    order = []
    for row in rows:
        row["items"].sort(key=lambda t: t[1])        # borde izquierdo, asc
        order += [idx for idx, _ in row["items"]]
    return order


def grid_rects(rows: int, cols: int, margin: float = 0.06, gap: float = 0.04):
    """Rects (l,b,w,h) de una grilla rows×cols con márgenes/gaps uniformes.

    Orden: por filas, de ARRIBA hacia abajo y de izquierda a derecha (orden de
    lectura), consistente con el orden de fuentes del resto del paquete.
    """
    rows, cols = max(1, int(rows)), max(1, int(cols))
    usable_w = max(0.1, 1.0 - 2 * margin - (cols - 1) * gap)
    usable_h = max(0.1, 1.0 - 2 * margin - (rows - 1) * gap)
    cw = usable_w / cols
    ch = usable_h / rows
    rects = []
    for rr in range(rows):
        for cc in range(cols):
            l = margin + cc * (cw + gap)
            # fila 0 arriba:
            b = margin + (rows - 1 - rr) * (ch + gap)
            rects.append((l, b, cw, ch))
    return rects


# ═════════════════════════════════════════════════════════════════════════════
#  PANEL (subfigura) del ensamble libre
# ═════════════════════════════════════════════════════════════════════════════
class FreePanel:
    __slots__ = ("source", "rect", "ax", "kind", "keep_aspect", "label",
                 "label_custom_xy", "label_anchor", "label_artist")

    def __init__(self, source, rect, keep_aspect=True, label=None):
        self.source = str(source)
        self.rect = normalize_rect(rect)
        self.ax = None
        self.kind = None
        self.keep_aspect = bool(keep_aspect)
        self.label = label
        self.label_custom_xy = None   # (x, y) en coords de ejes si fue ubicado a mano
        self.label_anchor = None      # clave de _LABEL_POS si fue imantado a un ancla
        self.label_artist = None      # objeto Text del rótulo de este panel

    def is_image(self):
        return self.kind in ("image", "raster", "vector")


# ═════════════════════════════════════════════════════════════════════════════
#  TEXTO LIBRE (anotación a nivel figura, arrastrable)
# ═════════════════════════════════════════════════════════════════════════════
class FreeText:
    """Texto colocable libremente sobre el lienzo (coords de figura).

    Se materializa como un Text a nivel figura (fig.text con transFigure), de
    modo que el guardado reconstruible lo serializa en `figure_texts` y vuelve
    EDITABLE en figure_editor. La familia (`fontfamily`) viaja siempre en la
    receta .free.json; en el editor sobrevive solo si éste soporta fontfamily
    en figure_texts (editor parcheado).
    """
    __slots__ = ("text", "x", "y", "fontfamily", "fontsize", "bold", "italic",
                 "color", "ha", "va", "rotation", "artist")

    def __init__(self, text="Texto", x=0.5, y=0.5, *, fontfamily=None,
                 fontsize=14.0, bold=False, italic=False, color="black",
                 ha="center", va="center", rotation=0.0):
        self.text = str(text)
        self.x = float(x)
        self.y = float(y)
        self.fontfamily = fontfamily
        self.fontsize = float(fontsize)
        self.bold = bool(bold)
        self.italic = bool(italic)
        self.color = color
        self.ha = ha
        self.va = va
        self.rotation = float(rotation)
        self.artist = None

    # ── (de)serialización para la receta ──────────────────────────────────────
    def to_dict(self):
        return {"text": self.text, "x": self.x, "y": self.y,
                "fontfamily": self.fontfamily, "fontsize": self.fontsize,
                "bold": self.bold, "italic": self.italic, "color": self.color,
                "ha": self.ha, "va": self.va, "rotation": self.rotation}

    @classmethod
    def from_dict(cls, d):
        return cls(text=d.get("text", "Texto"), x=d.get("x", 0.5),
                   y=d.get("y", 0.5), fontfamily=d.get("fontfamily"),
                   fontsize=d.get("fontsize", 14.0), bold=d.get("bold", False),
                   italic=d.get("italic", False), color=d.get("color", "black"),
                   ha=d.get("ha", "center"), va=d.get("va", "center"),
                   rotation=d.get("rotation", 0.0))


# ═════════════════════════════════════════════════════════════════════════════
#  ASSEMBLER DE LIENZO LIBRE (motor + interacción de mouse, backend-agnóstico)
# ═════════════════════════════════════════════════════════════════════════════
class FreeCanvasAssembler:
    """Ensamble libre: paneles arrastrables y redimensionables sobre una figura.

    Interacción (en backend interactivo Qt/Tk):
      * click + arrastre dentro de un panel -> mover
      * arrastre desde un borde/esquina -> redimensionar
      * click en vacío -> deseleccionar
      * flechas -> nudge fino; Shift+flechas -> nudge grueso
      * Supr/Backspace -> borrar panel seleccionado
      * doble click -> ajustar imagen a su contenido (toggle mantener proporción)
    Todo dibuja con draw_idle(); no usa input() ni plt.pause en bucle.
    """

    def __init__(self, figsize=(8.0, 6.0), dpi=150, *, snapping=True,
                 grid_step=1.0 / 24.0, show_grid=False, font_scale=0.9,
                 base_filename="figura_compuesta", on_change: Callable | None = None):
        self.panels: list[FreePanel] = []
        self.selected: int | None = None
        self.snapping = bool(snapping)
        self.grid_step = float(grid_step)
        self.show_grid = bool(show_grid)
        self.font_scale = float(font_scale)
        self.base_filename = base_filename
        self.on_change = on_change
        self.label_spec = None
        self.label_mode = False     # si True, el mouse arrastra rótulos en vez de paneles
        self.suptitle = None
        self.texts: list[FreeText] = []      # textos libres arrastrables (v8)
        self.selected_text: int | None = None
        self._cache: dict = {}
        self._all_data = {"all_reconstructible": True}

        self.fig = plt.figure(figsize=figsize, dpi=dpi)
        try:
            self.fig.canvas.manager.set_window_title(
                "Ensamble libre — Panel Assembler v8")
        except Exception:
            pass

        # overlay de selección (8 manijas + marco) y grilla guía
        self._sel_rect = Rectangle((0, 0), 0, 0, fill=False, ls="--", lw=1.3,
                                   ec="#1f77b4", transform=self.fig.transFigure,
                                   zorder=10000, visible=False)
        self.fig.patches.append(self._sel_rect)
        self._handles = []
        for _ in _HANDLES:
            hp = Rectangle((0, 0), 0, 0, fc="#1f77b4", ec="white", lw=0.8,
                           transform=self.fig.transFigure, zorder=10001,
                           visible=False)
            self.fig.patches.append(hp)
            self._handles.append(hp)
        self._grid_lines: list[Line2D] = []

        # overlay de selección de TEXTO libre (marco punteado naranja)
        self._text_sel = Rectangle((0, 0), 0, 0, fill=False, ls=":", lw=1.2,
                                   ec="#ff7f0e", transform=self.fig.transFigure,
                                   zorder=10002, visible=False)
        self.fig.patches.append(self._text_sel)

        # estado de arrastre
        self._drag = None  # dict: mode, idx, handle, off
        self._cids = []
        self._connect_events()
        self._rebuild_grid_overlay()

    # ── conexión de eventos ──────────────────────────────────────────────────
    def _connect_events(self):
        c = self.fig.canvas
        self._cids = [
            c.mpl_connect("button_press_event", self._on_press),
            c.mpl_connect("motion_notify_event", self._on_motion),
            c.mpl_connect("button_release_event", self._on_release),
            c.mpl_connect("key_press_event", self._on_key),
        ]

    def _disconnect_events(self):
        for cid in self._cids:
            try:
                self.fig.canvas.mpl_disconnect(cid)
            except Exception:
                pass
        self._cids = []

    # ── tolerancias en fracción de figura equivalentes a _HANDLE_PX px ────────
    def _tol_frac(self):
        w_in, h_in = self.fig.get_size_inches()
        dpi = self.fig.dpi
        return (_HANDLE_PX / max(1.0, w_in * dpi),
                _HANDLE_PX / max(1.0, h_in * dpi))

    def _event_to_frac(self, event):
        if event.x is None or event.y is None:
            return None
        inv = self.fig.transFigure.inverted()
        fx, fy = inv.transform((event.x, event.y))
        return float(fx), float(fy)

    # ── alta/baja de fuentes ──────────────────────────────────────────────────
    def add_source(self, source, rect=None, keep_aspect=True, select=True):
        if rect is None:
            # cascada simple para no apilar exactamente
            k = len(self.panels)
            off = 0.04 * (k % 5)
            rect = (0.12 + off, 0.30 - off, 0.42, 0.42)
        panel = FreePanel(source, rect, keep_aspect=keep_aspect)
        self.panels.append(panel)
        self._render_panel(panel)
        if select:
            self.selected = len(self.panels) - 1
        self._refresh_overlay()
        self._notify()
        return panel

    def add_sources(self, sources):
        for s in sources:
            self.add_source(s, select=False)
        if self.panels:
            self.selected = len(self.panels) - 1
        self._refresh_overlay()
        self._notify()

    def remove_selected(self):
        if self.selected is None or not (0 <= self.selected < len(self.panels)):
            return
        panel = self.panels.pop(self.selected)
        try:
            if panel.ax is not None:
                panel.ax.remove()
        except Exception:
            pass
        self.selected = (len(self.panels) - 1) if self.panels else None
        self._recompute_all_data_flag()
        self._refresh_overlay()
        self._draw()
        self._notify()

    # ── render de un panel (delega en v5._draw_source_into) ───────────────────
    def _render_panel(self, panel: FreePanel):
        rec, flag = [], {"all_reconstructible": True}
        ax = self.fig.add_axes(panel.rect)
        try:
            _ax, kind = _V5._draw_source_into(
                ax, panel.source, 0,
                font_scale=self.font_scale, dpi=int(self.fig.dpi),
                raster_crop_white=True, keep_source_suptitle=True,
                source_records=rec, all_data_flag=flag,
                cache=self._cache, legend_policy="auto_if_overlap")
            panel.kind = kind
        except Exception as e:
            # placeholder visible para no romper la sesión
            ax.clear()
            ax.text(0.5, 0.5, f"⚠ no se pudo cargar:\n{panel.source}\n{e}",
                    ha="center", va="center", fontsize=8, color="crimson",
                    transform=ax.transAxes, wrap=True)
            ax.set_xticks([]); ax.set_yticks([])
            panel.kind = "error"
        panel.ax = ax
        if not flag.get("all_reconstructible", True):
            self._all_data["all_reconstructible"] = False
        self._apply_aspect(panel)

    def _apply_aspect(self, panel: FreePanel):
        if panel.ax is None:
            return
        if panel.is_image() and not panel.keep_aspect:
            try:
                panel.ax.set_aspect("auto")
            except Exception:
                pass
        elif panel.is_image() and panel.keep_aspect:
            try:
                panel.ax.set_aspect("equal")
            except Exception:
                pass

    def rebuild_all(self):
        """Reconstruye todos los Axes desde (source, rect). Usar tras cambios de
        fuente o de escala de fuente; mover/redimensionar NO requiere esto."""
        # quitar solo axes de paneles (preservar overlay en fig.patches)
        for p in self.panels:
            try:
                if p.ax is not None:
                    p.ax.remove()
            except Exception:
                pass
            p.ax = None
        self._all_data = {"all_reconstructible": True}
        for p in self.panels:
            self._render_panel(p)
        self._apply_labels()
        self._apply_suptitle()
        self._refresh_overlay()
        self._draw()

    def _recompute_all_data_flag(self):
        self._all_data = {"all_reconstructible": True}
        for p in self.panels:
            if p.kind in ("csv", "image", "raster", "vector", "error"):
                self._all_data["all_reconstructible"] = False

    # ── presets / alineación / distribución ───────────────────────────────────
    def apply_grid_preset(self, rows, cols, margin=0.06, gap=0.04):
        rects = grid_rects(rows, cols, margin, gap)
        for p, r in zip(self.panels, rects):
            p.rect = normalize_rect(r)
            if p.ax is not None:
                p.ax.set_position(p.rect)
        self._maybe_relabel()
        self._refresh_overlay()
        self._draw()
        self._notify()

    def apply_layout_name(self, layout_name):
        """Usa los layouts nombrados de v5 (1x2, 2x2, split…) como punto de
        partida, traduciéndolos a rects absolutos."""
        try:
            info = _V5._PANEL_LAYOUTS[layout_name]
            rows, cols = int(info["rows"]), int(info["cols"])
        except Exception:
            return
        self.apply_grid_preset(rows, cols)

    def _sel_panel(self):
        if self.selected is None or not (0 <= self.selected < len(self.panels)):
            return None
        return self.panels[self.selected]

    def set_rect(self, rect):
        p = self._sel_panel()
        if p is None:
            return
        p.rect = normalize_rect(rect)
        if p.ax is not None:
            p.ax.set_position(p.rect)
        self._maybe_relabel()
        self._refresh_overlay()
        self._draw()
        self._notify()

    def set_keep_aspect(self, keep):
        p = self._sel_panel()
        if p is None:
            return
        p.keep_aspect = bool(keep)
        self._apply_aspect(p)
        self._draw()
        self._notify()

    def align(self, how):
        """how in {'left','right','top','bottom','center_h','center_v'}."""
        if len(self.panels) < 2:
            return
        ref = self._sel_panel() or self.panels[0]
        rl, rb, rw, rh = ref.rect
        for p in self.panels:
            l, b, w, h = p.rect
            if how == "left":
                l = rl
            elif how == "right":
                l = rl + rw - w
            elif how == "bottom":
                b = rb
            elif how == "top":
                b = rb + rh - h
            elif how == "center_h":
                l = rl + (rw - w) / 2.0
            elif how == "center_v":
                b = rb + (rh - h) / 2.0
            p.rect = normalize_rect((l, b, w, h))
            if p.ax is not None:
                p.ax.set_position(p.rect)
        self._maybe_relabel()
        self._refresh_overlay(); self._draw(); self._notify()

    def equalize(self, what):
        """what in {'width','height'}: iguala al panel seleccionado."""
        ref = self._sel_panel()
        if ref is None or len(self.panels) < 2:
            return
        rl, rb, rw, rh = ref.rect
        for p in self.panels:
            l, b, w, h = p.rect
            if what == "width":
                w = rw
            elif what == "height":
                h = rh
            p.rect = normalize_rect((l, b, w, h))
            if p.ax is not None:
                p.ax.set_position(p.rect)
        self._maybe_relabel()
        self._refresh_overlay(); self._draw(); self._notify()

    def distribute(self, axis):
        """axis in {'h','v'}: reparte huecos uniformemente entre paneles."""
        if len(self.panels) < 3:
            return
        idx = list(range(len(self.panels)))
        if axis == "h":
            idx.sort(key=lambda i: self.panels[i].rect[0])
            lo = self.panels[idx[0]].rect[0]
            hi = self.panels[idx[-1]].rect[0]
            span = hi - lo
            step = span / (len(idx) - 1) if len(idx) > 1 else 0
            for k, i in enumerate(idx):
                l, b, w, h = self.panels[i].rect
                self.panels[i].rect = normalize_rect((lo + k * step, b, w, h))
        else:
            idx.sort(key=lambda i: self.panels[i].rect[1])
            lo = self.panels[idx[0]].rect[1]
            hi = self.panels[idx[-1]].rect[1]
            span = hi - lo
            step = span / (len(idx) - 1) if len(idx) > 1 else 0
            for k, i in enumerate(idx):
                l, b, w, h = self.panels[i].rect
                self.panels[i].rect = normalize_rect((l, lo + k * step, w, h))
        for p in self.panels:
            if p.ax is not None:
                p.ax.set_position(p.rect)
        self._maybe_relabel()
        self._refresh_overlay(); self._draw(); self._notify()

    # ── escala de fuente / rótulos / suptitle ─────────────────────────────────
    def set_font_scale(self, scale):
        self.font_scale = float(scale)
        self.rebuild_all()
        self._notify()

    def set_label_spec(self, spec):
        self.label_spec = spec
        self._apply_labels()
        self._draw()
        self._notify()

    def _apply_labels(self):
        """Rotula en ORDEN DE LECTURA (izq→der, arriba→abajo). Respeta la
        posición personalizada por panel (arrastre/coordenadas) si existe; si no,
        usa la posición global (_LABEL_POS, interior o exterior)."""
        # limpiar rótulos previos
        for p in self.panels:
            art = getattr(p, "label_artist", None)
            if art is not None:
                try:
                    art.remove()
                except Exception:
                    pass
                p.label_artist = None
        spec = self.label_spec
        if not spec or not spec.get("enabled", True):
            return
        kind = spec.get("kind", "alpha_lower")
        wrap = spec.get("wrap", "paren_both")
        pos_key = spec.get("position", "outside_top_left")
        fs = float(spec.get("fontsize", 12.0))
        fw = spec.get("fontweight", "bold")
        color = spec.get("color", "black")
        order = reading_order_indices([p.rect for p in self.panels])
        for label_i, panel_i in enumerate(order):
            p = self.panels[panel_i]
            if p.ax is None:
                continue
            text = _V5.format_panel_label(label_i, kind, wrap)
            if p.label_anchor is not None and p.label_anchor in _LABEL_POS:
                x, y, ha, va = _LABEL_POS[p.label_anchor]
            elif p.label_custom_xy is not None:
                x, y = p.label_custom_xy
                ha, va = "center", "center"
            else:
                x, y, ha, va = _LABEL_POS.get(pos_key, _LABEL_POS["outside_top_left"])
            t = p.ax.text(x, y, text, transform=p.ax.transAxes, ha=ha, va=va,
                          fontsize=fs, fontweight=fw, color=color,
                          clip_on=False, zorder=10005)
            try:
                t._pa_panel_label = True
            except Exception:
                pass
            p.label_artist = t

    def set_label_mode(self, on):
        """Activa/desactiva el arrastre de rótulos con el mouse (en vez de paneles)."""
        self.label_mode = bool(on)
        self._notify()

    def set_label_custom_xy(self, x, y):
        """Fija la posición del rótulo del panel SELECCIONADO por coordenadas
        (fracción de ejes: 0,0 = abajo-izq.; 1,1 = arriba-der.). Quita el ancla
        imantado si lo había."""
        p = self._sel_panel()
        if p is None:
            return
        p.label_custom_xy = (float(x), float(y))
        p.label_anchor = None
        art = getattr(p, "label_artist", None)
        if art is not None:
            art.set_position((float(x), float(y)))
            art.set_ha("center"); art.set_va("center")
        else:
            self._apply_labels()
        self._draw()
        self._notify()

    def set_label_anchor(self, anchor_key, all_panels=False):
        """Imanta el/los rótulo(s) a un ancla nombrada de _LABEL_POS (alineación
        idéntica entre paneles). Si anchor_key es None, vuelve a la global."""
        targets = (self.panels if all_panels
                   else ([self._sel_panel()] if self._sel_panel() else []))
        for p in targets:
            if p is None:
                continue
            p.label_anchor = anchor_key if anchor_key in _LABEL_POS else None
            p.label_custom_xy = None
        self._apply_labels()
        self._draw()
        self._notify()

    def reset_label_pos(self, all_panels=False):
        """Vuelve el/los rótulo(s) a la posición global (quita personalizada y ancla)."""
        targets = (self.panels if all_panels
                   else ([self._sel_panel()] if self._sel_panel() else []))
        for p in targets:
            if p is not None:
                p.label_custom_xy = None
                p.label_anchor = None
        self._apply_labels()
        self._draw()
        self._notify()

    def _label_at(self, event):
        """Índice del panel cuyo rótulo está bajo el puntero, o None."""
        if event.x is None or event.y is None:
            return None
        try:
            rend = self.fig.canvas.get_renderer()
        except Exception:
            rend = None
        for i, p in enumerate(self.panels):
            art = getattr(p, "label_artist", None)
            if art is None or not art.get_visible():
                continue
            try:
                bb = art.get_window_extent(renderer=rend)
            except Exception:
                continue
            if (bb.x0 - 3) <= event.x <= (bb.x1 + 3) and \
               (bb.y0 - 3) <= event.y <= (bb.y1 + 3):
                return i
        return None

    # ── textos libres (v8) ────────────────────────────────────────────────────
    def add_text(self, text="Texto", xy=None, *, fontfamily=None, fontsize=14.0,
                 bold=False, italic=False, color="black", ha="center",
                 va="center", rotation=0.0, select=True):
        """Agrega un texto libre (coords de figura). Si xy es None, lo coloca en
        el centro. Devuelve el FreeText creado."""
        if xy is None:
            xy = (0.5, 0.5)
        ft = FreeText(text=text, x=xy[0], y=xy[1], fontfamily=fontfamily,
                      fontsize=fontsize, bold=bold, italic=italic, color=color,
                      ha=ha, va=va, rotation=rotation)
        self.texts.append(ft)
        self._render_text(ft)
        if select:
            self.selected_text = len(self.texts) - 1
            self.selected = None
        self._refresh_overlay()
        self._draw()
        self._notify()
        return ft

    def _render_text(self, ft: FreeText):
        """(Re)crea el artista Text a nivel figura de un FreeText."""
        art = getattr(ft, "artist", None)
        if art is not None:
            try:
                art.remove()
            except Exception:
                pass
            ft.artist = None
        kw = dict(transform=self.fig.transFigure, ha=ft.ha, va=ft.va,
                  fontsize=ft.fontsize, color=ft.color,
                  fontweight=("bold" if ft.bold else "normal"),
                  fontstyle=("italic" if ft.italic else "normal"),
                  rotation=ft.rotation, clip_on=False, zorder=10004)
        if ft.fontfamily:
            kw["fontfamily"] = ft.fontfamily
        t = self.fig.text(ft.x, ft.y, ft.text, **kw)
        try:
            t._pa_free_text = True   # marca para diagnóstico/limpieza
        except Exception:
            pass
        ft.artist = t

    def _sel_text(self):
        if self.selected_text is None:
            return None
        if 0 <= self.selected_text < len(self.texts):
            return self.texts[self.selected_text]
        return None

    def update_selected_text(self, *, text=None, fontfamily=None, fontsize=None,
                             bold=None, italic=None, color=None, rotation=None):
        """Actualiza la cosmética/contenido del texto seleccionado."""
        ft = self._sel_text()
        if ft is None:
            return
        if text is not None:
            ft.text = str(text)
        if fontfamily is not None:
            ft.fontfamily = fontfamily or None
        if fontsize is not None:
            ft.fontsize = float(fontsize)
        if bold is not None:
            ft.bold = bool(bold)
        if italic is not None:
            ft.italic = bool(italic)
        if color is not None:
            ft.color = color
        if rotation is not None:
            ft.rotation = float(rotation)
        self._render_text(ft)
        self._refresh_overlay()
        self._draw()
        self._notify()

    def remove_selected_text(self):
        ft = self._sel_text()
        if ft is None:
            return
        art = getattr(ft, "artist", None)
        if art is not None:
            try:
                art.remove()
            except Exception:
                pass
        self.texts.pop(self.selected_text)
        self.selected_text = (len(self.texts) - 1) if self.texts else None
        self._refresh_overlay()
        self._draw()
        self._notify()

    def _text_at(self, event):
        """Índice del texto libre bajo el puntero (de arriba hacia abajo), o None."""
        if event.x is None or event.y is None:
            return None
        try:
            rend = self.fig.canvas.get_renderer()
        except Exception:
            rend = None
        for i in range(len(self.texts) - 1, -1, -1):
            art = getattr(self.texts[i], "artist", None)
            if art is None or not art.get_visible():
                continue
            try:
                bb = art.get_window_extent(renderer=rend)
            except Exception:
                continue
            if (bb.x0 - 3) <= event.x <= (bb.x1 + 3) and \
               (bb.y0 - 3) <= event.y <= (bb.y1 + 3):
                return i
        return None

    def _refresh_text_overlay(self):
        ft = self._sel_text()
        if ft is None or getattr(ft, "artist", None) is None:
            self._text_sel.set_visible(False)
            return
        try:
            rend = self.fig.canvas.get_renderer()
            bb = ft.artist.get_window_extent(renderer=rend)
            inv = self.fig.transFigure.inverted()
            (x0, y0) = inv.transform((bb.x0, bb.y0))
            (x1, y1) = inv.transform((bb.x1, bb.y1))
            pad = 0.006
            self._text_sel.set_bounds(x0 - pad, y0 - pad,
                                      (x1 - x0) + 2 * pad, (y1 - y0) + 2 * pad)
            self._text_sel.set_visible(True)
        except Exception:
            self._text_sel.set_visible(False)

    def set_suptitle(self, text):
        self.suptitle = (text or None)
        self._apply_suptitle()
        self._draw()
        self._notify()

    def _apply_suptitle(self):
        try:
            if self.suptitle:
                self.fig.suptitle(str(self.suptitle))
            elif self.fig._suptitle is not None:
                self.fig._suptitle.set_text("")
        except Exception:
            pass

    def set_figsize(self, w_in, h_in):
        try:
            self.fig.set_size_inches(float(w_in), float(h_in), forward=True)
            self._refresh_overlay()
            self._draw()
            self._notify()
        except Exception:
            pass

    # ── overlay (marco + manijas + grilla) ────────────────────────────────────
    def _rebuild_grid_overlay(self):
        for ln in self._grid_lines:
            try:
                ln.remove()
            except Exception:
                pass
        self._grid_lines = []
        if not self.show_grid or self.grid_step <= 0:
            return
        n = int(round(1.0 / self.grid_step))
        for k in range(1, n):
            x = k * self.grid_step
            lnx = Line2D([x, x], [0, 1], lw=0.5, color="#bbbbbb", alpha=0.6,
                         transform=self.fig.transFigure, zorder=1)
            lny = Line2D([0, 1], [x, x], lw=0.5, color="#bbbbbb", alpha=0.6,
                         transform=self.fig.transFigure, zorder=1)
            self.fig.add_artist(lnx); self.fig.add_artist(lny)
            self._grid_lines += [lnx, lny]

    def set_show_grid(self, show):
        self.show_grid = bool(show)
        self._rebuild_grid_overlay()
        self._draw()

    def _handle_centers(self, rect):
        l, b, w, h = rect
        r, t = l + w, b + h
        cx, cy = l + w / 2.0, b + h / 2.0
        return {
            "sw": (l, b), "se": (r, b), "nw": (l, t), "ne": (r, t),
            "w": (l, cy), "e": (r, cy), "s": (cx, b), "n": (cx, t),
        }

    def _refresh_overlay(self):
        p = self._sel_panel()
        if p is None:
            self._sel_rect.set_visible(False)
            for hp in self._handles:
                hp.set_visible(False)
            self._refresh_text_overlay()
            return
        l, b, w, h = p.rect
        self._sel_rect.set_bounds(l, b, w, h)
        self._sel_rect.set_visible(True)
        tx, ty = self._tol_frac()
        hw, hh = tx * 1.4, ty * 1.4
        centers = self._handle_centers(p.rect)
        for hp, name in zip(self._handles, _HANDLES):
            cx, cy = centers[name]
            hp.set_bounds(cx - hw, cy - hh, 2 * hw, 2 * hh)
            hp.set_visible(True)
        self._refresh_text_overlay()

    # ── eventos de mouse/teclado ──────────────────────────────────────────────
    def _panel_at(self, fx, fy):
        """Devuelve (idx, handle) del panel bajo el puntero. Prioriza el
        seleccionado (para no perder sus manijas) y luego de arriba hacia abajo
        en orden inverso de creación."""
        tx, ty = self._tol_frac()
        order = []
        if self.selected is not None:
            order.append(self.selected)
        order += [i for i in range(len(self.panels) - 1, -1, -1)
                  if i != self.selected]
        for i in order:
            hit = hit_test_rect(self.panels[i].rect, fx, fy, tx, ty)
            if hit is not None:
                return i, hit
        return None, None

    def _on_press(self, event):
        # ignorar si hay herramienta de toolbar activa (pan/zoom)
        tb = getattr(self.fig.canvas, "toolbar", None)
        if tb is not None and getattr(tb, "mode", "") not in ("", None):
            return
        pt = self._event_to_frac(event)
        if pt is None or event.button != 1:
            return
        fx, fy = pt
        # 1) Un click sobre un TEXTO libre lo agarra para arrastrar (están arriba
        #    de todo). Tienen prioridad sobre rótulos y paneles.
        ti = self._text_at(event)
        if ti is not None:
            self.selected_text = ti
            self.selected = None
            ft = self.texts[ti]
            self._drag = {"mode": "text", "tidx": ti, "off": (fx - ft.x, fy - ft.y)}
            self._refresh_overlay(); self._draw(); self._notify()
            return
        # 2) En modo rótulo, un click sobre un rótulo lo agarra para arrastrar.
        if self.label_mode:
            li = self._label_at(event)
            if li is not None:
                self.selected = li
                self.selected_text = None
                self._drag = {"mode": "label", "idx": li}
                self._refresh_overlay(); self._draw(); self._notify()
                return
        idx, hit = self._panel_at(fx, fy)
        if idx is None:
            self.selected = None
            self.selected_text = None
            self._refresh_overlay(); self._draw(); self._notify()
            return
        self.selected = idx
        self.selected_text = None
        p = self.panels[idx]
        if hit == "body":
            l, b, w, h = p.rect
            self._drag = {"mode": "move", "idx": idx, "off": (fx - l, fy - b)}
        else:
            self._drag = {"mode": "resize", "idx": idx, "handle": hit}
        self._refresh_overlay(); self._draw(); self._notify()

    def _on_motion(self, event):
        if self._drag is None:
            return
        mode = self._drag.get("mode")
        # arrastre de TEXTO libre (coords de figura)
        if mode == "text":
            pt = self._event_to_frac(event)
            if pt is None:
                return
            fx, fy = pt
            ox, oy = self._drag.get("off", (0.0, 0.0))
            nx, ny = fx - ox, fy - oy
            if self.snapping:
                nx = snap_value(nx, self.grid_step, max(self._tol_frac()) * 1.5)
                ny = snap_value(ny, self.grid_step, max(self._tol_frac()) * 1.5)
            ft = self.texts[self._drag["tidx"]]
            ft.x, ft.y = float(nx), float(ny)
            if getattr(ft, "artist", None) is not None:
                ft.artist.set_position((ft.x, ft.y))
            self._refresh_text_overlay()
            self.fig.canvas.draw_idle()
            self._notify()
            return
        p = self.panels[self._drag["idx"]]
        if mode == "label":
            if event.x is None or event.y is None or p.ax is None:
                return
            ax_x, ax_y = p.ax.transAxes.inverted().transform((event.x, event.y))
            p.label_custom_xy = (float(ax_x), float(ax_y))
            p.label_anchor = None
            art = getattr(p, "label_artist", None)
            if art is not None:
                art.set_position((float(ax_x), float(ax_y)))
                art.set_ha("center"); art.set_va("center")
            self.fig.canvas.draw_idle()
            self._notify()
            return
        pt = self._event_to_frac(event)
        if pt is None:
            return
        fx, fy = pt
        if mode == "move":
            ox, oy = self._drag["off"]
            l, b, w, h = p.rect
            rect = (fx - ox, fy - oy, w, h)
        else:
            rect = resize_rect(p.rect, self._drag["handle"], fx, fy)
        rect = self._maybe_snap(rect, exclude_idx=self._drag["idx"])
        p.rect = normalize_rect(rect)
        if p.ax is not None:
            p.ax.set_position(p.rect)
        self._refresh_overlay()
        self.fig.canvas.draw_idle()

    def _on_release(self, event):
        if self._drag is not None:
            mode = self._drag.get("mode")
            idx = self._drag.get("idx")
            self._drag = None
            # al soltar una VIÑETA arrastrada: si el imantado está activo,
            # engancharla al ancla (de _LABEL_POS) más cercana dentro de tol,
            # para que todas las viñetas queden alineadas idénticamente.
            if mode == "label" and idx is not None and 0 <= idx < len(self.panels):
                p = self.panels[idx]
                if self.snapping and p.label_custom_xy is not None:
                    x, y = p.label_custom_xy
                    key, sx, sy, ha, va = snap_label_to_anchor(x, y, _LABEL_SNAP_TOL)
                    if key is not None:
                        p.label_anchor = key
                        p.label_custom_xy = None
                self._apply_labels()
                self._draw()
            # tras mover/redimensionar un panel, reasignar viñetas en orden de
            # lectura (las letras siguen a la posición, no al orden de creación)
            if mode in ("move", "resize") and self.label_spec \
                    and self.label_spec.get("enabled", True):
                self._apply_labels()
                self._draw()
            self._refresh_overlay()
            self._notify()

    def _maybe_snap(self, rect, exclude_idx=None):
        if not self.snapping:
            return rect
        tx, ty = self._tol_frac()
        tol = max(tx, ty) * 1.5
        rect = snap_rect_to_grid(rect, self.grid_step, tol)
        others = [self.panels[i].rect for i in range(len(self.panels))
                  if i != exclude_idx]
        if others:
            rect = snap_rect_to_edges(rect, others, tol)
        return rect

    def _on_key(self, event):
        if event.key in ("delete", "backspace"):
            if self.selected_text is not None:
                self.remove_selected_text()
            else:
                self.remove_selected()
            return
        p = self._sel_panel()
        if p is None:
            return
        step = (self.grid_step if "shift" in (event.key or "") else 0.005)
        l, b, w, h = p.rect
        key = event.key or ""
        if key.endswith("left"):
            l -= step
        elif key.endswith("right"):
            l += step
        elif key.endswith("up"):
            b += step
        elif key.endswith("down"):
            b -= step
        else:
            return
        self.set_rect((l, b, w, h))

    # ── refresco / notificación ───────────────────────────────────────────────
    def _maybe_relabel(self):
        """Reasigna las viñetas en orden de lectura si están activas (las letras
        siguen a la posición de los paneles, no al orden de creación)."""
        if self.label_spec and self.label_spec.get("enabled", True):
            self._apply_labels()

    def _draw(self):
        try:
            self.fig.canvas.draw_idle()
        except Exception:
            pass

    def _notify(self):
        if callable(self.on_change):
            try:
                self.on_change(self)
            except Exception:
                pass

    def show(self):
        try:
            plt.ion()
        except Exception:
            pass
        try:
            self.fig.canvas.draw()
        except Exception:
            pass
        try:
            mgr = getattr(self.fig.canvas, "manager", None)
            if mgr is not None:
                mgr.show()
        except Exception:
            pass
        try:
            plt.show(block=False)
        except Exception:
            pass
        self._draw()
        return self.fig

    # ── guardado (delega en v5.save_composite_figure) ─────────────────────────
    def _stamp_metadata(self):
        try:
            _V5._freeze_positions(self.fig)
        except Exception:
            pass
        self._recompute_all_data_flag()
        meta = {
            "format_version": _FORMAT_VERSION,
            "generator": "figure_panel_assembler_v8.py",
            "layout": "free",
            "panels": [{"source": p.source, "rect": list(p.rect),
                        "kind": p.kind, "keep_aspect": p.keep_aspect}
                       for p in self.panels],
            "font_scale": float(self.font_scale),
            "suptitle": self.suptitle,
            "free_texts": [ft.to_dict() for ft in self.texts],
            "all_sources_reconstructible": bool(self._all_data["all_reconstructible"]),
        }
        self.fig._pa_panel_metadata = meta
        self.fig._pa_all_panels_from_data = bool(self._all_data["all_reconstructible"])
        self.fig._serialize_axes_positions = True
        self.fig._save_subplots_adjust_none = True
        self.fig._apply_tight_layout_on_load = False

    def _set_overlay_visible(self, vis: bool):
        """Muestra/oculta el overlay de edición (marco + manijas + grilla guía).
        Se oculta SIEMPRE antes de exportar para que no aparezca en el archivo."""
        try:
            self._sel_rect.set_visible(vis and self._sel_panel() is not None)
            for hp in self._handles:
                hp.set_visible(vis and self._sel_panel() is not None)
            for ln in self._grid_lines:
                ln.set_visible(vis and self.show_grid)
            # el marco de selección de texto NO debe grabarse (los textos sí)
            self._text_sel.set_visible(vis and self._sel_text() is not None)
        except Exception:
            pass

    def save(self, base_filename=None, *, include_json="auto", save_png=True,
             save_pdf=True, dpi=300):
        base = base_filename or self.base_filename
        self._stamp_metadata()
        # CRÍTICO: el overlay de edición no debe quedar grabado en el archivo.
        self._set_overlay_visible(False)
        try:
            self.fig.canvas.draw()
        except Exception:
            pass
        try:
            return _V5.save_composite_figure(
                self.fig, base, include_json=include_json,
                save_png=save_png, save_pdf=save_pdf, dpi=dpi)
        finally:
            self._set_overlay_visible(True)
            self._refresh_overlay()
            self._draw()

    def to_config(self):
        """Receta serializable (para reabrir el ensamble libre tal cual)."""
        return {
            "format_version": _FORMAT_VERSION,
            "figsize": list(self.fig.get_size_inches()),
            "dpi": int(self.fig.dpi),
            "font_scale": self.font_scale,
            "snapping": self.snapping,
            "grid_step": self.grid_step,
            "suptitle": self.suptitle,
            "label_spec": self.label_spec,
            "panels": [{"source": p.source, "rect": list(p.rect),
                        "keep_aspect": p.keep_aspect,
                        "label_custom_xy": (list(p.label_custom_xy)
                                            if p.label_custom_xy else None),
                        "label_anchor": p.label_anchor}
                       for p in self.panels],
            "texts": [ft.to_dict() for ft in self.texts],
        }

    def save_recipe(self, path):
        p = Path(path).with_suffix(".free.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_config(), f, indent=2, ensure_ascii=False)
        return p

    @classmethod
    def from_recipe(cls, path, **kw):
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        asm = cls(figsize=tuple(cfg.get("figsize", (8.0, 6.0))),
                  dpi=int(cfg.get("dpi", 150)),
                  snapping=cfg.get("snapping", True),
                  grid_step=cfg.get("grid_step", 1.0 / 24.0),
                  font_scale=cfg.get("font_scale", 0.9), **kw)
        for pd in cfg.get("panels", []):
            pan = asm.add_source(pd["source"], rect=tuple(pd["rect"]),
                                 keep_aspect=pd.get("keep_aspect", True),
                                 select=False)
            cxy = pd.get("label_custom_xy")
            if cxy:
                pan.label_custom_xy = tuple(cxy)
            anc = pd.get("label_anchor")
            if anc in _LABEL_POS:
                pan.label_anchor = anc
        asm.suptitle = cfg.get("suptitle")
        asm.label_spec = cfg.get("label_spec")
        # textos libres (v8)
        for td in cfg.get("texts", []) or []:
            try:
                ft = FreeText.from_dict(td)
                asm.texts.append(ft)
                asm._render_text(ft)
            except Exception:
                pass
        asm._apply_suptitle(); asm._apply_labels()
        if asm.panels:
            asm.selected = len(asm.panels) - 1
        asm._refresh_overlay(); asm._draw()
        return asm


# ═════════════════════════════════════════════════════════════════════════════
#  PANEL DE CONTROL Qt (modalidad figure_editor3) — listas desplegables, sin stdin
# ═════════════════════════════════════════════════════════════════════════════
def _qt():
    try:
        from matplotlib.backends.qt_compat import QtWidgets, QtCore, QtGui
        return QtWidgets, QtCore, QtGui
    except Exception:
        return None


class _AssemblerControlPanel:
    """Ventana Qt no modal, junto al lienzo. Vive en el event loop del kernel."""

    def __init__(self, asm: FreeCanvasAssembler):
        q = _qt()
        if q is None:
            raise RuntimeError("Qt no disponible")
        self.QtWidgets, self.QtCore, self.QtGui = q
        self.asm = asm
        self.asm.on_change = self._sync_from_asm
        self._syncing = False
        self._build_ui()
        self._sync_from_asm(self.asm)

    def _build_ui(self):
        QtWidgets, QtCore, QtGui = self.QtWidgets, self.QtCore, self.QtGui
        self.win = QtWidgets.QWidget()
        self.win.setWindowTitle("Ensamble libre — control (v8)")
        self.win.resize(540, 820)
        try:
            self.win.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, True)
        except Exception:
            pass
        # Layout exterior: un área con scroll para que ningún grupo se superponga
        # aunque el contenido crezca; los botones de guardado quedan fijos abajo.
        outer = QtWidgets.QVBoxLayout(self.win)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(6)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        inner = QtWidgets.QWidget()
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)
        root = QtWidgets.QVBoxLayout(inner)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # fuentes
        gb_src = QtWidgets.QGroupBox("Figuras")
        v = QtWidgets.QVBoxLayout(gb_src)
        bar = QtWidgets.QHBoxLayout()
        b_add = QtWidgets.QPushButton("➕ Agregar…")
        b_add.clicked.connect(self._on_add)
        b_del = QtWidgets.QPushButton("🗑 Quitar")
        b_del.clicked.connect(lambda: self.asm.remove_selected())
        bar.addWidget(b_add); bar.addWidget(b_del)
        v.addLayout(bar)
        self.lst = QtWidgets.QListWidget()
        self.lst.currentRowChanged.connect(self._on_list_select)
        self.lst.setMaximumHeight(150)
        v.addWidget(self.lst)
        root.addWidget(gb_src)

        # presets de grilla (lista desplegable)
        gb_grid = QtWidgets.QGroupBox("Punto de partida (grilla)")
        g = QtWidgets.QHBoxLayout(gb_grid)
        self.cmb_layout = QtWidgets.QComboBox()
        self.cmb_layout.addItem("Layout…", None)
        try:
            for k, info in _V5._PANEL_LAYOUTS.items():
                self.cmb_layout.addItem(info.get("label", k), k)
        except Exception:
            for k in ("1x2", "2x1", "2x2", "1x3", "3x1", "2x3", "3x2", "3x3"):
                self.cmb_layout.addItem(k, k)
        b_apply = QtWidgets.QPushButton("Aplicar")
        b_apply.clicked.connect(self._on_apply_layout)
        g.addWidget(self.cmb_layout, 1); g.addWidget(b_apply)
        root.addWidget(gb_grid)

        # rect exacto de la selección
        gb_rect = QtWidgets.QGroupBox("Posición/tamaño de la selección (fracción)")
        form = QtWidgets.QFormLayout(gb_rect)
        self.sp_x = self._dspin(); self.sp_y = self._dspin()
        self.sp_w = self._dspin(lo=_MIN_FRAC); self.sp_h = self._dspin(lo=_MIN_FRAC)
        for sp in (self.sp_x, self.sp_y, self.sp_w, self.sp_h):
            sp.valueChanged.connect(self._on_rect_edit)
        form.addRow("x (izq.)", self.sp_x)
        form.addRow("y (abajo)", self.sp_y)
        form.addRow("ancho", self.sp_w)
        form.addRow("alto", self.sp_h)
        self.chk_aspect = QtWidgets.QCheckBox("Mantener proporción (imágenes)")
        self.chk_aspect.stateChanged.connect(
            lambda s: self.asm.set_keep_aspect(bool(s)))
        form.addRow(self.chk_aspect)
        root.addWidget(gb_rect)

        # alinear / distribuir (listas desplegables)
        gb_al = QtWidgets.QGroupBox("Alinear / distribuir / igualar")
        al = QtWidgets.QGridLayout(gb_al)
        self.cmb_align = QtWidgets.QComboBox()
        for lab, key in [("Alinear…", None), ("Izquierda", "left"),
                         ("Derecha", "right"), ("Arriba", "top"),
                         ("Abajo", "bottom"), ("Centrar H", "center_h"),
                         ("Centrar V", "center_v")]:
            self.cmb_align.addItem(lab, key)
        self.cmb_align.activated.connect(self._on_align)
        self.cmb_eq = QtWidgets.QComboBox()
        for lab, key in [("Igualar…", None), ("Igualar ancho", "width"),
                         ("Igualar alto", "height")]:
            self.cmb_eq.addItem(lab, key)
        self.cmb_eq.activated.connect(self._on_equalize)
        self.cmb_dist = QtWidgets.QComboBox()
        for lab, key in [("Distribuir…", None), ("Horizontal", "h"),
                         ("Vertical", "v")]:
            self.cmb_dist.addItem(lab, key)
        self.cmb_dist.activated.connect(self._on_distribute)
        al.addWidget(self.cmb_align, 0, 0)
        al.addWidget(self.cmb_eq, 0, 1)
        al.addWidget(self.cmb_dist, 1, 0, 1, 2)
        root.addWidget(gb_al)

        # snapping / grilla / tamaño de figura
        gb_opt = QtWidgets.QGroupBox("Opciones")
        o = QtWidgets.QFormLayout(gb_opt)
        self.chk_snap = QtWidgets.QCheckBox("Imantar a grilla y bordes")
        self.chk_snap.setChecked(self.asm.snapping)
        self.chk_snap.stateChanged.connect(
            lambda s: setattr(self.asm, "snapping", bool(s)))
        self.chk_gridv = QtWidgets.QCheckBox("Mostrar grilla guía")
        self.chk_gridv.setChecked(self.asm.show_grid)
        self.chk_gridv.stateChanged.connect(
            lambda s: self.asm.set_show_grid(bool(s)))
        self.sp_step = QtWidgets.QSpinBox(); self.sp_step.setRange(4, 64)
        self.sp_step.setValue(int(round(1.0 / max(self.asm.grid_step, 1e-6))))
        self.sp_step.valueChanged.connect(
            lambda n: (setattr(self.asm, "grid_step", 1.0 / max(1, n)),
                       self.asm._rebuild_grid_overlay(), self.asm._draw()))
        self.sp_fs = self._dspin(lo=0.4, hi=2.0, step=0.05, dec=2)
        self.sp_fs.setValue(self.asm.font_scale)
        self.sp_fs.valueChanged.connect(self._on_font_scale)
        sz = QtWidgets.QHBoxLayout()
        w_in, h_in = self.asm.fig.get_size_inches()
        self.sp_fw = self._dspin(lo=2.0, hi=20.0, step=0.5, dec=1); self.sp_fw.setValue(float(w_in))
        self.sp_fh = self._dspin(lo=2.0, hi=20.0, step=0.5, dec=1); self.sp_fh.setValue(float(h_in))
        b_sz = QtWidgets.QPushButton("Aplicar")
        b_sz.clicked.connect(lambda: self.asm.set_figsize(self.sp_fw.value(), self.sp_fh.value()))
        szw = QtWidgets.QWidget(); szl = QtWidgets.QHBoxLayout(szw); szl.setContentsMargins(0,0,0,0)
        szl.addWidget(self.sp_fw); szl.addWidget(QtWidgets.QLabel("×")); szl.addWidget(self.sp_fh); szl.addWidget(b_sz)
        o.addRow(self.chk_snap)
        o.addRow(self.chk_gridv)
        o.addRow("Paso grilla (1/N)", self.sp_step)
        o.addRow("Escala fuente", self.sp_fs)
        o.addRow("Figura (in)", szw)
        root.addWidget(gb_opt)

        # rótulos / suptitle
        gb_lab = QtWidgets.QGroupBox("Rótulos (viñetas) y título")
        lab = QtWidgets.QFormLayout(gb_lab)
        self.cmb_labstyle = QtWidgets.QComboBox()
        # (etiqueta visible, (kind, wrap))
        for lab_txt, key in [("Sin rótulos", None),
                             ("a)  b)  c)", ("alpha_lower", "paren_right")),
                             ("(a) (b) (c)", ("alpha_lower", "paren_both")),
                             ("a.  b.  c.", ("alpha_lower", "dot")),
                             ("a  b  c", ("alpha_lower", "bare")),
                             ("(A) (B) (C)", ("alpha_upper", "paren_both")),
                             ("(i) (ii) (iii)", ("roman_lower", "paren_both")),
                             ("(I) (II) (III)", ("roman_upper", "paren_both")),
                             ("(1) (2) (3)", ("arabic", "paren_both"))]:
            self.cmb_labstyle.addItem(lab_txt, key)
        self.cmb_labstyle.activated.connect(self._on_labels)
        # posición: 9 interiores + 8 exteriores (espejo)
        self.cmb_labpos = QtWidgets.QComboBox()
        for lab_txt, key in [
                ("Interior ↖ arriba-izq.", "inside_top_left"),
                ("Interior ↑ arriba-centro", "inside_top_center"),
                ("Interior ↗ arriba-der.", "inside_top_right"),
                ("Interior ← centro-izq.", "inside_center_left"),
                ("Interior • centro", "inside_center"),
                ("Interior → centro-der.", "inside_center_right"),
                ("Interior ↙ abajo-izq.", "inside_bottom_left"),
                ("Interior ↓ abajo-centro", "inside_bottom_center"),
                ("Interior ↘ abajo-der.", "inside_bottom_right")]:
            self.cmb_labpos.addItem(lab_txt, key)
        self.cmb_labpos.insertSeparator(self.cmb_labpos.count())
        for lab_txt, key in [
                ("Exterior ↖ arriba-izq.", "outside_top_left"),
                ("Exterior ↑ arriba-centro", "outside_top_center"),
                ("Exterior ↗ arriba-der.", "outside_top_right"),
                ("Exterior ← centro-izq.", "outside_center_left"),
                ("Exterior → centro-der.", "outside_center_right"),
                ("Exterior ↙ abajo-izq.", "outside_bottom_left"),
                ("Exterior ↓ abajo-centro", "outside_bottom_center"),
                ("Exterior ↘ abajo-der.", "outside_bottom_right")]:
            self.cmb_labpos.addItem(lab_txt, key)
        # arrancar en exterior arriba-izq. (lo más común para (a),(b),…)
        i_ext = self.cmb_labpos.findData("outside_top_left")
        if i_ext >= 0:
            self.cmb_labpos.setCurrentIndex(i_ext)
        self.cmb_labpos.activated.connect(self._on_labels)
        # tamaño de fuente del rótulo
        self.sp_lfs = self._dspin(lo=5.0, hi=40.0, step=0.5, dec=1)
        self.sp_lfs.setValue(12.0)
        self.sp_lfs.valueChanged.connect(self._on_labels)
        # modo arrastre con el mouse
        self.chk_labmove = QtWidgets.QCheckBox(
            "Mover rótulos con el mouse (en vez de paneles)")
        self.chk_labmove.stateChanged.connect(
            lambda s: self.asm.set_label_mode(bool(s)))
        # coordenadas del rótulo de la selección (fracción de ejes)
        self.sp_lx = self._dspin(lo=-0.4, hi=1.4, step=0.02, dec=3)
        self.sp_ly = self._dspin(lo=-0.4, hi=1.4, step=0.02, dec=3)
        self.sp_lx.valueChanged.connect(self._on_label_xy)
        self.sp_ly.valueChanged.connect(self._on_label_xy)
        coord = QtWidgets.QWidget(); cl = QtWidgets.QHBoxLayout(coord)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.addWidget(QtWidgets.QLabel("x")); cl.addWidget(self.sp_lx)
        cl.addWidget(QtWidgets.QLabel("y")); cl.addWidget(self.sp_ly)
        b_lreset = QtWidgets.QPushButton("Reset")
        b_lreset.setToolTip("Vuelve el rótulo de la selección a la posición global")
        b_lreset.clicked.connect(lambda: self.asm.reset_label_pos(False))
        b_lresetall = QtWidgets.QPushButton("Reset todas")
        b_lresetall.clicked.connect(lambda: self.asm.reset_label_pos(True))
        cl.addWidget(b_lreset); cl.addWidget(b_lresetall)
        self.txt_sup = QtWidgets.QLineEdit()
        self.txt_sup.editingFinished.connect(
            lambda: self.asm.set_suptitle(self.txt_sup.text()))
        lab.addRow("Estilo", self.cmb_labstyle)
        lab.addRow("Posición", self.cmb_labpos)
        lab.addRow("Tamaño fuente", self.sp_lfs)
        lab.addRow(self.chk_labmove)
        lab.addRow("Coord. rótulo", coord)
        lab.addRow("Suptitle", self.txt_sup)
        root.addWidget(gb_lab)

        # ── textos libres (arrastrables) ──────────────────────────────────────
        gb_txt = QtWidgets.QGroupBox("Textos libres (arrastrables)")
        tlay = QtWidgets.QVBoxLayout(gb_txt)
        tbar = QtWidgets.QHBoxLayout()
        b_tadd = QtWidgets.QPushButton("➕ Agregar texto")
        b_tadd.clicked.connect(self._on_text_add)
        b_tdel = QtWidgets.QPushButton("🗑 Quitar texto")
        b_tdel.clicked.connect(lambda: self.asm.remove_selected_text())
        tbar.addWidget(b_tadd); tbar.addWidget(b_tdel)
        tlay.addLayout(tbar)
        self.lst_txt = QtWidgets.QListWidget()
        self.lst_txt.currentRowChanged.connect(self._on_text_list_select)
        self.lst_txt.setMaximumHeight(90)
        tlay.addWidget(self.lst_txt)

        tform = QtWidgets.QFormLayout()
        tform.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        tform.setLabelAlignment(QtCore.Qt.AlignRight)
        self.ed_txt = QtWidgets.QLineEdit()
        self.ed_txt.setPlaceholderText("Contenido del texto…")
        self.ed_txt.textEdited.connect(self._on_text_props)
        tform.addRow("Texto", self.ed_txt)
        # tipo de letra
        self.cmb_family = QtWidgets.QFontComboBox()
        self.cmb_family.setEditable(False)
        self.cmb_family.currentFontChanged.connect(self._on_text_props)
        tform.addRow("Tipo de letra", self.cmb_family)
        # tamaño + negrita + itálica en una fila
        sr = QtWidgets.QWidget(); srl = QtWidgets.QHBoxLayout(sr)
        srl.setContentsMargins(0, 0, 0, 0)
        self.sp_tfs = self._dspin(lo=4.0, hi=120.0, step=1.0, dec=1)
        self.sp_tfs.setValue(14.0)
        self.sp_tfs.valueChanged.connect(self._on_text_props)
        self.chk_tbold = QtWidgets.QCheckBox("Negrita")
        self.chk_tbold.stateChanged.connect(self._on_text_props)
        self.chk_tital = QtWidgets.QCheckBox("Itálica")
        self.chk_tital.stateChanged.connect(self._on_text_props)
        srl.addWidget(self.sp_tfs, 1)
        srl.addWidget(self.chk_tbold); srl.addWidget(self.chk_tital)
        tform.addRow("Tamaño", sr)
        # color
        cr = QtWidgets.QWidget(); crl = QtWidgets.QHBoxLayout(cr)
        crl.setContentsMargins(0, 0, 0, 0)
        self._text_color = "#000000"
        self.btn_tcolor = QtWidgets.QPushButton("Elegir color…")
        self.btn_tcolor.clicked.connect(self._on_text_color)
        self.lbl_tswatch = QtWidgets.QLabel()
        self.lbl_tswatch.setFixedSize(28, 18)
        self.lbl_tswatch.setStyleSheet(
            "background:#000000; border:1px solid #888;")
        crl.addWidget(self.btn_tcolor, 1); crl.addWidget(self.lbl_tswatch)
        tform.addRow("Color", cr)
        tlay.addLayout(tform)
        tnote = QtWidgets.QLabel(
            "Hacé click en un texto del lienzo para moverlo. Los textos se "
            "guardan en el .json y quedan editables en el editor (el tipo de "
            "letra sobrevive al round-trip solo con el editor parcheado).")
        tnote.setWordWrap(True)
        tnote.setStyleSheet("color:#777; font-size:10px;")
        tlay.addWidget(tnote)
        root.addWidget(gb_txt)
        root.addStretch(1)

        # guardar (fijo abajo, fuera del scroll)
        sv = QtWidgets.QHBoxLayout()
        b_save = QtWidgets.QPushButton("💾 Guardar (.json/.csv/.png/.pdf)")
        b_save.clicked.connect(self._on_save)
        b_recipe = QtWidgets.QPushButton("📋 Guardar receta")
        b_recipe.clicked.connect(self._on_save_recipe)
        sv.addWidget(b_save); sv.addWidget(b_recipe)
        outer.addLayout(sv)

        self.status = QtWidgets.QLabel(
            "Arrastrá para mover; estirá bordes/esquinas para redimensionar. "
            "Flechas = nudge, Supr = borrar.  Viñetas: tildá «Mover rótulos…» y "
            "arrastralas (con «Imantar» se enganchan al ancla más cercana). "
            "Textos: «Agregar texto» y arrastralos por el lienzo.")
        self.status.setWordWrap(True)
        self.status.setStyleSheet("color:#555; font-size:11px;")
        outer.addWidget(self.status)

    def _dspin(self, lo=0.0, hi=1.0, step=0.01, dec=3):
        sp = self.QtWidgets.QDoubleSpinBox()
        sp.setRange(lo, hi); sp.setSingleStep(step); sp.setDecimals(dec)
        sp.setKeyboardTracking(False)
        return sp

    # ── handlers ──────────────────────────────────────────────────────────────
    def _on_add(self):
        QtWidgets = self.QtWidgets
        exts = " ".join("*" + e for e in sorted(
            set(_RASTER_EXTS) | set(_VECTOR_EXTS) | {".json", ".csv"}))
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self.win, "Elegí una o más figuras", "",
            f"Figuras ({exts});;Todos (*.*)")
        if files:
            self.asm.add_sources(files)
            self.status.setText(f"Agregadas {len(files)} figura(s).")

    def _on_list_select(self, row):
        if self._syncing:
            return
        if 0 <= row < len(self.asm.panels):
            self.asm.selected = row
            self.asm.selected_text = None
            self.asm._refresh_overlay(); self.asm._draw()
            self._sync_rect_fields()

    # ── textos libres ──────────────────────────────────────────────────────────
    def _on_text_add(self):
        # color/fuente actuales del panel como defaults del nuevo texto
        fam = self.cmb_family.currentFont().family() if hasattr(self, "cmb_family") else None
        self.asm.add_text("Texto", xy=(0.5, 0.5), fontfamily=fam,
                          fontsize=float(self.sp_tfs.value()),
                          bold=self.chk_tbold.isChecked(),
                          italic=self.chk_tital.isChecked(),
                          color=self._text_color)
        self.status.setText("Texto agregado: arrastralo por el lienzo para ubicarlo.")

    def _on_text_list_select(self, row):
        if self._syncing:
            return
        if 0 <= row < len(self.asm.texts):
            self.asm.selected_text = row
            self.asm.selected = None
            self.asm._refresh_overlay(); self.asm._draw()
            self._sync_text_fields()

    def _on_text_props(self, *_):
        if self._syncing:
            return
        if self.asm._sel_text() is None:
            return
        fam = self.cmb_family.currentFont().family()
        self.asm.update_selected_text(
            text=self.ed_txt.text(), fontfamily=fam,
            fontsize=float(self.sp_tfs.value()),
            bold=self.chk_tbold.isChecked(),
            italic=self.chk_tital.isChecked(),
            color=self._text_color)
        self._sync_text_list_only()

    def _on_text_color(self):
        QtWidgets, QtGui = self.QtWidgets, self.QtGui
        init = QtGui.QColor(self._text_color)
        col = QtWidgets.QColorDialog.getColor(init, self.win, "Color del texto")
        if col.isValid():
            self._text_color = col.name()
            self.lbl_tswatch.setStyleSheet(
                f"background:{self._text_color}; border:1px solid #888;")
            self._on_text_props()

    def _on_apply_layout(self):
        key = self.cmb_layout.currentData()
        if key:
            self.asm.apply_layout_name(key)
            self.status.setText(f"Grilla aplicada: {key}")

    def _on_rect_edit(self, *_):
        if self._syncing:
            return
        self.asm.set_rect((self.sp_x.value(), self.sp_y.value(),
                           self.sp_w.value(), self.sp_h.value()))

    def _on_align(self, _idx):
        key = self.cmb_align.currentData()
        if key:
            self.asm.align(key)
        self.cmb_align.setCurrentIndex(0)

    def _on_equalize(self, _idx):
        key = self.cmb_eq.currentData()
        if key:
            self.asm.equalize(key)
        self.cmb_eq.setCurrentIndex(0)

    def _on_distribute(self, _idx):
        key = self.cmb_dist.currentData()
        if key:
            self.asm.distribute(key)
        self.cmb_dist.setCurrentIndex(0)

    def _on_font_scale(self, val):
        if self._syncing:
            return
        self.asm.set_font_scale(float(val))

    def _on_labels(self, *_):
        style = self.cmb_labstyle.currentData()
        pos = self.cmb_labpos.currentData() or "outside_top_left"
        if style is None:
            self.asm.set_label_spec({"enabled": False})
            return
        kind, wrap = style
        self.asm.set_label_spec({"enabled": True, "kind": kind, "wrap": wrap,
                                 "position": pos, "fontsize": self.sp_lfs.value(),
                                 "fontweight": "bold", "color": "black"})

    def _on_label_xy(self, *_):
        if self._syncing:
            return
        self.asm.set_label_custom_xy(self.sp_lx.value(), self.sp_ly.value())

    def _on_save(self):
        QtWidgets = self.QtWidgets
        base, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.win, "Nombre base de salida", self.asm.base_filename,
            "Base (*)")
        if not base:
            return
        try:
            saved = self.asm.save(base)
            self.status.setText("Guardado: " + ", ".join(Path(s).name for s in saved))
        except Exception as e:
            self.status.setText(f"⚠ Error al guardar: {e}")

    def _on_save_recipe(self):
        QtWidgets = self.QtWidgets
        base, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.win, "Receta del ensamble libre", self.asm.base_filename,
            "JSON (*.free.json)")
        if not base:
            return
        try:
            p = self.asm.save_recipe(base)
            self.status.setText(f"Receta guardada: {Path(p).name}")
        except Exception as e:
            self.status.setText(f"⚠ {e}")

    # ── sincronización asm -> UI ───────────────────────────────────────────────
    def _sync_from_asm(self, asm):
        self._syncing = True
        try:
            cur = self.lst.currentRow()
            self.lst.clear()
            for i, p in enumerate(asm.panels):
                name = Path(p.source).name or p.source
                self.lst.addItem(f"{i+1}. {name}  [{p.kind or '?'}]")
            if asm.selected is not None and 0 <= asm.selected < self.lst.count():
                self.lst.setCurrentRow(asm.selected)
            elif 0 <= cur < self.lst.count():
                self.lst.setCurrentRow(cur)
            self._sync_rect_fields()
        finally:
            self._syncing = False
        self._sync_text_list()
        self._sync_text_fields()

    def _sync_text_list_only(self):
        """Actualiza solo las etiquetas de la lista de textos (sin tocar campos)."""
        self._syncing = True
        try:
            sel = self.asm.selected_text
            self.lst_txt.clear()
            for i, ft in enumerate(self.asm.texts):
                preview = (ft.text or "").replace("\n", " ")
                if len(preview) > 24:
                    preview = preview[:24] + "…"
                self.lst_txt.addItem(f"{i+1}. {preview or '(vacío)'}")
            if sel is not None and 0 <= sel < self.lst_txt.count():
                self.lst_txt.setCurrentRow(sel)
        finally:
            self._syncing = False

    def _sync_text_list(self):
        self._sync_text_list_only()

    def _sync_text_fields(self):
        """Carga los campos de texto desde el FreeText seleccionado."""
        self._syncing = True
        try:
            ft = self.asm._sel_text()
            enabled = ft is not None
            for w in (self.ed_txt, self.cmb_family, self.sp_tfs,
                      self.chk_tbold, self.chk_tital, self.btn_tcolor):
                w.setEnabled(enabled)
            if ft is not None:
                self.ed_txt.setText(ft.text)
                if ft.fontfamily:
                    try:
                        self.cmb_family.setCurrentFont(self.QtGui.QFont(ft.fontfamily))
                    except Exception:
                        pass
                self.sp_tfs.setValue(float(ft.fontsize))
                self.chk_tbold.setChecked(bool(ft.bold))
                self.chk_tital.setChecked(bool(ft.italic))
                self._text_color = self._color_to_hex(ft.color)
                self.lbl_tswatch.setStyleSheet(
                    f"background:{self._text_color}; border:1px solid #888;")
        finally:
            self._syncing = False

    def _color_to_hex(self, color):
        """Normaliza un color matplotlib/str a '#rrggbb' para el swatch/diálogo."""
        try:
            import matplotlib.colors as mcolors
            r, g, b, _a = mcolors.to_rgba(color)
            return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))
        except Exception:
            return "#000000"

    def _sync_rect_fields(self):
        self._syncing = True
        try:
            p = self.asm._sel_panel()
            enabled = p is not None
            for sp in (self.sp_x, self.sp_y, self.sp_w, self.sp_h):
                sp.setEnabled(enabled)
            self.chk_aspect.setEnabled(enabled and (p.is_image() if p else False))
            labels_on = bool(self.asm.label_spec
                             and self.asm.label_spec.get("enabled", True))
            self.sp_lx.setEnabled(enabled and labels_on)
            self.sp_ly.setEnabled(enabled and labels_on)
            if p is not None:
                l, b, w, h = p.rect
                self.sp_x.setValue(l); self.sp_y.setValue(b)
                self.sp_w.setValue(w); self.sp_h.setValue(h)
                self.chk_aspect.setChecked(p.keep_aspect)
                # coords del rótulo: la personalizada si existe, si no la global
                if p.label_custom_xy is not None:
                    lx, ly = p.label_custom_xy
                else:
                    pos_key = (self.asm.label_spec or {}).get(
                        "position", "outside_top_left")
                    lx, ly = _LABEL_POS.get(pos_key, _LABEL_POS["outside_top_left"])[:2]
                self.sp_lx.setValue(float(lx)); self.sp_ly.setValue(float(ly))
        finally:
            self._syncing = False

    def show(self):
        self.win.show()
        try:
            self.win.raise_()
            self.win.activateWindow()
        except Exception:
            pass


# ═════════════════════════════════════════════════════════════════════════════
#  Fallback con matplotlib.widgets (cuando no hay Qt pero sí backend interactivo)
# ═════════════════════════════════════════════════════════════════════════════
def _attach_mpl_toolbar(asm: FreeCanvasAssembler):
    from matplotlib.widgets import Button, CheckButtons
    ctrl = plt.figure(figsize=(3.0, 3.9))
    try:
        ctrl.canvas.manager.set_window_title("Ensamble libre — control (mpl)")
    except Exception:
        pass

    def _ax(y, h=0.085, x=0.06, w=0.88):
        return ctrl.add_axes([x, y, w, h])

    b_add = Button(_ax(0.88), "Agregar (consola)…")
    b_del = Button(_ax(0.78), "Quitar seleccionada")
    b_grid = Button(_ax(0.68), "Grilla 2×2")
    b_text = Button(_ax(0.58), "Agregar texto")
    b_save = Button(_ax(0.48), "Guardar (consola)…")
    chk = CheckButtons(_ax(0.16, 0.24), ["snapping", "grilla guía"],
                       [asm.snapping, asm.show_grid])

    def _add(_):
        try:
            s = input("Ruta o raíz de la figura a agregar: ").strip().strip('"')
        except Exception:
            s = ""
        if s:
            asm.add_source(s)

    def _save(_):
        try:
            base = input("Nombre base de salida: ").strip().strip('"')
        except Exception:
            base = ""
        if base:
            asm.save(base)

    def _toggle(label):
        if label == "snapping":
            asm.snapping = not asm.snapping
        else:
            asm.set_show_grid(not asm.show_grid)

    b_add.on_clicked(_add)
    b_del.on_clicked(lambda _: asm.remove_selected())
    b_grid.on_clicked(lambda _: asm.apply_grid_preset(2, 2))
    b_text.on_clicked(lambda _: asm.add_text("Texto", xy=(0.5, 0.5)))
    b_save.on_clicked(_save)
    chk.on_clicked(_toggle)
    ctrl._pa_widgets = [b_add, b_del, b_grid, b_text, b_save, chk]
    try:
        ctrl.show()
    except Exception:
        pass
    return ctrl


# ═════════════════════════════════════════════════════════════════════════════
#  Punto de entrada
# ═════════════════════════════════════════════════════════════════════════════
_OPEN = []  # evita que el GC se lleve panel/lienzo


def _backend_is_interactive() -> bool:
    # OJO: comparar por MEMBRESÍA EXACTA, no por endswith("agg"):
    # los backends interactivos modernos se llaman QtAgg / Qt5Agg / TkAgg, que
    # también terminan en "agg". Sólo 'agg' a secas es headless.
    try:
        b = str(plt.get_backend()).lower()
        return b not in ("agg", "pdf", "ps", "svg", "cairo", "template", "")
    except Exception:
        return False


def launch_free_assembler(sources=None, *, figsize=(8.0, 6.0), dpi=150,
                          base_filename="figura_compuesta", snapping=True,
                          show_grid=False, font_scale=0.9,
                          backend=None, editor=None):
    """Abre el ensamblador gráfico de lienzo libre.

    En Spyder requiere backend interactivo: ejecutá antes `%matplotlib qt`.
    Devuelve el FreeCanvasAssembler (mantené la referencia).

    backend / editor: opcionales, para forzar el motor de render/guardado y/o el
    editor a usar (por defecto se resuelven automáticamente: assembler v5/v4,
    editor v5/v4/v3). Ver configure_backend() y backend_info().
    """
    if backend is not None or editor is not None:
        configure_backend(backend=backend, editor=editor)
    print("[v8] " + backend_info())
    if not _backend_is_interactive():
        print("[v8] El modo gráfico requiere backend interactivo. En Spyder: "
              "%matplotlib qt   (o %matplotlib tk). Detecté backend no "
              f"interactivo: {plt.get_backend()}.")
        print("     Igual creo el assembler para uso programático/headless "
              "(add_source/apply_grid_preset/save).")
    asm = FreeCanvasAssembler(figsize=figsize, dpi=dpi, snapping=snapping,
                              show_grid=show_grid, font_scale=font_scale,
                              base_filename=base_filename)
    if sources:
        asm.add_sources(list(sources))
    asm.show()
    _OPEN.append(asm)

    if _backend_is_interactive():
        panel = None
        if _qt() is not None:
            try:
                panel = _AssemblerControlPanel(asm)
                panel.show()
                print("[v8] Listo: lienzo + panel de control Qt abiertos "
                      "(pueden estar DETRÁS de Spyder; usá Alt+Tab).")
            except Exception:
                import traceback
                print("[v8] No pude abrir el panel Qt; traceback completo "
                      "(pasámelo si querés que lo corrija):")
                traceback.print_exc()
                panel = None
        if panel is None:
            print("[v8] Uso la barra de control mínima de matplotlib.")
            panel = _attach_mpl_toolbar(asm)
        _OPEN.append(panel)
        if not matplotlib.is_interactive():
            try:
                plt.show()
            except Exception:
                pass
    return asm


def main():
    print("═" * 72)
    print("  ENSAMBLADOR GRÁFICO DE FIGURAS (v8) — lienzo libre + panel Qt")
    print("═" * 72)
    if not _backend_is_interactive():
        print("  Backend NO interactivo. En Spyder ejecutá:  %matplotlib qt")
    return launch_free_assembler()


__all__ = [
    "FreeCanvasAssembler", "FreePanel", "FreeText", "launch_free_assembler",
    "main", "configure_backend", "backend_info",
    # geometría pura (testeable)
    "hit_test_rect", "resize_rect", "snap_value", "snap_rect_to_grid",
    "snap_rect_to_edges", "grid_rects", "normalize_rect", "clamp01",
    "reading_order_indices", "snap_label_to_anchor",
]

if __name__ == "__main__":
    main()

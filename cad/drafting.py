"""2D drafting from the CadQuery model: hidden-line projections, sheet layout, dimensions,
title block, hole tables, balloons. Output is SVG in millimetres (A3 landscape).

Projection uses OpenCascade's exact hidden-line removal (HLRBRep), so visible edges are
solid and hidden edges dashed, as on a hand-made drawing. Several shapes can be projected
together; each keeps its own visible/hidden edge sets so a caller can style them apart
(the assembly guide draws new parts black and existing parts grey).
"""
from datetime import date
from math import atan2, cos, hypot, pi, sin, sqrt

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape

SHEET_W, SHEET_H = 420.0, 297.0
FONT = "DejaVu Sans, Liberation Sans, Arial, sans-serif"
INK = "#111"
THIN, MED, THICK = 0.18, 0.35, 0.5

# view name -> (direction towards the viewer, 2D x axis)
VIEWS = {
    "front": ((0, -1, 0), (1, 0, 0)),
    "top": ((0, 0, 1), (1, 0, 0)),
    "right": ((1, 0, 0), (0, 1, 0)),
    "left": ((-1, 0, 0), (0, -1, 0)),
    "back": ((0, 1, 0), (-1, 0, 0)),
    "iso": ((1, -1, 1), (1, 1, 0)),
    "iso_back": ((-1, 1, 1), (-1, -1, 0)),
    "iso_left": ((-1, -1, 1), (1, -1, 0)),
}


def _norm(v):
    n = sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


def _solids(w):
    if isinstance(w, cq.Workplane):
        return [s for s in w.vals() if isinstance(s, cq.Shape)]
    return [w]


# ------------------------------------------------------------------ projection
def _edges_to_polylines(compound, tol=0.25):
    if compound is None or compound.IsNull():
        return []
    out = []
    for e in cq.Shape.cast(compound).Edges():
        try:
            if e.geomType() == "LINE":
                a, b = e.startPoint(), e.endPoint()
                out.append([(a.x, a.y), (b.x, b.y)])
            else:
                n = max(6, min(200, int(e.Length() / tol / 4) + 6))
                pts = [e.positionAt(i / (n - 1)) for i in range(n)]
                out.append([(p.x, p.y) for p in pts])
        except Exception:
            continue
    return out


def project(shapes, view, with_hidden=True):
    """shapes: list of cq shapes/workplanes (one entry per 'part'). Returns a list of
    {'visible': [polyline], 'hidden': [polyline]} in the same order, in view coordinates (mm)."""
    d, x = VIEWS[view] if isinstance(view, str) else view
    algo = HLRBRep_Algo()
    tops = []
    for s in shapes:
        sol = _solids(s)
        comp = cq.Compound.makeCompound(sol).wrapped if len(sol) > 1 else sol[0].wrapped
        tops.append(comp)
        algo.Add(comp)
    algo.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*_norm(d)), gp_Dir(*_norm(x)))))
    algo.Update()
    algo.Hide()
    h = HLRBRep_HLRToShape(algo)
    res = []
    for t in tops:
        vis = _edges_to_polylines(h.VCompound(t)) + _edges_to_polylines(h.OutLineVCompound(t))
        hid = (_edges_to_polylines(h.HCompound(t)) + _edges_to_polylines(h.OutLineHCompound(t))) if with_hidden else []
        res.append({"visible": vis, "hidden": hid})
    return res


def bounds(polys):
    xs = [p[0] for pl in polys for p in pl]
    ys = [p[1] for pl in polys for p in pl]
    if not xs:
        return (0, 0, 1, 1)
    return min(xs), min(ys), max(xs), max(ys)


def point_2d(p, view):
    """Project a 3D point the same way as project() (orthographic)."""
    d, x = VIEWS[view] if isinstance(view, str) else view
    n, xa = _norm(d), _norm(x)
    ya = (n[1] * xa[2] - n[2] * xa[1], n[2] * xa[0] - n[0] * xa[2], n[0] * xa[1] - n[1] * xa[0])
    return (sum(a * b for a, b in zip(p, xa)), sum(a * b for a, b in zip(p, ya)))


# ------------------------------------------------------------------ SVG primitives
def _f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def polyline_svg(polys, tx, stroke=INK, width=MED, dash=None, opacity=1.0):
    """tx: function (x, y) -> (X, Y) on the sheet."""
    if not polys:
        return ""
    parts = []
    for pl in polys:
        pts = [tx(*p) for p in pl]
        parts.append("M" + " L".join(f"{_f(a)} {_f(b)}" for a, b in pts))
    da = f' stroke-dasharray="{dash}"' if dash else ""
    op = f' stroke-opacity="{opacity}"' if opacity < 1 else ""
    return (f'<path d="{" ".join(parts)}" fill="none" stroke="{stroke}" stroke-width="{width}"'
            f' stroke-linecap="round" stroke-linejoin="round"{da}{op}/>')


def text(x, y, s, size=3.5, anchor="middle", weight="normal", rotate=0, fill=INK, italic=False):
    rot = f' transform="rotate({_f(rotate)} {_f(x)} {_f(y)})"' if rotate else ""
    st = ' font-style="italic"' if italic else ""
    s = str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (f'<text x="{_f(x)}" y="{_f(y)}" font-family="{FONT}" font-size="{_f(size)}" text-anchor="{anchor}"'
            f' font-weight="{weight}" fill="{fill}"{st}{rot}>{s}</text>')


def line(x1, y1, x2, y2, w=THIN, stroke=INK, dash=None):
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{_f(x1)}" y1="{_f(y1)}" x2="{_f(x2)}" y2="{_f(y2)}" stroke="{stroke}" stroke-width="{w}"{da}/>'


def rect(x, y, w, h, sw=THIN, fill="none", stroke=INK, rx=0):
    return (f'<rect x="{_f(x)}" y="{_f(y)}" width="{_f(w)}" height="{_f(h)}" fill="{fill}" stroke="{stroke}"'
            f' stroke-width="{sw}" rx="{_f(rx)}"/>')


def arrow_head(x, y, ang, size=2.2, fill=INK):
    a1, a2 = ang + pi - 0.3, ang + pi + 0.3
    return (f'<path d="M{_f(x)} {_f(y)} L{_f(x + size * cos(a1))} {_f(y + size * sin(a1))} '
            f'L{_f(x + size * cos(a2))} {_f(y + size * sin(a2))} Z" fill="{fill}"/>')


def dim_linear(x1, y1, x2, y2, offset, label=None, size=3.0):
    """Aligned dimension between two sheet points, dimension line offset to the left of p1->p2."""
    L = hypot(x2 - x1, y2 - y1)
    if L < 1e-6:
        return ""
    ux, uy = (x2 - x1) / L, (y2 - y1) / L
    nx, ny = -uy, ux
    a = (x1 + nx * offset, y1 + ny * offset)
    b = (x2 + nx * offset, y2 + ny * offset)
    sgn = 1 if offset > 0 else -1
    out = [line(x1 + nx * sgn * 1.0, y1 + ny * sgn * 1.0, a[0] + nx * sgn * 1.5, a[1] + ny * sgn * 1.5),
           line(x2 + nx * sgn * 1.0, y2 + ny * sgn * 1.0, b[0] + nx * sgn * 1.5, b[1] + ny * sgn * 1.5),
           line(*a, *b)]
    ang = atan2(b[1] - a[1], b[0] - a[0])
    out += [arrow_head(*b, ang), arrow_head(*a, ang + pi)]
    deg = ang * 180 / pi
    if deg > 90.5 or deg <= -89.5:          # keep text readable from the bottom or the right
        deg -= 180 if deg > 0 else -180
    if abs(deg - 90) < 0.5:
        deg = -90
    r = deg * pi / 180
    up = (sin(r), -cos(r))                   # text "up" direction on the sheet
    mx, my = (a[0] + b[0]) / 2 + up[0] * 1.0, (a[1] + b[1]) / 2 + up[1] * 1.0
    out.append(text(mx, my, label if label is not None else _f(round(L, 1)), size=size, rotate=deg))
    return "".join(out)


def balloon(x, y, tx, ty, label, r=4.0):
    ang = atan2(y - ty, x - tx)
    return (line(tx, ty, x - r * cos(ang), y - r * sin(ang), w=THIN) + f'<circle cx="{_f(tx)}" cy="{_f(ty)}" r="0.7" fill="{INK}"/>'
            + f'<circle cx="{_f(x)}" cy="{_f(y)}" r="{_f(r)}" fill="#fff" stroke="{INK}" stroke-width="{MED}"/>'
            + text(x, y + 1.3, label, size=3.6, weight="bold"))


# ------------------------------------------------------------------ sheet furniture
def frame(sheet_no, total, title, subtitle, part_no, scale_label, material="", qty="", notes=()):
    m = 10.0
    out = [rect(0, 0, SHEET_W, SHEET_H, sw=0, fill="#fff", stroke="none"),
           rect(m, m, SHEET_W - 2 * m, SHEET_H - 2 * m, sw=0.7)]
    # zone markers
    cols, rows = 8, 6
    for i in range(cols):
        x0 = m + i * (SHEET_W - 2 * m) / cols
        if i:
            out.append(line(x0, 5, x0, m) + line(x0, SHEET_H - m, x0, SHEET_H - 5))
        out.append(text(x0 + (SHEET_W - 2 * m) / cols / 2, 8.6, i + 1, size=3) +
                   text(x0 + (SHEET_W - 2 * m) / cols / 2, SHEET_H - 6.2, i + 1, size=3))
    for j in range(rows):
        y0 = m + j * (SHEET_H - 2 * m) / rows
        if j:
            out.append(line(5, y0, m, y0) + line(SHEET_W - m, y0, SHEET_W - 5, y0))
        L = "ABCDEF"[j]
        out.append(text(7.5, y0 + (SHEET_H - 2 * m) / rows / 2 + 1, L, size=3) +
                   text(SHEET_W - 7.5, y0 + (SHEET_H - 2 * m) / rows / 2 + 1, L, size=3))
    # title block (bottom right)
    tw, th = 180.0, 36.0
    x0, y0 = SHEET_W - m - tw, SHEET_H - m - th
    out.append(rect(x0, y0, tw, th, sw=0.5))
    out.append(line(x0, y0 + 14, x0 + tw, y0 + 14, w=0.35))
    out.append(line(x0 + 120, y0 + 14, x0 + 120, y0 + th, w=0.35))
    out.append(line(x0, y0 + 25, x0 + 120, y0 + 25, w=THIN))
    for xx in (40, 80):
        out.append(line(x0 + xx, y0 + 25, x0 + xx, y0 + th, w=THIN))
    out.append(text(x0 + 3, y0 + 6.5, title, size=5.2, anchor="start", weight="bold"))
    out.append(text(x0 + 3, y0 + 11.6, subtitle, size=3.0, anchor="start"))
    out.append(text(x0 + 3, y0 + 18.5, f"PART / DWG No.  {part_no}", size=3.0, anchor="start"))
    out.append(text(x0 + 3, y0 + 23, f"MATERIAL  {material}", size=2.8, anchor="start"))
    for i, (k, v) in enumerate((("SCALE", scale_label), ("QTY", qty or "-"), ("UNITS", "mm"))):
        out.append(text(x0 + 3 + 40 * i, y0 + 28.5, k, size=2.2, anchor="start", fill="#555"))
        out.append(text(x0 + 3 + 40 * i, y0 + 33.6, v, size=3.4, anchor="start", weight="bold"))
    out.append(text(x0 + 150, y0 + 19, "CHESS ROBOT ARM", size=3.2, weight="bold"))
    out.append(text(x0 + 150, y0 + 24.5, f"SHEET {sheet_no} / {total}", size=3.0))
    out.append(text(x0 + 150, y0 + 30, date.today().isoformat(), size=2.6, fill="#555"))
    out.append(_third_angle_symbol(x0 + 140, y0 + 5))
    out.append(text(m + 4, m + 7, "ALL DIMENSIONS IN MM", size=3.2, anchor="start", weight="bold", italic=True))
    out.append(text(m + 4, m + 12, "THIRD-ANGLE PROJECTION · GENERATED FROM cad/ (CadQuery)", size=2.4,
                    anchor="start", fill="#555"))
    for i, n in enumerate(notes):
        out.append(text(m + 4, SHEET_H - m - 4 - 4.2 * (len(notes) - 1 - i), n, size=2.7, anchor="start"))
    return "".join(out)


def _third_angle_symbol(x, y):
    # cone frustum side view + circles (third angle)
    return (f'<path d="M{_f(x)} {_f(y + 1)} L{_f(x + 9)} {_f(y - 1.5)} L{_f(x + 9)} {_f(y + 5.5)} L{_f(x)} {_f(y + 3)} Z"'
            f' fill="none" stroke="{INK}" stroke-width="0.3"/>'
            f'<circle cx="{_f(x + 16)}" cy="{_f(y + 2)}" r="3.5" fill="none" stroke="{INK}" stroke-width="0.3"/>'
            f'<circle cx="{_f(x + 16)}" cy="{_f(y + 2)}" r="1.6" fill="none" stroke="{INK}" stroke-width="0.3"/>')


def table(x, y, headers, rows, widths, size=2.6, row_h=4.6):
    out = []
    total_w = sum(widths)
    out.append(rect(x, y, total_w, row_h * (len(rows) + 1), sw=0.35))
    out.append(rect(x, y, total_w, row_h, sw=0.35, fill="#eee"))
    cx = x
    for h, w in zip(headers, widths):
        out.append(text(cx + 1.5, y + row_h - 1.3, h, size=size, anchor="start", weight="bold"))
        cx += w
    for i, r in enumerate(rows):
        yy = y + row_h * (i + 2) - 1.3
        out.append(line(x, y + row_h * (i + 1), x + total_w, y + row_h * (i + 1), w=0.12))
        cx = x
        for v, w in zip(r, widths):
            out.append(text(cx + 1.5, yy, v, size=size, anchor="start"))
            cx += w
    cx = x
    for w in widths[:-1]:
        cx += w
        out.append(line(cx, y, cx, y + row_h * (len(rows) + 1), w=0.12))
    return "".join(out), row_h * (len(rows) + 1)


def svg_doc(body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{SHEET_W}mm" height="{SHEET_H}mm" '
            f'viewBox="0 0 {SHEET_W} {SHEET_H}">{body}</svg>')


# ------------------------------------------------------------------ analysis helpers
def hole_table(shape, min_d=1.5, max_d=80):
    """Group cylindrical holes (material outside the cylinder) by diameter and axis."""
    sol = _solids(shape)
    comp = cq.Compound.makeCompound(sol)
    seen = {}
    for f in comp.Faces():
        ad = BRepAdaptor_Surface(f.wrapped)
        if ad.GetType() != GeomAbs_Cylinder:
            continue
        cyl = ad.Cylinder()
        r = cyl.Radius()
        d = 2 * r
        if not (min_d <= d <= max_d):
            continue
        ax = cyl.Axis()
        dv = ax.Direction()
        axis = max((("X", abs(dv.X())), ("Y", abs(dv.Y())), ("Z", abs(dv.Z()))), key=lambda t: t[1])
        if axis[1] < 0.99:
            continue
        loc = ax.Location()
        # point on the surface, nudged towards the axis: inside material -> boss, outside -> hole
        c = f.Center()
        try:
            mid = f.positionAt(0.5, 0.5)
        except Exception:
            mid = c
        lp = (loc.X(), loc.Y(), loc.Z())
        a = axis[0]
        idx = "XYZ".index(a)
        foot = list(lp)
        foot[idx] = (mid.x, mid.y, mid.z)[idx]
        v = (mid.x - foot[0], mid.y - foot[1], mid.z - foot[2])
        vl = sqrt(sum(t * t for t in v)) or 1
        probe = cq.Vector(mid.x - v[0] / vl * 0.3, mid.y - v[1] / vl * 0.3, mid.z - v[2] / vl * 0.3)
        inside = any(s.isInside(probe, 0.01) for s in sol if hasattr(s, "isInside"))
        if inside:
            continue
        key_pos = tuple(round(lp[i], 1) for i in range(3) if i != idx)
        key = (round(d, 2), a, key_pos)
        seen[key] = True
    groups = {}
    for (d, a, _pos) in seen:
        groups[(d, a)] = groups.get((d, a), 0) + 1
    return sorted(((d, a, n) for (d, a), n in groups.items()), key=lambda t: (-t[0], t[1]))


STD_SCALES = [(5, "5:1"), (4, "4:1"), (2, "2:1"), (1.5, "3:2"), (1, "1:1"), (2 / 3, "2:3"), (0.5, "1:2"),
              (0.4, "1:2.5"), (1 / 3, "1:3"), (0.25, "1:4"), (0.2, "1:5"), (0.1, "1:10"), (0.05, "1:20")]


def pick_scale(need_w, need_h, avail_w, avail_h):
    for s, lab in STD_SCALES:
        if need_w * s <= avail_w and need_h * s <= avail_h:
            return s, lab
    return STD_SCALES[-1]


def orient_for_drawing(w):
    """Rotate a part (axis permutations only) so its largest extent is X, the next Z, the smallest Y,
    and move its bounding box to start at the origin. Returns the new Workplane."""
    bb = cq.Compound.makeCompound(_solids(w)).BoundingBox()
    dims = {"x": bb.xlen, "y": bb.ylen, "z": bb.zlen}
    order = sorted(dims, key=lambda k: -dims[k])          # largest first
    target = {order[0]: "x", order[1]: "z", order[2]: "y"}
    # build a permutation by successive 90 deg rotations
    def rot(wp, axis, deg):
        v = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[axis]
        return wp.rotate((0, 0, 0), v, deg)
    perm = (target["x"], target["y"], target["z"])           # where current x, y, z go
    seq = {("x", "y", "z"): [], ("x", "z", "y"): [("x", 90)], ("y", "x", "z"): [("z", 90)],
           ("z", "y", "x"): [("y", 90)], ("y", "z", "x"): [("x", 90), ("z", 90)], ("z", "x", "y"): [("z", 90), ("x", 90)]}
    for ax, deg in seq[perm]:
        w = rot(w, ax, deg)
    bb = cq.Compound.makeCompound(_solids(w)).BoundingBox()
    return w.translate((-bb.xmin, -bb.ymin, -bb.zmin))

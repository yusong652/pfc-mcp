import itasca as it

# ---------------------------------------------------------------- build
it.command("model new")
it.command("model large-strain on")
it.command("model domain extent -10 10 -16 16")
# expand -> each wall lengthened so the four sides overlap at corners (no leak)
it.command("wall generate id 1 name 'vessel' box -5 5 -10 10 expand 1.3")
it.command("contact cmat default model linear property kn 1.0e8 ks 5.0e7 fric 0.0 dp_nratio 0.5")
it.command("ball distribute porosity 0.16 radius 0.18 0.28 box -5 5 -10 10")
it.command("ball attribute density 1000.0 damp 0.8")

# classify the four box walls by centroid
walls = {}
for w in it.wall.list():
    p = w.pos(); walls[w.id()] = (p.x(), p.y())
def pick(axis, sign):
    best = None
    for wid, (x, y) in walls.items():
        v = x if axis == 'x' else y
        if best is None or (sign > 0 and v > best[1]) or (sign < 0 and v < best[1]):
            best = (wid, v)
    return best[0]
WL, WR, WB, WT = pick('x', -1), pick('x', 1), pick('y', -1), pick('y', 1)
W0, H0, SIG = 10.0, 20.0, 1.0e5

def wf(wid): return it.wall.find(wid).force_contact()
def maxv():  return max((b.vel().mag() for b in it.ball.list()), default=0.0)
def height(): return it.wall.find(WT).pos().y() - it.wall.find(WB).pos().y()
def width():  return it.wall.find(WR).pos().x() - it.wall.find(WL).pos().x()

import json, os
try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:        # __file__ may be unset when exec'd inside the bridge
    HERE = os.getcwd()
DATA = os.path.join(HERE, "data")
if not os.path.isdir(DATA):
    os.makedirs(DATA)
def export(fname, note):
    balls = [{"x": b.pos().x(), "y": b.pos().y(), "r": b.radius(),
              "vx": b.vel().x(), "vy": b.vel().y()} for b in it.ball.list()]
    contacts = []
    for c in it.contact.list():
        if type(c).__name__ != "BallBallContact" or not c.active():
            continue
        fg = c.force_global(); n = c.normal()
        fn = abs(fg.x() * n.x() + fg.y() * n.y())
        if fn <= 0.0:
            continue
        e1, e2 = c.end1(), c.end2()
        contacts.append({"x1": e1.pos().x(), "y1": e1.pos().y(),
                         "x2": e2.pos().x(), "y2": e2.pos().y(),
                         "fn": fn, "fmag": fg.mag()})
    fns = [c["fn"] for c in contacts]
    vmax = max((b["vx"] ** 2 + b["vy"] ** 2) ** 0.5 for b in balls)
    json.dump({"engine": "PFC2D 7.0", "note": note,
               "n_balls": len(balls), "n_contacts": len(contacts),
               "fn_max": max(fns), "fn_mean": sum(fns) / len(fns), "v_max": vmax,
               "balls": balls, "contacts": contacts},
              open(os.path.join(DATA, fname), "w"))
    print("exported %s  balls=%d contacts=%d fn_max=%.3e v_max=%.4f"
          % (fname, len(balls), len(contacts), max(fns), vmax))

# ---------------------------------------------------------------- consolidate
print("=== STAGE 1: isotropic consolidation (gain 0.3) ===")
Flr, Ftb = SIG * H0, SIG * W0
it.command("wall servo force (%g,0) activate on range id %d" % (Flr, WL))
it.command("wall servo force (%g,0) activate on range id %d" % (-Flr, WR))
it.command("wall servo force (0,%g) activate on range id %d" % (Ftb, WB))
it.command("wall servo force (0,%g) activate on range id %d" % (-Ftb, WT))
it.command("wall servo gain-factor 0.3")
it.command("wall servo velocity-max 1.0")
for k in range(80):
    it.command("model cycle 500")
    v = maxv()
    if k % 5 == 0:
        print("  consol k=%2d cyc=%d maxvel=%.4f H=%.3f W=%.3f" % (k, it.cycle(), v, height(), width()))
    if v < 0.08:
        print("  -> quiet after %d cycles, maxvel=%.4f" % (it.cycle(), v)); break

# ---------------------------------------------------------------- shear
print("=== STAGE 2: slow biaxial shear (fric=0.5, VAX=0.1) ===")
it.command("contact property fric 0.5")
it.command("wall servo activate off range id %d" % WB)
it.command("wall servo activate off range id %d" % WT)
VAX = 0.1
it.command("wall attribute velocity (0,%g) range id %d" % (VAX, WB))
it.command("wall attribute velocity (0,%g) range id %d" % (-VAX, WT))
H_start, TARGET_EPS, peak = height(), 0.035, 0.0
for k in range(400):
    it.command("model cycle 200")
    eps = (H_start - height()) / H_start
    q = abs(wf(WT).y()) / width() - abs(wf(WR).x()) / height()
    peak = max(peak, q)
    if k % 10 == 0 or eps >= TARGET_EPS:
        print("  shear k=%2d eps=%.4f q=%.3e maxvel=%.4f" % (k, eps, q, maxv()))
    if eps >= TARGET_EPS:
        print("  -> mid-shear eps=%.4f (peak q=%.3e)" % (eps, peak)); break

# snapshot WITH live velocity field (shear band kinematics) before quieting
export("pfc_biaxial_shear.json", "active mid-shear eps~0.035, live velocity field")

# ---------------------------------------------------------------- relax (quiet snapshot)
print("=== STAGE 3: relax to a quiet state (platens stopped, confinement held) ===")
it.command("wall attribute velocity (0,0) range id %d" % WB)
it.command("wall attribute velocity (0,0) range id %d" % WT)
for k in range(60):
    it.command("model cycle 500")
    v = maxv()
    if k % 5 == 0:
        print("  relax k=%2d cyc=%d maxvel=%.5f" % (k, it.cycle(), v))
    if v < 0.02:
        print("  -> relaxed, maxvel=%.5f" % v); break

export("pfc_biaxial_relaxed.json", "relaxed mid-shear eps~0.035, clean force chains")
it.command("model save 'biaxial_midshear'")
print("=== DONE balls=%d contacts=%d eps=%.4f maxvel=%.5f ==="
      % (it.ball.count(), it.contact.count(), (H_start - height()) / H_start, maxv()))

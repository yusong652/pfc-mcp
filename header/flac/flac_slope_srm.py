import itasca as it
import math, json, os

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:        # __file__ may be unset when exec'd inside the bridge
    HERE = os.getcwd()
DATA = os.path.join(HERE, "data")
if not os.path.isdir(DATA):
    os.makedirs(DATA)

# ---------------------------------------------------------------- build slope
it.command("model new")
it.command("model large-strain off")
# foundation (full width) + slope wedge on the left, merged
it.command("zone create2d quadrilateral point 0 (0,0)  point 1 (40,0)  point 2 (0,10) point 3 (40,10) size 40 10")
it.command("zone create2d quadrilateral point 0 (0,10) point 1 (25,10) point 2 (0,20) point 3 (10,20) size 25 10 merge on")
print("zones:", it.zone.count(), "gps:", it.gridpoint.count())

# Mohr-Coulomb
C0, PHI0, TENS = 1.8e4, 30.0, 5.0e3
it.command("zone cmodel assign mohr-coulomb")
it.command("zone property density 2000 young 5.0e7 poisson 0.3")
it.command("zone property cohesion %g friction %g tension %g dilation 0" % (C0, PHI0, TENS))

# boundary conditions: bottom fixed, sides roller (x)
it.command("zone gridpoint fix velocity range position-y -0.1 0.1")
it.command("zone gridpoint fix velocity-x range position-x -0.1 0.1")
it.command("zone gridpoint fix velocity-x range position-x 39.9 40.1")
it.command("model gravity 0 -9.81")

def vmax():
    return max((g.vel().mag() for g in it.gridpoint.list()), default=0.0)

def set_strength(F):
    c = C0 / F
    phi = math.degrees(math.atan(math.tan(math.radians(PHI0)) / F))
    it.command("zone property cohesion %g friction %g" % (c, phi))

# ---------------------------------------------------------------- equilibrium
print("=== STAGE 1: gravity equilibrium at full strength ===")
it.command("model solve ratio 1e-4 cycle 30000")
it.command("zone gridpoint initialize velocity-x 0")
it.command("zone gridpoint initialize velocity-y 0")
it.command("zone gridpoint initialize displacement-x 0")
it.command("zone gridpoint initialize displacement-y 0")
print("  equilibrated cyc=%d vmax=%.3e" % (it.cycle(), vmax()))

# ---------------------------------------------------------------- strength reduction
print("=== STAGE 2: strength reduction sweep (find slip) ===")
F_fail = None
for F in [1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6, 2.8, 3.0]:
    set_strength(F)
    it.command("zone gridpoint initialize velocity-x 0")
    it.command("zone gridpoint initialize velocity-y 0")
    it.command("model cycle 3000")
    v = vmax()
    print("  F=%.2f -> vmax=%.4e" % (F, v))
    if v > 1.0e-3:
        F_fail = F
        print("  -> SLIP at F~%.2f (FoS estimate)" % F)
        break

if F_fail is None:
    F_fail = 3.0
    print("  -> no clear slip up to F=3.0; capturing at 3.0")

# develop the slip-surface flow a bit more for a clean velocity field
it.command("model cycle 4000")
print("  developed slip, vmax=%.4e" % vmax())

# ---------------------------------------------------------------- export
gps = [{"id": g.id(), "x": g.pos().x(), "y": g.pos().y(),
        "vx": g.vel().x(), "vy": g.vel().y(),
        "dx": g.disp().x(), "dy": g.disp().y()} for g in it.gridpoint.list()]
zones = [[gp.id() for gp in z.gridpoints()] for z in it.zone.list()]
vm = max((g["vx"] ** 2 + g["vy"] ** 2) ** 0.5 for g in gps)
json.dump({"engine": "FLAC2D 9.0", "test": "slope strength-reduction, slip surface",
           "fos_estimate": F_fail, "n_gp": len(gps), "n_zones": len(zones), "v_max": vm,
           "gridpoints": gps, "zones": zones},
          open(os.path.join(DATA, "flac_slope.json"), "w"))
it.command("model save 'flac_slope_srm'")
print("=== DONE wrote %s  gps=%d zones=%d v_max=%.4e FoS~%.2f ==="
      % (os.path.join(DATA, "flac_slope.json"), len(gps), len(zones), vm, F_fail))

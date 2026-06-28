import itasca as it
import json, os

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.getcwd()
DATA = os.path.join(HERE, "data")
if not os.path.isdir(DATA):
    os.makedirs(DATA)

# ---------------------------------------------------------------- build
it.command("model new")
it.command("model large-strain on")
# gravity tilted ~30 deg toward -x: equivalent to the assembly on a downhill slope
it.command("model gravity -5 -8.5 0")
it.command("block create brick 0 30 0 3 0 4")  # fixed base
it.command("block create brick 0 30 3 22 0 4") # rock mass
# steep joints dipping INTO the hill (+x, anti-dip) -> slender columns that
# overturn downhill (-x free face) under the downslope gravity component
it.command("block cut joint-set dip 72 dip-direction 90 spacing 0.9 origin (15,3,2) range position-y 3.1 22")
it.command("block contact generate-subcontacts")
it.command("block contact material-table default property stiffness-normal 1e9 stiffness-shear 1e9 friction 28")
it.command("block contact jmodel assign mohr")
it.command("block contact property stiffness-normal 1e9 stiffness-shear 1e9 friction 28 cohesion 0")
it.command("block property density 2000")
it.command("block fix range position-y -0.1 2.9")
print("blocks:", it.block.count())

def topbot(b):
    gps = b.gridpoints()
    top = max(gps, key=lambda g: g.pos().y())
    bot = min(gps, key=lambda g: g.pos().y())
    return top.pos().x() - bot.pos().x()

init = {b.id(): (b.pos().x(), b.pos().y(), topbot(b)) for b in it.block.list()}

# ---------------------------------------------------------------- topple
print("=== toppling under gravity ===")
TARGET_SWING = 5.0
for k in range(30):
    it.command("model cycle 1000")
    swing = 0.0
    for b in it.block.list():
        x0, y0, t0 = init[b.id()]
        if y0 < 3:
            continue
        swing = max(swing, t0 - topbot(b))   # tops swinging toward -x
    print("  k=%2d cyc=%d max_top_swing=%.2f" % (k, it.cycle(), swing))
    if swing >= TARGET_SWING:
        print("  -> reached target topple swing=%.2f" % swing)
        break

# ---------------------------------------------------------------- export
blocks_out = []
for b in it.block.list():
    vs = [[g.pos().x(), g.pos().y(), g.pos().z()] for g in b.gridpoints()]
    c = b.pos()
    x0, y0, _ = init[b.id()]
    disp = ((c.x() - x0) ** 2 + (c.y() - y0) ** 2) ** 0.5
    blocks_out.append({"verts": vs, "disp": disp, "fixed": (y0 < 3)})

dmax = max(bk["disp"] for bk in blocks_out)
json.dump({"engine": "3DEC 9.0", "test": "jointed rock column block toppling",
           "n_blocks": len(blocks_out), "disp_max": dmax,
           "blocks": blocks_out},
          open(os.path.join(DATA, "3dec_toppling.json"), "w"))
it.command("model save '3dec_toppling'")
print("=== DONE blocks=%d disp_max=%.2f wrote %s ==="
      % (len(blocks_out), dmax, os.path.join(DATA, "3dec_toppling.json")))

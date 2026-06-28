import itasca as it
import os

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.getcwd()
DATA = os.path.join(HERE, "data")
if not os.path.isdir(DATA):
    os.makedirs(DATA)

# ---------------------------------------------------------------- build slope
# A steep triangular soil slope (back wall x=0, height 22; slope face 57 deg)
# carved from a block; far over the friction angle -> fails and flows (runout).
it.command("model new")
it.command("model domain extent -3 50 -3 28")
it.command("model large-strain on")
it.command("mpoint node spacing 0.5")
it.command("mpoint generate resolution 2 range position-x 0 14 position-y 0 22")
it.command("mpoint delete range plane origin (0,22) normal (22,14) above")  # carve the slope face
it.command("mpoint cmodel assign mohr-coulomb")
it.command("mpoint property density 2000 young 5e6 poisson 0.3 cohesion 1e3 friction 26 dilation 0 tension 0")
it.command("mpoint node fix velocity range position-y -0.6 0.01")    # floor
it.command("mpoint node fix velocity-x range position-x -0.6 0.01")  # back scarp
it.command("model gravity 0 -9.81")
it.command("mpoint initialize-stresses")
it.command("mpoint node damping local 0.5")    # dissipative -> controlled runout, no explosion

# ---------------------------------------------------------------- flow
# NOTE: no FISH here (FISH io.out inside an async task deadlocks the bridge log
# stream). Captured mid-flow (~peak runout velocity) for a dynamic image; the
# mpoint export is done separately via a synchronous execute_code.
print("=== slope failure runout (capturing mid-flow) ===")
it.command("model cycle 600")
it.command("model save 'mpoint_runout'")
print("=== DONE cycled %d, model saved (export via execute_code next) ===" % it.cycle())

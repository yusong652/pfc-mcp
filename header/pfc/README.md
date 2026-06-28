# Header asset — PFC panel (biaxial compression, force chains)

Source for the **PFC** panel of the repo header: a 2D drained biaxial
compression test taken at a mid-shear state, rendered as a force-chain
network (and a velocity field showing the shear band).

Engine: **PFC2D 7.0** (Python 3.6 embedded interpreter).

## Pipeline

```
pfc_biaxial.py   --(run inside PFC2D via itasca-mcp)-->  data/*.json
render.py        --(matplotlib)-->                       force-chain PNG
render_vel.py    --(matplotlib)-->                       velocity-field PNG
```

`pfc_biaxial.py` is deterministic (`model deterministic on`), so the JSON
snapshots regenerate identically.

## Model

- ~1000 balls (kept **under 1000** for the no-license demo cap), radius 0.18–0.28,
  specimen 10×20 (2:1), walls generated with `expand` so corners overlap (no leak).
- Linear contact model: `kn 1.0e8 ks 5.0e7`, local damping `0.7–0.8`.
- Consolidate **frictionless** (dense uniform pack) under isotropic confinement
  via `wall servo` (gain-factor 0.3), then set `fric 0.5` and shear by driving
  the platens at constant velocity while the side walls hold confinement.
- Captured just past peak (axial strain ≈ 0.035), then **relaxed** (platens
  stopped, confinement held, cycled to a quiet state) for a clean force-chain
  snapshot.

## Data (`data/`)

- `pfc_biaxial_shear.json` — active mid-shear: per-ball `x,y,r,vx,vy` + per-contact
  endpoints, normal force `fn`, total force `fmag`. Live velocity field → shear band.
- `pfc_biaxial_relaxed.json` — same schema at the relaxed (quiet) state → cleanest
  force chains. Velocities ≈ 0 here by design.

## Regenerate

Re-run the simulation (PFC2D GUI open with the itasca-mcp bridge started), via the
itasca-mcp `execute_task` tool pointed at `pfc_biaxial.py` — it writes `data/*.json`.

Render locally:

```bash
uv run --with matplotlib --with numpy python render.py       # force chains
uv run --with matplotlib --with numpy python render_vel.py   # velocity / shear band
```

> Final header styling (semi-transparent balls + montage with the other engine
> panels) is done downstream; these scripts produce the raw per-engine panels.

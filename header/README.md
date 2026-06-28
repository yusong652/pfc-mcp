# Repo header — four-engine montage

Source for the itasca-mcp README header: one panel per Itasca engine, each
running that engine's *classic* scenario, all rendered in the same dark-bg
(`#0e1116`) + `inferno` visual language so they tile into a single banner.

Every panel is a real simulation driven through **itasca-mcp** (engine GUI +
`itasca-mcp-bridge`), not a hand-drawn mock-up.

| Panel | Engine | Scenario | What you see |
|-------|--------|----------|--------------|
| [`pfc/`](pfc/) | PFC2D 7.0 | drained biaxial compression | force-chain network (+ shear-band velocity field) |
| [`flac/`](flac/) | FLAC2D 9.0 | strength-reduction (SRM) | rotational slip surface (shear-strain rate, FoS ≈ 2.2) |
| [`3dec/`](3dec/) | 3DEC 9.0 | jointed columns | block-toppling cascade (anti-dip joints + tilted gravity) |
| [`mpoint/`](mpoint/) | MPoint2D 9.0 | slope failure | runout tongue (MPM, coloured by mid-flow velocity) |

## Pipeline (same shape for every panel)

```
<sim>.py   --(run inside the engine GUI via itasca-mcp execute_task)-->  data/
render.py  --(matplotlib, local: uv run --with matplotlib --with numpy)-->  PNG
```

Simulate in the engine → `model save` + export the raw state to `data/` →
render externally with matplotlib for full visual control and reproducibility.
Sim scripts use a `__file__`-relative `data/` path so they are portable, and
read state through the Python API where one exists (PFC/FLAC/3DEC); MPoint has
no `it.mpoint` API, so its export goes through a synchronous-`execute_code` FISH
`file.write` loop.

## Per-engine notes

- **pfc/** — ~1000 balls (under the no-license demo cap), `kn 1e8 ks 5e7`,
  consolidate frictionless under `wall servo`, then `fric 0.5` and shear;
  captured just past peak, then relaxed for clean chains. Detail in
  [`pfc/README.md`](pfc/README.md).
- **flac/** — foundation + slope wedge, Mohr-Coulomb `C0=1.8e4 φ=30`, strength
  reduction sweep until a deep circular slip forms (`render.py` computes
  per-zone shear-strain rate by Green-Gauss from gridpoint velocities).
- **3dec/** — base brick + rock mass cut by a steep anti-dip joint set
  (`dip 72 dip-direction 90 spacing 0.9`); gravity tilted downhill
  (`-5 -8.5 0`) drives an overturning cascade. **Y is vertical** by 3DEC's
  `joint-set` convention. Kept to ~33 columns for the demo subcontact cap; the
  3D render swaps y/z so data-Y maps to screen-vertical.
- **mpoint/** — triangular slope carved from a block (`mpoint generate` + plane
  `delete`), Mohr-Coulomb, local damping, captured mid-flow (~cycle 600) so the
  runout tongue is moving when sampled.

## Regenerate a panel

With the matching engine GUI open and the itasca-mcp bridge started, run the
panel's `<sim>.py` via the itasca-mcp `execute_task` tool (it writes `data/`),
then render locally:

```bash
cd docs/assets/header/<engine>
uv run --with matplotlib --with numpy python render.py   # some add --with scipy
```

> These scripts produce the raw per-engine panels. Final styling
> (semi-transparent fills, colour grading, montage assembly) is done downstream.

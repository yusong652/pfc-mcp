# PFC headless dev container

Runs the Itasca PFC Linux engine in console mode plus `itasca-mcp-bridge`, so
Mac users can develop and test pfc-mcp without a Windows + USB-key setup.
Demo mode (no license required) caps models at 1000 balls/clumps + 1000
rigid blocks + 10 DFNs — enough for bridge integration testing.

## Build

The Itasca `.deb` (~2.5 GB) is downloaded once on the host so we get curl's
resume support if the connection blips, and so it never bakes into a Docker
layer:

```sh
curl -C - -L -o ~/Downloads/itascasoftware.latest.deb \
  https://itasca-software.s3.amazonaws.com/itasca-software/9.subscription/itascasoftware.latest.deb
```

Apple Silicon (M-series) Macs need x86_64 emulation. Use the helper:

```sh
./docker/build.sh
```

The script forwards `--platform=linux/amd64` and `--build-context
itasca-deb=$HOME/Downloads`, then `docker image prune -f`s the dangling
layers left over from the previous tagged build. Skip the prune with
`./docker/build.sh --no-prune` if you want the cache for inspection.

If your `.deb` is somewhere other than `~/Downloads`, set
`ITASCA_DEB_DIR=/path/to/dir` before invoking.

After the first successful build, subsequent rebuilds that only touch bridge
source files reuse the cached engine layer.

`run.sh` does **not** auto-rebuild. If you change `Dockerfile`, run
`./docker/build.sh` first; if you only edit `entrypoint.sh` or files under
`itasca-mcp-bridge/src/`, those are bind-mounted and pick up changes on the
next `run.sh`.

## Run

```sh
./docker/run.sh           # console mode (default, faster)
./docker/run.sh --gui     # also start X stack + noVNC
```

Thin wrapper over `docker compose -f docker/docker-compose.yml up`. The
compose file pins the platform, forwards ports, and live-mounts the bridge
source so editing on the host applies inside the container.

Endpoints:

| URL | When | What it is |
| --- | --- | --- |
| `http://localhost:9001` | always | itasca-mcp-bridge — point your MCP client here |
| `http://localhost:6080/vnc.html` | `--gui` only | PFC's Qt GUI in your browser via noVNC |

Console mode (default) runs `pfc3d9_console` with the bridge on a blocking
poll. Most Mac dev work — testing tools, validating MCP behaviour — needs
no GUI; skip the X stack to start in seconds. Switch to `--gui` only when
you actually want to see particles.

Drop user scripts into `workspace/` at the repo root; they appear at
`/workspace` inside the container.

## Notes on architecture

- Software OpenGL via llvmpipe (no GPU passthrough on Docker-on-Mac), so 3D
  rendering is CPU-bound. Fine for demo-mode dev; long simulations stay
  responsive but interactive 3D rotation feels sluggish.
- Performance under Rosetta is reduced (~30% slower than native x86_64).
  Demo mode caps models at 1000 balls/clumps anyway, so the gap is moot for
  bridge-development workloads.
- Web license auth (if you ever wire it up) goes outbound on
  `gateway.itascacloud.com:443`.

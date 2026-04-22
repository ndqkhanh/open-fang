# `fang` — terminal wrapper for OpenFang

`fang` is a thin shell wrapper that lets you talk to a local OpenFang server
from any terminal, without remembering port numbers, curl payloads, or
`uvicorn` invocations. It also forwards anything it doesn't recognize to the
underlying `openfang` Python CLI, so you don't have to learn two tools.

It is **not** an interactive LLM agent like `claude`. The REPL is a thin
input loop that POSTs each line to `POST /v1/research` and pretty-prints the
JSON result.

---

## Install / verify

The wrapper lives at `~/.local/bin/fang` and that directory is already on
your `PATH`. Confirm:

```bash
which fang
# → /Users/<you>/.local/bin/fang
```

Prerequisites (one-time):

```bash
cd /path/to/open-fang
make install        # creates .venv and installs open-fang + harness_core
```

The wrapper hard-codes the project location — if you move the repo, edit
`OPENFANG_DIR` at the top of `~/.local/bin/fang`.

---

## Quick start

```bash
fang server start            # boot uvicorn on :8010
fang health                  # sanity check
fang                         # drop into REPL
fang> what is chain-of-thought reasoning?
fang> exit
fang server stop             # shut it down when done
```

---

## Command reference

### `fang` (no args)
Interactive REPL.
- Each non-empty line is sent as `{"question": "<line>"}` to `/v1/research`.
- Pretty-prints with `jq` if installed, otherwise `python3 -m json.tool`.
- Type `exit`, `quit`, `q`, or hit Ctrl-D to leave.
- Lines starting with `#` are ignored (handy for inline notes).

```bash
fang
fang> # baseline
fang> retrieval-augmented generation: when is it worth the latency cost?
```

### `fang health`
Hits `GET /healthz` and prints the JSON response. Use it to confirm the
server is reachable.

### `fang ui` (alias `fang docs`)
Opens the FastAPI Swagger UI (`/docs`) in your default browser. Best place
to explore endpoints, request shapes, and try things interactively.

### `fang server <subcommand>`
Manages a local uvicorn process. State is tracked via a PID file at
`/tmp/openfang.pid`; logs go to `/tmp/openfang.log`.

| Subcommand | What it does |
|---|---|
| `start`   | Boots uvicorn in the background, waits up to 5s for `/healthz` to go green |
| `stop`    | SIGTERMs the process, falls back to SIGKILL if it doesn't die in 1.5s |
| `restart` | `stop` then `start` |
| `status`  | Prints PID + URL + `/healthz` body, or "not running" |
| `logs`    | `tail -f` of `/tmp/openfang.log` (Ctrl-C to leave) |

### `fang research "<question>"` (alias `fang ask`)
One-shot version of the REPL — useful in scripts or when you only want one
answer:

```bash
fang research "trade-offs of mixture-of-experts at inference time"
```

### `fang <anything else>`
Forwarded verbatim to the venv's `openfang` binary. So:

```bash
fang skill list                # → openfang skill list
fang mcp serve                 # → openfang mcp serve  (stdio MCP server)
fang trace validate runs.jsonl
```

### `fang help`
Prints this wrapper's usage plus the underlying `openfang --help`.

---

## Environment knobs

The wrapper reads a few env vars so you can run multiple servers or relocate
state without editing the script.

| Variable | Default | Purpose |
|---|---|---|
| `OPENFANG_PORT`     | `8010`               | Server port |
| `OPENFANG_BASE_URL` | `http://127.0.0.1:$OPENFANG_PORT` | Override if you proxy or use TLS |
| `OPENFANG_PIDFILE`  | `/tmp/openfang.pid`  | PID file for `server *` commands |
| `OPENFANG_LOGFILE`  | `/tmp/openfang.log`  | Where uvicorn stdout/stderr land |

The OpenFang server itself reads:

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY`         | Required for LLM-backed routes (`/v1/research` synthesis, LLM-judge verifier). |
| `HARNESS_LLM_MODEL`         | Default `claude-3-5-sonnet-latest`. |
| `OPEN_FANG_DB_PATH`         | SQLite KB location. |
| `OPEN_FANG_SUPERVISOR_MODE` | Set to `isolated` for subprocess-per-specialist supervision (v4.3). |

Set these *before* `fang server start` — uvicorn inherits the parent shell's
environment:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
fang server restart
```

---

## What works without an API key

These endpoints are deterministic and run with no external calls:

- `/healthz`
- `/v1/kb/papers`, `/v1/kb/paper/{id}`, `/v1/kb/graph`
- `/v1/supervisor/status`
- `/v1/memory/timeline`, `/v1/memory/observation/{id}`
- `/viewer/` (Cytoscape graph viewer)
- All `openfang skill *` subcommands

These need `ANTHROPIC_API_KEY`:

- `POST /v1/research` (which is what the REPL hits)
- LLM-judge verifier (Tier-3) and other LLM-backed pipeline steps

Without a key the REPL still runs — you'll just see fallback errors or
degraded results from the synthesis step.

---

## Recipes

**Pipe a question from a file:**
```bash
fang research "$(cat my-question.md)"
```

**Run on a non-default port:**
```bash
OPENFANG_PORT=9000 fang server start
OPENFANG_PORT=9000 fang health
```

**Tail logs while the REPL runs (two terminals):**
```bash
# terminal 1
fang server logs
# terminal 2
fang
```

**Hit a remote OpenFang instance instead of localhost:**
```bash
OPENFANG_BASE_URL=https://fang.example.com fang health
OPENFANG_BASE_URL=https://fang.example.com fang research "..."
```

**Stop everything cleanly:**
```bash
fang server stop
```

---

## Troubleshooting

**`fang: server not reachable at http://127.0.0.1:8010`**
The server isn't running. `fang server start`. If start fails with "did not
become healthy within 5s", check `fang server logs`.

**`fang server start` says "already running" but `fang health` fails**
The PID file is stale. `rm /tmp/openfang.pid && fang server start`. If port
8010 is occupied by something else: `lsof -i :8010` to find the culprit.

**REPL returns `{"detail": "..."}` errors for every question**
Almost certainly missing `ANTHROPIC_API_KEY`, or the configured model is
unavailable. Fix the env, then `fang server restart`.

**`uvicorn not found — run 'make install' in <dir>`**
The venv was wiped or never created. Run `make install` from the project
root.

**Permissions error opening the PID/log file**
Override the locations:
```bash
export OPENFANG_PIDFILE=$HOME/.openfang.pid
export OPENFANG_LOGFILE=$HOME/.openfang.log
```

---

## Internals (for the curious)

- The wrapper is ~120 lines of Bash — read it: `cat ~/.local/bin/fang`.
- `server start` uses `nohup uvicorn open_fang.app:app` with the venv's
  `uvicorn` binary, writing the PID to `$OPENFANG_PIDFILE`.
- The REPL builds the JSON body in Python (`json.dumps`) so quotes and
  special characters in your question are always escaped correctly.
- Forwarded subcommands `exec` into `openfang`, so signals and exit codes
  propagate cleanly (Ctrl-C in `fang mcp serve` works as expected).

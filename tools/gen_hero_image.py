#!/usr/bin/env python3
"""gen_hero_image.py — the single canonical Sanctum-docs hero generator.

House style (see HERO_ROADMAP.md): black-and-white pencil sketch, hand-drawn,
wide format, white/off-white background, Tommy the Abyssinian cat observing,
one subtle localized color halo (teal or amber). Pass the full prompt in.

Backends, ONE entry point:
  --backend auto   (default)  H3 in comfy-lab first; if that is down and the
                              internet is up, Imagen (metered); if offline, Flux.
  --backend h3                MiniMax H3 T2V → mid-frame (comfy-lab). Preferred local.
  --backend remote            Force Flux on the render host. Exits 1 rather than spending.
  --backend local             Flux.1-dev on THIS box. Outage path.
  --backend imagen            Metered Google API. Deliberate opt-in.

Usage:
  # metered (the only working path today) — note the cli-venv python:
  ~/.sanctum/cli-venv/bin/python tools/gen_hero_image.py --backend imagen \
      --prompt "..." --out src/content/docs/operations/images/hero-x.png
  # free, once the Flux weights are restored on the render host:
  python3 tools/gen_hero_image.py --backend remote --prompt "..." --out ...

The default is local so nobody accidentally spends on the API. If the local
env is missing we FAIL LOUDLY rather than silently falling back to the paid
path — that no-surprise-charge rule is the whole point of going local.

NO, THE AI ULTRA SUBSCRIPTION CANNOT PAY FOR THIS (probed 2026-07-25 — do not
re-litigate this every time a Cloud bill lands). Google runs two unrelated
ledgers: Ultra ($249/mo, Google Play) covers the Gemini *app*; the developer API
bills a Cloud project. Measured, not assumed:
  * Code Assist OAuth — the path :6543 uses, which DOES run on the Ultra
    allowance — serves text (HTTP 200) but returns HTTP 404 "Requested entity was
    not found" for every image model on the identical envelope. Controlled A/B,
    one field changed.
  * That same subscription token against generativelanguage: HTTP 403 "Request
    had insufficient authentication scopes". The ledgers reject each other in
    both directions.
  * `agy models`: 11 models, all text. No image plugin exists.
  * gemini-cli bundles generateImages, but only via ...FromVertex / ...FromMldev
    — both metered surfaces.
The only surface where Ultra pays for images is the web app, which means browser
automation. That was built and then deliberately deleted: at ~40 heroes/month it
saves about $1.60 against an already-capped $10/mo budget, and it cost a stored
Google session, a stale-cookie failure mode, a keep-warm daemon, and ToS exposure
on the account the haus depends on. Not worth it. If image volume ever grows by
two orders of magnitude, reopen it — the probe above is cheap to re-run.

KNOWN LIMIT OF THE LOCAL BACKEND — legible text and dense composition
(measured 2026-07-25). Flux renders the house style well but is weak at
multi-word signage and at compositions with many labelled elements or a
negation ("knobs REMOVED and set aside"). On the 2026-07-25 knobs hero it
produced invented words ("WIOUS", "WARLU"), garbled the plate to "AOIK-THEN",
drew three doorways instead of four, and left the knobs attached — inverting
the point of the illustration. 12 minutes of on-device compute, unusable frame.

IGNORE the CLIP warning you will see on every run:

    "The following part of your input was truncated because CLIP can only
     handle sequences up to 77 tokens: [...]"

It is benign and NOT the cause of a bad render. Flux has two text encoders:
CLIP supplies a pooled style embedding (77 tokens, always truncates on a long
prompt) while T5 carries the semantics — and flux_backend.py passes
max_sequence_length=512, so the full prompt does reach the model. Chasing that
warning as a truncation bug is a dead end; it was misdiagnosed as one here
before the T5 path was checked.

Practical rule: local is right for atmosphere and single-subject scenes. If the
hero needs LEGIBLE lettering or several precisely-labelled elements, use
--backend imagen and accept the metered cost.
"""
import argparse
import os
import pathlib
import subprocess
import sys

# aspect ratio -> (width, height), multiples of 16 for the diffusion backend
ASPECT_DIMS = {
    "16:9": (1344, 768),
    "1:1": (1024, 1024),
    "4:3": (1152, 896),
    "3:4": (896, 1152),
    "9:16": (768, 1344),
}
DEFAULT_FLUX_VENV = pathlib.Path.home() / "Projects" / "comfy-lab" / ".venv-flux"

# ── the Wizard cameo ─────────────────────────────────────────────────────────
# Like Tommy, the Wizard (the haus's one human, robe and staff, playa-issued)
# may appear in heroes as a small background figure — never the subject unless
# the page is actually about him. Appended by --wizard so individual prompts
# don't have to re-describe him and he stays visually consistent across pages.
WIZARD_CAMEO = (
    ". Small in the background, a robed wizard figure with long dreadlocks "
    "and a cap crowned with small deer antlers, holding a tall staff "
    "tipped by a single softly glowing amber halo, watches from the dust "
    "haze, back turned, unhurried, hand-drawn in the same pencil style"
)

# ── where Flux may run ───────────────────────────────────────────────────────
# Measured 2026-07-26 on manoir (Mac Mini M4, 64 GB): one 1344x768 / 40-step
# render peaked at 36 GiB resident. The Mini was already carrying the council,
# the VM, OrbStack and the curfew engine, so it went straight into swap —
# swap-sentinel logged `level=critical pressure=4 culprit=[python3.12 (36.0GiB)]`
# every two minutes, the render wedged in VAE decode for 15+ minutes without
# producing a file, and it had to be killed. This box has already taken one
# memory-exhaustion kernel panic (2026-07-10); it is not a render farm, and it
# runs the family's curfew enforcement.
#
# So: Flux renders on the MBP (M4 Max, 128 GB) over the TB5 bridge, and only
# when the MBP is actually idle enough to take it. If it isn't, we pay Google
# rather than gamble the Mini. Rendering Flux ON the Mini requires an explicit
# --force-local and prints what it is risking.
#
# Third option, for when the internet is dark AND the MBP is gone: a
# dereferenced copy of the model lives on the T9 Digital Ark
# (/Volumes/T9/models/flux). flux_backend.py falls through to it automatically
# when the HF cache has none, and says so on stderr. Still needs ~48 GB free
# RAM wherever you run it — the ark solves availability, not arithmetic.
RENDER_HOST = os.environ.get("SANCTUM_RENDER_HOST", "mbp")
# The render host answers to more than one name. RENDER_HOST is the SSH target;
# the same machine's `hostname -s` is "berts". Comparing the two as plain
# strings meant the designated render host refused to render on itself, while
# --backend auto ssh'd a name that does not resolve — so both paths fell through
# to Imagen, which is dead. Four pages shipped without heroes before anyone
# noticed the check was asking the wrong question.
RENDER_HOST_ALIASES = {
    RENDER_HOST,
    os.environ.get("SANCTUM_RENDER_HOSTNAME", "berts"),
}


def _local_names():
    """Every name this machine answers to.

    socket.gethostname() is NOT stable: it returned "berts" one hour and
    "Berts-MacBook-Pro-M4-Max-128GB" the next, on the same machine, because
    mDNS/DNS state changes what it reports. Ask several sources and match on a
    normalised prefix instead of trusting any single string.
    """
    import socket, subprocess
    names = {socket.gethostname()}
    for key in ("LocalHostName", "ComputerName"):
        try:
            r = subprocess.run(["scutil", "--get", key], capture_output=True,
                               text=True, timeout=5)
            if r.returncode == 0:
                names.add(r.stdout.strip())
        except Exception:
            pass
    out = set()
    for n in names:
        n = n.split(".")[0].strip().lower()
        if n:
            out.add(n)
    return out


def _internet_up(host=None, port=443, timeout=4.0):
    """Can we reach the Imagen API host? Decides auto's backend.

    Probes the host the paid call actually needs — not 1.1.1.1 and not a ping.
    A captive portal, a DNS failure, or a blocked egress rule all pass a generic
    reachability check and then fail the real request, which would strand the
    caller on the paid path with no image. TCP connect only; no request is sent,
    so this costs nothing.
    """
    import socket
    host = host or os.environ.get("SANCTUM_IMAGEN_HOST", "generativelanguage.googleapis.com")
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _is_render_host():
    """True when this box is the designated render host, by any of its names."""
    aliases = {a.strip().lower() for a in RENDER_HOST_ALIASES if a}
    for name in _local_names():
        for a in aliases:
            if name == a or name.startswith(a) or a.startswith(name):
                return True
    return False
# 36 GiB observed peak + headroom for the OS and whatever else is resident.
RENDER_MIN_FREE_GIB = float(os.environ.get("SANCTUM_RENDER_MIN_FREE_GIB", "48"))
# Substrings that mean "this host is busy doing something expensive" — a render
# dropped on top of a training run would evict its weights and thrash both.
BUSY_MARKERS = ("mlx_lm.lora", "train.py", "accelerate launch", "torchrun",
                "flux_backend.py", "mlx_lm.fuse", "finetune")


def _ssh(host, script, timeout=30):
    """Run a shell snippet on `host`; return CompletedProcess (never raises)."""
    return subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", host, script],
        capture_output=True, text=True, timeout=timeout,
    )


def remote_capacity(host=RENDER_HOST):
    """(ok, detail) — may `host` take a Flux render right now?

    Checks three things, all of which have to hold: it answers over TB5, it has
    the model cached, and it has both the free RAM and the idleness to spare.
    Free RAM is computed from vm_stat (free + inactive + speculative), which is
    what macOS will actually hand a new process without swapping."""
    probe = r"""
free=$(vm_stat | awk '
  /page size of/ {ps=$8}
  /Pages free/ {f=$3} /Pages inactive/ {i=$3} /Pages speculative/ {s=$3}
  END {gsub(/\./,"",f); gsub(/\./,"",i); gsub(/\./,"",s);
       printf "%.1f", (f+i+s)*ps/1073741824}')
model=no
[ -n "$(ls -d ~/.cache/huggingface/hub/models--black-forest-labs--FLUX.1-dev/snapshots/*/ 2>/dev/null | head -1)" ] && model=yes
busy=$(ps -eo args | grep -iE 'mlx_lm.lora|train\.py|accelerate launch|torchrun|flux_backend\.py|mlx_lm\.fuse|finetune' | grep -v grep | head -3 | cut -c1-60 | tr '\n' ';')
echo "FREE=$free MODEL=$model BUSY=$busy"
"""
    try:
        r = _ssh(host, probe)
    except Exception as e:
        return False, f"{host} unreachable ({type(e).__name__})"
    if r.returncode != 0:
        return False, f"{host} unreachable (ssh rc={r.returncode})"
    out = dict(kv.split("=", 1) for kv in
               (r.stdout.strip().split(" ", 2) if r.stdout.strip() else []) if "=" in kv)
    try:
        free = float(out.get("FREE", "0"))
    except ValueError:
        free = 0.0
    if out.get("MODEL") != "yes":
        return False, f"{host} has no FLUX.1-dev snapshot cached"
    busy = (out.get("BUSY") or "").strip("; ")
    if busy:
        return False, f"{host} is busy: {busy}"
    if free < RENDER_MIN_FREE_GIB:
        return False, f"{host} has {free:.1f} GiB free, need {RENDER_MIN_FREE_GIB:.0f}"
    return True, f"{host} ready ({free:.1f} GiB free)"


def gen_remote(a, host=RENDER_HOST) -> None:
    """Render on `host` over ssh, then copy the PNG back. Raises on failure so
    the caller can fall back to the metered path."""
    w, h = ASPECT_DIMS.get(a.aspect, ASPECT_DIMS["16:9"])
    remote_out = f"/tmp/hero-{os.getpid()}.png"
    venv = os.environ.get("SANCTUM_REMOTE_FLUX_VENV",
                          "~/Projects/comfy-lab/.venv-flux/bin/python")
    backend = os.environ.get("SANCTUM_REMOTE_FLUX_BACKEND",
                             "~/Projects/Claude_Code/sanctum-docs/tools/flux_backend.py")
    import shlex
    cmd = (f"{venv} {backend} --prompt {shlex.quote(a.prompt)} "
           f"--out {remote_out} --width {w} --height {h} "
           f"--steps {a.steps} --seed {a.seed}")
    if a.dry_run:
        cmd += " --dry-run"
    # Detach the render from the ssh session. A Flux render is ~10 minutes; if
    # the caller's shell exits (or a background job gets reaped, or the TB5 link
    # blips) a foreground `ssh host cmd` takes the render down with it — that
    # happened on the first remote run here, which died at step 4/40. nohup +
    # setsid on the far side means the render owns its own lifetime and we just
    # watch for its sentinel file.
    log = f"{remote_out}.log"
    done = f"{remote_out}.done"
    # Ship the command base64-encoded. `cmd` already contains shlex-quoted
    # single quotes around the prompt, so wrapping it in `sh -c '...'` nests
    # single quotes and the launch silently becomes a no-op — the first version
    # of this did exactly that and polled a sentinel that was never going to
    # appear. base64 has no quoting surface at all.
    import base64
    script = f"{cmd} > {log} 2>&1\necho $? > {done}\n"
    b64 = base64.b64encode(script.encode()).decode()
    runner = f"{remote_out}.sh"
    launch = (f"echo {b64} | base64 -d > {runner} && "
              f"nohup sh {runner} </dev/null >/dev/null 2>&1 & echo started")
    print(f"[render] delegating to {host} over TB5 (detached) …", flush=True)
    r = _ssh(host, launch, timeout=30)
    if r.returncode != 0:
        raise RuntimeError(f"could not launch render on {host} (rc={r.returncode})")

    import time
    deadline = time.time() + float(os.environ.get("SANCTUM_RENDER_TIMEOUT_S", "1800"))
    rc = None
    while time.time() < deadline:
        time.sleep(15)
        probe = _ssh(host, f"cat {done} 2>/dev/null || echo PENDING", timeout=20)
        val = (probe.stdout or "").strip()
        if val and val != "PENDING":
            rc = int(val) if val.isdigit() else 1
            break
    _ssh(host, f"rm -f {done} {runner}", timeout=15)
    if rc is None:
        _ssh(host, f"pkill -f {remote_out} 2>/dev/null; rm -f {log} {runner}", timeout=15)
        raise RuntimeError(f"remote render on {host} exceeded its timeout")
    if rc != 0:
        tail = _ssh(host, f"tail -5 {log} 2>/dev/null", timeout=20).stdout
        _ssh(host, f"rm -f {log}", timeout=15)
        raise RuntimeError(f"remote render failed on {host} (rc={rc})\n{tail}")
    _ssh(host, f"rm -f {log}", timeout=15)
    if a.dry_run:
        return
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    c = subprocess.run(["scp", "-q", f"{host}:{remote_out}", str(out)], text=True)
    _ssh(host, f"rm -f {remote_out}", timeout=15)
    if c.returncode != 0 or not out.exists():
        raise RuntimeError(f"could not copy the render back from {host}")
    print(f"OK {out} ({out.stat().st_size} bytes) — rendered on {host}")


def load_key() -> str:
    k = os.environ.get("GEMINI_API_KEY")
    if k:
        return k.strip()
    p = pathlib.Path.home() / ".sanctum" / "secrets" / "gemini-api-key"
    if p.exists():
        return p.read_text().strip()
    # macOS login keychain — the derived cache the haus already keeps in sync
    # (SOPS is the source of truth; the keychain is downstream of it). Added
    # 2026-07-29: the MBP has the key in its keychain but no bare file, so the
    # Imagen backend was dead on the render host. Reading the keychain instead
    # of writing a bare file matters: this particular key already leaked once by
    # being copied into six places, and a seventh copy is not a fix. GUI session
    # only — a cold SSH cannot unlock the login keychain.
    try:
        r = subprocess.run(
            ["security", "find-generic-password", "-a", "sanctum",
             "-s", "gemini-api-key", "-w"],
            capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    sys.exit(
        "no GEMINI_API_KEY here.\n"
        "  Looked in: $GEMINI_API_KEY, ~/.sanctum/secrets/gemini-api-key, and the\n"
        "  login keychain (service 'gemini-api-key', account 'sanctum').\n\n"
        "  On the MBP — which is the render host but does NOT hold this secret —\n"
        "  the key lives on the Mini. Pass it for one command only, so the render\n"
        "  host never gains a persistent copy:\n\n"
        "    GEMINI_API_KEY=$(ssh <MINI> 'cat ~/.sanctum/secrets/gemini-api-key') \\\n"
        "      ~/.sanctum/cli-venv/bin/python tools/gen_hero_image.py --backend imagen ...\n\n"
        "  Do NOT write it to a file here. This key already leaked once by being\n"
        "  copied into six places; the fix was fewer copies, not more.")


def gen_local(a) -> None:
    """Render with the local Flux backend. Fail loudly if the env is absent."""
    venv = pathlib.Path(os.environ.get("SANCTUM_FLUX_VENV", str(DEFAULT_FLUX_VENV)))
    py = venv / "bin" / "python"
    backend = pathlib.Path(__file__).with_name("flux_backend.py")
    if not py.exists():
        sys.exit(
            f"--backend local: flux venv not found at {py}\n"
            f"  Build it, or set SANCTUM_FLUX_VENV, or run with --backend imagen "
            f"(paid) if you deliberately want Google."
        )
    if not backend.exists():
        sys.exit(f"--backend local: flux_backend.py missing next to {__file__}")
    w, h = ASPECT_DIMS.get(a.aspect, ASPECT_DIMS["16:9"])
    cmd = [
        str(py), str(backend), "--prompt", a.prompt, "--out", a.out,
        "--width", str(w), "--height", str(h),
        "--steps", str(a.steps), "--seed", str(a.seed),
    ]
    if a.dry_run:
        cmd.append("--dry-run")
    # let stdout/stderr stream through so progress + the final "OK ..." show
    raise SystemExit(subprocess.call(cmd))


def _budget_gate() -> None:
    """Refuse to start a metered render when the month is already over budget.

    Ported from the Veo node (comfy-lab/common/nodes/comfyui_veo/veo.py) on
    2026-07-29, when Ultra became the house standard for hero art. Raising the
    quality bar is exactly the moment to add the guard: the tool used to render
    first and ledger afterwards, so the budget could only ever be discovered
    already spent. Fails OPEN — meter trouble must never block deliberate work.
    Set GCP_SPEND_OVERRIDE=1 to spend past the cap on purpose.
    """
    meter = pathlib.Path.home() / "Projects/Claude_Code/tools/gcp_spend.py"
    if os.environ.get("GCP_SPEND_OVERRIDE") == "1" or not meter.exists():
        return
    try:
        r = subprocess.run([sys.executable, str(meter), "check"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 1:
            sys.exit(
                f"GCP monthly budget reached — {r.stdout.strip()}.\n"
                "  Set GCP_SPEND_OVERRIDE=1 to spend past it deliberately, or render\n"
                "  locally with --backend local (free, ~13 min, lower fidelity)."
            )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass  # fail open


def gen_h3(a) -> None:
    """MiniMax H3 T2V in comfy-lab → harvest a still. Free, local, video-first."""
    script = pathlib.Path.home() / "Projects/comfy-lab/scripts/gen-hero-h3.py"
    if not script.exists():
        raise SystemExit(f"missing {script}")
    w, h = ASPECT_DIMS.get(a.aspect, (1344, 768))
    cmd = [
        sys.executable, str(script),
        "--prompt", a.prompt,
        "--out", a.out,
        "--width", str(w),
        "--height", str(h),
        "--seed", str(a.seed),
    ]
    if a.dry_run:
        cmd.append("--dry-run")
    raise SystemExit(subprocess.call(cmd))


def gen_imagen(a) -> None:
    """Render with Google Imagen 4 — METERED. Deliberate opt-in only."""
    if getattr(a, "dry_run", False):
        # A dry run must never spend. This guard was missing entirely: every other
        # backend honoured --dry-run, this one went straight to the paid API and
        # wrote a real image. It was survivable while `auto` tried Flux first and
        # dry-run exited at "would have fallen back to Imagen" — but the 2026-08-12
        # policy routes `auto` here whenever the box is online, so the very first
        # --dry-run after that change bought an image. A dry run that costs $0.134
        # is not a dry run.
        print(f"dry-run: would call {a.model} (METERED) -> {a.out}", file=sys.stderr)
        return
    _budget_gate()
    try:
        from google import genai
    except ImportError:
        sys.exit(
            "Imagen unavailable here: the `google-genai` package is not installed\n"
            "  in THIS interpreter. The package lives in the Sanctum CLI venv, so run:\n"
            "    ~/.sanctum/cli-venv/bin/python tools/gen_hero_image.py --backend imagen ...\n"
            "\n"
            "  (The key itself is fine: it is auto-rotated by the secret rotator and\n"
            "   read from ~/.sanctum/secrets/gemini-api-key. An older version of this\n"
            "   message claimed the key was permanently revoked — that stopped being\n"
            "   true on 2026-07-28 when headless minting was wired up.)\n"
            "\n"
            "  Local rendering still works and costs nothing, but takes ~13 min/image\n"
            "  versus ~10 s on Imagen. Do NOT reach for --force-local off the render\n"
            "  host; the 36 GiB guard is real."
        )
    from google.genai import types

    client = genai.Client(api_key=load_key())
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Two different Google image surfaces behind one --model flag:
    #   imagen-*  -> models.generate_images (a dedicated image endpoint)
    #   gemini-*  -> models.generate_content, image returned as an inline part
    # Added 2026-08-09: asked for "Imagen 5 Ultra", which does not exist on this
    # key — `models.list()` tops out at imagen-4.0-ultra. The genuinely newer
    # image models are the gemini-*-image family, and they were unreachable
    # because this function only ever spoke generate_images.
    if a.model.startswith("gemini"):
        cfg = None
        try:
            cfg = types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio=a.aspect),
            )
        except (AttributeError, TypeError):
            # Older SDK without ImageConfig: still get an image, just at the
            # model's default aspect rather than the requested one.
            cfg = types.GenerateContentConfig(response_modalities=["IMAGE"])
        resp = client.models.generate_content(
            model=a.model, contents=a.prompt, config=cfg)
        data = None
        for cand in (getattr(resp, "candidates", None) or []):
            for part in (getattr(getattr(cand, "content", None), "parts", None) or []):
                inline = getattr(part, "inline_data", None)
                if inline and getattr(inline, "data", None):
                    data = inline.data
                    break
            if data:
                break
        if not data:
            sys.exit(f"no image returned by {a.model} (safety filter or quota?)")
        out.write_bytes(data)
    else:
        resp = client.models.generate_images(
            model=a.model,
            prompt=a.prompt,
            config=types.GenerateImagesConfig(number_of_images=1,
                                              aspect_ratio=a.aspect),
        )
        imgs = getattr(resp, "generated_images", None) or []
        if not imgs:
            sys.exit("no image returned (safety filter or quota?)")
        image = imgs[0].image
        data = getattr(image, "image_bytes", None)
        if data:
            out.write_bytes(data)
        else:
            image.save(str(out))
    # Metered call ($0.02-0.06/image) — ledger it in the haus spend meter, fail-open.
    meter = pathlib.Path.home() / "Projects/Claude_Code/tools/gcp_spend.py"
    if meter.exists():
        try:
            subprocess.run([sys.executable, str(meter), "record", "--service", "imagen",
                            "--model", a.model, "--note", "gen_hero_image"],
                           capture_output=True, timeout=15)
        except Exception:
            pass
    print(f"OK {out} ({out.stat().st_size} bytes)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--aspect", default="16:9", choices=list(ASPECT_DIMS))
    ap.add_argument("--backend", default="auto",
                    choices=["auto", "h3", "remote", "local", "imagen"],
                    help="auto=H3 then Imagen (online) or Flux (offline); "
                         "h3=MiniMax H3 T2V→frame (comfy-lab); "
                         "remote=force Flux on the render host; "
                         "local=Flux HERE (needs --force-local); "
                         "imagen=Google (paid)")
    ap.add_argument("--force-local", action="store_true",
                    help="permit --backend local on a host that is not the render "
                         "host — see the RENDER_HOST note before using this")
    # local (Flux) knobs
    ap.add_argument("--steps", type=int, default=40, help="Flux inference steps (local)")
    ap.add_argument("--seed", type=int, default=42, help="Flux seed (local)")
    ap.add_argument("--dry-run", action="store_true", help="local: verify env, don't render")
    ap.add_argument("--wizard", action="store_true",
                    help="append the Wizard cameo (small background figure, house-consistent)")
    # paid-model knob
    # Newest-and-best is the house standard (Bert, 2026-07-29: "Apple standard,
    # so ... everything is gorgeous"; reaffirmed 2026-08-09 asking for the newest
    # Imagen). The default moved to gemini-3-pro-image on 2026-08-09 for two
    # reasons:
    #   1. The ENTIRE imagen-4.0 family is deprecated by Google, EOL 2026-08-17.
    #      Leaving the default there meant the house hero pipeline would simply
    #      stop working on a known date.
    #   2. "Imagen 5 Ultra" does not exist — models.list() on this key tops out
    #      at imagen-4.0-ultra. The genuinely newer image models are the
    #      gemini-*-image family.
    # Economics changed with it, so state them honestly rather than calling it a
    # rounding error: gemini-3-pro-image bills by OUTPUT TOKENS ($120/1M), which
    # is $0.134 for the 1K/2K image this tool renders and $0.24 at 4K — versus
    # $0.06 for the retiring imagen-4.0-ultra. At ~40 heroes/month that is
    # ~$5.40 against a $10 cap, so the cap is now the real constraint, not
    # decoration. `--model imagen-4.0-generate-001` ($0.04) remains the cheap
    # tier until it EOLs. Rates live in tools/gcp_spend.py; a model with no rate
    # there renders UNLEDGERED (fail-open meter), so add the rate with the model.
    ap.add_argument("--model", default="gemini-3-pro-image",
                    help="Paid model (imagen backend — which now covers BOTH the "
                         "imagen-* generate_images surface and the gemini-*-image "
                         "generate_content surface). Default: gemini-3-pro-image, "
                         "$0.134/image. Cheaper tiers exist but are not the standard.")
    a = ap.parse_args()

    if a.wizard:
        a.prompt = a.prompt.rstrip(". ") + WIZARD_CAMEO

    if a.backend == "imagen":
        gen_imagen(a)
        return

    if a.backend == "h3":
        gen_h3(a)
        return

    if a.backend == "local":
        # Flux here, on whatever box "here" is. Allowed without ceremony only on
        # the designated render host; anywhere else it needs --force-local,
        # because "here" is usually the Mini and the Mini cannot afford it.
        import socket
        here = socket.gethostname().split(".")[0]
        if not _is_render_host() and not a.force_local:
            sys.exit(
                f"refusing --backend local on '{here}': one render peaks at ~36 GiB.\n"
                f"  Measured on manoir 2026-07-26 — it swapped the box to a critical\n"
                f"  swap-sentinel alert, wedged in VAE decode, and had to be killed.\n"
                f"  Use --backend auto (delegates to {RENDER_HOST}, falls back to\n"
                f"  Imagen), or pass --force-local if you truly mean it."
            )
        gen_local(a)
        return

    # auto: H3 first. Then Imagen if online. Flux only when offline.
    if a.backend == "auto":
        try:
            gen_h3(a)
            return
        except SystemExit as e:
            print(f"[render] H3 unavailable: {e}", file=sys.stderr)
        except Exception as e:
            print(f"[render] H3 failed: {e}", file=sys.stderr)
        offline = not _internet_up()
        if not offline:
            gen_imagen(a)
            return
        print("[render] no internet — Flux is the offline path", file=sys.stderr)
        if _is_render_host():
            gen_local(a)
            return

    # remote / leftover auto: try the Flux render host.
    ok, detail = remote_capacity()
    if ok:
        try:
            gen_remote(a)
            return
        except Exception as e:
            print(f"[render] {e}", file=sys.stderr)
            if a.backend == "remote":
                sys.exit(1)
    else:
        print(f"[render] not delegating: {detail}", file=sys.stderr)
        if a.backend == "remote":
            sys.exit(1)

    # Offline with no working Flux path = no image. Falling back to Imagen here would
    # be incoherent: the reason we are on this branch is that the API is unreachable.
    # Say so plainly instead of dialling a number that cannot connect.
    if offline:
        sys.exit(
            f"no internet and no working Flux path ({detail}).\n"
            f"  Offline hero generation needs the FLUX.1-dev weights restored to the\n"
            f"  render host ({RENDER_HOST}) — its HuggingFace cache is empty.\n"
            f"  Online, this would have used Imagen and cost ~$0.134."
        )

    if a.dry_run:
        sys.exit(f"dry-run: would have fallen back to Imagen ({detail})")
    print(f"[render] falling back to Imagen (METERED) — {detail}", file=sys.stderr)
    gen_imagen(a)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""One command for the channel: make the next long videos and Shorts that have not been made yet.

It picks them from the library (longform/videos/ in file order; shorts/stories_library.json, then the older sets),
renders them on GitHub's computers (never this one), waits, and downloads the finished files to videos/<date>/.

  ./generate.py                    next 2 long videos + 5 Shorts
  ./generate.py --long 1 --shorts 3
  ./generate.py --status           what has been made and what is left
  ./generate.py --dry-run          show the picks, change nothing

Needs git and the GitHub CLI (gh), logged in with a token that may push and run workflows
(fine-grained token: Contents, Actions and Workflows set to "Read and write"). Python standard library only.
A failed render changes nothing: run the same command again and it retries the same picks.
"""
import argparse, datetime, json, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(ROOT, "generated.txt")  # one line per finished item: "<long|short> <id> <date>"


def sh(*cmd, out=False):
    r = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=out)
    if r.returncode:
        sys.exit(f"failed: {' '.join(cmd)}\n{(r.stderr or '').strip()}")
    return r.stdout.strip() if out else ""


def push():
    """Push, first replaying any commits made elsewhere meanwhile (local edits are set aside and restored)."""
    sh("git", "pull", "-q", "--rebase", "--autostash")
    sh("git", "push", "-q")


def load(*parts):
    return json.load(open(os.path.join(ROOT, *parts), encoding="utf-8"))


def library():
    """(long ids, short ids) in the order they should be made."""
    d = os.path.join(ROOT, "longform", "videos")
    longs = [load("longform", "videos", f)["id"] for f in sorted(os.listdir(d)) if f.endswith(".json")]
    shorts = ([s["id"] for s in load("shorts", "stories_library.json")] + [s["id"] for s in load("shorts", "stories.json")["stories"]]
              + [s["id"] for s in load("shorts", "stories_parchment.json")])
    return longs, shorts


def made():
    if not os.path.exists(STATE):
        return set()
    return {tuple(line.split()[:2]) for line in open(STATE, encoding="utf-8") if line.strip() and not line.startswith("#")}


def picks(n_long, n_short):
    done = made()
    longs, shorts = library()
    return ([i for i in longs if ("long", i) not in done][:n_long], [i for i in shorts if ("short", i) not in done][:n_short])


def status():
    done = made()
    longs, shorts = library()
    for kind, pool in (("long", longs), ("short", shorts)):
        left = [i for i in pool if (kind, i) not in done]
        print(f"{kind}: {len(pool) - len(left)} made, {len(left)} left" + (f"; next: {', '.join(left[:5])}" if left else ""))


def write_render_list(path, ids, what):
    head = [l for l in open(path, encoding="utf-8").read().split("\n") if l.startswith("#")]
    open(path, "w", encoding="utf-8").write("\n".join(head + ids) + "\n")
    print(f"  {what}: {', '.join(ids)}")


def dispatch(workflow, since):
    """Start a workflow on main and return its run (id, number) once GitHub lists it."""
    sh("gh", "workflow", "run", workflow, "--ref", "main")
    for _ in range(40):
        time.sleep(3)
        runs = json.loads(sh("gh", "run", "list", "--workflow", workflow, "--event", "workflow_dispatch", "--limit", "5",
                             "--json", "databaseId,number,createdAt", out=True))
        new = [r for r in runs if r["createdAt"] >= since]
        if new:
            return new[0]["databaseId"], new[0]["number"]
    sys.exit(f"{workflow} was started but never appeared in the run list; check the Actions tab")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--long", type=int, default=2)
    ap.add_argument("--shorts", type=int, default=5)
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.status:
        return status()
    longs, shorts = picks(a.long, a.shorts)
    if not longs and not shorts:
        sys.exit("The library is used up: add videos to longform/videos/ and stories to shorts/stories_library.json.")
    print("This run makes:")
    print(f"  long videos: {', '.join(longs) or '-'}")
    print(f"  shorts: {', '.join(shorts) or '-'}")
    if a.dry_run:
        return
    if sh("git", "status", "--porcelain", "--", "longform/render.txt", "shorts/render.txt", "generated.txt", out=True):
        sys.exit("render.txt or generated.txt has uncommitted edits; commit or discard them first")
    sh("git", "pull", "-q", "--rebase", "--autostash")

    print("Queueing the renders...")
    if longs:
        write_render_list(os.path.join(ROOT, "longform", "render.txt"), longs, "long")
    if shorts:
        write_render_list(os.path.join(ROOT, "shorts", "render.txt"), shorts, "shorts")
    sh("git", "add", "longform/render.txt", "shorts/render.txt")
    if sh("git", "diff", "--cached", "--name-only", out=True):
        # [skip ci]: this push must not start the push-triggered workflows; the dispatches below start them, once each
        sh("git", "commit", "-q", "-m", f"Render queue: {', '.join(longs + shorts)} [skip ci]")
        push()

    since = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    runs = []
    if longs:
        runs.append(("long",) + dispatch("long.yml", since))
    if shorts:
        runs.append(("shorts",) + dispatch("shorts.yml", since))
    repo = sh("gh", "repo", "view", "--json", "url", "-q", ".url", out=True)
    for kind, rid, _ in runs:
        print(f"Rendering {kind} on GitHub: {repo}/actions/runs/{rid}")
    print("Long videos take about an hour. If you close this window the render still finishes on GitHub; run")
    print("./generate.py again afterwards and it re-queues the same picks (nothing is marked done until downloaded).")

    out = os.path.join(ROOT, "videos", datetime.date.today().isoformat())
    for kind, rid, num in runs:
        r = subprocess.run(["gh", "run", "watch", str(rid), "--exit-status", "--interval", "60"], cwd=ROOT,
                           stdout=subprocess.DEVNULL)
        if r.returncode:
            sys.exit(f"The {kind} render failed: {repo}/actions/runs/{rid} (open it to read the error). Nothing was marked done.")
        tag = f"{kind}-{num}"
        os.makedirs(os.path.join(out, kind), exist_ok=True)
        sh("gh", "release", "download", tag, "-D", os.path.join(out, kind), "--clobber")
        print(f"  {kind}: downloaded release {tag} -> {os.path.join(out, kind)}")

    today = datetime.date.today().isoformat()
    with open(STATE, "a", encoding="utf-8") as f:
        f.writelines([f"long {i} {today}\n" for i in longs] + [f"short {i} {today}\n" for i in shorts])
    sh("git", "add", "generated.txt")
    sh("git", "commit", "-q", "-m", f"Made: {', '.join(longs + shorts)} [skip ci]")
    push()
    print(f"Done. Files are in {out}")
    status()


if __name__ == "__main__":
    main()

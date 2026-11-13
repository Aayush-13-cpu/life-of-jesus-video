"""Download the newest batch of rendered Shorts from this repo's GitHub Releases into shorts/output/.

  python shorts/fetch.py            # newest "shorts-N" release
  python shorts/fetch.py 3          # a specific batch, shorts-3

Public repo, so no login is needed; files already downloaded at the same size are skipped.
"""
import json, os, sys, urllib.request

REPO = "Aayush-13-cpu/life-of-jesus-video"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "shorts-fetch"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main():
    releases = [r for r in get(f"https://api.github.com/repos/{REPO}/releases?per_page=30") if r["tag_name"].startswith("shorts-")]
    if len(sys.argv) > 1:
        releases = [r for r in releases if r["tag_name"] == f"shorts-{sys.argv[1]}"]
    if not releases:
        sys.exit("no shorts release found yet; is the render finished?")
    rel = releases[0]
    os.makedirs(OUT, exist_ok=True)
    print(f"{rel['tag_name']}: {len(rel['assets'])} files -> {OUT}")
    for a in rel["assets"]:
        path = os.path.join(OUT, a["name"])
        if os.path.exists(path) and os.path.getsize(path) == a["size"]:
            continue
        urllib.request.urlretrieve(a["browser_download_url"], path + ".part")
        os.replace(path + ".part", path)  # a dropped connection never leaves a half file under the real name
        print(f"  {a['name']}  {a['size'] / 1e6:.1f} MB")


if __name__ == "__main__":
    main()

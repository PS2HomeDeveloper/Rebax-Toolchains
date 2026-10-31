import argparse, hashlib, json, lzma, os, subprocess, sys, tarfile

TOOLCHAINS = {
    "clang": [
        {"id": "linux-x86_64", "runner": "ubuntu-24.04", "kind": "linux", "arch": "x86_64"},
        {"id": "linux-arm64", "runner": "ubuntu-24.04-arm", "kind": "linux", "arch": "arm64"},
        {"id": "linux-x86", "runner": "ubuntu-24.04", "kind": "linux32", "arch": "x86"},
        {"id": "linux-arm", "runner": "ubuntu-24.04", "kind": "linuxarm", "arch": "arm"},
        {"id": "android-arm64-v8a", "runner": "ubuntu-24.04", "kind": "android", "arch": "arm64-v8a"},
        {"id": "android-armeabi-v7a", "runner": "ubuntu-24.04", "kind": "android", "arch": "armeabi-v7a"},
        {"id": "android-x86", "runner": "ubuntu-24.04", "kind": "android", "arch": "x86"},
        {"id": "android-x86_64", "runner": "ubuntu-24.04", "kind": "android", "arch": "x86_64"},
        {"id": "windows-x86_64", "runner": "windows-2022", "kind": "windows", "arch": "x64"},
        {"id": "windows-x86", "runner": "windows-2022", "kind": "windows", "arch": "x86"},
        {"id": "macos-x86_64", "runner": "macos-15-intel", "kind": "macos", "arch": "x86_64"},
        {"id": "macos-arm64", "runner": "macos-15", "kind": "macos", "arch": "arm64"},
    ],
}


def run(cmd, **kw):
    print("+ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


def list_tree(root, top):
    state = {"dirs": 0, "files": 0}
    lines = [top]

    def walk(path, prefix):
        names = sorted(os.listdir(path))
        for i, name in enumerate(names):
            full = os.path.join(path, name)
            last = i == len(names) - 1
            branch = "└── " if last else "├── "
            if os.path.islink(full):
                lines.append(prefix + branch + name + " -> " + os.readlink(full))
                state["files"] += 1
            elif os.path.isdir(full):
                lines.append(prefix + branch + name)
                state["dirs"] += 1
                walk(full, prefix + ("    " if last else "│   "))
            else:
                lines.append(prefix + branch + name)
                state["files"] += 1

    walk(root, "")
    lines.append("")
    lines.append("%d directories, %d files" % (state["dirs"], state["files"]))
    return "\n".join(lines) + "\n"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pack(root, top, name, dest):
    os.makedirs(dest, exist_ok=True)
    archive = os.path.join(dest, name + ".tar.xz")
    with tarfile.open(archive, "w:xz", format=tarfile.GNU_FORMAT, preset=9 | lzma.PRESET_EXTREME) as tf:
        tf.add(root, arcname=top)
    with open(os.path.join(dest, name + ".tree.txt"), "w", encoding="utf-8") as f:
        f.write(list_tree(root, top))
    digest = sha256(archive)
    with open(os.path.join(dest, name + ".sha256"), "w") as f:
        f.write(digest + "  " + name + ".tar.xz\n")
    print(name, os.path.getsize(archive), digest)


def manifest(directory, version):
    items = {}
    for fn in sorted(os.listdir(directory)):
        if fn.endswith(".tar.xz"):
            p = os.path.join(directory, fn)
            items[fn[:-7]] = {"file": fn, "size": os.path.getsize(p), "sha256": sha256(p)}
    with open(os.path.join(directory, "manifest.json"), "w") as f:
        json.dump({"version": version, "packages": items}, f, indent=2)
    print(len(items), "packages")


def matrix(only, toolchain):
    chosen = []
    for tc, hosts in TOOLCHAINS.items():
        if toolchain and tc != toolchain:
            continue
        for h in hosts:
            entry = dict(h)
            entry["toolchain"] = tc
            entry["name"] = tc + "-host-" + h["id"]
            if not only or only == entry["name"] or only == h["id"]:
                chosen.append(entry)
    if not chosen:
        sys.exit("nothing matches: " + only)
    line = "matrix=" + json.dumps({"include": chosen}, separators=(",", ":"))
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(line + "\n")
    print(line)


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("pack")
    k.add_argument("--root", required=True)
    k.add_argument("--top", required=True)
    k.add_argument("--name", required=True)
    k.add_argument("--dest", required=True)
    m = sub.add_parser("manifest")
    m.add_argument("--dir", required=True)
    m.add_argument("--version", default="")
    x = sub.add_parser("matrix")
    x.add_argument("--only", default="")
    x.add_argument("--toolchain", default="")
    a = p.parse_args()
    if a.cmd == "pack":
        pack(a.root, a.top, a.name, a.dest)
    elif a.cmd == "manifest":
        manifest(a.dir, a.version)
    else:
        matrix(a.only, a.toolchain)


if __name__ == "__main__":
    main()

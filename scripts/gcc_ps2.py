import argparse, glob, os, shutil, subprocess, sys

REPOS = [
    ("dvp", "https://github.com/ps2dev/ps2toolchain-dvp.git"),
    ("iop", "https://github.com/ps2dev/ps2toolchain-iop.git"),
    ("ee", "https://github.com/ps2dev/ps2toolchain-ee.git"),
]
REF = "main"
PRUNE = ["share/man", "share/info", "share/locale"]
PRUNE_GLOBS = ["lib/gcc/*/*/plugin"]


def run(cmd, cwd=None, env=None):
    print("+ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=cwd, env=env)


def capture(cmd, cwd):
    return subprocess.run(cmd, check=True, cwd=cwd, capture_output=True, text=True).stdout.strip()


def read_pins(folder):
    pins = []
    config_dir = os.path.join(folder, "config")
    for name in sorted(os.listdir(config_dir)):
        if name.endswith("-config.sh"):
            with open(os.path.join(config_dir, name)) as f:
                for line in f:
                    if "_REPO_URL=" in line or "_DEFAULT_REPO_REF=" in line:
                        pins.append(line.strip())
    return pins


def prune(ps2dev):
    for name, _ in REPOS:
        paths = [os.path.join(ps2dev, name, *rel.split("/")) for rel in PRUNE]
        for pattern in PRUNE_GLOBS:
            paths += glob.glob(os.path.join(ps2dev, name, *pattern.split("/")))
        for path in paths:
            if os.path.isdir(path):
                shutil.rmtree(path)
                print("removed " + path)


EE_TRIPLE = "mips64r5900el-ps2-elf"
KEEP_LIB = ("libstdc++", "libsupc++", "ldscripts")


def remove_path(path):
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)
    else:
        os.remove(path)


def finish(ps2dev):
    top_bin = os.path.join(ps2dev, "bin")
    if os.path.isdir(top_bin):
        dvp_bin = os.path.join(ps2dev, "dvp", "bin")
        os.makedirs(dvp_bin, exist_ok=True)
        for name in os.listdir(top_bin):
            shutil.move(os.path.join(top_bin, name), os.path.join(dvp_bin, name))
        os.rmdir(top_bin)
    ee = os.path.join(ps2dev, "ee", EE_TRIPLE)
    inc = os.path.join(ee, "include")
    if os.path.isdir(inc):
        for name in os.listdir(inc):
            if name != "c++":
                remove_path(os.path.join(inc, name))
    lib = os.path.join(ee, "lib")
    if os.path.isdir(lib):
        for name in os.listdir(lib):
            if not name.startswith(KEEP_LIB):
                remove_path(os.path.join(lib, name))


def build(out, work):
    ps2dev = os.path.abspath(out)
    work = os.path.abspath(work)
    for d in (ps2dev, work):
        if os.path.exists(d):
            shutil.rmtree(d)
    os.makedirs(ps2dev)
    os.makedirs(work)

    env = dict(os.environ)
    env["PS2DEV"] = ps2dev
    paths = [os.path.join(ps2dev, "bin")] + [os.path.join(ps2dev, name, "bin") for name, _ in REPOS]
    env["PATH"] = os.pathsep.join([env.get("PATH", "")] + paths)

    source = []
    for name, url in REPOS:
        folder = os.path.join(work, "ps2toolchain-" + name)
        run(["git", "clone", "--depth", "1", "-b", REF, url, folder])
        source.append("ps2toolchain-%s %s %s" % (name, url, capture(["git", "rev-parse", "HEAD"], folder)))
        source.extend("  " + pin for pin in read_pins(folder))
        run(["bash", "./toolchain.sh"], cwd=folder, env=env)

    prune(ps2dev)
    finish(ps2dev)

    with open(os.path.join(ps2dev, "SOURCE.txt"), "w") as f:
        f.write("\n".join(source) + "\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    p.add_argument("--work", default="gcc-ps2-work")
    a = p.parse_args()
    build(a.out, a.work)


if __name__ == "__main__":
    main()

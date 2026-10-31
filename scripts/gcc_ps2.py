import argparse, os, shutil, subprocess, sys

REPOS = [
    ("dvp", "https://github.com/ps2dev/ps2toolchain-dvp.git"),
    ("iop", "https://github.com/ps2dev/ps2toolchain-iop.git"),
    ("ee", "https://github.com/ps2dev/ps2toolchain-ee.git"),
]
REF = "main"
PRUNE = ["share/man", "share/info", "share/locale"]


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

    for name, _ in REPOS:
        for rel in PRUNE:
            path = os.path.join(ps2dev, name, *rel.split("/"))
            if os.path.isdir(path):
                shutil.rmtree(path)
                print("removed " + path)

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

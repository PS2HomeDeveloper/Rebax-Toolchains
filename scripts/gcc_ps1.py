import argparse, glob, os, shutil, sys

import gcc_ps2_cross as x

TARGET = "mipsel-none-elf"
BINUTILS = "2.45"
GCC = "15.2.0"
BINUTILS_URL = "https://ftp.gnu.org/gnu/binutils/binutils-%s.tar.xz" % BINUTILS
GCC_URL = "https://ftp.gnu.org/gnu/gcc/gcc-%s/gcc-%s.tar.xz" % (GCC, GCC)
NATIVE_IDS = ["linux-x86_64", "linux-arm64", "linux-x86", "macos-x86_64", "macos-arm64"]
HOST_IDS = NATIVE_IDS + x.HOST_IDS
GCC_ARGS = ["--disable-docs", "--disable-nls", "--disable-werror", "--disable-libada", "--disable-libssp",
            "--disable-libquadmath", "--disable-threads", "--disable-libgomp", "--disable-libstdcxx-pch",
            "--disable-hosted-libstdcxx", "--disable-multilib", "--disable-shared", "--disable-plugin",
            "--enable-languages=c,c++", "--without-isl", "--without-headers", "--with-float=soft",
            "--with-gnu-as", "--with-gnu-ld"]
BINUTILS_ARGS = ["--disable-docs", "--disable-nls", "--disable-werror", "--disable-gdb", "--disable-sim",
                 "--disable-gprofng", "--with-python=no"]
PRUNE = ["share/man", "share/info", "share/locale"]


def fetch(c, url, name):
    archive = os.path.join(c.work, name + ".tar.xz")
    x.run(["curl", "-fsSL", "--retry", "3", "-o", archive, url])
    x.run(["tar", "-xf", archive, "-C", c.work])
    return os.path.join(c.work, os.path.basename(url)[:-len(".tar.xz")])


def native_profile(host_id):
    return {"kind": "native", "host": "", "cc": "gcc", "cxx": "g++", "ar": "ar", "ld": "ld", "ranlib": "ranlib",
            "nm": "nm", "strip": "strip", "readelf": "readelf", "cflags": "-O2", "cxxflags": "-g -O2",
            "cache": {}, "gcc_args": [], "binutils_args": [], "pie": False, "needed": set()}


def build_native(c, host_id):
    env = x.native_env(c)
    if host_id.startswith("linux"):
        env["LDFLAGS"] = "-static-libstdc++ -static-libgcc"
    build_args = ["--build=i686-pc-linux-gnu"] if host_id == "linux-x86" else []
    x.build_deps(c, build_args)
    bsrc = fetch(c, BINUTILS_URL, "binutils")
    gsrc = fetch(c, GCC_URL, "gcc")
    x.patch_gcc_source(gsrc)
    prefix = c.ps1
    bb = x.fresh(os.path.join(c.work, "build-binutils"))
    x.configure(bsrc, bb, ["--quiet", "--prefix=" + prefix, "--target=" + TARGET] + BINUTILS_ARGS + build_args, env)
    x.make(bb, [], env)
    x.make(bb, ["install-strip"], env)
    env["PATH"] = os.path.join(prefix, "bin") + os.pathsep + env["PATH"]
    gb = x.fresh(os.path.join(c.work, "build-gcc"))
    env["CFLAGS_FOR_TARGET"] = x.TARGET_CFLAGS
    env["CXXFLAGS_FOR_TARGET"] = x.TARGET_CFLAGS
    args = (["--quiet", "--prefix=" + prefix, "--target=" + TARGET, "--with-gmp=" + c.deps,
             "--with-mpfr=" + c.deps, "--with-mpc=" + c.deps] + GCC_ARGS + build_args)
    x.configure(gsrc, gb, args, env)
    x.make(gb, ["all"], env)
    x.make(gb, ["install-strip"], env)
    c.source.append("binutils " + BINUTILS_URL)
    c.source.append("gcc " + GCC_URL)


def build_cross(c, host_id):
    bsrc = fetch(c, BINUTILS_URL, "binutils")
    gsrc = fetch(c, GCC_URL, "gcc")
    x.patch_gcc_source(gsrc)
    x.patch_libiberty(bsrc, False)
    x.build_deps(c)
    x.binutils_native(c, bsrc, TARGET, ".", False)
    x.binutils_host(c, bsrc, TARGET, ".", False)

    env = x.native_env(c)
    env["CFLAGS_FOR_TARGET"] = x.TARGET_CFLAGS
    env["CXXFLAGS_FOR_TARGET"] = x.TARGET_CFLAGS
    nb = x.fresh(os.path.join(gsrc, "build-native"))
    x.configure(gsrc, nb, ["--quiet", "--prefix=" + c.native, "--target=" + TARGET] + GCC_ARGS, env)
    x.make(nb, ["all"], env)
    x.make(nb, ["install-strip"], env)

    aenv = x.cross_gcc_env(c)
    hb = x.fresh(os.path.join(gsrc, "build-host"))
    x.configure(gsrc, hb, x.cross_gcc_args(c, ".", TARGET) + GCC_ARGS, aenv)
    x.make_gcc_with_module_fallback(c, hb, ["all-gcc"], aenv)
    x.make(hb, ["install-gcc"], aenv)

    ver = sorted(os.listdir(os.path.join(c.native, "lib", "gcc", TARGET)))[0]
    shutil.copytree(os.path.join(c.native, "lib", "gcc", TARGET, ver), os.path.join(c.ps1, "lib", "gcc", TARGET, ver),
                    symlinks=True, dirs_exist_ok=True)
    for d in ("lib", "include"):
        src = os.path.join(c.native, TARGET, d)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(c.ps1, TARGET, d), symlinks=True, dirs_exist_ok=True)
    if not os.path.exists(os.path.join(c.ps1, "lib", "gcc", TARGET, ver, "libgcc.a")):
        sys.exit("libgcc.a missing after copy")
    c.source.append("binutils " + BINUTILS_URL)
    c.source.append("gcc " + GCC_URL)


def prune(root):
    for rel in PRUNE:
        path = os.path.join(root, *rel.split("/"))
        if os.path.isdir(path):
            shutil.rmtree(path)
    for path in glob.glob(os.path.join(root, "lib", "gcc", TARGET, "*", "plugin")):
        shutil.rmtree(path)


def build(host_id, out, work):
    c = x.Ctx()
    native = host_id in NATIVE_IDS
    c.p = native_profile(host_id) if native else x.make_profile(host_id)
    x.WINDOWS_BUILD = c.p["kind"] == "windows"
    c.ps1 = os.path.abspath(out)
    c.ps2dev = c.ps1
    c.work = os.path.abspath(work)
    c.native = os.path.abspath("native-ps1")
    c.deps = os.path.abspath("host-deps")
    c.source = []
    for d in (c.ps1, c.work, c.native, c.deps):
        x.fresh(d)
    os.environ["PS2DEV"] = c.ps1
    front = [os.path.join(c.native, "bin")]
    if "path" in c.p:
        front.append(c.p["path"])
    os.environ["PATH"] = os.pathsep.join(front + [os.environ.get("PATH", "")])
    if native:
        build_native(c, host_id)
    else:
        build_cross(c, host_id)
    prune(c.ps1)
    if not native:
        x.strip_and_check(c)
    with open(os.path.join(c.ps1, "SOURCE.txt"), "w") as f:
        f.write("host %s\n" % host_id)
        f.write("\n".join(c.source) + "\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", required=True, choices=HOST_IDS)
    p.add_argument("--out", required=True)
    p.add_argument("--work", default="gcc-ps1-work")
    a = p.parse_args()
    build(a.host, a.out, a.work)


if __name__ == "__main__":
    main()

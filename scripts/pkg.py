import argparse, hashlib, json, lzma, os, shutil, subprocess, sys, tarfile

COMPONENTS = [
    "clang", "lld", "clang-resource-headers",
    "llvm-ar", "llvm-ranlib", "llvm-nm", "llvm-objcopy", "llvm-strip",
]

COMMON = [
    "-DCMAKE_BUILD_TYPE=Release",
    "-DLLVM_ENABLE_PROJECTS=clang;lld",
    "-DLLVM_TARGETS_TO_BUILD=X86;ARM;AArch64",
    "-DLLVM_ENABLE_ASSERTIONS=OFF",
    "-DLLVM_INCLUDE_TESTS=OFF",
    "-DLLVM_INCLUDE_EXAMPLES=OFF",
    "-DLLVM_INCLUDE_BENCHMARKS=OFF",
    "-DLLVM_INCLUDE_DOCS=OFF",
    "-DCLANG_INCLUDE_TESTS=OFF",
    "-DCLANG_INCLUDE_DOCS=OFF",
    "-DLLVM_ENABLE_ZLIB=OFF",
    "-DLLVM_ENABLE_ZSTD=OFF",
    "-DLLVM_ENABLE_LIBXML2=OFF",
    "-DLLVM_ENABLE_TERMINFO=OFF",
    "-DLLVM_ENABLE_LIBEDIT=OFF",
    "-DLLVM_ENABLE_PLUGINS=OFF",
    "-DCLANG_PLUGIN_SUPPORT=OFF",
    "-DCLANG_ENABLE_STATIC_ANALYZER=OFF",
    "-DCLANG_ENABLE_ARCMT=OFF",
    "-DCLANG_DEFAULT_LINKER=lld",
    "-DCLANG_DEFAULT_RTLIB=compiler-rt",
    "-DCLANG_DEFAULT_CXX_STDLIB=libc++",
    "-DLLVM_PARALLEL_LINK_JOBS=2",
    "-DLLVM_DISTRIBUTION_COMPONENTS=" + ";".join(COMPONENTS),
]

HOSTS = [
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
]

ANDROID_ABI = {
    "arm64-v8a": "aarch64-linux-android",
    "armeabi-v7a": "armv7-linux-androideabi",
    "x86": "i686-linux-android",
    "x86_64": "x86_64-linux-android",
}


def platform_args(kind, arch):
    if kind == "linux":
        return ["-DCMAKE_EXE_LINKER_FLAGS=-static"], False
    if kind == "linux32":
        return ["-DLLVM_BUILD_32_BITS=ON", "-DLLVM_HOST_TRIPLE=i686-linux-gnu",
                "-DCMAKE_EXE_LINKER_FLAGS=-static"], False
    if kind == "linuxarm":
        return ["-DCMAKE_SYSTEM_NAME=Linux", "-DCMAKE_SYSTEM_PROCESSOR=arm",
                "-DCMAKE_C_COMPILER=arm-linux-gnueabihf-gcc",
                "-DCMAKE_CXX_COMPILER=arm-linux-gnueabihf-g++",
                "-DCMAKE_STRIP=arm-linux-gnueabihf-strip",
                "-DLLVM_HOST_TRIPLE=armv7-linux-gnueabihf",
                "-DCMAKE_EXE_LINKER_FLAGS=-static"], False
    if kind == "android":
        ndk = os.environ.get("ANDROID_NDK_LATEST_HOME") or os.environ.get("ANDROID_NDK_HOME")
        if not ndk:
            sys.exit("ANDROID_NDK_LATEST_HOME / ANDROID_NDK_HOME is not set")
        return ["-DCMAKE_TOOLCHAIN_FILE=" + ndk + "/build/cmake/android.toolchain.cmake",
                "-DANDROID_ABI=" + arch, "-DANDROID_PLATFORM=android-24",
                "-DANDROID_STL=c++_static", "-DLLVM_HOST_TRIPLE=" + ANDROID_ABI[arch]], False
    if kind == "windows":
        return ["-DCMAKE_C_COMPILER=cl", "-DCMAKE_CXX_COMPILER=cl",
                "-DLLVM_USE_CRT_RELEASE=MT"], True
    if kind == "macos":
        cpu = "arm64" if arch == "arm64" else "x86_64"
        return ["-DCMAKE_OSX_ARCHITECTURES=" + cpu, "-DCMAKE_OSX_DEPLOYMENT_TARGET=11.0"], False
    sys.exit("unknown kind " + kind)


def run(cmd, dry):
    print("+ " + " ".join(cmd), flush=True)
    if not dry:
        subprocess.run(cmd, check=True)


def cmd_build(a):
    extra, no_strip = platform_args(a.kind, a.arch)
    src = os.path.join(a.src, "llvm")
    build = os.path.abspath(a.work)
    prefix = os.path.abspath(a.out)
    cfg = ["cmake", "-S", src, "-B", build, "-G", "Ninja"] + COMMON + extra + ["-DCMAKE_INSTALL_PREFIX=" + prefix]
    run(cfg, a.dry_run)
    target = "install-distribution" if no_strip else "install-distribution-stripped"
    run(["cmake", "--build", build, "--target", target], a.dry_run)


def list_tree(root):
    lines = []
    for base, dirs, files in os.walk(root):
        dirs.sort()
        rel = os.path.relpath(base, root)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if rel != ".":
            lines.append("  " * depth + os.path.basename(base) + "/")
        for f in sorted(files):
            p = os.path.join(base, f)
            if os.path.islink(p):
                lines.append("  " * (depth + 1) + f + " -> " + os.readlink(p))
            else:
                lines.append("  " * (depth + 1) + f + "  (" + str(os.path.getsize(p)) + " bytes)")
    return "\n".join(lines) + "\n"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cmd_pack(a):
    os.makedirs(a.dest, exist_ok=True)
    name = a.name
    archive = os.path.join(a.dest, name + ".tar.xz")
    with tarfile.open(archive, "w:xz", preset=9 | lzma.PRESET_EXTREME) as tf:
        tf.add(a.root, arcname=a.top)
    with open(os.path.join(a.dest, name + ".tree.txt"), "w", encoding="utf-8") as f:
        f.write(a.top + "/\n" + list_tree(a.root))
    digest = sha256(archive)
    with open(os.path.join(a.dest, name + ".sha256"), "w") as f:
        f.write(digest + "  " + name + ".tar.xz\n")
    print(name, os.path.getsize(archive), digest)


def cmd_manifest(a):
    items = {}
    for fn in sorted(os.listdir(a.dir)):
        if fn.endswith(".tar.xz"):
            p = os.path.join(a.dir, fn)
            items[fn[:-7]] = {"file": fn, "size": os.path.getsize(p), "sha256": sha256(p)}
    with open(os.path.join(a.dir, "manifest.json"), "w") as f:
        json.dump({"version": a.version, "packages": items}, f, indent=2)
    print(len(items), "packages")


def cmd_matrix(a):
    chosen = [h for h in HOSTS if not a.only or h["id"] == a.only]
    if not chosen:
        sys.exit("no host matches: " + a.only)
    line = "matrix=" + json.dumps({"include": chosen}, separators=(",", ":"))
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(line + "\n")
    print(line)


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--kind", required=True)
    b.add_argument("--arch", required=True)
    b.add_argument("--src", required=True)
    b.add_argument("--work", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--dry-run", action="store_true")
    k = sub.add_parser("pack")
    k.add_argument("--root", required=True)
    k.add_argument("--top", default="clang")
    k.add_argument("--name", required=True)
    k.add_argument("--dest", required=True)
    m = sub.add_parser("manifest")
    m.add_argument("--dir", required=True)
    m.add_argument("--version", required=True)
    x = sub.add_parser("matrix")
    x.add_argument("--only", default="")
    a = p.parse_args()
    {"build": cmd_build, "pack": cmd_pack, "manifest": cmd_manifest, "matrix": cmd_matrix}[a.cmd](a)


if __name__ == "__main__":
    main()

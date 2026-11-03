import argparse, glob, os, platform, shutil, struct, subprocess, sys, tarfile

HELLO_C = '#include <stdio.h>\nint main(void) { printf("REBAX_OK\\n"); return 0; }\n'
HELLO_CPP = (
    "#include <iostream>\n#include <string>\n#include <vector>\n#include <stdexcept>\n"
    "int main() {\n"
    '  std::vector<std::string> v{"REBAX", "OK"};\n'
    '  try { throw std::runtime_error("x"); }\n'
    '  catch (const std::exception &e) { std::cout << v[0] << "_" << v[1] << std::endl; return 0; }\n'
    "  return 1;\n}\n"
)
SDL_C = ("#include <SDL.h>\nint main(int argc, char *argv[]) {\n  SDL_version v;\n  (void)argc; (void)argv;\n"
         "  SDL_GetVersion(&v);\n  return v.major == 2 ? 0 : 1;\n}\n")

LINUX = {"linux-x86_64": "x86_64-linux-musl", "linux-x86": "i686-linux-musl", "linux-arm64": "aarch64-linux-musl",
         "linux-arm": "armv7-linux-musleabihf"}
ANDROID = {"android-arm64-v8a": ("aarch64-linux-android", "aarch64-linux-android"),
           "android-armeabi-v7a": ("armv7a-linux-androideabi", "arm-linux-androideabi"),
           "android-x86": ("i686-linux-android", "i686-linux-android"),
           "android-x86_64": ("x86_64-linux-android", "x86_64-linux-android")}
WINDOWS = {"windows-x86_64": ("x86_64-w64-mingw32", 0x8664), "windows-x86": ("i686-w64-mingw32", 0x14C),
           "windows-arm64": ("aarch64-w64-mingw32", 0xAA64), "windows-arm": ("armv7-w64-mingw32", 0x1C4)}
APPLE = {"macos-arm64": "arm64-apple-macos11", "macos-x86_64": "x86_64-apple-macos10.13",
         "ios-arm64": "arm64-apple-ios13.0", "ios-simulator-x86_64": "x86_64-apple-ios13.0-simulator"}
ELF_MACHINE = {"linux-x86_64": 0x3E, "linux-x86": 0x03, "linux-arm64": 0xB7, "linux-arm": 0x28,
               "android-arm64-v8a": 0xB7, "android-armeabi-v7a": 0x28, "android-x86": 0x03, "android-x86_64": 0x3E}
MACHO_CPU = {"macos-arm64": 0x0100000C, "macos-x86_64": 0x01000007, "ios-arm64": 0x0100000C,
             "ios-simulator-x86_64": 0x01000007}
QEMU = {"linux-arm64": "qemu-aarch64-static", "linux-arm": "qemu-arm-static"}


def extract(archive, dest):
    os.makedirs(dest, exist_ok=True)
    links = []
    with tarfile.open(archive, "r:xz") as tf:
        for m in tf:
            if m.issym():
                links.append(m)
                continue
            try:
                tf.extract(m, dest, filter="fully_trusted")
            except TypeError:
                tf.extract(m, dest)
    for m in links:
        path = os.path.join(dest, m.name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.lexists(path):
            os.remove(path)
        if os.name != "nt":
            os.symlink(m.linkname, path)
            continue
        src = os.path.normpath(os.path.join(os.path.dirname(path), m.linkname))
        if os.path.isfile(src):
            shutil.copy2(src, path)
    entries = os.listdir(dest)
    return os.path.join(dest, entries[0]) if len(entries) == 1 else dest


def exe_arch_ok(path, target):
    with open(path, "rb") as f:
        head = f.read(4096)
    if target in ELF_MACHINE:
        return head[:4] == b"\x7fELF" and int.from_bytes(head[18:20], "little") == ELF_MACHINE[target]
    if target in WINDOWS:
        off = int.from_bytes(head[60:64], "little")
        return head[:2] == b"MZ" and head[off:off + 4] == b"PE\0\0" and \
            int.from_bytes(head[off + 4:off + 6], "little") == WINDOWS[target][1]
    if target in MACHO_CPU:
        return struct.unpack("<II", head[:8])[1] == MACHO_CPU[target]
    return True


def flags(target, sdk, empty):
    std, rt, gfx = [os.path.join(sdk, n) for n in ("standard", "runtime", "graphics")]
    inc_gfx = os.path.join(gfx, "include", "SDL2")
    cxx_inc = ["-nostdinc++", "-isystem", os.path.join(rt, "include", "c++", "v1")]
    if target in LINUX:
        t = LINUX[target]
        cc = ["--target=" + t, "-nostdlibinc", "-isystem", os.path.join(rt, "include"), "-isystem",
              os.path.join(std, "include")]
        cxx = ["--target=" + t, "-nostdlibinc"] + cxx_inc + cc[2:]
        pre = [os.path.join(std, "lib", n) for n in ("crt1.o", "crti.o")]
        post = [os.path.join(std, "lib", "crtn.o")]
        base = ["--target=" + t, "-nostdlib", "-static", "-fuse-ld=lld", "-Wl,--eh-frame-hdr"]
        libs = ["-L" + os.path.join(rt, "lib"), "-L" + os.path.join(std, "lib")]
        return {"cc": cc, "cxx": cxx, "sdl": ["-I" + inc_gfx],
                "link_c": base + pre + ["@OBJ@"] + libs + ["-lc", "-lgcc"] + post,
                "link_cxx": base + pre + ["@OBJ@"] + libs + ["-lc++", "-lc++abi", "-lunwind", "-lc", "-lgcc"] + post,
                "ext": ""}
    if target in ANDROID:
        clang_t, d = ANDROID[target]
        t = clang_t + "21"
        common = ["--target=" + t, "--sysroot=" + std]
        link = common + ["-fuse-ld=lld", "-rtlib=compiler-rt", "-L" + os.path.join(rt, "lib", d),
                         "-L" + os.path.join(std, "usr", "lib", d, "21"), "-L" + os.path.join(std, "usr", "lib", d)]
        return {"cc": common, "cxx": common + cxx_inc, "sdl": ["-I" + inc_gfx],
                "link_c": link + ["@OBJ@"], "link_cxx": link + ["-static-libstdc++", "@OBJ@"], "ext": ""}
    if target in WINDOWS:
        t = WINDOWS[target][0]
        common = ["--target=" + t, "--sysroot=" + std]
        link = common + ["-fuse-ld=lld", "-rtlib=compiler-rt", "-unwindlib=libunwind", "-static",
                         "-L" + os.path.join(rt, "lib")]
        return {"cc": common, "cxx": common + ["-stdlib=libc++"] + cxx_inc, "sdl": ["-I" + inc_gfx],
                "link_c": link + ["@OBJ@"], "link_cxx": link + ["-stdlib=libc++", "@OBJ@"], "ext": ".exe"}
    t = APPLE[target]
    rtlib = glob.glob(os.path.join(rt, "lib", "libclang_rt.*.a"))
    common = ["--target=" + t, "-isysroot", empty, "-nostdlibinc", "-isystem", os.path.join(std, "include"),
              "-F" + os.path.join(std, "Frameworks"), "-F" + os.path.join(gfx, "Frameworks")]
    cc = common
    cxx = ["--target=" + t, "-isysroot", empty, "-nostdlibinc"] + cxx_inc + common[4:]
    link = ["--target=" + t, "-isysroot", empty, "-fuse-ld=lld", "-nostdlib", "-L" + os.path.join(std, "lib"),
            "-L" + os.path.join(rt, "lib")]
    return {"cc": cc, "cxx": cxx, "sdl": ["-I" + inc_gfx],
            "link_c": link + ["@OBJ@", "-lSystem"] + rtlib,
            "link_cxx": link + ["@OBJ@", "-lc++", "-lSystem"] + rtlib, "ext": ""}


def make_overlay(cc, clang_dir, target, sdk, work):
    ov = os.path.join(work, "resource-" + target)
    if os.path.exists(ov):
        shutil.rmtree(ov)
    inc = glob.glob(os.path.join(clang_dir, "lib", "clang", "*", "include"))
    if not inc:
        sys.exit("clang resource headers not found")
    shutil.copytree(inc[0], os.path.join(ov, "include"))
    t = flags_target(target)
    p = subprocess.run([cc, "--target=" + t, "-resource-dir", ov, "-print-runtime-dir"], stdout=subprocess.PIPE,
                       universal_newlines=True)
    rtdir = p.stdout.strip()
    builtins = glob.glob(os.path.join(sdk, "runtime", "lib", "**", "libclang_rt.builtins*.a"), recursive=True)
    if not rtdir or not builtins:
        sys.exit("cannot prepare compiler-rt for " + target)
    os.makedirs(rtdir, exist_ok=True)
    shutil.copy2(builtins[0], os.path.join(rtdir, "libclang_rt.builtins.a"))
    print("compiler-rt placed in " + rtdir)
    return ov


def flags_target(target):
    if target in ANDROID:
        return ANDROID[target][0] + "21"
    return WINDOWS[target][0]


def sh(cmd, cwd):
    print("+ " + " ".join(cmd), flush=True)
    p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    if p.stdout.strip():
        print(p.stdout.rstrip(), flush=True)
    return p.returncode == 0, p.stdout


def run_target(target, clang_dir, sdk, work, run):
    fl = flags(target, sdk, os.path.join(work, "empty-sysroot"))
    os.makedirs(os.path.join(work, "empty-sysroot"), exist_ok=True)
    ext = ".exe" if os.name == "nt" else ""
    cc = os.path.join(clang_dir, "bin", "clang" + ext)
    cxx = os.path.join(clang_dir, "bin", "clang++" + ext)
    if target in ANDROID or target in WINDOWS:
        ov = make_overlay(cc, clang_dir, target, sdk, work)
        for key in ("cc", "cxx", "link_c", "link_cxx"):
            fl[key] = ["-resource-dir", ov] + fl[key]
    out = os.path.join(work, target)
    os.makedirs(out, exist_ok=True)
    for name, text in (("hello.c", HELLO_C), ("hello.cpp", HELLO_CPP), ("sdl.c", SDL_C)):
        with open(os.path.join(out, name), "w") as f:
            f.write(text)
    results = {}
    for kind, comp, src in (("c", cc, "hello.c"), ("cpp", cxx, "hello.cpp")):
        key = "link_c" if kind == "c" else "link_cxx"
        okc, _ = sh([comp] + fl["cc" if kind == "c" else "cxx"] + ["-O1", "-c", src, "-o", kind + ".o"], out)
        exe = os.path.join(out, "hello_" + kind + fl["ext"])
        okl = False
        if okc:
            args = [a if a != "@OBJ@" else kind + ".o" for a in fl[key]]
            okl, _ = sh([comp] + args + ["-o", exe], out)
        results[kind + " build"] = okc and okl
        if okl:
            results[kind + " arch"] = exe_arch_ok(exe, target)
            if not results[kind + " arch"]:
                print("wrong architecture: " + exe)
            if run:
                prefix = []
                if target == "linux-arm64" and platform.machine().lower() in ("aarch64", "arm64"):
                    prefix = []
                elif target in QEMU and shutil.which(QEMU[target]):
                    prefix = [QEMU[target]]
                elif target in QEMU:
                    prefix = None
                if prefix is not None:
                    okr, text = sh(prefix + [exe], out)
                    results[kind + " run"] = okr and "REBAX_OK" in text
    oks, _ = sh([cc] + fl["cc"] + fl["sdl"] + ["-c", "sdl.c", "-o", "sdl.o"], out)
    results["sdl headers"] = oks
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--toolchain", required=True)
    p.add_argument("--sdks", required=True)
    p.add_argument("--targets", nargs="+", required=True)
    p.add_argument("--run", nargs="*", default=[])
    p.add_argument("--work", default="smoke-work")
    a = p.parse_args()
    work = os.path.abspath(a.work)
    clang_dir = extract(a.toolchain, os.path.join(work, "toolchain"))
    summary, failed = [], False
    for t in a.targets:
        print("::group::" + t, flush=True)
        archive = os.path.join(a.sdks, "rebax-sdk-%s.tar.xz" % t)
        sdk = extract(archive, os.path.join(work, "sdk-" + t))
        res = run_target(t, clang_dir, sdk, work, t in a.run)
        print("::endgroup::", flush=True)
        bad = [k for k, v in res.items() if not v]
        failed = failed or bool(bad)
        summary.append("%-24s %s" % (t, "OK (" + ", ".join(res) + ")" if not bad else "FAILED: " + ", ".join(bad)))
    print("\n".join(summary))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

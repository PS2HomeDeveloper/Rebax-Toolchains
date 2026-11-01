import argparse, glob, os, re, shutil, subprocess, sys

import gcc_ps2

ANDROID_ABIS = {
    "arm64-v8a": {"clang": "aarch64-linux-android", "host": "aarch64-linux-android", "api": "21", "machine": 0xB7},
    "armeabi-v7a": {"clang": "armv7a-linux-androideabi", "host": "arm-linux-androideabi", "api": "24", "machine": 0x28},
    "x86_64": {"clang": "x86_64-linux-android", "host": "x86_64-linux-android", "api": "21", "machine": 0x3E},
    "x86": {"clang": "i686-linux-android", "host": "i686-linux-android", "api": "24", "machine": 0x03},
}
WINDOWS_HOSTS = {
    "windows-x86": ("i686-w64-mingw32", 0x14C),
    "windows-arm64": ("aarch64-w64-mingw32", 0xAA64),
    "windows-arm": ("armv7-w64-mingw32", 0x1C4),
}
WINDOWS_CFLAGS = "-O2 -Wno-implicit-function-declaration -Wno-int-conversion -Wno-incompatible-function-pointer-types"
HOST_IDS = ["android-" + name for name in ANDROID_ABIS] + ["linux-arm"] + sorted(WINDOWS_HOSTS)
LINUX_NEEDED = {"libc.so.6", "libm.so.6", "libdl.so.2", "libpthread.so.0", "librt.so.1", "libutil.so.1",
                "ld-linux-armhf.so.3"}
EE = "mips64r5900el-ps2-elf"
IOP = "mipsel-none-elf"
DVP = "dvp"
TARGET_CFLAGS = "-O2 -gdwarf-2 -gz"
GMP, MPFR, MPC = "6.3.0", "4.2.1", "1.3.1"
ANDROID_NEEDED = {"libc.so", "libm.so", "libdl.so", "liblog.so", "libz.so", "libandroid.so"}
ANDROID_CFLAGS = ("-O2 -include limits.h -include fcntl.h -include unistd.h -D_GNU_SOURCE -D_FILE_OFFSET_BITS=64 "
                  "-Wno-implicit-function-declaration -DHAVE_SYS_SIGLIST=1 -DHAVE_PSIGNAL=1 -UHAVE_GETWD")
ANDROID_CXXFLAGS = "-g -O1 -fno-char8_t -D_GNU_SOURCE -D_FILE_OFFSET_BITS=64"
MODULE_CXXFLAGS = "-g -O1 -fPIC -fno-direct-access-external-data -fno-char8_t -D_GNU_SOURCE -D_FILE_OFFSET_BITS=64"
CACHE_VARS = {"ac_cv_header_fcntl_h": "yes", "ac_cv_func_open": "yes", "ac_cv_func_dup2": "yes",
              "ac_cv_func_getcwd": "yes", "ac_cv_func_psignal": "yes", "ac_cv_func_strsignal": "yes"}


WINDOWS_BUILD = False


class Ctx:
    pass


def run(cmd, cwd=None, env=None):
    print("+ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=cwd, env=env)


def run_logged(cmd, cwd, env):
    print("+ " + " ".join(cmd), flush=True)
    proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            universal_newlines=True)
    lines = []
    for line in proc.stdout:
        sys.stdout.write(line)
        lines.append(line)
    proc.wait()
    return proc.returncode, "".join(lines)


def jobs():
    return str(os.cpu_count() or 2)


def fresh(path):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)
    return path


def read_pins(folder, name):
    values = {}
    with open(os.path.join(folder, "config", "ps2toolchain-%s-config.sh" % name)) as f:
        for line in f:
            m = re.match(r'^(PS2TOOLCHAIN_\w+)="(.*)"\s*$', line.strip())
            if m:
                values[m.group(1)] = m.group(2)
    return values


def clone(url, ref, dest):
    run(["git", "clone", "--depth", "1", "-b", ref, url, dest])
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=dest, capture_output=True, text=True).stdout.strip()


def native_env(c):
    env = dict(os.environ)
    for k in ("CONFIGURE_HOST", "CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS"):
        env.pop(k, None)
    env.update({"CC": "gcc", "CXX": "g++", "AR": "ar", "AS": "as", "LD": "ld", "RANLIB": "ranlib",
                "STRIP": "strip", "NM": "nm"})
    return env


def plain_env(c):
    env = dict(os.environ)
    for k in ("CC", "CXX", "AR", "LD", "RANLIB", "NM", "STRIP", "CONFIGURE_HOST", "CPPFLAGS", "CFLAGS",
              "CXXFLAGS", "LDFLAGS"):
        env.pop(k, None)
    return env


def make_profile(host_id):
    if host_id == "linux-arm":
        t = "arm-linux-gnueabihf"
        return {"kind": "linux", "host": t, "machine": 0x28, "cc": t + "-gcc",
                "cxx": t + "-g++ -static-libstdc++ -static-libgcc", "ar": t + "-ar", "ld": t + "-ld",
                "ranlib": t + "-ranlib", "nm": t + "-nm", "strip": t + "-strip", "readelf": t + "-readelf",
                "cflags": "-O2", "cxxflags": "-g -O2 -fno-char8_t", "cache": {}, "gcc_args": [],
                "binutils_args": ["--disable-gprofng"], "pie": False, "needed": LINUX_NEEDED}
    if host_id in WINDOWS_HOSTS:
        t, machine = WINDOWS_HOSTS[host_id]
        root = os.environ.get("LLVM_MINGW")
        if not root:
            sys.exit("LLVM_MINGW is not set")
        b = os.path.join(root, "bin")
        return {"kind": "windows", "host": t, "machine": machine, "cc": "%s/%s-clang -static" % (b, t),
                "cxx": "%s/%s-clang++ -static" % (b, t), "ar": b + "/llvm-ar", "ld": "%s/%s-ld" % (b, t),
                "ranlib": b + "/llvm-ranlib", "nm": b + "/llvm-nm", "strip": b + "/llvm-strip",
                "readelf": b + "/llvm-readelf", "cflags": WINDOWS_CFLAGS, "cxxflags": "-g -O2 -fno-char8_t",
                "cache": {}, "gcc_args": ["--disable-fixincludes"], "binutils_args": ["--disable-gprofng"],
                "pie": False, "needed": set(), "path": b, "gmp_args": ["--disable-assembly"],
                "cmake_args": ["-DCMAKE_SYSTEM_NAME=Windows"], "note": "llvm-mingw"}
    abi = ANDROID_ABIS[host_id[len("android-"):]]
    ndk = os.environ.get("ANDROID_NDK_HOME")
    if not ndk:
        sys.exit("ANDROID_NDK_HOME is not set")
    b = os.path.join(ndk, "toolchains", "llvm", "prebuilt", "linux-x86_64", "bin")
    return {"kind": "android", "host": abi["host"], "machine": abi["machine"],
            "cc": "%s/%s%s-clang -fPIC -Wl,--no-relax" % (b, abi["clang"], abi["api"]),
            "cxx": "%s/%s%s-clang++ -static-libstdc++ -fPIC -Wl,--no-relax" % (b, abi["clang"], abi["api"]),
            "ar": b + "/llvm-ar", "ld": b + "/ld", "ranlib": b + "/llvm-ranlib", "nm": b + "/llvm-nm",
            "strip": b + "/llvm-strip", "readelf": b + "/llvm-readelf", "cflags": ANDROID_CFLAGS,
            "cxxflags": ANDROID_CXXFLAGS, "cache": CACHE_VARS, "gcc_args": ["--enable-host-pie"],
            "binutils_args": [], "pie": True, "needed": ANDROID_NEEDED, "path": b,
            "note": "ndk %s api %s" % (os.path.basename(ndk), abi["api"])}


def host_env(c):
    p = c.p
    env = dict(os.environ)
    env.update({"CC": p["cc"], "CXX": p["cxx"], "AR": p["ar"], "LD": p["ld"], "RANLIB": p["ranlib"],
                "NM": p["nm"], "STRIP": p["strip"], "CONFIGURE_HOST": p["host"], "CC_FOR_BUILD": "gcc"})
    return env


def configure(src, build, args, env):
    os.makedirs(build, exist_ok=True)
    try:
        run([os.path.join(src, "configure")] + args, cwd=build, env=env)
    except subprocess.CalledProcessError:
        log = os.path.join(build, "config.log")
        if os.path.isfile(log):
            with open(log, errors="replace") as f:
                print("".join(f.readlines()[-120:]))
        raise
    disable_fixincludes(build)


def disable_fixincludes(build):
    if not WINDOWS_BUILD:
        return
    path = os.path.join(build, "Makefile")
    if not os.path.isfile(path):
        return
    with open(path, errors="replace") as f:
        text = f.read()
    new = re.sub(r"(?m)^(maybe-[a-z-]*-fixincludes:).*$", r"\1", text)
    if new != text:
        with open(path, "w") as f:
            f.write(new)
        print("fixincludes disabled in " + path)


def summarize(text):
    pattern = re.compile(r"\berror\b|\*\*\*|fatal|undefined reference|cannot find|No such file", re.I)
    lines = [l.rstrip() for l in text.splitlines() if pattern.search(l) and "warning" not in l.lower()]
    print("=== ERROR SUMMARY ===")
    print("\n".join(lines[:60]))
    print("=== END ERROR SUMMARY ===", flush=True)


def make(build, targets, env, extra=None, retry_single=False):
    cmd = ["make", "--quiet", "-j", jobs()] + targets + (extra or [])
    rc, text = run_logged(cmd, build, env)
    if rc == 0:
        return
    if not retry_single:
        summarize(text)
        raise subprocess.CalledProcessError(rc, cmd)
    print("=== make failed: retrying with one job ===")
    cmd = ["make", "--quiet", "-j", "1"] + targets + (extra or [])
    rc, text = run_logged(cmd, build, env)
    if rc != 0:
        summarize(text)
        raise subprocess.CalledProcessError(rc, cmd)


def patch_libiberty(src, strict):
    path = os.path.join(src, "include", "libiberty.h")
    marker = "HAVE_DECL_BASENAME && !defined (__cplusplus)"
    if os.path.isfile(path):
        with open(path) as f:
            text = f.read()
        if marker not in text:
            text = re.sub(r"(?m)^#if !HAVE_DECL_BASENAME[ \t]*$", "#if !HAVE_DECL_BASENAME && !defined (__cplusplus)", text)
            with open(path, "w") as f:
                f.write(text)
        if strict and marker not in text:
            sys.exit("libiberty.h basename patch did not apply")
    fib = os.path.join(src, "libiberty", "fibheap.c")
    if os.path.isfile(fib):
        with open(fib) as f:
            text = f.read()
        if "#include <limits.h>" not in text:
            with open(fib, "w") as f:
                f.write("#include <limits.h>\n" + text)
    gc = os.path.join(src, "libiberty", "getcwd.c")
    if os.path.isfile(gc):
        with open(gc, "w") as f:
            f.write("typedef int libiberty_getcwd_unused_t;\n")


UTF8_RULES = """utf8rc-mingw32.o :
\t$(COMPILER) -x c -c /dev/null -o $@

sym-mingw32.o : $(srcdir)/config/i386/sym-mingw32.cc
\t$(COMPILER) -c $<

utf8-mingw32.o : sym-mingw32.o
\tcp sym-mingw32.o $@
"""


def patch_gcc_source(src):
    patch_libiberty(src, True)
    path = os.path.join(src, "gcc", "config", "i386", "x-mingw32-utf8")
    if os.path.isfile(path):
        with open(path, "w") as f:
            f.write(UTF8_RULES)


def build_deps(c):
    prefix = c.deps
    os.makedirs(prefix, exist_ok=True)
    env = host_env(c)
    env["CFLAGS"] = "-O2"
    items = [
        ("gmp", GMP, "https://ftp.gnu.org/gnu/gmp/gmp-%s.tar.xz", []),
        ("mpfr", MPFR, "https://ftp.gnu.org/gnu/mpfr/mpfr-%s.tar.xz", ["--with-gmp=" + prefix]),
        ("mpc", MPC, "https://ftp.gnu.org/gnu/mpc/mpc-%s.tar.gz", ["--with-gmp=" + prefix, "--with-mpfr=" + prefix]),
    ]
    for name, ver, url, extra in items:
        archive = os.path.join(c.work, name + ".tar")
        run(["curl", "-fsSL", "--retry", "3", "-o", archive, url % ver])
        run(["tar", "-xf", archive, "-C", c.work])
        src = os.path.join(c.work, "%s-%s" % (name, ver))
        build = os.path.join(c.work, name + "-build")
        configure(src, build, ["--host=" + c.p["host"], "--prefix=" + prefix, "--disable-shared",
                               "--enable-static", "--with-pic"] + c.p.get("gmp_args", []) + extra, env)
        make(build, [], env)
        make(build, ["install"], env)


def binutils_native(c, src, target, alias, sysroot):
    env = native_env(c)
    args = ["--quiet", "--prefix=%s/%s" % (c.native, alias), "--target=" + target]
    if sysroot:
        args.append("--with-sysroot=%s/%s/%s" % (c.native, alias, target))
    args += ["--disable-separate-code", "--disable-sim", "--disable-nls", "--disable-gdb", "--with-python=no"]
    build = fresh(os.path.join(src, "build-%s-native" % target))
    configure(src, build, args, env)
    make(build, [], env)
    make(build, ["install-strip"], env)


def binutils_flags(c):
    return (c.p["cflags"] + " -Wno-implicit-function-declaration").strip()


def binutils_host(c, src, target, alias, sysroot):
    env = host_env(c)
    env["CFLAGS"] = binutils_flags(c)
    args = ["--quiet", "--prefix=%s/%s" % (c.ps2dev, alias), "--target=" + target]
    if sysroot:
        args.append("--with-sysroot=%s/%s/%s" % (c.ps2dev, alias, target))
    args += ["--disable-separate-code", "--disable-sim", "--disable-nls", "--disable-gdb", "--with-python=no",
             "--host=" + c.p["host"]] + c.p["binutils_args"]
    build = fresh(os.path.join(src, "build-%s" % target))
    configure(src, build, args, env)
    make(build, [], env, retry_single=True)
    make(build, ["install-strip"], env)


def for_target_args(c, alias, target):
    nb = "%s/%s/bin" % (c.native, alias)
    args = []
    for var, tool in (("AS", "as"), ("LD", "ld"), ("AR", "ar"), ("RANLIB", "ranlib"), ("NM", "nm"),
                      ("OBJDUMP", "objdump"), ("READELF", "readelf")):
        args.append("%s_FOR_TARGET=%s/%s-%s" % (var, nb, target, tool))
    args.append("GCC_FOR_TARGET=%s/%s-gcc" % (nb, target))
    args.append("CC_FOR_TARGET=%s/%s-gcc" % (nb, target))
    gxx = "%s/%s-g++" % (nb, target)
    if os.path.exists(gxx):
        args.append("CXX_FOR_TARGET=" + gxx)
    return args


def cross_gcc_env(c):
    env = host_env(c)
    env["CFLAGS"] = c.p["cflags"]
    env["CXXFLAGS"] = c.p["cxxflags"]
    env["CFLAGS_FOR_TARGET"] = TARGET_CFLAGS
    env["CXXFLAGS_FOR_TARGET"] = TARGET_CFLAGS
    env["CXXFLAGS_FOR_BUILD"] = "-g -O2 -fno-char8_t -include limits.h"
    env.update(c.p["cache"])
    return env


def cross_gcc_args(c, alias, target):
    return ["--quiet", "--prefix=%s/%s" % (c.ps2dev, alias), "--target=" + target, "--disable-plugin", "--with-gmp=" + c.deps, "--with-mpfr=" + c.deps, "--with-mpc=" + c.deps,
            "--host=" + c.p["host"],
            "--with-build-time-tools=%s/%s/bin" % (c.native, alias)] + c.p["gcc_args"] + for_target_args(c, alias, target) + [
            "CC_FOR_BUILD=/usr/bin/gcc", "CXX_FOR_BUILD=/usr/bin/g++", "CFLAGS_FOR_BUILD=-g -O2 -include limits.h"]


def make_gcc_with_module_fallback(c, build, targets, env):
    rc, text = run_logged(["make", "--quiet", "-j", jobs()] + targets, build, env)
    if rc == 0:
        return
    if "cp/module.o" not in text:
        sys.exit("gcc build failed")
    print("=== rebuilding gcc/cp/module.o with GOT access to external data ===")
    module = os.path.join(build, "gcc", "cp", "module.o")
    if os.path.exists(module):
        os.remove(module)
    subprocess.run(["make", "--quiet", "-C", "gcc", "cp/module.o", "CXXFLAGS=" + MODULE_CXXFLAGS],
                   cwd=build, env=env)
    if not os.path.exists(module):
        sys.exit("gcc/cp/module.o was not rebuilt")
    make(build, targets, env)


def sync_target_tree(c):
    for d in ("include", "lib"):
        src = os.path.join(c.ps2dev, "ee", EE, d)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(c.native, "ee", EE, d), symlinks=True, dirs_exist_ok=True)


def build_ee(c):
    pins = read_pins(c.repos["ee"], "ee")
    src = {}
    for key, name in (("BINUTILS", "binutils-gdb"), ("GCC", "gcc"), ("NEWLIB", "newlib"),
                      ("PTHREAD_EMBEDDED", "pthread-embedded")):
        pre = "PS2TOOLCHAIN_EE_" + key
        src[key] = os.path.join(c.work, "ee-" + name)
        c.source.append("ee %s %s" % (name, clone(pins[pre + "_REPO_URL"], pins[pre + "_DEFAULT_REPO_REF"], src[key])))
    patch_gcc_source(src["GCC"])
    patch_libiberty(src["BINUTILS"], False)
    binutils_native(c, src["BINUTILS"], EE, "ee", True)
    binutils_host(c, src["BINUTILS"], EE, "ee", True)

    env = native_env(c)
    stage1 = fresh(os.path.join(src["GCC"], "build-stage1-native"))
    env1 = dict(env)
    env1["CFLAGS_FOR_TARGET"] = TARGET_CFLAGS
    env1["CXXFLAGS_FOR_TARGET"] = TARGET_CFLAGS
    configure(src["GCC"], stage1, ["--quiet", "--prefix=%s/ee" % c.native, "--target=" + EE,
                                   "--enable-languages=c", "--with-float=hard", "--without-headers",
                                   "--without-newlib", "--disable-libgcc", "--disable-shared",
                                   "--disable-threads", "--disable-multilib", "--disable-libatomic",
                                   "--disable-nls", "--disable-tls", "--disable-libssp", "--disable-libgomp",
                                   "--disable-libmudflap", "--disable-libquadmath", "--disable-plugin"], env1)
    make(stage1, ["all-gcc"], env1)
    make(stage1, ["install-gcc"], env1)

    penv = plain_env(c)
    nl = fresh(os.path.join(src["NEWLIB"], "build-newlib"))
    nenv = dict(penv)
    nenv["CFLAGS_FOR_TARGET"] = TARGET_CFLAGS
    configure(src["NEWLIB"], nl, ["--prefix=%s/ee" % c.ps2dev, "--target=" + EE,
                                  "--with-sysroot=%s/ee/%s" % (c.ps2dev, EE),
                                  "--enable-newlib-retargetable-locking", "--enable-newlib-multithread",
                                  "--enable-newlib-io-c99-formats"], nenv)
    make(nl, ["all"], nenv)
    make(nl, ["install-strip"], nenv)
    sync_target_tree(c)

    nano = fresh(os.path.join(src["NEWLIB"], "build-newlib-nano"))
    tmp = fresh(os.path.join(src["NEWLIB"], "ps2dev-tmp"))
    ncenv = dict(penv)
    ncenv["CFLAGS_FOR_TARGET"] = "-DPREFER_SIZE_OVER_SPEED=1 -Os -gdwarf-2 -gz"
    configure(src["NEWLIB"], nano, ["--prefix=%s/ee" % tmp, "--target=" + EE,
                                    "--with-sysroot=%s/ee/%s" % (c.ps2dev, EE),
                                    "--disable-newlib-supplied-syscalls", "--enable-newlib-reent-small",
                                    "--disable-newlib-fvwrite-in-streamio", "--disable-newlib-fseek-optimization",
                                    "--disable-newlib-wide-orient", "--enable-newlib-nano-malloc",
                                    "--disable-newlib-unbuf-stream-opt", "--enable-lite-exit",
                                    "--enable-newlib-global-atexit", "--enable-newlib-nano-formatted-io",
                                    "--enable-newlib-retargetable-locking", "--enable-newlib-multithread",
                                    "--disable-nls"], ncenv)
    make(nano, ["all"], ncenv)
    make(nano, ["install-strip"], ncenv)
    for lib in ("libc", "libg", "libm"):
        shutil.move("%s/ee/%s/lib/%s.a" % (tmp, EE, lib), "%s/ee/%s/lib/%s_nano.a" % (c.ps2dev, EE, lib))

    penv["PS2DEV"] = c.ps2dev
    plat = os.path.join(src["PTHREAD_EMBEDDED"], "platform", "ps2")
    make(plat, ["all"], penv)
    make(plat, ["install"], penv)
    sync_target_tree(c)

    stage2n = fresh(os.path.join(src["GCC"], "build-stage2-native"))
    env2 = dict(env)
    env2["CFLAGS_FOR_TARGET"] = TARGET_CFLAGS
    env2["CXXFLAGS_FOR_TARGET"] = TARGET_CFLAGS
    configure(src["GCC"], stage2n, ["--quiet", "--prefix=%s/ee" % c.native, "--target=" + EE,
                                    "--enable-languages=c,c++", "--with-float=hard",
                                    "--with-sysroot=%s/ee/%s" % (c.native, EE),
                                    "--with-native-system-header-dir=/include", "--with-newlib",
                                    "--disable-libssp", "--disable-multilib", "--disable-nls", "--disable-tls",
                                    "--enable-cxx-flags=-G0", "--enable-threads=posix"], env2)
    make(stage2n, ["all"], env2)
    make(stage2n, ["install-strip"], env2)

    aenv = cross_gcc_env(c)
    stage2 = fresh(os.path.join(src["GCC"], "build-stage2"))
    args = cross_gcc_args(c, "ee", EE) + ["--enable-languages=c,c++", "--with-float=hard",
                                            "--with-sysroot=%s/ee/%s" % (c.ps2dev, EE),
                                            "--with-native-system-header-dir=/include", "--with-newlib",
                                            "--disable-libssp", "--disable-multilib", "--disable-nls",
                                            "--disable-tls", "--enable-cxx-flags=-G0", "--enable-threads=posix"]
    configure(src["GCC"], stage2, args, aenv)
    make_gcc_with_module_fallback(c, stage2, ["all-gcc"], aenv)
    make(stage2, ["install-gcc"], aenv)

    nat = os.path.join(c.native, "ee")
    dst = os.path.join(c.ps2dev, "ee")
    ver = sorted(os.listdir(os.path.join(nat, "lib", "gcc", EE)))[0]
    shutil.copytree(os.path.join(nat, "lib", "gcc", EE, ver), os.path.join(dst, "lib", "gcc", EE, ver),
                    symlinks=True, dirs_exist_ok=True)
    for pattern in ("*.so", "*.so.*", "*.la"):
        for path in glob.glob(os.path.join(dst, "lib", "gcc", EE, ver, "plugin", pattern)):
            os.remove(path)
    for d in ("lib", "include"):
        shutil.copytree(os.path.join(nat, EE, d), os.path.join(dst, EE, d), symlinks=True, dirs_exist_ok=True)
    for rel in ("lib/gcc/%s/%s/libgcc.a" % (EE, ver), "%s/lib/libstdc++.a" % EE, "%s/include/c++" % EE):
        if not os.path.exists(os.path.join(dst, rel)):
            sys.exit("missing after copy: " + rel)
    crt0 = os.path.join(dst, EE, "lib", "crt0.o")
    if os.path.exists(crt0):
        os.remove(crt0)


def build_iop(c):
    pins = read_pins(c.repos["iop"], "iop")
    src = {}
    for key, name in (("BINUTILS", "binutils-gdb"), ("GCC", "gcc")):
        pre = "PS2TOOLCHAIN_IOP_" + key
        src[key] = os.path.join(c.work, "iop-" + name)
        c.source.append("iop %s %s" % (name, clone(pins[pre + "_REPO_URL"], pins[pre + "_DEFAULT_REPO_REF"], src[key])))
    patch_gcc_source(src["GCC"])
    patch_libiberty(src["BINUTILS"], False)
    binutils_native(c, src["BINUTILS"], IOP, "iop", False)
    binutils_host(c, src["BINUTILS"], IOP, "iop", False)

    common_args = ["--enable-languages=c,c++", "--with-float=soft", "--with-headers=no", "--without-newlib",
                   "--without-cloog", "--without-ppl", "--disable-decimal-float", "--disable-libada",
                   "--disable-libatomic", "--disable-libffi", "--disable-libgomp", "--disable-libmudflap",
                   "--disable-libquadmath", "--disable-libssp", "--disable-libstdcxx-pch", "--disable-multilib",
                   "--disable-shared", "--disable-threads", "--disable-target-libiberty", "--disable-target-zlib",
                   "--disable-nls", "--disable-tls", "--disable-libstdcxx"]
    env = native_env(c)
    env["CFLAGS_FOR_TARGET"] = TARGET_CFLAGS
    env["CXXFLAGS_FOR_TARGET"] = TARGET_CFLAGS
    native = fresh(os.path.join(src["GCC"], "build-native"))
    configure(src["GCC"], native, ["--quiet", "--prefix=%s/iop" % c.native, "--target=" + IOP] + common_args, env)
    make(native, ["all"], env)
    make(native, ["install-strip"], env)

    aenv = cross_gcc_env(c)
    build = fresh(os.path.join(src["GCC"], "build-android"))
    configure(src["GCC"], build, cross_gcc_args(c, "iop", IOP) + common_args, aenv)
    make_gcc_with_module_fallback(c, build, ["all"], aenv)
    make(build, ["install-strip"], aenv)


def cmake_build(c, src, extra):
    prefix = os.path.join(c.ps2dev, "dvp")
    env = host_env(c)
    for var in ("CC", "CXX"):
        for flag in (" -Wl,--no-relax", " -static-libstdc++", " -static-libgcc", " -static"):
            env[var] = env[var].replace(flag, "")
    build = os.path.join(src, "build")
    run(["cmake", "-S", src, "-B", build, "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_INSTALL_PREFIX=" + prefix,
         "-DBUILD_TESTING=OFF"] + c.p.get("cmake_args", []) + extra, env=env)
    run(["cmake", "--build", build, "-j", jobs()], env=env)
    run(["cmake", "--install", build], env=env)


def build_dvp(c):
    pins = read_pins(c.repos["dvp"], "dvp")
    src = {}
    for key, name in (("BINUTILS", "binutils-gdb"), ("MASP", "masp"), ("OPENVCL", "openvcl")):
        pre = "PS2TOOLCHAIN_DVP_" + key
        src[key] = os.path.join(c.work, "dvp-" + name)
        c.source.append("dvp %s %s" % (name, clone(pins[pre + "_REPO_URL"], pins[pre + "_DEFAULT_REPO_REF"], src[key])))
    patch_libiberty(src["BINUTILS"], False)
    env = host_env(c)
    env["CFLAGS"] = binutils_flags(c)
    build = fresh(os.path.join(src["BINUTILS"], "build-dvp"))
    configure(src["BINUTILS"], build, ["--quiet", "--prefix=%s/dvp" % c.ps2dev, "--target=" + DVP, "--disable-nls",
                                       "--disable-build-warnings", "--disable-gdb", "--host=" + c.p["host"]], env)
    make(build, [], env, extra=["CFLAGS=" + env["CFLAGS"]], retry_single=True)
    make(build, ["install"], env, extra=["CFLAGS=" + env["CFLAGS"]])
    if c.p["kind"] == "windows":
        stub = fresh(os.path.join(c.work, "regex-stub"))
        os.makedirs(os.path.join(stub, "include"))
        os.makedirs(os.path.join(stub, "lib"))
        with open(os.path.join(stub, "include", "regex.h"), "w") as f:
            f.write("/* masp only includes this header */\n")
        run([c.p["ar"], "rc", os.path.join(stub, "lib", "libgnurx.a")])
        cmake_build(c, src["MASP"], ["-DCMAKE_C_FLAGS=-I%s/include" % stub,
                                     "-DCMAKE_EXE_LINKER_FLAGS=-static -L%s/lib" % stub])
        cmake_build(c, src["OPENVCL"], ["-DCMAKE_EXE_LINKER_FLAGS=-static"])
        return
    cmake_build(c, src["MASP"], [])
    cmake_build(c, src["OPENVCL"], ["-DCMAKE_EXE_LINKER_FLAGS=-static-libstdc++ -static-libgcc"])


def elf_info(path):
    with open(path, "rb") as f:
        head = f.read(20)
    if len(head) < 20 or head[:4] != b"\x7fELF":
        return None
    return int.from_bytes(head[16:18], "little"), int.from_bytes(head[18:20], "little")


def pe_machine(path):
    with open(path, "rb") as f:
        data = f.read(4096)
    if data[:2] != b"MZ" or len(data) < 64:
        return None
    off = int.from_bytes(data[60:64], "little")
    if data[off:off + 4] != b"PE\0\0":
        return None
    return int.from_bytes(data[off + 4:off + 6], "little")


def strip_and_check_windows(c):
    total, bad = 0, []
    for root, _, files in os.walk(c.ps2dev):
        for name in files:
            if not name.endswith((".exe", ".dll")):
                continue
            path = os.path.join(root, name)
            if os.path.islink(path):
                continue
            machine = pe_machine(path)
            if machine is None:
                continue
            if machine != c.p["machine"]:
                bad.append("wrong machine (0x%x): %s" % (machine, path))
                continue
            subprocess.run([c.p["strip"], "--strip-all", path], check=False)
            total += 1
    print("host PE files checked: %d" % total)
    if total == 0:
        sys.exit("no host binaries found")
    if bad:
        print("\n".join(bad[:40]))
        sys.exit("PACKAGE CHECK FAILED")
    print("PACKAGE CHECK OK")


def strip_and_check(c):
    if c.p["kind"] == "windows":
        strip_and_check_windows(c)
        return
    strip = c.p["strip"]
    readelf = c.p["readelf"]
    total, bad = 0, []
    for root, _, files in os.walk(c.ps2dev):
        for name in files:
            path = os.path.join(root, name)
            if os.path.islink(path) or name.endswith((".o", ".a")):
                continue
            info = elf_info(path)
            if info is None or info[0] not in (2, 3):
                continue
            if info[1] == 8:
                continue
            if info[1] != c.p["machine"]:
                bad.append("foreign architecture (%d): %s" % (info[1], path))
                continue
            subprocess.run([strip, "--strip-unneeded", path], check=False)
            total += 1
            if c.p["pie"] and info[0] == 2:
                bad.append("non-PIE: " + path)
            out = subprocess.run([readelf, "-d", path], capture_output=True, text=True).stdout
            for lib in re.findall(r"\(NEEDED\).*Shared library: \[(.*?)\]", out):
                if lib not in c.p["needed"]:
                    bad.append("%s <- %s" % (lib, path))
    print("host ELF files checked: %d" % total)
    if total == 0:
        sys.exit("no host binaries found")
    if bad:
        print("\n".join(bad[:40]))
        sys.exit("PACKAGE CHECK FAILED")
    print("PACKAGE CHECK OK")


def build(host_id, out, work):
    global WINDOWS_BUILD
    c = Ctx()
    c.p = make_profile(host_id)
    WINDOWS_BUILD = c.p["kind"] == "windows"
    c.ps2dev = os.path.abspath(out)
    c.work = os.path.abspath(work)
    c.native = os.path.abspath("native-ps2dev")
    c.deps = os.path.abspath("host-deps")
    c.source = []
    for d in (c.ps2dev, c.work, c.native, c.deps):
        fresh(d)
    os.environ["PS2DEV"] = c.ps2dev
    front = ["%s/ee/bin" % c.native, "%s/iop/bin" % c.native]
    if "path" in c.p:
        front.append(c.p["path"])
    os.environ["PATH"] = os.pathsep.join(front + [os.environ.get("PATH", "")])
    c.repos = {}
    for name, url in gcc_ps2.REPOS:
        folder = os.path.join(c.work, "ps2toolchain-" + name)
        run(["git", "clone", "--depth", "1", "-b", gcc_ps2.REF, url, folder])
        c.repos[name] = folder
        c.source.append("ps2toolchain-%s %s" % (name, gcc_ps2.capture(["git", "rev-parse", "HEAD"], folder)))
    build_deps(c)
    build_dvp(c)
    build_iop(c)
    build_ee(c)
    gcc_ps2.prune(c.ps2dev)
    gcc_ps2.finish(c.ps2dev)
    strip_and_check(c)
    with open(os.path.join(c.ps2dev, "SOURCE.txt"), "w") as f:
        f.write("host %s %s\n" % (host_id, c.p.get("note", "")))
        f.write("\n".join(c.source) + "\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", required=True, choices=HOST_IDS)
    p.add_argument("--out", required=True)
    p.add_argument("--work", default="gcc-ps2-work")
    a = p.parse_args()
    build(a.host, a.out, a.work)


if __name__ == "__main__":
    main()

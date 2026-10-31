import argparse, glob, os, sys

import common

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

NATIVE_DIR = "build-native"
NATIVE_TARGETS = ["llvm-tblgen", "llvm-min-tblgen", "clang-tblgen"]

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
    if kind == "windowsarm":
        return ["-DCMAKE_SYSTEM_NAME=Windows", "-DCMAKE_SYSTEM_PROCESSOR=ARM",
                "-DCMAKE_C_COMPILER=cl", "-DCMAKE_CXX_COMPILER=cl", "-DLLVM_USE_CRT_RELEASE=MT",
                "-DLLVM_HOST_TRIPLE=armv7-pc-windows-msvc", "-DLLVM_TARGET_ARCH=ARM",
                "-DLLVM_NATIVE_TOOL_DIR=" + os.path.abspath(os.path.join(NATIVE_DIR, "bin"))], True
    if kind == "macos":
        cpu = "arm64" if arch == "arm64" else "x86_64"
        return ["-DCMAKE_OSX_ARCHITECTURES=" + cpu, "-DCMAKE_OSX_DEPLOYMENT_TARGET=11.0"], False
    sys.exit("unknown kind " + kind)


PRUNE_FILES = ["clang-cl", "clang-cpp", "lld-link", "wasm-ld"]
PRUNE_FILES_WINDOWS = ["lld"]
PRUNE_HEADER_DIRS = ["cuda_wrappers", "llvm_libc_wrappers", "llvm_offload_wrappers",
                     "openmp_wrappers", "ppc_wrappers", "zos_wrappers"]
PRUNE_HEADER_GLOBS = ["__clang_cuda_*", "__clang_hip_*", "altivec.h", "riscv_*.h", "wasm_simd128.h",
                      "hvx_*.h", "hexagon_*.h", "msa.h", "amdgpuintrin.h", "nvptxintrin.h", "gpuintrin.h", "vecintrin.h", "htmintrin.h", "htmxlintrin.h", "ppc_*.h"]


def remove(path):
    if os.path.isdir(path) and not os.path.islink(path):
        import shutil
        shutil.rmtree(path)
    else:
        os.remove(path)
    print("removed " + path)


def prune(prefix, kind):
    names = list(PRUNE_FILES) + (PRUNE_FILES_WINDOWS if kind.startswith("windows") else [])
    for name in names:
        for cand in (name, name + ".exe"):
            path = os.path.join(prefix, "bin", cand)
            if os.path.lexists(path):
                remove(path)
    for inc in glob.glob(os.path.join(prefix, "lib", "clang", "*", "include")):
        for d in PRUNE_HEADER_DIRS:
            path = os.path.join(inc, d)
            if os.path.lexists(path):
                remove(path)
        for pattern in PRUNE_HEADER_GLOBS:
            for path in glob.glob(os.path.join(inc, pattern)):
                remove(path)


def build_native_tools(src, dry):
    llvm_src = os.path.join(src, "llvm")
    cfg = ["cmake", "-S", llvm_src, "-B", NATIVE_DIR, "-G", "Ninja"] + COMMON + [
        "-DCMAKE_C_COMPILER=cl", "-DCMAKE_CXX_COMPILER=cl", "-DLLVM_USE_CRT_RELEASE=MT"]
    if not dry:
        common.run(cfg)
        common.run(["cmake", "--build", NATIVE_DIR, "--target"] + NATIVE_TARGETS)


def build(kind, arch, src, work, out, dry):
    extra, no_strip = platform_args(kind, arch)
    llvm_src = os.path.join(src, "llvm")
    build_dir = os.path.abspath(work)
    prefix = os.path.abspath(out)
    cfg = ["cmake", "-S", llvm_src, "-B", build_dir, "-G", "Ninja"] + COMMON + extra + ["-DCMAKE_INSTALL_PREFIX=" + prefix]
    if not dry:
        common.run(cfg)
    target = "install-distribution" if no_strip else "install-distribution-stripped"
    if not dry:
        common.run(["cmake", "--build", build_dir, "--target", target])
    if not dry:
        prune(prefix, kind)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kind", required=True)
    p.add_argument("--arch", required=True)
    p.add_argument("--src", required=True)
    p.add_argument("--work", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--stage", default="build", choices=["build", "tools"])
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    if a.stage == "tools":
        build_native_tools(a.src, a.dry_run)
        return
    build(a.kind, a.arch, a.src, a.work, a.out, a.dry_run)


if __name__ == "__main__":
    main()

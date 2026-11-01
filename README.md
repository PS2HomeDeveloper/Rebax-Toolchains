# Rebax Toolchains

Rebax Toolchains provides prebuilt compiler toolchains used by the Rebax development environment.

The repository contains compiler packages built for supported host platforms and architectures, allowing Rebax to use the appropriate compiler when building projects for different target platforms.

## Overview

The repository provides three groups of toolchains:

- **Clang** — host-specific compiler toolchains for modern platforms, supporting cross-compilation for Windows, Linux, Android, macOS, and iOS.
- **GCC for PlayStation 1** — cross-compilation toolchains for console development.
- **GCC for PlayStation 2** — cross-compilation toolchains for console development.

Each toolchain package is published as a compressed `.tar.xz` archive through GitHub Releases.
## Supported Platforms

### Host Platforms

Host platforms determine where the compiler runs.

| Platform | Architectures |
|---|---|
| Android | arm64-v8a, armeabi-v7a, x86, x86_64 |
| Linux | arm, arm64, x86, x86_64 |
| Windows | arm, arm64, x86, x86_64 |
| macOS | arm64, x86_64 |

Actual availability depends on the published release assets.

### Target Platforms

Target platforms determine the architecture or system for which the compiler generates output.

Supported targets depend on the available toolchain packages and their corresponding SDKs.

## Package Naming

Compiler packages follow consistent naming conventions.

**Clang:**

```text
rebax-clang-<host>-<arch>.tar.xz

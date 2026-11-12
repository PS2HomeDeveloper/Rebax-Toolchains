# Rebax Toolchains

Prebuilt compilers for the [Rebax Engine](https://github.com/PS2HomeDeveloper/Rebax).

Rebax compiles the games you make into native programs. The compiler that does this work lives in the packages of this repository. The packages are built from upstream sources by GitHub Actions and published as release assets. Rebax downloads the ones it needs by itself, so most people never have to touch this repository.

## Packages

| Package | Used for | Hosts |
| --- | --- | --- |
| `rebax-clang-<host>.tar.xz` | Compiling for Android, Linux, Windows, macOS and iOS | Every supported host |
| `rebax-gcc-ps2-<host>.tar.xz` | Compiling for PlayStation 2 | Every supported host |
| `rebax-gcc-ps1-<host>.tar.xz` | Compiling for PlayStation 1 | Every supported host |

A host is the system Rebax runs on, written as `<platform>-<arch>`:

| Platform | Architectures |
| --- | --- |
| Android | `arm64-v8a`, `armeabi-v7a`, `x86`, `x86_64` |
| Linux | `arm64`, `arm`, `x86`, `x86_64` |
| Windows | `arm64`, `arm`, `x86`, `x86_64` |
| macOS | `arm64`, `x86_64` |

For example `rebax-clang-linux-x86_64.tar.xz` is the Clang package for a computer that runs Linux on an x86_64 processor.

One Clang package builds for every target. The libraries of each target come from the packages of [Rebax SDKs](https://github.com/PS2HomeDeveloper/Rebax-SDKs).

The layout of the packages is described in [docs/package_format.md](docs/package_format.md).

## Download

Packages are published in the latest release:

```
https://github.com/PS2HomeDeveloper/Rebax-Toolchains/releases/latest/download/rebax-clang-<host>.tar.xz
```

The release also contains `manifest.json`, which lists every package with its size and SHA-256 checksum. Rebax uses it to verify downloads.

## Manual installation

1. Download the package for your host from the latest release.
2. Extract it into the `toolchains` folder of Rebax.

Rebax treats a package as installed when its folder exists, so no other step is needed. To remove a package, delete its folder. The Clang package of the host that Rebax runs on cannot be removed from the package window, because Rebax needs it to build.

## Building the packages

See [docs/building_packages.md](docs/building_packages.md).

## License

This repository is released under the [MIT License](LICENSE). The packages contain software from other projects, each under its own license. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

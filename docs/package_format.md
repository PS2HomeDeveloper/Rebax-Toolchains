# Package format

## File names

```
rebax-clang-<host>.tar.xz
rebax-gcc-ps2-<host>.tar.xz
rebax-gcc-ps1-<host>.tar.xz
```

`<host>` is `<platform>-<arch>`, for example `windows-x86_64`. Each archive is compressed with xz and has exactly one top folder.

## Clang package

The top folder is `clang`. Extracted inside `toolchains`, it gives `toolchains/clang`.

The package contains the compiler and everything needed to run it on its own:

- `bin/clang`, the compiler driver, and the LLD linker that it uses.
- The compiler's own headers, which Rebax uses directly.

The package does not contain any C library or graphics library. These come from the SDK package of the target, which Rebax passes to the compiler as the sysroot.

## GCC packages for PlayStation

The PlayStation 1 and PlayStation 2 packages contain a GCC cross compiler and its tools for the MIPS processors of those consoles. Rebax installs them as `toolchains/gcc-ps1` and `toolchains/gcc-ps2`.

## Checksums

`manifest.json` in the release lists each package with its file name, size and SHA-256 checksum. A mismatch is reported as a warning by Rebax.

## Version

Rebax always downloads from the latest release. A new release replaces the packages as a whole.

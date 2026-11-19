# Third-Party Notices

The toolchain packages are built from the projects below. Each project keeps its own license, and the terms of that license apply to the files that come from it. The packages themselves are not licensed under this repository's MIT License.

| Project | Used for | License | Source |
| --- | --- | --- | --- |
| LLVM, Clang and LLD | Compiler and linker for Android, Linux, Windows, macOS and iOS | Apache License 2.0 with LLVM Exceptions | https://github.com/llvm/llvm-project |
| GCC 15.2.0 | C and C++ compiler for PlayStation 1 | GNU GPL 3.0 or later | https://gcc.gnu.org |
| GNU Binutils 2.45 | Assembler and linker for PlayStation 1 | GNU GPL 3.0 or later | https://www.gnu.org/software/binutils/ |
| ps2toolchain (dvp, iop, ee) | GCC and Binutils for the PlayStation 2 processors, with the patches of the ps2dev project | GNU GPL 3.0 or later, and the licenses of the ps2dev scripts and patches | https://github.com/ps2dev/ps2toolchain-ee, https://github.com/ps2dev/ps2toolchain-iop, https://github.com/ps2dev/ps2toolchain-dvp |

## Source code of the GPL programs

The GCC and Binutils programs in the packages are built unmodified from the upstream releases named above, together with the patches of the ps2dev project for the PlayStation 2. The build scripts in the `scripts` folder of this repository show exactly which sources and options were used.

You can obtain the complete corresponding source code from the upstream project pages in the table. If you cannot get it from there, open an issue in the [Rebax repository](https://github.com/PS2HomeDeveloper/Rebax/issues) and it will be provided.

## Programs you build

The GPL license of the compilers does not apply to the programs you compile with them. The runtime libraries that GCC adds to a program are covered by the GCC Runtime Library Exception.

## Reporting a mistake

If a project is missing or a license is described incorrectly, please open an issue in the [Rebax repository](https://github.com/PS2HomeDeveloper/Rebax/issues).

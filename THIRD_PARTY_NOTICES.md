# Third-Party Notices

The toolchain packages are built from the projects below. Each project keeps its own license, and the terms of that license apply to the files that come from it. The packages themselves are not licensed under this repository's MIT License.

| Project | Used for | License | Source |
| --- | --- | --- | --- |
| LLVM, Clang and LLD | Compiler and linker for Android, Linux, Windows, macOS and iOS | Apache License 2.0 with LLVM Exceptions | https://github.com/llvm/llvm-project |
| GCC 15.2.0 | C and C++ compiler for PlayStation 1 | GNU GPL 3.0 or later | https://gcc.gnu.org |
| GNU Binutils 2.45 | Assembler and linker for PlayStation 1 | GNU GPL 3.0 or later | https://www.gnu.org/software/binutils/ |
| GCC 15.2.0 (PlayStation 2 EE) | C and C++ compiler for the PlayStation 2 Emotion Engine, using the PlayStation 2 patches of the ps2dev project | GNU GPL 3.0 or later | https://gcc.gnu.org, patches: https://github.com/ps2dev/gcc |
| GNU Binutils 2.45 (PlayStation 2 EE, IOP, DVP) | Assembler and linker for the PlayStation 2 processors, using the PlayStation 2 patches of the ps2dev project | GNU GPL 3.0 or later | https://www.gnu.org/software/binutils/, patches: https://github.com/ps2dev/binutils-gdb |

## Source code of the GPL programs

The GCC and Binutils programs in the packages are built from the upstream GNU sources named above. For the PlayStation 2 processors the upstream sources do not support the target, so the packages use the patched sources of the ps2dev project (the repositories linked above), at the versions recorded in the `SOURCE.txt` file of each package. The build scripts in the `scripts` folder of this repository show exactly which sources and options were used.

You can obtain the complete corresponding source code from the upstream project pages in the table. If you cannot get it from there, open an issue in the [Rebax repository](https://github.com/PS2HomeDeveloper/Rebax/issues) and it will be provided.

## Programs you build

The GPL license of the compilers does not apply to the programs you compile with them. The runtime libraries that GCC adds to a program are covered by the GCC Runtime Library Exception.

## Reporting a mistake

If a project is missing or a license is described incorrectly, please open an issue in the [Rebax repository](https://github.com/PS2HomeDeveloper/Rebax/issues).

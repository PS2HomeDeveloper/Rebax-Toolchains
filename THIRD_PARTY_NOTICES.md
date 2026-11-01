# Third-Party Notices

Rebax Toolchains builds and distributes compiler toolchains using software
maintained by third parties. This file identifies the principal upstream
projects found in the repository's build configuration and packaging scripts.

The licenses below apply to the corresponding upstream components, not to
the Rebax Toolchains project as a whole. Each component retains its own
copyright, license, notices, and redistribution conditions.

When a toolchain archive contains upstream license or notice files, those
files must be kept with the archive. This document is a summary and does not
replace the original license texts.

## LLVM / Clang toolchains

The Clang build downloads the LLVM Project source archive. The workflow
currently defaults to LLVM 20.1.8 and builds the `clang`, `lld`, Clang resource
headers, and selected LLVM utilities (`llvm-ar`, `llvm-ranlib`, `llvm-nm`,
`llvm-objcopy`, and `llvm-strip`).

- Project: LLVM Project
- Upstream: https://github.com/llvm/llvm-project
- License: Apache License 2.0 with LLVM Exceptions for the majority of the
  project. Some files may remain under the legacy University of
  Illinois/NCSA Open Source License, and third-party subcomponents may have
  their own licenses.
- License information:
  - https://llvm.org/docs/DeveloperPolicy.html
  - https://github.com/llvm/llvm-project/blob/llvmorg-20.1.8/LICENSE.TXT
  - https://github.com/llvm/llvm-project/blob/llvmorg-20.1.8/clang/LICENSE.TXT

The LLVM Project's own `LICENSE.TXT`, component license files, and any
applicable third-party notices must be preserved in redistributed packages.
Do not describe these toolchains as Apple Clang: the build script downloads
the upstream LLVM Project and builds Clang; it does not download Apple's
proprietary Xcode compiler.

## GCC / PlayStation 2 toolchains

The PS2 build scripts obtain and build components from the PS2Dev toolchain
repositories. The resulting toolchain includes compiler and supporting
utilities for the EE, IOP, and DVP environments.

Principal upstream projects identified by the build scripts:

### GNU Binutils

- Upstream source: https://github.com/ps2dev/binutils-gdb
- Upstream project: https://www.gnu.org/software/binutils/
- License: generally GNU GPL version 3 or later, with file-specific exceptions
  and notices in the source tree.
- Preserve the upstream `COPYING*` files and file-level notices.

### GNU Compiler Collection (GCC)

- Upstream source: https://github.com/ps2dev/gcc
- Upstream project: https://gcc.gnu.org/
- License: GCC compiler components are generally GNU GPL version 3 or later.
  Certain GCC runtime-library files are covered by the GCC Runtime Library
  Exception, version 3.1, only where the relevant file carries that notice.
- License information:
  - https://gcc.gnu.org/onlinedocs/gcc/Copying.html
  - https://gcc.gnu.org/onlinedocs/libstdc++/manual/license.html
  - https://www.gnu.org/licenses/gcc-exception-3.1.html

The GCC Runtime Library Exception is not a blanket exception for every GCC
file. Check the notices attached to each component.

### Newlib

- Upstream source: https://github.com/ps2dev/newlib
- Upstream project: https://sourceware.org/newlib/
- License: Newlib is a collection of components with multiple licenses,
  including BSD-style licenses and other file-specific terms. The applicable
  notices are documented in `COPYING.NEWLIB` and in individual source files.
- License information: https://sourceware.org/newlib/

Keep `COPYING.NEWLIB` and all applicable file-level copyright and license
notices with redistributed Newlib components.

### pthread-embedded

- Upstream source: https://github.com/ps2dev/pthread-embedded
- License: follow the license file and copyright notices at the exact
  upstream revision used for each build. Do not assume that the license of
  the build orchestration repository automatically applies to the compiled
  pthread component.

### PS2Dev build and toolchain projects

The build scripts use these repositories to orchestrate the PS2 toolchain
build:

- https://github.com/ps2dev/ps2toolchain-ee
- https://github.com/ps2dev/ps2toolchain-iop
- https://github.com/ps2dev/ps2toolchain-dvp

These repositories identify their build scripts as MIT-licensed. Their
license applies to those repositories' own scripts; it does not replace the
licenses of Binutils, GCC, Newlib, or other software that the scripts build.

### DVP utilities

The DVP build also obtains and builds `masp` and `openvcl`.

- OpenVCL upstream: https://github.com/ps2dev/openvcl
- OpenVCL license: Academic Free License, version 2.0 (AFL-2.0), as stated
  by its upstream project.
- `masp`: the build configuration obtains this from the upstream repository
  specified by the DVP toolchain configuration. Preserve and follow the
  license and notices at the exact source revision used. The source snapshot
  reviewed for this notice did not contain the resolved `masp` repository
  URL or its license text, so its precise license is not asserted here.

## GCC build-time arithmetic libraries

The Android and Linux ARM GCC cross-build script downloads and builds these
libraries at fixed versions:

| Component | Version | License |
|---|---:|---|
| GNU GMP | 6.3.0 | LGPL-3.0-or-later or GPL-2.0-or-later, at the recipient's choice, as described by GMP |
| GNU MPFR | 4.2.1 | LGPL-3.0-or-later |
| GNU MPC | 1.3.1 | LGPL-3.0-or-later |

Upstream license information:

- GMP: https://gmplib.org/manual/Copying
- MPFR: https://www.mpfr.org/mpfr-4.2.1/mpfr.html
- MPC: https://www.multiprecision.org/

These libraries are build dependencies passed to GCC's configure process. The
build scripts use static builds for these dependencies. Whether and how their
code is incorporated into each resulting compiler executable depends on the
specific host build. If incorporated, the corresponding license and source
availability obligations apply to that distributed executable. Retain the
license texts and source corresponding to the exact versions used.

## Build-environment components

The workflow also installs or downloads tools used to build the packages,
including CMake, Ninja, GNU Make, MSYS2 packages, an Android NDK, and an
LLVM-MinGW archive for a Windows ARM cross-build.

These are build-environment dependencies. The reviewed scripts do not
explicitly copy the full Android NDK, LLVM-MinGW distribution, CMake, Ninja,
or the runner's MSVC/Xcode toolchains into the final toolchain prefix.
Their presence in the build environment alone does not mean they are
redistributed in the published toolchain archives. If a future workflow
starts bundling any of them, add their exact versions, license texts, and
notices here before publishing.

## Source and build provenance

The PS2 build scripts write a `SOURCE.txt` file into the generated toolchain
with source revisions and selected repository pins. Keep that file with the
published package. The exact source revision matters because upstream
repositories can change their dependencies, versions, and license notices.

The LLVM workflow currently selects its source version through the
`llvm_version` workflow input (default: `20.1.8`). Record the actual value
used for each published build.

## Important distribution notes

- Do not apply the repository's `LICENSE` to third-party compiler binaries or
  libraries.
- Do not remove upstream copyright headers, license files, or notices.
- For GPL-covered components distributed in binary form, satisfy the
  applicable source-code and written-offer/source-access requirements.
  Make the corresponding source code available in the manner required by
  the applicable GPL version.
- For LGPL-covered libraries, comply with the applicable source, relinking,
  and notice requirements when distributing binaries that include them.
- A toolchain may contain files under different licenses. The license of the
  main compiler does not automatically determine the license of every file
  in the archive.
- This document is a project-maintained inventory, not legal advice. Review
  the exact files and license notices in every generated archive and update
  this document whenever the build inputs or bundled components change.

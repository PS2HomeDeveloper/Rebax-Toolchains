# Building the packages

The packages are built in GitHub Actions and published as assets of a release. The workflows are in `.github/workflows`.

## Steps of a build

1. The compiler is built from the upstream sources, once for every host.
2. The result is packed into `rebax-<name>-<host>.tar.xz`. The archive has one top folder and is compressed with xz.
3. A SHA-256 checksum is computed for every archive.
4. The archives and an updated `manifest.json` are uploaded to the release.

## Checking a package

Extract the archive and check that the compiler starts on a machine of the same host. For a Clang package, running `clang --version` from the `bin` folder must print the version without errors.

## Adding a host

1. Add the host to the build list of the workflow, with a runner that can build for it.
2. Run the workflow.
3. Add the host to the package list of Rebax so it appears in the package window.

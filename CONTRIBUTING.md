# Contributing

This repository builds the compiler packages used by [Rebax Engine](https://github.com/PS2HomeDeveloper/Rebax). The general contributing guide and the Code of Conduct are in the Rebax repository:

- [Contributing to Rebax](https://github.com/PS2HomeDeveloper/Rebax/blob/main/CONTRIBUTING.md)
- [Code of Conduct](https://github.com/PS2HomeDeveloper/Rebax/blob/main/CODE_OF_CONDUCT.md)

Please report problems and ask questions in the Rebax repository. Issues are disabled here.

## Changes to this repository

- A package is built by a script in `scripts/`. Keep the scripts small and readable.
- Do not add compiled binaries to the repository. Packages are produced by the workflow from upstream sources.
- Describe how the change was tested in the pull request. The packages are built by the **Build toolchain packages** workflow, see [docs/building_packages.md](docs/building_packages.md).
- If a package starts to include new third-party software, add it to [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

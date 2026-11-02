import argparse

import gcc_ps1
import gcc_ps2
import gcc_ps2_cross


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--toolchain", required=True, choices=["gcc-ps1", "gcc-ps2"])
    p.add_argument("--host", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--work", default="gcc-work")
    a = p.parse_args()
    if a.toolchain == "gcc-ps1":
        gcc_ps1.build(a.host, a.out, a.work)
    elif a.host in gcc_ps2_cross.HOST_IDS:
        gcc_ps2_cross.build(a.host, a.out, a.work)
    else:
        gcc_ps2.build(a.out, a.work)


if __name__ == "__main__":
    main()

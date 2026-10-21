# Polyglot POCs

A polyglot is one file that is two file types at once, for example a picture that is also a script.
Each folder under `samples-poc-existing/` and `samples-home-baked/` builds one of them.

## Install everything (Ubuntu)

```
sudo apt install make python3 python3-pil gcc-mingw-w64-x86-64 default-jdk-headless dosfstools
sudo apt install file unzip 7zip wine imagemagick poppler-utils ffmpeg qemu-utils php-cli
make venv
```

The first line is enough to build. The second line is only for the checks.
`make venv` installs two Python packages (pycdlib and pyfatfs) into `.venv/`. The ISO and VHD examples need them.

## Build

```
make            # build and check every example
make build      # only build
make clean      # delete every out/ and work/
make -C samples-poc-existing/bmp-hta     # just one example (same commands)
```

## Every example looks the same

```
input/     the parts, one file each. Put your own files here, with the same names.
out/       the result
scripts/   the build and check scripts
src/       source code of the demo parts, if they are compiled
```

Each example's `README.md` says which files go into `input/` and what rules they must follow.

If Docker and the `am-lab-remnux` image are installed, some checks also run in that container. Otherwise they are skipped.

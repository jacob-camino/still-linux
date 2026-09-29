# Native Linux build preparation

`still-build.yml` is a manual, x64-only unsigned test build on the public fork's
standard `ubuntu-24.04` runners. It retains the upstream pinned Chromium,
official build flags, PGO preparation, sandbox configuration, source checks,
and checkpoint mechanism. It does not publish a GitHub release, upload to an
external service, use signing secrets, or select paid/self-hosted runners.

The workflow prepares the existing Debian Docker environment with Node 24,
limits concurrent compiler jobs to four, and continues timed-out compilation
through the existing ten-stage sequence. Docker image tar files are removed
after loading. Build checkpoints and unsigned packages have one-day artifact
retention; the shared Docker image remains for three days to cover later stages. Package names and checksum files identify Still. Packaging uses the
existing unsigned local path; upstream signed release workflows are unchanged.

The [capacity probe on September 29, 2026](https://github.com/jacob-camino/still-linux/actions/runs/36614573573)
measured 106.3 GiB free after the upstream runner cleanup, four CPUs, and about
16 GiB RAM. Preparation requires at least 100 GiB free before downloading
sources. The completed Mac tree was about 34.3 GiB locally; that is context,
not a Linux storage guarantee. Checkpoints temporarily need both the build
tree and its compressed archive; Docker and package staging also consume disk.
Link memory and total compile time remain unmeasured for this Linux build.

GitHub documents standard runners for public repositories as free. Its
documented runner storage floor is only 14 GB; future image capacity can differ
from this probe. Chromium documents at least 100 GB free disk and recommends
more than 16 GB RAM. The six-hour job limit still applies, so checkpoint export
must complete after each five-hour compile segment.

- [GitHub standard runner specifications](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [GitHub job limits](https://docs.github.com/en/actions/reference/limits)
- [Chromium Linux requirements](https://chromium.googlesource.com/chromium/src/+/main/docs/linux/build_instructions.md)

Capacity probes are not native build or runtime tests. A successful packaging
job would still produce test artifacts needing real browser/UI, extension
lifecycle, distro, and installation validation before publication.

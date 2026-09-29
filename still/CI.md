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
retention; the shared Docker image remains for seven days. The twelve jobs can
use up to 72 active hours, leaving four days for aggregate queue delays before
the Docker artifact expires. A rolling checkpoint can still expire if the next
stage waits more than a day. This does not cover GitHub's full 35-day workflow
limit. The inherited Linux upload uses `overwrite: true`, which removes the
previous checkpoint before uploading its replacement. An interrupted upload
therefore fails the job and may require a fresh build attempt. Package names and checksum files identify Still. Packaging uses the
existing unsigned local path; upstream signed release workflows are unchanged.

The [capacity probe on September 29, 2026](https://github.com/jacob-camino/still-linux/actions/runs/36614573573)
measured 106.3 GiB free after the upstream runner cleanup, four CPUs, and about
16 GiB RAM. Preparation requires at least 100 GiB free before downloading
sources. The completed Mac tree was about 34.3 GiB locally; that is context,
not a Linux storage guarantee. Checkpoints temporarily need both the build
tree and its compressed archive; Docker and package staging also consume disk.
Link memory and total compile time remain unmeasured for this Linux build.

GitHub documents standard runner compute for public repositories as free. Its
documented runner storage floor is only 14 GB; future image capacity can differ
from this probe. Chromium documents at least 100 GB free disk and recommends
more than 16 GB RAM. The six-hour job limit still applies, so checkpoint export
must complete after each five-hour compile segment.

The manual workflow uses the account's existing billing and cache settings. It
does not configure a payment method, raise a budget/cache limit, or enable paid
resources. GitHub documents that usage stops at the included quota when no
valid payment method is configured. If an artifact upload is rejected for
quota or billing, stop the attempt; do not enable paid usage to continue.

Free public runner compute does not establish that all artifact storage is
free. The billing docs describe pooled artifact allowances and hourly accrual
at $0.25 per GiB-month, without clearly confirming a public-artifact exemption.
The estimate below describes potential storage use, including if the account's
billing configuration changes later.

Pre-upload checks bound each checkpoint archive to 50 GiB, the Docker image tar
to 10 GiB, and the final packages together to 5 GiB. An oversized artifact fails
before upload. There are at most eleven checkpoint uploads (prep plus ten build
stages). Conservatively counting every checkpoint for its entire one-day
retention, ignoring early replacement and the free allowance, gives:

`11 × 50 × 1 + 10 × 7 + 5 × 1 = 625 GiB-days`

At the documented monthly rate, that is $5.21 for a 30-day month, or $5.59 using
a conservative 28-day month. A $6 one-run storage allowance leaves a small margin
for archive metadata and rounding. This is an estimate, not an account billing
cap; it excludes tax, other account usage, and any additional workflow attempts.
The shared compiler cache is separate: GitHub includes 10 GiB per repository,
and this workflow does not increase that limit. It cannot determine the
account's effective billing allowance or enforce an account-wide spend cap. Pricing was checked on September 29, 2026.

- [GitHub standard runner specifications](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [GitHub job limits](https://docs.github.com/en/actions/reference/limits)
- [Chromium Linux requirements](https://chromium.googlesource.com/chromium/src/+/main/docs/linux/build_instructions.md)

Capacity probes are not native build or runtime tests. A successful packaging
job would still produce test artifacts needing real browser/UI, extension
lifecycle, distro, and installation validation before publication.

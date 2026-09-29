# Still Linux integration

This personal Helium fork adds the Ink Margin interface, larger left tabs,
grayscale pages with a hover/focus color toggle, separate product identities,
and the same signed local website controls as the Mac build. No Linux browser
binary, AppImage, Debian package, or signed release has been built or tested.
No paid build host or release workflow has been started.

The pinned base is Helium Chromium `b38c4bdd2ecbe5c680dc3c5d464a2edc84d49d4c`,
Chromium `154.0.8037.57`. `scripts/shared.sh` applies `still/apply.py` after
upstream patches, substitutions, translations, and resources. The helper
checks the pinned version, validates the signed blocker against its reviewed
sources, checks all pending patches together, and applies them idempotently.
Extracted source trees inside the outer repository are supported.

## Identity and scope

The launcher and desktop entry are `still` and `still.desktop`. The default
profile is `$XDG_CONFIG_HOME/com.jacobcamino.still`, falling back to
`~/.config/com.jacobcamino.still`; upstream development builds add `.dev`.
`STILL_CONFIG_HOME` and `STILL_DESKTOP` replace the corresponding Helium
environment overrides. Packages install under `/opt/still` and use
`com.jacobcamino.still` for AppStream identity.

Internal `helium`, `helium_crashpad_handler`, and compatibility `chrome` names
remain unchanged. Author attribution, translated prose, and existing icon art
are retained. The AppArmor changes only rename profiles, local include paths,
and executable paths; permission rules and bootstrap behavior are unchanged.
Upstream browser flags, sandbox behavior, policy rules, and signing logic remain
unchanged. The optional blocker uses normal signed extension permissions.

The shared UI, blocker, and product-string patches and all tracked blocker assets
are byte-identical to the Mac fork. An AI model is not bundled or enabled.

## Build and package

On a Linux build host with Docker, from the repository root:

```sh
git submodule update --init --recursive
scripts/docker-build.sh -c --pgo
package/docker-package.sh
```

The upstream clone path is needed when the pinned source archive is unavailable.
PGO profiles are supported for x64 by the upstream build helper. Set `ARCH=arm64`
for ARM64; the upstream helper retains its own ARM64 toolchain/PGO handling.
Set `MAKE_DEB=1` for the optional Debian package. The package script verifies
the exact signed blocker in the build output before assembling any release.

Expected outputs under `build/release/` are
`Still-<version>-linux-<x64|arm64>.tar.xz`, `.AppImage`, and optionally `.deb`.
They are not available yet. A resumed compile should use the existing output
directory; `scripts/build.sh` deliberately removes `out/` at the beginning.
The developer quilt helpers are inherited maintenance tools; Still overlays
must be accounted for before manually unapplying upstream patches.

AppImage update metadata points to the personal `jacob-camino/still-linux`
GitHub releases. No Still update assets or signing key have been published.
The inherited Helium repository key and package repositories do not sign or
distribute Still. The upstream signature routines require Still-owned signing
credentials before a signed release can be produced. Binary release publishing
also needs the matching source revision and license notices.

## Validation

On a prepared source tree, these checks do not require a Linux runtime:

```sh
python3 still/apply.py --source build/src --check-only
STILL_LINUX_FIXTURE=build/src python3 -m unittest discover -s still/tests -v
node --test still/blocking/tests/core.test.mjs
```

Five integration tests passed on macOS using a selected-file fixture rebuilt
from the exact Chromium commit and 67 ordered Helium core/Linux patches. They
cover all four Still patches and repeat application under an outer Git
repository, unchanged AppArmor permission semantics and browser flags,
desktop/AppStream identities, rejection of missing/corrupt blocker output, and
the real packaging script's tar/launcher/blocker placement with fake binaries
and a fake AppImage tool. The five copied blocker unit tests also pass.

Those fixture artifacts are not releases. Native Linux x64/ARM64 compilation,
real AppImage/Debian tooling, distro dependencies and AppArmor behavior,
first-profile extension installation, default-browser registration, grayscale
rendering, and uninstall/coexistence still need runtime validation.

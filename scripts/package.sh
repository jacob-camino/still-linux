#!/usr/bin/env bash
set -euo pipefail

_current_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
_root_dir="$(cd "$_current_dir/.." && pwd)"
_build_dir="$_root_dir/build"
_release_dir="$_build_dir/release"
_app_dir="$_release_dir/Still.AppDir"

_app_name="Still"
_version=$(python3 "$_root_dir/helium-chromium/utils/helium_version.py" \
                   --tree "$_root_dir/helium-chromium" \
                   --platform-tree "$_root_dir" \
                   --print)

_arch=$(cat "$_build_dir/src/out/Default/args.gn" \
                | grep ^target_cpu \
                | tail -1 \
                | sed 's/.*=//' \
                | cut -d'"' -f2)

case "$_arch" in
    x64|arm64) ;;
    *) echo "Unsupported Still package architecture: $_arch" >&2; exit 1 ;;
esac

_release_name="$_app_name-$_version-linux-$_arch"
_update_info="gh-releases-zsync|jacob-camino|still-linux|latest|$_app_name-*-linux-$_arch.AppImage.zsync"
_tarball_name="${_release_name}"
_tarball_dir="$_release_dir/$_tarball_name"

_files="helium
chrome_100_percent.pak
chrome_200_percent.pak
helium_crashpad_handler
chromedriver
icudtl.dat
libEGL.so
libGLESv2.so
libqt5_shim.so
libqt6_shim.so
libvk_swiftshader.so
libvulkan.so.1
product_logo_256.png
resources.pak
v8_context_snapshot.bin
vk_swiftshader_icd.json
xdg-mime
xdg-settings"

python3 "$_root_dir/still/verify-package-inputs.py" --source "$_build_dir/src"

echo "copying release files and creating $_tarball_name.tar.xz"

rm -rf "$_tarball_dir"
mkdir -p "$_tarball_dir"

for file in $_files; do
    cp -r "$_build_dir/src/out/Default/$file" "$_tarball_dir" &
done

mkdir -p "$_tarball_dir/resources"
cp "$_build_dir/src/out/Default/resources/still-blocking.crx" "$_tarball_dir/resources/"
cp "$_root_dir/LICENSE" "$_tarball_dir/LICENSE.helium-linux"
cp "$_root_dir/LICENSE.ungoogled_chromium" "$_tarball_dir/"
cp "$_build_dir/src/LICENSE" "$_tarball_dir/LICENSE.chromium"

mkdir -p "$_tarball_dir/locales"
cp "$_build_dir/src/out/Default/locales/"*.pak "$_tarball_dir/locales/"

cp "$_root_dir/package/still.desktop" "$_tarball_dir"
cp "$_root_dir/package/apparmor.cfg" "$_tarball_dir"
cp "$_root_dir/package/still-wrapper.sh" "$_tarball_dir/still-wrapper"

wait
(cd "$_tarball_dir" && ln -sf helium chrome)

_syms_zip="$_release_dir/${_release_name}_symbols.zip"
rm -f "$_syms_zip"
find "$_tarball_dir" -type f -exec file {} + \
    | awk -F: '/ELF/ {print $1}' \
    | sed "s|^$_tarball_dir/||" \
    | (cd "$_build_dir/src/out/Default" && zip -q "$_syms_zip" -@)

if command -v eu-strip >/dev/null 2>&1; then
    _strip_cmd=eu-strip
else
    _strip_cmd="strip --strip-unneeded"
fi

find "$_tarball_dir" -type f -exec file {} + \
    | awk -F: '/ELF/ {print $1}' \
    | xargs $_strip_cmd

_size="$(du -sk "$_tarball_dir" | cut -f1)"

pushd "$_release_dir"

TAR_PATH="$_release_dir/$_tarball_name.tar.xz"
tar vcf - "$_tarball_name" \
    | pv -s"${_size}k" \
    | xz -e9 > "$TAR_PATH" &

# create AppImage
rm -rf "$_app_dir"
mkdir -p "$_app_dir/opt/still/" "$_app_dir/usr/share/icons/hicolor/256x256/apps/"
cp -r "$_tarball_dir"/* "$_app_dir/opt/still/"
cp "$_root_dir/package/still.desktop" "$_app_dir"

cp "$_root_dir/package/still-wrapper-appimage.sh" "$_app_dir/AppRun"

for out in "$_app_dir/still.png" "${_app_dir}/usr/share/icons/hicolor/256x256/apps/still.png"; do
    cp "${_app_dir}/opt/still/product_logo_256.png" "$out"
done

export APPIMAGETOOL_APP_NAME="Still"
export VERSION="$_version"

# check whether CI GPG secrets are available
if [[ -n "${GPG_PRIVATE_KEY:-}" && -n "${GPG_PASSPHRASE:-}" ]]; then
    echo "$GPG_PRIVATE_KEY" | gpg --batch --import --passphrase "$GPG_PASSPHRASE"
    export APPIMAGETOOL_SIGN_PASSPHRASE="$GPG_PASSPHRASE"
fi

appimagetool \
    -u "$_update_info" \
    "$_app_dir" \
    "$_release_name.AppImage" "$@" &
popd
wait

if [ "${MAKE_DEB:-0}" = 1 ]; then
    "$_root_dir/package/mkdeb.sh" "$TAR_PATH"
fi

if [ -n "${SIGN_TARBALL:-}" ]; then
    gpg --batch --pinentry-mode loopback \
        --detach-sign --passphrase "$GPG_PASSPHRASE" \
        --output "$TAR_PATH.asc" "$TAR_PATH"
fi

rm -rf "$_tarball_dir" "$_app_dir"

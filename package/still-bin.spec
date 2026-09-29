%define version 0.18.1.1
%global debug_package %{nil}

Name:    still-bin
Summary: A quiet browser based on Helium
Version: %{version}
Release: 1%{?dist}
Group:   web
License: GPL-3.0
URL:     https://github.com/jacob-camino/still-linux
Source0: https://github.com/jacob-camino/still-linux/releases/download/%{version}/Still-%{version}-linux-x64.tar.xz
Source1: https://github.com/jacob-camino/still-linux/releases/download/%{version}/Still-%{version}-linux-arm64.tar.xz
Source2: com.jacobcamino.still.metainfo.xml

%if 0%{?debbuild}
Packager: Jacob Schmidt
Provides: www-browser
%endif

# Based on chrome/installer/linux/{debian,rpm}/additional_deps
# We do not recommend libgtk* because we don't use it by default.
# If the user wants GTK, they can install the relevant lib
# (and they already likely have them installed by default on a desktop install anyways).
Recommends: ca-certificates, xdg-utils
%if 0%{?debbuild}
Recommends: fonts-liberation, libvulkan1
%else
Recommends: liberation-fonts, vulkan-loader
%endif

%description
Still is a personal fork of Helium and Chromium with an Ink interface, grayscale pages, and local site controls.

%prep
%ifarch x86_64 amd64
%setup -q -n Still-%{version}-linux-x64
%endif

%ifarch aarch64 arm64
%setup -q -T -b 1 -n Still-%{version}-linux-arm64
%endif

%build
# We are using prebuilt binaries

%install
%define still_base /opt/still
%define stilldir %{buildroot}%{still_base}

mkdir -p %{stilldir} \
         %{buildroot}%{_bindir} \
         %{buildroot}%{_datadir}/applications \
         %{buildroot}%{_datadir}/metainfo \
         %{buildroot}%{_datadir}/icons/hicolor/256x256/apps

cp -a . %{stilldir}

%if 0%{?debbuild}
sed -Ei "s/(CHROME_VERSION_EXTRA=).*/\1deb/" \
    %{stilldir}/still-wrapper
%else
sed -Ei "s/(CHROME_VERSION_EXTRA=).*/\1rpm/" \
    %{stilldir}/still-wrapper
%endif

install -m 644 product_logo_256.png \
    %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/still.png

install -m 644 %{stilldir}/still.desktop \
    %{buildroot}%{_datadir}/applications/

install -m 644 %{SOURCE2} \
    %{buildroot}%{_datadir}/metainfo/com.jacobcamino.still.metainfo.xml

ln -sf %{still_base}/still-wrapper \
    %{buildroot}%{_bindir}/still

%files
%defattr(-,root,root,-)
%{still_base}/
%{_bindir}/still
%{_datadir}/applications/still.desktop
%{_datadir}/metainfo/com.jacobcamino.still.metainfo.xml
%{_datadir}/icons/hicolor/256x256/apps/still.png

%post
# Refresh icon cache and update desktop database
/usr/bin/update-desktop-database > /dev/null 2>&1 || :
/bin/touch --no-create %{_datadir}/icons/hicolor > /dev/null 2>&1 || :

if command -v apparmor_parser > /dev/null 2>&1 && [ -d /etc/apparmor.d ]; then
    cp %{still_base}/apparmor.cfg /etc/apparmor.d/still-bin
    apparmor_parser -r -W -T /etc/apparmor.d/still-bin || :
fi

%postun
# Refresh icon cache and update desktop database
/usr/bin/update-desktop-database > /dev/null 2>&1 || :
case "$1" in
    0|remove|purge)
        /bin/touch --no-create %{_datadir}/icons/hicolor > /dev/null 2>&1
        /usr/bin/gtk-update-icon-cache %{_datadir}/icons/hicolor > /dev/null 2>&1 || :

        if [ -f /etc/apparmor.d/still-bin ]; then
            if command -v apparmor_parser > /dev/null 2>&1; then
                apparmor_parser -R /etc/apparmor.d/still-bin || :
            fi
            rm -f /etc/apparmor.d/still-bin
        fi
        ;;
esac

%posttrans
/usr/bin/gtk-update-icon-cache %{_datadir}/icons/hicolor > /dev/null 2>&1 || :

%changelog
%if "%{_vendor}" != "debbuild"
%autochangelog
%endif

#!/usr/bin/python3

import os
import pathlib
import shutil
import sys
import tarfile
import argparse
from typing import Final, Callable, TextIO, Optional

CHUNK_SIZE: Final[int] = 8192
VERSION_EPOCH: Final[str] = "1"


def progress(count: int, total: int, prefix: str = '', suffix: str = ''):
    bar_len = shutil.get_terminal_size((40, 0)).columns - 14 - len(suffix)
    if prefix:
        bar_len -= len(prefix) + 1
    filled_len = int(bar_len * count / total)

    percents = round(100.0 * count / total, 1)
    bar = '=' * filled_len + '>' + ' ' * (bar_len - filled_len - 1)

    sys.stdout.write(f"{prefix} [{bar}] {percents}% ...{suffix}\r")
    sys.stdout.flush()


def _download_python(url: str, file_name: str):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        content_length: Optional[str] = response.headers.get("Content-Length", None)
        if content_length:
            content_length: Optional[int] = int(content_length)
            show_progress = True
        else:
            show_progress = False
        count = 0

        with open(file_name, 'wb') as file:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:  # Filter out keep-alive new chunks
                    file.write(chunk)
                    count += len(chunk)
                    if show_progress:
                        progress(count, content_length, f"Downloading {file_name}")
        if show_progress:
            progress(count, content_length, f"Downloading {file_name}")
            print()

    except requests.RequestException as e:
        print("Failed to download '%s' with error: %s" % (file_name, str(e)))
    except KeyboardInterrupt:
        print("Download interrupted by user")
        sys.exit(0)


def _download_wget(url: str, file_name: str):
    code = os.system("wget '%s' -O %s" % (url, file_name))
    if code != 0 or not os.path.exists(file_name):
        sys.exit(1)


try:
    import requests

    download: Callable[[str, str], None] = _download_python
except ImportError:
    download: Callable[[str, str], None] = _download_wget


def main():
    parser = argparse.ArgumentParser(description="Linux Mint Thunderbird downloader")
    parser.add_argument("-a", "--archi", type=str, help="Architecture type", choices=["x86_64", "amd64", "x86"],
                        required=True)
    parser.add_argument("-d", "--directory", type=str, help="Directory to download to", default=os.getcwd())
    parser.add_argument("-v", "--version", type=str, help="Version", required=True)
    parser.add_argument("-n", "--abort", type=bool, default=False)
    args = parser.parse_args()

    curdir: str = args.directory
    abort: bool = args.abort
    version: str = args.version
    archi: str = args.archi
    archi = "linux-x86_64" if archi == "amd64" or archi == "x86_64" else "linux-i686"
    if curdir.startswith("."):
        curdir = os.getcwd() + curdir[1:]

    release = version
    lmde = False
    if "+" in version:
        release = version.split("+")[0]
    elif "~" in version:
        release = version.split("~")[0]
        lmde = True

    release_for_urls = release.removeprefix("%s:" % VERSION_EPOCH)

    remove_thunderbird_prefixes = [entry
                                   for entry in os.scandir("%s/debian" % curdir)
                                   if entry.is_dir() and entry.name.startswith("thunderbird")
                                   ]
    for entry in remove_thunderbird_prefixes:
        shutil.rmtree(entry)
    print("Removed dirs/files: %s" % ", ".join(entry.name for entry in remove_thunderbird_prefixes))

    pathlib.Path("%s/debian/thunderbird/usr/lib" % curdir).mkdir(parents=True, exist_ok=True)
    os.chdir("%s/debian/thunderbird/usr/lib" % curdir)
    if not abort:
        download_thunderbird_archive(curdir, archi, release_for_urls)

    locale_prefix = "thunderbird-" + "l10n" if lmde else "locale"
    with open(os.path.join(curdir, "locales.shipped")) as f:
        codes = read_codes(f)

    print("Parsed thunderbird locales"
          ", starting download" if len(codes) > 0 else "")

    xpi_url = "https://download-origin.cdn.mozilla.net/pub/thunderbird/releases/%s/%s/xpi" % (release_for_urls, archi)
    for xpi, package_code in codes.items():
        extension_dir = ("%s/debian/%s-%s/usr/lib/thunderbird/distribution/extensions" % (
            curdir, locale_prefix, package_code))
        pathlib.Path(extension_dir).mkdir(parents=True, exist_ok=True)
        os.chdir(extension_dir)

        if abort:
            continue
        file_name = "%s.xpi" % xpi
        download("%s/%s.xpi" % (xpi_url, xpi), file_name)
        shutil.move("%s.xpi" % xpi, "langpack-%s@thunderbird.mozilla.org.xpi" % xpi)

    print("Done.")
    os.chdir(curdir)


def read_codes(text_io: TextIO) -> dict:
    codes = dict(())
    for line in text_io:
        if line.startswith("#"):
            continue

        splits = line.split(":")
        if len(splits) < 2:
            continue

        xpi_name, pkg_name = splits[0], splits[1]
        if "-mac" in xpi_name:
            continue

        pkg_name = pkg_name.replace("\n", "")
        codes[xpi_name] = pkg_name
    return codes


def download_thunderbird_archive(curdir: str, archi: str, release_for_urls: str):
    us_url = "https://download-origin.cdn.mozilla.net/pub/thunderbird/releases/%s/%s/en-US/thunderbird-%s.tar.bz2" % (
        release_for_urls, archi, release_for_urls)

    file_name = "thunderbird-%s.tar.bz2" % release_for_urls
    download(us_url, file_name)
    print(f"Extracting {file_name}")
    with tarfile.open(file_name) as tf:
        tf.extractall(".")

    os.remove("thunderbird-%s.tar.bz2" % release_for_urls)
    pathlib.Path("%s/debian/thunderbird/usr/lib/thunderbird/distribution" % curdir).mkdir(parents=True,
                                                                                          exist_ok=True)
    shutil.copy(os.path.join(curdir, "pref", "policies.json"),
                "%s/debian/thunderbird/usr/lib/thunderbird/distribution" % curdir)
    pathlib.Path("%s/debian/thunderbird/usr/share/icons/hicolor" % curdir).mkdir(parents=True, exist_ok=True)
    os.chdir("%s/debian/thunderbird/usr/share/icons/hicolor" % curdir)
    for entry in ["16x16/apps", "22x22/apps", "24x24/apps", "32x32/apps", "48x48/apps", "64x64/apps",
                  "128x128/apps", "256x256/apps"]:
        pathlib.Path(entry).mkdir(parents=True, exist_ok=True)
    os.symlink("/usr/lib/thunderbird/chrome/icons/default/default16.png", "16x16/apps/thunderbird.png")
    os.symlink("/usr/lib/thunderbird/chrome/icons/default/default22.png", "22x22/apps/thunderbird.png")
    os.symlink("/usr/lib/thunderbird/chrome/icons/default/default24.png", "24x24/apps/thunderbird.png")
    os.symlink("/usr/lib/thunderbird/chrome/icons/default/default32.png", "32x32/apps/thunderbird.png")
    os.symlink("/usr/lib/thunderbird/chrome/icons/default/default48.png", "48x48/apps/thunderbird.png")
    os.symlink("/usr/lib/thunderbird/chrome/icons/default/default64.png", "64x64/apps/thunderbird.png")
    os.symlink("/usr/lib/thunderbird/chrome/icons/default/default128.png", "128x128/apps/thunderbird.png")
    os.symlink("/usr/lib/thunderbird/chrome/icons/default/default256.png", "256x256/apps/thunderbird.png")


if __name__ == "__main__":
    main()

#!/usr/bin/python3

import os
import pathlib
import shutil
import sys
import tarfile
import argparse
from typing import Final, Callable

CHUNK_SIZE: Final[int] = 8192


def _download_python(url: str, filename: str):
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(filename, 'wb') as file:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                file.write(chunk)
    except requests.RequestException as e:
        print("Failed to download '%s' with error: %s" % (filename, str(e)))


def _download_wget(url: str, filename: str):
    code = os.system("wget '%s' -O %s" % (url, filename))
    if code != 0 or not os.path.exists(file_name):
        sys.exit(1)


try:
    import requests

    download: Callable[[str, str], None] = _download_python
except ImportError:
    download: Callable[[str, str], None] = _download_wget

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

VERSION_EPOCH = "1"

release = version
lmde = False
if "+" in version:
    release = version.split("+")[0]
if "~" in version:
    release = version.split("~")[0]
    lmde = True

release_for_urls = release.removeprefix("%s:" % VERSION_EPOCH)

US_URL = "https://download-origin.cdn.mozilla.net/pub/thunderbird/releases/%s/%s/en-US/thunderbird-%s.tar.bz2" % (
    release_for_urls, archi, release_for_urls)
XPI_URL = "https://download-origin.cdn.mozilla.net/pub/thunderbird/releases/%s/%s/xpi" % (release_for_urls, archi)

thunderbird_dir = [entry
                   for entry in os.scandir("%s/debian" % curdir)
                   if entry.is_dir() and entry.name.startswith("thunderbird")
                   ]
for entry in thunderbird_dir:
    shutil.rmtree(entry)
pathlib.Path("%s/debian/thunderbird/usr/lib" % curdir).mkdir(parents=True, exist_ok=True)
os.chdir("%s/debian/thunderbird/usr/lib" % curdir)
if not abort:
    file_name = "thunderbird-%s.tar.bz2" % release_for_urls
    download(US_URL, file_name)

    with tarfile.open("thunderbird-%s.tar.bz2" % release_for_urls) as tf:
        tf.extractall(".")
    os.remove("thunderbird-%s.tar.bz2" % release_for_urls)
    pathlib.Path("%s/debian/thunderbird/usr/lib/thunderbird/distribution" % curdir).mkdir(parents=True, exist_ok=True)
    shutil.copy(os.path.join(curdir, "pref", "policies.json"),
                "%s/debian/thunderbird/usr/lib/thunderbird/distribution" % curdir)
    pathlib.Path("%s/debian/thunderbird/usr/share/icons/hicolor" % curdir).mkdir(parents=True, exist_ok=True)
    os.chdir("%s/debian/thunderbird/usr/share/icons/hicolor" % curdir)
    for entry in ["16x16/apps", "22x22/apps", "24x24/apps", "32x32/apps", "48x48/apps", "64x64/apps", "128x128/apps",
                  "256x256/apps"]:
        pathlib.Path(entry).mkdir(parents=True, exist_ok=True)

    os.symlink("/usr/lib/thunderbird/chrome/icons/default/default16.png", "16x16/apps/thunderbird.png")
    os.symlink("/usr/lib/thunderbird/chrome/icons/default/default22.png", "22x22/apps/thunderbird.png")
    os.symlink("/usr/lib/thunderbird/chrome/icons/default/default24.png", "24x24/apps/thunderbird.png")
    os.symlink("/usr/lib/thunderbird/chrome/icons/default/default32.png", "32x32/apps/thunderbird.png")
    os.symlink("/usr/lib/thunderbird/chrome/icons/default/default48.png", "48x48/apps/thunderbird.png")
    os.symlink("/usr/lib/thunderbird/chrome/icons/default/default64.png", "64x64/apps/thunderbird.png")
    os.symlink("/usr/lib/thunderbird/chrome/icons/default/default128.png", "128x128/apps/thunderbird.png")
    os.symlink("/usr/lib/thunderbird/chrome/icons/default/default256.png", "256x256/apps/thunderbird.png")

locale_prefix = "thunderbird-" + "l10n" if lmde else "locale"

codes = {}
with open(os.path.join(curdir, "locales.shipped")) as f:
    for line in f:
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

for xpi, package_code in codes.items():
    extension_dir = ("%s/debian/%s-%s/usr/lib/thunderbird/distribution/extensions" % (
        curdir, locale_prefix, package_code))
    pathlib.Path(extension_dir).mkdir(parents=True, exist_ok=True)
    os.chdir(extension_dir)

    if abort:
        continue
    file_name = "%s.xpi" % xpi
    download("%s/%s.xpi" % (XPI_URL, xpi), file_name)
    shutil.move("%s.xpi" % xpi, "langpack-%s@thunderbird.mozilla.org.xpi" % xpi)

os.chdir(curdir)

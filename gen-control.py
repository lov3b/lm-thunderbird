#!/usr/bin/python3
import argparse
import os
from typing import Final, List, TextIO, Tuple

SNAP_REPLACEMENTS: Final[List[str]] = [
    "thunderbird-locale-bn",
    "thunderbird-locale-bn-bd",
    "thunderbird-locale-en-gb",
    "thunderbird-locale-en-us",
    "thunderbird-locale-es-ar",
    "thunderbird-locale-es-es",
    "thunderbird-locale-fa",
    "thunderbird-locale-fy-nl",
    "thunderbird-locale-ga-ie",
    "thunderbird-locale-mk",
    "thunderbird-locale-nb-no",
    "thunderbird-locale-nn-no",
    "thunderbird-locale-pa-in",
    "thunderbird-locale-pt-br",
    "thunderbird-locale-pt-pt",
    "thunderbird-locale-si",
    "thunderbird-locale-sv-se",
    "thunderbird-locale-ta",
    "thunderbird-locale-ta-lk",
    "thunderbird-locale-zh-cn",
    "thunderbird-locale-zh-tw",
]

LOCALE_PREFIX: Final[str] = "thunderbird-locale"


def main():
    parser = argparse.ArgumentParser(description="Linux Mint Thunderbird Control Generator")
    parser.add_argument("-d", "--directory", type=str, help="Directory to download to", default=os.getcwd())
    args = parser.parse_args()

    curdir = args.directory

    # Load code:Name list to popular control descriptions
    with open(os.path.join(curdir, "locales.all")) as file:
        locale_name_dict = parse_lang_codes(file)

    with open(os.path.join(curdir, "locales.shipped")) as file:
        shipped_packages, xpi_locale_map = parse_packages(file)

    control_locales = ""

    print("\nGenerating %s entries for control file...\n")

    for pkg in shipped_packages:
        if len(pkg.provides) != 0:
            provide_str = "\nProvides: " + ", ".join(pkg.provides)
        else:
            provide_str = ""
        control_locales += ShippedTemplate.get_control_locale(locale_name_dict, pkg, provide_str)

    for t_package_name in SNAP_REPLACEMENTS:
        control_locales += TransitionalPackage.get_control_locale(t_package_name)

    with open(os.path.join(curdir, "debian", "control"), "w") as file:
        control = ""
        with open(os.path.join(curdir, "debian", "control.in"), "r") as ini:
            control += ini.read()

        control += control_locales
        file.write(control)

    print("\nDone generating control file...\n")

    os.chdir(curdir)


class Pkg:
    pkg_name: str
    provides: list
    replaces: list

    def __init__(self, pkg_name: str):
        self.pkg_name = pkg_name
        self.provides = []
        self.replaces = []


class ShippedTemplate:
    SHIPPED_TEMPLATE: Final[str] = """
    Package: %s-%s
    Architecture: all
    Depends: ${misc:Depends}%s
    Description: %s language packs for Thunderbird
     %s language packs for the Mozilla Thunderbird Mail Client.
    """

    @staticmethod
    def get_control_locale(locale_name_dict: dict, pkg: Pkg, provide: str) -> str:
        locale_name = locale_name_dict[pkg.pkg_name]
        return ShippedTemplate.SHIPPED_TEMPLATE % (LOCALE_PREFIX, pkg.pkg_name, provide, locale_name, locale_name)


class TransitionalPackage:
    TRANSITIONAL_TEMPLATE: Final[str] = """
    Package: %s
    Architecture: all
    Description: Transitional package for Thunderbird language packs.
     .
     This is an empty transitional package to ensure a clean upgrade
     process. You can safely remove this package after installation.
    """

    @staticmethod
    def get_control_locale(t_package_name: str) -> str:
        return TransitionalPackage.TRANSITIONAL_TEMPLATE % (t_package_name,)


def parse_lang_codes(file: TextIO) -> dict:
    locale_name_dict = dict()
    for line in file:
        if line.startswith("#"):
            continue
        code, lang = line.split(":")
        locale_name_dict[code] = lang.replace("\n", "")
    return locale_name_dict


def parse_packages(f: TextIO) -> Tuple[List[Pkg], dict]:
    shipped_packages = []
    xpi_locale_map = dict()

    current_pkg = Pkg("")
    for line in f:
        if line.startswith("#"):
            continue
        line = line.replace("\n", "")
        print(line)

        splits = line.split(":")
        if len(splits) == 2:
            xpi_name, pkg_name, no_provide = splits[0], splits[1], False
        elif len(splits) == 3:
            xpi_name, pkg_name, no_provide = splits[0], splits[1], True
        else:
            continue

        pkg_name = pkg_name.replace("\n", "")
        xpi_locale_map[xpi_name] = pkg_name

        if pkg_name != current_pkg.pkg_name:
            current_pkg = Pkg(pkg_name)

        if (xpi_name != pkg_name) and not no_provide:
            current_pkg.provides.append(f"{LOCALE_PREFIX}-{xpi_name.lower()}")

        if current_pkg not in shipped_packages:
            shipped_packages.append(current_pkg)
    return shipped_packages, xpi_locale_map


if __name__ == "__main__":
    main()

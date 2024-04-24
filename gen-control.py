#!/usr/bin/python3

import os, sys

archi = sys.argv[1]
curdir = sys.argv[2]
version = sys.argv[3]
abort = False

lmde = False

release = version
if "+" in version:
    release = version.split("+")[0]

if "~" in version:
    release = version.split("~")[0]
    lmde = True

locale_prefix = "thunderbird-locale"

shipped_template = """
Package: %s-%s
Architecture: all
Depends: ${misc:Depends}%s
Description: %s language packs for Thunderbird
 %s language packs for the Mozilla Thunderbird Mail Client.
"""


transitional_template = """
Package: %s
Architecture: all
Description: Transitional package for Thunderbird language packs.
 .
 This is an empty transitional package to ensure a clean upgrade
 process. You can safely remove this package after installation.
"""

# Load code:Name list to popular control descriptions
locale_name_dict = {}
with open(os.path.join(curdir, "locales.all")) as f:
    for line in f:
        if line.startswith("#"):
            continue
        code, lang = line.split(":")
        locale_name_dict[code] = lang.replace("\n", "")

xpi_locale_map = {}

class Pkg():
    def __init__(self, pkg_name):
        self.pkg_name = pkg_name
        self.provides = []
        self.replaces = []

shipped_packages = []

with open(os.path.join(curdir, "locales.shipped")) as f:
    current_pkg = Pkg("")
    for line in f:
        if line.startswith("#"):
            continue
        line = line.replace("\n", "")
        print(line)

        noprovide = False
        try:
            xpi_name, pkg_name, noprovide = line.split(":")
        except:
            xpi_name, pkg_name = line.split(":")

        pkg_name = pkg_name.replace("\n", "")

        xpi_locale_map[xpi_name] = pkg_name

        if pkg_name != current_pkg.pkg_name:
            current_pkg = Pkg(pkg_name)

        if (xpi_name != pkg_name) and not noprovide:
            current_pkg.provides.append("%s-%s" % (locale_prefix, xpi_name.lower()))

        if current_pkg not in shipped_packages:
            shipped_packages.append(current_pkg)

control_locales = ""
used_codes = []

print("\nGenerating %s entries for control file...\n")

for pkg in shipped_packages:
    if len(pkg.provides) != 0:
        provide_str = "\nProvides: %s" % ", ".join(pkg.provides)
    else:
        provide_str = ""
    control_locales += (
        shipped_template % (locale_prefix, pkg.pkg_name, provide_str, locale_name_dict[pkg.pkg_name], locale_name_dict[pkg.pkg_name]))

snap_replacements = [
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

for t_package_name in snap_replacements:
    control_locales += (
        transitional_template % (t_package_name,))

with open(os.path.join(curdir, "debian", "control"), "w") as f:
    control = ""
    with open(os.path.join(curdir, "debian", "control.in"), "r") as ini:
        control += ini.read()

    control += control_locales

    f.write(control)

print("\nDone generating control file...\n")

os.chdir(curdir)

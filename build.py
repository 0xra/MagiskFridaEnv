#!/user/bin/env python3

import sys
import getopt
import lzma
import os
import shutil
import zipfile

import requests

PATH_BASE = os.path.abspath(os.path.dirname(__file__))
PATH_BASE_MODULE = os.path.join(PATH_BASE, "base")
PATH_BUILDS = os.path.join(PATH_BASE, "builds")
PATH_DOWNLOADS = os.path.join(PATH_BASE, "downloads")


def traverse_path_to_list(file_list, path):
    for dp, dn, fn in os.walk(path):
        for f in fn:
            if f == "placeholder" or f == ".gitkeep":
                continue
            file_list.append(os.path.join(dp, f))


def download_file(url, path):
    file_name = url[url.rfind("/") + 1:]

    print("Downloading '{0}' to '{1}'.".format(file_name, path))

    if os.path.exists(path):
        print("Exists.")
        return

    r = requests.get(url, allow_redirects=True)
    with open(path, 'wb') as f:
        f.write(r.content)

    print("Done.")


def extract_file(archive_path, dest_path):
    print("Extracting '{0}' to '{1}'.".format(
        os.path.basename(archive_path), os.path.basename(dest_path)))

    with lzma.open(archive_path) as f:
        file_content = f.read()
        path = os.path.dirname(dest_path)

        if not os.path.exists(path):
            os.makedirs(path)

        with open(dest_path, "wb") as out:
            out.write(file_content)


def create_service_script(module_dir, frida_release):
    # Create module.prop file.
    service_sh = """#!/system/bin/sh
# Do NOT assume where your module will be located.
# ALWAYS use $MODDIR if you need to know where this script
# and module is placed.
# This will make sure your module will still work
# if Magisk change its mount point in the future
MODDIR={0}

# This script will be executed in late_start service mode
mfe {1}
""".format(r'${0%/*}', frida_release)

    with open(os.path.join(module_dir, "common/service.sh"), "w", newline='\n') as f:
        f.write(service_sh)


def create_module_prop(path):
    # Create module.prop file.
    module_prop = """id=magiskfridaenv
name=MagiskFridaEnv
version=v{0}
versionCode={1}
author=toolsRE
description=Forked from AeonLucid/MagiskFrida. Runs frida-server on boot as root with magisk. And select the version.
support=https://github.com/toolsRE/MagiskFridaEnv/issues
minMagisk=1530""".format("0.0.1", "0.0.1".replace(".", ""))  # format(frida_release, frida_release.replace(".", ""))

    with open(os.path.join(path, "module.prop"), "w", newline='\n') as f:
        f.write(module_prop)


def create_module(platform, frida_releases):
    # Create directory.
    module_dir = os.path.join(PATH_BUILDS, platform)
    module_zip = os.path.join(
        PATH_BUILDS, "MagiskFridaEnv-{0}.zip".format(platform))

    if os.path.exists(module_dir):
        shutil.rmtree(module_dir)

    if os.path.exists(module_zip):
        os.remove(module_zip)

    # Copy base module into module dir.
    shutil.copytree(PATH_BASE_MODULE, module_dir)

    # cd into module directory.
    os.chdir(module_dir)

    # Create module.prop.
    create_module_prop(module_dir)

    for frida_release in frida_releases:
        # Download frida-server archives.
        frida_download_url = "https://github.com/frida/frida/releases/download/{0}/".format(
            frida_release)
        frida_server = "frida-server-{0}-android-{1}.xz".format(
            frida_release, platform)
        frida_server_path = os.path.join(PATH_DOWNLOADS, frida_server)

        download_file(frida_download_url + frida_server, frida_server_path)

        # Extract frida-server to correct path.
        extract_file(frida_server_path, os.path.join(
            module_dir, "system/bin/frida-server.{0}".format(frida_release)))

    create_service_script(module_dir, frida_releases[0])

    # Create flashable zip.
    print("Building Magisk module.")

    file_list = ["install.sh", "module.prop"]

    traverse_path_to_list(file_list, "./common")
    traverse_path_to_list(file_list, "./system")
    traverse_path_to_list(file_list, "./META-INF")

    with zipfile.ZipFile(module_zip, "w") as zf:
        for file_name in file_list:
            path = os.path.join(module_dir, file_name)

            if not os.path.exists(path):
                print("File {0} does not exist..".format(path))
                continue

            zf.write(path, arcname=file_name)


def main(versions, archs):
    # Create necessary folders.
    if not os.path.exists(PATH_DOWNLOADS):
        os.makedirs(PATH_DOWNLOADS)

    if not os.path.exists(PATH_BUILDS):
        os.makedirs(PATH_BUILDS)

    if len(versions) == 0:
        # Fetch frida information.
        frida_releases_url = "https://api.github.com/repos/frida/frida/releases/{0}".format(
            "latest")
        frida_releases = requests.get(frida_releases_url).json()
        frida_release = frida_releases["tag_name"]
        print("Latest frida version is {0}.".format(frida_release))
        versions.append(frida_release)

    # Create flashable modules.
    for arch in archs:
        create_module(arch, versions)

    print("Done.")


def usage():
    print(
        '\n'
        ' -h --help \n'
        ' -a --arch=        the arch to be built (one or more of arm/arm64/x86/x86_64) (default to arm and arm64)\n'
        ' -v --version=     the version to be built (default to latest)\n'
        ''
    )


if __name__ == "__main__":
    # main(sys.argv[1:])
    archs, versions = [], []
    opts, args = getopt.getopt(
        sys.argv[1:], '-h-a:-v:', ['help', 'arch=', 'version='])
    for opt_name, opt_value in opts:
        if opt_name in ('-h', '--help'):
            usage()
            exit()
        if opt_name in ('-a', '--arch'):
            archs.append(opt_value)
        if opt_name in ('-v', '--version'):
            versions.append(opt_value)

    if len(archs) == 0:
        archs = ['arm', 'arm64']

    print("[*] archs      ", archs)
    print("[*] versions   ", versions)
    main(versions, archs)

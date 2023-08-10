#!/usr/bin/env python

import hashlib
import json
import urllib3

from packaging.version import LegacyVersion

# Find the current stable versions of each browser we
# support and the sha256 of these. That's useful for
# updating `//common:repositories.bzl`

http = urllib3.PoolManager()

def calculate_hash(url):
    h = hashlib.sha256()
    r = http.request('GET', url, preload_content=False)
    for b in iter(lambda: r.read(4096), b""):
        h.update(b)
    return h.hexdigest()

def chromedriver():
    r = http.request('GET', 'https://chromedriver.storage.googleapis.com/LATEST_RELEASE')
    v = r.data.decode('utf-8')

    content = ""

    linux = f'https://chromedriver.storage.googleapis.com/{v}/chromedriver_linux64.zip'
    sha = calculate_hash(linux)
    content += """
    http_archive(
        name = "linux_chromedriver",
        url = "%s",
        sha256 = "%s",
        build_file_content = "exports_files([\\"chromedriver\\"])",
    )
    """ % (
        linux,
        sha,
    )

    mac = f'https://chromedriver.storage.googleapis.com/{v}/chromedriver_mac64.zip'
    sha = calculate_hash(mac)
    content += """
    http_archive(
        name = "mac_chromedriver",
        url = "%s",
        sha256 = "%s",
        build_file_content = "exports_files([\\"chromedriver\\"])",
    )
    """ % (
        mac,
        sha,
    )
    return content

def chrome():
    channel = "Stable"
    r = http.request('GET', f'https://chromiumdash.appspot.com/fetch_releases?channel={channel}&num=1&platform=Win32,Windows,Mac,Linux')
    milestone = json.loads(r.data)[0]["milestone"]

    r = http.request('GET', 'https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json')
    versions = json.loads(r.data)["versions"]

    selected_version = sorted(
        filter(lambda v: v['version'].split('.')[0] == str(milestone), versions),
        key=lambda v: LegacyVersion(v['version'])
    )[-1]

    downloads = selected_version["downloads"]["chrome"]

    linux = [d["url"] for d in downloads if d["platform"] == "linux64"][0]
    sha = calculate_hash(linux)

    content = """
    http_archive(
        name = "linux_chrome",
        url = "%s",
        sha256 = "%s",
        build_file_content = \"\"\"
filegroup(
    name = "files",
    srcs = glob(["**/*"]),
    visibility = ["//visibility:public"],
)

exports_files(
    ["chrome-linux64/chrome"],
)
\"\"\",
    )

""" % (linux, sha)

    mac = [d["url"] for d in downloads if d["platform"] == "mac-x64"][0]
    sha = calculate_hash(mac)

    content += """
    http_archive(
        name = "mac_chrome",
        url = "%s",
        sha256 = "%s",
        strip_prefix = "chrome-mac-x64",
        patch_cmds = [
            "mv 'Google Chrome for Testing.app' Chrome.app",
            "mv 'Chrome.app/Contents/MacOS/Google Chrome for Testing' Chrome.app/Contents/MacOS/Chrome",
        ],
        build_file_content = "exports_files([\\"Google Chrome for Testing.app\\"])",
    )

""" % (mac, sha)

    return content

def edge():
    r = http.request('GET', 'https://edgeupdates.microsoft.com/api/products')
    all_data = json.loads(r.data)

    edge = None
    hash = None
    version = None

    for data in all_data:
        if data.get("Product") != "Stable":
            continue
        for release in data["Releases"]:
            if release.get("Platform") == "MacOS":
                for artifact in release["Artifacts"]:
                    if artifact["ArtifactName"] == "pkg":
                        edge = artifact["Location"]
                        hash = artifact["Hash"]
                        version = release["ProductVersion"]

    if edge and hash:
        return """
    pkg_archive(
        name = "mac_edge",
        url = "%s",
        sha256 = "%s",
        move = {
            "MicrosoftEdge-%s.pkg/Payload/Microsoft Edge.app": "Edge.app",
        },
        build_file_content = "exports_files([\\"Edge.app\\"])",
    )
""" % (edge, hash.lower(), version)

    return ""

def edgedriver():
    r = http.request('GET', 'https://msedgedriver.azureedge.net/LATEST_STABLE')
    v = r.data.decode('utf-16').strip()

    content = ""

    linux = f"https://msedgedriver.azureedge.net/{v}/edgedriver_linux64.zip"
    sha = calculate_hash(linux)
    content += """
    http_archive(
        name = "linux_edgedriver",
        url = "%s",
        sha256 = "%s",
        build_file_content = "exports_files([\\"msedgedriver\\"])",
    )
    """ % (
        linux,
        sha,
    )

    mac = f"https://msedgedriver.azureedge.net/{v}/edgedriver_mac64.zip"
    sha = calculate_hash(mac)
    content += """
    http_archive(
        name = "mac_edgedriver",
        url = "%s",
        sha256 = "%s",
        build_file_content = "exports_files([\\"msedgedriver\\"])",
    )
    """ % (
        mac,
        sha,
    )
    return content

def geckodriver():
    content = ""

    r = http.request('GET', 'https://api.github.com/repos/mozilla/geckodriver/releases/latest')
    for a in json.loads(r.data)['assets']:
        if a['name'].endswith('-linux64.tar.gz'):
            url = a['browser_download_url']
            sha = calculate_hash(url)
            content = content + \
                  """
    http_archive(
        name = "linux_geckodriver",
        url = "%s",
        sha256 = "%s",
        build_file_content = "exports_files([\\"geckodriver\\"])",
    )
    """ % (url, sha)

        if a['name'].endswith('-macos.tar.gz'):
            url = a['browser_download_url']
            sha = calculate_hash(url)
            content = content + \
                  """
    http_archive(
        name = "mac_geckodriver",
        url = "%s",
        sha256 = "%s",
        build_file_content = "exports_files([\\"geckodriver\\"])",
    )
        """ % (url, sha)
    return content

def firefox():
    r = http.request('GET', 'https://product-details.mozilla.org/1.0/firefox_versions.json')
    v = json.loads(r.data)['LATEST_FIREFOX_VERSION']

    content = ""

    linux = f"https://ftp.mozilla.org/pub/firefox/releases/{v}/linux-x86_64/en-US/firefox-{v}.tar.bz2"
    sha = calculate_hash(linux)
    content += """
    http_archive(
        name = "linux_firefox",
        url = "%s",
        sha256 = "%s",
        build_file_content = \"\"\"
filegroup(
    name = "files",
    srcs = glob(["**/*"]),
    visibility = ["//visibility:public"],
)

exports_files(
    ["firefox/firefox"],
)
\"\"\",
    )

""" % (
        linux,
        sha,
    )

    mac = "https://ftp.mozilla.org/pub/firefox/releases/%s/mac/en-US/Firefox%%20%s.dmg" % (v, v)
    sha = calculate_hash(mac)
    content += """
    dmg_archive(
        name = "mac_firefox",
        url = "%s",
        sha256 = "%s",
        build_file_content = "exports_files([\\"Firefox.app\\"])",
    )

""" % (
        mac,
        sha,
    )

    return content

if __name__ == '__main__':
    content = """
# This file has been generated using `bazel run scripts:pinned_browsers`

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//common/private:dmg_archive.bzl", "dmg_archive")
load("//common/private:drivers.bzl", "local_drivers")
load("//common/private:pkg_archive.bzl", "pkg_archive")

def pin_browsers():
    local_drivers()
"""
    content += firefox()
    content = content + geckodriver()
    content = content + edge()
    content = content + edgedriver()
    content = content + chrome()
    content = content + chromedriver()

    print(content)

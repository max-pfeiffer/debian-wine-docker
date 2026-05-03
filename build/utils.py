"""Utilities for image publishing."""

import gzip
import io
import urllib.request
from pathlib import Path

import requests
import semver
from debian.deb822 import Packages


def get_context() -> Path:
    """Return Docker build context.

    :return:
    """
    return Path(__file__).parent.resolve()


def get_image_reference(
    registry: str,
    tag: str,
) -> str:
    """Return image reference.

    :param registry:
    :param image_version:
    :return:
    """
    reference: str = f"{registry}/pfeiffermax/debian-wine:{tag}"
    return reference


def get_latest_wine_stable_version() -> str:
    """Pull the latest version from Debian package sources.

    :return:
    """
    url = "https://dl.winehq.org/wine-builds/debian/dists/trixie/main/binary-amd64/Packages.gz"
    with urllib.request.urlopen(url) as resp:
        data = io.BytesIO(gzip.decompress(resp.read()))

    winehq_stable_versions = []

    for pkg in Packages.iter_paragraphs(data):
        print(pkg["Package"], pkg["Version"])
        print("  Depends:", pkg.get("Depends", "—"))
        print("  Filename:", pkg["Filename"])  # path relative to repo root
        if pkg["Package"] == "winehq-stable" and pkg["Architecture"] == "amd64":
            version = pkg["Version"].split("~")[0]
            version_parts = version.split(".")[:3]
            final_version = ".".join(version_parts)
            winehq_stable_versions.append(final_version)

    latest_version = max(winehq_stable_versions, key=semver.Version.parse)
    return latest_version


def tag_exists(build_id: str) -> bool:
    """Pull tag data from Docker Hub and check if tag with this build_id already exists.

    :param build_id:
    :return:
    """
    response = requests.get(
        "https://hub.docker.com/v2/namespaces/pfeiffermax/repositories/debian-wine/tags"
    )
    response.raise_for_status()
    tags: dict = response.json()["results"]
    matching_tags: list[dict] = [tag for tag in tags if (build_id in tag["name"])]
    if matching_tags:
        return True
    else:
        return False

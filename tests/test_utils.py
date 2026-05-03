"""Tests for build/utils.py."""

import gzip
import io
from pathlib import Path
from unittest.mock import MagicMock

from build.utils import (
    create_tag,
    get_context,
    get_image_reference,
    get_latest_wine_stable_version,
    tag_exists,
)


def _make_packages_gz(*packages: dict) -> bytes:
    """Build an in-memory gzip-compressed Debian Packages file.

    :param packages: Dicts mapping Debian control field names to values.
    :type packages: dict
    :returns: Gzip-compressed bytes of the resulting Packages index.
    :rtype: bytes
    """
    lines = []
    for pkg in packages:
        for key, value in pkg.items():
            lines.append(f"{key}: {value}")
        lines.append("")
    content = "\n".join(lines).encode()
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as f:
        f.write(content)
    return buf.getvalue()


def _mock_urlopen(mocker, packages_gz: bytes) -> None:
    """Patch urllib.request.urlopen to return *packages_gz* as the response body.

    :param mocker: pytest-mock fixture used to patch urlopen.
    :param packages_gz: Gzip-compressed Packages file bytes to serve as the response.
    :type packages_gz: bytes
    :returns: None
    :rtype: None
    """
    mock_resp = MagicMock()
    mock_resp.read.return_value = packages_gz
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    mocker.patch("urllib.request.urlopen", return_value=mock_resp)


# --- get_context ---


def test_get_context_returns_path() -> None:
    """Verify that get_context returns a Path instance.

    :returns: None
    :rtype: None
    """
    assert isinstance(get_context(), Path)


def test_get_context_points_to_build_directory() -> None:
    """Verify that the path returned by get_context is named 'build'.

    :returns: None
    :rtype: None
    """
    assert get_context().name == "build"


def test_get_context_exists() -> None:
    """Verify that the path returned by get_context exists on disk.

    :returns: None
    :rtype: None
    """
    assert get_context().exists()


# --- get_image_reference ---


def test_get_image_reference_docker_hub() -> None:
    """Verify get_image_reference builds the correct reference for Docker Hub.

    :returns: None
    :rtype: None
    """
    assert (
        get_image_reference("docker.io", "build-9.0.0")
        == "docker.io/pfeiffermax/debian-wine:build-9.0.0"
    )


def test_get_image_reference_local_registry() -> None:
    """Verify get_image_reference builds the correct reference for a local registry.

    :returns: None
    :rtype: None
    """
    assert (
        get_image_reference("localhost:5000", "latest")
        == "localhost:5000/pfeiffermax/debian-wine:latest"
    )


# --- create_tag ---


def test_create_tag_prefixes_build() -> None:
    """Verify that create_tag prepends 'build-' to the given version string.

    :returns: None
    :rtype: None
    """
    assert create_tag("9.0.0") == "build-9.0.0"


def test_create_tag_arbitrary_id() -> None:
    """Verify that create_tag works for an arbitrary version string.

    :returns: None
    :rtype: None
    """
    assert create_tag("10.1.2") == "build-10.1.2"


# --- get_latest_wine_stable_version ---


def test_get_latest_wine_stable_version_picks_highest(mocker) -> None:
    """Verify the highest version when multiple exist.

    :param mocker: pytest-mock fixture used to patch urlopen.
    :returns: None
    :rtype: None
    """
    packages_gz = _make_packages_gz(
        {
            "Package": "winehq-stable",
            "Version": "9.0.0.0~trixie-1",
            "Architecture": "amd64",
            "Filename": "pool/main/w/wine-installer/winehq-stable_9.0.0.0~"
            "trixie-1_amd64.deb",
        },
        {
            "Package": "winehq-stable",
            "Version": "10.0.0.0~trixie-1",
            "Architecture": "amd64",
            "Filename": "pool/main/w/wine-installer/winehq-stable_10.0.0.0~"
            "trixie-1_amd64.deb",
        },
    )
    _mock_urlopen(mocker, packages_gz)

    assert get_latest_wine_stable_version() == "10.0.0"


def test_get_latest_wine_stable_version_single_entry(mocker) -> None:
    """Verify get_latest_wine_stable_version works when only one package entry exists.

    :param mocker: pytest-mock fixture used to patch urlopen.
    :returns: None
    :rtype: None
    """
    packages_gz = _make_packages_gz(
        {
            "Package": "winehq-stable",
            "Version": "8.0.2.0~trixie-1",
            "Architecture": "amd64",
            "Filename": "pool/main/w/wine-installer/winehq-stable_8.0.2.0~"
            "trixie-1_amd64.deb",
        },
    )
    _mock_urlopen(mocker, packages_gz)

    assert get_latest_wine_stable_version() == "8.0.2"


def test_get_latest_wine_stable_version_ignores_non_amd64(mocker) -> None:
    """Verify get_latest_wine_stable_version ignores non-amd64 architecture entries.

    :param mocker: pytest-mock fixture used to patch urlopen.
    :returns: None
    :rtype: None
    """
    packages_gz = _make_packages_gz(
        {
            "Package": "winehq-stable",
            "Version": "10.0.0.0~trixie-1",
            "Architecture": "i386",
            "Filename": "pool/main/w/wine-installer/winehq-stable_10.0.0.0~"
            "trixie-1_i386.deb",
        },
        {
            "Package": "winehq-stable",
            "Version": "9.0.0.0~trixie-1",
            "Architecture": "amd64",
            "Filename": "pool/main/w/wine-installer/winehq-stable_9.0.0.0~"
            "trixie-1_amd64.deb",
        },
    )
    _mock_urlopen(mocker, packages_gz)

    assert get_latest_wine_stable_version() == "9.0.0"


def test_get_latest_wine_stable_version_ignores_other_packages(mocker) -> None:
    """Verify get_latest_wine_stable_version ignores packages other than winehq-stable.

    :param mocker: pytest-mock fixture used to patch urlopen.
    :returns: None
    :rtype: None
    """
    packages_gz = _make_packages_gz(
        {
            "Package": "wine-stable",
            "Version": "99.0.0.0~trixie-1",
            "Architecture": "amd64",
            "Filename": "pool/main/w/wine/wine-stable_99.0.0.0~trixie-1_amd64.deb",
        },
        {
            "Package": "winehq-stable",
            "Version": "9.0.0.0~trixie-1",
            "Architecture": "amd64",
            "Filename": "pool/main/w/wine-installer/winehq-stable_9.0.0.0~"
            "trixie-1_amd64.deb",
        },
    )
    _mock_urlopen(mocker, packages_gz)

    assert get_latest_wine_stable_version() == "9.0.0"


def test_get_latest_wine_stable_version_strips_epoch_suffix(mocker) -> None:
    """Verify get_latest_wine_stable_version strips the Debian epoch/trixie suffix.

    :param mocker: pytest-mock fixture used to patch urlopen.
    :returns: None
    :rtype: None
    """
    packages_gz = _make_packages_gz(
        {
            "Package": "winehq-stable",
            "Version": "9.0.0.0~trixie-1",
            "Architecture": "amd64",
            "Filename": "pool/main/w/wine-installer/winehq-stable_9.0.0.0~"
            "trixie-1_amd64.deb",
        },
    )
    _mock_urlopen(mocker, packages_gz)

    result = get_latest_wine_stable_version()
    assert "~" not in result


# --- tag_exists ---


def test_tag_exists_returns_true_when_build_id_in_tag_name(mocker) -> None:
    """Verify tag_exists returns True when the build tag is present results.

    :param mocker: pytest-mock fixture used to patch requests.get.
    :returns: None
    :rtype: None
    """
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [{"name": "build-9.0.0"}, {"name": "latest"}]
    }
    mocker.patch("requests.get", return_value=mock_response)

    assert tag_exists("9.0.0") is True


def test_tag_exists_returns_false_when_build_id_absent(mocker) -> None:
    """Verify tag_exists returns False when the build tag is absent from results.

    :param mocker: pytest-mock fixture used to patch requests.get.
    :returns: None
    :rtype: None
    """
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [{"name": "build-8.0.0"}, {"name": "latest"}]
    }
    mocker.patch("requests.get", return_value=mock_response)

    assert tag_exists("9.0.0") is False


def test_tag_exists_returns_false_for_empty_results(mocker) -> None:
    """Verify tag_exists returns False when Docker Hub returns an empty results list.

    :param mocker: pytest-mock fixture used to patch requests.get.
    :returns: None
    :rtype: None
    """
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mocker.patch("requests.get", return_value=mock_response)

    assert tag_exists("9.0.0") is False


def test_tag_exists_calls_raise_for_status(mocker) -> None:
    """Verify tag_exists calls raise_for_status on the HTTP response.

    :param mocker: pytest-mock fixture used to patch requests.get.
    :returns: None
    :rtype: None
    """
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mocker.patch("requests.get", return_value=mock_response)

    tag_exists("9.0.0")

    mock_response.raise_for_status.assert_called_once()

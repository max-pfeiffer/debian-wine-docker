"""Publish CLI."""

from pathlib import Path

import click
from python_on_whales import Builder, DockerClient

from build.utils import (
    get_context,
    get_image_reference,
    get_latest_wine_stable_version,
    tag_exists,
)


@click.command()
@click.option(
    "--docker-hub-username",
    envvar="DOCKER_HUB_USERNAME",
    help="Docker Hub username",
)
@click.option(
    "--docker-hub-token",
    envvar="DOCKER_HUB_TOKEN",
    help="Docker Hub token",
)
@click.option(
    "--registry", envvar="REGISTRY", default="docker.io", help="Docker registry"
)
@click.option(
    "--publish-manually",
    envvar="PUBLISH_MANUALLY",
    is_flag=True,
    help="Flag for building the Docker image manually, "
    "overrides the check for existing image tags",
)
def main(
    docker_hub_username: str,
    docker_hub_token: str,
    registry: str,
    publish_manually: bool,
) -> None:
    """Build and publish image to Docker Hub.

    :param docker_hub_username:
    :param docker_hub_token:
    :param registry:
    :param publish_manually:
    :return:
    """
    context: Path = get_context()

    click.echo("Checking Wine version for release branch...")
    wine_version = get_latest_wine_stable_version()
    click.echo(f"Current Wine version: {wine_version}")

    if not publish_manually and tag_exists(wine_version):
        click.echo(
            "Image for this Wine version already exists. Skipping Docker image build..."
        )
    else:
        click.echo("Building Wine Docker image...")

        image_reference_version: str = get_image_reference(registry, wine_version)
        image_reference_latest: str = get_image_reference(registry, "latest")

        docker_client: DockerClient = DockerClient()
        builder: Builder = docker_client.buildx.create(
            driver="docker-container", driver_options=dict(network="host")
        )

        docker_client.login(
            server=registry,
            username=docker_hub_username,
            password=docker_hub_token,
        )

        docker_client.buildx.build(
            context_path=context,
            tags=[image_reference_version, image_reference_latest],
            platforms=["linux/amd64"],
            builder=builder,
            push=True,
        )

        # Cleanup
        docker_client.buildx.stop(builder)
        docker_client.buildx.remove(builder)


if __name__ == "__main__":
    # pylint: disable=no-value-for-parameter
    main()

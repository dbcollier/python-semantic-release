from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

import pytest
from git import Repo

from tests.const import EXAMPLE_HVCS_DOMAIN
from tests.util import copy_dir_tree, temporary_working_directory

if TYPE_CHECKING:
    from pathlib import Path

    from semantic_release.hvcs import HvcsBase

    from tests.conftest import TeardownCachedDirFn
    from tests.fixtures.example_project import ExProjectDir
    from tests.fixtures.git_repo import (
        BaseRepoVersionDef,
        BuildRepoFn,
        CommitConvention,
        CreateReleaseFn,
        ExProjectGitRepoFn,
        GetRepoDefinitionFn,
        GetVersionStringsFn,
        RepoDefinition,
        SimulateChangeCommitsNReturnChangelogEntryFn,
        TomlSerializableTypes,
        VersionStr,
    )


@pytest.fixture(scope="session")
def get_commits_for_trunk_only_repo_w_tags() -> GetRepoDefinitionFn:
    base_definition: dict[str, BaseRepoVersionDef] = {
        "0.1.0": {
            "changelog_sections": {
                "angular": [{"section": "Unknown", "i_commits": [0]}],
                "emoji": [{"section": "Other", "i_commits": [0]}],
                "scipy": [{"section": "None", "i_commits": [0]}],
                "tag": [{"section": "Unknown", "i_commits": [0]}],
            },
            "commits": [
                {
                    "angular": "Initial commit",
                    "emoji": "Initial commit",
                    "scipy": "Initial commit",
                    "tag": "Initial commit",
                }
            ],
        },
        "0.1.1": {
            "changelog_sections": {
                "angular": [{"section": "Fix", "i_commits": [0]}],
                "emoji": [{"section": ":bug:", "i_commits": [0]}],
                "scipy": [{"section": "Fix", "i_commits": [0]}],
                "tag": [{"section": "Fix", "i_commits": [0]}],
            },
            "commits": [
                {
                    "angular": "fix: add some more text",
                    "emoji": ":bug: add some more text",
                    "scipy": "MAINT: add some more text",
                    "tag": ":nut_and_bolt: add some more text",
                }
            ],
        },
    }

    def _get_commits_for_trunk_only_repo_w_tags(
        commit_type: CommitConvention = "angular",
    ) -> RepoDefinition:
        definition: RepoDefinition = {}

        for version, version_def in base_definition.items():
            definition[version] = {
                # Extract the correct changelog section header for the commit type
                "changelog_sections": deepcopy(
                    version_def["changelog_sections"][commit_type]
                ),
                "commits": [
                    # Extract the correct commit message for the commit type
                    message_variants[commit_type]
                    for message_variants in version_def["commits"]
                ],
            }

        return definition

    return _get_commits_for_trunk_only_repo_w_tags


@pytest.fixture(scope="session")
def get_versions_for_trunk_only_repo_w_tags(
    get_commits_for_trunk_only_repo_w_tags: GetRepoDefinitionFn,
) -> GetVersionStringsFn:
    def _get_versions_for_trunk_only_repo_w_tags() -> list[VersionStr]:
        return list(get_commits_for_trunk_only_repo_w_tags().keys())

    return _get_versions_for_trunk_only_repo_w_tags


@pytest.fixture(scope="session")
def build_trunk_only_repo_w_tags(
    get_commits_for_trunk_only_repo_w_tags: GetRepoDefinitionFn,
    build_configured_base_repo: BuildRepoFn,
    default_tag_format_str: str,
    simulate_change_commits_n_rtn_changelog_entry: SimulateChangeCommitsNReturnChangelogEntryFn,
    create_release_tagged_commit: CreateReleaseFn,
) -> BuildRepoFn:
    def _build_trunk_only_repo_w_tags(
        dest_dir: Path | str,
        commit_type: CommitConvention = "angular",
        hvcs_client_name: str = "github",
        hvcs_domain: str = EXAMPLE_HVCS_DOMAIN,
        tag_format_str: str | None = None,
        extra_configs: dict[str, TomlSerializableTypes] | None = None,
    ) -> tuple[Path, HvcsBase]:
        repo_dir, hvcs = build_configured_base_repo(
            dest_dir,
            commit_type=commit_type,
            hvcs_client_name=hvcs_client_name,
            hvcs_domain=hvcs_domain,
            tag_format_str=tag_format_str,
            extra_configs=extra_configs,
        )

        repo_def = get_commits_for_trunk_only_repo_w_tags(commit_type)
        versions = (key for key in repo_def)
        next_version = next(versions)
        next_version_def = repo_def[next_version]

        # must be after build_configured_base_repo() so we dont set the
        # default tag format in the pyproject.toml (we want semantic-release to use its defaults)
        # however we need it to manually create the tags it knows how to parse
        tag_format = tag_format_str or default_tag_format_str

        # Run Git operations to simulate repo commit & release history
        with temporary_working_directory(repo_dir), Repo(".") as git_repo:
            # commit initial files & update commit msg with sha & url
            next_version_def["commits"] = simulate_change_commits_n_rtn_changelog_entry(
                git_repo, next_version_def["commits"], hvcs
            )

            # Publish initial feature release (v0.1.0) [updates tool.poetry.version]
            create_release_tagged_commit(git_repo, next_version, tag_format)

            # Increment version pointer
            next_version = next(versions)
            next_version_def = repo_def[next_version]

            # Add a patch level change
            next_version_def["commits"] = simulate_change_commits_n_rtn_changelog_entry(
                git_repo, next_version_def["commits"], hvcs
            )

            # Make a patch level release (v0.1.1)
            create_release_tagged_commit(git_repo, next_version, tag_format)

        return repo_dir, hvcs

    return _build_trunk_only_repo_w_tags


# --------------------------------------------------------------------------- #
# Session-level fixtures to use to set up cached repositories on first use    #
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="session")
def cached_repo_with_single_branch_angular_commits(
    build_trunk_only_repo_w_tags: BuildRepoFn,
    cached_files_dir: Path,
    teardown_cached_dir: TeardownCachedDirFn,
) -> Path:
    cached_repo_path = cached_files_dir.joinpath(
        cached_repo_with_single_branch_angular_commits.__name__
    )
    build_trunk_only_repo_w_tags(cached_repo_path, "angular")
    return teardown_cached_dir(cached_repo_path)


@pytest.fixture(scope="session")
def cached_repo_with_single_branch_emoji_commits(
    build_trunk_only_repo_w_tags: BuildRepoFn,
    cached_files_dir: Path,
    teardown_cached_dir: TeardownCachedDirFn,
) -> Path:
    cached_repo_path = cached_files_dir.joinpath(
        cached_repo_with_single_branch_emoji_commits.__name__
    )
    build_trunk_only_repo_w_tags(cached_repo_path, "emoji")
    return teardown_cached_dir(cached_repo_path)


@pytest.fixture(scope="session")
def cached_repo_with_single_branch_scipy_commits(
    build_trunk_only_repo_w_tags: BuildRepoFn,
    cached_files_dir: Path,
    teardown_cached_dir: TeardownCachedDirFn,
) -> Path:
    cached_repo_path = cached_files_dir.joinpath(
        cached_repo_with_single_branch_scipy_commits.__name__
    )
    build_trunk_only_repo_w_tags(cached_repo_path, "scipy")
    return teardown_cached_dir(cached_repo_path)


@pytest.fixture(scope="session")
def cached_repo_with_single_branch_tag_commits(
    build_trunk_only_repo_w_tags: BuildRepoFn,
    cached_files_dir: Path,
    teardown_cached_dir: TeardownCachedDirFn,
) -> Path:
    cached_repo_path = cached_files_dir.joinpath(
        cached_repo_with_single_branch_tag_commits.__name__
    )
    build_trunk_only_repo_w_tags(cached_repo_path, "tag")
    return teardown_cached_dir(cached_repo_path)


# --------------------------------------------------------------------------- #
# Test-level fixtures to use to set up temporary test directory               #
# --------------------------------------------------------------------------- #


@pytest.fixture
def repo_with_single_branch_angular_commits(
    cached_repo_with_single_branch_angular_commits: Path,
    example_project_git_repo: ExProjectGitRepoFn,
    example_project_dir: ExProjectDir,
    change_to_ex_proj_dir: None,
) -> Repo:
    if not cached_repo_with_single_branch_angular_commits.exists():
        raise RuntimeError("Unable to find cached repository!")
    copy_dir_tree(cached_repo_with_single_branch_angular_commits, example_project_dir)
    return example_project_git_repo()


@pytest.fixture
def repo_with_single_branch_emoji_commits(
    cached_repo_with_single_branch_emoji_commits: Path,
    example_project_git_repo: ExProjectGitRepoFn,
    example_project_dir: ExProjectDir,
    change_to_ex_proj_dir: None,
) -> Repo:
    if not cached_repo_with_single_branch_emoji_commits.exists():
        raise RuntimeError("Unable to find cached repository!")
    copy_dir_tree(cached_repo_with_single_branch_emoji_commits, example_project_dir)
    return example_project_git_repo()


@pytest.fixture
def repo_with_single_branch_scipy_commits(
    cached_repo_with_single_branch_scipy_commits: Path,
    example_project_git_repo: ExProjectGitRepoFn,
    example_project_dir: ExProjectDir,
    change_to_ex_proj_dir: None,
) -> Repo:
    if not cached_repo_with_single_branch_scipy_commits.exists():
        raise RuntimeError("Unable to find cached repository!")
    copy_dir_tree(cached_repo_with_single_branch_scipy_commits, example_project_dir)
    return example_project_git_repo()


@pytest.fixture
def repo_with_single_branch_tag_commits(
    cached_repo_with_single_branch_tag_commits: Path,
    example_project_git_repo: ExProjectGitRepoFn,
    example_project_dir: ExProjectDir,
    change_to_ex_proj_dir: None,
) -> Repo:
    if not cached_repo_with_single_branch_tag_commits.exists():
        raise RuntimeError("Unable to find cached repository!")
    copy_dir_tree(cached_repo_with_single_branch_tag_commits, example_project_dir)
    return example_project_git_repo()

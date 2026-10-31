from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from support import SCRIPTS, run_script

if TYPE_CHECKING:
    from conftest import Repository


def resolved(repository: Repository, *arguments: str) -> dict[str, Any]:
    process = run_script("run_resolve_range.py", *arguments, "--repo", str(repository.path))
    assert process.returncode == 0, process.stderr
    return json.loads(process.stdout)


def refused(repository: Repository, *arguments: str) -> str:
    process = run_script("run_resolve_range.py", *arguments, "--repo", str(repository.path))
    assert process.returncode == 1, process.stdout
    assert "Traceback" not in process.stderr
    return process.stderr


def executed(environment: dict[str, str], *arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "run_resolve_range.py"), *arguments],
        capture_output=True,
        env={**os.environ, **environment},
        timeout=60,
        check=False,
    )


def decoded(repository: Repository, environment: dict[str, str], *arguments: str) -> dict[str, Any]:
    process = executed(environment, *arguments, "--repo", str(repository.path))
    assert process.returncode == 0, process.stderr
    return json.loads(process.stdout.decode("utf-8"))


def message_file(repository: Repository, message: bytes) -> str:
    path = repository.path.parent / "message"
    path.write_bytes(message)
    return str(path)


def commit_raw(repository: Repository, message: bytes, name: bytes = b"raw.txt") -> None:
    (repository.path / os.fsdecode(name)).write_text("raw")
    repository.git("add", ".")
    tree = repository.git("write-tree")
    parent = repository.git("rev-parse", "HEAD")
    person = "Test <test@example.com> 1700000000 +0000"
    header = f"tree {tree}\nparent {parent}\nauthor {person}\ncommitter {person}\n\n"
    created = repository.git("hash-object", "-t", "commit", "-w", message_file(repository, header.encode() + message))
    repository.git("update-ref", "HEAD", created)


def endpoints(report: dict[str, Any]) -> tuple[str, str]:
    return report["from"], report["to"]


@pytest.mark.parametrize(
    ("older", "newer"),
    [("v1.2.0", "v1.10.0"), ("1.2.0", "1.10.0"), ("v1.2", "v1.2.1")],
)
def test_release_starts_at_latest_stable_for_both_spellings(repository: Repository, older: str, newer: str) -> None:
    repository.tagged(older, newer)
    repository.commit("after")
    assert endpoints(resolved(repository, "release")) == (newer, "HEAD")


def test_release_orders_by_version_and_not_by_date(repository: Repository) -> None:
    repository.tagged("v1.10.0", "v1.9.0")
    repository.commit("after")
    assert endpoints(resolved(repository, "release")) == ("v1.10.0", "HEAD")


@pytest.mark.parametrize(
    "prerelease",
    ["v2.0.0-beta.1", "v2.0.0-rc.1", "v2.0.0-alpha.1", "2.0.0b1", "2.0.0rc1", "2.0.0a1"],
)
def test_release_skips_every_prerelease(repository: Repository, prerelease: str) -> None:
    repository.tagged("v1.0.0", prerelease)
    assert endpoints(resolved(repository, "release")) == ("v1.0.0", "HEAD")


def test_release_at_tag_compares_with_previous_stable(repository: Repository) -> None:
    repository.tagged("v1.0.0", "v1.1.0-beta.1", "v1.1.0")
    assert endpoints(resolved(repository, "release")) == ("v1.0.0", "v1.1.0")


def test_release_at_annotated_tag_is_recognised(repository: Repository) -> None:
    repository.tagged("v1.0.0")
    repository.commit("next")
    repository.tag("v1.1.0", annotated=True)
    assert endpoints(resolved(repository, "release")) == ("v1.0.0", "v1.1.0")


def test_release_ignores_unreachable_tags(repository: Repository) -> None:
    repository.tagged("v1.0.0")
    repository.git("checkout", "-q", "-b", "side")
    repository.tagged("v9.0.0")
    repository.git("checkout", "-q", "main")
    repository.commit("after")
    assert endpoints(resolved(repository, "release")) == ("v1.0.0", "HEAD")


def test_two_stable_tags_on_one_commit_skip_to_a_different_commit(repository: Repository) -> None:
    repository.tagged("v1.0.0", "v1.1.0")
    repository.tag("1.1.0")
    report = resolved(repository, "release")
    assert report["from"] == "v1.0.0"
    assert report["commits"]


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("v1.1.0-beta.1", "v1.1.0-beta.2"),
        ("v1.1.0-beta.2", "v1.1.0-beta.10"),
        ("v1.1.0-beta.2", "v1.1.0-rc.1"),
        ("1.1.0b1", "1.1.0b2"),
        ("1.1.0b2", "1.1.0rc1"),
    ],
)
def test_beta_starts_at_latest_prerelease(repository: Repository, first: str, second: str) -> None:
    repository.tagged(first, second)
    repository.commit("after")
    assert endpoints(resolved(repository, "beta")) == (second, "HEAD")


def test_beta_at_tag_compares_with_previous_prerelease(repository: Repository) -> None:
    repository.tagged("v1.1.0-beta.1", "v1.1.0-beta.2")
    assert endpoints(resolved(repository, "beta")) == ("v1.1.0-beta.1", "v1.1.0-beta.2")


def test_beta_does_not_treat_alpha_as_a_boundary(repository: Repository) -> None:
    repository.tagged("v1.1.0-beta.1", "v1.2.0-alpha.1")
    assert endpoints(resolved(repository, "beta")) == ("v1.1.0-beta.1", "HEAD")


def test_only_alpha_tags_leave_beta_without_a_start(repository: Repository) -> None:
    repository.tagged("v1.1.0-alpha.1")
    assert "--from" in refused(repository, "beta")


def test_beta_after_stable_starts_at_the_stable_release(repository: Repository) -> None:
    repository.tagged("v1.1.0-beta.1", "v1.1.0")
    repository.commit("after")
    report = resolved(repository, "beta")
    assert endpoints(report) == ("v1.1.0", "HEAD")
    assert "newer than the last beta" in report["notes"][0]


def test_beta_at_stable_release_shows_changes_since_last_beta(repository: Repository) -> None:
    repository.tagged("v1.1.0-beta.1", "v1.1.0")
    report = resolved(repository, "beta")
    assert endpoints(report) == ("v1.1.0-beta.1", "v1.1.0")
    assert report["notes"]


def test_new_beta_cycle_at_tag_starts_at_stable_between(repository: Repository) -> None:
    repository.tagged("v1.1.0-beta.1", "v1.1.0", "v1.2.0-beta.1")
    assert endpoints(resolved(repository, "beta")) == ("v1.1.0", "v1.2.0-beta.1")


def test_new_beta_cycle_ahead_of_tag_starts_at_the_beta(repository: Repository) -> None:
    repository.tagged("v1.1.0", "v1.2.0-beta.1")
    repository.commit("after")
    assert endpoints(resolved(repository, "beta")) == ("v1.2.0-beta.1", "HEAD")


@pytest.mark.parametrize("mode", ["release", "beta"])
def test_no_tags_suggest_from(repository: Repository, mode: str) -> None:
    repository.commit("only")
    message = refused(repository, mode)
    assert "no version tags" in message
    assert "--from" in message


@pytest.mark.parametrize("mode", ["release", "beta"])
def test_only_non_version_tags_suggest_from(repository: Repository, mode: str) -> None:
    repository.tagged(
        "nightly", "deploy-2026", "release-candidate", "v1", "v1.2.0-foo", "pkg-1.2.0", "1.2.0.dev1", "1.2.0.post1"
    )
    assert "--from" in refused(repository, mode)


def test_non_version_tags_are_ignored_among_real_ones(repository: Repository) -> None:
    repository.tagged("v1.0.0", "nightly", "v99", "pkg-9.9.9")
    assert endpoints(resolved(repository, "release")) == ("v1.0.0", "HEAD")


def test_first_tag_at_head_has_nothing_to_compare_with(repository: Repository) -> None:
    repository.tagged("v1.0.0")
    assert "--from" in refused(repository, "release")


def test_only_stable_tags_refuse_beta(repository: Repository) -> None:
    repository.tagged("v1.0.0")
    repository.commit("after")
    assert "--from" in refused(repository, "beta")


def test_from_and_to_override_tags(repository: Repository) -> None:
    start = repository.commit("start")
    middle = repository.commit("middle")
    repository.commit("end")
    report = resolved(repository, "release", "--from", start, "--to", middle)
    assert endpoints(report) == (start, middle)
    assert [commit["subject"] for commit in report["commits"]] == ["middle"]


def test_to_moves_the_automatic_start(repository: Repository) -> None:
    repository.tagged("v1.0.0", "v1.1.0", "v1.2.0")
    assert endpoints(resolved(repository, "release", "--to", "v1.1.0")) == ("v1.0.0", "v1.1.0")


def test_unknown_reference_is_refused(repository: Repository) -> None:
    repository.commit("only")
    assert "nope" in refused(repository, "release", "--from", "nope")


def test_outside_a_repository_is_refused(tmp_path: Path) -> None:
    process = run_script("run_resolve_range.py", "release", "--repo", str(tmp_path))
    assert process.returncode == 1
    assert "Traceback" not in process.stderr


def test_output_carries_commits_and_files(repository: Repository) -> None:
    repository.tagged("v1.0.0")
    commit = repository.commit("Add export", "Long body\n\nwith two paragraphs")
    (repository.path / "file1.txt").unlink()
    repository.git("add", ".")
    repository.git("commit", "-q", "-m", "Remove first | file")
    report = resolved(repository, "release")
    assert report["commits"][0]["subject"] == "Remove first | file"
    assert report["commits"][1] == {
        "hash": commit,
        "subject": "Add export",
        "body": "Long body\n\nwith two paragraphs",
    }
    assert {"status": "A", "path": "file2.txt"} in report["files"]
    assert {"status": "D", "path": "file1.txt"} in report["files"]


def test_label_is_safe_for_a_directory_name(repository: Repository) -> None:
    repository.tagged("v1.0.0", "v1.1.0")
    assert resolved(repository, "release")["label"] == "v1.1.0"
    repository.commit("after")
    assert resolved(repository, "release")["label"] == "v1.1.0--HEAD"


def test_build_metadata_is_accepted_and_does_not_order(repository: Repository) -> None:
    repository.tagged("v1.0.0+build9", "v1.0.1+build1")
    repository.commit("after")
    assert endpoints(resolved(repository, "release")) == ("v1.0.1+build1", "HEAD")


def test_from_with_tagged_end_reports_the_tag(repository: Repository) -> None:
    start = repository.commit("start")
    repository.tagged("v1.0.0")
    report = resolved(repository, "release", "--from", start)
    assert endpoints(report) == (start, "v1.0.0")


@pytest.mark.parametrize("arguments", [["release"], ["beta"], ["release", "--from", "HEAD"]])
def test_missing_git_is_a_short_failure(repository: Repository, tmp_path: Path, arguments: list[str]) -> None:
    repository.tagged("v1.0.0")
    empty = tmp_path / "empty"
    empty.mkdir()
    process = executed({"PATH": str(empty)}, *arguments, "--repo", str(repository.path))
    assert process.returncode == 1
    assert process.stdout == b""
    assert process.stderr.decode().startswith("error: git is not available")
    assert b"Traceback" not in process.stderr


LOCALES = [
    pytest.param({"LC_ALL": "C.UTF-8"}, id="utf8"),
    pytest.param({"LC_ALL": "C"}, id="c"),
    pytest.param({"LC_ALL": "C", "PYTHONUTF8": "0", "PYTHONCOERCECLOCALE": "0"}, id="ascii"),
]


@pytest.mark.parametrize("environment", LOCALES)
def test_latin1_message_is_replaced_and_the_rest_stays_correct(
    repository: Repository, environment: dict[str, str]
) -> None:
    repository.tagged("v1.0.0")
    commit_raw(repository, b"caf\xe9 subject\n\nna\xefve body\n")
    repository.commit("clean after", "clean body")
    report = decoded(repository, environment, "release")
    assert endpoints(report) == ("v1.0.0", "HEAD")
    assert [(commit["subject"], commit["body"]) for commit in report["commits"]] == [
        ("clean after", "clean body"),
        ("caf\ufffd subject", "na\ufffdve body"),
    ]
    assert {"status": "A", "path": "raw.txt"} in report["files"]


@pytest.mark.parametrize("environment", LOCALES)
def test_non_utf8_file_name_is_replaced_and_the_rest_stays_correct(
    repository: Repository, environment: dict[str, str]
) -> None:
    repository.tagged("v1.0.0")
    commit_raw(repository, b"raw name\n", b"caf\xe9.txt")
    repository.commit("after")
    report = decoded(repository, environment, "release")
    assert [commit["subject"] for commit in report["commits"]] == ["after", "raw name"]
    assert report["files"] == [
        {"status": "A", "path": "caf\ufffd.txt"},
        {"status": "A", "path": "file2.txt"},
    ]


@pytest.mark.parametrize("environment", LOCALES)
def test_declared_commit_encoding_is_converted(repository: Repository, environment: dict[str, str]) -> None:
    repository.tagged("v1.0.0")
    (repository.path / "declared.txt").write_text("declared")
    repository.git("add", ".")
    message = message_file(repository, "caf\u00e9\n".encode("latin-1"))
    repository.git("-c", "i18n.commitEncoding=latin-1", "commit", "-q", "-F", message)
    assert decoded(repository, environment, "release")["commits"][0]["subject"] == "caf\u00e9"


@pytest.mark.parametrize("environment", LOCALES)
def test_log_output_encoding_setting_does_not_corrupt_subjects(
    repository: Repository, environment: dict[str, str]
) -> None:
    repository.tagged("v1.0.0")
    repository.commit("caf\u00e9")
    repository.git("config", "i18n.logOutputEncoding", "latin-1")
    assert decoded(repository, environment, "release")["commits"][0]["subject"] == "caf\u00e9"


@pytest.mark.parametrize("environment", LOCALES)
def test_non_utf8_tag_is_ignored_among_real_ones(repository: Repository, environment: dict[str, str]) -> None:
    repository.tagged("v1.0.0")
    repository.tag(os.fsdecode(b"caf\xe9"))
    repository.commit("after")
    assert endpoints(decoded(repository, environment, "release")) == ("v1.0.0", "HEAD")


@pytest.mark.parametrize("environment", LOCALES)
def test_non_ascii_digits_are_not_a_version(repository: Repository, environment: dict[str, str]) -> None:
    repository.tagged("v1.0.0")
    repository.tag("v\u0661.\u0662")
    repository.commit("after")
    assert endpoints(decoded(repository, environment, "release")) == ("v1.0.0", "HEAD")


@pytest.mark.parametrize("environment", LOCALES)
def test_non_utf8_reference_leaves_valid_json(repository: Repository, environment: dict[str, str]) -> None:
    repository.tagged("v1.0.0")
    name = os.fsdecode(b"caf\xe9")
    repository.tag(name)
    commit = repository.git("rev-parse", "HEAD")
    repository.commit("after")
    report = decoded(repository, environment, "release", "--from", name)
    assert report["from"] == "caf?"
    assert report["from_commit"] == commit
    assert [entry["subject"] for entry in report["commits"]] == ["after"]


def test_branch_named_like_a_version_gets_the_untagged_label(repository: Repository) -> None:
    repository.tagged("v1.0.0")
    repository.commit("after")
    repository.git("branch", "1.2")
    report = resolved(repository, "release", "--to", "1.2")
    assert endpoints(report) == ("v1.0.0", "1.2")
    assert report["label"] == "v1.0.0--1.2"


def test_branch_named_like_a_version_with_from_gets_the_untagged_label(repository: Repository) -> None:
    start = repository.commit("start")
    repository.commit("after")
    repository.git("branch", "1.2")
    assert resolved(repository, "release", "--from", start, "--to", "1.2")["label"] == f"{start}--1.2"


@pytest.mark.parametrize("annotated", [False, True], ids=["lightweight", "annotated"])
def test_real_tag_at_the_end_keeps_its_label(repository: Repository, annotated: bool) -> None:
    repository.tagged("v1.0.0")
    repository.commit("after")
    repository.tag("v1.1.0", annotated=annotated)
    repository.commit("later")
    report = resolved(repository, "release", "--to", "v1.1.0")
    assert endpoints(report) == ("v1.0.0", "v1.1.0")
    assert report["label"] == "v1.1.0"


def test_tag_wins_over_a_branch_of_the_same_name(repository: Repository) -> None:
    repository.tagged("v1.0.0")
    repository.commit("branch tip")
    repository.git("branch", "1.2")
    repository.commit("tag target")
    repository.tag("1.2")
    tagged_commit = repository.git("rev-parse", "refs/tags/1.2")
    report = resolved(repository, "release", "--to", "1.2")
    assert report["to_commit"] == tagged_commit
    assert report["label"] == "1.2"
    assert report["commits"][0]["subject"] == "tag target"


@pytest.mark.parametrize("flag", ["--from", "--to"])
def test_empty_reference_is_refused_by_its_flag(repository: Repository, flag: str) -> None:
    repository.tagged("v1.0.0")
    repository.commit("after")
    assert f"error: {flag} must not be empty" in refused(repository, "release", flag, "")

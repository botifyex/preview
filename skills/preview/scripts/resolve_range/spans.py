from pathlib import Path

from resolve_range.git import commit_of
from resolve_range.model import RangeFailure, Span, Version
from resolve_range.versions import reachable_versions


def tag_at(versions: list[Version], commit: str, end: str) -> str:
    matching = [version.tag for version in versions if version.commit == commit]
    return matching[-1] if matching else end


def earlier_than(candidates: list[Version], latest: Version) -> list[Version]:
    return [version for version in candidates if version.order < latest.order and version.commit != latest.commit]


def closing_span(candidates: list[Version], latest: Version, channel: str) -> Span:
    earlier = earlier_than(candidates, latest)
    if not earlier:
        raise RangeFailure(
            f"{latest.tag} is the first {channel} tag and the end of the range: "
            "nothing earlier to compare with, pass --from <ref>"
        )
    return Span(earlier[-1].tag, latest.tag)


def release_span(versions: list[Version], commit: str, end: str) -> Span:
    stable = [version for version in versions if version.stable]
    if not stable:
        raise RangeFailure(f"no stable version tag is reachable from {end}: pass --from <ref>")
    latest = stable[-1]
    if latest.commit == commit:
        return closing_span(stable, latest, "stable")
    return Span(latest.tag, end)


def beta_span(versions: list[Version], commit: str, end: str) -> Span:
    betas = [version for version in versions if version.beta]
    if not betas:
        raise RangeFailure(f"no beta or rc version tag is reachable from {end}: pass --from <ref>")
    latest = betas[-1]
    if latest.commit == commit:
        boundaries = [version for version in versions if version.beta or version.stable]
        return closing_span(boundaries, latest, "beta")
    stable = [version for version in versions if version.stable and version.order > latest.order]
    if not stable:
        return Span(latest.tag, end)
    newest = stable[-1]
    if newest.commit == commit:
        note = (
            f"{newest.tag} is a stable release at the end of the range, "
            f"showing what changed since the last beta {latest.tag}"
        )
        return Span(latest.tag, newest.tag, (note,))
    note = (
        f"stable {newest.tag} is newer than the last beta {latest.tag}, "
        f"so the range starts at {newest.tag}: earlier changes are already released"
    )
    return Span(newest.tag, end, (note,))


def automatic_span(repository: Path, mode: str, end: str) -> Span:
    commit = commit_of(repository, end)
    versions = reachable_versions(repository, end)
    if not versions:
        raise RangeFailure(f"no version tags are reachable from {end}: pass --from <ref>")
    if mode == "release":
        return release_span(versions, commit, end)
    return beta_span(versions, commit, end)


def explicit_span(repository: Path, start: str, end: str) -> Span:
    commit = commit_of(repository, end)
    return Span(start, tag_at(reachable_versions(repository, end), commit, end))

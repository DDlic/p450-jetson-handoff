#!/usr/bin/env python3
"""Fail-closed structural audit for the P450 handoff repository."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote


LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
IGNORED_PREFIXES = ("#", "http://", "https://", "mailto:", "tel:", "data:")


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=False
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout


def repository_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("run this script inside a Git repository")
    return Path(result.stdout.strip()).resolve()


def local_target(raw: str) -> str | None:
    value = raw.strip()
    if value.startswith("<") and ">" in value:
        value = value[1 : value.index(">")]
    else:
        value = value.split(maxsplit=1)[0]
    value = unquote(value).split("#", 1)[0].split("?", 1)[0]
    if not value or value.lower().startswith(IGNORED_PREFIXES):
        return None
    return value


def broken_links(root: Path) -> list[str]:
    failures: list[str] = []
    tracked_markdown = set(git(root, "ls-files", "*.md").splitlines())
    working_markdown = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*.md")
        if ".git" not in path.relative_to(root).parts
    }
    for relative in sorted(tracked_markdown | working_markdown):
        source = root / relative
        if not source.exists():
            continue
        content = source.read_text(encoding="utf-8")
        for match in LINK_RE.finditer(content):
            target = local_target(match.group(1))
            if target is None:
                continue
            resolved = (source.parent / target).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                failures.append(f"{relative}: target escapes repository: {target}")
                continue
            if not resolved.exists():
                line = content.count("\n", 0, match.start()) + 1
                failures.append(f"{relative}:{line}: missing local target: {target}")
    return failures


def deleted_paths(root: Path, base_ref: str) -> list[str]:
    output = git(root, "diff", "--name-status", "--find-renames", base_ref)
    return [line for line in output.splitlines() if line.startswith("D\t")]


def evidence_mutations(root: Path, base_ref: str) -> list[str]:
    output = git(root, "diff", "--name-status", "--find-renames", base_ref, "--", "evidence")
    return [line for line in output.splitlines() if not line.startswith("A\t")]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-ref",
        default="HEAD",
        help="Git reference used to detect deletion/evidence mutation (default: HEAD)",
    )
    args = parser.parse_args()

    try:
        root = repository_root()
        failures = broken_links(root)
        failures.extend(f"deleted tracked path: {line}" for line in deleted_paths(root, args.base_ref))
        failures.extend(
            f"existing evidence changed: {line}" for line in evidence_mutations(root, args.base_ref)
        )
        root_markdown = sorted(path.name for path in root.glob("*.md"))
        tracked = git(root, "ls-files").splitlines()
    except (OSError, UnicodeError, RuntimeError) as error:
        print(f"AUDIT_ERROR: {error}", file=sys.stderr)
        return 2

    print(f"repository={root}")
    print(f"tracked_files={len(tracked)}")
    print(f"root_markdown={len(root_markdown)}")
    print(f"base_ref={args.base_ref}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        print(f"AUDIT_FAIL findings={len(failures)}")
        return 1
    print("AUDIT_PASS no_broken_local_links=true no_tracked_deletions=true evidence_immutable=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

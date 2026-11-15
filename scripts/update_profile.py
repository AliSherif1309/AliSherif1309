"""Refresh only the marked profile section using public GitHub metadata."""
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

OWNER = "AliSherif1309"
README = Path(__file__).resolve().parents[1] / "README.md"
START = "<!-- RECENT-PROJECTS:START -->"
END = "<!-- RECENT-PROJECTS:END -->"


def fetch_repositories():
    repositories = []
    for page in range(1, 101):
        request = Request(
            f"https://api.github.com/users/{OWNER}/repos?type=owner&sort=pushed&per_page=100&page={page}",
            headers={"Accept": "application/vnd.github+json", "User-Agent": "aly-profile-refresh"},
        )
        with urlopen(request, timeout=30) as response:
            batch = json.load(response)
        if not isinstance(batch, list):
            raise ValueError("Unexpected repository response")
        repositories.extend(batch)
        if len(batch) < 100:
            return repositories
    raise ValueError("Pagination exceeded expected limit")


def escape(value):
    value = " ".join(str(value).split())
    return re.sub(r"([\\`*_{\[\]()#+.!|<>}])", r"\\\1", value)


def render(repositories):
    eligible = [r for r in repositories if not any(
        r.get(key) for key in ("private", "fork", "archived", "disabled")
    ) and r["name"].lower() != OWNER.lower() and r.get("pushed_at")]
    eligible.sort(key=lambda r: (r["pushed_at"], r["name"]), reverse=True)
    if not eligible:
        raise ValueError("No eligible public projects; preserving existing profile")
    lines = ["| Project | Latest push (UTC) |", "| --- | --- |"]
    for repo in eligible[:5]:
        name = repo["name"]
        description = repo.get("description")
        summary = f" — {escape(description[:160])}" if description else ""
        lines.append(f"| [{escape(name)}](https://github.com/{OWNER}/{name}){summary} | {repo['pushed_at'][:10]} |")
    return "\n".join(lines)


def update_readme(path, repositories):
    original = path.read_text(encoding="utf-8-sig")
    if original.count(START) != 1 or original.count(END) != 1:
        raise ValueError("Expected exactly one pair of profile markers")
    before, remainder = original.split(START)
    _, after = remainder.split(END)
    updated = before + START + "\n" + render(repositories) + "\n" + END + after
    if updated == original:
        return False
    temporary = path.with_suffix(".md.tmp")
    temporary.write_text(updated, encoding="utf-8", newline="\n")
    temporary.replace(path)
    return True


if __name__ == "__main__":
    print("Profile updated." if update_readme(README, fetch_repositories()) else "Profile is already current.")

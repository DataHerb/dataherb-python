import subprocess

import yaml
from click.testing import CliRunner

from dataherb.catalog import add as add_mod
from dataherb.catalog.add import add_repos, default_id, list_org_repos
from dataherb.catalog.config import load_config
from dataherb.catalog.resolve import build_catalog
from dataherb.catalog.util import split_front_matter
from dataherb.command import dataherb


def _git_repo(path, files):
    path.mkdir(parents=True)
    for name, text in files.items():
        (path / name).parent.mkdir(parents=True, exist_ok=True)
        (path / name).write_text(text)
    run = lambda *a: subprocess.run(
        ["git", *a], cwd=path, check=True, capture_output=True
    )  # noqa: E731
    run("init", "-q")
    run("add", ".")
    run("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init")


def test_default_id():
    assert default_id("DataHerb/dataset-covid-19", "dataset") == "covid-19"
    assert default_id("DataHerb/dataset", "dataset") == "dataset"
    assert default_id("acme/Orders", "") == "orders"


def test_add_pointer_inline_and_skip(project, tmp_path):
    # acme/orders has dataherb.json on the fake raw host and is already listed;
    # acme/raw has data only and is reached by cloning.
    _git_repo(tmp_path / "clones" / "acme" / "raw", {"data/x.csv": "a,b\n1,2\n3,4\n"})
    meta_dir = tmp_path / "git" / "acme" / "meta" / "HEAD"
    meta_dir.mkdir(parents=True)
    (meta_dir / "dataherb.yml").write_text("id: meta\nname: Meta\n")

    cfg = load_config(project / "dataherb.config.yml")
    res = add_repos(
        cfg,
        ["acme/orders", "acme/meta", "acme/raw", "acme/gone"],
        strip_prefix="",
        tags=("new",),
        clone_url_template=f"{tmp_path}/clones/{{repo}}",
    )
    kinds = {r.repo: r.kind for r in res}
    assert kinds == {
        "acme/orders": "skipped",
        "acme/meta": "pointer",
        "acme/raw": "inline",
        "acme/gone": "skipped",
    }
    meta, body = split_front_matter((project / "catalog" / "meta.md").read_text())
    assert meta == {"id": "meta", "repo": "acme/meta", "tags": ["new"]}
    assert body == ""
    raw, _ = split_front_matter((project / "catalog" / "raw.md").read_text())
    assert raw["inline"] is True and raw["repo"] == "acme/raw"
    r0 = raw["datapackage"]["resources"][0]
    assert r0["path"] == "data/x.csv" and r0["rows"] == 2
    assert not (project / "catalog" / "gone.md").exists()

    ds = {
        d["id"]: d
        for d in build_catalog(load_config(project / "dataherb.config.yml")).datasets
    }
    assert ds["meta"]["name"] == "Meta"
    assert ds["raw"]["resources"][0]["url"].endswith("/git/acme/raw/HEAD/data/x.csv")


def test_list_org_repos(monkeypatch):
    import json

    seen = []

    def fake_get(url, headers=None, timeout=20.0):
        seen.append(url)
        return json.dumps(
            [
                {"name": "dataset-a", "full_name": "o/dataset-a"},
                {"name": "Dataset-b", "full_name": "o/Dataset-b", "archived": True},
                {"name": "tool", "full_name": "o/tool"},
            ]
        ).encode()

    monkeypatch.setattr(add_mod, "http_get", fake_get)
    assert list_org_repos("o", "dataset") == ["o/dataset-a"]
    assert list_org_repos("o", "dataset", include_archived=True) == [
        "o/Dataset-b",
        "o/dataset-a",
    ]
    assert seen[0].startswith("https://api.github.com/orgs/o/repos?")


def test_cli_dry_run(project):
    meta_dir = project / "git" / "acme" / "meta" / "HEAD"
    meta_dir.mkdir(parents=True)
    (meta_dir / "dataherb.json").write_text("{}")
    res = CliRunner().invoke(
        dataherb,
        [
            "catalog",
            "add",
            "-c",
            str(project / "dataherb.config.yml"),
            "--dry-run",
            "acme/meta",
        ],
    )
    assert res.exit_code == 0, res.output
    assert "pointer" in res.output and "would add 1 of 1" in res.output
    assert not (project / "catalog" / "meta.md").exists()


def test_force_keeps_markdown_body(project):
    meta_dir = project / "git" / "acme" / "meta" / "HEAD"
    meta_dir.mkdir(parents=True)
    (meta_dir / "dataherb.json").write_text("{}")
    entry = project / "catalog" / "meta.md"
    entry.write_text("---\nid: meta\nrepo: acme/meta\n---\n\nHand-written notes.\n")
    cfg = load_config(project / "dataherb.config.yml")
    [r] = add_repos(cfg, ["acme/meta"], tags=("x",), force=True)
    assert r.kind == "pointer"
    data, body = split_front_matter(entry.read_text())
    assert data["tags"] == ["x"] and body.strip() == "Hand-written notes."


def test_yml_format(project):
    meta_dir = project / "git" / "acme" / "meta" / "HEAD"
    meta_dir.mkdir(parents=True)
    (meta_dir / "dataherb.json").write_text("{}")
    add_repos(load_config(project / "dataherb.config.yml"), ["acme/meta"], fmt="yml")
    assert (
        yaml.safe_load((project / "catalog" / "meta.yml").read_text())["repo"]
        == "acme/meta"
    )

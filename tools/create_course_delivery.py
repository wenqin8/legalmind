"""Create a verified course ZIP from committed files plus the original plan."""
import argparse
import hashlib
import json
import os
import posixpath
import re
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
PLAN = "output/pdf/法律咨询Agent一个月开发计划.pdf"
PLAN_SHA256 = "9a49723fee1ad8bb1610a92bc5c088d5f73e12f622859681f2cc2669c61ebc1d"
DECISION = "docs/acceptance/m4-project-acceptance-20261002.json"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def committed_files(commit):
    names = git("ls-tree", "-r", "-z", "--name-only", commit).decode().split("\0")
    names = sorted(name for name in names if name)
    requests = "".join(f"{commit}:{name}\n" for name in names).encode()
    response = subprocess.run(["git", "cat-file", "--batch"], input=requests,
        cwd=ROOT, stdout=subprocess.PIPE, check=True).stdout
    files = {}
    offset = 0
    for name in names:
        end = response.index(b"\n", offset)
        _, kind, size = response[offset:end].split()
        if kind != b"blob":
            raise ValueError("Non-file Git entry: " + name)
        offset = end + 1
        files[name] = response[offset:offset + int(size)]
        offset += int(size) + 1
    if offset != len(response):
        raise ValueError("Unexpected Git batch response")
    return files


def validate_contents(files):
    forbidden = []
    for name in files:
        parts = Path(name).parts
        if name.startswith("/") or ".." in parts or any(part in {
            ".git", ".venv", "node_modules", "__pycache__", "tmp", "models", "chroma"
        } for part in parts):
            forbidden.append(name)
        if any(part.startswith(".env") and part != ".env.example" for part in parts):
            forbidden.append(name)
        if name.endswith((".db", ".sqlite", ".zip")):
            forbidden.append(name)
    if forbidden:
        raise ValueError("Forbidden archive paths: " + repr(forbidden))
    from dotenv import dotenv_values
    secrets = []
    for relative in ("backend/.env", "frontend/.env", "deployment/.env"):
        path = ROOT / relative
        if path.exists():
            for key, value in dotenv_values(path).items():
                if value and len(value) >= 16 and re.search(r"secret|api.?key|password|credential", key, re.I):
                    secrets.append(value.encode())
    suspect = [name for name, data in files.items() if
        any(secret in data for secret in secrets)
        or re.search(rb"sk-[A-Za-z0-9]{24,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", data)]
    if suspect:
        raise ValueError("Secret scan requires review in: " + repr(suspect))
    broken = []
    for name, data in files.items():
        if not name.endswith(".md"):
            continue
        for match in re.finditer(r"\[[^\]\n]+\]\(([^)\n]+)\)", data.decode("utf-8-sig")):
            target = match.group(1).strip().strip("<>")
            if target.startswith("#") or re.match(r"^(?:https?://|mailto:|app://|codex://)", target):
                continue
            target = unquote(target.split("#", 1)[0]).replace("\\", "/")
            target = re.sub(r":\d+$", "", target)
            if target.startswith(ROOT.as_posix() + "/"):
                target = target[len(ROOT.as_posix()) + 1:]
            else:
                target = posixpath.normpath(posixpath.join(posixpath.dirname(name), target))
            if target not in files and not any(key.startswith(target.rstrip("/") + "/") for key in files):
                broken.append({"document": name, "target": target})
    if broken:
        raise ValueError("Broken local links: " + repr(broken))


def build(commit_ref, output):
    output = output.resolve()
    manifest_path = output.with_suffix(".manifest.json")
    if output.parent != (ROOT / "output/delivery").resolve():
        raise ValueError("Archive must be directly inside output/delivery")
    if output.exists() or manifest_path.exists():
        raise ValueError("Refusing to overwrite an existing delivery")
    commit = git("rev-parse", "--verify", commit_ref + "^{commit}").decode().strip()
    m4 = git("rev-parse", "m4^{commit}").decode().strip()
    tags = {}
    for tag in git("tag", "--list").decode().splitlines():
        tags[tag] = {"tag_object": git("rev-parse", tag).decode().strip(),
            "commit": git("rev-parse", tag + "^{commit}").decode().strip()}
    files = committed_files(commit)
    # Prior delivery manifests describe separate historical assets, not this ZIP.
    files = {name: data for name, data in files.items() if not name.startswith("output/delivery/")}
    plan = (ROOT / PLAN).read_bytes()
    if digest(plan) != PLAN_SHA256:
        raise ValueError("Original plan fingerprint changed")
    files[PLAN] = plan
    decision = json.loads(files[DECISION])
    if not decision["course_mvp_acceptance_passed"] or decision["ai_review_passed_questions"] != 24:
        raise ValueError("Project acceptance is not complete")
    smoke_path = "docs/acceptance/m4-deployment-smoke-20261002-run1.json"
    runtime_path = "docs/acceptance/m4-deployment-runtime-20261002-run1.json"
    smoke, runtime = (json.loads(files[name]) for name in (smoke_path, runtime_path))
    if not smoke["passed"] or not runtime["passed"]:
        raise ValueError("Current deployment verification did not pass")
    files["DELIVERY.md"] = (
        "# LegalMind M4 最终课程交付\n\n"
        f"交付日期：2026-10-02（Asia/Shanghai）。源码提交：`{commit}`；M4提交：`{m4}`。\n\n"
        "本地课程MVP及项目方认可的AI法律内容复核通过，24/24未发现阻断性问题。"
        "AI复核非独立专家认证；严格依赖安全审计未完全通过，公网生产部署不在范围。\n\n"
        "当前专用Docker环境烟测14/14、运行检查9/9通过，真实模型调用0；不是新建干净卷或新法律模型重验。\n\n"
        "先读[最终验收决定](docs/acceptance/m4-project-acceptance-20261002.md)、"
        "[提交前复验](docs/acceptance/m4-submission-closeout-20261002.md)、"
        "[运行入口](README.md)及[部署说明](deployment/README.md)。\n\n"
        "包内仅含配置模板；自行配置密钥。原始开发计划PDF保持校验值，"
        "历史失败、人工空表和原专家门槛保留原状态。"
        "全部阶段标签与校验结果记录在随ZIP交付的外部manifest；本包不含Git历史。\n"
    ).encode()
    validate_contents(files)
    entries = [{"path": name, "bytes": len(data), "sha256": digest(data)} for name, data in sorted(files.items())]
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(name, data)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None or sorted(archive.namelist()) != sorted(files):
            raise ValueError("Archive CRC or inventory mismatch")
        if not all(digest(archive.read(row["path"])) == row["sha256"] for row in entries):
            raise ValueError("Archive entry fingerprint mismatch")
    report = {"recorded_at": datetime.now(timezone.utc).isoformat(), "client_date": "2026-10-02",
        "archive": output.relative_to(ROOT).as_posix(), "archive_sha256": digest(output.read_bytes()),
        "archive_bytes": output.stat().st_size, "file_count": len(entries),
        "uncompressed_bytes": sum(row["bytes"] for row in entries), "source_commit": commit,
        "m4_commit": m4, "stage_tags": tags, "requires_base_archive": False,
        "acceptance": {"course_mvp_passed": True, "project_approved_ai_review_passed": True,
            "ai_review_passed_questions": 24, "current_docker_smoke_checks_passed": 14,
            "current_docker_runtime_checks_passed": 9, "python_dependency_audit_passed": False,
            "public_production_deployment_in_scope": False, "independent_expert_certified": False,
            "remote_upload_certified_by_this_archive": False},
        "verification": {"crc_and_each_entry_sha256_passed": True, "configured_secrets_found": 0,
            "broken_local_links": 0, "live_data_or_dependencies_included": False,
            "real_model_calls": 0, "original_plan_sha256": PLAN_SHA256},
        "files": entries}
    with manifest_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({key: report[key] for key in ["archive", "archive_sha256", "file_count", "source_commit", "verification"]}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", default="HEAD")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.commit, args.output)


if __name__ == "__main__":
    main()

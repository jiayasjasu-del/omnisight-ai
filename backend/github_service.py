"""GitHub integration for human-approved draft pull requests.

Prepares and submits draft pull requests for verified UI repairs ONLY after
explicit reviewer inspection and approval in the OmniSight dashboard.
Never merges pull requests, never applies unreviewed AI code, and never
exposes or logs GitHub access tokens.
"""

from __future__ import annotations

import base64
import os
import re
from typing import Any
import httpx


def _sanitize_token(text: str) -> str:
    """Ensure GitHub tokens and credentials are never exposed in messages or logs."""
    text = re.sub(r"ghp_[a-zA-Z0-9_\-]{15,}", "ghp_***[REDACTED]***", text)
    text = re.sub(r"github_pat_[a-zA-Z0-9_\-]{15,}", "github_pat_***[REDACTED]***", text)
    text = re.sub(r"Bearer\s+[a-zA-Z0-9_\-\.]{15,}", "Bearer ***[REDACTED]***", text)
    return text


def get_github_config() -> dict[str, Any]:
    """Retrieve server-side GitHub configuration without exposing tokens."""
    token = os.getenv("GITHUB_TOKEN", "").strip()
    repository = os.getenv("GITHUB_REPOSITORY", "jiayasjasu-del/omnisight-ai").strip()
    base_branch = os.getenv("GITHUB_BASE_BRANCH", "feature/visual-diff-report").strip()

    return {
        "configured": bool(token),
        "repository": repository,
        "base_branch": base_branch,
        "message": (
            "GitHub integration is configured."
            if token
            else "GITHUB_TOKEN is not configured in backend environment."
        ),
    }


def generate_repair_diff(
    proposal: dict[str, Any],
    target_file: str = "frontend/src/AuditFixture.css",
) -> tuple[str, str]:
    """Generate the exact proposed patch and unified diff text for reviewer inspection."""
    code = proposal.get("code", "").strip()
    if not code:
        code = "/* Proposed repair */"

    # Format CSS lines as diff additions
    patch_lines = [f"+{line}" for line in code.splitlines()]
    patch_content = "\n".join(patch_lines)

    diff_text = (
        f"--- a/{target_file}\n"
        f"+++ b/{target_file}\n"
        f"@@ -0,0 +1,{len(patch_lines)} @@\n"
        f"{patch_content}\n"
    )

    return code, diff_text


def preview_draft_pr(
    job_id: str,
    finding_index: int,
    jobs_store: dict[str, Any],
    target_file: str | None = None,
) -> dict[str, Any]:
    """Assemble all draft PR metadata and exact diff for reviewer preview and confirmation."""
    job = jobs_store.get(job_id)
    if not job:
        raise ValueError(f"Job '{job_id}' not found.")

    findings = job.get("findings", [])
    if finding_index < 0 or finding_index >= len(findings):
        raise ValueError(f"Finding index {finding_index} is out of bounds for job '{job_id}'.")

    finding = findings[finding_index]
    proposal = finding.get("repair_proposal")
    if not proposal:
        raise ValueError("The selected finding does not contain a repair proposal.")

    config = get_github_config()
    chosen_target_file = target_file or "frontend/src/AuditFixture.css"
    code, diff_text = generate_repair_diff(proposal, chosen_target_file)

    clean_title = proposal.get("title", "Contain wide table in parent wrapper")
    short_slug = re.sub(r"[^a-zA-Z0-9]+", "-", clean_title.lower()).strip("-")[:32]
    proposed_branch = f"fix/{short_slug}-{job_id[:8]}"

    pr_title = f"fix(ui): {clean_title.lower()}"
    pr_body = (
        f"## OmniSight Automated Repair Proposal (Draft)\n\n"
        f"**Audit Job ID:** `{job_id}`\n"
        f"**Finding Code:** `{finding.get('code', 'ui_finding')}`\n"
        f"**Viewport:** `{finding.get('viewport', 'all')}`\n\n"
        f"### Evidence\n"
        f"> {finding.get('evidence', 'No specific evidence string.')}\n\n"
        f"### Reviewer Explanation\n"
        f"{proposal.get('explanation', '')}\n\n"
        f"### Proposed CSS\n"
        f"```css\n{code}\n```\n\n"
        f"---\n"
        f"*Note: This draft pull request was prepared upon explicit human reviewer "
        f"inspection and approval in the OmniSight dashboard. It must be tested and reviewed "
        f"before merging.*"
    )

    return {
        "status": "ready",
        "github_configured": config["configured"],
        "repository": config["repository"],
        "base_branch": config["base_branch"],
        "proposed_branch": proposed_branch,
        "target_file": chosen_target_file,
        "title": pr_title,
        "description": pr_body,
        "diff": diff_text,
        "repair_proposal": proposal,
    }


def create_draft_pr(
    job_id: str,
    finding_index: int,
    approved: bool,
    jobs_store: dict[str, Any],
    repository: str | None = None,
    base_branch: str | None = None,
    proposed_branch: str | None = None,
    target_file: str | None = None,
    pr_title: str | None = None,
    pr_body: str | None = None,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Create a draft pull request on GitHub after explicit human reviewer approval.

    Never merges or modifies code automatically.
    """
    if not approved:
        return {
            "status": "rejected",
            "message": "Reviewer rejected the repair proposal. No pull request was created.",
            "pr_url": None,
            "pr_number": None,
            "draft": True,
        }

    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        return {
            "status": "not_configured",
            "message": (
                "GITHUB_TOKEN environment variable is not configured. "
                "Set GITHUB_TOKEN on the backend server to create GitHub draft pull requests."
            ),
            "pr_url": None,
            "pr_number": None,
            "draft": True,
        }

    preview = preview_draft_pr(job_id, finding_index, jobs_store, target_file)

    repo = repository or preview["repository"]
    base = base_branch or preview["base_branch"]
    branch = proposed_branch or preview["proposed_branch"]
    file_path = target_file or preview["target_file"]
    title = pr_title or preview["title"]
    body = pr_body or preview["description"]
    code, _ = generate_repair_diff(preview["repair_proposal"], file_path)

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    own_client = False
    if client is None:
        client = httpx.Client(base_url="https://api.github.com", headers=headers, timeout=15.0)
        own_client = True

    try:
        # 1. Fetch base branch commit SHA
        ref_res = client.get(f"/repos/{repo}/git/ref/heads/{base}")
        if ref_res.status_code != 200:
            raise RuntimeError(f"Base branch '{base}' not found on {repo} ({ref_res.status_code}): {ref_res.text}")
        base_sha = ref_res.json()["object"]["sha"]

        # 2. Create the new proposed branch
        create_branch_res = client.post(
            f"/repos/{repo}/git/refs",
            json={"ref": f"refs/heads/{branch}", "sha": base_sha},
        )
        if create_branch_res.status_code not in (200, 201):
            raise RuntimeError(f"Failed to create branch '{branch}' ({create_branch_res.status_code}): {create_branch_res.text}")

        # 3. Read existing file content on proposed branch if it exists
        content_res = client.get(f"/repos/{repo}/contents/{file_path}", params={"ref": branch})
        file_sha = None
        new_content_str = code + "\n"

        if content_res.status_code == 200:
            file_data = content_res.json()
            file_sha = file_data.get("sha")
            try:
                raw_existing = base64.b64decode(file_data.get("content", "")).decode("utf-8")
                new_content_str = raw_existing.rstrip() + "\n\n/* OmniSight automated fix */\n" + code + "\n"
            except Exception:
                pass

        # 4. Commit file update to the new branch
        commit_payload: dict[str, Any] = {
            "message": f"fix(ui): apply human-approved repair for {preview['repair_proposal'].get('title', 'UI defect')}",
            "content": base64.b64encode(new_content_str.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        if file_sha:
            commit_payload["sha"] = file_sha

        put_res = client.put(f"/repos/{repo}/contents/{file_path}", json=commit_payload)
        if put_res.status_code not in (200, 201):
            raise RuntimeError(f"Failed to commit change to '{file_path}' ({put_res.status_code}): {put_res.text}")

        # 5. Open draft pull request
        pr_payload = {
            "title": title,
            "body": body,
            "head": branch,
            "base": base,
            "draft": True,  # Strictly draft pull request
        }
        pr_res = client.post(f"/repos/{repo}/pulls", json=pr_payload)
        if pr_res.status_code not in (200, 201):
            raise RuntimeError(f"Failed to open draft pull request ({pr_res.status_code}): {pr_res.text}")

        pr_data = pr_res.json()
        return {
            "status": "created",
            "message": f"Draft pull request #{pr_data.get('number')} created successfully.",
            "pr_url": pr_data.get("html_url"),
            "pr_number": pr_data.get("number"),
            "draft": pr_data.get("draft", True),
            "branch": branch,
            "repository": repo,
            "base_branch": base,
        }

    except Exception as exc:
        sanitized = _sanitize_token(str(exc))
        return {
            "status": "error",
            "message": "Failed to create draft PR on GitHub.",
            "detail": sanitized,
            "pr_url": None,
            "pr_number": None,
            "draft": True,
        }
    finally:
        if own_client:
            client.close()

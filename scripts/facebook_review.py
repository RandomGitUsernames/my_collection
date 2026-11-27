"""Read-only upstream triage. Never execute upstream code or publish an IPA."""
import json
import os
import re
import subprocess
import tempfile

UPSTREAM = "shajon-dev/Facebook-Plus"
REMOTE = "https://github.com/" + UPSTREAM + ".git"
# Comparison reference only: not an approved or fully audited commit.
REFERENCE = "726d4908e9894829f71fadf5006235a5bfdf1df2"
PATTERNS = {
    "credential or session handling": r"SecItem|kSecAttr|password|access.?token|session.?token|cookie|Authorization",
    "network or external destinations": r"https?://|NSURLSession|NSURLConnection|XMLHttpRequest|uploadTask|WebSocket",
    "injection or process execution": r"dlopen|dlsym|fishhook|subprocess\.|shell=True|eval\(|popen\(",
    "diagnostics or sensitive logging": r"FBP_DIAG|FBPDiagLog|NSLog|os_log",
    "entitlements or app groups": r"keychain-access-groups|application-groups|SecTaskCopyValueForEntitlement|entitlement",
}

def run(args, cwd=None, allowed=(0,)):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                            errors="replace", timeout=120, check=False)
    if result.returncode not in allowed:
        raise RuntimeError(f"{args[0]} failed with exit code {result.returncode}")
    return result.stdout.strip()

def main():
    release = json.loads(run(["gh", "api", f"repos/{UPSTREAM}/releases/latest"]))
    tag = release["tag_name"]
    if not re.fullmatch(r"v?[0-9]+(?:\.[0-9]+){1,4}", tag):
        raise ValueError("Unexpected release tag format; human review required")
    if release.get("draft") or release.get("prerelease"):
        raise ValueError("Expected a stable published release")
    with tempfile.TemporaryDirectory() as directory:
        def git(*args, allowed=(0,)):
            return run(["git", *args], cwd=directory, allowed=allowed)
        git("init", "--quiet")
        git("fetch", "--no-tags", "--depth=1", REMOTE, f"refs/tags/{tag}")
        commit = git("rev-parse", "FETCH_HEAD^{commit}")
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise ValueError("Unexpected commit identifier")
        if commit != REFERENCE:
            git("fetch", "--no-tags", "--depth=1", REMOTE, REFERENCE)
        changed = git("diff", "--no-ext-diff", "--name-status", REFERENCE, commit)
        flags = {}
        for label, pattern in PATTERNS.items():
            found = git("grep", "-I", "-l", "-i", "-E", pattern, commit,
                        "--", "src", "FBPNotifyBridge", "OpenInFacebookSafariExtension",
                        "build.py", "Makefile", ".github/workflows", allowed=(0, 1))
            flags[label] = found.splitlines() if found else []
        main_head = git("ls-remote", REMOTE, "refs/heads/main").split()
        report = {
            "release": tag, "commit": commit, "comparison_reference_not_approved": REFERENCE,
            "main_tip": main_head[0] if main_head else None,
            "changed_files": changed.splitlines(), "flagged_files": flags,
            "decision": "HUMAN REVIEW REQUIRED; not a security audit or build approval",
        }
        print(json.dumps(report, ensure_ascii=True))
    title = f"Facebook Plus review required: {tag} ({commit[:12]})"
    repository = os.environ["REVIEW_REPOSITORY"]
    existing = run(["gh", "api", "--paginate", f"repos/{repository}/issues?state=all&per_page=100",
                    "--jq", ".[].title"])
    if title in existing.splitlines():
        print("Review issue already exists.")
        return
    counts = "\n".join(f"- {label}: {len(files)} matching files" for label, files in flags.items())
    body = (
        f"Upstream release: https://github.com/{UPSTREAM}/releases/tag/{tag}\n\n"
        f"Exact source commit: \`{commit}\`\n\n"
        f"Comparison (reference is NOT approved): https://github.com/{UPSTREAM}/compare/{REFERENCE}...{commit}\n\n"
        f"Changed files relative to reference: {len(report['changed_files'])}\n\n"
        f"Keyword triage (not findings of malware):\n{counts}\n\n"
        "Full flagged-file list is in the Actions run log. Review source and dependency changes manually. "
        "No upstream code was executed; no IPA was built or published. Closing this issue does not approve a build."
    )
    print(run(["gh", "issue", "create", "--repo", repository, "--title", title, "--body", body]))

if __name__ == "__main__":
    main()

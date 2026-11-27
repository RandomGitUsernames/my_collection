# Personal App Updates for AltStore Classic

A small, allowlisted release tracker, not an IPA mirror or a security certification. No paid signing service, personal access token, Apple ID, or GitHub Pages setup is necessary. The public repository contains only code and release metadata, never your personal IPA.

## Set up once on a Mac

1. Unzip the supplied archive. Create an **empty public repository** called `personal-altstore` at https://github.com/new (do not add a README or license on GitHub). A public repo is required for anonymous AltStore access to the raw JSON. Do not put credentials or personal IPA files in it.
2. In Terminal, `cd` into the extracted `personal-altstore` directory. Run these commands (replace `YOUR_USERNAME`):

```sh
git init -b main
git add .
git commit -m "Initial personal AltStore source"
git remote add origin https://github.com/YOUR_USERNAME/personal-altstore.git
git push -u origin main
```

Authenticate GitHub normally if prompted (e.g. GitHub CLI or GitHub Desktop). GitHub does not accept your account password for Git HTTPS pushes. If Git requires your name/email, configure those first. Alternatively, use GitHub Desktop to publish the extracted directory as a public repository, ensuring the hidden `.github` directory is included.

3. Open your repository on GitHub → Actions → **Update AltStore source**. If necessary enable workflows, then select **Run workflow** on `main`. The initial push may already have started it. Open `status.json` after the run; this reports each project's result. If the publish step has a permission error, check Settings → Actions → General and repository/organization policies allow the workflow's `contents: write` permission. No personal access token is needed.
4. Once the first run has completed, open this URL in Safari (replace `YOUR_USERNAME`):

```
https://raw.githubusercontent.com/YOUR_USERNAME/personal-altstore/main/source.json
```

You should see JSON, not a GitHub HTML page, a 404, or a login screen. Confirm there is a YouMod entry under `apps` if the validation passed, plus project entries under `news`. Do not add the GitHub repository homepage itself. Open AltStore Classic → Sources (or Browse → Sources) → + → paste this exact raw URL → Add Source.

## What is automated?

- Daily at 09:23 UTC (03:23 US Central standard time / 04:23 daylight time), and on manual request, GitHub checks the latest stable release from the four allowlisted projects. GitHub schedules may be delayed.
- YouMod: the updater accepts only one matching IPA under its original GitHub project. It downloads temporarily to inspect metadata, checks the asset size and GitHub-provided SHA-256 (when available), reads actual bundle ID/version/build and privacy descriptions, and uses the macOS codesign utility to inspect entitlements. It does not execute the app or publish its binary. If checks fail, inspect `status.json`; new unvalidated listings are withheld. On API failure, a previous validated listing may be retained and marked stale. Metadata inspection is not malware scanning or signature trust verification.
- Facebook Plus, YTMusicUltimate and EeveeSpotify: monitor releases and create News entries pointing directly to the original developers. The updater will not download or redistribute their proprietary base IPAs. Build your own personal copy following the developer instructions and import via AltStore's My Apps → +. A public AltStore source cannot fetch a private draft release requiring GitHub authentication.
- New releases produce unique News entries with notifications requested. AltStore's own background fetching and notification settings determine delivery. If a new tweak release reuses the same app version and build number, AltStore might not show an Update button; use the News link and install manually if needed. Existing manual installs may not link to the source automatically, especially if their original bundle ID differs.
- The daily GitHub job is separate from the 6 AM LocalDevVPN/AltStore certificate refresh on your phone. App updates are not silently installed. Your current iOS automation remains unchanged.

## Safety and troubleshooting

- `projects.json` is the explicit allowlist. Do not add third-party mirrors just to obtain Facebook IPAs. Public source code and a GitHub release do not prove that a binary is safe or matches source. Review upstream changes and permissions before updating; hashes detect changes, not malicious code.
- The script rejects unexpected bundle IDs and ambiguous IPA variants. If an upstream changes the expected ID or file naming, review that release before editing the config. Do not blindly bypass the checks. AltStore itself also validates permissions. A signature inspection failure can prevent a listing. The included test suite uses synthetic fixtures and does not test real device installation or Apple signing.
- `status.json` tells you whether each project succeeded. If the Actions job is red, read its log and status. An empty Browse list means no IPA passed validation, not that the update alerts are missing (check News).
- If a workflow is disabled after 60 days without repository activity, re-enable it in Actions. The daily status commit is designed to keep the repository active. macOS public runners are subject to GitHub availability and usage policies.
- To stop monitoring a project, remove it from projects.json and run the workflow. Old News entries remain until they age out (last 40 entries).
- Do not upload personal or copyrighted base IPA files, Apple credentials, or authentication tokens to this repository. `.gitignore` excludes common sensitive file types but is not a substitute for checking your commit.

## Upstream projects and documentation

- https://github.com/jaydenjcpy/YouMod/releases
- https://github.com/shajon-dev/Facebook-Plus (personal build instructions; no public IPA)
- https://github.com/dayanch96/YTMusicUltimate (personal build instructions)
- https://github.com/SideloadLabs/EeveeSpotifyReincarnated (personal build instructions)
- https://faq.altstore.io/developers/make-a-source
- https://faq.altstore.io/developers/updating-apps

## Local tests

`python3 -m unittest discover -s tests -v` (Python 3.9+). Actual IPA entitlement inspection needs macOS, so the scheduled runner is macOS. No third-party Python dependencies.

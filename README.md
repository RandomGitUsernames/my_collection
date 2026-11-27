# my_collection — personal AltStore source

Existing repo: https://github.com/RandomGitUsernames/my_collection

## Upgrade once

Unzip the package, open Terminal and run:

```
bash ~/Downloads/my_collection_upgrade/install.sh --include-community
```

This selects five providers. For a stricter mode use `--developer-only` instead (Facebook Plus and YTMusicUltimate will be release alerts only). The full mode opts into two **third-party compiled IPAs, not audited or guaranteed safe**. The installer clones your existing repository, preserves your current source and unrelated files, replaces the updater and pushes a normal commit. It does not force push or ask for Apple ID credentials. You need Git authentication with permission to update workflows; use your normal GitHub login / GitHub CLI if prompted. The script leaves the checkout for recovery. If push is rejected due to a concurrent update, rerun the installer once that update completes.

A push starts the workflow automatically; see https://github.com/RandomGitUsernames/my_collection/actions. `status.json` reports the number of listed and expected apps and errors, if any. The permanent source stays https://raw.githubusercontent.com/RandomGitUsernames/my_collection/main/source.json. Do not remove/re-add it each day. Allow time for GitHub/AltStore caching. The job uses the same 09:23 UTC daily schedule and never installs software on your Mac or phone. To run again manually use Actions → Update AltStore source → Run workflow.

## Providers (not security certifications)

| App | Source of binary | Trust limitation |
|---|---|---|
| YouMod | https://github.com/jaydenjcpy/YouMod/releases | Developer release; modified proprietary app |
| Facebook Plus | https://github.com/927tx/IPA-Vault (exact Facebook Plus listing only) | Opt-in community build, not original developer; version can lag |
| YTMusicUltimate | https://github.com/mrdrvt99/Altstore-Repository (ytmusic.json) | Opt-in community build, contains additional tweaks |
| EeveeSpotify | https://github.com/SideloadLabs/Eevee-Alt-Source (unpatched free-cert entry only) | Developer organization feed, external Catbox host; not audited |
| LiveContainer | https://github.com/LiveContainer/LiveContainer/releases (standalone) | Official project; guest apps share a sandbox, do not use for sensitive accounts |

Facebook Plus and YTMusicUltimate upstream explicitly do not distribute ready-made IPAs. To avoid these community binaries you must build personal IPAs from a legitimately obtained decrypted base, using upstream instructions (https://github.com/shajon-dev/Facebook-Plus and https://github.com/dayanch96/YTMusicUltimate). This upgrade does not build or republish proprietary IPAs and does not promise the community builds contain only the named tweak. It does not bypass AltStore permission checks. Community mode is a deliberate compromise on your original developer-only requirement. No aggregator is added to the phone.

## Checks and limits

The updater checks selected source URLs, exact app names and bundle IDs, expected download hosts/paths, bounded archive size, real IPA metadata and entitlements, and SHA-256 against GitHub asset digest if present. It never launches downloaded apps. It generates exactly one entry per selected bundle ID. If a provider changes naming/host or metadata checks fail, a previously validated entry may be retained and status is marked failed; if there is no previously validated entry it is omitted. A changing URL or same version/build can prevent AltStore from showing an update; review News. External binary links may change content at the same URL; recorded hashes and metadata checks do not prove authenticity, and a cache hit does not rehash bytes. A successful workflow with five listings is not a malware scan or a guarantee of iOS 27 compatibility. No unapproved automatic fallback is used. To disable community builds later edit `settings.json` to false and rerun.

Free AltStore has two extra active app slots. Keep YouMod standalone if you need CarPlay; use LiveContainer only if you accept shared guest data. LiveContainer supports sources (see https://livecontainer.github.io/docs/guides/sources); add the same source there if desired, configure its official JIT-less setup, and import apps as guests. CarPlay, notifications, and guest-app updates are not guaranteed. Your 6 AM shortcut renews signed apps and does not install new versions.

Tests: `python3 -m unittest discover -s tests -v`. These use synthetic fixtures, not live downloads or iPhone testing. GitHub's macOS runner performs real metadata inspection on the next workflow run.

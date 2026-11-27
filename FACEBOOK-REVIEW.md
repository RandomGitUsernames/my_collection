# Facebook Plus review gate

The existing third-party Facebook listing is on hold. The updater keeps the previous listing if present, but it remains unverified and the remote URL may serve changed bytes. Do not treat it as an approved build. Other projects are unchanged.

The separate monitor checks the latest stable upstream release daily and on demand, resolves its tag to a commit, compares against v1.1.1's reference commit (not a security-approved baseline), records keyword flags, and opens one review issue per release commit. It does not run upstream code, approve changes, compile or publish an IPA. It records the main branch tip but does not open issues for unreleased commits.

## Before private builds can be enabled

1. Create a separate private GitHub repository and authorize the GitHub connection.
2. Establish provenance of a lawfully obtained, compatible decrypted base Facebook IPA; verify its expected SHA-256. Do not commit the IPA or credentials to a public repository.
3. Review each exact upstream commit and all dependency changes, including submodules, build actions and package/tool versions. Pin immutable revisions. Keyword checks alone are not an audit.
4. Configure a human approval gate in the private build repository and ensure the build accepts only approved immutable source and base hashes. Build with minimal permissions in isolation; never run unreviewed code with secrets.
5. Inspect built IPA, extension removal, permissions, injected libraries, and hash; test on a device; establish private hosting accessible to AltStore without exposing credentials.
6. Integrate the verified private build feed with AltStore and test updates before lifting the existing hold. Never automatically fall back to a community IPA.

No approval or hosting credentials are stored here.

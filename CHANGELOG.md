# CAIROS Changelog

This file records notable CAIROS changes by release.

## 0.5.0a1

- Added template confidence routing and `cairos plan --debug-route`.
- Reduced aggressive template matching for broad or fuzzy requests.
- Added AI fallback/no-match behavior for uncertain deterministic matches.
- Improved fuzzy directory navigation handling and routed cd guidance through `cairos find-dir`.
- Improved navigation `run` output with matches and copy-paste cd guidance.
- Added safe update/upgrade guidance with config/profile preservation messaging.
- Added config schema versioning, atomic writes, migrations and timestamped backups.
- Added first-class OpenRouter free setup and provider examples.
- Improved OpenAI-compatible and Gemini HTTP/API error handling for 401, 402, 403, 404 and 429.
- Fixed Windows cmd.exe directory guidance so it does not emit Unix `find`.
- Added shell-aware directory navigation guidance and expanded `cairos find-dir`.
- Added AI doctor/examples commands and richer provider setup docs.
- Added Windows, shell navigation, AI troubleshooting and updating docs.
- Bumped release version to 0.5.0a1.

## 0.4.0a1

- GitHub-first installation docs.
- Quicksetup/onboarding improvements.
- Windows/PowerShell setup guidance.
- Shell completion preview.
- Expanded deterministic offline templates.
- System, WSL and Windows helper templates.
- Documentation cleanup.

## 0.3.0

- Package/distribution name is `cairos-shell`; command remains `cairos`.
- Added setup and install diagnostics.
- Added deterministic templates, safety checks, AI configuration, history,
  preview, diff, and documentation improvements.

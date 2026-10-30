# Contributing

Thanks for helping make storage management clearer and safer.

1. Follow README setup on Windows x64; build the frontend before browser tests.
2. Run `python -m unittest discover -s tests -v` and `python tests/e2e.py`.
3. Keep deletion tests restricted to newly created temporary fixtures. Never run cleanup tests against a personal scan.
4. Explain behavior, safety implications and tests in your pull request. Preserve the existing light/dark theme and accessibility semantics.

Do not commit reports, snapshots, private scripts, real-PC screenshots, credentials or generated packages. Use synthetic demo artwork. Do not weaken system/link checks or introduce silent installs. Performance claims require reproducible measurements. Keep `app_info.py` and frontend version metadata aligned.

Bug reports should be sanitized as described in `docs/SUPPORT.md`. Security issues should follow `SECURITY.md` rather than public exploit disclosure. Treat contributors respectfully; maintainers may decline unsafe or out-of-scope changes.

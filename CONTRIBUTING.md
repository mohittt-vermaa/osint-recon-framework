# Contributing to ORF-5

Thanks for considering it. Ground rules, kept short:

1. **One change per PR.** A new platform entry, a bugfix, a docs fix — not all three at once.
2. **Test it.** Run your change on at least one real platform (Linux or Windows). If it touches
   the network engine, make sure `python main.py username octocat` still completes.
3. **New platforms go in `config/platforms.json`**, not in code. Verify the status-code /
   body rules manually (a private/incognito browser window works well) before submitting.
4. **No auth walls, no scraping behind logins.** ORF-5 is public-data only by design;
   PRs that add anything requiring someone else's credentials will be closed.
5. Keep the async model intact — blocking calls (`requests`, `time.sleep`, sync file I/O in
   hot paths) don't belong in the modules.
6. Style: whatever `ruff` accepts with default settings. No reformatting the world.

## Ideas that are always welcome

- Platform schema entries (especially non-US networks)
- Providers for more game titles that expose *public* stats endpoints
- Better error messages — the current ones try hard to say *why*, keep that tone

## Questions / bugs

Open an issue with: OS (including Termux version if relevant), Python version, the exact
command, and the full output. "It doesn't work" is hard to debug.

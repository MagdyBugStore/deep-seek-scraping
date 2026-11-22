# dschat — notes for Claude

Tool to send prompts to DeepSeek chat (many parallel chats, each with a prompt list) so Claude spends fewer tokens. Full usage in `skill/deepseek-chat/SKILL.md`; install it with:

```powershell
Copy-Item -Recurse skill\deepseek-chat $HOME\.claude\skills\
```

- Code: `dschat/scraper.py` (Playwright, async), `dschat/cli.py` (click).
- Never commit `.profile/`, `.chrome-profile/`, `results/` (session cookies / outputs).
- Use `-n 2`; 3 parallel chats failed once (TargetClosedError), cause not found yet.
- Not verified: headless mode with Google login.

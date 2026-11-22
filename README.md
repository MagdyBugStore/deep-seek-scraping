# dschat

CLI: drive many DeepSeek chats in parallel, each chat gets its own list of prompts (sent in order, same conversation).

## Setup

```powershell
pip install -r requirements.txt
playwright install chromium
python -m dschat login        # log in once, session saved in .profile
```

## Use

```powershell
python -m dschat run prompts.example.json -n 3
python -m dschat ask -p "hello" -p "and then?"
```

Config (`chats` array): each chat has `name`, `prompts`, optional `deepthink` / `search` (true/false).

Options: `-n` parallel chats, `--headless`, `--timeout`, `--stable` (seconds text must stay unchanged to count as done), `--channel chrome`.

Output in `results/<timestamp>/`: `results.jsonl` (live, appended per prompt), `<chat>.json`, `<chat>.md`.

## Notes

- Selectors in `dschat/scraper.py` top (`SEL_INPUT`, `SEL_ANSWER`). Fix there if DeepSeek changes DOM.
- Chats share one browser profile = one account. Too many parallel chats may hit rate limits; keep `-n` small.
- Don't run `login` and `run` at the same time (profile locked).

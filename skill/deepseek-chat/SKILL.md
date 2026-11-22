---
name: deepseek-chat
description: Offload prompts to DeepSeek chat via the dschat CLI (parallel chats, each with a prompt list) to save Claude tokens. Use when the user asks to send prompts to DeepSeek, run bulk/parallel prompts, or delegate heavy generation/drafting to DeepSeek.
---

# deepseek-chat

`dschat` CLI drives chat.deepseek.com through the user's logged-in Chrome. Claude only writes the prompts file and reads answers, so DeepSeek does the heavy generation.

Repo: https://github.com/MagdyBugStore/deep-seek-scraping

## 0. Locate / install the tool (once)

Find the repo dir `$DS`: `E:\MYCLIENTS\Magdy\deep-seek-scraping` if it exists, else `$HOME\deep-seek-scraping`. If neither exists:

```powershell
git clone https://github.com/MagdyBugStore/deep-seek-scraping $HOME\deep-seek-scraping
cd $HOME\deep-seek-scraping
pip install -r requirements.txt
```

Real Chrome is used, so no `playwright install` needed in `--real-chrome` mode.

## 1. Chrome with debug port

Check: `curl -s http://localhost:9222/json/version`. If it fails, ask the user to run `python -m dschat chrome` in `$DS`, log in to DeepSeek with Google once, and leave that window open. Never type credentials for them.

## 2. Config

One object per chat. Prompts of one chat go in order, same conversation. `deepthink`/`search` optional.

```json
{"chats":[{"name":"a","prompts":["p1","p2"],"deepthink":false,"search":false}]}
```

## 3. Run (from `$DS`)

Keep `-n 2`: 3 parallel chats failed once with TargetClosedError.

```powershell
python -m dschat run cfg.json -n 2 --real-chrome --out results
python -m dschat ask --real-chrome -p "q1" -p "q2"   # single quick chat
```

Long batches: run in background. Defaults: `--timeout 180` per answer, `--stable 3`, `--retries 1`.

## 4. Read results

`$DS/results/<timestamp>/`: `<chat>.md` (readable), `<chat>.json` (chat,index,prompt,answer,error), `results.jsonl` (all). Check every record's `error` is null; re-run failed prompts only.

## Token saving rules

- Don't paste full answers into the conversation unless asked; summarize or point to the file.
- Read big results with offset/limit or grep.
- Put everything DeepSeek can do (drafts, bulk Q&A) in one config instead of many calls.

## Known limits

- Answers contain UI noise: code blocks carry "Copy"/"Download" text; tables come as tab-separated text.
- One account/browser: heavy parallelism can hit rate limits.
- DOM change on DeepSeek → fix `SEL_INPUT` / `SEL_ANSWER` at top of `dschat/scraper.py`.

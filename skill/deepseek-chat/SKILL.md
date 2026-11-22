---
name: deepseek-chat
description: Offload prompts to DeepSeek chat via the dschat CLI (parallel chats, each with a prompt list) to save Claude tokens. Use when the user asks to send prompts to DeepSeek, run bulk/parallel prompts, or delegate heavy generation to DeepSeek.
---

# deepseek-chat

CLI at the repo root (default local path: `E:\MYCLIENTS\Magdy\deep-seek-scraping`). Drives chat.deepseek.com through the user's logged-in Chrome. Claude only writes the prompts file and reads the answers, so DeepSeek does the heavy generation.

## Run

1. Chrome with debug port must be open (once per boot): `python -m dschat chrome`. User logs in with Google there once and leaves it open. Check: `curl -s http://localhost:9222/json/version`. If down, ask the user to run it; never type credentials.
2. Write a config JSON (one object per chat; prompts of one chat go in order, same conversation):
   `{"chats":[{"name":"a","prompts":["p1","p2"],"deepthink":false,"search":false}]}`
3. Run from the repo dir. Keep `-n` at 2 (3 parallel chats failed once with TargetClosedError):
   `python -m dschat run cfg.json -n 2 --real-chrome --out results`
   Single quick chat: `python -m dschat ask --real-chrome -p "q1" -p "q2"`
4. Read only what is needed from `results/<timestamp>/`: `<chat>.md` (readable), `<chat>.json` (fields chat,index,prompt,answer,error), `results.jsonl` (all). Check `error` is null for each record; failed prompts can be re-run.

## Token saving rules

- Do not paste full answers back into the conversation unless asked; summarize or point to the file.
- Read results with offsets/grep when large.
- Long answers can take minutes; run in background for big batches.

## Known limits

- Answers include UI noise: code blocks carry "Copy"/"Download" text, tables come as tab-separated text.
- One account, one browser: heavy parallelism can hit DeepSeek rate limits.
- If DeepSeek changes its DOM, fix `SEL_INPUT` / `SEL_ANSWER` at the top of `dschat/scraper.py`.

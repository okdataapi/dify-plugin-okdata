# okdata Social Data for Dify

Social media data for Dify workflows and agents. Search TikTok, RedNote (Xiaohongshu), Douyin, WeChat, X and YouTube; read comments, the Douyin and Weibo hot search lists, WeChat article reads and likes, and video transcripts. One [okdata](https://okdata.online/?src=dify-plugin) API key covers 200+ endpoints on 17 platforms, billed per call. Failed calls are free, and you need no platform accounts, cookies or QR logins.

- Source repository: https://github.com/okdataapi/dify-plugin-okdata
- Simplified Chinese README: [readme/README_zh_Hans.md](readme/README_zh_Hans.md)

## Tools

| Tool | What it returns | Per call at release |
|---|---|---|
| TikTok Video Search | Videos by keyword, with plays, likes, comments and shares | $0.002 |
| RedNote (Xiaohongshu) Note Search | Notes by keyword, newest or most popular first | $0.02 |
| RedNote (Xiaohongshu) Note Comments | Comments on a note, with likes and replies | $0.02 |
| Douyin Video Search | Videos by keyword, with likes, comments and shares | $0.02 |
| Douyin Video Comments | Top comments on a video | $0.002 |
| Douyin Hot Search | The current hot search board | $0.002 |
| Weibo Hot Search | The current hot search list | $0.002 |
| WeChat Search: Articles and Channels Videos | Official Account articles and Channels videos by keyword | $0.02 |
| WeChat Official Account Articles | An account's published articles, newest first | $0.02 |
| WeChat Article Reads and Likes | Reads, likes, shares, saves and comments of an article | $0.02 |
| X (Twitter) Post Search | Posts by query, X search operators included | $0.002 |
| YouTube Transcript | A video's transcript with timestamps | $0.004 |
| Find an okdata Endpoint | Any of the 200+ endpoints, found by plain words, with price and parameters | free |
| Call Any okdata Endpoint | Any endpoint by id: Bilibili, Kuaishou, Zhihu, Instagram, Reddit, Telegram, WeChat Channels, Meta and Google ad libraries and more | the endpoint's price |

Live prices and every endpoint's fields: [okdata.online/apis](https://okdata.online/apis/?src=dify-plugin).

## Setup

1. Sign up at [okdata.online](https://okdata.online/signup/?src=dify-plugin) with your email. New accounts get trial credit, and the console makes your first API key (it starts with `okd_`).
2. In Dify, install **okdata Social Data**, open it under **Tools**, choose to authorize it and paste the API key. Dify checks the key with a free call that reads your balance.

Use a key made for this Dify workspace: everyone who can run its apps spends that key's balance. You can give the key daily or monthly spending limits in the okdata console.

## Usage

**In a workflow**, add a tool node such as RedNote (Xiaohongshu) Note Search and map its Keywords input. Each tool outputs `text` (a readable summary), `json` (the full okdata response) and variables you can reference directly: `items`, `next_cursor`, `has_more`, `cost`, `balance_after`, `request_id` and `result_status` (tools that return one object output `item` instead of `items`). Loop over `items` with an Iteration node. For the next page, pass `next_cursor` into the Cursor input; each page is a separate call.

**In an agent**, add the tools you need. Find an okdata Endpoint plus Call Any okdata Endpoint give the agent the whole catalog. A first prompt to try:

```text
What is trending on Weibo and Douyin right now? Pick three topics a coffee brand
could post about, and find two recent RedNote notes for each. Say what the calls cost.
```

**Cost control.** Every paid tool has a **Max price per call** setting, a little above the endpoint's current price (Call Any okdata Endpoint: $0.10). okdata refuses any call that could cost more, before it runs, and bills nothing for it. It is a setting, not an agent input, so an agent cannot raise its own cap. Failed calls and timeouts cost nothing.

## Connection requirements

The plugin connects only to `https://api.okdata.online` over HTTPS. A self-hosted Dify needs outbound access to that host. Each request times out after 60 seconds and is retried at most once, with the same idempotency key, so a retry is never billed twice.

## Errors

A failed call raises an error with the okdata code and what to do, for example `unauthorized` (the key is wrong or revoked), `insufficient_balance` (top up in the console), `max_price_exceeded` (raise Max price per call) or `rate_limited` (wait and retry). Every code: [okdata.online/docs/errors](https://okdata.online/docs/errors/?src=dify-plugin).

## Privacy

The plugin sends your API key and the tool inputs to `api.okdata.online` and nothing else; it stores nothing itself. Details in [PRIVACY.md](PRIVACY.md).

## Support

Email hello@okdata.online or open an issue at https://github.com/okdataapi/dify-plugin-okdata/issues. Other ways to use okdata in Dify (the remote MCP server, an OpenAPI tool): [okdata.online/integrations/dify](https://okdata.online/integrations/dify/?src=dify-plugin).

MIT licensed.

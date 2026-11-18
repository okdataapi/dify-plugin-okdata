# TikTok, YouTube, Instagram, X & Reddit Data for Dify (okdata)

Public data from TikTok, YouTube, Instagram, X (Twitter), Reddit and Amazon for Dify workflows and agents, plus RedNote (Xiaohongshu), Douyin, WeChat, Bilibili and Weibo. Search videos, posts and products; read comments, reviews, profiles, transcripts and trending topics. One [okdata](https://okdata.online/?src=dify-plugin) API key covers 230+ endpoints on 23 platforms. You need no platform accounts, cookies or QR logins.

Pay per call, no subscription. Every endpoint has its own price, and new accounts get trial credit.

- Source repository: https://github.com/okdataapi/dify-plugin-okdata
- Simplified Chinese README: [readme/README_zh_Hans.md](readme/README_zh_Hans.md)

## What you can build

**Weekly product feedback digest from Reddit and YouTube.** Reddit Post Search with your product name and Posted within = week, then an Iteration node that runs Reddit Post Comments on each post. In parallel, YouTube Video Search (Newest) and YouTube Video Comments on the top results. An LLM node sorts what people said into praise, complaints and feature requests, with links to the threads. Run it every Monday.

**Complaint themes from Amazon reviews.** Amazon Product Search for your category in the store you sell in, then Amazon Product Reviews for your product and the top competitors (pass each result's `id`, its ASIN). An LLM node keeps the reviews of 3 stars or less and groups them into themes such as "leaks after a month" or "hard to clean", with a count and a quote for each.

**RedNote (Xiaohongshu) brand mentions, daily.** RedNote Note Search for your brand name, Newest first, then RedNote Note Comments on the notes with the most likes. An LLM node writes a short daily report in Chinese: what people praise, what they complain about, and which notes to answer first.

## Tools

| Tool | What it returns | Per call |
|---|---|---|
| TikTok Video Search | Videos by keyword, with plays, likes, comments and shares | $0.002 |
| TikTok Video Comments | Comments on a video, with likes and replies | $0.002 |
| YouTube Video Search | Videos by keyword, with views, length and channel | $0.004 |
| YouTube Video Comments | Comments on a video, top or newest first | $0.002 |
| YouTube Transcript | A video's transcript with timestamps | $0.004 |
| Instagram Profile | An account's bio, followers, following, post count and links | $0.004 |
| Instagram Account Posts | An account's posts or reels, newest first | $0.004 |
| Instagram Post Comments | Comments on a post or reel | $0.004 |
| X (Twitter) Post Search | Posts by query, X search operators included | $0.002 |
| X (Twitter) Trending Topics | What is trending, worldwide or in one country | $0.009 |
| Reddit Post Search | Posts across Reddit by keyword, optionally from the last day, week, month or year | $0.004 |
| Reddit Post Comments | Comments on a post with the first levels of replies | $0.002 |
| Amazon Product Search | Products by keyword in 22 country stores, with price, stars and units bought last month | $0.006 |
| Amazon Product Reviews | The reviews shown on a product page, up to 10 | $0.006 |
| RedNote (Xiaohongshu) Note Search | Notes by keyword, newest or most popular first | $0.02 |
| RedNote (Xiaohongshu) Note Comments | Comments on a note, with likes and replies | $0.02 |
| Douyin Video Search | Videos by keyword, with likes, comments and shares | $0.02 |
| Douyin Video Comments | Top comments on a video | $0.002 |
| Douyin Hot Search | The current hot search board | $0.002 |
| WeChat Search: Articles and Channels Videos | Official Account articles and Channels videos by keyword | $0.02 |
| WeChat Official Account Articles | An account's published articles, newest first | $0.02 |
| WeChat Article Reads and Likes | Reads, likes, shares, saves and comments of an article | $0.02 |
| Weibo Hot Search | The current hot search list | $0.002 |
| Find an okdata Endpoint | Any of the 230+ endpoints, found by plain words, with price and parameters | free |
| Call Any okdata Endpoint | Any endpoint by id: Telegram, AliExpress, Meta Ad Library, Google Ads Transparency, Bilibili, Kuaishou, Zhihu, WeChat Channels, Taobao, 1688, Xianyu and more | the endpoint's price |

Prices are per call at release; each page of results is a separate call. Live prices and every endpoint's fields: [okdata.online/apis](https://okdata.online/apis/?src=dify-plugin).

## Setup

1. Sign up at [okdata.online](https://okdata.online/signup/?src=dify-plugin) with your email. New accounts get trial credit, and the console makes your first API key (it starts with `okd_`).
2. In Dify, install the plugin from the Marketplace, open it under **Tools**, choose to authorize it and paste the API key. Dify checks the key by reading your balance.
3. Add a tool to a workflow or an agent and run it.

Use a key made for this Dify workspace: everyone who can run its apps spends that key's balance. You can give the key daily or monthly spending limits in the okdata console.

## Using the tools

**In a workflow**, add a tool node such as Reddit Post Search and map its inputs. Each tool outputs `text` (a readable summary), `json` (the full okdata response) and variables you can reference directly: `items`, `next_cursor`, `has_more`, `cost`, `balance_after`, `request_id` and `result_status` (tools that return one object, such as Instagram Profile, output `item` instead of `items`). Loop over `items` with an Iteration node. For the next page, pass `next_cursor` into the Cursor input; each page is a separate call.

Inputs that take an ID also accept the full page link: `tiktok.com/@user/video/...`, `youtube.com` or `youtu.be`, `instagram.com/p/...` or `/reel/...`, any Reddit post link (share links too) and Amazon `/dp/` links.

**In an agent**, add the tools you need. Find an okdata Endpoint plus Call Any okdata Endpoint give the agent the whole catalog. A first prompt to try:

```text
Find this month's most discussed Reddit posts about standing desks, read their
comments, and list the three complaints that come up most. Say what the calls cost.
```

**Price cap.** Every paid tool has a **Max price per call** setting, a little above the endpoint's current price (Call Any okdata Endpoint: $0.10). okdata refuses any call that could cost more than that, before it runs. It is a setting, not an agent input, so an agent cannot raise its own cap.

## Connection requirements

The plugin connects only to `https://api.okdata.online` over HTTPS. A self-hosted Dify needs outbound access to that host. Each request times out after 60 seconds. A request that cannot connect is tried once more, and so is a call okdata says can be retried after a short wait.

## Errors

A failed call raises an error with the okdata code and what to do, for example `unauthorized` (the key is wrong or revoked), `insufficient_balance` (top up in the console), `max_price_exceeded` (raise Max price per call) or `rate_limited` (wait and retry). Every code: [okdata.online/docs/errors](https://okdata.online/docs/errors/?src=dify-plugin).

## Privacy

The plugin sends your API key and the tool inputs to `api.okdata.online` and nothing else, and it stores nothing itself. What comes back is public data on the platforms. Details in [PRIVACY.md](PRIVACY.md).

## Support

Email hello@okdata.online or open an issue at https://github.com/okdataapi/dify-plugin-okdata/issues. Other ways to use okdata in Dify (the remote MCP server, an OpenAPI tool): [okdata.online/integrations/dify](https://okdata.online/integrations/dify/?src=dify-plugin).

MIT licensed.

# Privacy Policy: okdata Social Data plugin for Dify

Last updated: 2026-11-13

This plugin connects Dify to the okdata API (`https://api.okdata.online`), a pay-per-call service that returns public social media data. This page says what the plugin sends, where, and what is kept.

## What the plugin collects and stores

The plugin itself collects and stores nothing. It keeps no logs, files or databases of its own and writes nothing to Dify's plugin storage. Your okdata API key is stored by Dify as an encrypted tool credential, like any other plugin credential; the plugin reads it only to sign requests. The only thing held in memory is a copy of okdata's public endpoint catalog (no personal data), kept for ten minutes.

## What the plugin sends, and to whom

Every request goes to one host, `api.okdata.online`, over HTTPS. A request carries:

- your okdata API key, in the `Authorization` header (not sent for the free catalog lookup);
- the inputs of the tool you ran: keywords, IDs, links (such as a WeChat article link), a page cursor, the endpoint id and parameters of Call Any okdata Endpoint;
- your price cap (`X-Max-Price`), a random idempotency key, the label `X-Source: dify` and a `User-Agent` naming this plugin and its version.

The plugin sends no conversation history, no Dify user or workspace identifiers, no uploaded files and nothing else from your Dify workspace. Tool inputs can contain personal data if you type it in (for example a person's username); only send what the task needs.

## What okdata keeps

okdata is the third party that receives these requests. According to the [okdata privacy policy](https://okdata.online/privacy/?src=dify-plugin):

- each call is recorded (time, key, endpoint, parameters, result status, cost, request ID) for your call log and billing, and these records are deleted after 30 days;
- a call's result is kept for 24 hours so that a retried request returns the same answer instead of being billed again;
- API keys are stored only as hashes;
- the parameters of a call are used only to answer it, never together with your key, email address or identity;
- okdata does not sell personal information or share it for advertising.

Your okdata account (email address, balance, keys) is governed by that policy, not by this plugin.

## Data returned to you

okdata returns content that people published on public platforms: posts, comments, public profiles, view and like counts. It can include their names, usernames and words. Use it lawfully and in line with okdata's [acceptable use policy](https://okdata.online/acceptable-use/?src=dify-plugin), and keep only what you need in your Dify apps and logs.

## Contact

Questions or deletion requests: hello@okdata.online. Source code: https://github.com/okdataapi/dify-plugin-okdata

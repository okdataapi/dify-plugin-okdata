# okdata 社媒数据（Dify 插件）

给 Dify 工作流和智能体用的社媒数据：搜抖音视频、小红书笔记、公众号文章和视频号，拉抖音和小红书评论，看抖音热搜和微博热搜，查公众号文章的阅读数和点赞数，也能搜 TikTok、X、YouTube 并拿视频字幕。一个 [okdata](https://okdata.online/zh/?src=dify-plugin) Key 调用 17 个平台的 200 多个接口，按次计费，调用失败不扣钱，不需要平台账号、Cookie，也不用扫码。

- 源码：https://github.com/okdataapi/dify-plugin-okdata
- English README: [README.md](../README.md)

## 工具

| 工具 | 返回什么 | 发布时单价 |
|---|---|---|
| 抖音视频搜索 | 按关键词搜视频，带点赞、评论、转发 | $0.02 / 次 |
| 抖音视频评论 | 视频的一级评论，按最热排序 | $0.002 / 次 |
| 抖音热搜榜 | 当前热搜榜，带排名和热度 | $0.002 / 次 |
| 小红书笔记搜索 | 按关键词搜笔记，可按最新或最热 | $0.02 / 次 |
| 小红书笔记评论 | 笔记下的评论，带点赞和回复数 | $0.02 / 次 |
| 微信搜一搜：公众号文章和视频号 | 按关键词搜公众号文章和视频号视频 | $0.02 / 次 |
| 公众号历史文章 | 公众号已发布的文章，从新到旧 | $0.02 / 次 |
| 公众号文章阅读数和点赞数 | 按链接取阅读、点赞、在看、分享、收藏、评论数 | $0.02 / 次 |
| 微博热搜 | 当前微博热搜榜 | $0.002 / 次 |
| TikTok 视频搜索 | 按关键词搜全球 TikTok 视频 | $0.002 / 次 |
| X（推特）帖子搜索 | 支持 X 搜索语法 | $0.002 / 次 |
| YouTube 视频字幕 | 带时间戳的字幕 | $0.004 / 次 |
| 查找 okdata 接口（免费） | 用中文或英文描述需求，在 200 多个接口里找，带价格和参数 | 免费 |
| 调用任意 okdata 接口 | 按 ID 调用任意接口：B站、快手、知乎、视频号、Instagram、Reddit、Telegram、Meta 和 Google 广告库等 | 按该接口价格 |

实时价格和每个接口的字段：[okdata.online/zh/apis](https://okdata.online/zh/apis/?src=dify-plugin)。

## 配置

1. 在 [okdata.online](https://okdata.online/zh/signup/?src=dify-plugin) 用邮箱注册，新账号有试用额度，控制台会自动生成第一个 API Key（以 `okd_` 开头）。支付宝、微信、银行卡都能充值。
2. 在 Dify 里安装 **okdata 社媒数据**，在 **工具** 里打开它，选择授权并粘贴 API Key。Dify 会用一次免费调用（读余额）检查这个 Key。

建议为这个 Dify 工作空间单独建一个 Key：能运行其中应用的人都会用这个 Key 的余额。在 okdata 控制台可以给 Key 设每日或每月消费上限。

## 使用

**工作流里**：加一个工具节点，比如“小红书笔记搜索”，把关键词接进去。每个工具输出 `text`（可读摘要）、`json`（okdata 的完整返回）和可以直接引用的变量：`items`、`next_cursor`、`has_more`、`cost`、`balance_after`、`request_id`、`result_status`（返回单个对象的工具输出 `item`）。用迭代节点遍历 `items`。要下一页时，把 `next_cursor` 填进“翻页 cursor”；每一页都是一次单独计费的调用。

**智能体里**：加上需要的工具。“查找 okdata 接口”加“调用任意 okdata 接口”两个工具，就能让智能体用到全部接口。可以先试这句：

```text
现在微博热搜和抖音热搜上有什么？挑三个适合咖啡品牌蹭的话题，每个话题再找两篇最近的小红书笔记，最后告诉我这些调用花了多少钱。
```

**控制花费**：每个付费工具都有“单次调用最高价格”设置，默认略高于接口当前价格（“调用任意 okdata 接口”默认 $0.10）。可能超过这个价格的调用会在执行前被拒绝，不扣钱。这是工具设置而不是智能体能填的参数，智能体没法自己调高。失败和超时的调用都不扣钱。

## 网络要求

插件只连接 `https://api.okdata.online`（HTTPS）。自部署的 Dify 需要能访问这个域名。每次请求 60 秒超时，最多重试一次，并且用同一个幂等键，重试不会重复扣费。

## 出错时

调用失败会报出 okdata 的错误码和处理办法，比如 `unauthorized`（Key 不对或已撤销）、`insufficient_balance`（到控制台充值）、`max_price_exceeded`（调高单次最高价格）、`rate_limited`（稍等再试）。全部错误码：[okdata.online/zh/docs/errors](https://okdata.online/zh/docs/errors/?src=dify-plugin)。

## 隐私

插件只把你的 API Key 和工具输入发给 `api.okdata.online`，自己不存任何东西。详见 [PRIVACY.md](../PRIVACY.md)。

## 支持

邮件 hello@okdata.online，或在 https://github.com/okdataapi/dify-plugin-okdata/issues 提 issue。在 Dify 里用 okdata 的其他方式（远程 MCP 服务、OpenAPI 工具）：[okdata.online/zh/integrations/dify](https://okdata.online/zh/integrations/dify/?src=dify-plugin)。

MIT 许可。

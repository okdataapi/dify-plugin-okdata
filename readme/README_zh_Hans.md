# 小红书 抖音 公众号 TikTok 数据（okdata，Dify 插件）

给 Dify 工作流和智能体用的平台公开数据。搜小红书笔记、抖音视频和公众号文章，拉评论，看抖音热搜和微博热搜，查公众号文章的阅读数和点赞数。TikTok、YouTube、Instagram、X、Reddit 和亚马逊也有专门的工具：搜视频和帖子、拉评论、看账号、取字幕、看趋势，搜商品和看买家评论。

一个 [okdata](https://okdata.online/zh/?src=dify-plugin) Key 能调 23 个平台的 230 多个接口，不需要平台账号、Cookie，也不用扫码。按次付费，不用订阅，每个接口单独定价，新账号有试用额度。

- 源码：https://github.com/okdataapi/dify-plugin-okdata
- English README: [README.md](../README.md)

## 在工作流里能做什么

**小红书品牌口碑日报。** 用“小红书笔记搜索”搜品牌名，按最新排，再对点赞最多的几篇笔记跑“小红书笔记评论”。最后接一个 LLM 节点，写一份当天的口碑日报：大家夸什么、吐槽什么、哪几篇笔记该先去回复。每天跑一次。

**Reddit 和 YouTube 的产品反馈周报。** “Reddit 帖子搜索”搜产品名，发布时间选一周内，用迭代节点对每个帖子跑“Reddit 帖子评论”。另一路用“YouTube 视频搜索”按最新排，再拉前几个视频的评论。LLM 节点把这些反馈分成好评、抱怨和功能需求，附上原帖链接。每周一跑。

**从亚马逊评论里找差评主题。** 在你卖货的站点用“亚马逊商品搜索”搜品类，把自家商品和头部竞品的 `id`（就是 ASIN）传给“亚马逊商品评论”。LLM 节点只留 3 星及以下的评论，归成几类问题，比如“用一个月就漏水”“不好清洗”，每类给出条数和一句原话。

## 工具

| 工具 | 返回什么 | 单价 |
|---|---|---|
| 小红书笔记搜索 | 按关键词搜笔记，可按最新或最热 | $0.02 / 次 |
| 小红书笔记评论 | 笔记下的评论，带点赞和回复数 | $0.02 / 次 |
| 抖音视频搜索 | 按关键词搜视频，带点赞、评论、转发 | $0.02 / 次 |
| 抖音视频评论 | 视频的一级评论，按最热排序 | $0.002 / 次 |
| 抖音热搜榜 | 当前热搜榜，带排名和热度 | $0.002 / 次 |
| 微信搜一搜：公众号文章和视频号 | 按关键词搜公众号文章和视频号视频 | $0.02 / 次 |
| 公众号历史文章 | 公众号已发布的文章，从新到旧 | $0.02 / 次 |
| 公众号文章阅读数和点赞数 | 按链接取阅读、点赞、在看、分享、收藏、评论数 | $0.02 / 次 |
| 微博热搜 | 当前微博热搜榜 | $0.002 / 次 |
| TikTok 视频搜索 | 按关键词搜全球 TikTok 视频 | $0.002 / 次 |
| TikTok 视频评论 | 视频下的评论，带点赞和回复数 | $0.002 / 次 |
| YouTube 视频搜索 | 按关键词搜视频，带播放量、时长和频道 | $0.004 / 次 |
| YouTube 视频评论 | 视频下的评论，按热门或最新 | $0.002 / 次 |
| YouTube 视频字幕 | 带时间戳的字幕 | $0.004 / 次 |
| Instagram 账号信息 | 简介、粉丝数、关注数、帖子数和主页链接 | $0.004 / 次 |
| Instagram 账号帖子 | 账号的帖子或 Reels，从新到旧 | $0.004 / 次 |
| Instagram 帖子评论 | 帖子或 Reel 下的评论 | $0.004 / 次 |
| X（推特）帖子搜索 | 支持 X 搜索语法 | $0.002 / 次 |
| X（推特）趋势 | 全球或某个国家正在热的话题 | $0.009 / 次 |
| Reddit 帖子搜索 | 全站按关键词搜帖子，可限定一天、一周、一个月或一年内 | $0.004 / 次 |
| Reddit 帖子评论 | 帖子下的评论，连同前几层回复 | $0.002 / 次 |
| 亚马逊商品搜索 | 22 个国家站点按关键词搜商品，带价格、星级和上月购买量 | $0.006 / 次 |
| 亚马逊商品评论 | 商品页上展示的评论，最多 10 条 | $0.006 / 次 |
| 查找 okdata 接口（免费） | 用中文或英文描述需求，在 230 多个接口里找，带价格和参数 | 免费 |
| 调用任意 okdata 接口 | 按 ID 调用任意接口：B站、快手、知乎、视频号、淘宝、1688、闲鱼、速卖通、Telegram、Meta 和 Google 广告库等 | 按该接口价格 |

单价是发布时的价格，翻一页就是一次调用。实时价格和每个接口的字段：[okdata.online/zh/apis](https://okdata.online/zh/apis/?src=dify-plugin)。

## 配置

1. 在 [okdata.online](https://okdata.online/zh/signup/?src=dify-plugin) 用邮箱注册。新账号有试用额度，控制台会自动生成第一个 API Key（以 `okd_` 开头）。支付宝、微信、银行卡都能充值。
2. 在 Dify 插件市场安装本插件，在 **工具** 里打开它，选择授权并粘贴 API Key。Dify 会读一次余额来检查这个 Key。
3. 把工具加进工作流或智能体，运行。

建议给这个 Dify 工作空间单独建一个 Key，因为能运行其中应用的人都会用这个 Key 的余额。在 okdata 控制台可以给 Key 设每日或每月消费上限。

## 使用

**工作流里**：加一个工具节点，比如“小红书笔记搜索”，把关键词接进去。每个工具输出 `text`（可读摘要）、`json`（okdata 的完整返回）和可以直接引用的变量：`items`、`next_cursor`、`has_more`、`cost`、`balance_after`、`request_id`、`result_status`。返回单个对象的工具（比如“Instagram 账号信息”）输出 `item`。用迭代节点遍历 `items`。要下一页时，把 `next_cursor` 填进“翻页 cursor”，每一页都是一次单独的调用。

要填 ID 的地方也可以直接贴网页链接：`douyin.com/video/...`、`xiaohongshu.com/explore/...`、`tiktok.com/@用户名/video/...`、`youtube.com` 或 `youtu.be`、`instagram.com/p/...` 或 `/reel/...`、Reddit 帖子链接（分享链接也行），以及亚马逊的 `/dp/` 商品链接。

**智能体里**：加上需要的工具。“查找 okdata 接口”加“调用任意 okdata 接口”两个工具，就能让智能体用到全部接口。可以先试这句：

```text
现在微博热搜和抖音热搜上有什么？挑三个适合咖啡品牌蹭的话题，每个话题再找两篇最近的小红书笔记，最后告诉我这些调用花了多少钱。
```

**单次最高价格**：每个付费工具都有“单次调用最高价格”设置，默认略高于接口当前价格（“调用任意 okdata 接口”默认 $0.10）。可能超过这个价格的调用会在执行前被拒绝。这是工具设置，不是智能体能填的参数，智能体没法自己调高。

## 网络要求

插件只连接 `https://api.okdata.online`（HTTPS）。自部署的 Dify 需要能访问这个域名。每次请求 60 秒超时。连不上时会再试一次；okdata 回复可以稍后重试的调用，也会再试一次。

## 出错时

调用失败会报出 okdata 的错误码和处理办法，比如 `unauthorized`（Key 不对或已撤销）、`insufficient_balance`（到控制台充值）、`max_price_exceeded`（调高单次最高价格）、`rate_limited`（稍等再试）。全部错误码：[okdata.online/zh/docs/errors](https://okdata.online/zh/docs/errors/?src=dify-plugin)。

## 隐私

插件只把你的 API Key 和工具输入发给 `api.okdata.online`，自己不存任何东西。返回的是各平台上的公开数据。详见 [PRIVACY.md](../PRIVACY.md)。

## 支持

邮件 hello@okdata.online，或在 https://github.com/okdataapi/dify-plugin-okdata/issues 提 issue。在 Dify 里用 okdata 的其他方式（远程 MCP 服务、OpenAPI 工具）：[okdata.online/zh/integrations/dify](https://okdata.online/zh/integrations/dify/?src=dify-plugin)。

MIT 许可。

# dòu (豆)

**open access to douyin for the rest of the world. no vpn. no censorship. no phone number.**

<br>

## what is dòu

douyin is the original tiktok — the chinese version that the rest of the world never gets to see. the content is different. the trends start there weeks before they hit western tiktok. the creators are different. the algorithms are different.

but if you're not in china, you can't use it. geo-blocked. requires a chinese phone number. half the content is filtered for foreign IPs.

dòu removes all of that.

it's an open-source gateway that gives you full, unfiltered access to douyin's content — from anywhere. no vpn. no chinese sim card. no account. just open it and scroll.

every caption, every comment, every hashtag — auto-translated to english in real time using deepseek (not google translate — actual chinese AI that understands slang, internet culture, and context).

---

## why this exists

the internet was supposed to be borderless. it's not. the great firewall keeps chinese content in, and western platforms keep copying it without credit.

dòu is the window. see what china is actually watching, not what gets reposted three weeks later on instagram reels.

- **trend scouts** — see what's going viral in china before it crosses over
- **creators** — find inspiration from the largest short-video ecosystem on earth
- **researchers** — access unfiltered chinese social media data for analysis
- **the curious** — just browse. it's genuinely fascinating content that most of the world has zero access to

---

## features

- **no geo-block** — reverse-engineered douyin API, works from any country
- **no account needed** — browse anonymously, no login wall, no phone verification
- **real-time translation** — deepseek-powered translation that actually understands chinese internet slang (not literal garbage translations)
- **clean infinite scroll** — no bloatware, no tracking, no telemetry. just content
- **trending discovery** — surfaces what's actually trending in china right now, unfiltered
- **search in english** — type in english, dòu translates your query to chinese and searches douyin natively
- **video download** — save any video, no watermark
- **developer API** — JSON endpoints for videos, users, hashtags, trending feeds, comments
- **self-hostable** — run your own instance, zero dependencies on our servers

---

## how it works

```
you open dòu
    ↓
pick a feed (trending, search, creator, hashtag)
    ↓
dòu hits douyin's API through the gateway (bypasses geo-block)
    ↓
content comes back raw + unfiltered
    ↓
deepseek translates everything to english in real time
    ↓
you scroll. that's it.
```

---

## architecture

```
dòu/
├── gateway/        # douyin API reverse-engineering + proxy
│   ├── client.py   # async http client with failover
│   ├── auth.py     # device registration + request signing (X-Bogus, a-bogus)
│   ├── feeds.py    # trending, search, hashtag, user feeds
│   ├── video.py    # video metadata + no-watermark stream extraction
│   └── proto/      # protobuf definitions from douyin APK
├── translate/      # deepseek translation pipeline
│   ├── engine.py   # async translation with redis cache
│   ├── slang.py    # 80+ douyin-specific slang mappings
│   └── batch.py    # bulk translation for feeds and comments
├── api/            # REST + websocket server (fastapi)
│   ├── app.py      # main server with lifespan management
│   ├── routes/     # feed, video, user, translate endpoints
│   ├── ws.py       # websocket live feed streaming
│   └── middleware.py # rate limiting, CORS, error handling
├── web/            # browser UI (vanilla html/css/js)
│   ├── index.html  # main feed with infinite scroll
│   ├── style.css   # dark theme, mobile-first
│   └── app.js      # feed logic, video modal, search
└── scripts/        # deployment & utilities
    ├── healthcheck.py
    └── benchmark.py
```

---

## quick start

```bash
# clone
git clone https://github.com/getdou/dou.git
cd dou

# install
pip install -r requirements.txt

# configure
cp .env.example .env
# fill in DEEPSEEK_API_KEY (get one at platform.deepseek.com)

# run
python -m api.app

# open http://localhost:8000
```

self-host it, share it, fork it. the internet should be open.

---

## API

all endpoints return JSON. no auth required for public feeds.

| method | endpoint | description |
|--------|----------|-------------|
| `GET` | `/api/feed/trending` | trending videos (translated) |
| `GET` | `/api/feed/search?q=cooking` | search (english or chinese) |
| `GET` | `/api/feed/hashtag/美食` | hashtag feed |
| `GET` | `/api/feed/hot` | hot search keywords |
| `GET` | `/api/video/{id}` | single video + metadata |
| `GET` | `/api/video/{id}/comments` | comment thread (translated) |
| `GET` | `/api/video/{id}/download` | no-watermark video redirect |
| `GET` | `/api/user/{id}` | creator profile |
| `GET` | `/api/user/{id}/videos` | creator's video list |
| `GET` | `/api/translate?text=你好` | standalone translation |
| `WS` | `/ws/feed` | live feed stream |

all feed endpoints accept `?translate=false` to skip translation and get raw chinese.

---

## env

```
DEEPSEEK_API_KEY=           # required for translation
DEEPSEEK_MODEL=deepseek-chat # model to use
DOUYIN_DEVICE_ID=           # auto-generated if empty
REDIS_URL=redis://localhost:6379
API_HOST=0.0.0.0
API_PORT=8000
TRANSLATION_CACHE_TTL=3600  # seconds
RATE_LIMIT_RPM=120          # requests per minute per IP
LOG_LEVEL=info
PROXY_URL=                  # optional SOCKS5/HTTP proxy for douyin API
```

---

## translation quality

dòu uses deepseek for translation because it's trained on massive chinese internet corpora. it understands:

- **douyin slang** — 绝绝子, 破防了, yyds, 摆烂, 内卷 → all translated to natural english equivalents
- **meme context** — doesn't just translate words, understands the joke
- **food vocabulary** — chinese food content is huge on douyin, translations are accurate not generic
- **regional dialects** — handles 东北话, 四川话 references in comments

plus a custom slang dictionary (80+ entries) for terms that even deepseek occasionally misses.

---

## status

**alpha — still experimenting.** this project is under active development and is not fully finished yet. core gateway and translation are working, web UI is functional, API is stable. we're actively improving signature generation, adding more feed types, and squashing edge cases.

**coming soon: wechat integration.** same concept — unrestricted access to wechat moments, channels, and articles from anywhere in the world. no chinese phone number required. no restrictions. currently in early development.

---

## disclaimer

this project is an independent research tool for cross-cultural content access. it is not affiliated with, endorsed by, or associated with ByteDance, Douyin, TikTok, or any related entity.

dòu does not host, store, or redistribute any content. it acts as a translation and access layer only. all content remains the property of its original creators.

use responsibly and in accordance with applicable laws in your jurisdiction.

---

## support the project

dòu is free and open source. if you find it useful, consider supporting development:

| currency | address |
|----------|---------|
| **SOL** | `getdou.sol` |
| **ETH** | `0x21e14dad93B42FEA00E9d5108C743f4885902B14` |
| **BTC** | `bc1q4nmu5h7ghy8ap5nlu0zv70xv887yefay3lf77l` |

or just star the repo. that helps too.

---

[getdou.xyz](https://getdou.xyz) · [@getdou](https://twitter.com/getdou)

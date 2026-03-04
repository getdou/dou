"""Douyin-specific slang dictionary.

These terms get pre-processed before sending to DeepSeek to improve
translation accuracy. Even though DeepSeek handles most Chinese well,
some ultra-recent slang and Douyin-specific terms benefit from explicit
mappings.

Updated regularly as new slang emerges on the platform.
"""

DOUYIN_SLANG: dict[str, str] = {
    # === viral catchphrases ===
    "yyds": "GOAT",
    "YYDS": "GOAT",
    "绝绝子": "absolutely insane",
    "破防了": "I'm shook / can't handle this",
    "笑死": "I'm dead",
    "离谱": "that's wild",
    "无语": "I can't even",
    "社死": "died of embarrassment",
    "摆烂": "quiet quitting / giving up",
    "内卷": "rat race / toxic grind culture",
    "躺平": "lying flat / opting out of the rat race",
    "凡尔赛": "humble bragging",
    "炸裂": "mind-blowing",
    "上头": "obsessed / addicted",
    "下头": "instant turnoff",
    "拿捏": "nailed it / served",
    "太绝了": "too good",
    "封神": "legendary / goated",
    "DNA动了": "nostalgia activated / this hit different",
    "遥遥领先": "miles ahead of everyone",
    "泰裤辣": "too cool",
    "脆皮大学生": "fragile college students",
    "i人": "introvert",
    "e人": "extrovert",
    "搭子": "activity buddy / doing X together",
    "特种兵旅游": "speed-run tourism",
    "显眼包": "attention-seeker (endearing)",
    "电子榨菜": "content you watch while eating",
    "多巴胺穿搭": "dopamine dressing / bright colorful outfits",
    "美拉德穿搭": "Maillard-reaction-inspired earth tone outfits",
    "命运的齿轮开始转动": "the wheels of fate started turning",
    "公主请上车": "princess please get in the car",

    # === people / address ===
    "集美": "bestie / girls",
    "姐妹": "sis",
    "家人们": "fam / everyone",
    "老铁": "bro / homie",
    "宝子": "babe / hun",
    "兄弟们": "bros",
    "各位观众": "ladies and gentlemen",

    # === reactions ===
    "绝了": "fire / incredible",
    "牛": "amazing / badass",
    "6": "slick / pro move",
    "666": "impressive / pro",
    "好家伙": "damn / well well well",
    "真的假的": "no way / for real?",
    "蚌埠住了": "can't hold it together / losing it",
    "整个人都不好了": "I'm not okay after seeing this",
    "CPU了": "completely confused / brain crashed",
    "刀了": "emotionally destroyed",
    "我不理解": "I don't understand why",

    # === food content (huge on douyin) ===
    "好吃到哭": "so good I could cry",
    "米其林嘴替": "my taste buds' spokesperson",
    "干饭人": "someone who lives to eat",
    "减肥的忽略": "dieters scroll past this",
    "馋哭了": "drooling so hard I'm crying",
    "神仙吃法": "god-tier way of eating this",
    "小时候的味道": "tastes like childhood",

    # === douyin-specific terms ===
    "抖音": "Douyin",
    "直播": "livestream",
    "带货": "selling products on stream",
    "种草": "got me wanting to buy this",
    "拔草": "finally bought it / tried it",
    "安利": "recommendation / you NEED to try this",
    "好物": "good finds / must-haves",
    "同款": "same one / link please",
    "滤镜": "filter",
    "卡点": "beat sync / matching cuts to beat",
    "变装": "outfit transformation / transition",
    "手势舞": "hand dance / finger choreo",
    "合拍": "duet",
    "原声": "original sound",

    # === positive vibes ===
    "正能量": "positive vibes",
    "治愈": "healing / wholesome",
    "暖心": "heartwarming",
    "高级感": "looks expensive / luxurious aesthetic",
    "氛围感": "the vibes / aesthetic",
    "松弛感": "effortlessly chill",

    # === recent 2025-2026 slang ===
    "city不city": "is it city enough / is this giving city vibes",
    "班味": "that corporate worker smell / aura",
    "发疯文学": "unhinged writing / going feral",
    "你个老六": "you sneaky player / rat",
    "一整个住了": "completely obsessed",
}

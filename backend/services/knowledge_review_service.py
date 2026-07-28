"""知识点复习卡：概念、易错点、例题、自测及关联错题。"""

import asyncio
import json
import logging
import re
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import BusinessError
from backend.model.mastery import (
    KnowledgeMastery,
    KnowledgeReviewRecord,
    Mistake,
)

logger = logging.getLogger(__name__)

CARDS = {
    "一元一次方程": {
        "summary": "只含一个未知数，并且未知数最高次数为 1 的等式，可通过等式性质逐步化为 x=a。",
        "concepts": ["等式两边同时加、减、乘或除以同一个非零数，等式仍成立", "标准步骤：去分母、去括号、移项、合并同类项、系数化为 1", "移项本质是等式两边同时进行相同运算"],
        "formula": "ax+b=0（a≠0）⇒ x=-b/a",
        "pitfalls": ["移项后忘记变号", "去括号时漏乘某一项", "系数化为 1 时只除了一边"],
        "example": {"question": "解方程 3(x-2)+5=11。", "answer": "x=4", "steps": ["去括号：3x-6+5=11", "合并：3x-1=11", "移项：3x=12", "系数化为1：x=4"]},
        "quiz": [
            {"question": "方程 2x+3=9 移项后正确的是？", "options": ["2x=9+3", "2x=9-3", "x=9-3"], "correct_index": 1, "explanation": "等式两边同时减去 3。"},
            {"question": "去括号 2(x-3) 的结果是？", "options": ["2x-3", "2x-6", "x-6"], "correct_index": 1, "explanation": "括号内每一项都要乘 2。"},
            {"question": "5x=20 的解是？", "options": ["x=4", "x=15", "x=25"], "correct_index": 0, "explanation": "等式两边同时除以 5。"},
        ],
    },
    "运算顺序与括号": {
        "summary": "混合运算先处理括号，再乘除、后加减；同级运算从左到右。",
        "concepts": ["括号会改变默认运算顺序", "同一级运算按从左到右计算", "折扣、优惠券等情境要先确定业务发生顺序再列式"],
        "formula": "括号 → 乘方 → 乘除 → 加减",
        "pitfalls": ["去掉括号后仍按原顺序心算", "把“先打折再满减”和“先满减再打折”混为一谈", "小数计算时忽略位数和单位"],
        "example": {"question": "商品原价 45 元，先减 8 元再打 9 折，应付多少？", "answer": "33.3 元", "steps": ["先满减：45-8=37", "再打折：37×0.9=33.3", "保留单位：33.3 元"]},
        "quiz": [
            {"question": "计算 20-3×4，应先算什么？", "options": ["20-3", "3×4", "从左到右任选"], "correct_index": 1, "explanation": "乘除优先于加减。"},
            {"question": "(20-3)×4 的第一步是？", "options": ["3×4", "20-3", "20×4"], "correct_index": 1, "explanation": "先计算括号内。"},
            {"question": "100 元先打 8 折再减 10 元，应列式为？", "options": ["(100-10)×0.8", "100×0.8-10", "100-10×0.8"], "correct_index": 1, "explanation": "业务顺序是先乘 0.8，再减 10。"},
        ],
    },
    "现在完成时": {
        "summary": "表示过去发生但与现在仍有联系的动作，或从过去持续到现在的状态。",
        "concepts": ["结构：have/has + 过去分词", "I/you/we/they 用 have，he/she/it 用 has", "常与 already、yet、ever、never、since、for 连用"],
        "formula": "主语 + have/has + past participle",
        "pitfalls": ["第三人称单数误用 have", "把过去分词写成一般过去式", "与明确过去时间连用时混淆一般过去时"],
        "example": {"question": "Maya 已经练习了 18 段对话。", "answer": "Maya has practiced 18 dialogues.", "steps": ["主语 Maya 是第三人称单数，选 has", "practice 的过去分词是 practiced", "组合完整主谓宾"]},
        "quiz": [
            {"question": "She ___ finished her homework.", "options": ["have", "has", "had"], "correct_index": 1, "explanation": "She 是第三人称单数。"},
            {"question": "write 的过去分词是？", "options": ["wrote", "written", "writing"], "correct_index": 1, "explanation": "write-wrote-written。"},
            {"question": "哪一句是现在完成时？", "options": ["I finished it yesterday.", "I have finished it.", "I will finish it."], "correct_index": 1, "explanation": "have + finished 构成现在完成时。"},
        ],
    },
    "主将从现": {
        "summary": "谈论真实可能发生的未来条件或时间时，主句用将来时，从句用一般现在时。",
        "concepts": ["if/when/unless/as soon as 等引导的从句用一般现在时", "主句常用 will + 动词原形", "从句主语为第三人称单数时动词仍要加 s/es"],
        "formula": "If/When + 一般现在时，主语 + will + 动词原形",
        "pitfalls": ["if 从句误用 will", "主句漏掉 will", "从句第三人称单数漏加 s/es"],
        "example": {"question": "如果她现在离开，她将赶上末班车。", "answer": "If she leaves now, she will catch the last bus.", "steps": ["if 从句使用一般现在时", "she 对应 leaves", "主句使用 will catch"]},
        "quiz": [
            {"question": "If it ___ tomorrow, we will stay home.", "options": ["will rain", "rains", "rained"], "correct_index": 1, "explanation": "if 从句用一般现在时。"},
            {"question": "When he arrives, I ___ him.", "options": ["call", "will call", "called"], "correct_index": 1, "explanation": "主句描述未来结果，用 will call。"},
            {"question": "哪一句正确？", "options": ["If she will come, I go.", "If she comes, I will go.", "If she come, I will go."], "correct_index": 1, "explanation": "从句一般现在时，主句一般将来时。"},
        ],
    },
    "OSI参考模型各层功能定位": {
        "summary": "OSI 参考模型用七个层次划分网络通信职责，使不同厂商的协议与设备可以按统一接口协作，并便于按层定位故障。",
        "concepts": [
            "物理层传输比特；数据链路层在同一链路上传输帧并进行差错检测；网络层负责跨网络寻址与路由",
            "传输层提供端到端传输、可靠性与流量控制；会话层管理会话；表示层处理编码、压缩和加密；应用层直接为应用提供网络服务",
            "发送端数据从应用层逐层封装，接收端从物理层逐层解封装；交换机主要工作在数据链路层，路由器主要工作在网络层",
        ],
        "formula": "应用层 → 表示层 → 会话层 → 传输层 → 网络层 → 数据链路层 → 物理层",
        "pitfalls": [
            "把传输层的端到端可靠传输与数据链路层的相邻节点帧传输混淆",
            "把 IP 寻址和路由归到数据链路层，或把 MAC 地址归到网络层",
            "只背七层顺序，却不能根据协议、地址、PDU 或设备判断其所属层次",
        ],
        "example": {
            "question": "主机 A 向异地服务器发送数据，途中路由器根据 IP 地址选择下一跳。该功能属于 OSI 哪一层，为什么？",
            "answer": "网络层，因为网络层负责逻辑寻址以及跨网络的路径选择与分组转发。",
            "steps": [
                "识别题干关键对象是 IP 地址和路由器",
                "IP 是网络层逻辑地址，跨网络路径选择属于路由功能",
                "因此定位到 OSI 第三层——网络层，而不是负责帧传输的数据链路层",
            ],
        },
        "quiz": [
            {
                "question": "负责端到端可靠传输、分段与重组的是哪一层？",
                "options": ["数据链路层", "传输层", "会话层"],
                "correct_index": 1,
                "explanation": "传输层面向端系统提供端到端传输，TCP 的可靠传输、分段和重组都属于该层。",
            },
            {
                "question": "交换机依据 MAC 地址转发以太网帧，主要对应 OSI 哪一层？",
                "options": ["物理层", "数据链路层", "网络层"],
                "correct_index": 1,
                "explanation": "MAC 地址和帧是数据链路层概念，二层交换机据此进行局域网内转发。",
            },
            {
                "question": "数据加密、压缩和字符编码转换主要属于哪一层？",
                "options": ["表示层", "会话层", "应用层"],
                "correct_index": 0,
                "explanation": "表示层负责数据表示形式的转换，包括编码、加密和压缩。",
            },
        ],
    },
}

ADVANCED_CONTENT = {
    "一元一次方程": {
        "focus": "从直接求解提升到含参数、分式和实际建模，重点判断方程在什么条件下有唯一解。",
        "quiz": [
            {"question": "关于 x 的方程 (a-2)x=6 有唯一解的条件是？", "options": ["a=2", "a≠2", "a≠0"], "correct_index": 1, "explanation": "未知数系数必须不为 0，所以 a-2≠0。"},
            {"question": "方程 (x-1)/2-(x+1)/3=1 的解是？", "options": ["x=7", "x=9", "x=11"], "correct_index": 2, "explanation": "同乘 6 得 3(x-1)-2(x+1)=6，解得 x=11。"},
            {"question": "甲数比乙数的 2 倍少 3，两数和为 18。设乙数为 x，正确方程是？", "options": ["2x-3+x=18", "2(x-3)+x=18", "2x+3+x=18"], "correct_index": 0, "explanation": "甲数是 2x-3，再利用两数和列方程。"},
        ],
    },
    "运算顺序与括号": {
        "focus": "从单一步骤运算提升到多重优惠、反向推理和方案比较，先把自然语言转换为完整算式。",
        "quiz": [
            {"question": "商品 200 元，先打 8 折，再满 150 减 20，最后加 5 元运费，应付多少？", "options": ["145 元", "150 元", "165 元"], "correct_index": 0, "explanation": "200×0.8-20+5=145。"},
            {"question": "某商品打 9 折后再减 12 元，实付 78 元。原价是多少？", "options": ["90 元", "100 元", "110 元"], "correct_index": 1, "explanation": "设原价 x 元，0.9x-12=78，解得 x=100。"},
            {"question": "原价 120 元。方案甲：先减 20 再打 9 折；方案乙：先打 9 折再减 20。哪种更便宜？", "options": ["甲便宜 2 元", "乙便宜 2 元", "价格相同"], "correct_index": 1, "explanation": "甲为 90 元，乙为 88 元，业务顺序会改变结果。"},
        ],
    },
    "现在完成时": {
        "focus": "从结构辨认提升到 since/for、延续性动词以及与一般过去时的语境区分。",
        "quiz": [
            {"question": "He ___ the book for two weeks.", "options": ["has borrowed", "has kept", "borrowed"], "correct_index": 1, "explanation": "for two weeks 表示持续时间，要用可延续的 kept。"},
            {"question": "I ___ him in 2024, and we ___ friends since then.", "options": ["met; have been", "have met; were", "met; were"], "correct_index": 0, "explanation": "明确过去时间用 met；since then 延续至今用 have been。"},
            {"question": "How long ___ she ___ in Shanghai?", "options": ["has; lived", "did; lived", "has; live"], "correct_index": 0, "explanation": "询问持续到现在的时长，用 has lived。"},
        ],
    },
    "主将从现": {
        "focus": "从单一 if 句型提升到 unless、as soon as、多从句组合及语义等价转换。",
        "quiz": [
            {"question": "Unless you ___ now, you ___ the train.", "options": ["leave; will miss", "will leave; miss", "leave; miss"], "correct_index": 0, "explanation": "unless 从句用一般现在时，主句用一般将来时。"},
            {"question": "I will call you as soon as he ___.", "options": ["will arrive", "arrives", "arrived"], "correct_index": 1, "explanation": "as soon as 引导时间从句，用一般现在时表示将来。"},
            {"question": "If she doesn't hurry, she will be late. 的同义句是？", "options": ["Unless she hurries, she will be late.", "Unless she will hurry, she is late.", "If she hurries, she will be late."], "correct_index": 0, "explanation": "unless 等于 if...not，且从句遵循主将从现。"},
        ],
    },
    "OSI参考模型各层功能定位": {
        "focus": "从背诵七层名称提升到根据协议、PDU、地址类型、网络设备和故障现象进行跨层定位与边界辨析。",
        "quiz": [
            {
                "question": "主机能解析域名并获得 IP，但无法与目标建立 TCP 连接；若网络层连通正常，下一步优先检查哪一层？",
                "options": ["物理层", "传输层", "表示层"],
                "correct_index": 1,
                "explanation": "网络层已确认连通，而 TCP 建连、端口和端到端连接状态属于传输层。",
            },
            {
                "question": "以下封装顺序正确的是？",
                "options": ["数据→段→分组→帧→比特", "数据→帧→段→分组→比特", "数据→分组→段→帧→比特"],
                "correct_index": 0,
                "explanation": "应用数据向下依次成为传输层段、网络层分组、链路层帧，最终转为物理层比特。",
            },
            {
                "question": "路由器转发 IP 分组时，哪组字段分别体现二层和三层信息？",
                "options": ["端口号与会话标识", "MAC 地址与 IP 地址", "字符编码与压缩格式"],
                "correct_index": 1,
                "explanation": "MAC 地址属于数据链路层，IP 地址属于网络层；路由转发过程中二层首部会逐跳变化。",
            },
        ],
    },
}

_DYNAMIC_CARD_CACHE: dict[tuple[str, str, str], dict] = {}
_DYNAMIC_CARD_LOCKS: dict[tuple[str, str, str], asyncio.Lock] = {}


def _parse_generated_card(raw: str, name: str, mode: str) -> dict:
    match = re.search(r"\{[\s\S]*\}", raw or "")
    if not match:
        raise ValueError("AI response has no JSON object")
    data = json.loads(match.group(0))
    required_text = ("summary", "formula")
    if any(not isinstance(data.get(key), str) or not data[key].strip() for key in required_text):
        raise ValueError("generated card misses required text")
    for key in ("concepts", "pitfalls", "quiz"):
        if not isinstance(data.get(key), list) or len(data[key]) < (2 if mode == "quick" else 3):
            raise ValueError(f"generated card misses {key}")
    example = data.get("example")
    if not isinstance(example, dict) or not all(example.get(key) for key in ("question", "answer", "steps")):
        raise ValueError("generated card misses example")
    if not isinstance(example["steps"], list) or len(example["steps"]) < 2:
        raise ValueError("generated example has too few steps")
    quiz_count = 2 if mode == "quick" else 3
    data["quiz"] = data["quiz"][:quiz_count]
    for item in data["quiz"]:
        if not isinstance(item, dict):
            raise ValueError("invalid quiz item")
        options = item.get("options")
        correct_index = item.get("correct_index")
        if (
            not item.get("question")
            or not item.get("explanation")
            or not isinstance(options, list)
            or len(options) != 3
            or not isinstance(correct_index, int)
            or not 0 <= correct_index < 3
        ):
            raise ValueError("invalid quiz structure")
        # 模型有时会把“A. / B. / C.”写进选项正文，前端本身也会生成
        # 选项序号。入库/缓存前统一去掉前缀，避免显示成“A. A. …”。
        item["options"] = [
            re.sub(r"^\s*[A-CＡ-Ｃ][.．、:：]\s*", "", str(option))
            for option in options
        ]

    # Reject the former generic template and cards that barely mention the target.
    serialized = json.dumps(data, ensure_ascii=False)
    generic_markers = ("答案格式", "做题速度", "只抄答案", "记住一道例题")
    if any(marker in serialized for marker in generic_markers):
        raise ValueError("generic placeholder content detected")
    ascii_tokens = re.findall(r"[A-Za-z][A-Za-z0-9+.#-]{1,}", name)
    if ascii_tokens:
        relevance_hits = sum(
            serialized.lower().count(token.lower()) for token in ascii_tokens
        )
        is_relevant = relevance_hits >= 3
    else:
        exact_hits = serialized.count(name)
        # 复合概念通常不会在自然讲解中反复逐字复述完整问题，例如
        # “进程与线程的区别”会分别讲“进程”和“线程”。拆出有意义的
        # 主题词校验，仍要求至少两个主题词实际出现，避免放宽成泛化内容。
        topic_tokens = [
            token.strip("？?：:，,。 ")
            for token in re.split(
                r"(?:有什么区别|有何区别|的区别|什么是|与|和|及|、|/)",
                name,
            )
            if len(token.strip("？?：:，,。 ")) >= 2
        ]
        matched_topics = [
            token for token in topic_tokens if token in serialized
        ]
        topic_hits = sum(serialized.count(token) for token in matched_topics)
        required_topics = min(2, len(set(topic_tokens)))
        is_relevant = (
            exact_hits >= 2
            or (
                required_topics > 0
                and len(set(matched_topics)) >= required_topics
                and topic_hits >= 3
            )
        )
    if not is_relevant:
        raise ValueError("generated card is not relevant enough")

    data["concepts"] = data["concepts"][:3]
    data["pitfalls"] = data["pitfalls"][:3]
    if mode == "advanced" and not str(data.get("advanced_focus") or "").strip():
        raise ValueError("advanced card misses advanced_focus")
    return data


async def _generate_dynamic_card(name: str, subject: Optional[str], mode: str) -> dict:
    key = ((subject or "").strip(), name, mode)
    if key in _DYNAMIC_CARD_CACHE:
        return _DYNAMIC_CARD_CACHE[key]
    lock = _DYNAMIC_CARD_LOCKS.setdefault(key, asyncio.Lock())
    async with lock:
        if key in _DYNAMIC_CARD_CACHE:
            return _DYNAMIC_CARD_CACHE[key]
        from backend.agents.agent.get_llm import get_llm

        level_instruction = (
            "快速回顾：自测仅2题，聚焦最核心辨析。"
            if mode == "quick"
            else "进阶巩固：内容必须包含复杂情境、跨层关联或迁移分析，并提供advanced_focus。"
            if mode == "advanced"
            else "完整复习：覆盖概念、结构、易错点、典型应用与3题自测。"
        )
        prompt = f"""
你是严谨的大学课程教研老师。请为“{subject or '当前课程'}”中的知识点“{name}”编写复习卡。
{level_instruction}
内容必须是该知识点的真实学科知识，不得使用“先看定义、再做题”“答案格式、做题速度”等通用学习方法占位。
核心概念要准确回答它解决什么问题、关键组成或机制是什么；典型例题必须能用该知识点推理出确定答案；
自测题必须直接考查该知识点，每题3个选项且只有1个正确答案，干扰项要来自真实易错理解。
只输出JSON对象，字段严格为：
{{
  "summary":"具体概念摘要",
  "concepts":["具体要点1","具体要点2","具体要点3"],
  "formula":"核心结构、流程、模型或方法",
  "pitfalls":["具体易错点1","具体易错点2","具体易错点3"],
  "example":{{"question":"代表性问题","answer":"明确答案","steps":["推理1","推理2","推理3"]}},
  "quiz":[
    {{"question":"题目","options":["A内容","B内容","C内容"],"correct_index":0,"explanation":"知识依据"}}
  ],
  "advanced_focus":"仅进阶模式需要的迁移目标，其他模式可为空字符串"
}}
"""
        response = await get_llm().ainvoke(prompt)
        card = _parse_generated_card(
            getattr(response, "content", None) or str(response), name, mode
        )
        _DYNAMIC_CARD_CACHE[key] = card
        return card


def _generic_card(name: str) -> dict:
    return {
        "summary": f"「{name}」需要从定义、适用条件、基本方法和典型错误四个方面建立完整理解。",
        "concepts": [f"准确说出「{name}」的定义和解决的问题", "识别它成立或适用的必要条件", "掌握标准步骤，并能解释每一步的依据"],
        "formula": "先理解定义与条件，再记忆结论并通过例题验证",
        "pitfalls": ["只记结论，不理解适用条件", "遇到变式题时机械套用", "订正后没有总结错误发生在哪一步"],
        "example": {"question": f"请用自己的话说明「{name}」解决什么问题。", "answer": "应包含定义、适用条件和一个典型应用。", "steps": ["先说定义", "补充适用条件", "给出一个例子"]},
        "quiz": [
            {"question": f"复习「{name}」时最先应该确认什么？", "options": ["定义与适用条件", "答案格式", "做题速度"], "correct_index": 0, "explanation": "理解定义和边界是正确应用的前提。"},
            {"question": "发现同类题反复出错时，最有效的做法是？", "options": ["只抄答案", "定位出错步骤并做变式题", "跳过该题"], "correct_index": 1, "explanation": "定位错误机制才能形成迁移。"},
            {"question": "判断是否真正掌握知识点的较好标准是？", "options": ["看过解析", "能独立解释并完成变式", "记住一道例题"], "correct_index": 1, "explanation": "能解释和迁移比短期记忆更可靠。"},
        ],
    }


def _card_for_mode(name: str, mode: str) -> dict:
    card = dict(CARDS.get(name) or _generic_card(name))
    card["concepts"] = list(card["concepts"])
    card["quiz"] = [dict(item) for item in card["quiz"]]
    if mode == "quick":
        card["concepts"] = card["concepts"][:2]
        card["quiz"] = card["quiz"][:2]
    elif mode == "advanced":
        advanced = ADVANCED_CONTENT.get(name)
        card["advanced_focus"] = (
            advanced["focus"] if advanced
            else f"综合运用「{name}」解决条件变化、反向推理和跨情境迁移问题。"
        )
        card["quiz"] = [dict(item) for item in (
            advanced["quiz"] if advanced else [
                {"question": f"面对「{name}」的陌生变式，第一步最合理的是？", "options": ["直接套结论", "识别条件变化并重建解题关系", "照抄旧题步骤"], "correct_index": 1, "explanation": "迁移题的关键是判断条件和关系发生了什么变化。"},
                {"question": "完成一道综合题后，哪种复盘最能提升迁移能力？", "options": ["只核对答案", "总结关键条件、方法选择和可替换变量", "记住题目数字"], "correct_index": 1, "explanation": "抽取稳定的方法结构，才能迁移到新情境。"},
                {"question": "原有方法不再适用时应该怎么做？", "options": ["继续机械套用", "回到定义检查适用边界并调整策略", "跳过所有变式"], "correct_index": 1, "explanation": "适用条件改变时，应从定义和边界重新推导。"},
            ]
        )]
    return card


async def _card_for_mode_with_ai(
    name: str, subject: Optional[str], mode: str
) -> dict:
    if name in CARDS:
        return _card_for_mode(name, mode)
    try:
        return await _generate_dynamic_card(name, subject, mode)
    except Exception as exc:
        logger.exception(
            "dynamic knowledge card generation failed: subject=%s, name=%s, mode=%s",
            subject,
            name,
            mode,
        )
        raise BusinessError(
            "KNOWLEDGE_REVIEW_GENERATION_FAILED",
            f"「{name}」的专业复习内容生成失败，请稍后重试",
            503,
        ) from exc


class KnowledgeReviewService:
    async def get_card(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        knowledge_point_name: str,
        subject: Optional[str],
        mode: str,
    ) -> dict:
        name = knowledge_point_name.strip()
        if not name or name in {"综合知识点", "其他", "未知知识点"}:
            raise BusinessError("INVALID_KNOWLEDGE_POINT", "请选择具体知识点", 422)

        mastery = (
            await db.execute(
                select(KnowledgeMastery).where(
                    KnowledgeMastery.user_id == user_id,
                    KnowledgeMastery.knowledge_point_name == name,
                ).order_by(KnowledgeMastery.updated_at.desc()).limit(1)
            )
        ).scalar_one_or_none()
        mistake_conditions = [
            Mistake.user_id == user_id,
            Mistake.knowledge_point_name == name,
        ]
        if subject:
            mistake_conditions.append(Mistake.subject == subject)
        mistakes = (
            await db.execute(
                select(Mistake)
                .where(*mistake_conditions)
                .order_by(Mistake.created_at.desc())
                .limit(20)
            )
        ).scalars().all()
        latest_review = (
            await db.execute(
                select(KnowledgeReviewRecord)
                .where(
                    KnowledgeReviewRecord.user_id == user_id,
                    KnowledgeReviewRecord.knowledge_point_name == name,
                    KnowledgeReviewRecord.review_mode == mode,
                )
                .order_by(
                    KnowledgeReviewRecord.completed_at.desc(),
                    KnowledgeReviewRecord.id.desc(),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        completed_modes = set(
            (
                await db.execute(
                    select(KnowledgeReviewRecord.review_mode).where(
                        KnowledgeReviewRecord.user_id == user_id,
                        KnowledgeReviewRecord.knowledge_point_name == name,
                    )
                )
            ).scalars().all()
        )
        error_counts = {}
        for item in mistakes:
            if item.error_type:
                error_counts[item.error_type] = error_counts.get(item.error_type, 0) + 1
        error_map = {"knowledge": "概念不清", "calculation": "计算错误", "reading": "审题错误", "method": "方法选择不当"}
        top_error = max(error_counts, key=error_counts.get) if error_counts else None

        card = await _card_for_mode_with_ai(name, subject, mode)
        card.update({
            "knowledge_point_name": name,
            "subject": subject,
            "mode": mode,
            "mastery_score": mastery.mastery_score if mastery else None,
            "learning_status": mastery.learning_status if mastery else None,
            "personalized_insight": (
                f"你在该知识点共有 {len(mistakes)} 道历史错题，最常见问题是"
                f"「{error_map.get(top_error, top_error)}」。建议先针对这一错误复习，再开始订正。"
                if mistakes else "目前没有关联错题，可以通过概念自测检查是否真正掌握。"
            ),
            "mistake_summary": {
                "total": len(mistakes),
                "pending": sum(m.correction_status != "corrected" for m in mistakes),
                "corrected": sum(m.correction_status == "corrected" for m in mistakes),
                "top_error_type": top_error,
            },
            "related_mistakes": [{
                "mistake_id": m.id,
                "question_content": m.question_content,
                "correction_status": m.correction_status,
                "error_type": m.error_type,
            } for m in mistakes[:5]],
            "review_progress": (
                {
                    "completed": True,
                    "review_id": latest_review.id,
                    "answers": list(latest_review.answers or []),
                    "quiz_score": latest_review.quiz_score,
                    "quiz_total": latest_review.quiz_total,
                    "passed": (
                        latest_review.quiz_total > 0
                        and latest_review.quiz_score / latest_review.quiz_total >= 0.67
                    ),
                    "completed_at": (
                        latest_review.completed_at.isoformat()
                        if latest_review.completed_at else None
                    ),
                }
                if latest_review else None
            ),
            "completed_modes": sorted(completed_modes),
        })
        return card

    async def complete(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        payload,
        request_id: str,
    ) -> dict:
        existing = (
            await db.execute(
                select(KnowledgeReviewRecord).where(
                    KnowledgeReviewRecord.request_id == request_id
                )
            )
        ).scalar_one_or_none()
        if existing:
            return self._record_data(existing)

        card = await _card_for_mode_with_ai(
            payload.knowledge_point_name, payload.subject, payload.review_mode
        )
        quiz = card["quiz"]
        answers = list(payload.answers)
        score = sum(
            1 for index, item in enumerate(quiz)
            if index < len(answers) and answers[index] == item["correct_index"]
        )
        record = KnowledgeReviewRecord(
            user_id=user_id,
            subject=payload.subject,
            knowledge_point_name=payload.knowledge_point_name,
            review_mode=payload.review_mode,
            quiz_score=score,
            quiz_total=len(quiz),
            answers=answers,
            request_id=request_id,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return self._record_data(record)

    @staticmethod
    def _record_data(record: KnowledgeReviewRecord) -> dict:
        return {
            "review_id": record.id,
            "knowledge_point_name": record.knowledge_point_name,
            "review_mode": record.review_mode,
            "quiz_score": record.quiz_score,
            "quiz_total": record.quiz_total,
            "passed": record.quiz_total > 0 and record.quiz_score / record.quiz_total >= 0.67,
            "completed_at": record.completed_at.isoformat() if record.completed_at else None,
        }


knowledge_review_service = KnowledgeReviewService()

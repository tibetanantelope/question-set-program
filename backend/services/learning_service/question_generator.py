"""成员二：基于大模型的动态出题（题库未覆盖的知识点/科目走这里）。

设计：
- 预置题库覆盖的数学知识点仍用题库（答案精确、判分可靠、零延迟）；
- 题库未覆盖的知识点/科目由本模块调用 LLM 动态生成，支持任意科目；
- LLM 只在此模块内被 **懒加载** 调用，保持 learning_service 的导入链干净、
  单元测试无需网络（解析逻辑为纯函数，可独立测试）。
"""

import ast
import json
import math
import os
import random
import re
import uuid
from typing import List, Optional

import httpx

_ARITHMETIC_CHARS = re.compile(
    r"(?<![A-Za-z0-9_.])[-+]?\d[\d\s+\-−×xX*÷/().=]*\d(?![A-Za-z0-9_.])"
)


def _safe_numeric_eval(expression: str) -> Optional[float]:
    """Evaluate a numeric arithmetic expression without executing arbitrary code."""
    normalized = (
        expression.replace("−", "-")
        .replace("×", "*")
        .replace("÷", "/")
        .replace("（", "(")
        .replace("）", ")")
        .replace(" ", "")
    )
    # The letter x is accepted as a multiplication sign only between numbers/brackets.
    normalized = re.sub(r"(?<=[\d)])\s*[xX]\s*(?=[\d(])", "*", normalized)
    if not normalized or not re.fullmatch(r"[\d.+\-*/()]+", normalized):
        return None
    try:
        node = ast.parse(normalized, mode="eval")
    except (SyntaxError, ValueError):
        return None

    allowed_binary = (ast.Add, ast.Sub, ast.Mult, ast.Div)
    allowed_unary = (ast.UAdd, ast.USub)

    def evaluate(current):
        if isinstance(current, ast.Expression):
            return evaluate(current.body)
        if isinstance(current, ast.Constant) and isinstance(current.value, (int, float)):
            return float(current.value)
        if isinstance(current, ast.UnaryOp) and isinstance(current.op, allowed_unary):
            value = evaluate(current.operand)
            return value if isinstance(current.op, ast.UAdd) else -value
        if isinstance(current, ast.BinOp) and isinstance(current.op, allowed_binary):
            left, right = evaluate(current.left), evaluate(current.right)
            if isinstance(current.op, ast.Add):
                return left + right
            if isinstance(current.op, ast.Sub):
                return left - right
            if isinstance(current.op, ast.Mult):
                return left * right
            if right == 0:
                raise ZeroDivisionError
            return left / right
        raise ValueError("unsupported arithmetic expression")

    try:
        result = float(evaluate(node))
    except (ValueError, TypeError, ZeroDivisionError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def arithmetic_explanations_are_consistent(text: str) -> bool:
    """Reject explanations containing a false fully-numeric equality chain."""
    for match in _ARITHMETIC_CHARS.finditer(text or ""):
        chain = match.group(0).strip(" ,，;；:：。")
        if "=" not in chain:
            continue
        values = [_safe_numeric_eval(part) for part in chain.split("=")]
        if len(values) < 2 or any(value is None for value in values):
            continue
        if any(not math.isclose(values[0], value, rel_tol=1e-9, abs_tol=1e-9) for value in values[1:]):
            return False
    return True

_DIFFICULTY_LABEL = {'easy': '简单', 'medium': '中等', 'hard': '困难'}

# 出题多样性：随机挑选一个切入角度，避免同一知识点每次都出雷同题面
_VARIETY_ANGLES = [
    '优先考察实际生活情境的应用题', '侧重概念辨析与易错点', '结合图形/表格信息',
    '设计需要多步推理的综合题', '从常见错误入手设计陷阱题', '用不同的数值与背景包装',
    '偏重快速心算与估算', '强调逆向思维（已知结果求条件）',
]


def llm_available() -> bool:
    """是否启用真实 LLM 出题；可通过 LLM_PRACTICE_ENABLED=false 显式关闭。"""
    enabled = os.getenv('LLM_PRACTICE_ENABLED', 'true').strip().lower()
    return enabled not in {'0', 'false', 'no', 'off'} and bool(os.getenv('API_KEY'))


def build_prompt(
    kp_name: str,
    difficulty: str,
    count: int,
    subject: Optional[str],
    user_desc: Optional[str] = None,
    stage: Optional[str] = None,
    grade: Optional[str] = None,
) -> str:
    """构造出题提示词。要求答案简洁、可自动判分，输出严格 JSON。

    user_desc：用户在诊断时的原始描述/薄弱点，用于让题目真正贴合其困惑；
    另叠加随机“出题角度”与唯一批次标记，提升每次生成的多样性、避免重复。
    """
    diff_label = _DIFFICULTY_LABEL.get(difficulty, '中等')
    subj = f'「{subject}」科目的' if subject else ''
    angle = random.choice(_VARIETY_ANGLES)
    batch = uuid.uuid4().hex[:8]

    lines = [
        f'你是一名资深命题老师。请为{subj}知识点「{kp_name}」出 {count} 道{diff_label}难度的练习题。',
    ]
    if stage or grade:
        lines.append(f'学生范围：{stage or ""} {grade or ""}。所有题目必须严格位于该学段和年级课程范围内。')
    if '随机巩固' in kp_name:
        lines.append(
            f'学生没有指定薄弱知识点。请从{grade or "当前年级"}{subject or "当前学科"}'
            '课程范围内抽取有代表性的具体知识点；每道题仍必须标注准确、具体的知识点名称，'
            '不得使用“综合知识点”“其他”或“未知知识点”。'
        )
    if user_desc:
        desc = user_desc.strip()[:500]
        lines.append(
            f'下面包含本次任务类型和学生原始输入。必须遵循任务策略并紧扣本次问题出题：\n'
            f'“{desc}”'
        )
    lines.append('要求：')
    lines.append(f'1. 恰好 {count} 道，题目互不重复，且与以往常见模板不同，力求新颖；')
    lines.append(
        '2. 每道题都要有明确、唯一的标准答案，答案尽量简洁并采用标准写法，'
        '便于程序自动判分（例如：x=5、1/2、0.8、C、正确）；'
    )
    lines.append('3. 每道题都要给出简短、确定的解析，解析推导结果必须与标准答案完全一致；')
    lines.append(f'4. 本次出题请{angle}，在保证知识点准确的前提下变换题目情境与数值；')
    lines.append('5. 只输出一个 JSON 数组，不要输出任何多余文字或 markdown 代码块标记。')
    lines.append(f'（本批次编号 {batch}，仅用于区分批次，不要出现在题目中。）')
    lines.append(
        '6. 同时给出 answer_type（numeric/symbolic/set/proof/code/short_text）和 grading_spec；'
    )
    lines.append(
        'grading_spec 至少包含 acceptable_forms、required_points、unit、tolerance，'
        '不适用时使用空数组或 null；'
    )
    lines.append('输出格式（严格遵守字段名）：')
    lines.append(
        '[{"content":"题干","knowledge_point_name":"具体知识点名称","ans":"标准答案","answer_type":"numeric",'
        '"grading_spec":{"acceptable_forms":[],"required_points":[],'
        '"unit":null,"tolerance":0},"analysis":"解析"}]'
    )
    return '\n'.join(lines)


def parse_llm_questions(text: str) -> List[dict]:
    """从 LLM 原始输出解析题目列表（纯函数，容错 markdown 包裹与多余文字）。

    返回 [{content, ans, analysis}, ...]；解析失败抛出 ValueError（上层视为生成失败）。
    """
    if not text or not text.strip():
        raise ValueError('empty LLM output')

    raw = text.strip()
    # 去掉 ```json ... ``` 或 ``` ... ``` 包裹
    fence = re.search(r'```(?:json)?\s*(.*?)```', raw, re.DOTALL)
    if fence:
        raw = fence.group(1).strip()

    # 截取第一个 JSON 数组
    start = raw.find('[')
    end = raw.rfind(']')
    if start == -1 or end == -1 or end <= start:
        raise ValueError('no JSON array found in LLM output')
    payload = raw[start:end + 1]

    data = json.loads(payload)  # 失败自然抛 JSONDecodeError（ValueError 子类）
    if not isinstance(data, list):
        raise ValueError('LLM output is not a JSON array')

    out: List[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        content = str(item.get('content') or item.get('question') or '').strip()
        ans = str(item.get('ans') or item.get('answer') or item.get('standard_answer') or '').strip()
        analysis = str(item.get('analysis') or item.get('explanation') or '').strip()
        answer_type = str(item.get('answer_type') or 'short_text').strip().lower()
        if answer_type not in {'numeric', 'symbolic', 'set', 'proof', 'code', 'short_text'}:
            answer_type = 'short_text'
        grading_spec = item.get('grading_spec')
        if not isinstance(grading_spec, dict):
            grading_spec = {}
        parsed = {
            'content': content,
            'ans': ans,
            'analysis': analysis,
            'answer_type': answer_type,
            'grading_spec': grading_spec,
        }
        knowledge_point_name = str(item.get('knowledge_point_name') or '').strip()
        if knowledge_point_name:
            parsed['knowledge_point_name'] = knowledge_point_name
        out.append(parsed)
    return out


def _build_diverse_llm():
    """构造一个高温度 LLM 实例用于出题（更强多样性）。

    不复用团队共享的 get_llm（temperature=0.3 固定，出题偏保守易重复）；
    在本模块内单独读取环境变量、创建 ChatOpenAI，temperature 提高到 0.9。
    读取不到配置时返回 None，交由上层回退。
    """
    from langchain_openai import ChatOpenAI

    model = os.getenv('MODEL_NAME')
    api_key = os.getenv('API_KEY')
    base_url = os.getenv('API_URL')
    if not (model and api_key and base_url):
        return None
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=0.9,
        http_async_client=httpx.AsyncClient(trust_env=False),
    )


async def generate_questions_via_llm(
    kp_name: str,
    difficulty: str,
    count: int,
    subject: Optional[str] = None,
    user_desc: Optional[str] = None,
    stage: Optional[str] = None,
    grade: Optional[str] = None,
) -> List[dict]:
    """调用 LLM 生成题目并解析。异常上抛，由上层统一按“生成失败”处理（重试/清晰失败）。

    user_desc：用户诊断时的原始描述/薄弱点，注入提示词让题目更贴合真实困惑。
    出题使用高温度实例以提升多样性；若本模块无法构造，则回退到共享 get_llm。
    """
    prompt = build_prompt(kp_name, difficulty, count, subject, user_desc, stage, grade)

    llm = _build_diverse_llm()
    if llm is None:
        # 懒加载：仅在真正出题时才引入共享 LLM（避免把 llama_index 拉进导入链）
        from backend.agents.agent.get_llm import get_llm
        llm = get_llm()

    resp = await llm.ainvoke(prompt)
    text = getattr(resp, 'content', None) or str(resp)
    return parse_llm_questions(text)


async def identify_knowledge_point_via_llm(
    content: str,
    subject: str,
    stage: str,
    grade: str,
) -> Optional[str]:
    """Classify an explicit learning question into one concrete curriculum point."""
    if not llm_available():
        return None
    prompt = (
        f'你是课程知识点分类器。学段：{stage}；年级：{grade}；学科：{subject}。'
        f'学生输入：“{content[:500]}”\n'
        '判断它对应的一个最具体、规范的教材知识点名称。'
        '如果输入没有指定任何确定内容，只返回空字符串。'
        '只输出 JSON：{"knowledge_point_name":"名称或空字符串"}'
    )
    try:
        llm = _build_diverse_llm()
        if llm is None:
            from backend.agents.agent.get_llm import get_llm
            llm = get_llm()
        response = await llm.ainvoke(prompt)
        raw = getattr(response, 'content', None) or str(response)
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not match:
            return None
        name = str(json.loads(match.group(0)).get('knowledge_point_name') or '').strip()
        if not name or name in {'综合知识点', '其他', '未知知识点'}:
            return None
        return name[:128]
    except Exception:
        return None

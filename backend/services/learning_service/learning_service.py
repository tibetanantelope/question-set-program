"""成员二：智能诊断与练习生成 Service。

职责（对齐《五人任务分工》第 4 节 + 《业务设计》第 5 节）：
- 学情诊断：识别知识点、评估掌握度、给出薄弱点与练习建议；
- 针对性练习生成：预置题库 + 内容质量校验 + 一次自动重试；
- 三级难度调整：连续答对两题升难，连续答错两题降难；
- 判题与错因分类：knowledge / calculation / reading / method；
- 写操作幂等（request_id）；生成或校验失败不创建有效练习。

大模型接入尚未就绪，本实现沿用诊断 Service 的“预置题库”轻量策略，
并保留 _raw_generate 钩子便于后续替换为真实 LLM 调用与 mock 测试。
"""

import inspect
import re
from datetime import datetime, timezone, timedelta
from typing import Callable, List, Optional

from backend.core.exceptions import BusinessError
from backend.dao.learning_mapper import LearningMapper
from backend.dao.user_profile_mapper import UserProfileMapper
from backend.model.learning import Diagnosis, Practice, Question
from backend.schemas.request.learning_request import (
    DiagnosisRequest,
    PracticeGenerateRequest,
    AnswerSubmitRequest,
)
from backend.schemas.response.learning_response import (
    DiagnosisResponse,
    PracticeResponse,
    QuestionItem,
    AnswerResultItem,
    AnswerSubmitResponse,
)

# 难度顺序（用于升降级）
_DIFFICULTY_ORDER = ['easy', 'medium', 'hard']

# 错因类型
_ERROR_KNOWLEDGE = 'knowledge'      # 知识点未掌握（空答/概念错误）
_ERROR_CALCULATION = 'calculation'  # 计算/数值错误
_ERROR_READING = 'reading'          # 审题/理解错误
_ERROR_METHOD = 'method'            # 方法/步骤错误

# 东八区
_TZ = timezone(timedelta(hours=8))

# ───────────────────────────────────────────────
# 预置练习题库：按 [知识点关键词][难度] 组织
# 结构: {kp_keyword: {difficulty: [{content, ans, analysis}]}}
# 命中知识点关键词则用对应题，否则用通用回退生成器。
# ───────────────────────────────────────────────

_PRACTICE_BANK: dict = {
    '一元一次方程': {
        'easy': [
            {'content': '解方程：x + 5 = 12', 'ans': 'x=7', 'analysis': '两边同时减 5，得 x=7。'},
            {'content': '解方程：x - 3 = 8', 'ans': 'x=11', 'analysis': '两边同时加 3，得 x=11。'},
            {'content': '解方程：3x = 21', 'ans': 'x=7', 'analysis': '两边同时除以 3，得 x=7。'},
            {'content': '解方程：x + 9 = 15', 'ans': 'x=6', 'analysis': '移项得 x=15-9=6。'},
            {'content': '解方程：2x = 18', 'ans': 'x=9', 'analysis': '两边同时除以 2，得 x=9。'},
        ],
        'medium': [
            {'content': '解方程：3x - 5 = 10', 'ans': 'x=5', 'analysis': '移项得 3x=15，两边除以 3 得 x=5。'},
            {'content': '解方程：2x + 7 = 19', 'ans': 'x=6', 'analysis': '移项得 2x=12，x=6。'},
            {'content': '解方程：5x - 8 = 2x + 7', 'ans': 'x=5', 'analysis': '移项合并得 3x=15，x=5。'},
            {'content': '解方程：4x + 3 = 2x + 11', 'ans': 'x=4', 'analysis': '移项得 2x=8，x=4。'},
            {'content': '解方程：6x - 4 = 3x + 11', 'ans': 'x=5', 'analysis': '移项得 3x=15，x=5。'},
        ],
        'hard': [
            {'content': '解方程：2(x - 3) = 3(x - 5)', 'ans': 'x=9', 'analysis': '去括号得 2x-6=3x-15，移项得 x=9。'},
            {'content': '解方程：(x+1)/2 - (x-1)/3 = 1', 'ans': 'x=1', 'analysis': '去分母得 3(x+1)-2(x-1)=6，化简 x+5=6，x=1。'},
            {'content': '解方程：3(2x-1) - 2(x+2) = 5', 'ans': 'x=3', 'analysis': '去括号得 6x-3-2x-4=5，4x=12，x=3。'},
            {'content': '解方程：(2x-1)/3 = (x+2)/4', 'ans': 'x=2', 'analysis': '交叉相乘得 4(2x-1)=3(x+2)，8x-4=3x+6，5x=10，x=2。'},
            {'content': '解方程：5(x-2) - 3(2x-1) = -4', 'ans': 'x=-3', 'analysis': '去括号得 5x-10-6x+3=-4，-x-7=-4，x=-3。'},
        ],
    },
    '有理数': {
        'easy': [
            {'content': '计算：(-3) + 5 = ?', 'ans': '2', 'analysis': '异号相加取绝对值大的符号，5-3=2。'},
            {'content': '计算：(-4) + (-6) = ?', 'ans': '-10', 'analysis': '同号相加，符号不变，绝对值相加。'},
            {'content': '计算：7 - 10 = ?', 'ans': '-3', 'analysis': '减去一个数等于加它的相反数，7+(-10)=-3。'},
            {'content': '计算：(-2) × 3 = ?', 'ans': '-6', 'analysis': '异号相乘得负。'},
            {'content': '计算：(-8) ÷ 4 = ?', 'ans': '-2', 'analysis': '异号相除得负。'},
        ],
        'medium': [
            {'content': '计算：(-3) + 8 - 5 = ?', 'ans': '0', 'analysis': '按顺序计算：-3+8=5，5-5=0。'},
            {'content': '计算：(-2)³ = ?', 'ans': '-8', 'analysis': '负数的奇次方为负，(-2)×(-2)×(-2)=-8。'},
            {'content': '计算：|-5| + (-3) = ?', 'ans': '2', 'analysis': '绝对值 |-5|=5，5+(-3)=2。'},
            {'content': '计算：(-1)²⁰²⁶ = ?', 'ans': '1', 'analysis': '负数的偶次方为正，得 1。'},
            {'content': '计算：12 ÷ (-3) × 2 = ?', 'ans': '-8', 'analysis': '从左到右：12÷(-3)=-4，-4×2=-8。'},
        ],
        'hard': [
            {'content': '计算：(-2)² × 3 - (-4) ÷ 2 = ?', 'ans': '14', 'analysis': '4×3=12，(-4)÷2=-2，12-(-2)=14。'},
            {'content': '计算：-3² + (-2)³ = ?', 'ans': '-17', 'analysis': '-3²=-9，(-2)³=-8，-9+(-8)=-17。'},
            {'content': '计算：(-1/2) × (-4) + 2⁻¹ 说明：2⁻¹=0.5', 'ans': '2.5', 'analysis': '(-1/2)×(-4)=2，2+0.5=2.5。'},
            {'content': '计算：|-6| - (-3)² + 2 = ?', 'ans': '-1', 'analysis': '6-9+2=-1。'},
            {'content': '计算：(-2)⁴ ÷ (-4) × 3 = ?', 'ans': '-12', 'analysis': '16÷(-4)=-4，-4×3=-12。'},
        ],
    },
    '二次': {  # 一元二次方程 / 二次函数
        'easy': [
            {'content': '解方程：x² = 9', 'ans': 'x=±3', 'analysis': '开平方得 x=3 或 x=-3。'},
            {'content': '解方程：x² - 4 = 0', 'ans': 'x=±2', 'analysis': '移项得 x²=4，x=±2。'},
            {'content': '解方程：x² - 2x = 0', 'ans': 'x=0或x=2', 'analysis': '提取公因式 x(x-2)=0。'},
            {'content': '解方程：(x-1)² = 4', 'ans': 'x=3或x=-1', 'analysis': 'x-1=±2，得 x=3 或 x=-1。'},
            {'content': '解方程：x² - 16 = 0', 'ans': 'x=±4', 'analysis': '平方差，x=±4。'},
        ],
        'medium': [
            {'content': '解方程：x² - 5x + 6 = 0', 'ans': 'x=2或x=3', 'analysis': '因式分解 (x-2)(x-3)=0。'},
            {'content': '解方程：x² + 2x - 3 = 0', 'ans': 'x=1或x=-3', 'analysis': '因式分解 (x-1)(x+3)=0。'},
            {'content': '解方程：x² - 7x + 12 = 0', 'ans': 'x=3或x=4', 'analysis': '因式分解 (x-3)(x-4)=0。'},
            {'content': '求抛物线 y=x²-4x+3 与 x 轴交点的横坐标', 'ans': 'x=1或x=3', 'analysis': '令 y=0，(x-1)(x-3)=0。'},
            {'content': '解方程：2x² - 8 = 0', 'ans': 'x=±2', 'analysis': 'x²=4，x=±2。'},
        ],
        'hard': [
            {'content': '用求根公式解：x² - 3x + 1 = 0（结果保留根号）', 'ans': 'x=(3±√5)/2', 'analysis': 'Δ=9-4=5，x=(3±√5)/2。'},
            {'content': '求抛物线 y=x²-4x+3 的顶点坐标', 'ans': '(2,-1)', 'analysis': '配方 y=(x-2)²-1，顶点 (2,-1)。'},
            {'content': '解方程：2x² - 5x + 2 = 0', 'ans': 'x=2或x=1/2', 'analysis': '因式分解 (2x-1)(x-2)=0。'},
            {'content': '已知方程 x²-6x+k=0 有两个相等实根，求 k', 'ans': 'k=9', 'analysis': 'Δ=36-4k=0，k=9。'},
            {'content': '求抛物线 y=x²-2x-3 与 x 轴围成图形的对称轴', 'ans': 'x=1', 'analysis': '对称轴 x=-b/2a=1。'},
        ],
    },
    '概率': {  # 概率论 / 古典概型 / 条件概率
        'easy': [
            {'content': '掷一枚均匀硬币，正面朝上的概率是多少？', 'ans': '1/2', 'analysis': '两种等可能结果，正面占其一，概率为 1/2。'},
            {'content': '掷一个均匀骰子，出现点数 3 的概率是多少？', 'ans': '1/6', 'analysis': '6 种等可能结果，目标 1 种，概率为 1/6。'},
            {'content': '一副去掉大小王的 52 张扑克，随机抽 1 张是红桃的概率？', 'ans': '1/4', 'analysis': '红桃 13 张，13/52=1/4。'},
            {'content': '袋中有 3 个红球、2 个白球，随机取 1 个是红球的概率？', 'ans': '3/5', 'analysis': '红球 3 个共 5 个，概率 3/5。'},
            {'content': '掷一个均匀骰子，出现偶数点的概率是多少？', 'ans': '1/2', 'analysis': '偶数点为 2、4、6 共 3 种，3/6=1/2。'},
        ],
        'medium': [
            {'content': '同时掷两枚均匀硬币，恰好一正一反的概率是多少？', 'ans': '1/2', 'analysis': '4 种等可能结果中「正反」「反正」占 2 种，2/4=1/2。'},
            {'content': '掷两个均匀骰子，点数之和为 7 的概率是多少？', 'ans': '1/6', 'analysis': '和为 7 有 6 种组合，6/36=1/6。'},
            {'content': '从 1~10 中任取一个整数，取到 3 的倍数的概率是多少？', 'ans': '3/10', 'analysis': '3、6、9 共 3 个，3/10。'},
            {'content': '袋中 4 红 6 白共 10 球，不放回连取 2 个都是红球的概率？', 'ans': '2/15', 'analysis': '(4/10)×(3/9)=12/90=2/15。'},
            {'content': '掷一个骰子两次，至少出现一次 6 点的概率是多少？', 'ans': '11/36', 'analysis': '一次都不出 6 的概率 (5/6)²=25/36，故 1-25/36=11/36。'},
        ],
        'hard': [
            {'content': '已知 P(A)=0.6，P(B)=0.5，P(A∩B)=0.3，求 P(A∪B)。', 'ans': '0.8', 'analysis': 'P(A∪B)=P(A)+P(B)-P(A∩B)=0.6+0.5-0.3=0.8。'},
            {'content': '三条产线产量占比 0.5、0.3、0.2，次品率分别 0.02、0.03、0.04，随机取一件是次品的概率？', 'ans': '0.027', 'analysis': '全概率：0.5×0.02+0.3×0.03+0.2×0.04=0.027。'},
            {'content': '掷一个均匀骰子，点数的数学期望是多少？', 'ans': '3.5', 'analysis': '(1+2+3+4+5+6)/6=3.5。'},
            {'content': '已知 P(A)=0.7，P(B|A)=0.4，求 P(A∩B)。', 'ans': '0.28', 'analysis': 'P(A∩B)=P(A)×P(B|A)=0.7×0.4=0.28。'},
            {'content': '袋中 2 红 3 白，有放回取 2 次，两次都是红球的概率？', 'ans': '4/25', 'analysis': '(2/5)×(2/5)=4/25。'},
        ],
    },
}

class LearningService:
    def __init__(
        self,
        mapper: Optional[LearningMapper] = None,
        profile_mapper: Optional[UserProfileMapper] = None,
        raw_generate: Optional[Callable] = None,
    ):
        self._mapper = mapper
        self._profile_mapper = profile_mapper
        # 生成钩子：便于测试注入“模型失败/格式错误”场景
        self._raw_generate = raw_generate

    @property
    def mapper(self) -> LearningMapper:
        if self._mapper is None:
            self._mapper = LearningMapper(
                __import__('backend.model', fromlist=['AsyncSessionLocal']).AsyncSessionLocal
            )
        return self._mapper

    @property
    def profile_mapper(self) -> UserProfileMapper:
        if self._profile_mapper is None:
            self._profile_mapper = UserProfileMapper(
                __import__('backend.model', fromlist=['AsyncSessionLocal']).AsyncSessionLocal
            )
        return self._profile_mapper

    # ==================================================================
    # 8.1 学情诊断
    # ==================================================================

    async def diagnose(self, user_id: int, req: DiagnosisRequest) -> DiagnosisResponse:
        await self._get_and_validate_profile(user_id)

        # 基础输入校验：非空、长度、学习相关
        content = (req.content or '').strip()
        if not content:
            raise BusinessError('INVALID_LEARNING_CONTENT', '学习输入不能为空', 422)
        if len(content) > 2000:
            raise BusinessError('INVALID_LEARNING_CONTENT', '学习输入过长', 422)
        if req.input_type not in ('question', 'learning_question', 'weakness'):
            raise BusinessError('INVALID_LEARNING_CONTENT', 'input_type 非法', 422)

        # 识别知识点
        kp_name = self._identify_knowledge_point(content)
        kp_id = self._kp_id(kp_name)

        # 评估掌握度与薄弱点
        mastery_score, weakness = self._assess(req.input_type, content, kp_name)
        learning_status = self._score_to_status(mastery_score)
        suggestion = self._practice_suggestion(learning_status, kp_name)

        diagnosis = Diagnosis(
            user_id=user_id,
            session_id=req.session_id,
            input_type=req.input_type,
            content=content,
            knowledge_point_id=kp_id,
            knowledge_point_name=kp_name,
            mastery_score=mastery_score,
            learning_status=learning_status,
            weakness=weakness,
            practice_suggestion=suggestion,
        )
        diagnosis = await self.mapper.create_diagnosis(diagnosis)

        return DiagnosisResponse(
            diagnosis_id=diagnosis.id,
            knowledge_point_id=kp_id,
            knowledge_point_name=kp_name,
            mastery_score=mastery_score,
            learning_status=learning_status,
            weakness=weakness,
            practice_suggestion=suggestion,
        )

    # ==================================================================
    # 8.2 创建练习组（含内容校验 + 一次自动重试 + 幂等）
    # ==================================================================

    async def generate_practice(
        self, user_id: int, request_id: str, req: PracticeGenerateRequest
    ) -> PracticeResponse:
        profile = await self._get_and_validate_profile(user_id)
        subject = getattr(profile, 'subject', None)

        if not request_id:
            raise BusinessError('MISSING_REQUEST_ID', '缺少 X-Request-ID 请求头', 400)

        # 幂等：同一 request_id 已生成则直接返回
        existing = await self.mapper.get_practice_by_request_id(user_id, request_id)
        if existing:
            questions = await self.mapper.get_questions(existing.id)
            return self._to_practice_response(existing, questions)

        if not (3 <= req.question_count <= 5):
            raise BusinessError('INVALID_LEARNING_CONTENT', 'question_count 只能为 3~5', 422)

        # 确定知识点与起始难度（user_desc 为诊断原始描述，供 LLM 出题贴合真实困惑）
        kp_name, kp_id, difficulty, user_desc = await self._resolve_target(user_id, req)

        # 生成 + 校验，失败自动重试一次
        raw = await self._generate_and_validate(
            kp_name, difficulty, req.question_count, subject, user_desc
        )
        if raw is None:
            raw = await self._generate_and_validate(
                kp_name, difficulty, req.question_count, subject, user_desc
            )

        if raw is None:
            # 两次均失败：不创建有效练习记录，不扣次数/积分
            raise BusinessError(
                'PRACTICE_GENERATION_FAILED', '练习生成或校验失败，请稍后重试', 500
            )

        # 落库（练习组 + 题目在同一事务）
        practice = Practice(
            user_id=user_id,
            diagnosis_id=req.diagnosis_id,
            knowledge_point_id=kp_id,
            knowledge_point_name=kp_name,
            difficulty=difficulty,
            status='in_progress',
            question_count=len(raw),
            correct_count=0,
            accuracy=0.0,
            is_valid=False,  # 提交后才置为有效
            request_id=request_id,
        )
        questions = [
            Question(
                question_order=i + 1,
                content=q['content'],
                question_type='short_answer',
                difficulty=difficulty,
                knowledge_point_id=kp_id,
                knowledge_point_name=kp_name,
                standard_answer=q['ans'],
                analysis=q['analysis'],
            )
            for i, q in enumerate(raw)
        ]
        practice = await self.mapper.create_practice_with_questions(practice, questions)
        questions = await self.mapper.get_questions(practice.id)

        return self._to_practice_response(practice, questions)

    # ==================================================================
    # 8.3 查询练习组（不返回标准答案）
    # ==================================================================

    async def get_practice(self, user_id: int, practice_id: int) -> PracticeResponse:
        practice = await self.mapper.get_practice(practice_id, user_id)
        if practice is None:
            raise BusinessError('PRACTICE_NOT_FOUND', '练习不存在或不属于当前用户', 404)
        questions = await self.mapper.get_questions(practice_id)
        return self._to_practice_response(practice, questions)

    # ==================================================================
    # 8.4 提交练习答案（判题 + 错因分类 + 难度调整 + 幂等 + 事件）
    # ==================================================================

    async def submit_answers(
        self, user_id: int, practice_id: int, request_id: str, req: AnswerSubmitRequest
    ) -> AnswerSubmitResponse:
        if not request_id:
            raise BusinessError('MISSING_REQUEST_ID', '缺少 X-Request-ID 请求头', 400)

        practice = await self.mapper.get_practice(practice_id, user_id)
        if practice is None:
            raise BusinessError('PRACTICE_NOT_FOUND', '练习不存在或不属于当前用户', 404)

        # 幂等：已提交则拒绝重复提交
        if practice.status == 'completed':
            raise BusinessError('PRACTICE_ALREADY_SUBMITTED', '该练习已提交，请勿重复提交', 409)

        questions = await self.mapper.get_questions(practice_id)
        q_map = {q.id: q for q in questions}
        answer_map = {a.question_id: a.answer for a in req.answers}

        results: List[AnswerResultItem] = []
        correct_count = 0
        # 判题序列（按题目顺序），用于难度调整
        correctness_seq: List[bool] = []

        for q in questions:
            user_answer = (answer_map.get(q.id) or '').strip()
            is_correct = self._judge_answer(user_answer, q.standard_answer)
            error_type = None
            error_description = None
            next_suggestion = None
            if not is_correct:
                error_type, error_description, next_suggestion = self._classify_error(
                    user_answer, q.standard_answer, q.knowledge_point_name
                )
            else:
                correct_count += 1

            correctness_seq.append(is_correct)

            await self.mapper.update_question_analysis(
                q.id, user_answer, is_correct, error_type, error_description, next_suggestion
            )

            results.append(AnswerResultItem(
                question_id=q.id,
                is_correct=is_correct,
                standard_answer=q.standard_answer,
                analysis=q.analysis,
                error_type=error_type,
                error_description=error_description,
                next_suggestion=next_suggestion,
            ))

        total = len(questions)
        accuracy = round(correct_count / max(total, 1) * 100, 2)

        # 更新练习组为已完成、有效
        await self.mapper.update_practice_result(practice_id, correct_count, accuracy)

        # 计算下一次建议难度（连续答对2题升，连续答错2题降）
        next_difficulty = self._adjust_difficulty(practice.difficulty, correctness_seq)

        # 构造并派发业务事件（成员三/四/五消费）
        self._emit_answer_events(practice, q_map, results, request_id, user_id)
        self._emit_practice_completed_event(
            practice, question_count=total, correct_count=correct_count,
            accuracy=accuracy, request_id=request_id, user_id=user_id,
            next_difficulty=next_difficulty,
        )

        return AnswerSubmitResponse(
            practice_id=practice_id,
            status='completed',
            question_count=total,
            correct_count=correct_count,
            accuracy=accuracy,
            results=results,
            current_difficulty=practice.difficulty,
            next_difficulty=next_difficulty,
        )

    # ==================================================================
    # 内部方法：画像与目标
    # ==================================================================

    async def _get_and_validate_profile(self, user_id: int):
        p = await self.profile_mapper.get_by_user_id(user_id)
        if p is None or not p.stage or not p.grade or not p.subject:
            raise BusinessError('PROFILE_NOT_COMPLETED', '请先完善学习信息（学段、年级、学科）', 400)
        return p

    async def _resolve_target(self, user_id: int, req: PracticeGenerateRequest):
        """确定练习针对的知识点与起始难度。

        优先使用关联诊断的知识点与掌握度；否则回退到默认知识点、easy。
        """
        kp_name = '一元一次方程'
        kp_id = self._kp_id(kp_name)
        difficulty = 'easy'
        user_desc: Optional[str] = None

        if req.diagnosis_id:
            diag = await self.mapper.get_diagnosis(req.diagnosis_id, user_id)
            if diag is None:
                raise BusinessError('PRACTICE_NOT_FOUND', '关联诊断不存在或不属于当前用户', 404)
            if diag.knowledge_point_name:
                kp_name = diag.knowledge_point_name
                kp_id = diag.knowledge_point_id or self._kp_id(kp_name)
            # 掌握度决定起始难度：weak→easy, consolidating→medium, mastered→hard
            difficulty = self._status_to_difficulty(diag.learning_status)
            # 原始描述/薄弱点：让 LLM 出题紧扣用户真实困惑（题库命中时不使用，无副作用）
            user_desc = getattr(diag, 'content', None) or getattr(diag, 'weakness', None)

        # 难度衔接（“再练一组”）：优先级 显式指定 > 最近完成练习按正确率推算 > 诊断静态难度
        if req.difficulty in _DIFFICULTY_ORDER:
            difficulty = req.difficulty
        else:
            last = await self.mapper.get_latest_completed_practice(user_id, kp_id)
            if last is not None:
                difficulty = self._next_difficulty_by_accuracy(
                    last.difficulty, last.accuracy or 0.0
                )

        return kp_name, kp_id, difficulty, user_desc

    # ==================================================================
    # 内部方法：知识点识别与掌握度评估
    # ==================================================================

    def _identify_knowledge_point(self, content: str) -> str:
        """从输入文本识别知识点（关键词匹配，未命中给出通用知识点）。"""
        rules = [
            ('概率论', ['概率', '古典概型', '条件概率', '期望', '随机', '抛硬币', '掷骰子', '贝叶斯']),
            ('一元一次方程', ['一元一次', '移项', '一次方程']),
            ('一元二次方程', ['一元二次', '二次方程', '求根', '配方']),
            ('二次函数', ['二次函数', '抛物线', '顶点']),
            ('有理数运算', ['有理数', '正负', '绝对值', '负数']),
            ('分数运算', ['分数', '通分', '约分']),
            ('三角函数', ['sin', 'cos', 'tan', '三角函数', '正弦', '余弦']),
            ('几何证明', ['全等', '相似', '证明', '三角形', '平行']),
        ]
        low = content.lower()
        for kp, keywords in rules:
            for kw in keywords:
                if kw.lower() in low:
                    return kp
        return '综合知识点'

    def _assess(self, input_type: str, content: str, kp_name: str):
        """评估掌握度并给出薄弱点描述。

        - weakness 输入：用户主动反馈薄弱，判为 weak（55）；
        - question / learning_question：默认 consolidating（65），
          若含“不会/不懂/不明白/错”等负面词则降为 weak。
        """
        strong_neg = ['完全不会', '一点不会', '不懂', '不明白', '不理解', '总是错', '老是错', '经常错']
        weak_neg = ['不会', '出错', '错误', '错', '难', '困惑', '搞不清', '容易']
        strong_hits = sum(1 for w in strong_neg if w in content)
        weak_hits = sum(1 for w in weak_neg if w in content)

        if input_type == 'weakness':
            # 主动反馈薄弱：基准 55，负面信号越强分越低（40~60）
            score = 55 - strong_hits * 6 - weak_hits * 2
            score = max(40, min(60, score))
            weakness = f'在「{kp_name}」上存在薄弱环节：{content[:60]}'
        elif strong_hits or weak_hits:
            # 提问但带明显困难信号：偏薄弱（50~62）
            score = 62 - strong_hits * 5 - weak_hits * 2
            score = max(50, min(62, score))
            weakness = f'「{kp_name}」存在理解难点，需针对性练习：{content[:60]}'
        else:
            # 中性提问：基础掌握、待巩固（68~72，随输入长度略浮动）
            score = 68 + min(len(content) // 30, 4)
            score = max(66, min(74, score))
            weakness = f'「{kp_name}」基础掌握，需要巩固练习'
        return score, weakness

    def _practice_suggestion(self, status: str, kp_name: str) -> str:
        if status == 'weak':
            return f'先完成一组简单「{kp_name}」练习，巩固基础后再进阶'
        if status == 'consolidating':
            return f'完成一组中等难度「{kp_name}」练习以稳固掌握'
        return f'可挑战一组困难「{kp_name}」练习检验掌握程度'

    # ==================================================================
    # 内部方法：练习生成与内容质量校验
    # ==================================================================

    async def _generate_and_validate(
        self, kp_name: str, difficulty: str, count: int,
        subject: Optional[str] = None, user_desc: Optional[str] = None
    ) -> Optional[List[dict]]:
        """生成一组题目并做内容质量校验；不通过返回 None（触发重试）。"""
        try:
            raw = await self._raw_generate_questions(
                kp_name, difficulty, count, subject, user_desc
            )
        except Exception:
            # 模型调用失败：视为一次生成失败
            return None

        if not self._validate_content(raw, count):
            return None
        return raw

    async def _raw_generate_questions(
        self, kp_name: str, difficulty: str, count: int,
        subject: Optional[str] = None, user_desc: Optional[str] = None
    ) -> List[dict]:
        """原始题目生成。

        优先级：
        1. self._raw_generate 钩子（测试注入的 mock / LLM，可同步或异步）；
        2. 预置题库（数学高频知识点，答案精确、判分可靠、零延迟）；
        3. 大模型动态出题（题库未覆盖的知识点/科目，支持任意科目）；
        4. 离线兜底（无 LLM 配置时，生成结构完整的算术练习并注明来源）。
        """
        if self._raw_generate is not None:
            res = self._raw_generate(kp_name, difficulty, count)
            if inspect.isawaitable(res):
                res = await res
            return res

        # 预置题库策略：按知识点关键词匹配
        bank = self._match_bank(kp_name)
        if bank:
            pool = bank.get(difficulty) or bank.get('easy') or []
            if len(pool) >= count:
                import random
                selected = random.sample(pool, count)
                return [dict(q) for q in selected]

        # 题库未覆盖 → 交给大模型动态出题（支持任意科目/知识点）
        from backend.services.learning_service.question_generator import (
            generate_questions_via_llm,
            llm_available,
        )
        if llm_available():
            # LLM 调用失败会抛异常 → 由 _generate_and_validate 捕获并重试一次，
            # 两次都失败则 PRACTICE_GENERATION_FAILED（不创建无效练习）。
            return await generate_questions_via_llm(kp_name, difficulty, count, subject, user_desc)

        # 无 LLM 配置（离线/本地开发）→ 结构完整的兜底
        return self._fallback_questions(difficulty, count, kp_name)

    def _match_bank(self, kp_name: str) -> Optional[dict]:
        for key, bank in _PRACTICE_BANK.items():
            if key in kp_name:
                return bank
        return None

    def _fallback_questions(self, difficulty: str, count: int, kp_name: str = '') -> List[dict]:
        import random
        # 题库暂无该知识点时的兜底：题面注明来源，避免"概率论出成方程题"的误导
        tag = f'（{kp_name}·基础巩固）' if kp_name and kp_name != '综合知识点' else ''
        out = []
        seen = set()
        while len(out) < count:
            a = random.randint(2, 9)
            b = random.randint(1, 20)
            c = random.randint(1, 30)
            if difficulty == 'easy':
                x = c
                content = f'{tag}解方程：x + {b} = {c + b}'
                item = {'content': content, 'ans': f'x={x}', 'analysis': f'两边同时减 {b}，得 x={x}。'}
            elif difficulty == 'medium':
                x = c
                content = f'{tag}解方程：{a}x + {b} = {a * x + b}'
                item = {'content': content, 'ans': f'x={x}', 'analysis': f'移项得 {a}x={a * x}，两边除以 {a} 得 x={x}。'}
            else:
                x = c
                content = f'{tag}解方程：{a}(x - {b}) = {a * (x - b)}'
                item = {'content': content, 'ans': f'x={x}', 'analysis': f'去括号并移项，解得 x={x}。'}
            if content in seen:
                continue
            seen.add(content)
            out.append(item)
        return out

    def _validate_content(self, raw, count: int) -> bool:
        """内容质量校验：数量、字段完整、题目不重复。"""
        if not raw or not isinstance(raw, list):
            return False
        if len(raw) != count:
            return False
        seen = set()
        for q in raw:
            if not isinstance(q, dict):
                return False
            content = (q.get('content') or '').strip()
            ans = (q.get('ans') or '').strip()
            analysis = (q.get('analysis') or '').strip()
            # 题目、答案、解析均须齐全
            if not content or not ans or not analysis:
                return False
            # 题目不得重复
            if content in seen:
                return False
            seen.add(content)
        return True

    # ==================================================================
    # 内部方法：判题与错因分类
    # ==================================================================

    def _judge_answer(self, user_answer: str, standard_answer: Optional[str]) -> bool:
        """判题：规范化后比较（去空格、全角转半角、小写、去 x= 前缀）。"""
        if not user_answer or not user_answer.strip():
            return False
        if not standard_answer:
            return True  # 无标准答案的主观题宽松判对
        return self._normalize(user_answer) == self._normalize(standard_answer)

    @staticmethod
    def _normalize(s: str) -> str:
        s = s.strip().lower()
        # 全角转半角
        s = s.replace('＝', '=').replace('，', ',').replace('（', '(').replace('）', ')')
        s = s.replace('±', '+-')
        s = s.replace(' ', '')
        # 去掉 "x=" / "x是" 等前缀，只比较值；同时统一 "或"
        s = s.replace('x=', '').replace('x:', '')
        s = s.replace('或', ',')
        return s

    def _classify_error(self, user_answer: str, standard_answer: Optional[str], kp_name: str):
        """错因分类：knowledge / calculation / reading / method。

        返回 (error_type, error_description, next_suggestion)。
        """
        if not user_answer or not user_answer.strip():
            return (
                _ERROR_KNOWLEDGE,
                '未作答，可能是相关知识点尚未掌握',
                f'先复习「{kp_name}」的基本概念，再完成两道同类题',
            )

        ua = self._normalize(user_answer)
        sa = self._normalize(standard_answer) if standard_answer else ''

        # 提取数值用于判断误差类型
        ua_nums = re.findall(r'-?\d+\.?\d*', ua)
        sa_nums = re.findall(r'-?\d+\.?\d*', sa)

        # 数值个数不一致 → 审题/漏解（reading）
        if sa_nums and len(ua_nums) != len(sa_nums):
            return (
                _ERROR_READING,
                '答案个数与标准答案不一致，可能审题时漏掉了部分解',
                f'重新审读题目条件，注意「{kp_name}」是否存在多个解',
            )

        # 符号相反 → 方法/步骤错误（method，常见于移项忘变号）
        if ua_nums and sa_nums and len(ua_nums) == len(sa_nums):
            try:
                if all(abs(float(a)) == abs(float(b)) for a, b in zip(ua_nums, sa_nums)) and \
                        any(float(a) != float(b) for a, b in zip(ua_nums, sa_nums)):
                    return (
                        _ERROR_METHOD,
                        '数值正确但符号相反，多为移项或运算步骤时符号处理有误',
                        f'重做本题并重点检查「{kp_name}」的符号变化',
                    )
            except ValueError:
                pass

        # 有数值但数值不同 → 计算错误（calculation）
        if ua_nums and sa_nums:
            return (
                _ERROR_CALCULATION,
                '解题方向正确但计算结果有误',
                '放慢计算步骤，完成两道同类题以巩固',
            )

        # 其余：知识点未掌握
        return (
            _ERROR_KNOWLEDGE,
            f'与标准答案差异较大，可能对「{kp_name}」理解不到位',
            f'先复习「{kp_name}」的知识点讲解，再练习',
        )

    # ==================================================================
    # 内部方法：难度调整
    # ==================================================================

    def _adjust_difficulty(self, current: str, correctness_seq: List[bool]) -> str:
        """根据本组表现给出下一组建议难度。

        规则（正确率为主，连对/连错为辅）：
        - 正确率 ≥ 80%（或最后两题连对）→ 升一级；
        - 正确率 ≤ 40%（或最后两题连错）→ 降一级；
        - 其余 → 保持当前难度。
        难度封顶 hard、封底 easy。
        """
        if current not in _DIFFICULTY_ORDER:
            current = 'easy'
        idx = _DIFFICULTY_ORDER.index(current)

        total = len(correctness_seq)
        if total == 0:
            return _DIFFICULTY_ORDER[idx]

        accuracy = sum(1 for c in correctness_seq if c) / total
        last_two_correct = total >= 2 and all(correctness_seq[-2:])
        last_two_wrong = total >= 2 and not any(correctness_seq[-2:])

        if accuracy >= 0.8 or last_two_correct:
            idx = min(idx + 1, len(_DIFFICULTY_ORDER) - 1)
        elif accuracy <= 0.4 or last_two_wrong:
            idx = max(idx - 1, 0)

        return _DIFFICULTY_ORDER[idx]

    def _next_difficulty_by_accuracy(self, current: str, accuracy_pct: float) -> str:
        """依据上一组正确率（百分数 0~100）推算下一组难度，阈值同 _adjust_difficulty。"""
        if current not in _DIFFICULTY_ORDER:
            current = 'easy'
        idx = _DIFFICULTY_ORDER.index(current)
        if accuracy_pct >= 80:
            idx = min(idx + 1, len(_DIFFICULTY_ORDER) - 1)
        elif accuracy_pct <= 40:
            idx = max(idx - 1, 0)
        return _DIFFICULTY_ORDER[idx]

    def _status_to_difficulty(self, status: Optional[str]) -> str:
        return {'weak': 'easy', 'consolidating': 'medium', 'mastered': 'hard'}.get(status or '', 'easy')

    # ==================================================================
    # 内部方法：业务事件（对齐契约 5.4 / 5.5）
    # ==================================================================

    def _emit_answer_events(self, practice, q_map, results, request_id, user_id) -> None:
        """为每道题构造 AnswerResultEvent 交给成员三（掌握度/错题）。

        事件总线尚未接入，这里构造载荷并记录日志，保留对接口点。
        """
        now = datetime.now(_TZ).isoformat()
        for r in results:
            q = q_map.get(r.question_id)
            event = {
                'request_id': request_id,
                'user_id': user_id,
                'practice_id': practice.id,
                'question_id': r.question_id,
                'knowledge_point_id': q.knowledge_point_id if q else None,
                'knowledge_point_name': q.knowledge_point_name if q else None,
                'difficulty': q.difficulty if q else practice.difficulty,
                'is_correct': r.is_correct,
                'error_type': r.error_type,
                'answered_at': now,
            }
            self._publish_event('ANSWER_RESULT', event)

    def _emit_practice_completed_event(
        self, practice, question_count, correct_count, accuracy,
        request_id, user_id, next_difficulty,
    ) -> None:
        """整组完成后构造 PracticeCompletedEvent 交给成员四/五。"""
        event = {
            'request_id': request_id,
            'user_id': user_id,
            'practice_id': practice.id,
            'subject': None,  # 由消费方结合画像补全
            'knowledge_point_id': practice.knowledge_point_id,
            'question_count': question_count,
            'correct_count': correct_count,
            'accuracy': accuracy,
            'is_valid': True,
            'next_difficulty': next_difficulty,
            'completed_at': datetime.now(_TZ).isoformat(),
        }
        self._publish_event('PRACTICE_COMPLETED', event)

    def _publish_event(self, topic: str, payload: dict) -> None:
        """事件发布占位：事件总线接入后替换为真实发布。"""
        import logging
        logging.getLogger('learning.events').info('[%s] %s', topic, payload)

    # ==================================================================
    # 内部方法：转换与工具
    # ==================================================================

    def _to_practice_response(self, practice, questions) -> PracticeResponse:
        return PracticeResponse(
            practice_id=practice.id,
            knowledge_point_id=practice.knowledge_point_id,
            knowledge_point_name=practice.knowledge_point_name,
            difficulty=practice.difficulty,
            status=practice.status,
            questions=[
                QuestionItem(
                    question_id=q.id,
                    content=q.content,
                    question_type=q.question_type,
                    difficulty=q.difficulty,
                    knowledge_point_id=q.knowledge_point_id,
                    knowledge_point_name=q.knowledge_point_name,
                )
                for q in questions
            ],
        )

    @staticmethod
    def _kp_id(kp_name: str) -> int:
        return abs(hash(kp_name)) % 10000

    @staticmethod
    def _score_to_status(score: int) -> str:
        if score >= 81:
            return 'mastered'
        if score >= 60:
            return 'consolidating'
        return 'weak'


# 单例
_learning_service: Optional[LearningService] = None


async def get_learning_service() -> LearningService:
    global _learning_service
    if _learning_service is None:
        _learning_service = LearningService()
    return _learning_service









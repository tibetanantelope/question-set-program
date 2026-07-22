"""成员一：首次诊断 Service —— 生成诊断题、判题、初始化掌握度、跳过诊断。"""

import random
from datetime import datetime
from typing import List, Optional

from backend.core.exceptions import BusinessError
from backend.dao.diagnostic_mapper import DiagnosticMapper, get_diagnostic_mapper
from backend.dao.user_profile_mapper import UserProfileMapper, get_user_profile_mapper
from backend.model.diagnostic import DiagnosticSession, DiagnosticAnswer
from backend.schemas.response.diagnostic_response import (
    DiagnosticStatusResponse,
    DiagnosticStartResponse,
    DiagnosticSubmitResponse,
    MasteryItem,
    QuestionItem,
)
from backend.schemas.request.diagnostic_request import DiagnosticSubmitRequest, DiagnosticAnswerItem

# ───────────────────────────────────────────────
# 预置诊断题（按学段和年级，用作 LLM 失败时的后备）
# ───────────────────────────────────────────────

_DIAGNOSTIC_QUESTIONS: dict = {
    'primary': {
        '三年级': [
            {'content': '计算：25 + 37 = ?', 'knowledge_point_name': '两位数加法', 'knowledge_point_id': 1},
            {'content': '计算：72 - 45 = ?', 'knowledge_point_name': '两位数减法', 'knowledge_point_id': 2},
            {'content': '计算：6 × 8 = ?', 'knowledge_point_name': '一位数乘法', 'knowledge_point_id': 3},
            {'content': '计算：56 ÷ 7 = ?', 'knowledge_point_name': '一位数除法', 'knowledge_point_id': 4},
            {'content': '填空题：1米 = ____ 厘米', 'knowledge_point_name': '长度单位换算', 'knowledge_point_id': 5},
        ],
    },
    'junior': {
        '七年级': [
            {'content': '解方程：x + 3 = 7', 'knowledge_point_name': '一元一次方程', 'knowledge_point_id': 101},
            {'content': '解方程：3x - 5 = 10', 'knowledge_point_name': '一元一次方程-移项', 'knowledge_point_id': 102},
            {'content': '计算：(-3) + 8 - 5 = ?', 'knowledge_point_name': '有理数运算', 'knowledge_point_id': 103},
            {'content': '化简：2(3x - 1) - (x + 4)', 'knowledge_point_name': '整式的加减', 'knowledge_point_id': 104},
            {'content': '解方程：2(x - 1) = x + 3', 'knowledge_point_name': '一元一次方程-去括号', 'knowledge_point_id': 105},
        ],
    },
    'senior': {
        '高一': [
            {'content': '若集合 A = {1, 2, 3}, B = {2, 3, 4}，求 A ∩ B', 'knowledge_point_name': '集合运算', 'knowledge_point_id': 201},
            {'content': '解不等式：|x - 2| ≤ 3', 'knowledge_point_name': '绝对值不等式', 'knowledge_point_id': 202},
            {'content': '计算：f(3) = 2×3² - 3×3 + 1', 'knowledge_point_name': '二次函数求值', 'knowledge_point_id': 203},
            {'content': '已知 sin α = 3/5，cos α = ?（锐角）', 'knowledge_point_name': '三角函数', 'knowledge_point_id': 204},
            {'content': '求直线 y = 2x + 1 的斜率', 'knowledge_point_name': '直线方程', 'knowledge_point_id': 205},
        ],
    },
    'university': {
        '大一': [
            {'content': '求极限 lim(x→0) sin(x)/x = ?', 'knowledge_point_name': '函数极限', 'knowledge_point_id': 301},
            {'content': '求导数：f(x) = x²eˣ', 'knowledge_point_name': '导数计算', 'knowledge_point_id': 302},
            {'content': '求不定积分 ∫(2x + 1)dx', 'knowledge_point_name': '不定积分', 'knowledge_point_id': 303},
            {'content': '矩阵 A = [[1,2],[3,4]]，求 det(A)', 'knowledge_point_name': '行列式计算', 'knowledge_point_id': 304},
            {'content': '判断敛散性：∑(1/n²) (n=1 to ∞)', 'knowledge_point_name': '级数判别', 'knowledge_point_id': 305},
        ],
    },
}

# 默认年级（当具体年级不在预置库时回退）
_DEFAULT_GRADE = {
    'primary': '三年级',
    'junior': '七年级',
    'senior': '高一',
    'university': '大一',
}

DIAGNOSTIC_QUESTION_COUNT = 5


class DiagnosticService:
    def __init__(self, mapper: Optional[DiagnosticMapper] = None, profile_mapper: Optional[UserProfileMapper] = None):
        self._mapper = mapper
        self._profile_mapper = profile_mapper

    @property
    def mapper(self) -> DiagnosticMapper:
        if self._mapper is None:
            self._mapper = DiagnosticMapper(
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

    # ------------------------------------------------------------------
    # 查询诊断状态
    # ------------------------------------------------------------------

    async def get_status(self, user_id: int) -> DiagnosticStatusResponse:
        p = await self.profile_mapper.get_by_user_id(user_id)
        if p is None or p.diagnostic_status == 'required':
            return DiagnosticStatusResponse(status='required')

        if p.diagnostic_status == 'in_progress':
            session = await self.mapper.get_latest_in_progress(user_id)
            return DiagnosticStatusResponse(status='in_progress', diagnostic_id=session.id if session else None)

        return DiagnosticStatusResponse(status=p.diagnostic_status)

    # ------------------------------------------------------------------
    # 开始诊断
    # ------------------------------------------------------------------

    async def start_diagnostic(self, user_id: int) -> DiagnosticStartResponse:
        p = await self._get_and_validate_profile(user_id)

        if p.diagnostic_status == 'completed':
            raise BusinessError('DIAGNOSTIC_ALREADY_COMPLETED', '已完成首次诊断，无需再次诊断', 409)

        # 如果已有进行中的诊断，直接返回
        existing = await self.mapper.get_latest_in_progress(user_id)
        if existing:
            answers = await self.mapper.get_answers(existing.id)
            if answers:
                return DiagnosticStartResponse(
                    diagnostic_id=existing.id,
                    question_count=existing.question_count,
                    questions=[self._answer_to_question(a) for a in answers],
                )

        # 生成诊断题
        questions = self._generate_questions(p.stage, p.grade)
        session = await self.mapper.create_session(user_id, len(questions))

        # 持久化题目
        answers = [
            DiagnosticAnswer(
                diagnostic_id=session.id,
                question_id=q['question_id'],
                content=q['content'],
                question_type=q.get('question_type', 'short_answer'),
                difficulty=q.get('difficulty', 'easy'),
                knowledge_point_id=q.get('knowledge_point_id'),
                knowledge_point_name=q.get('knowledge_point_name'),
            )
            for q in questions
        ]
        await self.mapper.save_answers(session.id, answers)

        # 标记画像诊断状态
        await self.profile_mapper.update(user_id, diagnostic_status='in_progress')

        return DiagnosticStartResponse(
            diagnostic_id=session.id,
            question_count=len(questions),
            questions=[self._question_to_item(q) for q in questions],
        )

    # ------------------------------------------------------------------
    # 提交诊断
    # ------------------------------------------------------------------

    async def submit_diagnostic(self, user_id: int, req: DiagnosticSubmitRequest) -> DiagnosticSubmitResponse:
        p = await self._get_and_validate_profile(user_id)

        session = await self.mapper.get_session(req.diagnostic_id, user_id)
        if session is None:
            raise BusinessError('DIAGNOSTIC_NOT_FOUND', '诊断会话不存在', 404)

        if session.status != 'in_progress':
            raise BusinessError('DIAGNOSTIC_ALREADY_COMPLETED', '该诊断已完成或已跳过', 409)

        stored_answers = await self.mapper.get_answers(session.id)
        stored_map = {a.question_id: a for a in stored_answers}

        # 逐一判题（简单规则 + 可选的 LLM 判题）
        masteries: dict = {}
        for item in req.answers:
            stored = stored_map.get(item.question_id)
            if stored is None:
                continue
            correct = self._judge_answer(item.answer, stored.content)
            await self.mapper.update_answer(stored.id, item.answer, correct)

            kp_name = stored.knowledge_point_name or '未知知识点'
            kp_id = stored.knowledge_point_id or 0
            if kp_name not in masteries:
                score = 60 + (10 if correct else -5)
                masteries[kp_name] = {
                    'knowledge_point_id': kp_id,
                    'knowledge_point_name': kp_name,
                    'mastery_score': max(0, min(100, score)),
                }

        # 标记诊断完成
        await self.mapper.update_session_status(session.id, 'completed')
        await self.profile_mapper.update(user_id, diagnostic_status='completed')

        mastery_list = [
            MasteryItem(
                knowledge_point_id=m['knowledge_point_id'],
                knowledge_point_name=m['knowledge_point_name'],
                mastery_score=m['mastery_score'],
                learning_status=self._score_to_status(m['mastery_score']),
            )
            for m in masteries.values()
        ]

        return DiagnosticSubmitResponse(status='completed', masteries=mastery_list)

    # ------------------------------------------------------------------
    # 跳过诊断
    # ------------------------------------------------------------------

    async def skip_diagnostic(self, user_id: int) -> DiagnosticSubmitResponse:
        p = await self._get_and_validate_profile(user_id)

        if p.diagnostic_status == 'completed':
            raise BusinessError('DIAGNOSTIC_ALREADY_COMPLETED', '已完成首次诊断，无需跳过', 409)

        session = await self.mapper.get_latest_in_progress(user_id)
        if session:
            await self.mapper.update_session_status(session.id, 'skipped')

        await self.profile_mapper.update(user_id, diagnostic_status='skipped')

        return DiagnosticSubmitResponse(status='skipped', masteries=[])

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    async def _get_and_validate_profile(self, user_id: int):
        p = await self.profile_mapper.get_by_user_id(user_id)
        if p is None or not p.stage or not p.grade or not p.subject:
            raise BusinessError('PROFILE_NOT_COMPLETED', '请先完善学习信息（学段、年级、学科）', 400)
        return p

    def _generate_questions(self, stage: str, grade: str) -> List[dict]:
        """从预置题库选取诊断题。后续可接入 LLM 生成。"""
        stage_questions = _DIAGNOSTIC_QUESTIONS.get(stage, {})
        grade_questions = stage_questions.get(grade) or stage_questions.get(_DEFAULT_GRADE.get(stage, list(stage_questions.values())[0] if stage_questions else []))

        if not grade_questions:
            # 回退：用初中七年级
            grade_questions = _DIAGNOSTIC_QUESTIONS.get('junior', {}).get('七年级', [])

        selected = grade_questions[:DIAGNOSTIC_QUESTION_COUNT]
        return [
            {
                'question_id': i + 1,
                'content': q['content'],
                'question_type': 'short_answer',
                'difficulty': 'easy',
                'knowledge_point_id': q.get('knowledge_point_id'),
                'knowledge_point_name': q.get('knowledge_point_name'),
            }
            for i, q in enumerate(selected)
        ]

    def _judge_answer(self, user_answer: str, correct_content: str) -> bool:
        """简单判题：去除空格后模糊比较。后续可接入 LLM 判题。"""
        ua = user_answer.strip().replace(' ', '').lower()
        # 尝试提取题目中的标准答案
        correct = self._extract_expected(correct_content)
        return ua == correct

    def _extract_expected(self, content: str) -> str:
        """从题目中提取期望答案（简化版）。"""
        # 尝试匹配 "= ?" 模式
        import re
        # 对于常见中小学题目，使用关键词提取
        m = re.search(r'[=＝]\s*(\S+)', content)
        if m:
            return m.group(1).strip().replace(' ', '').replace('?', '').replace('？', '').lower()
        return ''

    def _question_to_item(self, q: dict) -> QuestionItem:
        return QuestionItem(
            question_id=q['question_id'],
            content=q['content'],
            question_type=q.get('question_type', 'short_answer'),
            difficulty=q.get('difficulty', 'easy'),
            knowledge_point_id=q.get('knowledge_point_id'),
            knowledge_point_name=q.get('knowledge_point_name'),
        )

    def _answer_to_question(self, a) -> QuestionItem:
        return QuestionItem(
            question_id=a.question_id,
            content=a.content,
            question_type=a.question_type,
            difficulty=a.difficulty,
            knowledge_point_id=a.knowledge_point_id,
            knowledge_point_name=a.knowledge_point_name,
        )

    @staticmethod
    def _score_to_status(score: int) -> str:
        if score >= 81:
            return 'mastered'
        if score >= 60:
            return 'consolidating'
        return 'weak'


# 单例
_diagnostic_service: Optional[DiagnosticService] = None


async def get_diagnostic_service() -> DiagnosticService:
    global _diagnostic_service
    if _diagnostic_service is None:
        _diagnostic_service = DiagnosticService()
    return _diagnostic_service

"""成员二：智能诊断与练习生成 Service 单元测试。

覆盖验收要点（对齐《五人任务分工》第 4 节 / 《业务设计》第 5 节）：
- 正常流程：诊断 → 生成练习 → 提交答题（判题、正确率、错因、难度调整）；
- 模型失败：两次生成均失败时返回 PRACTICE_GENERATION_FAILED，不创建有效练习；
- 格式错误：模型返回内容不完整/重复时校验不通过，自动重试一次；
- 重复提交：同一练习二次提交返回 PRACTICE_ALREADY_SUBMITTED；
- 幂等生成：同一 X-Request-ID 重复创建练习返回同一条记录。

使用内存 SQLite + 注入的假画像 Mapper，无需 MySQL。
"""

import json
import os

# 让 backend.model 能在无 MySQL 环境下导入
os.environ.setdefault("SQL_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.core.exceptions import BusinessError
from backend.model import Base
from backend.model.learning import LearningSession, Diagnosis, Practice, Question
from backend.dao.learning_mapper import LearningMapper
from backend.services.learning_service.learning_service import LearningService
from backend.services.learning_service.question_generator import arithmetic_explanations_are_consistent


def test_arithmetic_explanation_consistency_rejects_false_step():
    assert not arithmetic_explanations_are_consistent(
        "先算6+3=9，再算9×8=72，最后72−5=64。"
    )


def test_arithmetic_explanation_consistency_accepts_correct_steps():
    assert arithmetic_explanations_are_consistent(
        "先算6+3=9，再算9×8=72，最后72−5=67。"
    )
from backend.schemas.request.learning_request import (
    DiagnosisRequest,
    PracticeGenerateRequest,
    AnswerItem,
    AnswerSubmitRequest,
)

USER_ID = 1
_DIFFICULTY_RANK = {"easy": 0, "medium": 1, "hard": 2}


class _FakeProfile:
    stage = "junior"
    grade = "七年级"
    subject = "数学"


class _FakeProfileMapper:
    """画像永远返回一个已完善的画像。"""
    async def get_by_user_id(self, user_id: int):
        return _FakeProfile()


# ── Fixtures ──────────────────────────────────────────────

@pytest_asyncio.fixture
async def service():
    """基于内存 SQLite 的 LearningService（默认预置题库生成）。"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[
                LearningSession.__table__,
                Diagnosis.__table__,
                Practice.__table__,
                Question.__table__,
            ],
        )
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    mapper = LearningMapper(factory)
    svc = LearningService(mapper=mapper, profile_mapper=_FakeProfileMapper())
    yield svc
    await engine.dispose()


def _make_service_with_generator(engine_service, raw_generate):
    """复用已建表的 mapper，替换生成钩子。"""
    svc = LearningService(
        mapper=engine_service.mapper,
        profile_mapper=_FakeProfileMapper(),
        raw_generate=raw_generate,
    )
    return svc


# ── 1. 正常流程 ────────────────────────────────────────────

class TestNormalFlow:
    async def test_diagnose_identifies_kp(self, service: LearningService):
        req = DiagnosisRequest(
            input_type="weakness",
            content="我做一元一次方程时经常在移项处出错",
        )
        resp = await service.diagnose(USER_ID, req)
        assert resp.diagnosis_id > 0
        assert resp.knowledge_point_name == "一元一次方程"
        assert resp.learning_status == "weak"  # weakness 输入判为薄弱
        # 掌握度按负面信号动态评分，落在薄弱区间（40~60），不再固定为常数
        assert 40 <= resp.mastery_score <= 60
        assert resp.weakness
        assert resp.practice_suggestion

    async def test_generate_practice_then_submit(self, service: LearningService):
        # 生成练习
        gen = await service.generate_practice(
            USER_ID, "req-normal-1",
            PracticeGenerateRequest(question_count=3),
        )
        assert gen.practice_id > 0
        assert gen.status == "in_progress"
        assert len(gen.questions) == 3
        # 查询接口不得返回标准答案
        for q in gen.questions:
            assert not hasattr(q, "standard_answer") or getattr(q, "standard_answer", None) is None

        # 全部答对（用标准答案作答）
        practice = await service.mapper.get_practice(gen.practice_id, USER_ID)
        questions = await service.mapper.get_questions(gen.practice_id)
        answers = [
            AnswerItem(question_id=q.id, answer=q.standard_answer)
            for q in questions
        ]
        submit = await service.submit_answers(
            USER_ID, gen.practice_id, "req-submit-1",
            AnswerSubmitRequest(answers=answers),
        )
        assert submit.status == "completed"
        assert submit.question_count == 3
        assert submit.correct_count == 3
        assert submit.accuracy == 100.0
        assert len(submit.results) == 3
        # 提交后结果含标准答案与解析
        for r in submit.results:
            assert r.is_correct is True
            assert r.standard_answer
            assert r.analysis

    async def test_submit_wrong_answers_classifies_error(self, service: LearningService):
        gen = await service.generate_practice(
            USER_ID, "req-normal-2",
            PracticeGenerateRequest(question_count=3),
        )
        questions = await service.mapper.get_questions(gen.practice_id)
        # 全部空答 → knowledge 错因
        answers = [AnswerItem(question_id=q.id, answer="") for q in questions]
        submit = await service.submit_answers(
            USER_ID, gen.practice_id, "req-submit-2",
            AnswerSubmitRequest(answers=answers),
        )
        assert submit.correct_count == 0
        assert submit.accuracy == 0.0
        for r in submit.results:
            assert r.is_correct is False
            assert r.error_type == "knowledge"
            assert r.error_description
            assert r.next_suggestion

    async def test_get_practice_hides_standard_answer(self, service: LearningService):
        gen = await service.generate_practice(
            USER_ID, "req-normal-3",
            PracticeGenerateRequest(question_count=3),
        )
        got = await service.get_practice(USER_ID, gen.practice_id)
        assert got.practice_id == gen.practice_id
        assert len(got.questions) == 3
        dumped = got.model_dump()
        for q in dumped["questions"]:
            assert "standard_answer" not in q
            assert "analysis" not in q


# ── 2. 难度调整 ────────────────────────────────────────────

class TestDifficultyAdjustment:
    def test_two_correct_raises(self, service: LearningService):
        assert service._adjust_difficulty("easy", [True, True]) == "medium"
        assert service._adjust_difficulty("medium", [False, True, True]) == "hard"
        assert service._adjust_difficulty("hard", [True, True]) == "hard"  # 封顶

    def test_two_wrong_lowers(self, service: LearningService):
        assert service._adjust_difficulty("hard", [False, False]) == "medium"
        assert service._adjust_difficulty("medium", [True, False, False]) == "easy"
        assert service._adjust_difficulty("easy", [False, False]) == "easy"  # 封底

    def test_mixed_keeps(self, service: LearningService):
        assert service._adjust_difficulty("medium", [True, False]) == "medium"
        assert service._adjust_difficulty("medium", [False, True]) == "medium"

    def test_accuracy_threshold_drives_difficulty(self, service: LearningService):
        # 正确率 ≥80% 升级；≤40% 降级；中间保持
        assert service._adjust_difficulty("easy", [True, True, True]) == "medium"
        assert service._adjust_difficulty("medium", [False, False, True]) == "easy"
        assert service._adjust_difficulty("medium", [False, True, True]) == "hard"  # 末尾连对即使总正确率未达标也升级
        assert service._next_difficulty_by_accuracy("easy", 100.0) == "medium"
        assert service._next_difficulty_by_accuracy("medium", 33.3) == "easy"
        assert service._next_difficulty_by_accuracy("medium", 60.0) == "medium"

    async def test_submit_returns_next_difficulty(self, service: LearningService):
        gen = await service.generate_practice(
            USER_ID, "req-nextdiff",
            PracticeGenerateRequest(question_count=3),
        )
        questions = await service.mapper.get_questions(gen.practice_id)
        # 全答对 → 应升难度
        answers = [AnswerItem(question_id=q.id, answer=q.standard_answer) for q in questions]
        resp = await service.submit_answers(
            USER_ID, gen.practice_id, "req-nextdiff-sub",
            AnswerSubmitRequest(answers=answers),
        )
        assert resp.current_difficulty == gen.difficulty
        assert resp.accuracy == 100.0
        assert _DIFFICULTY_RANK[resp.next_difficulty] >= _DIFFICULTY_RANK[gen.difficulty]


class TestKnowledgePointCoverage:
    async def test_ambiguous_input_uses_random_scope_not_generic_label(
        self, service: LearningService, monkeypatch
    ):
        monkeypatch.setenv("LLM_PRACTICE_ENABLED", "false")
        diag = await service.diagnose(
            USER_ID,
            DiagnosisRequest(input_type="weakness", content="我不知道练什么，随便出几道题"),
        )
        assert diag.knowledge_point_name == "七年级数学随机巩固"
        assert diag.knowledge_point_name != "综合知识点"

    async def test_generated_questions_keep_concrete_knowledge_points(
        self, service: LearningService
    ):
        raw = [
            {
                "content": "题目A",
                "knowledge_point_name": "有理数加法",
                "ans": "1",
                "analysis": "解析A",
            },
            {
                "content": "题目B",
                "knowledge_point_name": "绝对值",
                "ans": "2",
                "analysis": "解析B",
            },
            {
                "content": "题目C",
                "knowledge_point_name": "数轴",
                "ans": "3",
                "analysis": "解析C",
            },
        ]
        svc = _make_service_with_generator(service, lambda kp, diff, count: raw)
        diag = await svc.diagnose(
            USER_ID,
            DiagnosisRequest(input_type="weakness", content="我不知道练什么，随便出几道题"),
        )
        generated = await svc.generate_practice(
            USER_ID,
            "req-concrete-kps",
            PracticeGenerateRequest(diagnosis_id=diag.diagnosis_id, question_count=3),
        )
        assert generated.knowledge_point_name == "数学多知识点练习"
        assert [item.knowledge_point_name for item in generated.questions] == [
            "有理数加法", "绝对值", "数轴"
        ]

    async def test_probability_uses_probability_bank(self, service: LearningService):
        # 概率论应被识别，且出题来自概率题库（题面含概率相关词，不再是方程）
        diag = await service.diagnose(
            USER_ID, DiagnosisRequest(input_type="weakness", content="我概率论的计算题总是算错")
        )
        assert diag.knowledge_point_name == "概率论"
        gen = await service.generate_practice(
            USER_ID, "req-prob-1",
            PracticeGenerateRequest(diagnosis_id=diag.diagnosis_id, question_count=3),
        )
        assert gen.knowledge_point_name == "概率论"
        blob = "".join(q.content for q in gen.questions)
        assert any(kw in blob for kw in ["概率", "骰子", "硬币", "球", "P("])
        assert "解方程" not in blob


# ── 3. 模型失败 ────────────────────────────────────────────

class TestGenerationFailure:
    async def test_model_always_fails(self, service: LearningService):
        def boom(kp, diff, count):
            raise RuntimeError("模型调用超时")

        svc = _make_service_with_generator(service, boom)
        with pytest.raises(BusinessError) as ei:
            await svc.generate_practice(
                USER_ID, "req-fail-1",
                PracticeGenerateRequest(question_count=3),
            )
        assert ei.value.code == "PRACTICE_GENERATION_FAILED"
        assert ei.value.status_code == 500
        # 未创建有效练习记录
        existing = await service.mapper.get_practice_by_request_id(USER_ID, "req-fail-1")
        assert existing is None


# ── 4. 格式错误 + 自动重试 ─────────────────────────────────

class TestContentValidation:
    async def test_format_error_then_retry_succeeds(self, service: LearningService):
        calls = {"n": 0}

        def flaky(kp, diff, count):
            calls["n"] += 1
            if calls["n"] == 1:
                # 第一次：缺少解析字段（格式错误）→ 校验失败
                return [{"content": f"题{i}", "ans": "1"} for i in range(count)]
            # 第二次：完整
            return [
                {"content": f"题{i}", "ans": str(i), "analysis": f"解析{i}"}
                for i in range(count)
            ]

        svc = _make_service_with_generator(service, flaky)
        gen = await svc.generate_practice(
            USER_ID, "req-retry-1",
            PracticeGenerateRequest(question_count=3),
        )
        assert calls["n"] == 2  # 触发了一次自动重试
        assert len(gen.questions) == 3

    async def test_duplicate_questions_rejected(self, service: LearningService):
        def dup(kp, diff, count):
            # 所有题目内容相同 → 重复，校验不通过
            return [{"content": "同一道题", "ans": "1", "analysis": "解析"} for _ in range(count)]

        svc = _make_service_with_generator(service, dup)
        with pytest.raises(BusinessError) as ei:
            await svc.generate_practice(
                USER_ID, "req-dup-1",
                PracticeGenerateRequest(question_count=3),
            )
        assert ei.value.code == "PRACTICE_GENERATION_FAILED"


# ── 5. 幂等与重复提交 ──────────────────────────────────────

class TestIdempotency:
    async def test_generate_idempotent(self, service: LearningService):
        r1 = await service.generate_practice(
            USER_ID, "req-idem-1", PracticeGenerateRequest(question_count=3)
        )
        r2 = await service.generate_practice(
            USER_ID, "req-idem-1", PracticeGenerateRequest(question_count=3)
        )
        assert r1.practice_id == r2.practice_id

    async def test_duplicate_submit_rejected(self, service: LearningService):
        gen = await service.generate_practice(
            USER_ID, "req-idem-2", PracticeGenerateRequest(question_count=3)
        )
        questions = await service.mapper.get_questions(gen.practice_id)
        answers = [AnswerItem(question_id=q.id, answer=q.standard_answer) for q in questions]
        await service.submit_answers(
            USER_ID, gen.practice_id, "req-sub-idem",
            AnswerSubmitRequest(answers=answers),
        )
        # 二次提交
        with pytest.raises(BusinessError) as ei:
            await service.submit_answers(
                USER_ID, gen.practice_id, "req-sub-idem-2",
                AnswerSubmitRequest(answers=answers),
            )
        assert ei.value.code == "PRACTICE_ALREADY_SUBMITTED"
        assert ei.value.status_code == 409

    async def test_same_submit_request_can_retry_for_downstream_compensation(
        self, service: LearningService
    ):
        gen = await service.generate_practice(
            USER_ID, "req-idem-retry", PracticeGenerateRequest(question_count=3)
        )
        questions = await service.mapper.get_questions(gen.practice_id)
        answers = [AnswerItem(question_id=q.id, answer=q.standard_answer) for q in questions]
        request = AnswerSubmitRequest(answers=answers)

        first = await service.submit_answers(
            USER_ID, gen.practice_id, "req-sub-retry", request
        )
        retried = await service.submit_answers(
            USER_ID, gen.practice_id, "req-sub-retry", request
        )

        assert retried.model_dump() == first.model_dump()


# ── 6. 画像未完善 ──────────────────────────────────────────

class TestProfileGuard:
    async def test_profile_not_completed(self, service: LearningService):
        class _EmptyProfileMapper:
            async def get_by_user_id(self, user_id: int):
                return None

        svc = LearningService(mapper=service.mapper, profile_mapper=_EmptyProfileMapper())
        with pytest.raises(BusinessError) as ei:
            await svc.diagnose(USER_ID, DiagnosisRequest(input_type="weakness", content="x"))
        assert ei.value.code == "PROFILE_NOT_COMPLETED"


# ===========================================================================
# LLM 题目解析器（纯函数，无网络依赖）
# ===========================================================================
from backend.services.learning_service.question_generator import parse_llm_questions


class TestParseLlmQuestions:
    """parse_llm_questions 是纯函数，无需 event loop 或数据库 fixture。"""

    def test_clean_json_array(self):
        text = '[{"content":"1+1=?","ans":"2","analysis":"加法"}]'
        result = parse_llm_questions(text)
        assert len(result) == 1
        assert result[0] == {
            "content": "1+1=?",
            "ans": "2",
            "analysis": "加法",
            "answer_type": "short_text",
            "grading_spec": {},
        }

    def test_strips_markdown_fence(self):
        text = '```json\n[{"content":"Q","ans":"A","analysis":"E"}]\n```'
        result = parse_llm_questions(text)
        assert result[0]["ans"] == "A"

    def test_strips_fence_no_lang(self):
        text = '```\n[{"content":"Q","ans":"A","analysis":"E"}]\n```'
        result = parse_llm_questions(text)
        assert result[0]["content"] == "Q"

    def test_extra_text_before_and_after(self):
        text = '以下是题目：\n[{"content":"Q","ans":"A","analysis":"E"}]\n好了。'
        result = parse_llm_questions(text)
        assert result[0]["ans"] == "A"

    def test_multiple_questions(self):
        items = [
            {"content": f"题{i}", "ans": str(i), "analysis": f"解析{i}"}
            for i in range(1, 4)
        ]
        text = json.dumps(items, ensure_ascii=False)
        result = parse_llm_questions(text)
        assert len(result) == 3
        assert result[2]["ans"] == "3"

    def test_alternative_field_names(self):
        """LLM 有时输出 answer / question 而非 ans / content，也要容忍。"""
        text = '[{"question":"Q?","answer":"42","explanation":"因为答案是42"}]'
        result = parse_llm_questions(text)
        assert result[0]["ans"] == "42"
        assert result[0]["analysis"] == "因为答案是42"


class TestLlmPracticeGeneration:
    async def test_configured_llm_is_preferred_over_question_bank(self, monkeypatch):
        import backend.services.learning_service.question_generator as generator

        async def fake_generate(kp_name, difficulty, count, subject, user_desc):
            assert (kp_name, subject, user_desc) == ("一元一次方程", "数学", "移项容易出错")
            return [
                {"content": f"LLM题{i}", "ans": str(i), "analysis": "个性化解析"}
                for i in range(count)
            ]

        monkeypatch.setattr(generator, "llm_available", lambda: True)
        monkeypatch.setattr(generator, "generate_questions_via_llm", fake_generate)
        result = await LearningService()._raw_generate_questions(
            "一元一次方程", "easy", 3, "数学", "移项容易出错"
        )
        assert [item["content"] for item in result] == ["LLM题0", "LLM题1", "LLM题2"]

    async def test_llm_failure_falls_back_to_question_bank(self, monkeypatch):
        import backend.services.learning_service.question_generator as generator

        async def failed_generate(*_args):
            raise RuntimeError("provider unavailable")

        monkeypatch.setattr(generator, "llm_available", lambda: True)
        monkeypatch.setattr(generator, "generate_questions_via_llm", failed_generate)
        result = await LearningService()._raw_generate_questions(
            "一元一次方程", "easy", 3, "数学", None
        )
        assert len(result) == 3
        assert all(item["content"] and item["ans"] and item["analysis"] for item in result)


class TestHybridAnswerJudging:
    def test_single_numeric_answer_accepts_unit_and_explanation(self):
        service = LearningService()
        assert service._judge_answer("19元", "19") is True
        assert service._judge_answer("答案是 19.0 元", "19") is True

    def test_relationship_answer_is_not_decided_by_numeric_extraction(self):
        service = LearningService()
        assert service._judge_answer("结果比系统价格高4.5元", "低5.6元") is False

    async def test_semantic_ai_grade_can_accept_equivalent_expression(
        self, service: LearningService, monkeypatch
    ):
        generated = await service.generate_practice(
            USER_ID,
            "req-semantic-judge",
            PracticeGenerateRequest(question_count=3),
        )
        questions = await service.mapper.get_questions(generated.practice_id)

        async def fake_judge(items, *, review=False):
            return {
                item["question_id"]: {
                    "verdict": "correct",
                    "confidence": 0.96,
                    "reason": "表达不同但含义等价",
                    "error_type": None,
                    "suggestion": "",
                }
                for item in items
            }

        monkeypatch.setattr(
            "backend.services.learning_service.learning_service.judge_answers_via_llm",
            fake_judge,
        )
        answers = [
            AnswerItem(question_id=q.id, answer=f"用文字表达的等价答案 {index}")
            for index, q in enumerate(questions, 1)
        ]
        result = await service.submit_answers(
            USER_ID,
            generated.practice_id,
            "req-semantic-submit",
            AnswerSubmitRequest(answers=answers),
        )
        assert result.correct_count == 3
        assert all(item.is_correct for item in result.results)

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            parse_llm_questions("")

    def test_no_array_raises(self):
        with pytest.raises(ValueError):
            parse_llm_questions('{"content":"Q","ans":"A","analysis":"E"}')

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError):
            parse_llm_questions("[not valid json]")

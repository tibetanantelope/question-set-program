<template>
  <div v-if="!isAuthed" class="auth-page">
    <section class="auth-showcase">
      <div class="auth-brand"><span class="brand-mark">智</span><strong>智学伴</strong></div>
      <div class="showcase-copy">
        <span class="eyebrow light">AI PERSONAL LEARNING</span>
        <h1>让每一次练习，<br>都更接近真正掌握</h1>
        <p>从薄弱点诊断到针对性训练，智学伴陪你形成自己的学习节奏。</p>
        <div class="showcase-points">
          <span>✓ 个性化学情诊断</span><span>✓ 智能生成专项练习</span><span>✓ 错题订正与定期复习</span>
        </div>
      </div>
      <div class="float-score"><small>本周掌握度</small><strong>+12%</strong><span>保持得很好</span></div>
      <p class="auth-foot">面向小学、初中、高中和大学阶段的智能学习助手</p>
    </section>

    <section class="auth-panel">
      <div class="auth-box">
        <div class="mobile-brand"><span class="brand-mark">智</span><strong>智学伴</strong></div>
        <span class="eyebrow">WELCOME TO ZHIXUEBAN</span>
        <h2>{{ authMode === 'login' ? '欢迎回来' : '创建学生账号' }}</h2>
        <p>{{ authMode === 'login' ? '登录后继续今天的学习计划' : '注册后即可开始建立专属学习画像' }}</p>
        <div class="auth-tabs">
          <button :class="{ active: authMode === 'login' }" @click="authMode = 'login'">登录</button>
          <button :class="{ active: authMode === 'register' }" @click="authMode = 'register'">注册</button>
        </div>
        <form @submit.prevent="submitAuth">
          <label>用户名<input v-model.trim="authForm.username" autocomplete="username" maxlength="20" placeholder="请输入 6—20 位用户名"></label>
          <label>密码<input v-model="authForm.password" autocomplete="current-password" maxlength="20" type="password" placeholder="请输入 6—20 位密码"></label>
          <label v-if="authMode === 'register'">确认密码<input v-model="authForm.confirmPassword" autocomplete="new-password" maxlength="20" type="password" placeholder="请再次输入密码"></label>
          <button class="primary-btn auth-submit" :disabled="authLoading">{{ authLoading ? '请稍候…' : authMode === 'login' ? '登录并开始学习' : '注册学生账号' }}</button>
        </form>
        <div class="demo-tip"><span>i</span><p>课程项目开发环境，注册数据由本地后端保存。</p></div>
      </div>
    </section>
  </div>

  <div v-else class="app-layout">
    <aside class="sidebar" :class="{ open: mobileMenu }">
      <div class="side-brand"><span class="brand-mark">智</span><div><strong>智学伴</strong><small>AI 个性化学习助手</small></div></div>
      <nav>
        <template v-for="item in navItems" :key="item.key">
          <p v-if="item.group" class="nav-group">{{ item.group }}</p>
          <button :class="{ active: currentView === item.key }" @click="go(item.key)"><span>{{ item.icon }}</span>{{ item.label }}<i v-if="item.badge !== null && item.badge > 0">{{ item.badge }}</i></button>
        </template>
      </nav>
      <div class="goal-card"><div><span>今日目标</span><strong>{{ todayPlan.task_completed || 0 }} / {{ todayPlan.task_total || (todayPlan.tasks?.length || 0) }} 项</strong></div><div class="progress"><i :style="{width: ((todayPlan.task_total || todayPlan.tasks?.length || 0) > 0 ? Math.round((todayPlan.task_completed || 0) / (todayPlan.task_total || todayPlan.tasks.length) * 100) : 0) + '%'}"></i></div><small>{{ todayPlan.completed ? '今日目标已完成 ✓' : '还有 ' + Math.max(0, (todayPlan.task_total || todayPlan.tasks?.length || 0) - (todayPlan.task_completed || 0)) + ' 项任务待完成' }}</small></div>
      <button class="side-user" @click="go('settings')"><span class="avatar">{{ userInitial }}</span><span><strong>{{ currentUsername }}</strong><small>{{ profileShortText }}</small></span><b>›</b></button>
    </aside>

    <main class="main-shell">
      <header class="topbar">
        <button class="menu-btn" @click="mobileMenu = !mobileMenu">☰</button>
        <div><h1>{{ pageMeta.title }}</h1><p>{{ pageMeta.subtitle }}</p></div>
        <div class="top-actions">
          <button class="points-pill" @click="go('points')">◆ <strong>{{ pointAccount.balance }}</strong> 积分</button>
          <button class="notify" :class="{ hasUnread: unreadCount > 0 }" @click="toggleNotificationPanel">
            ♢
            <i v-if="unreadCount > 0">{{ unreadCount > 99 ? '99+' : unreadCount }}</i>
          </button>
          <span class="avatar small">{{ userInitial }}</span>
        </div>
      </header>

      <!-- 通知面板 -->
      <div v-if="showNotificationPanel" class="notification-panel">
        <div class="notify-header">
          <h3>站内提醒</h3>
          <button class="text-btn" @click="markAllRead" :disabled="unreadCount === 0">全部已读</button>
        </div>
        <div v-if="notificationLoading" class="notify-loading">加载中…</div>
        <div v-else-if="notificationList.length === 0" class="notify-empty">
          <span>🔔</span>
          <p>暂无提醒</p>
          <small>完成学习后会收到提醒</small>
        </div>
        <div v-else class="notify-list">
          <div
            v-for="item in notificationList"
            :key="item.notification_id"
            :class="['notify-item', { unread: !item.is_read }]"
            @click="handleNotificationClick(item)"
          >
            <span class="notify-dot" :class="item.type"></span>
            <div class="notify-body">
              <strong>{{ item.title }}</strong>
              <small>{{ item.content || '' }}</small>
              <time>{{ formatTime(item.created_at) }}</time>
            </div>
            <button v-if="!item.is_read" class="mark-read-btn" @click.stop="markOneRead(item.notification_id)">✓</button>
          </div>
        </div>
        <div class="notify-footer" v-if="notificationList.length > 0">
          <button class="text-btn" @click="go('records')">查看全部学习记录 →</button>
        </div>
      </div>

      <div class="content">
        <!-- 首页 -->
        <section v-if="currentView === 'home'" class="view">
          <article class="hero"><div><span class="eyebrow">{{ greeting }}，{{ currentUsername }}</span><h2>今天从薄弱点开始，<br>把不会的真正弄懂</h2><p>{{ homeRecommendations.primary?.description || '完成一组练习，系统会逐步生成更准确的个性化建议。' }}</p><div class="hero-actions"><button class="primary-btn" :disabled="recommendationLoading" @click="startRecommendation(homeRecommendations.primary)">{{ recommendationLoading?'正在准备练习…':'开始智能学习 →' }}</button><button class="ghost-btn" @click="go('mistakes')">复习历史错题</button></div></div><div class="hero-art"><div class="book">∑<i></i></div><span class="orbit one"></span><span class="orbit two"></span><div class="mini-card a">平均正确率<br><strong>{{ statsSummary.avgAccuracy || 0 }}%</strong></div><div class="mini-card b">今日计划<br><strong>{{ todayPlan.task_completed || 0 }} / {{ todayPlan.task_total || (todayPlan.tasks?.length || 0) }}</strong></div></div></article>
          <div class="stats"><article><span class="stat-icon blue">◎</span><div><small>知识点平均掌握度</small><strong>{{ homeMastery.score }}<em>%</em></strong><p>{{ homeMastery.total }} 个知识点</p></div></article><article><span class="stat-icon green">✓</span><div><small>本周完成练习</small><strong>{{ statsSummary.practiceCount }}<em> 组</em></strong><p>累计 {{ statsSummary.questionCount }} 道题</p></div></article><article><span class="stat-icon orange">△</span><div><small>历史错题</small><strong>{{ homeMistakes.total }}<em> 道</em></strong><p :class="{warn:homeMistakes.due>0}">{{ homeMistakes.due }} 道今日到期</p></div></article><article><span class="stat-icon purple">◆</span><div><small>当前积分</small><strong>{{ pointAccount.balance }}</strong><p>累计获得 {{ pointAccount.earned_total }}</p></div></article></div>
          <div class="dashboard-grid">
            <article class="panel"><div class="panel-head"><div><h3>优先学习建议</h3><p>根据复习计划和近期表现生成</p></div><span class="priority">今日推荐</span></div>
          <div v-if="homeRecommendations.primary" class="recommend-card"><span class="subject-icon">{{ (homeRecommendations.primary.title || '练')[0] }}</span><div><small>{{ homeRecommendations.primary.type === 'review' ? '到期错题复习 · 优先级最高' : homeRecommendations.primary.priority === 2 ? '薄弱知识点巩固' : '推荐练习' }}</small><h3>{{ homeRecommendations.primary.title }}</h3><p>{{ homeRecommendations.primary.description || '' }}</p></div><button class="round-btn" :disabled="recommendationLoading" @click="startRecommendation(homeRecommendations.primary)">→</button></div>
          <div v-if="!homeRecommendations.primary" class="recommend-card"><span class="subject-icon">练</span><div><small>开始今天的学习</small><h3>从练习开始吧</h3><p>完成一组练习，系统会为你生成更精准的推荐。</p></div><button class="round-btn" @click="go('learn')">→</button></div>
          <div v-for="(item, idx) in (homeRecommendations.secondary || []).slice(0, 3)" :key="idx" class="knowledge-row"><span class="rank" :class="idx === 0 ? 'red' : 'amber'">{{ idx + 1 }}</span><div><strong>{{ item.title }}</strong><small>{{ item.description || '' }}</small></div><b></b><button :disabled="recommendationLoading" @click="startRecommendation(item)">练习</button></div>
          <div v-if="(!homeRecommendations.secondary || homeRecommendations.secondary.length === 0)" class="knowledge-row"><span class="rank red">1</span><div><strong>去括号法则</strong><small>完成练习后自动更新推荐</small></div><b></b><button @click="go('learn')">练习</button></div></article>
            <article class="panel"><div class="panel-head"><div><h3>今日学习计划</h3><p>每天一点，进步看得见</p></div><b class="task-count" title="已完成任务项 / 今日任务总项">{{ todayPlan.task_completed || 0 }} / {{ todayPlan.task_total || (todayPlan.tasks?.length || 0) }} 项</b></div>
          <div v-for="(task, idx) in (todayPlan.tasks && todayPlan.tasks.length ? todayPlan.tasks : [])" :key="idx" :class="['task', { done: task.status === 'completed' }]"><span>{{ task.status === 'completed' ? '✓' : (idx + 1) }}</span><div><strong>{{ task.title }}</strong><small>{{ task.status === 'completed' ? '已完成' : '待完成' }}</small></div><em v-if="task.status === 'completed' && task.reward_points">+{{ task.reward_points }}</em></div>
          <div v-if="!todayPlan.tasks || todayPlan.tasks.length === 0" class="task"><span>1</span><div><strong>完成一组推荐练习</strong><small>开始学习即可获得积分奖励</small></div><em>+5</em></div>
          <button class="soft-btn full" @click="go(todayPlan.tasks?.some(task => task.task_type === 'correction' && task.status !== 'completed') ? 'mistakes' : 'learn')">{{ todayPlan.completed ? '今日目标已完成 ✓' : '继续完成今日计划' }}</button></article>
          </div>
        </section>

        <!-- 智能学习 -->
        <section v-else-if="currentView === 'learn'" class="view learn-view">
          <div class="steps"><span :class="{active:learnStep>=1}"><b>1</b>描述问题</span><i></i><span :class="{active:learnStep>=2}"><b>2</b>学情诊断</span><i></i><span :class="{active:learnStep>=3}"><b>3</b>针对练习</span><i></i><span :class="{active:learnStep>=4}"><b>4</b>分析反馈</span></div>
          <div class="learn-grid"><article class="panel ask-panel"><div class="ai-title"><span>AI</span><div><h2>{{ currentLearningTab.title }}</h2><p>{{ currentLearningTab.description }}</p></div></div><div class="context-chips"><span>{{ settings.stage }}</span><span>{{ settings.grade }}</span><span>{{ settings.subject }}</span><button @click="go('settings')">修改</button></div><div class="input-tabs"><button v-for="tab in learningInputTabs" :key="tab.value" :class="{active:learningInputType===tab.value}" @click="switchLearningType(tab.value)">{{ tab.label }}</button></div><textarea v-model="requestForm.text" :disabled="learningBusy" :placeholder="currentLearningTab.placeholder"></textarea><div class="quick"><small>试试这样问：</small><button v-for="prompt in currentLearningTab.prompts" :key="prompt" @click="requestForm.text = prompt">{{ prompt }}</button></div><button class="primary-btn analyse-btn" :disabled="learningBusy||!requestForm.text.trim()" @click="startDiagnosis">{{ diagnosisLoading ? currentLearningTab.loadingLabel : currentLearningTab.actionLabel }}</button></article>
            <aside><article class="panel usage"><div class="panel-head"><h3>今日使用</h3><span>{{ vipStatus.is_vip?'VIP 用户':'普通用户' }}</span></div><div><span>练习生成</span><strong>{{ vipUsage.practice_generation?.used||0 }} / {{ vipUsage.practice_generation?.limit||(vipStatus.is_vip?20:5) }}</strong></div><div class="knowledge-progress"><i :style="{width:usagePercent+'%'}"></i></div><div><span>当前积分</span><strong>{{ pointAccount.balance }}</strong></div><button class="vip-btn full" @click="go('vip')">♛ 查看会员权益</button></article></aside>
          </div>
          <article v-if="diagnosisResult" class="panel learning-result">
            <div class="panel-head"><div><h3>{{ currentLearningTab.resultTitle }}</h3><p>{{ diagnosisResult.knowledge_point_name }}</p></div><span :class="['learning-status',diagnosisResult.learning_status]">{{ diagnosisResult.mastery_evidence==='historical'?learningStatusLabel(diagnosisResult.learning_status):'待练习评估' }}</span></div>
            <div v-if="learningInputType==='learning_question' && diagnosisResult.concept_explanation" class="concept-teaching">
              <section class="concept-lead"><small>先理解概念</small><p>{{ diagnosisResult.concept_explanation.summary }}</p></section>
              <section><h4>关键要点</h4><ul><li v-for="item in diagnosisResult.concept_explanation.key_points" :key="item">{{ item }}</li></ul></section>
              <section v-if="diagnosisResult.concept_explanation.core_structure"><h4>核心结构 / 判断方法</h4><p>{{ diagnosisResult.concept_explanation.core_structure }}</p></section>
              <section v-if="diagnosisResult.concept_explanation.pitfalls?.length"><h4>容易混淆</h4><ul><li v-for="item in diagnosisResult.concept_explanation.pitfalls" :key="item">{{ item }}</li></ul></section>
              <section v-if="diagnosisResult.concept_explanation.example" class="concept-example"><h4>举个例子</h4><p><strong>{{ diagnosisResult.concept_explanation.example.question }}</strong></p><p>{{ diagnosisResult.concept_explanation.example.answer }}</p><ol v-if="diagnosisResult.concept_explanation.example.steps?.length"><li v-for="step in diagnosisResult.concept_explanation.example.steps" :key="step">{{ step }}</li></ol></section>
            </div>
            <div class="diagnosis-grid"><div><small>{{ diagnosisResult.mastery_evidence==='historical'?'当前掌握度':'掌握度' }}</small><strong>{{ diagnosisResult.mastery_evidence==='historical'?diagnosisResult.mastery_score+'%':'待评估' }}</strong><p class="evidence-note">{{ diagnosisResult.mastery_evidence_text }}</p></div><div><small>{{ currentLearningTab.focusLabel }}</small><p>{{ diagnosisResult.weakness||'需要通过练习进一步确认' }}</p></div><div><small>下一步</small><p>{{ diagnosisResult.practice_suggestion||'完成一组针对性练习' }}</p></div></div>
            <div v-if="learningInputType==='learning_question'" class="concept-next"><p>概念看明白后，可以用一组相关检测题确认是否真正理解。</p><button class="primary-btn" :disabled="practiceLoading" @click="generatePractice()">{{ practiceLoading?'正在生成检测题…':'我已理解，生成概念检测 →' }}</button></div>
            <button v-else class="primary-btn" :disabled="practiceLoading" @click="generatePractice()">{{ practiceLoading?'正在生成题目…':currentLearningTab.generateLabel }}</button>
          </article>
          <article v-if="entitlementError" class="panel entitlement-alert"><h3>今日免费练习次数已用完</h3><p>可以使用 10 积分兑换一组额外练习，或开通 VIP 将每日额度提升到 20 组。</p><div><button class="primary-btn" :disabled="exchangeLoading||pointAccount.balance<10" @click="exchangeExtraPractice">{{ exchangeLoading?'兑换中…':`使用 10 积分兑换（余额 ${pointAccount.balance}）` }}</button><button class="ghost-btn" @click="go('vip')">开通 VIP</button></div></article>
          <article v-if="currentPractice" class="panel practice-panel"><div class="panel-head"><div><h3>针对性练习</h3><p>{{ currentPractice.knowledge_point_name }} · {{ difficultyLabel(currentPractice.difficulty) }}</p></div><button class="text-btn" @click="resetLearning">重新诊断</button></div><div v-for="(question,index) in currentPractice.questions" :key="question.question_id" class="practice-question"><div class="question-title"><b>{{ index+1 }}</b><strong>{{ question.content }}</strong><span>{{ difficultyLabel(question.difficulty) }}</span></div><input v-model="practiceAnswers[question.question_id]" :disabled="answerLoading||Boolean(answerResult)" placeholder="请输入答案" /></div><button v-if="!answerResult" class="primary-btn full" :disabled="answerLoading||!allQuestionsAnswered" @click="submitPracticeAnswers">{{ answerLoading?'正在提交分析…':'提交答案并查看分析' }}</button></article>
          <article v-if="answerResult" class="panel feedback-panel">
            <div class="panel-head"><div><h3>练习反馈</h3><p>答对 {{ answerResult.correct_count }} / {{ answerResult.question_count }} 道</p></div><strong :class="answerResult.accuracy>=60?'up':'warn'">{{ answerResult.accuracy }}%</strong></div>
            <div v-for="(result,index) in answerResult.results" :key="result.question_id" :class="['answer-feedback',{correct:result.is_correct}]">
              <div class="feedback-title"><b>{{ result.is_correct?'✓':'×' }}</b><strong>第 {{ index+1 }} 题 · {{ result.is_correct?'回答正确':'需要巩固' }}</strong></div>
              <p><span>你的答案：</span>{{ practiceAnswers[result.question_id] }}</p><p><span>标准答案：</span>{{ result.standard_answer }}</p><p><span>解析：</span>{{ result.analysis }}</p>
              <p v-if="!result.is_correct"><span>错因：</span>{{ errorTypeLabel(result.error_type) }}{{ result.error_description?' · '+result.error_description:'' }}</p>
              <p v-if="result.next_suggestion"><span>建议：</span>{{ result.next_suggestion }}</p>
            </div>
            <div v-if="hasWrongAnswers && !detailedAnalysisUnlocked" class="detail-unlock"><p>解锁每道错题的具体原因和下一步建议。</p><button class="ghost-btn" :disabled="detailedLoading || (!vipStatus.is_vip && pointAccount.balance < 10)" @click="loadDetailedAnalysis">{{ detailedLoading ? '解锁中…' : (vipStatus.is_vip ? 'VIP 查看详细错因' : '使用 10 积分查看详细错因') }}</button></div>
            <div class="feedback-actions"><button class="primary-btn" @click="practiceAgain">按建议难度再练一组</button><button class="ghost-btn" @click="resetLearning">换一个问题</button></div>
          </article>
        </section>

        <!-- 学习画像 -->
        <ProfileView v-else-if="currentView === 'profile'" :profile="profileSummary" :username="currentUsername" @edit="go('settings')" @practice="practiceKnowledgePoint" @review="openKnowledgeReview" />

        <!-- 错题订正 -->
        <MistakesView v-else-if="currentView === 'mistakes'" :stage="profileSummary?.stage" :is-vip="vipStatus.is_vip" :point-balance="pointAccount.balance" :initial-knowledge-point="mistakeKnowledgePoint" :initial-status="mistakeInitialStatus" @updated="refreshAfterCorrection" @review="openKnowledgeReview" @clear-filter="clearMistakeFilter" />

        <KnowledgeReviewView v-else-if="currentView === 'knowledge-review'" :knowledge-point-name="reviewTarget.name" :subject="reviewTarget.subject" @back="go(reviewTarget.from || 'profile')" @mistakes="openRelatedMistakes" />

        <!-- 学习记录 -->
        <section v-else-if="currentView === 'records'" class="view">
          <div class="summary"><div><span>练习记录</span><strong>{{ statsSummary.practiceCount || timelineTotal }}<small> 组</small></strong></div><div><span>完成题目</span><strong>{{ statsSummary.questionCount }}<small> 道</small></strong></div><div><span>平均正确率</span><strong class="up">{{ statsSummary.avgAccuracy }}<small>%</small></strong></div><div><span>掌握度变化</span><strong :class="statsSummary.masteryChange >= 0 ? 'up' : 'warn'">{{ statsSummary.masteryChange >= 0 ? '+' : '' }}{{ statsSummary.masteryChange }}<small>%</small></strong></div></div>
          <article class="panel record-panel">
            <div class="panel-head"><div><h3>学习时间线</h3><p>练习、诊断和订正记录将在这里统一呈现</p></div><div class="filters">
              <button :class="{ active: recordsFilter === 'all' }" @click="setRecordsFilter('all')">全部记录</button>
              <button :class="{ active: recordsFilter === 'practice' }" @click="setRecordsFilter('practice')">专项练习</button>
              <button :class="{ active: recordsFilter === 'correction' }" @click="setRecordsFilter('correction')">错题订正</button>
              <button :class="{ active: recordsFilter === 'report' }" @click="setRecordsFilter('report')">学情报告</button>
            </div></div>
            <div class="subject-filter-bar">
              <span>{{ profileSummary?.stage === 'university' ? '课程' : '学科' }}</span>
              <button :class="{active: recordsSubject === ''}" @click="setRecordsSubject('')">全部</button>
              <button v-for="item in recordSubjectOptions" :key="item" :class="{active: recordsSubject === item}" @click="setRecordsSubject(item)">{{ item }}</button>
              <button v-if="hasUnclassifiedRecords" :class="{active: recordsSubject === '__unclassified__'}" @click="setRecordsSubject('__unclassified__')">历史未分类</button>
            </div>
            <div v-if="recordsLoading" class="notify-loading">加载中…</div>
            <template v-else>
              <template v-for="(record, index) in timelineRecords" :key="record.record_id">
                <div v-if="isDateBoundary(record, index)" class="date-label">{{ formatDateLabel(record.occurred_at) }}</div>
                <div class="record">
                  <time>{{ (record.occurred_at || '').slice(11, 16) }}</time>
                  <span class="record-dot"></span>
                  <div>
                    <span class="subject-icon small-icon">{{ recordTypeIcon(record.record_type) }}</span>
                    <div>
                      <b>{{ record.title }}</b>
                      <p>
                        {{ record.question_count ? record.question_count + ' 道题' : '' }}
                        {{ ' · ' + (record.subject || '历史未分类') }}
                        {{ record.knowledge_point_name ? ' · ' + record.knowledge_point_name : '' }}
                        {{ record.accuracy != null ? ' · 正确率 ' + Math.round(record.accuracy) + '%' : '' }}
                        {{ record.mastery_change ? ' · 掌握度 ' + (record.mastery_change > 0 ? '+' : '') + record.mastery_change : '' }}
                      </p>
                    </div>
                    <strong :class="(record.accuracy || 0) >= 80 ? 'up' : (record.accuracy || 0) < 60 ? 'warn' : ''">
                      {{ record.accuracy != null ? '正确率 ' + Math.round(record.accuracy) + '%' : '' }}
                    </strong>
                  </div>
                </div>
              </template>
            </template>
            <div v-if="!recordsLoading && timelineRecords.length === 0" class="notify-empty">
              <span>📝</span>
              <p>暂无学习记录</p>
              <small>完成练习后这里会显示记录</small>
            </div>
            <div v-if="timelineTotal > 0" class="pagination">
              <button :disabled="recordsPage <= 1" @click="loadRecords(recordsPage - 1)">上一页</button>
              <span>{{ recordsPage }} / {{ recordsPages || 1 }}</span>
              <button :disabled="recordsPage >= recordsPages" @click="loadRecords(recordsPage + 1)">下一页</button>
            </div>
          </article>
          <article class="report-banner"><span>▥</span><div><small>阶段性学情报告</small><h3>生成你的本周学习报告</h3><p>总结掌握度变化、高频错因和下一阶段建议。</p></div><b>普通用户需<br>◆ 20 积分</b><button class="primary-btn" @click="generateReport" :disabled="reportLoading">{{ reportLoading ? '生成中…' : '生成报告' }}</button></article>
          <!-- 最近报告快速入口 -->
          <article v-if="reportList.length > 0" class="panel report-panel" style="margin-top:24px">
            <div class="panel-head"><div><h3>历史报告</h3><p>最近生成的学情报告</p></div><button @click="go('reports')">查看全部 →</button></div>
            <div v-for="r in reportList.slice(0, 3)" :key="r.report_id" class="report-mini-row" @click="viewReportDetail(r.report_id)">
              <span>📊</span>
              <div>
                <strong>{{ r.date_from }} ~ {{ r.date_to }}</strong>
                <small>{{ r.practice_count }} 次练习 · 正确率 {{ r.accuracy != null ? Math.round(r.accuracy) + '%' : '--' }}</small>
              </div>
              <button class="text-btn">查看</button>
            </div>
          </article>
        </section>

        <!-- 学情报告（独立视图） -->
        <section v-else-if="currentView === 'reports'" class="view">
          <div v-if="!selectedReport">
            <div class="panel-head" style="margin-bottom:20px"><div><h2>学情报告</h2><p>阶段性学习分析和建议</p></div><button class="primary-btn" @click="generateReport" :disabled="reportLoading">{{ reportLoading ? '生成中…' : '+ 生成新报告' }}</button></div>
            <article class="panel">
              <div v-if="reportsLoading" class="notify-loading">加载中…</div>
              <div v-else-if="reportList.length === 0" class="notify-empty">
                <span>📊</span>
                <p>暂无学情报告</p>
                <small>完成阶段学习后可生成报告</small>
              </div>
              <div v-else class="report-list">
                <div v-for="r in reportList" :key="r.report_id" class="report-card" @click="viewReportDetail(r.report_id)">
                  <span class="report-card-icon">📊</span>
                  <div class="report-card-body">
                    <div class="report-card-header">
                      <strong>{{ r.date_from }} ~ {{ r.date_to }}</strong>
                      <span>{{ r.created_at ? r.created_at.slice(0, 10) : '' }}</span>
                    </div>
                    <div class="report-card-stats">
                      <span>练习 {{ r.practice_count }} 次</span>
                      <span :class="(r.accuracy || 0) >= 80 ? 'up' : (r.accuracy || 0) < 60 ? 'warn' : ''">正确率 {{ r.accuracy != null ? Math.round(r.accuracy) + '%' : '--' }}</span>
                    </div>
                  </div>
                  <button class="round-btn">→</button>
                </div>
              </div>
              <div v-if="reportList.length > 0" class="pagination">
                <button :disabled="reportsPage <= 1" @click="loadReports(reportsPage - 1)">上一页</button>
                <span>{{ reportsPage }} / {{ reportsPages || 1 }}</span>
                <button :disabled="reportsPage >= reportsPages" @click="loadReports(reportsPage + 1)">下一页</button>
              </div>
            </article>
          </div>
          <!-- 报告详情 -->
          <div v-else>
            <button class="ghost-btn back-btn" @click="selectedReport = null">← 返回报告列表</button>
            <article class="panel report-detail">
              <div class="report-detail-head">
                <div>
                  <h2>{{ selectedReport.date_from }} ~ {{ selectedReport.date_to }}</h2>
                  <p>生成于 {{ selectedReport.created_at ? selectedReport.created_at.slice(0, 10) : '--' }}</p>
                </div>
                <div class="report-score">
                  <small>阶段正确率</small>
                  <strong :class="reportOverview.accuracy >= 80 ? 'up' : reportOverview.accuracy < 60 ? 'warn' : ''">{{ Math.round(reportOverview.accuracy || 0) }}%</strong>
                  <span v-if="activeReport?.comparison?.has_previous_data" :class="activeReport.comparison.accuracy_delta >= 0 ? 'up' : 'warn'">
                    较上阶段 {{ activeReport.comparison.accuracy_delta >= 0 ? '+' : '' }}{{ activeReport.comparison.accuracy_delta }}%
                  </span>
                  <span v-else>作为后续报告的对比基线</span>
                </div>
              </div>
              <div class="report-scope-tabs">
                <button v-for="tab in reportTabs" :key="tab.value" :class="{active:reportSection===tab.value}" @click="reportSection=tab.value">{{ tab.label }}</button>
              </div>
              <div v-if="activeReport && reportSection !== 'all' && !activeReport.sample_sufficient" class="sample-warning">本阶段该{{ reportScopeMode === 'course' ? '课程' : '学科' }}答题少于 5 道，分析仅供参考，继续练习后会更准确。</div>
              <div v-if="!activeReport" class="report-no-data">
                <span>▥</span>
                <h3>本阶段暂无{{ activeReportLabel }}学情报告</h3>
                <p v-if="reportScopeMode === 'course'">完成该课程至少一组有效练习后，系统会自动生成课程分析。</p>
                <p v-else>完成{{ activeReportLabel }}练习后，这里将展示知识点、错因和专项提升计划。</p>
              </div>
              <template v-else>
              <div v-if="activeReport.summary" class="report-summary"><span>AI 学习诊断</span><p>{{ activeReport.summary }}</p></div>
              <div class="stats" style="margin:20px 0">
                <article><span class="stat-icon blue">◎</span><div><small>专项练习</small><strong>{{ reportOverview.practice_count || 0 }}<em> 次</em></strong></div></article>
                <article><span class="stat-icon green">✓</span><div><small>答对题目</small><strong>{{ reportOverview.correct_count || 0 }}<em> / {{ reportOverview.question_count || 0 }}</em></strong></div></article>
                <article><span class="stat-icon orange">日</span><div><small>学习活跃度</small><strong>{{ reportOverview.study_days || 0 }}<em> / {{ reportOverview.period_days || 0 }} 天</em></strong></div></article>
                <article><span class="stat-icon red-soft">!</span><div><small>错题与订正</small><strong>{{ reportOverview.wrong_count || 0 }}<em> 错 · {{ reportOverview.correction_count || 0 }} 订正</em></strong></div></article>
                <article v-if="reportOverview.knowledge_review_count"><span class="stat-icon purple">知</span><div><small>知识点复习</small><strong>{{ reportOverview.knowledge_review_count }}<em> 次</em></strong><p>概念自测 {{ reportOverview.concept_quiz_accuracy }}%</p></div></article>
              </div>

              <div v-if="activeReport.daily_trend?.length" class="report-section">
                <div class="report-section-head"><div><h4>学习趋势</h4><p>按天查看练习量与正确率，判断学习节奏是否稳定</p></div></div>
                <div class="report-trend">
                  <div v-for="day in activeReport.daily_trend" :key="day.date" class="trend-day">
                    <div class="trend-bar"><i :style="{height: `${Math.max(day.accuracy, 4)}%`}"></i></div>
                    <strong>{{ Math.round(day.accuracy) }}%</strong>
                    <small>{{ day.date.slice(5) }}</small>
                    <em>{{ day.question_count }}题</em>
                  </div>
                </div>
              </div>

              <div v-if="activeReport.knowledge_breakdown?.length" class="report-section">
                <div class="report-section-head"><div><h4>知识点表现</h4><p>不只看平均分，定位每个知识点的练习证据与当前掌握度</p></div></div>
                <div class="report-kp-table">
                  <div class="report-kp-row head"><span>知识点</span><span>答题</span><span>正确率</span><span>掌握度</span><span>判断</span></div>
                  <div v-for="item in activeReport.knowledge_breakdown" :key="item.name" class="report-kp-row">
                    <strong><button class="kp-review-link" @click="openKnowledgeReview({name:item.name,subject:reportSection==='all'?'':reportSection,from:'reports'})">{{ item.name }} <small>先复习</small></button></strong>
                    <span>{{ item.correct_count }} / {{ item.question_count }}</span>
                    <span><i class="mini-progress"><b :style="{width:`${item.accuracy}%`}"></b></i>{{ Math.round(item.accuracy) }}%</span>
                    <span>{{ item.mastery_score == null ? '--' : item.mastery_score + '%' }}</span>
                    <em :class="item.accuracy >= 80 ? 'good' : item.accuracy < 60 ? 'weak' : 'medium'">{{ item.accuracy >= 80 ? '表现稳定' : item.accuracy < 60 ? '优先补弱' : '继续巩固' }}</em>
                  </div>
                </div>
              </div>

              <div class="report-analysis-grid">
                <div class="report-section analysis-card">
                  <div class="report-section-head"><div><h4>错因分布</h4><p>本阶段错题的主要成因</p></div></div>
                  <div v-if="activeReport.error_distribution?.length" class="error-distribution">
                    <div v-for="item in activeReport.error_distribution" :key="item.type">
                      <span>{{ errorTypeLabel(item.type) }}</span><i><b :style="{width:`${item.percentage}%`}"></b></i><strong>{{ item.count }} 道 · {{ item.percentage }}%</strong>
                    </div>
                  </div>
                  <p v-else class="report-empty">本阶段暂无已分类错题</p>
                </div>
                <div class="report-section analysis-card">
                  <div class="report-section-head"><div><h4>阶段对比</h4><p>{{ activeReport.comparison?.previous_date_from }} ~ {{ activeReport.comparison?.previous_date_to }}</p></div></div>
                  <div v-if="activeReport.comparison" class="comparison-list">
                    <div><span>正确率变化</span><strong v-if="activeReport.comparison.has_previous_data" :class="activeReport.comparison.accuracy_delta >= 0 ? 'up' : 'warn'">{{ activeReport.comparison.accuracy_delta >= 0 ? '+' : '' }}{{ activeReport.comparison.accuracy_delta }}%</strong><strong v-else>暂无基线</strong></div>
                    <div><span>答题量变化</span><strong>{{ activeReport.comparison.question_delta >= 0 ? '+' : '' }}{{ activeReport.comparison.question_delta }} 道</strong></div>
                    <div><span>练习次数变化</span><strong>{{ activeReport.comparison.practice_delta >= 0 ? '+' : '' }}{{ activeReport.comparison.practice_delta }} 次</strong></div>
                  </div>
                </div>
              </div>

              <div v-if="activeReport.action_plan?.length" class="report-section action-plan">
                <div class="report-section-head"><div><h4>下一阶段行动计划</h4><p>按优先级执行，下一份报告将检验是否达成</p></div></div>
                <div v-for="plan in activeReport.action_plan" :key="plan.priority" class="action-item">
                  <span>{{ plan.priority }}</span>
                  <div><strong>{{ plan.title }}</strong><p>{{ plan.reason }}</p><small>目标：{{ plan.target }}</small></div>
                </div>
              </div>
              </template>
            </article>
          </div>
        </section>

        <section v-else-if="currentView === 'points'" class="view"><div class="points-hero"><div><span>当前可用积分</span><strong>{{ pointAccount.balance }} <small>◆</small></strong><p>坚持有效学习，让每一次进步都有回报</p></div><div class="points-stats"><span><small>累计消费</small><b>{{ pointAccount.spent_total }}</b></span><span><small>累计获得</small><b>{{ pointAccount.earned_total }}</b></span></div><div class="coins">◆</div></div><div class="two-col"><article class="panel"><div class="panel-head"><div><h3>每日学习任务</h3><p>完成任务即可获得积分</p></div></div><div v-for="task in pointTasks" :key="task.task_type" class="mission" :class="{ done: task.claimed }"><span>{{ task.claimed ? '✓' : '学' }}</span><div><b>{{ task.title }}</b><small>进度 {{ task.progress }} / {{ task.target }}</small></div><em>+{{ task.reward_points }}</em><button :disabled="task.claimed" @click="completePointTask(task)">{{ task.claimed ? (task.task_type === 'daily_check_in' ? '已签到' : '已完成') : (task.task_type === 'daily_check_in' ? '签到' : '去完成') }}</button></div></article><article class="panel streak"><div class="panel-head"><div><h3>积分流水</h3><p>最近的积分变化</p></div></div><p v-if="!pointTransactions.length">暂无积分流水</p><p v-for="transaction in pointTransactions.slice(0, 5)" :key="transaction.transaction_id">{{ transaction.description }}：{{ transaction.change > 0 ? '+' : '' }}{{ transaction.change }}</p></article></div><article class="panel exchange"><div class="panel-head"><div><h3>积分兑换</h3><p>普通用户也能体验高级学习能力</p></div><span>余额 {{ pointAccount.balance }}</span></div><div class="exchange-grid"><div v-for="item in exchanges" :key="item.itemType"><span>{{ item.icon }}</span><div><h4>{{ item.name }}</h4><p>{{ item.desc }}</p></div><b>◆ {{ item.cost }}</b><button @click="redeem(item)">{{ item.action }}</button></div></div></article></section>

        <section v-else-if="currentView === 'vip'" class="view">
          <div v-if="paymentState.message" :class="['payment-state', paymentState.status]"><strong>{{ {paid:'支付成功',closed:'订单已关闭',failed:'支付处理失败',paying:'支付确认中',pending:'等待支付'}[paymentState.status] || '支付状态' }}</strong><span>{{ paymentState.message }}</span><button v-if="paymentState.orderNo && ['pending','paying','failed'].includes(paymentState.status)" :disabled="paymentQuerying===paymentState.orderNo" @click="refreshPaymentOrder(paymentState.orderNo)">{{ paymentQuerying===paymentState.orderNo?'查询中…':'再次查询' }}</button></div>
          <div class="vip-hero"><div><span>{{ vipStatus.is_vip ? '已开通智学伴 VIP' : '智学伴 VIP' }}</span><h2>让每一次学习，都更懂你</h2><p>{{ vipStatus.is_vip ? `有效期至 ${new Date(vipStatus.expires_at).toLocaleString()}` : '解锁更深入的错因分析、更完整的学习画像和更持续的个性化服务。' }}</p><div><b>✓ 更多针对性练习</b><b>✓ 完整学情报告</b><b>✓ 详细错因分析</b></div></div><div class="vip-card"><small>♛ ZHIXUEBAN</small><strong>VIP</strong><span>{{ vipUsage.membership === 'vip' ? `今日练习 ${vipUsage.practice_generation?.used || 0} / ${vipUsage.practice_generation?.limit || 20}` : '专属个性化学习服务' }}</span></div></div>
          <article class="panel compare"><div class="panel-head centered"><div><h2>选择适合你的学习方式</h2><p>基础学习始终开放，VIP 提供更深入的服务</p></div></div><div class="compare-row head"><span>功能权益</span><b>普通用户</b><b>♛ VIP 用户</b></div><div v-for="row in vipRows" :key="row[0]" class="compare-row"><span>{{ row[0] }}</span><b>{{ row[1] }}</b><b>{{ row[2] }}</b></div></article>
          <article class="plan-card"><span class="recommend-label">{{ vipStatus.is_vip ? '当前会员' : '推荐套餐' }}</span><div><h3>30 天 VIP 会员</h3><p>通过支付宝沙箱体验完整支付和开通流程</p></div><strong>¥ <b>19</b>.9</strong><ul><li>每日 20 组智能练习</li><li>详细错因分析</li><li>完整历史记录</li><li>阶段性学情报告</li></ul><button class="gold-btn" :disabled="vipPayLoading" @click="startVipPayment">{{ vipPayLoading ? '正在创建订单…' : (vipStatus.is_vip ? '续费 30 天' : '使用支付宝沙箱支付') }}</button><small>有效会员续费会从当前到期时间顺延 30 天</small></article>
          <article class="panel"><div class="panel-head"><div><h3>订单记录</h3><p>最近的会员订单与支付状态</p></div></div><p v-if="!vipOrders.length">暂无会员订单</p><div v-for="order in vipOrders" :key="order.order_no" class="knowledge-row"><div><strong>{{ order.order_no }}</strong><small>{{ order.created_at ? new Date(order.created_at).toLocaleString() : '' }}</small></div><b>¥ {{ order.amount }}</b><span>{{ {pending:'待支付',paying:'支付中',paid:'已支付',closed:'已关闭',refunded:'已退款'}[order.status] || order.status }}</span><button v-if="['pending','paying'].includes(order.status)" :disabled="paymentQuerying===order.order_no" @click="refreshPaymentOrder(order.order_no)">{{ paymentQuerying===order.order_no?'查询中…':'查询结果' }}</button></div></article>
        </section>

        <!-- 设置 -->
        <SettingsView v-else @saved="handleProfileSaved" @logout="clearSession" />
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, defineAsyncComponent, reactive, ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getToken, login, register, setToken } from './api'
import { clearSessionMemory, getMyProfile } from './api/profile'
import { getMasteries, getMistakes, getTodayReviews } from './api/mastery'
import { createPractice, diagnose, newRequestId, submitAnswers, unlockDetailedAnalysis } from './api/learning'
import { getRecords as fetchRecordsApi, getRecordsStats, getHomeRecommendations, getTodayPlan, getNotifications, getUnreadCount, markNotificationRead, markAllNotificationsRead } from './api/records'
import { subjectsForStage } from './constants/education'
import { getReports, generateStageReport, getReportDetail } from './api/reports'
import { createAlipayForm, createVipOrder, getVipOrders, getVipStatus, getVipUsage, queryVipOrder } from './api/vip'
import { checkIn, exchangePoints, getPointAccount, getPointTasks, getPointTransactions } from './api/points'
const SettingsView = defineAsyncComponent(() => import('./components/SettingsView.vue'))
const ProfileView = defineAsyncComponent(() => import('./components/ProfileView.vue'))
const MistakesView = defineAsyncComponent(() => import('./components/MistakesView.vue'))
const KnowledgeReviewView = defineAsyncComponent(() => import('./components/KnowledgeReviewView.vue'))

const route=useRoute(), router=useRouter()
const routeViews=new Set(['home','learn','profile','mistakes','knowledge-review','records','reports','points','vip','settings'])
const initialView=route.name==='payment-result'?'vip':routeViews.has(String(route.name))?String(route.name):'home'
const authMode=ref('login'), authLoading=ref(false), analysisLoading=ref(false), vipPayLoading=ref(false), token=ref(''), currentView=ref(initialView), mobileMenu=ref(false), messages=ref([])
const authForm=reactive({username:'',password:'',confirmPassword:''})
const requestForm=reactive({userId:1,sessionId:1,text:''})
const settings=reactive({stage:'初中',grade:'七年级',subject:'数学',days:'5 天',target:'3 组练习'})
const profileSummary=ref(null)
const savedReviewTarget=(()=>{
  try{return JSON.parse(sessionStorage.getItem('knowledge_review_target')||'{}')}catch{return {}}
})()
const reviewTarget=reactive({
  name:String(route.query.kp||savedReviewTarget.name||''),
  subject:String(route.query.subject||savedReviewTarget.subject||''),
  from:String(route.query.from||savedReviewTarget.from||'profile'),
})
const mistakeKnowledgePoint=ref(route.name==='mistakes'?String(route.query.kp||''):'')
const mistakeInitialStatus=ref(route.name==='mistakes'?String(route.query.status||''):'')
const currentUsername=ref(localStorage.getItem('question_set_username') || '同学')
const pointAccount=reactive({balance:0,earned_total:0,spent_total:0}), pointTasks=ref([]), pointTransactions=ref([])
const vipStatus=reactive({is_vip:false,started_at:null,expires_at:null}), vipUsage=reactive({}), vipOrders=ref([])
const paymentState=reactive({status:'',orderNo:'',message:''}), paymentQuerying=ref('')
const learningInputTabs=[
  {value:'weakness',label:'专项补弱',title:'描述你反复出错的地方',description:'定位错误机制，随后生成由易到难的专项变式。',placeholder:'例如：我做一元一次方程时，经常在去括号和移项处出错……',actionLabel:'分析薄弱点 ✦',loadingLabel:'正在分析薄弱点…',resultTitle:'薄弱点诊断',focusLabel:'定位结果',generateLabel:'生成专项训练 →',prompts:['移项时为什么总变错号？','我总在去括号时出错','分数方程通分容易错']},
  {value:'question',label:'原题攻克',title:'粘贴一道不会做或做错的题',description:'识别原题考点与解题入口，再生成同类迁移题。',placeholder:'请粘贴完整题目；如果有自己的答案或卡住的步骤，也可以一起写上。',actionLabel:'分析这道题 ✦',loadingLabel:'正在分析原题…',resultTitle:'原题考点分析',focusLabel:'解题卡点',generateLabel:'生成同类变式 →',prompts:['这道题第一步应该怎么想？','我的解法错在哪里？','给我出几道同类变式']},
  {value:'learning_question',label:'概念答疑',title:'提出一个想真正弄懂的概念',description:'梳理定义、适用条件和易混点，再用检测题确认理解。',placeholder:'例如：现在完成时和一般过去时到底有什么区别？',actionLabel:'讲清这个概念 ✦',loadingLabel:'正在梳理概念…',resultTitle:'概念理解诊断',focusLabel:'理解难点',generateLabel:'生成概念检测 →',prompts:['为什么移项要变号？','现在完成时什么时候用？','相似和全等有什么区别？']},
]
const learningInputType=ref('weakness'), diagnosisLoading=ref(false), practiceLoading=ref(false), answerLoading=ref(false), exchangeLoading=ref(false), recommendationLoading=ref(false)
const detailedLoading=ref(false), detailedRequestId=ref('')
const diagnosisResult=ref(null), currentPractice=ref(null), answerResult=ref(null), entitlementError=ref(false)
const recommendedSubject=ref('')
const practiceRequestId=ref(''), answerRequestId=ref('')
const practiceAnswers=reactive({})
const isAuthed=computed(()=>Boolean(token.value))
const learningBusy=computed(()=>diagnosisLoading.value||practiceLoading.value||answerLoading.value)
const learnStep=computed(()=>answerResult.value?4:currentPractice.value?3:diagnosisResult.value?2:1)
const allQuestionsAnswered=computed(()=>Boolean(currentPractice.value?.questions?.length)&&currentPractice.value.questions.every(q=>String(practiceAnswers[q.question_id]||'').trim()))
const hasWrongAnswers=computed(()=>Boolean(answerResult.value?.results?.some(item=>!item.is_correct)))
const detailedAnalysisUnlocked=computed(()=>Boolean(answerResult.value?.results?.some(item=>item.error_description||item.next_suggestion)))
const usagePercent=computed(()=>{const item=vipUsage.practice_generation||{};return item.limit?Math.min(100,Math.round((item.used||0)/item.limit*100)):0})
const navItems=computed(()=>[
  {key:'home',label:'学习首页',icon:'⌂',group:'学习空间',badge:null},
  {key:'learn',label:'智能学习',icon:'✦',badge:null},
  {key:'profile',label:'学习画像',icon:'◎',badge:null},
  {key:'mistakes',label:'错题订正',icon:'↻',badge:null},
  {key:'records',label:'学习记录',icon:'▤',badge:null},
  {key:'reports',label:'学情报告',icon:'📊',badge:null},
  {key:'points',label:'积分中心',icon:'◆',group:'成长与权益',badge:null},
  {key:'vip',label:'会员中心',icon:'♛',badge:null},
  {key:'settings',label:'基础信息设置',icon:'⚙',group:'个人设置',badge:null}
])
const metas={home:['学习首页','继续保持今天的学习节奏吧'],learn:['智能学习','描述你的问题，智学伴会为你诊断并生成针对性练习'],profile:['学习画像','了解每个知识点的掌握情况和成长趋势'],mistakes:['错题订正','完成订正并按计划复习，真正掌握薄弱知识点'],'knowledge-review':['知识点复习','先理解概念与方法，再订正错题和完成变式练习'],records:['学习记录','回顾每一次练习和进步'],reports:['学情报告','查看阶段性的学习分析和建议'],points:['积分中心','坚持有效学习，用积分兑换更多学习能力'],vip:['会员中心','解锁更深入、更持续的个性化学习服务'],settings:['基础信息设置','完善信息，让学习内容更适合你']}
const pageMeta=computed(()=>{
  const meta=metas[currentView.value]
  return meta?{title:meta[0],subtitle:meta[1]}:{title:currentView.value,subtitle:''}
})
const currentLearningTab=computed(()=>learningInputTabs.find(item=>item.value===learningInputType.value)||learningInputTabs[0])
const stageLabels={primary:'小学',junior:'初中',senior:'高中',university:'大学'}
const userInitial=computed(()=>currentUsername.value.slice(0,1).toUpperCase()||'学')
const profileShortText=computed(()=>profileSummary.value?`${stageLabels[profileSummary.value.stage]||profileSummary.value.stage} · ${profileSummary.value.grade} · ${profileSummary.value.subject}`:'待完善学习信息')
const greeting=computed(()=>{const hour=new Date().getHours();return hour<6?'夜深了':hour<12?'上午好':hour<18?'下午好':'晚上好'})
// ── 成员四：真实 API 数据状态 ──
const homeRecommendations = ref({ primary: null, secondary: [] })
const todayPlan = ref({ date: '', target_groups: 3, completed_groups: 0, completed: false, task_completed: 0, task_total: 0, tasks: [] })
const timelineRecords = ref([])
const timelineTotal = ref(0)
const statsSummary = ref({ practiceCount: 0, questionCount: 0, avgAccuracy: 0, masteryChange: 0 })
const homeMastery = ref({ score: 0, total: 0 })
const homeMistakes = ref({ total: 0, due: 0 })
const reportList = ref([])
const reportLoading = ref(false)
const reportRequestId = ref('')
const recordsLoading = ref(false)
const recordsPage = ref(1)
const recordsPages = ref(1)
const recordsFilter = ref('all')
const recordsSubject = ref('')
const recordSubjects = ref([])
const recordSubjectOptions = computed(() => {
  const configured = subjectsForStage(profileSummary.value?.stage)
  return [...new Set([...configured, ...recordSubjects.value])]
})
const hasUnclassifiedRecords = ref(false)
const reportsLoading = ref(false)
const reportsPage = ref(1)
const reportsPages = ref(1)
const selectedReport = ref(null)
const reportSection = ref('all')
const reportScopeMode = computed(() => selectedReport.value?.report_scope?.mode
  || (profileSummary.value?.stage === 'university' ? 'course' : 'subject'))
const reportTabs = computed(() => {
  if (!selectedReport.value) return []
  const tabs = [{ value: 'all', label: '综合总览' }]
  const available = selectedReport.value.report_scope?.available_subjects || []
  const names = reportScopeMode.value === 'course'
    ? [...new Set([profileSummary.value?.subject, ...available].filter(Boolean))]
    : subjectsForStage(profileSummary.value?.stage)
  return [...tabs, ...names.map(name => ({ value: name, label: name }))]
})
const activeReport = computed(() => reportSection.value === 'all'
  ? selectedReport.value
  : selectedReport.value?.subject_reports?.[reportSection.value] || null)
const reportOverview = computed(() => activeReport.value?.overview || activeReport.value || {})
const activeReportLabel = computed(() => reportSection.value === 'all'
  ? '综合'
  : `${reportSection.value}${reportScopeMode.value === 'course' ? '课程' : '学科'}`)

// ── 通知状态 ──
const showNotificationPanel = ref(false)
const notificationList = ref([])
const notificationLoading = ref(false)
const unreadCount = ref(0)

// ── 成员四：API 数据获取 ──
async function fetchHomeData() {
  if (!isAuthed.value) return
  const results = await Promise.allSettled([
      getHomeRecommendations(),
      getTodayPlan(),
      getRecordsStats(),
      getMasteries({ page_size: 100 }),
      getMistakes({ page_size: 1 }),
      getTodayReviews(),
  ])
  const [recResult, planResult, statsResult, masteryResult, mistakeResult, reviewResult] = results
  if (recResult.status === 'fulfilled' && recResult.value?.data) homeRecommendations.value = recResult.value.data
  if (planResult.status === 'fulfilled' && planResult.value?.data) todayPlan.value = planResult.value.data
  if (statsResult.status === 'fulfilled' && statsResult.value?.data) {
    const data = statsResult.value.data
    statsSummary.value = {
      practiceCount: data.practice_count || 0,
      questionCount: data.question_count || 0,
      avgAccuracy: data.avg_accuracy || 0,
      masteryChange: data.mastery_change || 0,
    }
  }
  if (masteryResult.status === 'fulfilled' && masteryResult.value?.data) {
    const items = masteryResult.value.data.items || []
    homeMastery.value = {
      score: items.length ? Math.round(items.reduce((sum, item) => sum + item.mastery_score, 0) / items.length) : 0,
      total: masteryResult.value.data.total || items.length,
    }
  }
  if (mistakeResult.status === 'fulfilled' && mistakeResult.value?.data) homeMistakes.value.total = mistakeResult.value.data.total || 0
  if (reviewResult.status === 'fulfilled') homeMistakes.value.due = reviewResult.value?.data?.length || 0
}

async function loadRecords(page = 1) {
  recordsLoading.value = true
  recordsPage.value = page
  const params = { page, page_size: 20 }
  if (recordsFilter.value !== 'all') params.type = recordsFilter.value
  if (recordsSubject.value) params.subject = recordsSubject.value
  try {
    const res = await fetchRecordsApi(params)
    if (res?.data) {
      timelineRecords.value = res.data.items || []
      timelineTotal.value = res.data.total || 0
      recordsPages.value = res.data.pages || 1
      recordSubjects.value = res.data.subjects || []
      hasUnclassifiedRecords.value = Boolean(res.data.has_unclassified)
    }
    // 获取统计摘要
    try {
      const statsRes = await getRecordsStats()
      if (statsRes?.data) {
        statsSummary.value = {
          practiceCount: statsRes.data.practice_count || 0,
          questionCount: statsRes.data.question_count || 0,
          avgAccuracy: statsRes.data.avg_accuracy || 0,
          masteryChange: statsRes.data.mastery_change || 0,
        }
      }
    } catch (e) { /* */ }
  } catch (e) { /* 静默降级 */ }
  finally { recordsLoading.value = false }
}

function setRecordsFilter(filter) {
  recordsFilter.value = filter
  loadRecords(1)
}

function setRecordsSubject(subject) {
  recordsSubject.value = subject
  loadRecords(1)
}

async function loadReports(page = 1) {
  reportsLoading.value = true
  reportsPage.value = page
  try {
    const res = await getReports({ page, page_size: 20 })
    if (res?.data) {
      reportList.value = res.data.items || []
      reportsPages.value = res.data.pages || 1
    }
  } catch (e) { /* 静默降级 */ }
  finally { reportsLoading.value = false }
}

async function viewReportDetail(reportId) {
  try {
    const res = await getReportDetail(reportId)
    if (res?.data) {
      selectedReport.value = res.data
      reportSection.value = 'all'
    }
  } catch (e) {
    ElMessage.warning(e.message || '获取报告详情失败')
  }
}

async function generateReport() {
  reportLoading.value = true
  try {
    if (!reportRequestId.value) reportRequestId.value = newRequestId()
    const today = new Date()
    const weekAgo = new Date(today.getTime() - 7 * 86400000)
    const fmt = d => d.toISOString().slice(0, 10)
    const res = await generateStageReport({
      date_from: fmt(weekAgo),
      date_to: fmt(today),
      payment_method: vipStatus.is_vip ? 'vip' : 'points',
    }, reportRequestId.value)
    if (res?.data) {
      reportRequestId.value = ''
      ElMessage.success('报告生成成功')
      reportList.value.unshift(res.data)
      selectedReport.value = res.data
      reportSection.value = 'all'
      currentView.value = 'reports'
    }
  } catch (e) {
    ElMessage.warning(e.message || '生成报告失败，请稍后重试')
  }
  finally { reportLoading.value = false }
}

// ── 通知功能 ──
async function loadNotifications() {
  notificationLoading.value = true
  try {
    const [notifRes, countRes] = await Promise.all([
      getNotifications({ page: 1, page_size: 20 }),
      getUnreadCount(),
    ])
    if (notifRes?.data) {
      notificationList.value = notifRes.data.items || []
    }
    if (countRes?.data) {
      unreadCount.value = countRes.data.count || 0
    }
  } catch (e) { /* 静默降级 */ }
  finally { notificationLoading.value = false }
}

function toggleNotificationPanel() {
  showNotificationPanel.value = !showNotificationPanel.value
  if (showNotificationPanel.value) {
    loadNotifications()
  }
}

async function markOneRead(id) {
  try {
    await markNotificationRead(id)
    const item = notificationList.value.find(n => n.notification_id === id)
    if (item) item.is_read = true
    unreadCount.value = Math.max(0, unreadCount.value - 1)
  } catch (e) {
    ElMessage.warning(e.message || '操作失败')
  }
}

async function markAllRead() {
  try {
    await markAllNotificationsRead()
    notificationList.value.forEach(n => { n.is_read = true })
    unreadCount.value = 0
    ElMessage.success('已全部标记为已读')
  } catch (e) {
    ElMessage.warning(e.message || '操作失败')
  }
}

function handleNotificationClick(item) {
  if (!item.is_read) {
    markOneRead(item.notification_id)
  }
  if (item.type === 'review_due' || item.type === 'daily_plan') {
    go('home')
  }
  showNotificationPanel.value = false
}

// ── 辅助函数 ──
function recordTypeIcon(type) {
  const map = { practice: '练', correction: '订', diagnosis: '诊', review: '复', report: '报' }
  return map[type] || '记'
}

function isDateBoundary(record, index) {
  if (!record?.occurred_at) return false
  if (index === 0) return true
  return timelineRecords.value[index - 1]?.occurred_at?.slice(0, 10) !== record.occurred_at.slice(0, 10)
}

function formatDateLabel(dateStr) {
  if (!dateStr) return ''
  const today = new Date().toISOString().slice(0, 10)
  const d = dateStr.slice(0, 10)
  if (d === today) return '今天 · ' + d.slice(5)
  const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10)
  if (d === yesterday) return '昨天 · ' + d.slice(5)
  return d
}

function formatTime(dateStr) {
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
    const now = new Date()
    const diff = now - d
    if (diff < 60000) return '刚刚'
    if (diff < 3600000) return Math.floor(diff / 60000) + ' 分钟前'
    if (diff < 86400000) return Math.floor(diff / 3600000) + ' 小时前'
    return dateStr.slice(0, 10)
  } catch { return dateStr }
}

function errorTypeLabel(type) {
  const map = { knowledge: '概念不清', calculation: '计算错误', reading: '审题不清', method: '方法不对' }
  return map[type] || type
}

// 监听页面切换，自动加载数据
watch(currentView, (view) => {
  const routeName = route.name === 'payment-result' && view === 'vip' ? 'payment-result' : route.name
  if (routeName !== view && routeViews.has(view)) {
    const query=view==='knowledge-review'&&reviewTarget.name
      ?{kp:reviewTarget.name,subject:reviewTarget.subject,from:reviewTarget.from}
      :undefined
    router.push({name:view,query})
  }
  if (view === 'home') fetchHomeData()
  if (view === 'records') loadRecords()
  if (view === 'reports') loadReports()
  showNotificationPanel.value = false
  selectedReport.value = null
})

watch(() => route.name, (name) => {
  const next = name === 'payment-result' ? 'vip' : String(name || 'home')
  if (routeViews.has(next) && currentView.value !== next) currentView.value = next
})

watch(
  () => [route.name, route.query.kp, route.query.subject, route.query.from],
  ([name, kp, subject, from]) => {
    if(name!=='knowledge-review')return
    const nextName=String(kp||reviewTarget.name||'')
    if(!nextName){
      ElMessage.warning('请选择需要复习的具体知识点')
      router.replace({name:'profile'})
      return
    }
    Object.assign(reviewTarget,{
      name:nextName,
      subject:String(subject||reviewTarget.subject||''),
      from:String(from||reviewTarget.from||'profile'),
    })
    sessionStorage.setItem('knowledge_review_target',JSON.stringify(reviewTarget))
  },
  {immediate:true},
)

// 点击外部关闭通知面板
watch(showNotificationPanel, (val) => {
  if (val) {
    setTimeout(() => {
      const handler = (e) => {
        const panel = document.querySelector('.notification-panel')
        const btn = document.querySelector('.notify')
        if (panel && !panel.contains(e.target) && btn && !btn.contains(e.target)) {
          showNotificationPanel.value = false
          document.removeEventListener('click', handler)
        }
      }
      document.addEventListener('click', handler)
    }, 0)
  }
})

// 首次进入时加载数据
onMounted(async () => {
  try { const res = await getTodayPlan(); if (res?.data) todayPlan.value = res.data } catch (e) { /* */ }
  try { const res = await getUnreadCount(); if (res?.data) unreadCount.value = res.data.count || 0 } catch (e) { /* */ }
  if (currentView.value === 'home') fetchHomeData()
})

const exchanges=[{itemType:'extra_practice',icon:'＋',name:'额外一组练习',desc:'兑换后生成下一组练习时自动核销',cost:10,action:'兑换次数'},{itemType:'detailed_analysis',icon:'⌕',name:'详细错因分析',desc:'在练习反馈中按次解锁，成功后扣分',cost:10,action:'去完成练习'},{itemType:'stage_report',icon:'▥',name:'阶段性学习报告',desc:'生成成功后保留报告，失败可按同一请求重试',cost:20,action:'生成报告'}]
const vipRows=[['基础学情诊断','✓ 支持','✓ 支持'],['每日练习生成','5 组 / 天','20 组 / 天'],['详细错因分析','10 积分 / 次','✓ 直接使用'],['学习历史记录','最近 10 条','✓ 全部记录'],['阶段性学情报告','20 积分 / 次','✓ 直接生成']]

function go(view){currentView.value=view;mobileMenu.value=false;if(route.name!==view)router.push({name:view});if(view==='points')loadPoints();if(view==='vip')loadVip()}
async function loadPoints(full=true){if(!isAuthed.value)return;try{if(full){const [account,tasks,transactions]=await Promise.all([getPointAccount(),getPointTasks(),getPointTransactions()]);Object.assign(pointAccount,account.data);pointTasks.value=tasks.data.items;pointTransactions.value=transactions.data.items}else{const account=await getPointAccount();Object.assign(pointAccount,account.data)}}catch(error){ElMessage.error(error.message||'积分数据加载失败')}}
async function loadVip(full=true){
  if(!isAuthed.value)return
  try{
    const requests=[getVipStatus(),getVipUsage()]
    if(full)requests.push(getVipOrders())
    const [status,usage,orders]=await Promise.all(requests)
    Object.assign(vipStatus,status.data)
    Object.assign(vipUsage,usage.data)
    if(full)vipOrders.value=orders?.data?.items||[]
  }catch(error){ElMessage.error(error.message||'会员数据加载失败')}
}
async function redeem(item){
  if(item.itemType==='detailed_analysis'){go('learn');ElMessage.info('完成练习后可在反馈区解锁详细错因');return}
  if(item.itemType==='stage_report'){go('reports');await generateReport();return}
  try{const payload=await exchangePoints(item.itemType);pointAccount.balance=payload.data.balance;ElMessage.success(`已兑换${item.name}`);await loadPoints()}catch(error){ElMessage.error(error.message||'积分兑换失败')}
}
async function completePointTask(task){if(task.task_type!=='daily_check_in'){go(task.task_type==='correction_reward'?'records':'learn');return}try{const payload=await checkIn();ElMessage.success(payload.data.awarded?'签到成功，获得 2 积分':'今天已经签到');await loadPoints()}catch(error){ElMessage.error(error.message||'签到失败')}}
function applyProfile(profile){
  profileSummary.value=profile||null
  if(!profile)return
  Object.assign(settings,{
    stage:stageLabels[profile.stage]||profile.stage,
    grade:profile.grade,
    subject:profile.subject,
    days:`${profile.weekly_study_days} 天`,
    target:`${profile.daily_target_groups} 组练习`,
  })
}
async function bootstrapProfile(){
  const payload=await getMyProfile()
  const profile=payload?.data?.profile||null
  applyProfile(profile)
  if(!profile){currentView.value='settings';return}
}
async function restoreSession(){const savedToken=getToken();if(!savedToken)return;token.value=savedToken;try{await Promise.all([loadPoints(false),loadVip(false),bootstrapProfile()]);await fetchHomeData()}catch{setToken('');token.value=''}}
async function submitAuth(){if(authForm.username.length<6||authForm.password.length<6){ElMessage.warning('用户名和密码都需要 6 到 20 位');return}if(authMode.value==='register'&&authForm.password!==authForm.confirmPassword){ElMessage.warning('两次输入的密码不一致');return}authLoading.value=true;try{if(authMode.value==='register'){const user=await register(authForm.username,authForm.password);if(user?.id)requestForm.userId=user.id;ElMessage.success('注册成功，请登录');authMode.value='login';authForm.password='';authForm.confirmPassword='';return}const payload=await login(authForm.username,authForm.password);token.value=payload.access_token;currentUsername.value=authForm.username;localStorage.setItem('question_set_username',authForm.username);await Promise.all([loadPoints(false),loadVip(false),bootstrapProfile()]);await fetchHomeData();ElMessage.success('登录成功，欢迎回来')}catch(error){ElMessage.error(error.message||'认证失败')}finally{authLoading.value=false}}
async function clearSession(){
  try{await clearSessionMemory(Number(requestForm.sessionId)||1)}catch(error){ElMessage.warning(error.message||'短期会话清除失败，已退出本地登录')}
  setToken('');token.value='';profileSummary.value=null;currentView.value='home';ElMessage.success('已清除当前会话并安全退出')
}
function learningStatusLabel(status){return {weak:'基础薄弱',consolidating:'正在巩固',mastered:'掌握良好'}[status]||status}
function difficultyLabel(value){return {easy:'简单',medium:'中等',hard:'困难'}[value]||value}
function clearPracticeAnswers(){Object.keys(practiceAnswers).forEach(key=>delete practiceAnswers[key])}
function resetLearning(){diagnosisResult.value=null;currentPractice.value=null;answerResult.value=null;entitlementError.value=false;recommendedSubject.value='';practiceRequestId.value='';answerRequestId.value='';detailedRequestId.value='';clearPracticeAnswers();requestForm.text=''}
async function startDiagnosis(){const content=requestForm.text.trim();if(!content)return;diagnosisLoading.value=true;entitlementError.value=false;currentPractice.value=null;answerResult.value=null;clearPracticeAnswers();try{const payload=await diagnose({session_id:Number(requestForm.sessionId)||null,input_type:learningInputType.value,content});diagnosisResult.value=payload.data;ElMessage.success(learningInputType.value==='learning_question'?'概念讲解已生成，看懂后可继续检测':'诊断完成，可以生成针对性练习')}catch(error){ElMessage.error(error.message||'学情诊断失败')}finally{diagnosisLoading.value=false}}
async function generatePractice(difficulty=null){if(!diagnosisResult.value)return;const selectedDifficulty=typeof difficulty==='string'?difficulty:null;const questionCount=learningInputType.value==='weakness'?4:3;if(!practiceRequestId.value)practiceRequestId.value=newRequestId();practiceLoading.value=true;entitlementError.value=false;try{const payload=await createPractice({diagnosis_id:diagnosisResult.value.diagnosis_id,question_count:questionCount,...(recommendedSubject.value?{subject:recommendedSubject.value}:{}),...(selectedDifficulty?{difficulty:selectedDifficulty}:{})},practiceRequestId.value);currentPractice.value=payload.data;answerResult.value=null;answerRequestId.value='';clearPracticeAnswers();practiceRequestId.value='';await loadVip()}catch(error){if(error.code==='USAGE_LIMIT_REACHED'||error.status===403){entitlementError.value=true}else{ElMessage.error(error.message||'练习生成失败，请重试')}}finally{practiceLoading.value=false}}
async function startRecommendation(item){
  if(!item){go('learn');return}
  if(item.type==='review'){
    mistakeKnowledgePoint.value=String(item.knowledge_point_name||'')
    mistakeInitialStatus.value='review_due'
    await router.push({name:'mistakes',query:{status:'review_due',...(mistakeKnowledgePoint.value?{kp:mistakeKnowledgePoint.value}:{})}})
    return
  }
  const recommendationSubject=String(item.subject||profileSummary.value?.subject||'')
  const targetKnowledgePoint=String(
    item.knowledge_point_name
    || `${profileSummary.value?.grade||''}${recommendationSubject||'当前学科'}随机巩固`
  )
  recommendationLoading.value=true
  resetLearning()
  learningInputType.value='weakness'
  recommendedSubject.value=recommendationSubject
  requestForm.text=item.knowledge_point_name
    ? `我需要巩固「${targetKnowledgePoint}」`
    : `请自动安排${recommendationSubject||'当前学科'}今日巩固训练`
  try{
    await router.push({name:'learn'})
    const payload=await diagnose({
      session_id:Number(requestForm.sessionId)||null,
      input_type:'weakness',
      content:requestForm.text,
      knowledge_point_name:targetKnowledgePoint,
    })
    diagnosisResult.value=payload.data
    await generatePractice()
    if(currentPractice.value)ElMessage.success(
      item.knowledge_point_name
        ? `已生成「${targetKnowledgePoint}」专项练习`
        : `已自动生成${recommendationSubject||'今日'}巩固训练`
    )
  }catch(error){
    ElMessage.error(error.message||'推荐练习生成失败，请重试')
  }finally{recommendationLoading.value=false}
}
function switchLearningType(value){if(learningInputType.value===value)return;learningInputType.value=value;resetLearning()}
async function exchangeExtraPractice(){if(pointAccount.balance<10){ElMessage.warning('积分不足，请先完成学习任务获取积分');return}exchangeLoading.value=true;try{await exchangePoints('extra_practice');await loadPoints();ElMessage.success('兑换成功，正在生成额外练习');await generatePractice()}catch(error){ElMessage.error(error.message||'额外练习兑换失败')}finally{exchangeLoading.value=false}}
async function submitPracticeAnswers(){if(!currentPractice.value||!allQuestionsAnswered.value)return;if(!answerRequestId.value)answerRequestId.value=newRequestId();answerLoading.value=true;try{const answers=currentPractice.value.questions.map(q=>({question_id:q.question_id,answer:String(practiceAnswers[q.question_id]).trim()}));const payload=await submitAnswers(currentPractice.value.practice_id,answers,answerRequestId.value);answerResult.value=payload.data;answerRequestId.value='';await Promise.all([loadPoints(),loadVip(),fetchHomeData()]);ElMessage.success('答案分析完成，学习数据已更新')}catch(error){ElMessage.error(error.message||'答案提交失败，请重试')}finally{answerLoading.value=false}}
async function loadDetailedAnalysis(){
  if(!currentPractice.value||!answerResult.value)return
  if(!detailedRequestId.value)detailedRequestId.value=newRequestId()
  detailedLoading.value=true
  try{
    const payload=await unlockDetailedAnalysis(currentPractice.value.practice_id,vipStatus.is_vip?'vip':'points',detailedRequestId.value)
    const details=new Map((payload.data.items||[]).map(item=>[item.question_id,item]))
    answerResult.value.results=answerResult.value.results.map(item=>({...item,...(details.get(item.question_id)||{})}))
    detailedRequestId.value=''
    await Promise.all([loadPoints(),loadVip()])
    ElMessage.success('详细错因分析已解锁')
  }catch(error){ElMessage.error(error.message||'详细错因分析解锁失败')}
  finally{detailedLoading.value=false}
}
async function practiceAgain(){const difficulty=answerResult.value?.next_difficulty||currentPractice.value?.difficulty;currentPractice.value=null;answerResult.value=null;detailedRequestId.value='';clearPracticeAnswers();practiceRequestId.value='';await generatePractice(difficulty)}
async function handleProfileSaved(profile){
  applyProfile(profile)
  go('home')
  await loadPoints()
  await fetchHomeData()
}
function practiceKnowledgePoint(name){requestForm.text=`我想针对${name}进行练习`;learningInputType.value='weakness';resetLearning();requestForm.text=`我想针对${name}进行练习`;go('learn')}
function openKnowledgeReview(target){
  const data=typeof target==='string'?{name:target}:target||{}
  if(!data.name){ElMessage.warning('请选择具体知识点');return}
  Object.assign(reviewTarget,{name:data.name,subject:data.subject||profileSummary.value?.subject||'',from:data.from||currentView.value||'profile'})
  sessionStorage.setItem('knowledge_review_target',JSON.stringify(reviewTarget))
  mobileMenu.value=false
  router.push({name:'knowledge-review',query:{kp:reviewTarget.name,subject:reviewTarget.subject,from:reviewTarget.from}})
}
function openRelatedMistakes(target){
  mistakeKnowledgePoint.value=String(target?.name||reviewTarget.name||'')
  mistakeInitialStatus.value='pending'
  router.push({name:'mistakes',query:mistakeKnowledgePoint.value?{kp:mistakeKnowledgePoint.value,status:'pending'}:undefined})
}
function clearMistakeFilter(){
  mistakeKnowledgePoint.value=''
  mistakeInitialStatus.value=''
  if(route.name==='mistakes')router.replace({name:'mistakes'})
}
async function refreshAfterCorrection(){await Promise.all([loadPoints(),fetchHomeData(),loadRecords(1)])}
async function startVipPayment(){if(!isAuthed.value){ElMessage.warning('请先登录');return}const paymentWindow=window.open('','_blank');if(!paymentWindow){ElMessage.warning('浏览器阻止了支付窗口，请允许本站弹出窗口');return}paymentWindow.document.write('<p style="font-family:sans-serif;padding:24px">正在跳转支付宝沙箱收银台…</p>');vipPayLoading.value=true;try{const orderPayload=await createVipOrder();const order=orderPayload.data;paymentState.status='paying';paymentState.orderNo=order.order_no;paymentState.message='支付窗口已打开，支付成功后系统会自动确认并开通 VIP';const formPayload=await createAlipayForm(order.order_no);paymentWindow.location.replace(formPayload.data.payment_url);await loadVip();void pollPaymentOrder(order.order_no);ElMessage.success('支付窗口已打开，请使用沙箱买家账号完成支付')}catch(error){paymentWindow.close();paymentState.status='failed';paymentState.message=error.message||'创建支付宝支付失败';ElMessage.error(paymentState.message)}finally{vipPayLoading.value=false}}
async function pollPaymentOrder(orderNo){
  for(let attempt=0;attempt<60;attempt+=1){
    await new Promise(resolve=>setTimeout(resolve,2000))
    if(!isAuthed.value||paymentState.orderNo!==orderNo)return
    try{
      const order=await refreshPaymentOrder(orderNo,{silent:true})
      if(['paid','closed'].includes(order.status))return
    }catch{
      // 临时网络错误不终止轮询，用户仍可通过订单旁按钮手动查单。
    }
  }
  if(paymentState.orderNo===orderNo&&paymentState.status==='paying'){
    paymentState.message='暂未自动确认到账，请点击订单旁“查询结果”继续查单'
  }
}
async function refreshPaymentOrder(orderNo,{silent=false}={}){
  paymentQuerying.value=orderNo
  try{
    const payload=await queryVipOrder(orderNo)
    const order=payload.data
    paymentState.status=order.status
    paymentState.orderNo=orderNo
    if(order.status==='paid'){
      Object.assign(vipStatus,{is_vip:true,expires_at:order.vip_expires_at})
      paymentState.message=`支付成功，VIP有效期至 ${new Date(order.vip_expires_at).toLocaleString()}`
      if(!silent)ElMessage.success(paymentState.message)
    }else if(order.status==='closed'){
      paymentState.message='订单已关闭，请重新创建订单'
      if(!silent)ElMessage.warning(paymentState.message)
    }else{
      paymentState.message='支付结果确认中；如已付款，请稍后再次查询'
      if(!silent)ElMessage.info(paymentState.message)
    }
    await loadVip()
    return order
  }catch(error){paymentState.status='failed';paymentState.message=error.message||'查询支付结果失败';if(!silent)ElMessage.error(paymentState.message);throw error}
  finally{paymentQuerying.value=''}
}
async function confirmReturnedPayment(){if(route.name!=='payment-result')return;currentView.value='vip';const orderNo=String(route.query.out_trade_no||'');if(!orderNo){paymentState.status='failed';paymentState.message='支付返回地址缺少订单号';return}if(!getToken()){paymentState.status='failed';paymentState.message='登录状态已失效，请重新登录后在订单列表查询';return}paymentState.status='paying';paymentState.orderNo=orderNo;paymentState.message='正在确认支付结果…';try{for(let attempt=0;attempt<15;attempt+=1){const order=await refreshPaymentOrder(orderNo,{silent:true});if(['paid','closed'].includes(order.status)){await router.replace({name:'vip'});return}await new Promise(resolve=>setTimeout(resolve,2000))}paymentState.message='支付结果仍在确认中，可以稍后点击订单旁的“查询结果”'}catch(error){ElMessage.error(paymentState.message)}}
onMounted(async()=>{await restoreSession();await confirmReturnedPayment()})
</script>

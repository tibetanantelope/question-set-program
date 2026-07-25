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
      <div class="goal-card"><div><span>今日目标</span><strong>{{ todayPlan.completed_groups }} / {{ todayPlan.target_groups }} 组</strong></div><div class="progress"><i :style="{width: (todayPlan.target_groups > 0 ? Math.round(todayPlan.completed_groups / todayPlan.target_groups * 100) : 0) + '%'}"></i></div><small>{{ todayPlan.completed ? '今日目标已完成 ✓' : '再完成 ' + (todayPlan.target_groups - todayPlan.completed_groups) + ' 组，获得 5 积分' }}</small></div>
      <button class="side-user" @click="go('settings')"><span class="avatar">林</span><span><strong>林小满</strong><small>初一 · 数学</small></span><b>›</b></button>
    </aside>

    <main class="main-shell">
      <header class="topbar">
        <button class="menu-btn" @click="mobileMenu = !mobileMenu">☰</button>
        <div><h1>{{ pageMeta.title }}</h1><p>{{ pageMeta.subtitle }}</p></div>
        <div class="top-actions">
          <button class="points-pill" @click="go('points')">◆ <strong>126</strong> 积分</button>
          <button class="notify" :class="{ hasUnread: unreadCount > 0 }" @click="toggleNotificationPanel">
            ♢
            <i v-if="unreadCount > 0">{{ unreadCount > 99 ? '99+' : unreadCount }}</i>
          </button>
          <span class="avatar small">林</span>
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
          <article class="hero"><div><span class="eyebrow">下午好，林小满</span><h2>今天从薄弱点开始，<br>把不会的真正弄懂</h2><p>根据你的学习画像，建议优先复习"一元一次方程 · 移项"。</p><div class="hero-actions"><button class="primary-btn" @click="go('learn')">开始智能学习 →</button><button class="ghost-btn" @click="go('records')">复习历史错题</button></div></div><div class="hero-art"><div class="book">∑<i></i></div><span class="orbit one"></span><span class="orbit two"></span><div class="mini-card a">今日正确率<br><strong>82%</strong></div><div class="mini-card b">连续学习<br><strong>6 天</strong></div></div></article>
          <div class="stats"><article><span class="stat-icon blue">◎</span><div><small>知识点掌握度</small><strong>72<em>%</em></strong><p class="up">较上周 +5%</p></div></article><article><span class="stat-icon green">✓</span><div><small>本周完成练习</small><strong>{{ statsSummary.practiceCount || 12 }}<em> 组</em></strong><p>累计 {{ statsSummary.questionCount || 43 }} 道题</p></div></article><article><span class="stat-icon orange">△</span><div><small>待复习错题</small><strong>8<em> 道</em></strong><p class="warn">3 道今日到期</p></div></article><article><span class="stat-icon purple">◆</span><div><small>当前积分</small><strong>126</strong><p class="up">本周获得 32</p></div></article></div>
          <div class="dashboard-grid">
            <article class="panel"><div class="panel-head"><div><h3>优先学习建议</h3><p>根据复习计划和近期表现生成</p></div><span class="priority">今日推荐</span></div>
          <div v-if="homeRecommendations.primary" class="recommend-card"><span class="subject-icon">{{ (homeRecommendations.primary.title || '练')[0] }}</span><div><small>{{ homeRecommendations.primary.type === 'review' ? '到期错题复习 · 优先级最高' : homeRecommendations.primary.priority === 2 ? '薄弱知识点巩固' : '推荐练习' }}</small><h3>{{ homeRecommendations.primary.title }}</h3><p>{{ homeRecommendations.primary.description || '' }}</p></div><button class="round-btn" @click="go('learn')">→</button></div>
          <div v-if="!homeRecommendations.primary" class="recommend-card"><span class="subject-icon">练</span><div><small>开始今天的学习</small><h3>从练习开始吧</h3><p>完成一组练习，系统会为你生成更精准的推荐。</p></div><button class="round-btn" @click="go('learn')">→</button></div>
          <div v-for="(item, idx) in (homeRecommendations.secondary || []).slice(0, 3)" :key="idx" class="knowledge-row"><span class="rank" :class="idx === 0 ? 'red' : 'amber'">{{ idx + 1 }}</span><div><strong>{{ item.title }}</strong><small>{{ item.description || '' }}</small></div><b></b><button @click="go('learn')">练习</button></div>
          <div v-if="(!homeRecommendations.secondary || homeRecommendations.secondary.length === 0)" class="knowledge-row"><span class="rank red">1</span><div><strong>去括号法则</strong><small>完成练习后自动更新推荐</small></div><b></b><button @click="go('learn')">练习</button></div></article>
            <article class="panel"><div class="panel-head"><div><h3>今日学习计划</h3><p>每天一点，进步看得见</p></div><b class="task-count">{{ todayPlan.completed_groups }} / {{ todayPlan.target_groups }}</b></div>
          <div v-for="(task, idx) in (todayPlan.tasks && todayPlan.tasks.length ? todayPlan.tasks : [])" :key="idx" :class="['task', { done: task.status === 'completed' }]"><span>{{ task.status === 'completed' ? '✓' : (idx + 1) }}</span><div><strong>{{ task.title }}</strong><small>{{ task.status === 'completed' ? '已完成' : '待完成' }}</small></div><em v-if="task.status === 'completed'">+5</em></div>
          <div v-if="!todayPlan.tasks || todayPlan.tasks.length === 0" class="task"><span>1</span><div><strong>完成一组推荐练习</strong><small>开始学习即可获得积分奖励</small></div><em>+5</em></div>
          <button class="soft-btn full" @click="go('learn')">{{ todayPlan.completed ? '今日目标已完成 ✓' : '继续完成今日计划' }}</button></article>
          </div>
        </section>

        <!-- 智能学习 -->
        <section v-else-if="currentView === 'learn'" class="view learn-view">
          <div class="steps"><span class="active"><b>1</b>描述问题</span><i></i><span><b>2</b>学情诊断</span><i></i><span><b>3</b>针对练习</span><i></i><span><b>4</b>分析反馈</span></div>
          <div class="learn-grid"><article class="panel ask-panel"><div class="ai-title"><span>AI</span><div><h2>今天想解决什么问题？</h2><p>输入不会的题目、学习问题或薄弱点，我会结合你的学习画像分析。</p></div></div><div class="context-chips"><span>初中</span><span>七年级</span><span>数学</span><button @click="go('settings')">修改</button></div><div class="input-tabs"><button class="active">描述薄弱点</button><button>输入题目</button><button>学习问题</button></div><textarea v-model="requestForm.text" placeholder="例如：我做一元一次方程时，经常在去括号和移项处出错……"></textarea><div class="quick"><small>试试这样问：</small><button v-for="prompt in quickPrompts" :key="prompt" @click="requestForm.text = prompt">{{ prompt }}</button></div><button class="primary-btn analyse-btn" :disabled="analysisLoading" @click="send(true)">{{ analysisLoading ? '正在分析…' : '开始智能分析 ✦' }}</button></article>
            <aside><article class="panel profile-mini"><div class="panel-head"><h3>当前学习画像</h3><button @click="go('profile')">查看详情</button></div><div class="profile-line"><span>数</span><div><strong>七年级数学</strong><small>薄弱点补习</small></div></div><div class="mini-mastery"><span>总体掌握度</span><strong>72%</strong></div><div class="knowledge-progress"><i style="width:72%"></i></div><p>近期高频错因：<b>计算错误</b></p></article><article class="panel usage"><div class="panel-head"><h3>今日使用</h3><span>普通用户</span></div><div><span>练习生成</span><strong>1 / 5</strong></div><div class="knowledge-progress"><i style="width:20%"></i></div><div><span>详细错因分析</span><strong>需 10 积分</strong></div><button class="vip-btn full" @click="go('vip')">♛ 升级 VIP 解锁更多</button></article></aside>
          </div>
          <article v-if="messages.length" class="panel result-panel"><div class="panel-head"><div><h3>智能分析结果</h3><p>来自当前后端 Agent 接口</p></div><button @click="messages = []">清空</button></div><div v-for="message in messages" :key="message.id" class="result-message" :class="message.role"><strong>{{ message.title }}</strong><pre>{{ message.content }}</pre></div></article>
        </section>

        <!-- 学习画像 -->
        <section v-else-if="currentView === 'profile'" class="view"><div class="profile-banner"><div><span class="avatar large">林</span><div><h2>林小满的学习画像</h2><p>初中 · 七年级 · 数学　学习目标：薄弱点补习</p><span>已连续学习 6 天</span></div></div><button class="white-btn" @click="go('settings')">编辑基础信息</button></div><div class="profile-cards"><article class="panel mastery-card"><div class="donut"><span><strong>72</strong><small>总体掌握度</small></span></div><div><h3>正在稳步提升</h3><p>本周掌握度提升 5%，继续保持当前节奏。</p><div class="legend"><span><i class="red-dot"></i>基础薄弱</span><span><i class="amber-dot"></i>正在巩固</span><span><i class="green-dot"></i>掌握良好</span></div></div></article><article class="panel trend"><div class="panel-head"><div><h3>掌握度趋势</h3><p>最近 7 次学习变化</p></div><b class="up">↗ +12%</b></div><div class="fake-chart"><span v-for="h in [35,42,39,55,61,68,76]" :key="h" :style="{height:h+'%'}"></span></div></article></div><article class="panel knowledge-table"><div class="panel-head"><div><h3>知识点掌握情况</h3><p>数据接口待学习画像模块完成后接入</p></div><div class="filters"><button class="active">全部</button><button>薄弱</button><button>巩固中</button></div></div><div class="table-row head"><span>知识点</span><span>掌握度</span><span>学习状态</span><span>答题统计</span><span>最近学习</span><span></span></div><div v-for="item in knowledgeItems" :key="item.name" class="table-row"><span><b>{{ item.name }}</b><small>{{ item.chapter }}</small></span><span><div class="knowledge-progress"><i :style="{width:item.score+'%'}"></i></div><b>{{ item.score }}%</b></span><span><em :class="item.type">{{ item.status }}</em></span><span>{{ item.correct }} / {{ item.total }}</span><span>{{ item.date }}</span><button @click="go('learn')">去练习</button></div></article></section>

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
            <div v-if="recordsLoading" class="notify-loading">加载中…</div>
            <template v-else>
              <template v-for="record in timelineRecords" :key="record.record_id">
                <div v-if="showDateLabel(record.occurred_at)" class="date-label">{{ formatDateLabel(record.occurred_at) }}</div>
                <div class="record">
                  <time>{{ (record.occurred_at || '').slice(11, 16) }}</time>
                  <span class="record-dot"></span>
                  <div>
                    <span class="subject-icon small-icon">{{ recordTypeIcon(record.record_type) }}</span>
                    <div>
                      <b>{{ record.title }}</b>
                      <p>
                        {{ record.question_count ? record.question_count + ' 道题' : '' }}
                        {{ record.subject ? ' · ' + record.subject : '' }}
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
                <span :class="(selectedReport.accuracy || 0) >= 80 ? 'up' : (selectedReport.accuracy || 0) < 60 ? 'warn' : ''" style="font-size:28px;font-weight:700">{{ Math.round(selectedReport.accuracy || 0) }}%</span>
              </div>
              <div class="stats" style="margin:20px 0">
                <article><span class="stat-icon blue">◎</span><div><small>练习次数</small><strong>{{ selectedReport.practice_count }}<em> 次</em></strong></div></article>
                <article><span class="stat-icon green">✓</span><div><small>完成题目</small><strong>{{ selectedReport.question_count }}<em> 道</em></strong></div></article>
                <article><span class="stat-icon orange">△</span><div><small>掌握度变化</small><strong :class="selectedReport.mastery_change >= 0 ? 'up' : 'warn'">{{ selectedReport.mastery_change >= 0 ? '+' : '' }}{{ selectedReport.mastery_change }}<em>%</em></strong></div></article>
                <article v-if="selectedReport.frequent_error_type"><span class="stat-icon red-soft">!</span><div><small>高频错因</small><strong>{{ errorTypeLabel(selectedReport.frequent_error_type) }}</strong></div></article>
              </div>
              <div v-if="selectedReport.weak_points && selectedReport.weak_points.length > 0" class="report-section">
                <h4>薄弱知识点</h4>
                <div class="weak-tags">
                  <span v-for="wp in selectedReport.weak_points" :key="wp" class="weak-tag">{{ wp }}</span>
                </div>
              </div>
              <div v-if="selectedReport.suggestion" class="report-section suggestion">
                <h4>学习建议</h4>
                <p>{{ selectedReport.suggestion }}</p>
              </div>
            </article>
          </div>
        </section>

        <!-- 积分中心 -->
        <section v-else-if="currentView === 'points'" class="view"><div class="points-hero"><div><span>当前可用积分</span><strong>126 <small>◆</small></strong><p>坚持有效学习，让每一次进步都有回报</p></div><div class="points-stats"><span><small>本周获得</small><b>+32</b></span><span><small>累计获得</small><b>468</b></span></div><div class="coins">◆</div></div><div class="two-col"><article class="panel"><div class="panel-head"><div><h3>每日学习任务</h3><p>完成任务即可获得积分</p></div><span class="task-count">今日 2 / 3</span></div><div class="mission done"><span>✓</span><div><b>每日首次登录</b><small>每天登录即可完成</small></div><em>+2</em><button disabled>已领取</button></div><div class="mission"><span>练</span><div><b>再完成一组有效练习</b><small>今日最多奖励 3 组</small></div><em>+5</em><button @click="go('learn')">去完成</button></div><div class="mission"><span>订</span><div><b>完成一道错题订正</b><small>首次订正成功后获得</small></div><em>+3</em><button @click="go('records')">去订正</button></div></article><article class="panel streak"><div class="panel-head"><div><h3>连续学习</h3><p>已坚持学习</p></div><strong>6 天</strong></div><div class="week"><span v-for="day in ['一','二','三','四','五','六','日']" :key="day" :class="{ checked: day !== '日' }">{{ day }}<b>{{ day !== '日' ? '✓' : '7/21' }}</b></span></div><p>明天继续学习，可获得连续三天奖励 ◆10</p></article></div><article class="panel exchange"><div class="panel-head"><div><h3>积分兑换</h3><p>普通用户也能体验高级学习能力</p></div><span>余额 126</span></div><div class="exchange-grid"><div v-for="item in exchanges" :key="item.name"><span>{{ item.icon }}</span><div><h4>{{ item.name }}</h4><p>{{ item.desc }}</p></div><b>◆ {{ item.cost }}</b><button @click="placeholder(item.name)">立即兑换</button></div></div></article></section>

        <!-- 会员中心 -->
        <section v-else-if="currentView === 'vip'" class="view"><div class="vip-hero"><div><span>智学伴 VIP</span><h2>让每一次学习，都更懂你</h2><p>解锁更深入的错因分析、更完整的学习画像和更持续的个性化服务。</p><div><b>✓ 更多针对性练习</b><b>✓ 完整学情报告</b><b>✓ 详细错因分析</b></div></div><div class="vip-card"><small>♛ ZHIXUEBAN</small><strong>VIP</strong><span>专属个性化学习服务</span></div></div><article class="panel compare"><div class="panel-head centered"><div><h2>选择适合你的学习方式</h2><p>基础学习始终开放，VIP 提供更深入的服务</p></div></div><div class="compare-row head"><span>功能权益</span><b>普通用户</b><b>♛ VIP 用户</b></div><div v-for="row in vipRows" :key="row[0]" class="compare-row"><span>{{ row[0] }}</span><b>{{ row[1] }}</b><b>{{ row[2] }}</b></div></article><article class="plan-card"><span class="recommend-label">推荐套餐</span><div><h3>30 天 VIP 会员</h3><p>通过支付宝沙箱体验完整支付和开通流程</p></div><strong>¥ <b>19</b>.9</strong><ul><li>每日 20 组智能练习</li><li>详细错因分析</li><li>完整历史记录</li><li>阶段性学情报告</li></ul><button class="gold-btn" @click="placeholder('支付宝沙箱支付接口')">使用支付宝沙箱支付</button><small>支付接口已预留，待会员服务与支付宝沙箱配置完成后接入</small></article></section>

        <!-- 设置 -->
        <section v-else class="view"><article class="panel settings"><div class="settings-title"><span>⚙</span><div><h2>基础信息设置</h2><p>完善信息，让诊断和练习更适合你</p></div></div><form @submit.prevent="saveSettings"><label>当前学段<div class="segments"><button type="button" v-for="stage in ['小学','初中','高中','大学']" :key="stage" :class="{active:settings.stage===stage}" @click="settings.stage=stage">{{ stage }}</button></div></label><div class="form-grid"><label>年级<select v-model="settings.grade"><option>七年级</option><option>八年级</option><option>九年级</option></select></label><label>学科或课程<select v-model="settings.subject"><option>数学</option><option>语文</option><option>英语</option></select></label></div><div class="book-tip">✓ 中小学阶段默认按照人教版控制学习范围</div><label>学习目标<div class="segments goals"><button type="button" v-for="goal in ['日常巩固','薄弱点补习','考试复习']" :key="goal" :class="{active:settings.goal===goal}" @click="settings.goal=goal">{{ goal }}</button></div></label><div class="form-grid"><label>每周学习天数<select v-model="settings.days"><option>3 天</option><option>5 天</option><option>7 天</option></select></label><label>每日目标<select v-model="settings.target"><option>1 组练习</option><option>3 组练习</option><option>5 组练习</option></select></label></div><div class="settings-actions"><button type="button" class="danger-link" @click="clearSession">退出登录</button><button class="primary-btn">保存设置</button></div></form></article></section>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { analyseStream, getToken, login, register, setToken } from './api'
import { getRecords as fetchRecordsApi, getRecordsStats, getHomeRecommendations, getTodayPlan, getNotifications, getUnreadCount, markNotificationRead, markAllNotificationsRead } from './api/records'
import { getReports, generateStageReport, getReportDetail } from './api/reports'

const authMode=ref('login'), authLoading=ref(false), analysisLoading=ref(false), token=ref(getToken()), currentView=ref('home'), mobileMenu=ref(false), messages=ref([])
const authForm=reactive({username:'',password:'',confirmPassword:''})
const requestForm=reactive({userId:1,sessionId:1,text:''})
const settings=reactive({stage:'初中',grade:'七年级',subject:'数学',goal:'薄弱点补习',days:'5 天',target:'3 组练习'})
const isAuthed=computed(()=>Boolean(token.value))
const navItems=computed(()=>[
  {key:'home',label:'学习首页',icon:'⌂',group:'学习空间',badge:null},
  {key:'learn',label:'智能学习',icon:'✦',badge:null},
  {key:'profile',label:'学习画像',icon:'◎',badge:null},
  {key:'records',label:'学习记录',icon:'▤',badge:null},
  {key:'reports',label:'学情报告',icon:'📊',badge:null},
  {key:'points',label:'积分中心',icon:'◆',group:'成长与权益',badge:null},
  {key:'vip',label:'会员中心',icon:'♛',badge:null},
  {key:'settings',label:'基础信息设置',icon:'⚙',group:'个人设置',badge:null}
])
const metas={home:['学习首页','下午好，继续保持今天的学习节奏吧'],learn:['智能学习','描述你的问题，智学伴会为你诊断并生成针对性练习'],profile:['学习画像','了解每个知识点的掌握情况和成长趋势'],records:['学习记录','回顾每一次练习和进步'],reports:['学情报告','查看阶段性的学习分析和建议'],points:['积分中心','坚持有效学习，用积分兑换更多学习能力'],vip:['会员中心','解锁更深入、更持续的个性化学习服务'],settings:['基础信息设置','完善信息，让学习内容更适合你']}
const pageMeta=computed(()=>{
  const meta=metas[currentView.value]
  return meta?{title:meta[0],subtitle:meta[1]}:{title:currentView.value,subtitle:''}
})
const quickPrompts=['移项时为什么要变号？','我总在去括号时出错','帮我复习一元一次方程']
const knowledgeItems=[{name:'一元一次方程 · 移项',chapter:'第三章 一元一次方程',score:55,status:'基础薄弱',type:'weak',correct:5,total:12,date:'今天'},{name:'去括号法则',chapter:'第二章 整式的加减',score:63,status:'正在巩固',type:'medium',correct:8,total:13,date:'昨天'},{name:'有理数乘除法',chapter:'第一章 有理数',score:86,status:'掌握良好',type:'good',correct:18,total:21,date:'7月18日'}]
const exchanges=[{icon:'＋',name:'额外一组练习',desc:'突破普通用户每日次数限制',cost:10},{icon:'⌕',name:'详细错因分析',desc:'获得更深入的错误原因说明',cost:10},{icon:'▥',name:'阶段性学习报告',desc:'总结近期表现与学习建议',cost:20}]
const vipRows=[['基础学情诊断','✓ 支持','✓ 支持'],['每日练习生成','5 组 / 天','20 组 / 天'],['详细错因分析','10 积分 / 次','✓ 直接使用'],['学习历史记录','最近 10 条','✓ 全部记录'],['阶段性学情报告','20 积分 / 次','✓ 直接生成']]

// ── 成员四：真实 API 数据状态 ──
const homeRecommendations = ref({ primary: null, secondary: [] })
const todayPlan = ref({ date: '', target_groups: 3, completed_groups: 0, completed: false, tasks: [] })
const timelineRecords = ref([])
const timelineTotal = ref(0)
const statsSummary = ref({ practiceCount: 0, questionCount: 0, avgAccuracy: 0, masteryChange: 0 })
const reportList = ref([])
const reportLoading = ref(false)
const recordsLoading = ref(false)
const recordsPage = ref(1)
const recordsPages = ref(1)
const recordsFilter = ref('all')
const reportsLoading = ref(false)
const reportsPage = ref(1)
const reportsPages = ref(1)
const selectedReport = ref(null)

// ── 通知状态 ──
const showNotificationPanel = ref(false)
const notificationList = ref([])
const notificationLoading = ref(false)
const unreadCount = ref(0)

// ── 成员四：API 数据获取 ──
async function fetchHomeData() {
  try {
    const [recRes, planRes] = await Promise.all([
      getHomeRecommendations(),
      getTodayPlan(),
    ])
    if (recRes?.data) homeRecommendations.value = recRes.data
    if (planRes?.data) todayPlan.value = planRes.data
  } catch (e) { /* 静默降级 */ }
}

async function loadRecords(page = 1) {
  recordsLoading.value = true
  recordsPage.value = page
  const params = { page, page_size: 20 }
  if (recordsFilter.value !== 'all') params.type = recordsFilter.value
  try {
    const res = await fetchRecordsApi(params)
    if (res?.data) {
      timelineRecords.value = res.data.items || []
      timelineTotal.value = res.data.total || 0
      recordsPages.value = res.data.pages || 1
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
    }
  } catch (e) {
    ElMessage.warning(e.message || '获取报告详情失败')
  }
}

async function generateReport() {
  reportLoading.value = true
  try {
    const today = new Date()
    const weekAgo = new Date(today.getTime() - 7 * 86400000)
    const fmt = d => d.toISOString().slice(0, 10)
    const res = await generateStageReport({
      date_from: fmt(weekAgo),
      date_to: fmt(today),
      payment_method: 'vip',
    })
    if (res?.data) {
      ElMessage.success('报告生成成功')
      reportList.value.unshift(res.data)
      selectedReport.value = res.data
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

let lastDateLabel = ''
function showDateLabel(dateStr) {
  if (!dateStr) return false
  const d = dateStr.slice(0, 10)
  if (d !== lastDateLabel) {
    lastDateLabel = d
    return true
  }
  return false
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
  if (view === 'home') fetchHomeData()
  if (view === 'records') loadRecords()
  if (view === 'reports') loadReports()
  showNotificationPanel.value = false
  selectedReport.value = null
  lastDateLabel = ''
})

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

function go(view){currentView.value=view;mobileMenu.value=false;window.scrollTo({top:0,behavior:'smooth'})}
async function submitAuth(){if(authForm.username.length<6||authForm.password.length<6){ElMessage.warning('用户名和密码都需要 6 到 20 位');return}if(authMode.value==='register'&&authForm.password!==authForm.confirmPassword){ElMessage.warning('两次输入的密码不一致');return}authLoading.value=true;try{if(authMode.value==='register'){const user=await register(authForm.username,authForm.password);if(user?.id)requestForm.userId=user.id;ElMessage.success('注册成功，请登录');authMode.value='login';authForm.password='';authForm.confirmPassword='';return}const payload=await login(authForm.username,authForm.password);token.value=payload.access_token;ElMessage.success('登录成功，欢迎回来')}catch(error){ElMessage.error(error.message||'认证失败')}finally{authLoading.value=false}}
function clearSession(){setToken('');token.value='';currentView.value='home';ElMessage.success('已安全退出')}
function addMessage(role,content,title=role==='assistant'?'智学伴 AI':'你'){const msg={id:`${Date.now()}-${Math.random()}`,role,title,content};messages.value.push(msg);return msg}
async function send(){const text=requestForm.text.trim();if(!text){ElMessage.warning('先描述你想解决的学习问题');return}addMessage('user',text);requestForm.text='';analysisLoading.value=true;const reply=addMessage('assistant','','智学伴 AI');try{await analyseStream({userId:requestForm.userId,sessionId:requestForm.sessionId,text,onEvent(event){if(event.type==='result'||event.type==='raw')reply.content+=event.content||'';if(event.type==='thinking'&&event.thought)reply.content+=`${event.thought}\n`;if(event.type==='observation')reply.content+=`${event.content}\n`}});if(!reply.content)reply.content='分析已完成，后端暂未返回可展示内容。'}catch(error){reply.content=error.message||'请求失败';ElMessage.error(reply.content)}finally{analysisLoading.value=false}}
function placeholder(name){ElMessage.info(`${name}页面与接口位置已预留，等待后端服务接入`)}
function saveSettings(){ElMessage.success('基础信息已保存（接口待接入）')}
</script>

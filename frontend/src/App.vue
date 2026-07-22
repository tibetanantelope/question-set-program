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
          <button :class="{ active: currentView === item.key }" @click="go(item.key)"><span>{{ item.icon }}</span>{{ item.label }}<i v-if="item.badge">{{ item.badge }}</i></button>
        </template>
      </nav>
      <div class="goal-card"><div><span>今日目标</span><strong>0 / {{ realProfile?.daily_target_groups || 3 }} 组</strong></div><div class="progress"><i style="width:0%"></i></div><small>完善信息后开始今天的学习</small></div>
      <button class="side-user" @click="go('settings')"><span class="avatar">{{ (realProfile?.stage ? stageMap[realProfile.stage] || '学' : '学')[0] }}</span><span><strong>{{ realProfile?.grade || '完善信息' }}</strong><small>{{ realProfile?.stage ? (stageMap[realProfile.stage]||'') + ' · ' + (realProfile?.subject||'') : '点击设置学习信息' }}</small></span><b>›</b></button>
    </aside>

    <main class="main-shell">
      <header class="topbar">
        <button class="menu-btn" @click="mobileMenu = !mobileMenu">☰</button>
        <div><h1>{{ pageMeta.title }}</h1><p>{{ pageMeta.subtitle }}</p></div>
        <div class="top-actions"><button class="points-pill" @click="go('points')">◆ <strong>126</strong> 积分</button><button class="notify">♢<i></i></button><span class="avatar small">{{ realProfile?.grade?.[0] || authForm.username?.[0] || '我' }}</span></div>
      </header>

      <div class="content">
        <section v-if="currentView === 'home'" class="view">
          <article class="hero"><div><span class="eyebrow">{{ realProfile ? '下午好，' + (realProfile.grade||'同学') : '下午好，同学' }}</span><h2>今天从薄弱点开始，<br>把不会的真正弄懂</h2><p>根据你的学习画像，建议优先复习“一元一次方程 · 移项”。</p><div class="hero-actions"><button class="primary-btn" @click="go('learn')">开始智能学习 →</button><button class="ghost-btn" @click="go('records')">复习历史错题</button></div></div><div class="hero-art"><div class="book">∑<i></i></div><span class="orbit one"></span><span class="orbit two"></span><div class="mini-card a">今日正确率<br><strong>82%</strong></div><div class="mini-card b">连续学习<br><strong>6 天</strong></div></div></article>
          <div class="stats"><article><span class="stat-icon blue">◎</span><div><small>知识点掌握度</small><strong>72<em>%</em></strong><p class="up">较上周 +5%</p></div></article><article><span class="stat-icon green">✓</span><div><small>本周完成练习</small><strong>12<em> 组</em></strong><p>累计 43 道题</p></div></article><article><span class="stat-icon orange">△</span><div><small>待复习错题</small><strong>8<em> 道</em></strong><p class="warn">3 道今日到期</p></div></article><article><span class="stat-icon purple">◆</span><div><small>当前积分</small><strong>126</strong><p class="up">本周获得 32</p></div></article></div>
          <div class="dashboard-grid">
            <article class="panel"><div class="panel-head"><div><h3>优先学习建议</h3><p>根据复习计划和近期表现生成</p></div><span class="priority">今日推荐</span></div><div class="recommend-card"><span class="subject-icon">数</span><div><small>到期错题复习 · 优先级最高</small><h3>一元一次方程 · 移项</h3><p>你在符号变化上连续出错 2 次，建议完成一组基础巩固。</p><div class="knowledge-progress"><i style="width:55%"></i></div></div><button class="round-btn" @click="go('learn')">→</button></div><div class="knowledge-row"><span class="rank red">1</span><div><strong>去括号法则</strong><small>计算错误较多</small></div><b>48%</b><button @click="go('learn')">练习</button></div><div class="knowledge-row"><span class="rank amber">2</span><div><strong>整式的加减</strong><small>需要继续巩固</small></div><b>63%</b><button @click="go('learn')">练习</button></div></article>
            <article class="panel"><div class="panel-head"><div><h3>今日学习计划</h3><p>每天一点，进步看得见</p></div><b class="task-count">2 / 3</b></div><div class="task done"><span>✓</span><div><strong>完成一组移项专项练习</strong><small>今天 09:24 完成</small></div><em>+5</em></div><div class="task done"><span>✓</span><div><strong>订正 2 道历史错题</strong><small>今天 12:10 完成</small></div><em>+6</em></div><div class="task"><span></span><div><strong>完成一组推荐练习</strong><small>预计用时 8 分钟</small></div><em>+5</em></div><button class="soft-btn full" @click="go('learn')">继续完成今日计划</button></article>
          </div>
        </section>

        <section v-else-if="currentView === 'learn'" class="view learn-view">
          <div class="steps"><span class="active"><b>1</b>描述问题</span><i></i><span><b>2</b>学情诊断</span><i></i><span><b>3</b>针对练习</span><i></i><span><b>4</b>分析反馈</span></div>
          <div class="learn-grid"><article class="panel ask-panel"><div class="ai-title"><span>AI</span><div><h2>今天想解决什么问题？</h2><p>输入不会的题目、学习问题或薄弱点，我会结合你的学习画像分析。</p></div></div><div class="context-chips"><span>{{ realProfile?.stage ? stageMap[realProfile.stage]||'未设置' : '未设置' }}</span><span>{{ realProfile?.grade||'未设置' }}</span><span>{{ realProfile?.subject||'未设置' }}</span><button @click="go('settings')">修改</button></div><div class="input-tabs"><button class="active">描述薄弱点</button><button>输入题目</button><button>学习问题</button></div><textarea v-model="requestForm.text" placeholder="例如：我做一元一次方程时，经常在去括号和移项处出错……"></textarea><div class="quick"><small>试试这样问：</small><button v-for="prompt in quickPrompts" :key="prompt" @click="requestForm.text = prompt">{{ prompt }}</button></div><button class="primary-btn analyse-btn" :disabled="analysisLoading" @click="send(true)">{{ analysisLoading ? '正在分析…' : '开始智能分析 ✦' }}</button></article>
            <aside><article class="panel profile-mini"><div class="panel-head"><h3>当前学习画像</h3><button @click="go('profile')">查看详情</button></div><div class="profile-line"><span>数</span><div><strong>七年级数学</strong><small>薄弱点补习</small></div></div><div class="mini-mastery"><span>总体掌握度</span><strong>72%</strong></div><div class="knowledge-progress"><i style="width:72%"></i></div><p>近期高频错因：<b>计算错误</b></p></article><article class="panel usage"><div class="panel-head"><h3>今日使用</h3><span>普通用户</span></div><div><span>练习生成</span><strong>1 / 5</strong></div><div class="knowledge-progress"><i style="width:20%"></i></div><div><span>详细错因分析</span><strong>需 10 积分</strong></div><button class="vip-btn full" @click="go('vip')">♛ 升级 VIP 解锁更多</button></article></aside>
          </div>
          <article v-if="messages.length" class="panel result-panel"><div class="panel-head"><div><h3>智能分析结果</h3><p>来自当前后端 Agent 接口</p></div><button @click="messages = []">清空</button></div><div v-for="message in messages" :key="message.id" class="result-message" :class="message.role"><strong>{{ message.title }}</strong><pre>{{ message.content }}</pre></div></article>
        </section>

        <section v-else-if="currentView === 'profile'" class="view"><div class="profile-banner"><div><span class="avatar large">林</span><div><h2>{{ realProfile?.grade || '我' }}的学习画像</h2><p>{{ realProfile?.stage ? stageMap[realProfile.stage]||'' : '' }} · {{ realProfile?.grade||'' }} · {{ realProfile?.subject||'' }}　学习目标：{{ realProfile?.learning_goal ? goalMap[realProfile.learning_goal] : '' }}</p><span>已连续学习 6 天</span></div></div><button class="white-btn" @click="go('settings')">编辑基础信息</button></div><div class="profile-cards"><article class="panel mastery-card"><div class="donut"><span><strong>72</strong><small>总体掌握度</small></span></div><div><h3>正在稳步提升</h3><p>本周掌握度提升 5%，继续保持当前节奏。</p><div class="legend"><span><i class="red-dot"></i>基础薄弱</span><span><i class="amber-dot"></i>正在巩固</span><span><i class="green-dot"></i>掌握良好</span></div></div></article><article class="panel trend"><div class="panel-head"><div><h3>掌握度趋势</h3><p>最近 7 次学习变化</p></div><b class="up">↗ +12%</b></div><div class="fake-chart"><span v-for="h in [35,42,39,55,61,68,76]" :key="h" :style="{height:h+'%'}"></span></div></article></div><article class="panel knowledge-table"><div class="panel-head"><div><h3>知识点掌握情况</h3><p>数据接口待学习画像模块完成后接入</p></div><div class="filters"><button class="active">全部</button><button>薄弱</button><button>巩固中</button></div></div><div class="table-row head"><span>知识点</span><span>掌握度</span><span>学习状态</span><span>答题统计</span><span>最近学习</span><span></span></div><div v-for="item in knowledgeItems" :key="item.name" class="table-row"><span><b>{{ item.name }}</b><small>{{ item.chapter }}</small></span><span><div class="knowledge-progress"><i :style="{width:item.score+'%'}"></i></div><b>{{ item.score }}%</b></span><span><em :class="item.type">{{ item.status }}</em></span><span>{{ item.correct }} / {{ item.total }}</span><span>{{ item.date }}</span><button @click="go('learn')">去练习</button></div></article></section>

        <section v-else-if="currentView === 'records'" class="view"><div class="summary"><div><span>本周练习</span><strong>12<small> 组</small></strong></div><div><span>完成题目</span><strong>43<small> 道</small></strong></div><div><span>平均正确率</span><strong class="up">82<small>%</small></strong></div><div><span>掌握度变化</span><strong class="up">+5<small>%</small></strong></div></div><article class="panel record-panel"><div class="panel-head"><div><h3>学习时间线</h3><p>练习、诊断和订正记录将在这里统一呈现</p></div><div class="filters"><button class="active">全部记录</button><button>专项练习</button><button>错题订正</button></div></div><div class="date-label">今天 · 7月20日</div><div v-for="record in records" :key="record.title" class="record"><time>{{ record.time }}</time><span class="record-dot"></span><div><span class="subject-icon small-icon">{{ record.icon }}</span><div><b>{{ record.title }}</b><p>{{ record.desc }}</p></div><strong :class="record.good ? 'up' : 'warn'">{{ record.result }}</strong><button>查看详情</button></div></div></article><article class="report-banner"><span>▥</span><div><small>阶段性学情报告</small><h3>生成你的本周学习报告</h3><p>总结掌握度变化、高频错因和下一阶段建议。</p></div><b>普通用户需<br>◆ 20 积分</b><button class="primary-btn" @click="placeholder('学习报告')">生成报告</button></article></section>

        <section v-else-if="currentView === 'points'" class="view"><div class="points-hero"><div><span>当前可用积分</span><strong>126 <small>◆</small></strong><p>坚持有效学习，让每一次进步都有回报</p></div><div class="points-stats"><span><small>本周获得</small><b>+32</b></span><span><small>累计获得</small><b>468</b></span></div><div class="coins">◆</div></div><div class="two-col"><article class="panel"><div class="panel-head"><div><h3>每日学习任务</h3><p>完成任务即可获得积分</p></div><span class="task-count">今日 2 / 3</span></div><div class="mission done"><span>✓</span><div><b>每日首次登录</b><small>每天登录即可完成</small></div><em>+2</em><button disabled>已领取</button></div><div class="mission"><span>练</span><div><b>再完成一组有效练习</b><small>今日最多奖励 3 组</small></div><em>+5</em><button @click="go('learn')">去完成</button></div><div class="mission"><span>订</span><div><b>完成一道错题订正</b><small>首次订正成功后获得</small></div><em>+3</em><button @click="go('records')">去订正</button></div></article><article class="panel streak"><div class="panel-head"><div><h3>连续学习</h3><p>已坚持学习</p></div><strong>6 天</strong></div><div class="week"><span v-for="day in ['一','二','三','四','五','六','日']" :key="day" :class="{ checked: day !== '日' }">{{ day }}<b>{{ day !== '日' ? '✓' : '7/21' }}</b></span></div><p>明天继续学习，可获得连续三天奖励 ◆10</p></article></div><article class="panel exchange"><div class="panel-head"><div><h3>积分兑换</h3><p>普通用户也能体验高级学习能力</p></div><span>余额 126</span></div><div class="exchange-grid"><div v-for="item in exchanges" :key="item.name"><span>{{ item.icon }}</span><div><h4>{{ item.name }}</h4><p>{{ item.desc }}</p></div><b>◆ {{ item.cost }}</b><button @click="placeholder(item.name)">立即兑换</button></div></div></article></section>

        <section v-else-if="currentView === 'vip'" class="view"><div class="vip-hero"><div><span>智学伴 VIP</span><h2>让每一次学习，都更懂你</h2><p>解锁更深入的错因分析、更完整的学习画像和更持续的个性化服务。</p><div><b>✓ 更多针对性练习</b><b>✓ 完整学情报告</b><b>✓ 详细错因分析</b></div></div><div class="vip-card"><small>♛ ZHIXUEBAN</small><strong>VIP</strong><span>专属个性化学习服务</span></div></div><article class="panel compare"><div class="panel-head centered"><div><h2>选择适合你的学习方式</h2><p>基础学习始终开放，VIP 提供更深入的服务</p></div></div><div class="compare-row head"><span>功能权益</span><b>普通用户</b><b>♛ VIP 用户</b></div><div v-for="row in vipRows" :key="row[0]" class="compare-row"><span>{{ row[0] }}</span><b>{{ row[1] }}</b><b>{{ row[2] }}</b></div></article><article class="plan-card"><span class="recommend-label">推荐套餐</span><div><h3>30 天 VIP 会员</h3><p>通过支付宝沙箱体验完整支付和开通流程</p></div><strong>¥ <b>19</b>.9</strong><ul><li>每日 20 组智能练习</li><li>详细错因分析</li><li>完整历史记录</li><li>阶段性学情报告</li></ul><button class="gold-btn" @click="placeholder('支付宝沙箱支付接口')">使用支付宝沙箱支付</button><small>支付接口已预留，待会员服务与支付宝沙箱配置完成后接入</small></article></section>

        <section v-else class="view"><article class="panel settings"><div class="settings-title"><span>⚙</span><div><h2>基础信息设置</h2><p>完善信息，让诊断和练习更适合你</p></div></div><form @submit.prevent="saveSettings"><label>当前学段<div class="segments"><button type="button" v-for="stage in ['小学','初中','高中','大学']" :key="stage" :class="{active:settings.stage===stage}" @click="onStageChange(stage)">{{ stage }}</button></div></label><div class="form-grid"><label>年级<select v-model="settings.grade"><option value="" disabled>请选择年级</option><option v-for="g in currentGrades" :key="g" :value="g">{{ g }}</option></select></label><label>学科或课程<select v-model="settings.subject"><option value="" disabled>请选择学科</option><option v-for="s in currentSubjects" :key="s" :value="s">{{ s }}</option></select></label></div><div class="book-tip">✓ 中小学阶段默认按照人教版控制学习范围</div><label>学习目标<div class="segments goals"><button type="button" v-for="goal in ['日常巩固','薄弱点补习','考试复习']" :key="goal" :class="{active:settings.goal===goal}" @click="settings.goal=goal">{{ goal }}</button></div></label><div class="form-grid"><label>每周学习天数<select v-model="settings.days"><option :value="3">3 天</option><option :value="5">5 天</option><option :value="7">7 天</option></select></label><label>每日目标<select v-model="settings.target"><option :value="1">1 组练习</option><option :value="3">3 组练习</option><option :value="5">5 组练习</option></select></label></div><div class="settings-actions"><button type="button" class="danger-link" @click="clearSession">退出登录</button><button type="submit" class="primary-btn">保存设置</button></div></form>

<div v-if="profileLoaded && diagnostic.status" class="diagnostic-section" style="margin-top:24px">
  <div style="border-top:1px solid var(--border-color);padding-top:24px">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
      <span style="font-size:24px">📝</span>
      <div><h2 style="margin:0;font-size:18px">首次诊断</h2>
      <p style="margin:4px 0 0;color:var(--text-secondary);font-size:14px">完成 5 道诊断题帮助系统了解你的当前水平</p></div>
    </div>

    <div v-if="diagnostic.status==='required'||diagnostic.status==='skipped'" style="padding:20px;background:var(--bg-secondary);border-radius:12px;text-align:center">
      <p style="margin:0 0 12px;color:var(--text-secondary)">{{ diagnostic.status==='skipped'?'你已跳过诊断，可重新开始':'建议先完成诊断，让练习更有针对性' }}</p>
      <div style="display:flex;gap:12px;justify-content:center">
        <button class="primary-btn" :disabled="diagnostic.loading" @click="startDiagnosticFlow">{{ diagnostic.loading?'生成中…':'开始诊断（5 道题）' }}</button>
        <button class="ghost-btn" :disabled="diagnostic.loading" @click="skipDiagnosticFlow">{{ diagnostic.loading?'处理中…':'跳过诊断' }}</button>
      </div>
    </div>

    <div v-else-if="diagnostic.status==='in_progress'&&!diagnostic.submitted" style="padding:20px;background:var(--bg-secondary);border-radius:12px">
      <p style="font-weight:600;margin:0 0 16px">请完成以下 5 道诊断题：</p>
      <div v-for="(q,i) in diagnostic.questions" :key="q.question_id" style="margin-bottom:16px;padding:12px;background:#fff;border-radius:8px;border:1px solid var(--border-color)">
        <p style="margin:0 0 8px;font-weight:500">{{ i+1 }}. {{ q.content }}</p>
        <input v-model="diagnostic.answers[i]" :placeholder="'请输入答案'" style="width:100%;padding:8px 12px;border:1px solid #ddd;border-radius:6px;font-size:14px">
      </div>
      <button class="primary-btn" :disabled="diagnostic.loading" @click="submitDiagnosticFlow" style="width:100%">{{ diagnostic.loading?'提交中…':'提交诊断答案' }}</button>
    </div>

    <div v-else-if="diagnostic.status==='completed'" style="padding:20px;background:#e8f5e9;border-radius:12px;text-align:center">
      <p style="margin:0;color:#2e7d32;font-weight:600">✅ 首次诊断已完成</p>
      <button class="ghost-btn" :disabled="diagnostic.loading" @click="startDiagnosticFlow" style="margin-top:8px">重新诊断</button>
    </div>
  </div>
</div>
</article></section>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { analyseStream, getToken, login, register, setToken } from './api'
import { getMyProfile, saveMyProfile, getDiagnosticStatus, startDiagnostic, submitDiagnostic, skipDiagnostic } from './api/profile'

const authMode=ref('login'), authLoading=ref(false), analysisLoading=ref(false), token=ref(getToken()), currentView=ref('home'), mobileMenu=ref(false), messages=ref([])
const authForm=reactive({username:'',password:'',confirmPassword:''})
const requestForm=reactive({userId:1,sessionId:1,text:''})
const settings=reactive({stage:'',grade:'',subject:'',goal:'',days:5,target:3})
const profileLoaded=ref(false), profileLoading=ref(false), realProfile=ref(null)
const diagnostic=reactive({status:'',diagnosticId:null,questions:[],answers:[],loading:false,submitted:false})
const isAuthed=computed(()=>Boolean(token.value))
const navItems=[{key:'home',label:'学习首页',icon:'⌂',group:'学习空间'},{key:'learn',label:'智能学习',icon:'✦'},{key:'profile',label:'学习画像',icon:'◎'},{key:'records',label:'学习记录',icon:'▤',badge:'8'},{key:'points',label:'积分中心',icon:'◆',group:'成长与权益'},{key:'vip',label:'会员中心',icon:'♛'},{key:'settings',label:'基础信息设置',icon:'⚙',group:'个人设置'}]
const metas={home:['学习首页','下午好，继续保持今天的学习节奏吧'],learn:['智能学习','描述你的问题，智学伴会为你诊断并生成针对性练习'],profile:['学习画像','了解每个知识点的掌握情况和成长趋势'],records:['学习记录','回顾每一次练习和进步'],points:['积分中心','坚持有效学习，用积分兑换更多学习能力'],vip:['会员中心','解锁更深入、更持续的个性化学习服务'],settings:['基础信息设置','完善信息，让学习内容更适合你']}
const pageMeta=computed(()=>({title:metas[currentView.value][0],subtitle:metas[currentView.value][1]}))
const quickPrompts=['移项时为什么要变号？','我总在去括号时出错','帮我复习一元一次方程']
const knowledgeItems=[{name:'一元一次方程 · 移项',chapter:'第三章 一元一次方程',score:55,status:'基础薄弱',type:'weak',correct:5,total:12,date:'今天'},{name:'去括号法则',chapter:'第二章 整式的加减',score:63,status:'正在巩固',type:'medium',correct:8,total:13,date:'昨天'},{name:'有理数乘除法',chapter:'第一章 有理数',score:86,status:'掌握良好',type:'good',correct:18,total:21,date:'7月18日'}]
const records=[{time:'14:45',icon:'数',title:'一元一次方程专项练习',desc:'3 道题 · 中等难度 · 获得 5 积分',result:'正确率 67%',good:false},{time:'12:10',icon:'订',title:'历史错题订正',desc:'完成 2 道移项错题订正 · 获得 6 积分',result:'全部通过',good:true},{time:'09:24',icon:'诊',title:'薄弱点智能诊断',desc:'识别知识点：去括号与移项',result:'掌握度 +3%',good:true}]
const exchanges=[{icon:'＋',name:'额外一组练习',desc:'突破普通用户每日次数限制',cost:10},{icon:'⌕',name:'详细错因分析',desc:'获得更深入的错误原因说明',cost:10},{icon:'▥',name:'阶段性学习报告',desc:'总结近期表现与学习建议',cost:20}]
const vipRows=[['基础学情诊断','✓ 支持','✓ 支持'],['每日练习生成','5 组 / 天','20 组 / 天'],['详细错因分析','10 积分 / 次','✓ 直接使用'],['学习历史记录','最近 10 条','✓ 全部记录'],['阶段性学情报告','20 积分 / 次','✓ 直接生成']]

const stageMap={primary:'小学',junior:'初中',senior:'高中',university:'大学'}
const goalMap={daily:'日常巩固',weakness:'薄弱点补习',exam:'考试复习'}
function stageEn(cn){for(const[en,name]of Object.entries(stageMap)){if(name===cn)return en}return''}
function goalEn(cn){for(const[en,name]of Object.entries(goalMap)){if(name===cn)return en}return''}

const gradeOptions={小学:['一年级','二年级','三年级','四年级','五年级','六年级'],初中:['七年级','八年级','九年级'],高中:['高一','高二','高三'],大学:['大一','大二','大三','大四']}
const subjectOptions={小学:['语文','数学','英语','科学'],初中:['语文','数学','英语','物理','化学','生物','政治','历史','地理'],高中:['语文','数学','英语','物理','化学','生物','政治','历史','地理'],大学:['高等数学','大学英语','线性代数','概率论','Python程序设计','C语言','数据结构']}
const currentGrades=computed(()=>gradeOptions[settings.stage]||[])
const currentSubjects=computed(()=>subjectOptions[settings.stage]||[])
function onStageChange(stage){settings.stage=stage;settings.grade='';settings.subject=''}

function go(view){currentView.value=view;mobileMenu.value=false;window.scrollTo({top:0,behavior:'smooth'});if(view==='settings')loadProfile()}

async function loadProfile(){if(!token.value)return;profileLoading.value=true;try{const resp=await getMyProfile();const p=resp?.data?.profile;realProfile.value=p;if(p){settings.stage=stageMap[p.stage]||p.stage;settings.grade=p.grade||'';settings.subject=p.subject||'';settings.goal=goalMap[p.learning_goal]||p.learning_goal;settings.days=p.weekly_study_days||5;settings.target=p.daily_target_groups||3;profileLoaded.value=true;await loadDiagnosticStatus()}else{profileLoaded.value=false}}catch(e){console.error('加载画像失败',e)}finally{profileLoading.value=false}}

async function loadDiagnosticStatus(){try{const resp=await getDiagnosticStatus();diagnostic.status=resp?.data?.status||'';diagnostic.diagnosticId=resp?.data?.diagnostic_id||null}catch(e){console.error('加载诊断状态失败',e)}}
async function submitAuth(){if(authForm.username.length<6||authForm.password.length<6){ElMessage.warning('用户名和密码都需要 6 到 20 位');return}if(authMode.value==='register'&&authForm.password!==authForm.confirmPassword){ElMessage.warning('两次输入的密码不一致');return}authLoading.value=true;try{if(authMode.value==='register'){const user=await register(authForm.username,authForm.password);if(user?.id)requestForm.userId=user.id;ElMessage.success('注册成功，请登录');authMode.value='login';authForm.password='';authForm.confirmPassword='';return}const payload=await login(authForm.username,authForm.password);token.value=payload.access_token;ElMessage.success('登录成功，欢迎回来');await loadProfile();if(!realProfile.value){ElMessage.warning('请先完善学习信息');go('settings')}}catch(error){ElMessage.error(error.message||'认证失败')}finally{authLoading.value=false}}
function clearSession(){setToken('');token.value='';realProfile.value=null;profileLoaded.value=false;diagnostic.status='';diagnostic.questions=[];diagnostic.answers=[];diagnostic.submitted=false;currentView.value='home';ElMessage.success('已安全退出')}
function addMessage(role,content,title=role==='assistant'?'智学伴 AI':'你'){const msg={id:`${Date.now()}-${Math.random()}`,role,title,content};messages.value.push(msg);return msg}
async function send(){const text=requestForm.text.trim();if(!text){ElMessage.warning('先描述你想解决的学习问题');return}addMessage('user',text);requestForm.text='';analysisLoading.value=true;const reply=addMessage('assistant','','智学伴 AI');try{await analyseStream({userId:requestForm.userId,sessionId:requestForm.sessionId,text,onEvent(event){if(event.type==='result'||event.type==='raw')reply.content+=event.content||'';if(event.type==='thinking'&&event.thought)reply.content+=`${event.thought}\n`;if(event.type==='observation')reply.content+=`${event.content}\n`}});if(!reply.content)reply.content='分析已完成，后端暂未返回可展示内容。'}catch(error){reply.content=error.message||'请求失败';ElMessage.error(reply.content)}finally{analysisLoading.value=false}}
function placeholder(name){ElMessage.info(`${name}页面与接口位置已预留，等待后端服务接入`)}
async function saveSettings(){const apiData={stage:stageEn(settings.stage),grade:settings.grade,subject:settings.subject,learning_goal:goalEn(settings.goal),weekly_study_days:Number(settings.days),daily_target_groups:Number(settings.target)};try{const resp=await saveMyProfile(apiData);realProfile.value=resp?.data;profileLoaded.value=true;diagnostic.submitted=false;ElMessage.success('基础信息已保存');await loadDiagnosticStatus()}catch(e){ElMessage.error(e.message||'保存失败')}}

async function startDiagnosticFlow(){diagnostic.loading=true;diagnostic.questions=[];diagnostic.answers=[];diagnostic.submitted=false;try{const resp=await startDiagnostic();diagnostic.diagnosticId=resp?.data?.diagnostic_id;diagnostic.questions=resp?.data?.questions||[];diagnostic.answers=diagnostic.questions.map(()=>'');diagnostic.status='in_progress'}catch(e){ElMessage.error(e.message||'生成诊断题失败')}finally{diagnostic.loading=false}}

async function submitDiagnosticFlow(){if(!diagnostic.diagnosticId)return;diagnostic.loading=true;const answers=diagnostic.questions.map((q,i)=>({question_id:q.question_id,answer:diagnostic.answers[i]||''}));try{const resp=await submitDiagnostic(diagnostic.diagnosticId,answers);diagnostic.status='completed';diagnostic.submitted=true;const masteries=resp?.data?.masteries||[];ElMessage.success('诊断完成！初始化了 '+masteries.length+'个知识点的掌握度');await loadDiagnosticStatus()}catch(e){ElMessage.error(e.message||'提交诊断失败')}finally{diagnostic.loading=false}}

async function skipDiagnosticFlow(){diagnostic.loading=true;try{const resp=await skipDiagnostic();diagnostic.status='skipped';diagnostic.submitted=true;ElMessage.success('已跳过首次诊断，使用默认掌握度 60');await loadDiagnosticStatus()}catch(e){ElMessage.error(e.message||'跳过诊断失败')}finally{diagnostic.loading=false}}
</script>

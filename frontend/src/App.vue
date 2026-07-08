<template>
  <main class="app-shell">
    <section class="workspace">
      <aside class="side-panel">
        <div class="brand">
          <div class="brand-mark">Q</div>
          <div>
            <h1>学生学情分析系统</h1>
            <p>{{ isAuthed ? '已连接后端服务' : '请先登录后使用 Agent' }}</p>
          </div>
        </div>

        <el-tabs v-model="authMode" stretch>
          <el-tab-pane label="登录" name="login" />
          <el-tab-pane label="注册" name="register" />
        </el-tabs>

        <el-form class="auth-form" label-position="top" @submit.prevent>
          <el-form-item label="用户名">
            <el-input v-model.trim="authForm.username" :prefix-icon="User" maxlength="20" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input
              v-model="authForm.password"
              :prefix-icon="Lock"
              maxlength="20"
              show-password
              type="password"
            />
          </el-form-item>
          <el-button class="full-button" type="primary" :loading="authLoading" @click="submitAuth">
            {{ authMode === 'login' ? '登录' : '注册' }}
          </el-button>
        </el-form>

        <el-divider />

        <el-form label-position="top">
          <el-form-item label="用户 ID">
            <el-input-number v-model="requestForm.userId" :min="1" controls-position="right" />
          </el-form-item>
          <el-form-item label="会话 ID">
            <el-input-number v-model="requestForm.sessionId" :min="1" controls-position="right" />
          </el-form-item>
          <el-form-item label="后端地址">
            <el-input :model-value="apiBaseLabel" disabled />
          </el-form-item>
        </el-form>

        <el-button class="full-button" :icon="RefreshLeft" @click="clearSession">
          退出登录
        </el-button>
      </aside>

      <section class="chat-panel">
        <header class="chat-header">
          <div>
            <h2>学情分析 Agent</h2>
            <p>发送学生表现、错题情况或知识点掌握描述，后端会返回分析结果。</p>
          </div>
          <el-tag :type="isAuthed ? 'success' : 'info'" effect="light">
            {{ isAuthed ? 'Token 已保存' : '未登录' }}
          </el-tag>
        </header>

        <div class="messages">
          <article
            v-for="message in messages"
            :key="message.id"
            class="message"
            :class="`message-${message.role}`"
          >
            <div class="message-meta">
              <span>{{ message.role === 'user' ? '你' : message.title }}</span>
              <time>{{ message.time }}</time>
            </div>
            <pre>{{ message.content }}</pre>
          </article>
        </div>

        <footer class="composer">
          <el-input
            v-model="requestForm.text"
            type="textarea"
            :autosize="{ minRows: 4, maxRows: 8 }"
            resize="none"
            placeholder="例如：学生最近函数题正确率低，二次函数图像变换经常做错，请分析薄弱点并给出练习建议。"
            @keydown.ctrl.enter.prevent="send(false)"
          />
          <div class="composer-actions">
            <el-switch
              v-model="streamMode"
              active-text="流式"
              inactive-text="普通"
              inline-prompt
            />
            <div class="button-row">
              <el-button :icon="Delete" @click="messages = []">清空</el-button>
              <el-button
                type="primary"
                :icon="Promotion"
                :loading="analysisLoading"
                @click="send(streamMode)"
              >
                发送
              </el-button>
            </div>
          </div>
        </footer>
      </section>
    </section>
  </main>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Delete, Lock, Promotion, RefreshLeft, User } from '@element-plus/icons-vue'
import { analyse, analyseStream, getToken, login, register, setToken } from './api'

const authMode = ref('login')
const authLoading = ref(false)
const analysisLoading = ref(false)
const streamMode = ref(true)
const token = ref(getToken())
const messages = ref([])

const authForm = reactive({
  username: '',
  password: ''
})

const requestForm = reactive({
  userId: 1,
  sessionId: 1,
  text: ''
})

const isAuthed = computed(() => Boolean(token.value))
const apiBaseLabel = computed(() => import.meta.env.VITE_API_BASE_URL || 'Vite 代理 -> http://127.0.0.1:8000')

async function submitAuth() {
  if (authForm.username.length < 6 || authForm.password.length < 6) {
    ElMessage.warning('用户名和密码都需要 6 到 20 位')
    return
  }

  authLoading.value = true
  try {
    if (authMode.value === 'register') {
      const user = await register(authForm.username, authForm.password)
      if (user?.id) {
        requestForm.userId = user.id
      }
      ElMessage.success('注册成功，可以登录了')
      authMode.value = 'login'
      return
    }

    const payload = await login(authForm.username, authForm.password)
    token.value = payload.access_token
    ElMessage.success('登录成功')
  } catch (error) {
    ElMessage.error(error.message || '认证失败')
  } finally {
    authLoading.value = false
  }
}

function clearSession() {
  setToken('')
  token.value = ''
  ElMessage.success('已退出')
}

function addMessage(role, content, title = role === 'assistant' ? 'Agent' : '你') {
  const message = {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    title,
    content,
    time: new Date().toLocaleTimeString()
  }
  messages.value.push(message)
  return message
}

function normalizeResult(payload) {
  const data = payload?.data ?? payload
  if (typeof data === 'string') return data
  if (data?.final_result) return data.final_result
  return JSON.stringify(data, null, 2)
}

async function send(useStream) {
  const text = requestForm.text.trim()
  if (!text) {
    ElMessage.warning('先输入要分析的内容')
    return
  }

  addMessage('user', text)
  requestForm.text = ''
  analysisLoading.value = true

  try {
    if (!useStream) {
      const payload = await analyse({
        userId: requestForm.userId,
        sessionId: requestForm.sessionId,
        text
      })
      addMessage('assistant', normalizeResult(payload))
      return
    }

    const reply = addMessage('assistant', '', 'Agent')
    await analyseStream({
      userId: requestForm.userId,
      sessionId: requestForm.sessionId,
      text,
      onEvent(event) {
        if (event.type === 'thinking') {
          const action = event.action ? `动作：${event.action}\n` : ''
          const thought = event.thought ? `思考：${event.thought}\n` : ''
          reply.content += `${action}${thought}\n`
          return
        }

        if (event.type === 'result') {
          reply.content += event.content
          return
        }

        if (event.type === 'skill_loaded' || event.type === 'observation') {
          reply.content += `\n${event.content}\n`
          return
        }

        if (event.type === 'raw') {
          reply.content += event.content
        }
      }
    })
  } catch (error) {
    addMessage('assistant', error.message || '请求失败', '错误')
    ElMessage.error(error.message || '请求失败')
  } finally {
    analysisLoading.value = false
  }
}
</script>

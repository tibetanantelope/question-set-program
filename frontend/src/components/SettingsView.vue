<template>
  <section class="view">
    <article class="panel settings">
      <div class="settings-title"><span>⚙</span><div><h2>基础信息设置</h2><p>完善信息，让诊断和练习更适合你</p></div></div>
      <div v-if="loading" class="state-tip">正在加载学习信息…</div>
      <form v-else @submit.prevent="save">
        <label>当前学段
          <div class="segments">
            <button v-for="item in stages" :key="item.value" type="button" :class="{active: form.stage === item.value}" @click="form.stage = item.value">{{ item.label }}</button>
          </div>
        </label>
        <div class="form-grid">
          <label>年级
            <select v-model="form.grade"><option v-for="grade in gradeOptions" :key="grade">{{ grade }}</option></select>
          </label>
          <label>学科或课程
            <input v-if="form.stage === 'university'" v-model.trim="form.subject" maxlength="30" placeholder="例如：高等数学">
            <select v-else v-model="form.subject"><option v-for="subject in subjectOptions" :key="subject">{{ subject }}</option></select>
          </label>
        </div>
        <div v-if="form.stage !== 'university'" class="book-tip">✓ 中小学阶段默认按照人教版控制学习范围</div>
        <div class="form-grid">
          <label>每周学习天数
            <select v-model.number="form.weekly_study_days"><option v-for="day in 7" :key="day" :value="day">{{ day }} 天</option></select>
          </label>
          <label>每日目标
            <select v-model.number="form.daily_target_groups"><option v-for="count in 5" :key="count" :value="count">{{ count }} 组练习</option></select>
          </label>
        </div>
        <div class="settings-actions">
          <button type="button" class="danger-link" @click="$emit('logout')">退出登录</button>
          <button class="primary-btn" :disabled="saving">{{ saving ? '保存中…' : '保存设置' }}</button>
        </div>
      </form>
    </article>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getMyProfile, saveMyProfile } from '../api/profile'
import { subjectsForStage } from '../constants/education'

const emit = defineEmits(['saved', 'logout'])
const loading = ref(true)
const saving = ref(false)
const stages = [
  { value: 'primary', label: '小学' }, { value: 'junior', label: '初中' },
  { value: 'senior', label: '高中' }, { value: 'university', label: '大学' },
]
const grades = {
  primary: ['一年级', '二年级', '三年级', '四年级', '五年级', '六年级'],
  junior: ['七年级', '八年级', '九年级'],
  senior: ['高一', '高二', '高三'],
  university: ['大学'],
}
const form = reactive({
  stage: 'junior', grade: '七年级', subject: '数学',
  weekly_study_days: 5, daily_target_groups: 3,
})
const gradeOptions = computed(() => grades[form.stage] || [])
const subjectOptions = computed(() => subjectsForStage(form.stage))

watch(() => form.stage, () => {
  if (!gradeOptions.value.includes(form.grade)) form.grade = gradeOptions.value[0]
  if (form.stage !== 'university' && !subjectOptions.value.includes(form.subject)) {
    form.subject = subjectOptions.value[0] || ''
  }
})

onMounted(async () => {
  try {
    const payload = await getMyProfile()
    if (payload?.data?.profile) Object.assign(form, payload.data.profile)
  } catch (error) {
    ElMessage.warning(error.message || '学习信息加载失败')
  } finally {
    loading.value = false
  }
})

async function save() {
  if (!form.grade || !form.subject.trim()) {
    ElMessage.warning('请填写完整的年级和学科或课程')
    return
  }
  saving.value = true
  try {
    const { learning_goal: _legacyGoal, ...stableProfile } = form
    const payload = await saveMyProfile(stableProfile)
    ElMessage.success(payload?.message || '学习信息已保存')
    emit('saved', payload.data)
  } catch (error) {
    ElMessage.error(error.message || '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.state-tip{padding:50px;text-align:center;color:#8490a2}
.settings input{width:100%;box-sizing:border-box;padding:11px 12px;border:1px solid #dfe5ed;border-radius:8px}
</style>

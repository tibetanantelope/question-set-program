<template>
  <section class="view">
    <button class="ghost-btn back" @click="$emit('back')">← 返回</button>
    <div class="review-hero">
      <div><span>{{ card.subject || subject || '知识点复习' }}</span><h2>{{ card.knowledge_point_name || knowledgePointName }}</h2><p>{{ heroDescription }}</p></div>
      <div class="review-score"><small>当前掌握度</small><strong>{{ card.mastery_score == null ? '--' : `${card.mastery_score}%` }}</strong><em>{{ statusLabel(card.learning_status) }}</em></div>
    </div>
    <div class="mode-tabs">
      <button v-for="item in modes" :key="item.value" :class="{active:mode===item.value}" @click="changeMode(item.value)"><b>{{ item.label }}</b><small>{{ item.desc }}</small></button>
    </div>
    <div v-if="loading" class="panel loading">正在加载个性化复习卡…</div>
    <div v-else-if="loadError" class="panel load-error">
      <strong>复习内容加载失败</strong>
      <p>{{ loadError }}</p>
      <button class="primary-btn" @click="load">重新加载</button>
    </div>
    <template v-else-if="card.knowledge_point_name">
      <div class="review-layout">
        <main>
          <article class="panel insight"><span>AI</span><div><h3>结合你的学习记录</h3><p>{{ card.personalized_insight }}</p></div></article>
          <article v-if="mode==='advanced' && card.advanced_focus" class="panel advanced-focus">
            <span>进阶目标</span>
            <div><h3>从会做提升到会迁移</h3><p>{{ card.advanced_focus }}</p></div>
          </article>
          <article class="panel review-block">
            <div class="block-title"><span>01</span><div><h3>核心概念</h3><p>先理解它解决什么问题，再记忆公式和结论</p></div></div>
            <div class="concept-summary">{{ card.summary }}</div>
            <ul><li v-for="item in card.concepts" :key="item">{{ item }}</li></ul>
            <div class="formula"><small>核心结构 / 方法</small><strong>{{ card.formula }}</strong></div>
          </article>
          <article class="panel review-block">
            <div class="block-title"><span>02</span><div><h3>易错点提醒</h3><p>做题前先避开最常见的错误</p></div></div>
            <div class="pitfalls"><div v-for="(item,index) in card.pitfalls" :key="item"><b>易错 {{ index+1 }}</b><span>{{ item }}</span></div></div>
          </article>
          <article class="panel review-block">
            <div class="block-title"><span>03</span><div><h3>典型例题</h3><p>用一道代表题把概念落到解题步骤</p></div></div>
            <div class="example"><h4>{{ card.example?.question }}</h4><button v-if="!exampleRevealed" class="soft-btn" @click="exampleRevealed=true">思考后查看答案</button><div v-else class="example-answer"><strong>答案：{{ card.example?.answer }}</strong><ol><li v-for="step in card.example?.steps" :key="step">{{ step }}</li></ol></div></div>
          </article>
          <article class="panel review-block quiz-block">
            <div class="block-title"><span>04</span><div><h3>{{ mode==='advanced'?'综合迁移挑战':'概念自测' }}</h3><p>{{ mode==='advanced'?'运用知识解决条件变化和反向推理问题':'通过后再开始错题订正，效果更好' }}</p></div></div>
            <div v-for="(question,index) in card.quiz" :key="question.question" class="quiz-item">
              <h4>{{ index+1 }}. {{ question.question }}</h4>
              <div><button v-for="(option,optionIndex) in question.options" :key="optionIndex" :disabled="completed" :class="{selected:answers[index]===optionIndex,correct:completed&&optionIndex===question.correct_index,wrong:completed&&answers[index]===optionIndex&&optionIndex!==question.correct_index}" @click="answers[index]=optionIndex">{{ String.fromCharCode(65+optionIndex) }}. {{ cleanOptionLabel(option) }}</button></div>
              <p v-if="completed">{{ question.explanation }}</p>
            </div>
            <button class="primary-btn complete" :disabled="submitting || !(card.quiz || []).every((_,index)=>Number.isInteger(answers[index]))" @click="completeReview">{{ submitting?'提交中…':'完成复习并检查自测' }}</button>
            <div v-if="result" :class="['quiz-result',{passed:result.passed}]"><strong>{{ result.quiz_score }} / {{ result.quiz_total }}</strong><span>{{ result.passed ? '概念自测通过，可以开始订正错题' : '建议重新阅读易错点后再尝试错题' }}</span></div>
          </article>
        </main>
        <aside>
          <article class="panel mistake-link"><h3>关联错题</h3><div class="mistake-count"><strong>{{ card.mistake_summary?.pending || 0 }}</strong><span>道待订正</span></div><p>已订正 {{ card.mistake_summary?.corrected || 0 }} 道 · 共 {{ card.mistake_summary?.total || 0 }} 道</p><div v-for="item in card.related_mistakes?.slice(0,3)" :key="item.mistake_id" class="mini-mistake">{{ item.question_content }}</div><button class="primary-btn full" :disabled="!hasCompletedAnyMode" @click="$emit('mistakes',{name:card.knowledge_point_name,subject:card.subject})">{{ hasCompletedAnyMode?'开始订正这组错题':'任选一种模式完成自测后开始订正' }}</button></article>
        </aside>
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { completeKnowledgeReview, getKnowledgeReviewCard, newRequestId } from '../api/mastery'

const props = defineProps({ knowledgePointName:{type:String,required:true}, subject:{type:String,default:''} })
defineEmits(['back','mistakes'])
const modes=[{value:'quick',label:'快速回顾',desc:'核心概念 + 2题自测'},{value:'full',label:'完整复习',desc:'概念、易错点、例题与自测'},{value:'advanced',label:'进阶巩固',desc:'完整内容 + 迁移思考'}]
const mode=ref('full'), card=ref({}), loading=ref(true), loadError=ref(''), submitting=ref(false), exampleRevealed=ref(false), completed=ref(false), result=ref(null)
const answers=reactive([])
function cleanOptionLabel(option){
  return String(option||'').replace(/^\s*[A-CＡ-Ｃ][.．、:：]\s*/i,'')
}
const modeStates=reactive({})
const hasCompletedAnyMode=computed(()=>
  completed.value
  ||Boolean(card.value.completed_modes?.length)
  ||Object.values(modeStates).some(state=>state?.completed)
)
const heroDescription=computed(()=>{
  if(loading.value)return '正在加载复习内容…'
  if(loadError.value)return '复习内容暂时无法加载，请重试'
  return card.value.summary||'暂无可用的复习内容'
})
onMounted(load)
async function load(){
  loading.value=true
  loadError.value=''
  if(!props.knowledgePointName.trim()){
    card.value={}
    loadError.value='未指定需要复习的知识点，请返回学习画像重新选择'
    loading.value=false
    return
  }
  try{
    const saved=modeStates[mode.value]
    if(saved?.card){
      restoreModeState(saved)
      return
    }
    const payload=await getKnowledgeReviewCard(props.knowledgePointName,props.subject,mode.value)
    if(!payload?.data?.knowledge_point_name)throw new Error('服务器未返回有效的复习内容')
    card.value=payload.data
    const progress=card.value.review_progress
    answers.splice(0,answers.length,...(progress?.answers||[]))
    completed.value=Boolean(progress?.completed)
    result.value=progress?.completed?{
      review_id:progress.review_id,
      quiz_score:progress.quiz_score,
      quiz_total:progress.quiz_total,
      passed:progress.passed,
      completed_at:progress.completed_at,
    }:null
    exampleRevealed.value=false
    saveModeState()
  }
  catch(error){
    card.value={}
    loadError.value=error.message||'知识点复习卡加载失败'
  }
  finally{loading.value=false}
}
function saveModeState(){
  modeStates[mode.value]={
    card:card.value,
    answers:[...answers],
    completed:completed.value,
    result:result.value,
    exampleRevealed:exampleRevealed.value,
  }
}
function restoreModeState(saved){
  card.value=saved.card
  answers.splice(0,answers.length,...saved.answers)
  completed.value=saved.completed
  result.value=saved.result
  exampleRevealed.value=saved.exampleRevealed
}
async function changeMode(value){
  if(value===mode.value)return
  saveModeState()
  mode.value=value
  await load()
}
async function completeReview(){
  submitting.value=true
  try{
    const payload=await completeKnowledgeReview({knowledge_point_name:props.knowledgePointName,subject:props.subject||null,review_mode:mode.value,answers:[...answers]},newRequestId())
    result.value=payload.data;completed.value=true
    saveModeState()
    ElMessage.success('本次知识点复习已记录')
  }catch(error){ElMessage.error(error.message||'复习记录提交失败')}
  finally{submitting.value=false}
}
function statusLabel(value){return {weak:'基础薄弱',consolidating:'正在巩固',mastered:'掌握良好'}[value]||'待评估'}
</script>

<style scoped>
.back{margin-bottom:15px}.review-hero{display:flex;align-items:center;justify-content:space-between;padding:29px 34px;border-radius:17px;color:#fff;background:linear-gradient(120deg,#346fdc,#6553c7)}.review-hero span{font-size:10px;color:#d9e5ff}.review-hero h2{margin:7px 0;font-size:27px}.review-hero p{max-width:700px;margin:0;color:#e4ebff;font-size:11px;line-height:1.7}.review-score{text-align:right}.review-score>*{display:block}.review-score strong{font-size:30px}.review-score em{font-size:9px;font-style:normal}.mode-tabs{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:16px 0}.mode-tabs button{padding:13px;border:1px solid #e0e6ef;border-radius:11px;color:#667489;background:#fff;text-align:left}.mode-tabs b,.mode-tabs small{display:block}.mode-tabs small{margin-top:4px;color:#9aa4b3;font-size:9px}.mode-tabs button.active{color:#356fe6;border-color:#83a8ef;background:#f2f6ff}.review-layout{display:grid;grid-template-columns:minmax(0,1fr) 280px;gap:16px;align-items:start}.review-layout main{display:flex;flex-direction:column;gap:16px}.review-layout aside{position:sticky;top:96px}.loading{padding:60px;text-align:center;color:#8b96a7}.load-error{padding:48px;text-align:center}.load-error strong{display:block;color:#273b5a;font-size:18px}.load-error p{margin:10px 0 18px;color:#7f8b9d}.insight,.advanced-focus{display:flex;gap:13px;background:#f2f7ff}.insight>span,.advanced-focus>span{display:grid;place-items:center;min-width:37px;height:37px;padding:0 10px;flex:none;border-radius:10px;color:#fff;background:#356fe6;font-weight:800}.advanced-focus{border:1px solid #d8ccff;background:#f7f4ff}.advanced-focus>span{background:#6b52cb}.insight h3,.insight p,.advanced-focus h3,.advanced-focus p{margin:0}.insight p,.advanced-focus p{margin-top:6px;color:#5d6d83;font-size:10px;line-height:1.7}.review-block{padding:25px}.block-title{display:flex;align-items:center;gap:12px;margin-bottom:18px}.block-title>span{display:grid;place-items:center;width:33px;height:33px;border-radius:9px;color:#356fe6;background:#edf4ff;font-size:10px;font-weight:800}.block-title h3,.block-title p{margin:0}.block-title p{margin-top:4px;color:#929cad;font-size:9px}.concept-summary{padding:15px;border-left:3px solid #356fe6;border-radius:0 9px 9px 0;color:#40516a;background:#f6f9ff;font-size:11px;line-height:1.8}.review-block ul{padding-left:22px;color:#58677c;font-size:10px;line-height:2}.formula{padding:14px;border-radius:10px;background:#f7f9fc}.formula>*{display:block}.formula small{color:#8995a6;font-size:8px}.formula strong{margin-top:6px;color:#2e4770}.pitfalls{display:grid;gap:9px}.pitfalls>div{display:flex;gap:12px;padding:12px;border-radius:9px;background:#fff6f2;font-size:10px}.pitfalls b{color:#e06a3f}.example h4{line-height:1.7}.example-answer{padding:15px;border-radius:10px;background:#eef9f3;color:#35634a}.example-answer ol{padding-left:20px;font-size:10px;line-height:1.9}.quiz-item{padding:16px 0;border-top:1px solid #edf0f4}.quiz-item h4{font-size:11px}.quiz-item>div{display:grid;gap:7px}.quiz-item button{padding:10px 12px;border:1px solid #e0e5ed;border-radius:8px;color:#526178;background:#fff;text-align:left;font-size:10px}.quiz-item button.selected{color:#356fe6;border-color:#7fa5ee;background:#f1f6ff}.quiz-item button.correct{color:#168056;border-color:#75c8a5;background:#eaf8f2}.quiz-item button.wrong{color:#bd4d55;border-color:#e9a5aa;background:#fff1f2}.quiz-item p{color:#66758a;font-size:9px}.complete{width:100%;margin-top:10px}.quiz-result{display:flex;align-items:center;gap:12px;margin-top:12px;padding:13px;border-radius:9px;color:#a24b51;background:#fff1f2}.quiz-result.passed{color:#197553;background:#eaf8f2}.quiz-result strong{font-size:20px}.quiz-result span{font-size:10px}.mistake-link h3{margin:0}.mistake-count{margin:18px 0}.mistake-count strong{font-size:32px}.mistake-count span,.mistake-link p{color:#8b96a7;font-size:9px}.mini-mistake{overflow:hidden;margin:9px 0;padding:9px;border-radius:8px;background:#f7f9fc;color:#66758a;font-size:9px;white-space:nowrap;text-overflow:ellipsis}.full{width:100%;margin-top:12px}@media(max-width:900px){.review-layout{grid-template-columns:1fr}.review-layout aside{position:static}.mode-tabs{grid-template-columns:1fr}}
</style>

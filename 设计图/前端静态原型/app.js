const titles={home:['学习首页','下午好，继续保持今天的学习节奏吧'],learn:['智能学习','描述你的问题，智学伴会为你诊断并生成针对性练习'],profile:['学习画像','了解每个知识点的掌握情况和成长趋势'],records:['学习记录','回顾每一次练习和进步'],points:['积分中心','坚持有效学习，用积分兑换更多学习能力'],vip:['会员中心','解锁更深入、更持续的个性化学习服务'],settings:['基础信息设置','完善信息，让学习内容更适合你']};
let points=126,selectedAnswer='',question=1;
const $=s=>document.querySelector(s),$$=s=>document.querySelectorAll(s);
function switchView(name){$$('.view').forEach(v=>v.classList.remove('active'));$(`#view-${name}`)?.classList.add('active');$$('.nav-item').forEach(n=>n.classList.toggle('active',n.dataset.view===name));$('#pageTitle').textContent=titles[name][0];$('#pageSubtitle').textContent=titles[name][1];$('#sidebar').classList.remove('open');window.scrollTo({top:0,behavior:'smooth'})}
$$('[data-view]').forEach(el=>el.addEventListener('click',()=>switchView(el.dataset.view)));
$('#mobileMenu').addEventListener('click',()=>$('#sidebar').classList.toggle('open'));

const input=$('#studyInput');input.addEventListener('input',()=>$('#inputCount').textContent=input.value.length);
$$('.quick-prompts button').forEach(b=>b.addEventListener('click',()=>{input.value=b.textContent;$('#inputCount').textContent=input.value.length}));
$('#analyseBtn').addEventListener('click',()=>{if(!input.value.trim())return toast('请先描述你的学习问题');$('#analyseBtn').textContent='正在分析学习画像…';$('#analyseBtn').disabled=true;setTimeout(()=>{$('#askCard').classList.add('hidden');$('#diagnosisCard').classList.remove('hidden');$$('.step')[0].classList.remove('active');$$('.step')[1].classList.add('active');toast('智能诊断已完成')},700)});
$('#startPractice').addEventListener('click',()=>{$('#diagnosisCard').classList.add('hidden');$('#practiceCard').classList.remove('hidden');$$('.step')[1].classList.remove('active');$$('.step')[2].classList.add('active')});
$$('#answerOptions button').forEach(b=>b.addEventListener('click',()=>{selectedAnswer=b.dataset.answer;$$('#answerOptions button').forEach(x=>x.classList.remove('selected'));b.classList.add('selected');$('#submitAnswer').disabled=false}));
$('#submitAnswer').addEventListener('click',()=>{if(!selectedAnswer)return;$$('#answerOptions button').forEach(x=>{x.disabled=true;if(x.dataset.answer==='C')x.classList.add('correct')});$('#feedback').classList.remove('hidden');$('#submitAnswer').classList.add('hidden')});
$('#nextQuestion').addEventListener('click',()=>{question++;if(question>3){points+=5;updatePoints();showModal('练习完成','本组练习共完成 3 题，掌握度提升 3 分，并获得 5 积分。');$$('.step')[2].classList.remove('active');$$('.step')[3].classList.add('active');return}$('#questionNo').textContent=question;$('#questionBar').style.width=`${question*33}%`;selectedAnswer='';$$('#answerOptions button').forEach(x=>{x.disabled=false;x.classList.remove('selected','correct')});$('#feedback').classList.add('hidden');$('#submitAnswer').classList.remove('hidden');$('#submitAnswer').disabled=true;toast(`已进入第 ${question} 题（静态原型复用示例题）`)});

function updatePoints(){$('#pointBalance').textContent=points;$('#heroPoints').textContent=points}
$$('.exchange-btn').forEach(b=>b.addEventListener('click',()=>{const cost=Number(b.dataset.cost);if(points<cost)return toast('积分不足，完成学习任务可以获得积分');points-=cost;updatePoints();showModal('兑换成功',`已使用 ${cost} 积分兑换“${b.dataset.name}”，当前剩余 ${points} 积分。`)}));
$('#reportBtn').addEventListener('click',()=>{if(points<20)return toast('积分不足');points-=20;updatePoints();showModal('报告生成成功','已使用 20 积分生成阶段性学情报告。完整报告将包含掌握度变化、高频错因和下一阶段建议。')});
$('#openVip').addEventListener('click',()=>showModal('VIP 开通成功','模拟订单 ZXB20260716001 已完成，30 天 VIP 权益已生效，有效期至 2026 年 8 月 15 日。','♛'));
$('#settingsForm').addEventListener('submit',e=>{e.preventDefault();showModal('保存成功','基础学习信息已更新，后续诊断和练习将按照新的信息生成。')});
$$('.segment button,.goal-options button').forEach(b=>b.addEventListener('click',()=>{[...b.parentElement.children].forEach(x=>x.classList.remove('active'));b.classList.add('active')}));
$$('.input-tabs button,.filter-chips button').forEach(b=>b.addEventListener('click',()=>{[...b.parentElement.children].forEach(x=>x.classList.remove('active'));b.classList.add('active')}));

function showModal(title,text,icon='✓'){$('#modalTitle').textContent=title;$('#modalText').textContent=text;$('#modalIcon').textContent=icon;$('#modalBackdrop').classList.remove('hidden')}
function closeModal(){$('#modalBackdrop').classList.add('hidden')}
$('#modalClose').addEventListener('click',closeModal);$('#modalConfirm').addEventListener('click',closeModal);$('#modalBackdrop').addEventListener('click',e=>{if(e.target===$('#modalBackdrop'))closeModal()});
let toastTimer;function toast(text){const el=$('#toast');el.textContent=text;el.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove('show'),2200)}

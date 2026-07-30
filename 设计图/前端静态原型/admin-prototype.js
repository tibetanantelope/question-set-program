const pages = {
  dashboard: ['运营看板', '查看平台学习与运营趋势', '📊', '运营总览.html'],
  users: ['用户管理', '管理账号状态和用户学习摘要', '👥', '用户管理.html'],
  content: ['题库管理', '维护知识点、题目和审核状态', '🧩', '题库管理.html'],
  learning: ['学习详情', '查看错题、复习和学习轨迹', '📚', '学习详情.html'],
  orders: ['订单管理', '查看 VIP 订单和支付状态', '💳', '订单管理.html'],
  logs: ['系统日志', '查看操作记录和系统异常', '🛡', '系统日志.html']
}

function shell(active, title, subtitle, body) {
  const nav = Object.entries(pages).map(([key, item]) => `<a class="${key === active ? 'active' : ''}" href="${item[3]}"><span>${item[2]}</span>${item[0]}</a>`).join('')
  return `<div class="admin-shell"><aside class="sidebar"><div class="brand"><span class="brand-mark">智</span><div><strong>智学伴</strong><small>运营管理中心 · 原型</small></div></div><div class="nav-title">管理工作台</div><nav class="nav">${nav}</nav><div class="sidebar-foot"><strong>演示管理员</strong><span>admin@example.com · 模拟环境</span></div></aside><main class="main"><header class="topbar"><div><h1>${title}</h1><p>${subtitle}</p></div><div class="topbar-right"><span>数据更新时间：刚刚</span><span class="avatar">管</span><span>退出</span></div></header><section class="content">${body}</section></main></div>`
}

function mount(active, title, subtitle, body) { document.body.innerHTML = shell(active, title, subtitle, body) }

function bindDemoButtons() {
  document.querySelectorAll('.btn,.link-btn').forEach(btn => btn.addEventListener('click', () => {
    if (btn.dataset.noop !== 'true') alert('静态原型：此操作将在正式开发中接入真实接口。')
  }))
}

window.mountAdminPrototype = mount
window.bindDemoButtons = bindDemoButtons

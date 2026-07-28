export const SUBJECTS_BY_STAGE = {
  primary: ['语文', '数学', '英语', '科学', '道德与法治'],
  junior: ['语文', '数学', '英语', '物理', '化学', '生物', '道德与法治', '历史', '地理'],
  senior: ['语文', '数学', '英语', '物理', '化学', '生物', '思想政治', '历史', '地理'],
}

export function subjectsForStage(stage) {
  return SUBJECTS_BY_STAGE[stage] || []
}

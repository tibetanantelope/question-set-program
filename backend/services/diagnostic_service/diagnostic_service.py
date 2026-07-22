"""成员一：首次诊断 Service —— 生成诊断题、判题、初始化掌握度、跳过诊断。"""

import random
from datetime import datetime
from typing import List, Optional

from backend.core.exceptions import BusinessError
from backend.dao.diagnostic_mapper import DiagnosticMapper, get_diagnostic_mapper
from backend.dao.user_profile_mapper import UserProfileMapper, get_user_profile_mapper
from backend.model.diagnostic import DiagnosticSession, DiagnosticAnswer
from backend.schemas.response.diagnostic_response import (
    DiagnosticStatusResponse,
    DiagnosticStartResponse,
    DiagnosticSubmitResponse,
    MasteryItem,
    QuestionItem,
)
from backend.schemas.request.diagnostic_request import DiagnosticSubmitRequest, DiagnosticAnswerItem

# ───────────────────────────────────────────────
# 预置诊断题库：按 [学段][学科][年级] 三维组织
# 结构: {stage: {subject: {grade: [questions]}}}
# ───────────────────────────────────────────────

_Q = {  # shorthand for questions dict
    # ============================================================
    # 小学
    # ============================================================
    'primary': {
        '数学': {
            '一年级': [
                {'content': '计算：3 + 5 = ?',        'kp': '10以内加法'},
                {'content': '计算：9 - 4 = ?',        'kp': '10以内减法'},
                {'content': '比较大小：7 ○ 5（填 > < =）', 'kp': '数的比较'},
                {'content': '看图填空：☆☆☆ + ☆☆ = ____ 颗星', 'kp': '图文加法'},
                {'content': '数一数：15 里面有 ____ 个十和 ____ 个一', 'kp': '数的组成'},
            ],
            '二年级': [
                {'content': '计算：25 + 37 = ?',      'kp': '两位数加法'},
                {'content': '计算：72 - 45 = ?',      'kp': '两位数减法'},
                {'content': '计算：6 × 8 = ?',        'kp': '乘法口诀'},
                {'content': '计算：56 ÷ 7 = ?',       'kp': '表内除法'},
                {'content': '1米 = ____ 厘米',         'kp': '长度单位'},
            ],
            '三年级': [
                {'content': '计算：128 + 357 = ?',    'kp': '三位数加法'},
                {'content': '计算：603 - 278 = ?',    'kp': '三位数减法'},
                {'content': '计算：23 × 4 = ?',       'kp': '多位数乘一位数'},
                {'content': '计算：96 ÷ 3 = ?',       'kp': '两位数除以一位数'},
                {'content': '一个长方形的长是8cm，宽是5cm，周长 = ____ cm', 'kp': '长方形周长'},
            ],
            '四年级': [
                {'content': '计算：125 × 24 = ?',     'kp': '三位数乘两位数'},
                {'content': '计算：960 ÷ 15 = ?',     'kp': '除数是两位数的除法'},
                {'content': '0.3 + 0.25 = ?',         'kp': '小数加法'},
                {'content': '把1/4化成小数是 ____',    'kp': '分数与小数'},
                {'content': '一个三角形中，∠1=50°, ∠2=60°, ∠3=____°', 'kp': '三角形内角和'},
            ],
            '五年级': [
                {'content': '计算：3.6 × 2.5 = ?',    'kp': '小数乘法'},
                {'content': '计算：7.2 ÷ 0.9 = ?',    'kp': '小数除法'},
                {'content': '计算：2/3 + 1/4 = ?',    'kp': '异分母分数加法'},
                {'content': '解方程：2x + 3 = 11',     'kp': '简易方程'},
                {'content': '一个正方体的棱长是3cm，体积 = ____ cm³', 'kp': '正方体体积'},
            ],
            '六年级': [
                {'content': '计算：3/4 × 2/5 = ?',    'kp': '分数乘法'},
                {'content': '计算：5/6 ÷ 2/3 = ?',    'kp': '分数除法'},
                {'content': '25% 化成分数是 ____',     'kp': '百分数与分数'},
                {'content': '圆的半径是4cm，面积是 ____ cm²（π取3.14）', 'kp': '圆的面积'},
                {'content': '化简比：12 : 18 = ____',  'kp': '比和比例'},
            ],
        },
        '语文': {
            '三年级': [
                {'content': '"床前明月光"的下一句是？',  'kp': '古诗背诵'},
                {'content': '请用"美丽"造一个句子',     'kp': '词语运用'},
                {'content': '"他跑得很快"改为比喻句',   'kp': '修辞手法'},
                {'content': '"认真"的反义词是？',       'kp': '反义词'},
                {'content': '请写出三个描写春天的成语',  'kp': '成语积累'},
            ],
        },
        '英语': {
            '三年级': [
                {'content': '请将"apple"翻译成中文',   'kp': '单词翻译'},
                {'content': 'I ____ a student. (填 am/is/are)', 'kp': 'be动词'},
                {'content': '"book"的复数形式是？',     'kp': '名词复数'},
                {'content': '请用英语说出三种颜色',      'kp': '颜色词汇'},
                {'content': '"How are you?" 的正确回答是？', 'kp': '日常问候'},
            ],
        },
        '科学': {
            '三年级': [
                {'content': '水在什么温度下结冰？',      'kp': '水的三态'},
                {'content': '植物生长需要的三个条件是什么？', 'kp': '植物生长'},
                {'content': '磁铁的两个极分别叫什么？',   'kp': '磁铁'},
                {'content': '太阳从哪个方向升起？',      'kp': '天文常识'},
                {'content': '人体最大的器官是？',        'kp': '人体'},
            ],
        },
    },
    # ============================================================
    # 初中
    # ============================================================
    'junior': {
        '数学': {
            '七年级': [
                {'content': '计算：(-3) + 8 - 5 = ?',  'kp': '有理数运算'},
                {'content': '解方程：x + 3 = 7',        'kp': '一元一次方程'},
                {'content': '化简：2(3x - 1) - (x + 4)', 'kp': '整式的加减'},
                {'content': '解方程：3x - 5 = 10',       'kp': '一元一次方程-移项'},
                {'content': '解方程：2(x - 1) = x + 3',  'kp': '一元一次方程-去括号'},
            ],
            '八年级': [
                {'content': '计算：(a²)³ = ?',          'kp': '幂的运算'},
                {'content': '因式分解：x² - 9 = ?',      'kp': '平方差公式'},
                {'content': '在△ABC中，∠A=40°, ∠B=60°, ∠C=____°', 'kp': '三角形内角和'},
                {'content': '一次函数y=2x+1的斜率是？',   'kp': '一次函数'},
                {'content': '化简：(x+3)(x-3) = ?',      'kp': '乘法公式'},
            ],
            '九年级': [
                {'content': '解方程：x² - 5x + 6 = 0',   'kp': '一元二次方程'},
                {'content': '抛物线y=x²-4x+3的顶点坐标是？', 'kp': '二次函数'},
                {'content': '计算sin30°的值',            'kp': '锐角三角函数'},
                {'content': '相似比为1:2的两个三角形，面积比是？', 'kp': '相似三角形'},
                {'content': '概率：掷一枚骰子，出现偶数的概率是？', 'kp': '概率初步'},
            ],
        },
        '语文': {
            '七年级': [
                {'content': '"学而时习之"出自哪部经典？',  'kp': '文学常识'},
                {'content': '请默写《静夜思》的前两句',    'kp': '古诗默写'},
                {'content': '"他高兴得跳了起来"用了什么修辞？', 'kp': '修辞判断'},
                {'content': '"寂静"的反义词是？',         'kp': '词语辨析'},
                {'content': '朱自清的《春》描绘了哪几幅画面？', 'kp': '课文理解'},
            ],
        },
        '英语': {
            '七年级': [
                {'content': 'My name ____ Tom. (填 is / am / are)', 'kp': 'be动词用法'},
                {'content': 'She ____ (like) playing basketball. 用适当形式填空', 'kp': '一般现在时'},
                {'content': '请写出"go"的过去式',       'kp': '动词过去式'},
                {'content': '"some"通常用于 ____ 句。(肯定/否定/疑问)', 'kp': 'some与any'},
                {'content': 'There ____ a book and two pens on the desk. (is/are)', 'kp': 'There be句型'},
            ],
        },
        '物理': {
            '八年级': [
                {'content': '声音在空气中的传播速度约为 ____ m/s', 'kp': '声速'},
                {'content': '光在同种均匀介质中沿 ____ 传播', 'kp': '光的直线传播'},
                {'content': '1kg物体的重力约为 ____ N（取g=10N/kg）', 'kp': '重力计算'},
                {'content': '压强=压力÷____',            'kp': '压强公式'},
                {'content': '凸透镜对光有 ____ 作用（会聚/发散）', 'kp': '透镜'},
            ],
            '九年级': [
                {'content': '欧姆定律公式是 I = ____',   'kp': '欧姆定律'},
                {'content': '1度电 = ____ 千瓦时',       'kp': '电能单位'},
                {'content': '串联电路中，电流处处 ____',  'kp': '串联电路'},
                {'content': '同名磁极相互 ____（吸引/排斥）', 'kp': '磁极作用'},
                {'content': '功率P = W / ____',           'kp': '功率公式'},
            ],
        },
        '化学': {
            '九年级': [
                {'content': '水的化学式是？',             'kp': '化学式'},
                {'content': '氧的元素符号是？',            'kp': '元素符号'},
                {'content': '化学变化和物理变化的本质区别是？', 'kp': '物质变化'},
                {'content': '铁在氧气中燃烧生成 ____',    'kp': '化学反应'},
                {'content': 'pH=7的溶液是 ____ 性',       'kp': '酸碱盐'},
            ],
        },
        '生物': {
            '七年级': [
                {'content': '细胞的基本结构包括 ____、____ 和 ____', 'kp': '细胞结构'},
                {'content': '光合作用的场所是？',          'kp': '光合作用'},
                {'content': '人体消化和吸收的主要器官是？',  'kp': '消化系统'},
                {'content': '呼吸作用的主要场所是？',       'kp': '呼吸作用'},
                {'content': 'DNA的中文全称是？',           'kp': '遗传物质'},
            ],
        },
        '政治': {
            '七年级': [
                {'content': '我国的根本大法是？',          'kp': '宪法'},
                {'content': '公民最基本的人身权利是？',     'kp': '人身权利'},
                {'content': '法律最主要的特征是？',         'kp': '法律特征'},
                {'content': '未成年人是指未满 ____ 周岁的公民', 'kp': '未成年人保护'},
                {'content': '请写出社会主义核心价值观的三个层面', 'kp': '核心价值观'},
            ],
        },
        '历史': {
            '七年级': [
                {'content': '中国历史上第一个统一的封建王朝是？', 'kp': '秦朝'},
                {'content': '造纸术是在哪个朝代发明的？',   'kp': '四大发明'},
                {'content': '唐朝的开国皇帝是？',          'kp': '唐朝'},
                {'content': '丝绸之路的起点城市是？',       'kp': '丝绸之路'},
                {'content': '被称为"天下第一行书"的书法作品是？', 'kp': '书法艺术'},
            ],
        },
        '地理': {
            '七年级': [
                {'content': '地球的形状最接近一个 ____ 体', 'kp': '地球形状'},
                {'content': '赤道周长约为 ____ 万千米',    'kp': '地球数据'},
                {'content': '世界上最大的洋是？',          'kp': '世界地理'},
                {'content': '我国地势特征是 ____ 高 ____ 低', 'kp': '中国地形'},
                {'content': '影响气候的主要因素有？',       'kp': '气候因素'},
            ],
        },
    },
    # ============================================================
    # 高中
    # ============================================================
    'senior': {
        '数学': {
            '高一': [
                {'content': '若集合A={1,2,3}, B={2,3,4}，求A∩B', 'kp': '集合运算'},
                {'content': '解不等式：|x-2| ≤ 3',        'kp': '绝对值不等式'},
                {'content': '求f(3)=2×3²-3×3+1的值',     'kp': '二次函数求值'},
                {'content': '已知sinα=3/5，cosα=?（锐角）', 'kp': '三角函数'},
                {'content': '直线y=2x+1的斜率是？',        'kp': '直线方程'},
            ],
            '高二': [
                {'content': '求导数：f(x)=x³-3x的导函数',  'kp': '导数计算'},
                {'content': '在等差数列{an}中，a₁=2,d=3,a₅=?', 'kp': '等差数列'},
                {'content': '椭圆x²/9+y²/4=1的焦点在哪个轴上？', 'kp': '椭圆'},
                {'content': '已知向量a=(1,2),b=(3,4)，求a·b', 'kp': '向量数量积'},
                {'content': '抛物线y²=4x的焦点坐标是？',     'kp': '抛物线'},
            ],
            '高三': [
                {'content': '求定积分∫₀¹(2x+1)dx',        'kp': '定积分'},
                {'content': '复数(1+i)² = ?',             'kp': '复数运算'},
                {'content': '二项式(x+1)⁴展开式中x²的系数是？', 'kp': '二项式定理'},
                {'content': '一个袋子有3红2白球，任取1球为红的概率？', 'kp': '古典概型'},
                {'content': '用数学归纳法证明的第一步是验证n=____', 'kp': '数学归纳法'},
            ],
        },
        '语文': {
            '高一': [
                {'content': '《红楼梦》的作者是？',         'kp': '文学常识'},
                {'content': '"落霞与孤鹜齐飞"出自哪篇文章？', 'kp': '古文名篇'},
                {'content': '鲁迅的第一篇白话小说是？',     'kp': '现代文学'},
                {'content': '请分析"春风又绿江南岸"中"绿"字的妙处', 'kp': '诗歌鉴赏'},
                {'content': '议论文的三要素是？',           'kp': '议论文写作'},
            ],
        },
        '英语': {
            '高一': [
                {'content': 'I have ____ (see) the movie twice. 用适当形式填空', 'kp': '现在完成时'},
                {'content': 'The book ____ (write) by Lu Xun. 用被动语态填空', 'kp': '被动语态'},
                {'content': 'If I ____ (be) you, I would study harder. 用虚拟语气填空', 'kp': '虚拟语气'},
                {'content': 'She asked me ____ I had finished my homework. (填that/if/what)', 'kp': '宾语从句'},
                {'content': 'Not until he arrived ____ (do) he know the truth.', 'kp': '倒装句'},
            ],
        },
        '物理': {
            '高一': [
                {'content': '牛顿第二定律的表达式是 F = ____', 'kp': '牛顿定律'},
                {'content': '自由落体运动的加速度g ≈ ____ m/s²', 'kp': '自由落体'},
                {'content': '做匀速圆周运动的物体，向心力方向指向 ____', 'kp': '圆周运动'},
                {'content': '动能定理：合外力做功 = ____ 的变化量', 'kp': '动能定理'},
                {'content': '两个共点力F₁=3N,F₂=4N夹角90°，合力=____N', 'kp': '力的合成'},
            ],
        },
        '化学': {
            '高一': [
                {'content': '钠的元素符号是？',             'kp': '元素符号'},
                {'content': '写出H₂SO₄的名称',             'kp': '化学物质'},
                {'content': '氧化还原反应的本质是电子的 ____', 'kp': '氧化还原'},
                {'content': '1mol气体在标准状况下的体积约为 ____ L', 'kp': '物质的量'},
                {'content': '写出钠与水反应的化学方程式',     'kp': '化学方程式'},
            ],
        },
        '生物': {
            '高一': [
                {'content': 'DNA的基本组成单位是？',        'kp': 'DNA结构'},
                {'content': '有氧呼吸三个阶段中释放能量最多的是？', 'kp': '细胞呼吸'},
                {'content': '减数分裂的结果是染色体数目 ____', 'kp': '减数分裂'},
                {'content': '基因分离定律的核心是等位基因 ____', 'kp': '遗传定律'},
                {'content': '自然选择学说的核心观点是？',     'kp': '进化论'},
            ],
        },
        '政治': {
            '高一': [
                {'content': '商品的两个基本属性是？',         'kp': '商品属性'},
                {'content': '价值规律的基本内容是？',         'kp': '价值规律'},
                {'content': '我国的基本经济制度是？',         'kp': '经济制度'},
                {'content': '货币的本质是？',               'kp': '货币'},
                {'content': '市场经济中，资源配置的两种基本手段是？', 'kp': '市场经济'},
            ],
        },
        '历史': {
            '高一': [
                {'content': '辛亥革命爆发于哪一年？',         'kp': '辛亥革命'},
                {'content': '鸦片战争后签订的第一个不平等条约是？', 'kp': '鸦片战争'},
                {'content': '五四运动爆发的导火索是？',       'kp': '五四运动'},
                {'content': '标志着中国共产党诞生的会议是？',  'kp': '中共成立'},
                {'content': '新航路开辟中，哥伦布到达了 ____ 洲', 'kp': '新航路开辟'},
            ],
        },
        '地理': {
            '高一': [
                {'content': '地球自转产生了 ____ 现象',      'kp': '地球自转'},
                {'content': '大气对太阳辐射的削弱作用不包括 ____', 'kp': '大气热力'},
                {'content': '世界人口分布最密集的地区是？',    'kp': '人口分布'},
                {'content': '我国最大的淡水湖是？',           'kp': '中国地理'},
                {'content': '热带雨林气候的特征是？',          'kp': '气候类型'},
            ],
        },
    },
    # ============================================================
    # 大学
    # ============================================================
    'university': {
        '高等数学': {
            '大一': [
                {'content': '求极限 lim(x→0) sin(x)/x = ?', 'kp': '函数极限'},
                {'content': '求导数：f(x)=x²eˣ的导函数',     'kp': '导数计算'},
                {'content': '求不定积分 ∫(2x+1)dx',        'kp': '不定积分'},
                {'content': '矩阵A=[[1,2],[3,4]]，求det(A)', 'kp': '行列式'},
                {'content': '判断敛散性：∑(1/n²) (n=1→∞)',   'kp': '级数判别'},
            ],
            '大二': [
                {'content': '计算二重积分∬(x+y)dxdy，区域D=[0,1]×[0,1]', 'kp': '二重积分'},
                {'content': '求解微分方程 y\'+y=0 的通解',   'kp': '微分方程'},
                {'content': '求矩阵A=[[1,0],[0,2]]的特征值',  'kp': '特征值'},
                {'content': '写出傅里叶级数的一般形式',        'kp': '傅里叶级数'},
                {'content': '偏导数∂f/∂x中，f(x,y)=x²y+xy²', 'kp': '偏导数'},
            ],
        },
        '大学英语': {
            '大一': [
                {'content': 'Translate: "努力学习" (into English)', 'kp': '词汇翻译'},
                {'content': 'The number of students ____ increasing. (is/are)', 'kp': '主谓一致'},
                {'content': 'He suggested that we ____ (start) early.', 'kp': '虚拟语气'},
                {'content': 'It is important ____ (learn) a foreign language.', 'kp': '不定式'},
                {'content': 'Reading comprehension: What is the main idea of the passage?', 'kp': '阅读理解'},
            ],
        },
        '线性代数': {
            '大一': [
                {'content': '矩阵A的秩定义为？',             'kp': '矩阵的秩'},
                {'content': 'n阶方阵可逆的充要条件是秩=____',  'kp': '可逆矩阵'},
                {'content': '齐次线性方程组Ax=0有非零解⇔|A|____0', 'kp': '方程组解'},
                {'content': '向量组线性无关的定义是？',       'kp': '线性相关'},
                {'content': '求矩阵[[2,1],[1,2]]的特征值',   'kp': '特征值计算'},
            ],
        },
        '概率论': {
            '大一': [
                {'content': '设P(A)=0.3,P(B)=0.4,A与B互斥，求P(A∪B)', 'kp': '概率加法'},
                {'content': '正态分布N(0,1)的期望是？',       'kp': '正态分布'},
                {'content': '掷两枚硬币，至少一枚正面的概率？',   'kp': '古典概型'},
                {'content': '随机变量X的方差D(X)=？',         'kp': '方差公式'},
                {'content': '设X~B(10,0.5)，求E(X)',         'kp': '二项分布'},
            ],
        },
        'Python程序设计': {
            '大一': [
                {'content': 'Python中如何声明一个列表？',     'kp': '列表'},
                {'content': '写出for循环遍历range(5)的代码',  'kp': 'for循环'},
                {'content': 'Python中如何定义一个函数？',     'kp': '函数定义'},
                {'content': 'dict的key-value对如何访问？',    'kp': '字典'},
                {'content': '如何用Python读取一个文件？',     'kp': '文件操作'},
            ],
        },
        'C语言': {
            '大一': [
                {'content': 'C语言中int类型占几个字节？',     'kp': '数据类型'},
                {'content': '写出C语言中main函数的标准格式',   'kp': '函数结构'},
                {'content': 'C语言中如何用malloc动态分配内存？', 'kp': '动态内存'},
                {'content': '指针变量存储的是变量的 ____',      'kp': '指针'},
                {'content': '数组int a[5]中，a[0]是第几个元素？', 'kp': '数组'},
            ],
        },
        '数据结构': {
            '大二': [
                {'content': '栈的特点是 ____ 先出',           'kp': '栈'},
                {'content': '二叉树的三种遍历方式是？',        'kp': '二叉树遍历'},
                {'content': '冒泡排序的时间复杂度是O(____)',    'kp': '排序算法'},
                {'content': '链表与数组相比，____ 操作更高效',   'kp': '链表'},
                {'content': '哈希表查找的平均时间复杂度是O(____)', 'kp': '哈希表'},
            ],
        },
    },
}

# 默认年级回退（当精确年级未命中时）
_DEFAULT_GRADE: dict = {
    'primary': {'数学': '三年级', '语文': '三年级', '英语': '三年级', '科学': '三年级'},
    'junior': {'数学': '七年级', '语文': '七年级', '英语': '七年级',
               '物理': '八年级', '化学': '九年级', '生物': '七年级',
               '政治': '七年级', '历史': '七年级', '地理': '七年级'},
    'senior': {'数学': '高一', '语文': '高一', '英语': '高一',
               '物理': '高一', '化学': '高一', '生物': '高一',
               '政治': '高一', '历史': '高一', '地理': '高一'},
    'university': {'高等数学': '大一', '大学英语': '大一', '线性代数': '大一',
                   '概率论': '大一', 'Python程序设计': '大一', 'C语言': '大一',
                   '数据结构': '大二'},
}

DIAGNOSTIC_QUESTION_COUNT = 5


class DiagnosticService:
    def __init__(self, mapper: Optional[DiagnosticMapper] = None, profile_mapper: Optional[UserProfileMapper] = None):
        self._mapper = mapper
        self._profile_mapper = profile_mapper

    @property
    def mapper(self) -> DiagnosticMapper:
        if self._mapper is None:
            self._mapper = DiagnosticMapper(
                __import__('backend.model', fromlist=['AsyncSessionLocal']).AsyncSessionLocal
            )
        return self._mapper

    @property
    def profile_mapper(self) -> UserProfileMapper:
        if self._profile_mapper is None:
            self._profile_mapper = UserProfileMapper(
                __import__('backend.model', fromlist=['AsyncSessionLocal']).AsyncSessionLocal
            )
        return self._profile_mapper

    # ------------------------------------------------------------------
    # 查询掌握度（从最近一次诊断结果）
    # ------------------------------------------------------------------

    async def get_latest_masteries(self, user_id: int) -> list[dict]:
        """查询当前学生最近一次已完成/已跳过的诊断中的知识点掌握度。

        按诊断时间倒序，取最新一条 completed 或 skipped 的会话，
        从诊断答案中汇总每个知识点的掌握度。
        """
        from backend.model import AsyncSessionLocal
        from sqlalchemy import select, desc

        async with AsyncSessionLocal() as session:
            # 查询最新完成的诊断会话
            stmt = (
                select(DiagnosticSession)
                .where(
                    DiagnosticSession.user_id == user_id,
                    DiagnosticSession.status.in_(('completed', 'skipped')),
                )
                .order_by(desc(DiagnosticSession.id))
                .limit(1)
            )
            result = await session.execute(stmt)
            diag = result.scalar_one_or_none()

            if diag is None:
                return []

            # 查询该会话的所有题目
            stmt = select(DiagnosticAnswer).where(
                DiagnosticAnswer.diagnostic_id == diag.id
            ).order_by(DiagnosticAnswer.question_id)
            result = await session.execute(stmt)
            answers = result.scalars().all()

            # 按知识点汇总
            masteries: dict[str, dict] = {}
            for a in answers:
                kp = a.knowledge_point_name or '未知知识点'
                if kp not in masteries:
                    masteries[kp] = {
                        'knowledge_point_id': a.knowledge_point_id or 0,
                        'knowledge_point_name': kp,
                        'score': 60,
                        'answer_count': 0,
                        'correct_count': 0,
                    }
                masteries[kp]['answer_count'] += 1
                if a.is_correct:
                    masteries[kp]['correct_count'] += 1
                    masteries[kp]['score'] = min(100, masteries[kp]['score'] + 3)
                else:
                    masteries[kp]['score'] = max(0, masteries[kp]['score'] - 3)

            return [
                {
                    'knowledge_point_id': m['knowledge_point_id'],
                    'knowledge_point_name': m['knowledge_point_name'],
                    'mastery_score': m['score'],
                    'learning_status': self._score_to_status(m['score']),
                    'answer_count': m['answer_count'],
                    'correct_count': m['correct_count'],
                }
                for m in masteries.values()
            ]

    # ------------------------------------------------------------------
    # 查询诊断状态
    # ------------------------------------------------------------------

    async def get_status(self, user_id: int) -> DiagnosticStatusResponse:
        p = await self.profile_mapper.get_by_user_id(user_id)
        if p is None or p.diagnostic_status == 'required':
            return DiagnosticStatusResponse(status='required')

        if p.diagnostic_status == 'in_progress':
            session = await self.mapper.get_latest_in_progress(user_id)
            return DiagnosticStatusResponse(status='in_progress', diagnostic_id=session.id if session else None)

        return DiagnosticStatusResponse(status=p.diagnostic_status)

    # ------------------------------------------------------------------
    # 开始诊断
    # ------------------------------------------------------------------

    async def start_diagnostic(self, user_id: int) -> DiagnosticStartResponse:
        p = await self._get_and_validate_profile(user_id)

        if p.diagnostic_status == 'completed':
            raise BusinessError('DIAGNOSTIC_ALREADY_COMPLETED', '已完成首次诊断，无需再次诊断', 409)

        # 如果已有进行中的诊断且画像未被重置，直接返回旧会话
        existing = await self.mapper.get_latest_in_progress(user_id)
        if existing and p.diagnostic_status == 'in_progress':
            answers = await self.mapper.get_answers(existing.id)
            if answers:
                return DiagnosticStartResponse(
                    diagnostic_id=existing.id,
                    question_count=existing.question_count,
                    questions=[self._answer_to_question(a) for a in answers],
                )
        # 画像被重置 → 关闭旧会话，下面会生成新题
        if existing and p.diagnostic_status != 'in_progress':
            await self.mapper.update_session_status(existing.id, 'skipped')

        # 按学段×年级×学科生成诊断题
        questions = self._generate_questions(p.stage, p.grade, p.subject)
        session = await self.mapper.create_session(user_id, len(questions))

        # 持久化题目
        answers = [
            DiagnosticAnswer(
                diagnostic_id=session.id,
                question_id=q['question_id'],
                content=q['content'],
                question_type=q.get('question_type', 'short_answer'),
                difficulty=q.get('difficulty', 'easy'),
                knowledge_point_id=q.get('knowledge_point_id'),
                knowledge_point_name=q.get('knowledge_point_name'),
            )
            for q in questions
        ]
        await self.mapper.save_answers(session.id, answers)

        # 标记画像诊断状态
        await self.profile_mapper.update(user_id, diagnostic_status='in_progress')

        return DiagnosticStartResponse(
            diagnostic_id=session.id,
            question_count=len(questions),
            questions=[self._question_to_item(q) for q in questions],
        )

    # ------------------------------------------------------------------
    # 提交诊断
    # ------------------------------------------------------------------

    async def submit_diagnostic(self, user_id: int, req: DiagnosticSubmitRequest) -> DiagnosticSubmitResponse:
        p = await self._get_and_validate_profile(user_id)

        session = await self.mapper.get_session(req.diagnostic_id, user_id)
        if session is None:
            raise BusinessError('DIAGNOSTIC_NOT_FOUND', '诊断会话不存在', 404)

        if session.status != 'in_progress':
            raise BusinessError('DIAGNOSTIC_ALREADY_COMPLETED', '该诊断已完成或已跳过', 409)

        stored_answers = await self.mapper.get_answers(session.id)
        stored_map = {a.question_id: a for a in stored_answers}

        # 判题并累计掌握度（按《系统业务设计》评分规则）
        # 基础分 60，诊断题均为 easy，答对 +3、答错 -3
        masteries: dict[str, dict] = {}
        for item in req.answers:
            stored = stored_map.get(item.question_id)
            if stored is None:
                continue
            correct = self._judge_answer(item.answer, stored.content)
            await self.mapper.update_answer(stored.id, item.answer, correct)

            kp_name = stored.knowledge_point_name or '未知知识点'
            kp_id = stored.knowledge_point_id or 0
            if kp_name not in masteries:
                masteries[kp_name] = {
                    'knowledge_point_id': kp_id,
                    'knowledge_point_name': kp_name,
                    'score': 60,
                }
            delta = 3 if correct else -3
            masteries[kp_name]['score'] = max(0, min(100, masteries[kp_name]['score'] + delta))

        # 标记诊断完成
        await self.mapper.update_session_status(session.id, 'completed')
        await self.profile_mapper.update(user_id, diagnostic_status='completed')

        mastery_list = [
            MasteryItem(
                knowledge_point_id=m['knowledge_point_id'],
                knowledge_point_name=m['knowledge_point_name'],
                mastery_score=m['score'],
                learning_status=self._score_to_status(m['score']),
            )
            for m in masteries.values()
        ]

        return DiagnosticSubmitResponse(status='completed', masteries=mastery_list)

    # ------------------------------------------------------------------
    # 跳过诊断
    # ------------------------------------------------------------------

    async def skip_diagnostic(self, user_id: int) -> DiagnosticSubmitResponse:
        p = await self._get_and_validate_profile(user_id)

        if p.diagnostic_status == 'completed':
            raise BusinessError('DIAGNOSTIC_ALREADY_COMPLETED', '已完成首次诊断，无需跳过', 409)

        # 关闭旧的进行中的会话
        existing = await self.mapper.get_latest_in_progress(user_id)
        if existing:
            await self.mapper.update_session_status(existing.id, 'skipped')

        # 生成诊断题以确定涉及的知识点，全部初始化为 60
        questions = self._generate_questions(p.stage, p.grade, p.subject)
        session = await self.mapper.create_session(user_id, len(questions))

        # 持久化题目（跳过时答案为跳过标记）
        answers = [
            DiagnosticAnswer(
                diagnostic_id=session.id,
                question_id=q['question_id'],
                content=q['content'],
                question_type=q.get('question_type', 'short_answer'),
                difficulty=q.get('difficulty', 'easy'),
                knowledge_point_id=q.get('knowledge_point_id'),
                knowledge_point_name=q.get('knowledge_point_name'),
                user_answer='[跳过]',
                is_correct=None,
            )
            for q in questions
        ]
        await self.mapper.save_answers(session.id, answers)
        await self.mapper.update_session_status(session.id, 'skipped')
        await self.profile_mapper.update(user_id, diagnostic_status='skipped')

        # 所有知识点初始掌握度均为 60
        seen: set[str] = set()
        mastery_list: list[MasteryItem] = []
        for q in questions:
            kp = q.get('knowledge_point_name', '')
            if kp and kp not in seen:
                seen.add(kp)
                mastery_list.append(MasteryItem(
                    knowledge_point_id=q.get('knowledge_point_id', 0),
                    knowledge_point_name=kp,
                    mastery_score=60,
                    learning_status='consolidating',
                ))

        return DiagnosticSubmitResponse(status='skipped', masteries=mastery_list)

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    async def _get_and_validate_profile(self, user_id: int):
        p = await self.profile_mapper.get_by_user_id(user_id)
        if p is None or not p.stage or not p.grade or not p.subject:
            raise BusinessError('PROFILE_NOT_COMPLETED', '请先完善学习信息（学段、年级、学科）', 400)
        return p

    def _generate_questions(self, stage: str, grade: str, subject: str) -> List[dict]:
        """按学段×年级×学科从预置题库选取诊断题。

        优先级：
        1. 精确匹配 stage → subject → grade
        2. 同 stage 同 subject 的默认年级
        3. 同 stage 同 subject（任一可用年级）
        4. 回退到初中数学
        """
        # 1. 精确匹配
        questions = self._fetch_questions(stage, subject, grade)
        if questions:
            return self._build_questions(questions)

        # 2. 默认年级回退
        default_grade = _DEFAULT_GRADE.get(stage, {}).get(subject, '')
        if default_grade and default_grade != grade:
            questions = self._fetch_questions(stage, subject, default_grade)
            if questions:
                return self._build_questions(questions)

        # 3. 同stage同subject任意年级
        questions = self._fetch_any_grade(stage, subject)
        if questions:
            return self._build_questions(questions)

        # 4. 终极回退：初中数学
        questions = self._fetch_questions('junior', '数学', '七年级')
        return self._build_questions(questions)

    def _fetch_questions(self, stage: str, subject: str, grade: str) -> list:
        """获取指定 stage/subject/grade 下的题目列表。"""
        stage_data = _Q.get(stage, {})
        subject_data = stage_data.get(subject, {})
        return subject_data.get(grade, [])

    def _fetch_any_grade(self, stage: str, subject: str) -> list:
        """获取同 stage 同 subject 下任意年级的题目。"""
        stage_data = _Q.get(stage, {})
        subject_data = stage_data.get(subject, {})
        for grade_questions in subject_data.values():
            if grade_questions:
                return grade_questions
        return []

    def _build_questions(self, questions: list) -> List[dict]:
        """从题目池中随机选取 DIAGNOSTIC_QUESTION_COUNT 道，组装为标准结构。"""
        pool = list(questions)  # 不修改原始数据
        random.shuffle(pool)
        selected = pool[:DIAGNOSTIC_QUESTION_COUNT]
        return [
            {
                'question_id': i + 1,
                'content': q['content'],
                'question_type': 'short_answer',
                'difficulty': 'easy',
                'knowledge_point_id': hash(q.get('kp', '')) % 10000,
                'knowledge_point_name': q.get('kp', ''),
            }
            for i, q in enumerate(selected)
        ]

    def _judge_answer(self, user_answer: str, correct_content: str) -> bool:
        """简单判题：去除空格后比较。"""
        ua = user_answer.strip().replace(' ', '').lower()
        expected = self._extract_expected(correct_content)
        return ua == expected

    def _extract_expected(self, content: str) -> str:
        """从题目中提取期望答案（简化版）。"""
        import re
        m = re.search(r'[=＝]\s*(\S+)', content)
        if m:
            return m.group(1).strip().replace(' ', '').replace('?', '').replace('？', '').lower()
        return ''

    def _question_to_item(self, q: dict) -> QuestionItem:
        return QuestionItem(
            question_id=q['question_id'],
            content=q['content'],
            question_type=q.get('question_type', 'short_answer'),
            difficulty=q.get('difficulty', 'easy'),
            knowledge_point_id=q.get('knowledge_point_id'),
            knowledge_point_name=q.get('knowledge_point_name'),
        )

    def _answer_to_question(self, a) -> QuestionItem:
        return QuestionItem(
            question_id=a.question_id,
            content=a.content,
            question_type=a.question_type,
            difficulty=a.difficulty,
            knowledge_point_id=a.knowledge_point_id,
            knowledge_point_name=a.knowledge_point_name,
        )

    @staticmethod
    def _score_to_status(score: int) -> str:
        if score >= 81:
            return 'mastered'
        if score >= 60:
            return 'consolidating'
        return 'weak'


# 单例
_diagnostic_service: Optional[DiagnosticService] = None


async def get_diagnostic_service() -> DiagnosticService:
    global _diagnostic_service
    if _diagnostic_service is None:
        _diagnostic_service = DiagnosticService()
    return _diagnostic_service

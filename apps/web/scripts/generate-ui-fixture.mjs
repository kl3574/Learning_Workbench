import {createHash} from 'node:crypto'
import {writeFileSync} from 'node:fs'
const canonical = value => JSON.stringify(value, (_,v) => v && typeof v === 'object' && !Array.isArray(v) ? Object.fromEntries(Object.entries(v).sort(([a],[b]) => a.localeCompare(b,'en'))) : v)
const ref = (entity,id,object) => ({entity,id,revision:1,sha256:createHash('sha256').update(canonical(object),'utf8').digest('hex')})
const chapterNames = ['观察、变量与一个小模型','从误差到平方和','条件与唯一性的边界','向量与几何直觉','矩阵表达与维度检查','计算过程与结果复核','假设变化后的修订比较','回顾与后续学习方向']
const sectionNames = ['本章目标与思路','变量、定义域与记号','从一个简单例子开始理解推导中的条件与边界','逐步展开计算','一个需要仔细核对适用条件的长中文标题示例：当观测数量变化时如何理解结论','边界、小结与下一步']
const lessons = chapterNames.flatMap((_,ci)=>sectionNames.map((title,li)=>{
 const id=`synthetic_lesson_${ci+1}_${li+1}`
 const body=`这是一段**合成排版材料**，用于检查阅读工作台。它不是已审核教材，也不代表任何人的真实学习记录。\n\n## 目标与逻辑链\n\n明确变量 → 写出条件 → 展开计算 → 检查边界。这里令 $x\\in\\mathbb{R}$，通过一个小例子检查数学显示与阅读节奏。\n\n## 定义与条件\n\n对给定实数 $a$，考虑函数 $f(x)=(x-a)^2$。因为平方非负，当且仅当 $x=a$ 时取零。\n\n$$\nf(x)=(x-a)^2=x^2-2ax+a^2\\geq 0\n$$\n\n### 例题 · 逐步检查\n\n取 $a=2$。代入 $x=3$ 得 $(3-2)^2=1$；代入 $x=2$ 得零。这一段是教材内的完整算例展示，并未建立练习或测试。\n\n## 长公式排版检查\n\n下式故意较长；超出阅读宽度的部分应在公式内部滚动。\n\n$$\n\\underbrace{(x-a)^2+(x-a)^2+(x-a)^2+(x-a)^2+(x-a)^2+(x-a)^2+(x-a)^2+(x-a)^2}_{\\text{eight identical terms}}=8x^2-16ax+8a^2\\geq 0\n$$\n\n## 边界与小结\n\n本例只讨论实数平方；换用其他定义域时应重新检查条件。页面支持选文预览，并保留原始 LaTeX。\n\n| 检查对象 | 状态说明 |\n| --- | --- |\n| 数学显示 | 本地 MathJax SVG |\n| 样例身份 | 合成 UI 数据 |\n| 学习证据 | 未创建 |\n\n\\n第 ${ci+1} 章，第 ${li+1} 节。`
 const object={id,title:`${ci+1}.${li+1} ${title}`,body,revision:1,synthetic:true}
 return {...object,chapter:ci+1,number:li+1,ref:ref('lesson',id,object),sampleState:ci===0&&li===0?'read':ci===0&&li===4?'stale':'unread'}
}))
const course={id:'synthetic_course_layout',title:'理解模型、条件与计算：合成阅读工作台示例课程',revision:1,synthetic:true,lesson_refs:lessons.map(l=>l.ref)}
const data={notice:'仅用于界面验收的合成示例；已读和过期是展示状态，不产生真实阅读、成绩或掌握证据。',course:{...course,ref:ref('course',course.id,course)},chapters:chapterNames.map((title,i)=>({id:`synthetic_chapter_${i+1}`,title:`第 ${i+1} 章 ${title}`,lessonIds:lessons.filter(l=>l.chapter===i+1).map(l=>l.id)})),lessons}
writeFileSync('src/features/synthetic-course.json',JSON.stringify(data,null,2)+'\n')
console.log(`Generated explicitly synthetic UI fixture: ${data.chapters.length} chapters, ${lessons.length} lessons; SHA-256 computed from canonical UTF-8 objects.`)

import { mathjax } from '@mathjax/src/js/mathjax.js'
import { TeX } from '@mathjax/src/js/input/tex.js'
import { SVG } from '@mathjax/src/js/output/svg.js'
import { liteAdaptor } from '@mathjax/src/js/adaptors/liteAdaptor.js'
import { RegisterHTMLHandler } from '@mathjax/src/js/handlers/html.js'
import { MathJaxTexFont } from '@mathjax/mathjax-tex-font/js/svg.js'
import '@mathjax/src/js/input/tex/base/BaseConfiguration.js'
import '@mathjax/src/js/input/tex/ams/AmsConfiguration.js'
const adaptor = liteAdaptor()
RegisterHTMLHandler(adaptor)
const document = mathjax.document('', {
  InputJax: new TeX({ packages: ['base', 'ams'], maxBuffer: 12000, maxMacros: 1000 }),
  OutputJax: new SVG({ fontData: new MathJaxTexFont(), fontCache: 'local', displayOverflow: 'scroll' }),
})
// These packages are deliberately absent: require, autoload, html, newcommand.
export function mathSvg(source: string, display: boolean): string {
  if (source.length > 12000 || /\\(?:require|href|url|htmlClass|htmlId|htmlStyle|includegraphics|def|gdef|newcommand|renewcommand|csname)\b/.test(source)) throw new Error('公式超出本地宏白名单或长度限制')
  let node
  try { node = document.convert(source, { display }) } catch { throw new Error('此公式当前无法在本地渲染') }
  const result = adaptor.outerHTML(node)
  if (result.includes('data-mjx-error')) throw new Error('MathJax 不支持此公式；原始 LaTeX 已保留')
  return result
}

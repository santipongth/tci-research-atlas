import { describe, expect, it } from 'vitest'
import { bibEscape, toBibtex, toRis, type CiteRecord } from './citation'

const TH = 'การตลาดดิจิทัลของวิสาหกิจชุมชน'
const records: CiteRecord[] = [
  { id: 'so02:example0:10001', titleTh: TH, titleEn: 'Digital marketing of community enterprises', journal: 'วารสารวิชาการตัวอย่าง ก', year: 2023, doi: '10.14456/example.2023.10001', url: 'https://so02.tci-thaijo.org/index.php/example0/article/view/10001' },
  { id: 'so02:example3:20002', titleTh: '', titleEn: 'R&D {braces} 50% of $x_1^2 #3 ~ \\ok', journal: 'Example Journal of Science', year: null, doi: null, url: null },
]

describe('RIS', () => {
  const ris = toRis(records, '2026Q4')
  const lines = ris.split('\r\n')

  it('writes one JOUR record per article with the Thai title first and the English one as translated title', () => {
    expect(lines.filter((l) => l === 'TY  - JOUR')).toHaveLength(2)
    expect(lines.filter((l) => l.startsWith('ER  -'))).toHaveLength(2)
    expect(lines).toContain(`TI  - ${TH}`)
    expect(lines).toContain('TT  - Digital marketing of community enterprises')
    expect(lines).toContain('T2  - วารสารวิชาการตัวอย่าง ก')
    expect(lines).toContain('PY  - 2023')
    expect(lines).toContain('DO  - 10.14456/example.2023.10001')
    expect(lines).toContain('UR  - https://so02.tci-thaijo.org/index.php/example0/article/view/10001')
    expect(lines.filter((l) => l === 'N1  - Source: TCI Research Atlas 2026Q4')).toHaveLength(2)
  })

  it('uses the English title when there is no Thai one and leaves out empty fields', () => {
    const second = lines.slice(lines.lastIndexOf('TY  - JOUR'))
    expect(second).toContain('TI  - R&D {braces} 50% of $x_1^2 #3 ~ \\ok')
    expect(second.some((l) => /^(TT|PY|DO|UR) {2}-/.test(l))).toBe(false)
  })

  it('never writes an author', () => {
    expect(lines.some((l) => /^(AU|A1|A2|A3|A4) {2}-/.test(l))).toBe(false)
  })
})

describe('BibTeX', () => {
  const bib = toBibtex(records, '2026Q4')

  it('writes @article entries with Thai titles kept as they are', () => {
    expect(bib.match(/@article\{/g)).toHaveLength(2)
    expect(bib).toContain('@article{tci:so02:example0:10001,')
    expect(bib).toContain(`title = {${TH}},`)
    expect(bib).toContain('journal = {วารสารวิชาการตัวอย่าง ก},')
    expect(bib).toContain('year = {2023},')
    expect(bib).toContain('doi = {10.14456/example.2023.10001},')
    expect(bib).toContain('note = {Digital marketing of community enterprises. Source: TCI Research Atlas 2026Q4},')
  })

  it('escapes LaTeX special characters so braces always balance', () => {
    expect(bibEscape('R&D {braces} 50% of $x_1^2 #3 ~ \\ok')).toBe('R\\&D \\{braces\\} 50\\% of \\$x\\_1\\^{}2 \\#3 \\~{} \\textbackslash{}ok')
    for (const entry of bib.split('\n@')) {
      let depth = 0
      for (let i = 0; i < entry.length; i++) {
        if (entry[i] === '\\') {
          i++
          continue
        }
        if (entry[i] === '{') depth++
        if (entry[i] === '}') depth--
        expect(depth).toBeGreaterThanOrEqual(0)
      }
      expect(depth).toBe(0)
    }
  })

  it('gives every entry a distinct key and never writes an author', () => {
    const twice = toBibtex([records[1], records[1]], '2026Q4')
    expect(twice).toContain('@article{tci:so02:example3:20002,')
    expect(twice).toContain('@article{tci:so02:example3:20002-2,')
    expect(/\bauthor\s*=/i.test(bib + twice)).toBe(false)
  })
})

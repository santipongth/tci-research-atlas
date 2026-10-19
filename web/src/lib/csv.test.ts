import { describe, expect, it } from 'vitest'
import { csvCell, toCsv } from './csv'

describe('CSV', () => {
  it('starts with a BOM, uses CRLF and keeps raw numbers', () => {
    const csv = toCsv([{ id: 'T000201', th: 'AI เพื่อการศึกษา', g: 0.1234 }], [
      { header: 'id', value: (r) => r.id },
      { header: 'name_th', value: (r) => r.th },
      { header: 'share_growth', value: (r) => r.g },
    ])
    expect(csv).toBe('﻿id,name_th,share_growth\r\nT000201,AI เพื่อการศึกษา,0.1234\r\n')
  })

  it('quotes separators, quotes and newlines; leaves missing values empty', () => {
    expect(csvCell('a,b')).toBe('"a,b"')
    expect(csvCell('say "hi"')).toBe('"say ""hi"""')
    expect(csvCell('two\nlines')).toBe('"two\nlines"')
    expect(csvCell(null)).toBe('')
    expect(csvCell(Number.NaN)).toBe('')
    expect(csvCell(true)).toBe('true')
  })

  it('neutralises spreadsheet formulas in text cells', () => {
    expect(csvCell('=SUM(A1)')).toBe("'=SUM(A1)")
    expect(csvCell('@cmd')).toBe("'@cmd")
    expect(csvCell(-3)).toBe('-3')
  })
})

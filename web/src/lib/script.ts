/** Any character of the Thai block (U+0E00–U+0E7F): which text is Thai, for `lang` attributes and name rules. */
export const THAI = new RegExp(`[${String.fromCodePoint(0x0e00)}-${String.fromCodePoint(0x0e7f)}]`)

/** The `lang` attribute for a piece of text: Thai when it has any Thai letter, else English. */
export const langOf = (text: string): 'th' | 'en' => (THAI.test(text) ? 'th' : 'en')

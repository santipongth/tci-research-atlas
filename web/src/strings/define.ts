/** One UI string in both languages. Every string the UI shows is an Entry in src/strings/*.ts. */
export interface Entry {
  th: string
  en: string
}

export function defineStrings<T extends Record<string, Entry>>(d: T): T {
  return d
}

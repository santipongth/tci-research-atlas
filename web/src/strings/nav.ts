import { defineStrings } from './define'

/** The site navigation: page names, the question groups and the one-line hints under each name (desktop menu). */
export const nav = defineStrings({
  'nav.journals': { th: 'วารสาร', en: 'Journals' },
  'nav.topics': { th: 'หัวข้อวิจัย', en: 'Research topics' },
  'nav.places': { th: 'สถาบันและจังหวัด', en: 'Institutions and provinces' },
  'nav.goals': { th: 'เป้าหมายชาติและโลก', en: 'National and global goals' },
  'nav.sec.dash': { th: 'แดชบอร์ด', en: 'Dashboards' },
  'nav.sec.maps': { th: 'แผนที่', en: 'Maps' },
  'nav.sec.help': { th: 'คำอธิบาย', en: 'Help' },
})

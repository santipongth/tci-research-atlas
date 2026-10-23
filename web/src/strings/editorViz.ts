import { defineStrings } from './define'

/**
 * The editors' pages as infographics (web refresh, batch 6): the journals scatter and special-issue cards, one journal's
 * then-vs-now topic mix and record checklist, the methods bar ranking, the /match example and result cards, and the
 * compare page's small multiples. Lazy pages only (read with useStrings) — kept out of the entry chunk.
 */
export const editorViz = defineStrings({
  'js.h': { th: 'ข้อมูลบทความครบแค่ไหน และผู้เขียนมาจากเจ้าของวารสารแค่ไหน', en: 'How complete the records are, and how many authors come from the owner' },
  'js.intro': {
    th: 'เช่น “{j}” ข้อมูลบทความครบ {c} เต็ม 100 และ {p} ของบทความมีผู้เขียนจากเจ้าของวารสาร ทั้งสองเรื่องนี้บรรณาธิการปรับได้เองก่อนถึงรอบประเมิน',
    en: 'For example, “{j}” scores {c} out of 100 for complete records, and {p} of its articles have an author from the owner. Both are things an editor can change before an assessment.',
  },
  'js.fig': { th: 'วารสารแต่ละฉบับ: ข้อมูลบทความครบ กับผู้เขียนจากเจ้าของวารสาร', en: 'Each journal: complete records and authors from the owner' },
  'js.table': { th: 'ตัวเลขของวารสารในแผนภูมิ', en: 'The journals in the chart' },
  'js.x': { th: 'ข้อมูลบทความครบ (เต็ม 100) →', en: 'Complete records (out of 100) →' },
  'js.y': { th: '↑ บทความที่มีผู้เขียนจากเจ้าของวารสาร', en: '↑ Articles with an author from the owner' },
  'js.zone': { th: 'เกิน {p}', en: 'Above {p}' },
  'js.owner': { th: 'วารสาร (ทะเบียนระบุเจ้าของ)', en: 'Journal (owner from the registry)' },
  'js.inferred': { th: 'วารสารที่ระบบเดาเจ้าของจากบทความ', en: 'Journal whose owner was guessed from its articles' },
  'js.label': { th: 'แผนภูมิจุดของวารสาร {n} ฉบับ ดูตัวเลขในมุมมองตาราง', en: 'Scatter of {n} journals; the figures are in the table view.' },
  'js.tip': { th: '{j}: ข้อมูลครบ {c} · ผู้เขียนจากเจ้าของ {p} · {n} บทความ', en: '{j}: records {c} · from the owner {p} · {n} articles' },
  'js.how': {
    th: 'หนึ่งจุดคือหนึ่งวารสาร ยิ่งไปทางขวา ข้อมูลบทความยิ่งครบ (เช่น มี DOI บทคัดย่อภาษาอังกฤษ) ยิ่งสูง บทความยิ่งมีผู้เขียนจากเจ้าของวารสารมาก แถบสีอ่อนด้านบนคือส่วนที่เกิน {p} ชื่อบนภาพคือวารสารที่เกินเกณฑ์และวารสารที่มีบทความมากที่สุด ทุกฉบับอยู่ในมุมมองตาราง',
    en: 'One dot per journal. The further right, the more complete its article records (a DOI, an English abstract …); the higher, the more of its articles have an author from the owner. The tinted band at the top is above {p}. Names go to journals above the bar and the largest ones; every journal is in the table view.',
  },
  'js.howNoBar': {
    th: 'หนึ่งจุดคือหนึ่งวารสาร ยิ่งไปทางขวา ข้อมูลบทความยิ่งครบ ยิ่งสูง บทความยิ่งมีผู้เขียนจากเจ้าของวารสารมาก ชื่อบนภาพคือวารสารที่มีบทความมากที่สุด ทุกฉบับอยู่ในมุมมองตาราง',
    en: 'One dot per journal. The further right, the more complete its article records; the higher, the more of its articles have an author from the owner. Names go to the largest journals; every journal is in the table view.',
  },
  'js.left': { th: 'อีก {n} วารสารไม่อยู่ในแผนภูมิ เพราะบทความน้อยเกินไปหรือยังไม่รู้เจ้าของ ดูได้ในตารางวารสารทั้งหมด', en: '{n} more journals are not in the chart: too few articles or no known owner. They are in the table of all journals.' },

  'si.cards': { th: 'หัวข้อที่น่าเปิดฉบับพิเศษ', en: 'Topics worth a special issue' },
  'si.asTable': { th: 'ดูเป็นตาราง', en: 'See as a table' },

  'pm.fig': { th: 'เรื่องที่วารสารตีพิมพ์: ปี {b} เทียบกับปี {r}', en: 'What the journal publishes: {b} vs {r}' },
  'pm.table': { th: 'หัวข้อที่สัดส่วนเปลี่ยนมากที่สุด', en: 'Topics whose share moved most' },
  'pm.lead': { th: 'เช่น “{t}” จาก {a} เป็น {b} ของบทความในวารสาร', en: 'For example, “{t}” went from {a} to {b} of the journal’s articles.' },
  'pm.how': {
    th: 'แถบบนคือบทความของวารสารปี {b} แถบล่างคือปี {r} แต่ละแถบเต็ม 100% แบ่งตามหัวข้อที่สัดส่วนเปลี่ยนมากที่สุด ที่เหลือรวมเป็น “เรื่องอื่น” หัวข้อเดียวกันอยู่ตำแหน่งเดียวกันและสีเดียวกันทั้งสองแถบ ส่วนที่ยาวขึ้นหรือสั้นลงคือการเปลี่ยนแนวของวารสาร',
    en: 'The top bar is the journal’s articles in {b}, the bottom bar {r}. Each bar is 100%, split by the topics whose share moved most; the rest is “Other”. A topic keeps its place and shade in both bars, so a part that grows or shrinks is the journal changing course.',
  },
  'pm.other': { th: 'เรื่องอื่น', en: 'Other' },
  'ty.fig': { th: '{n} เรื่องใหญ่ของวารสาร ปีต่อปี ({a}–{b})', en: 'The journal’s {n} largest topics, year by year ({a}–{b})' },
  'ty.table': { th: 'สัดส่วนบทความของเรื่องใหญ่ รายปี', en: 'Share of articles in the largest topics, by year' },
  'ty.lead': { th: 'เช่น “{t}” จาก {a} ในปี {y1} เป็น {b} ในปี {y2} ของบทความในวารสาร', en: 'For example, “{t}” went from {a} in {y1} to {b} in {y2} of the journal’s articles.' },
  'ty.how': {
    th: 'แต่ละช่องคือหนึ่งเรื่อง เส้นคือสัดส่วนบทความของวารสารปีนั้นที่อยู่ในเรื่องนี้ เส้นสีเทาคือเรื่องใหญ่อื่นของวารสาร ส่วนที่เหลือรวมเป็น “เรื่องอื่น” ในตาราง',
    en: 'Each panel is one topic; the line is the share of that year’s articles in the topic, the grey lines are the journal’s other large topics, and the rest is pooled as “Other” in the table.',
  },
  'ty.thin': { th: 'ปีที่มีบทความน้อยกว่า {m} เรื่องเว้นว่าง (ไม่ใช่ศูนย์): {years}', en: 'Years with fewer than {m} articles are left blank (not zero): {years}' },
  'ty.col.articles': { th: 'บทความ', en: 'Articles' },
  'ty.col.other': { th: 'เรื่องอื่น', en: 'Other' },
  'pm.label': { th: 'สัดส่วนหัวข้อ ปี {b}: {x}; ปี {r}: {y}', en: 'Topic shares, {b}: {x}; {r}: {y}' },
  'pm.col.before': { th: 'ปี {b}', en: '{b}' },
  'pm.col.after': { th: 'ปี {r}', en: '{r}' },
  'pm.col.change': { th: 'เปลี่ยน', en: 'Change' },
  'pm.pts': { th: '{d} จุด', en: '{d} pts' },
  'pm.ptsUnit': { th: 'จุด', en: 'points' },
  'jr.trend': { th: 'บทความรายปี {a}–{b}: {values}', en: 'Articles a year, {a}–{b}: {values}' },

  'ck.fig': { th: 'รายการข้อมูลที่บทความมี (7 รายการตามเกณฑ์ TCI)', en: 'What the article records include (7 items from the TCI assessment)' },
  'ck.lead': { th: 'ครบแล้ว {k} จาก {n} รายการ ที่ยังขาดมากที่สุดคือ{item} (มีใน {p} ของบทความ)', en: '{k} of {n} items are complete; the one most often missing is {item} (in {p} of articles).' },
  'ck.leadAll': { th: 'ครบแล้วทั้ง {n} รายการ', en: 'All {n} items are complete.' },
  'ck.how': {
    th: 'แต่ละแถวคือข้อมูลหนึ่งรายการ แถบและตัวเลขคือสัดส่วนบทความที่มีรายการนั้น ช่องติ๊กเต็ม = มีในอย่างน้อย {full} ของบทความ ช่องครึ่ง = มีบางส่วน ช่องกากบาท = แทบไม่มี (ไม่เกิน {none}) จำนวนบทความที่ตรวจอยู่ในมุมมองตาราง',
    en: 'One row per item. The bar and number are the share of articles that have it. A full tick = at least {full} of articles; half = some; a cross = almost none (at most {none}). The table view has the number of articles checked.',
  },
  'ck.full': { th: 'ครบ', en: 'Complete' },
  'ck.partial': { th: 'บางส่วน', en: 'Partial' },
  'ck.none': { th: 'แทบไม่มี', en: 'Almost none' },
  'ck.unknown': { th: 'ไม่ทราบ', en: 'Unknown' },
  'ck.label': { th: 'รายการข้อมูลบทความ {n} รายการ', en: '{n} record items' },

  'mb.fig': { th: 'วิธีวิจัยที่บทความใช้มากที่สุด ปี {a}–{b}', en: 'The methods articles use most, {a}–{b}' },
  'mb.how': {
    th: 'ความยาวแถบเทียบกับวิธีที่ใช้มากที่สุด ตัวเลขคือสัดส่วนของบทความที่ระบุวิธีได้ บทความหนึ่งใช้ได้หลายวิธี สัดส่วนจึงรวมกันเกิน 100% ได้',
    en: 'Bar length is relative to the most used method; the number is the share of the articles that name a method. An article can use several, so the shares can add up to more than 100%.',
  },
  'mb.label': { th: 'วิธีวิจัยเรียงตามจำนวนบทความ', en: 'Methods ranked by articles' },
  'mb.more': { th: 'ดูอีก {n} วิธี', en: 'See {n} more methods' },
  'mb.val': { th: '{p} · {n} เรื่อง', en: '{p} · {n}' },

  'ms.steps': { th: 'ใช้งานใน 3 ขั้น', en: 'Three steps' },
  'ms.1t': { th: 'วางบทคัดย่อ', en: 'Paste an abstract' },
  'ms.1b': { th: 'ไทยหรืออังกฤษก็ได้ ยิ่งยาวยิ่งแม่น และข้อความจะไม่ออกไปนอกเบราว์เซอร์นี้', en: 'Thai or English; the longer, the better. The text never leaves this browser.' },
  'ms.2t': { th: 'ดูหัวข้อที่ใกล้ที่สุด', en: 'See the closest topics' },
  'ms.2b': { th: 'พร้อมสถานะของหัวข้อและงานที่มีอยู่แล้ว', en: 'With each topic’s status and existing work' },
  'ms.3t': { th: 'ดูวารสารที่ตีพิมพ์เรื่องนี้', en: 'See the journals that publish it' },
  'ms.3b': { th: 'แล้วตรวจดูขอบเขตของวารสารก่อนส่งบทความ', en: 'Then check the journal’s scope before you submit' },
  'ms.try': { th: 'ลองด้วยตัวอย่าง', en: 'Try an example' },
  'ms.tryHint': { th: 'เติมบทคัดย่อสมมติเรื่องการดูแลผู้สูงอายุในชุมชน แล้วหาหัวข้อให้ทันที', en: 'Fills in a made-up abstract on community elderly care and finds its topics.' },
  'ms.sample': {
    th: 'งานวิจัยนี้ศึกษารูปแบบการดูแลผู้สูงอายุในชุมชนของจังหวัดในภาคตะวันออกเฉียงเหนือ โดยสำรวจผู้ดูแลในครอบครัว อาสาสมัครสาธารณสุขประจำหมู่บ้าน และเจ้าหน้าที่องค์กรปกครองส่วนท้องถิ่น ผลการศึกษาพบว่าการเยี่ยมบ้านอย่างสม่ำเสมอ การมีส่วนร่วมของชุมชน และการประสานงานกับโรงพยาบาลส่งเสริมสุขภาพตำบล ช่วยให้ผู้สูงอายุที่มีภาวะพึ่งพิงได้รับการดูแลต่อเนื่อง และลดภาระของครอบครัว ข้อเสนอแนะคือควรพัฒนาศักยภาพผู้ดูแลและระบบการดูแลระยะยาวในชุมชน',
    en: 'This study examines community-based elderly care in provinces of northeastern Thailand. It surveys family caregivers, village health volunteers and local government officers. Regular home visits, community participation and coordination with sub-district health promoting hospitals help dependent older people receive continuous care and reduce the burden on families. The study recommends strengthening caregiver skills and long-term care systems in the community.',
  },
  'ms.cards': { th: 'หัวข้อที่ใกล้ที่สุด เรียงจากใกล้ที่สุด', en: 'Closest topics, closest first' },
  'ms.sim': { th: 'คำตรงกัน {p}', en: '{p} matching words' },
  'ms.rank': { th: 'อันดับ {n}', en: 'No. {n}' },
  'ms.size': { th: '{n} บทความปี {r}', en: '{n} articles in {r}' },

  'sm.label': { th: 'แผนภูมิเล็กของ {t}: {values}', en: 'Small chart of {t}: {values}' },
  'sm.same': { th: 'ทุกช่องใช้แกนตั้งเดียวกัน จึงเทียบความสูงข้ามช่องได้', en: 'Every panel uses the same vertical scale, so heights compare across panels.' },
})

import { defineStrings } from './define'

/** /galaxy (R8 article galaxy). Imported only by the lazy GalaxyPage (entry budget). */
export const galaxy = defineStrings({
  title: { th: 'กาแล็กซีบทความ', en: 'Article galaxy' },
  lede: {
    th: 'บทความ {n} เรื่องในคลัง หนึ่งจุดคือหนึ่งบทความ จุดที่อยู่ใกล้กันมีเนื้อหาใกล้กัน สีบอกสาขาวิชา',
    en: '{n} articles in the collection, one dot each. Dots close together are about similar things; the colour shows the field.',
  },

  'f.h': { th: 'เลือกบทความที่จะเน้น', en: 'Highlight articles' },
  'f.from': { th: 'ตั้งแต่ปี', en: 'From' },
  'f.to': { th: 'ถึงปี', en: 'To' },
  'f.group': { th: 'สาขาวิชา', en: 'Field' },
  'f.any': { th: 'ทั้งหมด', en: 'All' },
  'f.reset': { th: 'ล้างตัวเลือก', en: 'Clear' },
  shown: { th: 'เน้น {shown} จาก {n} บทความ', en: '{shown} of {n} articles highlighted' },
  shownAll: { th: 'แสดงทั้งหมด {n} บทความ', en: 'All {n} articles shown' },
  noCoord: { th: 'อีก {n} บทความยังไม่มีตำแหน่งบนแผนที่ จึงไม่ปรากฏในภาพ', en: '{n} more articles have no place on the map yet, so they are not drawn.' },

  'fig.title': { th: 'บทความทุกเรื่องบนแผนที่หัวข้อวิจัย', en: 'Every article on the map of research topics' },
  'fig.label': { th: 'กาแล็กซีบทความ ลากเพื่อเลื่อน ใช้ปุ่มบวกลบเพื่อซูม กด Enter เพื่อดูบทความตรงกลางภาพ', en: 'Article galaxy. Drag to move, use plus and minus to zoom, press Enter to see the article in the middle.' },
  hint: {
    th: 'ลากเพื่อเลื่อน · ปุ่ม + − หรือกด Ctrl ค้างแล้วหมุนล้อเมาส์เพื่อซูม · ชี้หรือแตะจุดเพื่อดูบทความ · แป้นพิมพ์: ลูกศรเลื่อน, + − ซูม, Enter เลือกจุดกลางภาพ, 0 กลับมุมมองเดิม',
    en: 'Drag to move · + − or Ctrl + wheel to zoom · point at or tap a dot to see the article · Keyboard: arrows move, + − zoom, Enter picks the dot in the middle, 0 resets',
  },
  'zoom.group': { th: 'ซูม', en: 'Zoom' },
  'zoom.in': { th: 'ขยาย', en: 'Zoom in' },
  'zoom.out': { th: 'ย่อ', en: 'Zoom out' },
  'zoom.reset': { th: 'กลับมุมมองเดิม', en: 'Reset view' },
  failed: { th: 'วาดภาพไม่สำเร็จในเบราว์เซอร์นี้ ดูรายการหัวข้อในแท็บตารางแทน', en: 'The picture could not be drawn in this browser. See the topics in the Table tab instead.' },
  lost: { th: 'ภาพหยุดชั่วคราว เบราว์เซอร์กำลังกู้คืน…', en: 'The picture paused; the browser is restoring it…' },
  legend: { th: 'สีของสาขาวิชา', en: 'Field colours' },
  'legend.none': { th: 'ไม่ระบุสาขา', en: 'No field' },
  'legend.note': { th: 'สีบางสาขาใกล้กัน ชื่อสาขาบนภาพและการ์ดบทความจึงบอกสาขาเสมอ', en: 'Some field colours are close; the names on the picture and the article card always say the field.' },

  'card.h': { th: 'บทความที่เลือก', en: 'Selected article' },
  'card.empty': { th: 'ชี้หรือแตะจุดบนภาพเพื่อดูชื่อบทความ วารสาร และลิงก์ไปอ่าน', en: 'Point at or tap a dot to see the article’s title, journal and a link to read it.' },
  'card.loading': { th: 'กำลังโหลดบทความ…', en: 'Loading the article…' },
  'card.error': { th: 'โหลดรายละเอียดบทความไม่ได้ ลองใหม่อีกครั้ง', en: 'The article details could not be loaded. Try again.' },
  'card.noDocs': { th: 'รอบข้อมูลนี้ไม่มีรายละเอียดบทความ (ส่วนค้นหาบทความ) จึงแสดงได้เพียงปีและหัวข้อ', en: 'This release has no article details (the article search files), so only the year and topic are shown.' },
  'card.journal': { th: 'วารสาร', en: 'Journal' },
  'card.year': { th: 'ปี', en: 'Year' },
  'card.topic': { th: 'หัวข้อวิจัย', en: 'Research topic' },
  'card.field': { th: 'สาขาวิชา', en: 'Field' },
  'card.noTopic': { th: 'ยังไม่จัดหัวข้อ', en: 'No topic' },
  'card.read': { th: 'อ่านบทความใน ThaiJO', en: 'Read on ThaiJO' },
  'card.doi': { th: 'DOI', en: 'DOI' },
  'card.clear': { th: 'ล้างการเลือก', en: 'Clear selection' },
  'card.none': { th: 'ไม่มีบทความตรงกลางภาพ ลองเลื่อนหรือซูมเข้าใกล้จุดก่อน แล้วกด Enter อีกครั้ง', en: 'No article in the middle of the picture. Move or zoom closer to a dot, then press Enter again.' },

  'tbl.title': { th: 'หัวข้อวิจัยและจำนวนบทความ', en: 'Research topics and their articles' },
  'tbl.topic': { th: 'หัวข้อวิจัย', en: 'Research topic' },
  'tbl.field': { th: 'สาขาวิชา', en: 'Field' },
  'tbl.articles': { th: 'บทความ', en: 'Articles' },
  'tbl.empty': { th: 'ไม่มีหัวข้อในสาขานี้', en: 'No topic in this field' },

  'nogl.h': { th: 'เบราว์เซอร์นี้วาดภาพกาแล็กซีไม่ได้', en: 'This browser cannot draw the galaxy' },
  'nogl.body': {
    th: 'ภาพนี้วาดบทความจำนวนมากพร้อมกันด้วย WebGL 2 ซึ่งเบราว์เซอร์หรือเครื่องนี้ไม่รองรับหรือปิดไว้ ลองเปิดด้วย Chrome, Edge, Firefox หรือ Safari รุ่นล่าสุด หรือดูหัวข้อวิจัยทั้งหมดบนแผนที่แทน',
    en: 'The picture draws many articles at once with WebGL 2, which this browser or device does not support or has turned off. Try a recent Chrome, Edge, Firefox or Safari, or see every research topic on the map instead.',
  },
  'nogl.link': { th: 'ไปที่แผนที่หัวข้อวิจัย', en: 'Go to the map of research topics' },
})

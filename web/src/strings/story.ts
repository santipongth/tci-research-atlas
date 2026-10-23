import { defineStrings } from './define'

/** "เรื่องเล่าข้อมูลรายไตรมาส" (/story): five facts of the release, each with a share image. Lazy page only. */
export const story = defineStrings({
  'st.title': { th: '5 เรื่องน่ารู้จากงานวิจัยไทย รอบ {release}', en: '5 things to know about Thai research, release {release}' },
  'st.lede': {
    th: 'สรุปสั้น ๆ จากข้อมูลรอบนี้ แต่ละเรื่องมีภาพสี่เหลี่ยมให้ดาวน์โหลดไปแชร์ต่อได้ทันที ตัวเลขทุกตัวมาจากข้อมูลบนเว็บนี้',
    en: 'A short summary of this release. Each fact has a square image you can download and share; every number comes from this site.',
  },
  'st.download': { th: 'ดาวน์โหลดภาพสำหรับแชร์', en: 'Download the share image' },
  'st.making': { th: 'กำลังสร้างภาพ…', en: 'Making the image…' },
  'st.more': { th: 'ดูรายละเอียด', en: 'See the details' },
  'st.footer': { th: 'ที่มา: TCI Research Atlas · รอบ {release}', en: 'Source: TCI Research Atlas · release {release}' },
  'st.how': {
    th: 'เรื่องทั้ง 5 เลือกจากตัวเลขของรอบนี้แบบเดียวกันทุกรอบ: เรื่องที่สัดส่วนบทความโตเร็วที่สุด จำนวนเรื่องกำลังเกิดใหม่ เรื่องใหญ่ที่ยังโต เรื่องที่ลดลงเร็วที่สุด และจังหวัดที่มีงานวิจัยมากที่สุด ภาพสร้างในเบราว์เซอร์ของคุณ ไม่ได้ส่งข้อมูลไปที่ไหน',
    en: 'The five are picked the same way every release: the fastest-growing topic, the number of emerging topics, the large topic still growing, the fastest-shrinking topic and the province with the most research. Images are drawn in your browser; nothing is sent anywhere.',
  },
  'st.rise.line': { th: '“{topic}” โตเร็วที่สุด', en: '“{topic}” is growing fastest' },
  'st.rise.subTimes': { th: 'ทุกปี สัดส่วนบทความเรื่องนี้เพิ่มเป็นราว {m} เท่าของปีก่อน', en: 'Every year its share of articles grows to about {m} times the year before' },
  'st.rise.subPct': { th: 'สัดส่วนบทความเรื่องนี้เพิ่มขึ้นราว {g} ต่อปี', en: 'Its share of articles grows about {g} a year' },
  'st.em.big': { th: '{n} เรื่อง', en: '{n} topics' },
  'st.em.line': { th: 'เรื่องที่กำลังเกิดใหม่ในรอบนี้', en: 'are emerging this release' },
  'st.em.sub': { th: 'เช่น {list} เรื่องเล็กที่โตเร็วจากหลายสถาบัน', en: 'For example {list}: small topics growing fast across many institutions' },
  'st.big.big': { th: '{k} ใน 100', en: '{k} in 100' },
  'st.big.line': { th: '“{topic}” ใหญ่และยังโต', en: '“{topic}” is large and still growing' },
  'st.big.sub': { th: 'ทุก 100 บทความ มีเรื่องนี้ราว {k} เรื่อง และสัดส่วนยังเพิ่มราว {g} ต่อปี', en: 'About {k} in every 100 articles, and its share still grows about {g} a year' },
  'st.down.line': { th: '“{topic}” ลดลงเร็วที่สุด', en: '“{topic}” is shrinking fastest' },
  'st.down.sub': { th: 'สัดส่วนบทความเรื่องนี้หายไปราว {g} ต่อปี', en: 'Its share of articles falls about {g} a year' },
  'st.prov.line': { th: 'งานวิจัยอยู่ที่{name}มากที่สุด', en: 'Most research is in {name}' },
  'st.prov.sub': { th: '{p} ของบทความที่ระบุจังหวัดได้ มีผู้เขียนอยู่ใน{name} รองลงมาคือ{next}', en: '{p} of the articles we can place have an author in {name}; next is {next}' },
  'st.kpi.line': { th: 'บทความในวารสารไทยรอบนี้', en: 'articles in Thai journals this release' },
  'st.kpi.sub': { th: 'จัดเป็น {k} หัวข้อวิจัย ข้อมูลถึงปี {y}', en: 'Grouped into {k} research topics, data up to {y}' },
})

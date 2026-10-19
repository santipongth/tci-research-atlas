import type { Entry } from '../strings/define'

/** /about: the method in plain language. {R} {B} {W} are filled with the release's windows. */
export const METHOD: readonly { id: string; h: Entry; body: readonly Entry[] }[] = [
  {
    id: 'data',
    h: { th: 'ข้อมูลมาจากไหน', en: 'Where the data comes from' },
    body: [
      {
        th: 'ข้อมูลคือบทความในวารสารไทยที่อยู่ในฐานข้อมูล TCI และเผยแพร่ผ่าน ThaiJO ระบบอ่านชื่อเรื่อง บทคัดย่อ คำสำคัญ ปีที่พิมพ์ และสังกัดของผู้แต่ง แปลงปี พ.ศ. เป็น ค.ศ. ซ่อมตัวอักษรไทยที่เพี้ยนจากการแปลงไฟล์ PDF และตัดบทความซ้ำออก',
        en: 'The data is the articles in Thai journals indexed by TCI and published on ThaiJO. The system reads titles, abstracts, keywords, publication years and author affiliations, converts Buddhist-era years to the Gregorian calendar, repairs Thai characters damaged by PDF conversion and removes duplicates.',
      },
    ],
  },
  {
    id: 'topics',
    h: { th: 'หัวข้อวิจัยได้มาอย่างไร', en: 'How the topics are found' },
    body: [
      {
        th: 'แต่ละบทความถูกแปลงเป็นเวกเตอร์ความหมายด้วยโมเดลภาษาที่อ่านได้ทั้งไทยและอังกฤษ แล้วจัดบทความที่ความหมายใกล้กันเป็นหัวข้อ รวมกลุ่มที่ซ้ำกัน และตั้งชื่อหัวข้อจากคำสำคัญของผู้แต่งหรือด้วย AI ที่บรรณาธิการสุ่มตรวจ หัวข้อมีรหัสคงที่ข้ามรอบข้อมูลเพื่อให้ติดตามได้',
        en: 'Each article is turned into a meaning vector by a language model that reads Thai and English, articles close in meaning are grouped into topics, duplicate groups are merged, and topics are named from author keywords or by AI that editors spot-check. Topic ids stay the same across releases so topics can be followed over time.',
      },
      {
        th: 'สาขาหลักอ้างอิงสาขาของ OpenAlex เพื่อให้เทียบกับต่างประเทศได้ ตำแหน่งบนแผนที่ตรึงไว้ข้ามรอบ ระยะห่างบอกความคล้ายของเนื้อหา ไม่ใช่ภูมิศาสตร์',
        en: 'The main fields follow OpenAlex fields so the atlas can be compared internationally. Map positions are kept stable across releases; distance shows similarity of content, not geography.',
      },
    ],
  },
  {
    id: 'status',
    h: { th: 'สถานะของหัวข้อคำนวณอย่างไร', en: 'How a topic’s status is decided' },
    body: [
      {
        th: 'สถานะดูจากอัตราโตของ “สัดส่วน” บทความ ไม่ใช่จำนวนบทความ เพราะจำนวนบทความทั้งหมดเพิ่มขึ้นทุกปี อัตราโตประมาณด้วยแบบจำลอง Poisson จากทุกปีในช่วง {W} พร้อมช่วงเชื่อมั่น แล้วเทียบช่วงล่าสุด {R} กับช่วงฐาน {B} และตรวจว่าการเติบโตมาจากหลายวารสารและหลายสถาบัน',
        en: 'Status looks at growth in the share of articles, not the number of articles, because the total grows every year. Growth is estimated with a Poisson model from every year in {W}, with a confidence interval; the recent window {R} is compared with the baseline {B}, and the growth must come from several journals and institutions.',
      },
    ],
  },
  {
    id: 'forecast',
    h: { th: 'การคาดการณ์', en: 'Forecasts' },
    body: [
      {
        th: 'คาดการณ์ 2 ปีจากสัดส่วนของหัวข้อคูณจำนวนบทความรวม เลือกโมเดลด้วยการทดสอบย้อนหลังหลายจุด และแสดงตัวเลขเฉพาะหัวข้อที่โมเดลแม่นกว่าการใช้ค่าของปีล่าสุด หัวข้ออื่นแสดงว่า “แนวโน้มไม่แน่นอน” ช่วงคาดการณ์ 80% และ 95% ปรับให้ตรงกับความคลาดเคลื่อนจริงในอดีต',
        en: 'Two-year forecasts multiply the topic’s share by the total number of articles. Models are chosen by back-testing from several starting points, and numbers are shown only where the model beats repeating last year’s value; other topics say “trend uncertain”. The 80% and 95% intervals are calibrated on past errors.',
      },
    ],
  },
  {
    id: 'limits',
    h: { th: 'ข้อจำกัดที่ควรรู้', en: 'Limits to keep in mind' },
    body: [
      {
        th: 'วารสารที่เพิ่งเข้าระบบหรืออัปโหลดฉบับย้อนหลังทำให้หัวข้อดูเหมือนโตเร็ว ระบบจึงแยกสถานะ “จับตา” ออกมา ปีที่ข้อมูลยังเข้าไม่ครบจะไม่นำมาคำนวณ ข้อมูลสังกัดผู้แต่งบางส่วนไม่ครบ จึงมีหัวข้อที่ตรวจความกว้างของสถาบันไม่ได้ และตัวเลขทั้งหมดเป็นการวิเคราะห์เชิงสถิติ ไม่ใช่การประเมินคุณภาพงานวิจัย',
        en: 'A journal that was just indexed or uploaded back issues can make a topic look fast-growing, so such topics get the separate “watch” status. Years whose data is still arriving are not counted. Some author affiliations are incomplete, so some topics cannot have their institution breadth checked. All figures are statistical analysis, not an assessment of research quality.',
      },
    ],
  },
]

import type { Entry } from '../strings/define'

/** /about: the method in plain language (layer 1) and its technical detail behind "วิธีอ่าน" (layer 2).
 *  {R} {B} {W} are filled with the release's windows. */
export const METHOD: readonly { id: string; h: Entry; body: readonly Entry[]; how?: Entry }[] = [
  {
    id: 'data',
    h: { th: 'ข้อมูลมาจากไหน', en: 'Where the data comes from' },
    body: [
      {
        th: 'ข้อมูลคือบทความในวารสารไทยที่อยู่ในฐาน TCI และเผยแพร่ใน ThaiJO ระบบอ่านชื่อเรื่อง บทคัดย่อ คำสำคัญ ปีที่พิมพ์ และสังกัดของผู้เขียน',
        en: 'The data is the articles in Thai journals indexed by TCI and published on ThaiJO. The system reads their titles, abstracts, keywords, years and author affiliations.',
      },
    ],
    how: {
      th: 'ปี พ.ศ. แปลงเป็น ค.ศ. ตัวอักษรไทยที่เพี้ยนจากการแปลงไฟล์ PDF ถูกซ่อม และบทความซ้ำถูกตัดออก',
      en: 'Buddhist-era years are converted to the Gregorian calendar, Thai characters damaged by PDF conversion are repaired and duplicate articles are removed.',
    },
  },
  {
    id: 'topics',
    h: { th: 'หัวข้อวิจัยได้มาอย่างไร', en: 'How the topics are found' },
    body: [
      {
        th: 'เช่น บทความเรื่องข้าวหอมมะลิกับเรื่องโรคใบไหม้ของข้าว มีเนื้อหาใกล้กัน จึงอยู่หัวข้อเดียวกัน ระบบจัดบทความที่เนื้อหาใกล้กันเป็นหัวข้อ แล้วตั้งชื่อหัวข้อ',
        en: 'For example, an article on jasmine rice and one on rice blast disease are close in content, so they share a topic. The system groups articles with similar content into topics and then names them.',
      },
      {
        th: 'หัวข้อมีรหัสเดิมทุกรอบ จึงติดตามข้ามรอบได้ บนแผนที่ หัวข้อที่อยู่ใกล้กันมีเนื้อหาคล้ายกัน ไม่ใช่อยู่ใกล้กันทางภูมิศาสตร์',
        en: 'Each topic keeps its id in every release, so it can be followed over time. On the map, nearby topics have similar content; it is not geography.',
      },
    ],
    how: {
      th: 'ชื่อเรื่องและบทคัดย่อถูกแปลงเป็นชุดตัวเลขความหมาย (embedding) ด้วยโมเดลภาษาที่อ่านได้ทั้งไทยและอังกฤษ กลุ่มที่ซ้ำกันถูกรวม ชื่อหัวข้อมาจากคำสำคัญของผู้เขียนหรือจาก AI ที่บรรณาธิการสุ่มตรวจ สาขาหลักใช้สาขาของ OpenAlex เพื่อให้เทียบกับต่างประเทศได้ ตำแหน่งบนแผนที่ตรึงไว้ข้ามรอบ',
      en: 'Titles and abstracts are turned into lists of numbers that capture meaning (embeddings) by a language model that reads Thai and English. Duplicate groups are merged; topics are named from author keywords or by AI that editors spot-check. Main fields follow OpenAlex so the atlas can be compared internationally, and map positions are kept stable across releases.',
    },
  },
  {
    id: 'status',
    h: { th: 'สถานะของหัวข้อคำนวณอย่างไร', en: 'How a topic’s status is decided' },
    body: [
      {
        th: 'เช่น ถ้าปีก่อนหัวข้อหนึ่งมี 1 ใน 100 บทความ ปีนี้มี 2 ใน 100 สัดส่วนโตเท่าตัว ระบบดู “สัดส่วน” ไม่ใช่จำนวน เพราะบทความทั้งหมดเพิ่มขึ้นทุกปี',
        en: 'For example, if a topic had 1 in 100 articles last year and 2 in 100 this year, its share has doubled. The system looks at the share, not the count, because the total number of articles grows every year.',
      },
      {
        th: 'ระบบเทียบปี {R} กับปี {B} และดูว่าการเติบโตมาจากหลายวารสารและหลายสถาบันหรือไม่',
        en: 'It compares {R} with {B} and checks that the growth comes from several journals and institutions.',
      },
    ],
    how: {
      th: 'อัตราโตของสัดส่วนประมาณด้วยแบบจำลอง Poisson จากทุกปีในช่วง {W} พร้อมช่วงที่น่าจะเป็น (ช่วงเชื่อมั่น) กฎของแต่ละสถานะอยู่ในหัวข้อถัดไป',
      en: 'Share growth is estimated with a Poisson model from every year in {W}, with a likely range (a confidence interval). The rule for each status is in the next section.',
    },
  },
  {
    id: 'forecast',
    h: { th: 'การคาดการณ์', en: 'Forecasts' },
    body: [
      {
        th: 'ระบบคาดการณ์จำนวนบทความล่วงหน้า 2 ปี และแสดงตัวเลขเฉพาะหัวข้อที่คาดได้แม่นกว่าการเดาว่าจะเท่าปีล่าสุด หัวข้ออื่นแสดงว่า “แนวโน้มไม่แน่นอน”',
        en: 'The system forecasts article counts two years ahead and shows numbers only for topics where it beats guessing “same as last year”. Other topics say “trend uncertain”.',
      },
    ],
    how: {
      th: 'คาดการณ์จากสัดส่วนของหัวข้อคูณจำนวนบทความรวม เลือกโมเดลด้วยการทดสอบย้อนหลังหลายจุด ต้องชนะการใช้ค่าปีล่าสุดในการทดสอบที่เชื่อถือได้อย่างน้อย 3 จุด ช่วงที่น่าจะเป็น 80% และ 95% ปรับให้ตรงกับความคลาดเคลื่อนจริงในอดีต',
      en: 'Forecasts multiply the topic’s share by the total number of articles. Models are chosen by back-testing from several starting points and must beat repeating last year on at least 3 honest test points. The 80% and 95% ranges are calibrated on past errors.',
    },
  },
  {
    id: 'writing',
    h: { th: 'ข้อความสรุปเขียนอย่างไร', en: 'How the summaries are written' },
    body: [
      {
        th: 'ประโยคสรุปเขียนจากแม่แบบข้อความเป็นหลัก ถ้าใช้ข้อความที่ AI เขียน ตัวเลขทุกตัวต้องตรงกับผลของระบบก่อน',
        en: 'Summary sentences are written from templates by default. AI-written text is used only after every number in it matches the system’s results.',
      },
    ],
  },
  {
    id: 'limits',
    h: { th: 'ข้อจำกัดที่ควรรู้', en: 'Limits to keep in mind' },
    body: [
      {
        th: 'เช่น วารสารที่เพิ่งเข้าระบบ อาจทำให้หัวข้อดูเหมือนโตเร็ว ระบบจึงแยกสถานะ “จับตา” ออกมา',
        en: 'For example, a journal that has just been indexed can make a topic look fast-growing, so such topics get the separate “watch” status.',
      },
      {
        th: 'ปีที่ข้อมูลยังเข้าไม่ครบไม่นำมาคิด ข้อมูลสังกัดผู้เขียนบางส่วนไม่ครบ และตัวเลขทั้งหมดเป็นสถิติ ไม่ใช่การประเมินคุณภาพงานวิจัย',
        en: 'Years whose data is still arriving are not counted, some author affiliations are incomplete, and every figure is a statistic, not a judgement of research quality.',
      },
    ],
  },
]

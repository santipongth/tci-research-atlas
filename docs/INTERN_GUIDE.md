# คู่มือนักศึกษาฝึกงาน: เตรียมคลังบทความ → รันวิเคราะห์ → เปิดเว็บบนเซิร์ฟเวอร์ขององค์กร

คู่มือนี้พาทำทีละขั้น ตั้งแต่ได้รับข้อมูลบทความ จนเว็บ TCI Research Atlas เปิดให้ประชาชนใช้ได้บนเซิร์ฟเวอร์ขององค์กร
ทุกขั้นบอกว่า **ทำไม** ต้องทำ, **คำสั่ง** ทำอะไร, **ที่ควรเห็น** เมื่อสำเร็จ และ **ถ้าไม่เป็นอย่างนั้น** ต้องทำอย่างไร

เอกสารที่เกี่ยวข้อง:
- รายละเอียดรูปแบบคลังบทความ: [`docs/corpus/README.md`](corpus/README.md)
- ขั้นตอนรอบไตรมาสฉบับหลักสำหรับผู้ดูแล และรายละเอียดเชิงเทคนิคทั้งหมด: [`docs/OPERATIONS.md`](OPERATIONS.md) §1 (คู่มือนี้ทำตามขั้นเดียวกัน แต่อธิบายละเอียดกว่า)
- ถ้าองค์กรเลือกเผยแพร่ผ่านช่องทางอื่น (เช่น GitHub Pages) ผู้ดูแลเป็นคนทำเอง นักศึกษาไม่ต้องทำ

---

## คำศัพท์ที่จะเจอ

| คำ | ความหมาย |
|---|---|
| คลังบทความ (corpus) | ชุดไฟล์ข้อมูลบทความทั้งหมดของรอบนี้ อยู่ในโฟลเดอร์เดียว |
| รอบ (release) | ข้อมูล 1 ไตรมาส ตั้งชื่อแบบ `YYYYQn` เช่น `2026Q4` = ไตรมาส 4 ปี 2026 |
| terminal / PowerShell | หน้าต่างพิมพ์คำสั่ง บน Windows เปิดจากเมนู Start พิมพ์ "PowerShell" |
| config | ไฟล์ตั้งค่า (`config.yaml`) บอกโปรแกรมว่าข้อมูลอยู่ที่ไหน ใช้บริการอะไร |
| environment variable (env var) | ค่าที่เก็บไว้ในเครื่องสำหรับผู้ใช้คนนี้ ไม่อยู่ในไฟล์ใด ใช้เก็บรหัสลับ (API key) |
| API key | รหัสลับสำหรับใช้บริการที่เสียเงิน ใครได้ไปก็ใช้เงินขององค์กรได้ |
| embedding | การแปลงข้อความของบทความแต่ละเรื่องเป็นชุดตัวเลข เพื่อให้เครื่องจัดบทความที่เนื้อหาใกล้กันไว้ด้วยกัน ทำผ่านบริการที่คิดเงิน |
| LLM | โมเดลภาษา (แบบเดียวกับแชตบอต) ใช้ตั้งชื่อหัวข้อและเขียนคำอธิบายภาษาง่าย คิดเงินตามปริมาณข้อความ |
| dry-run | การ "ซ้อม" นับงานและประมาณค่าใช้จ่าย โดยยังไม่เรียกบริการและยังไม่เสียเงิน |
| cache | ที่เก็บผลที่เคยได้แล้ว รันซ้ำจึงไม่ต้องจ่ายซ้ำ |
| validate | การตรวจผลก่อนเผยแพร่ เช่น ไฟล์ครบไหม มีข้อมูลส่วนบุคคลหลุดไหม |
| publish | การวางข้อมูลรอบใหม่ลงในโฟลเดอร์เว็บ |
| static site (เว็บแบบไฟล์ล้วน) | เว็บที่มีแต่ไฟล์ HTML, JavaScript, CSS และ JSON ไม่มีฐานข้อมูล ไม่มีโปรแกรมทำงานบนเซิร์ฟเวอร์ เซิร์ฟเวอร์แค่ส่งไฟล์ให้ |
| HTTPS | การเชื่อมต่อเว็บแบบเข้ารหัส (ที่อยู่ขึ้นต้นด้วย `https://` มีรูปแม่กุญแจ) |
| MIME type | ป้ายบอกเบราว์เซอร์ว่าไฟล์เป็นชนิดอะไร เช่น `application/json` |

## ข้อควรจำ (อ่านก่อนเริ่ม)

- **ข้อมูลบทความมีชื่อผู้แต่ง ซึ่งเป็นข้อมูลส่วนบุคคล** เก็บในเครื่องหรือโฟลเดอร์ภายในองค์กรเท่านั้น ห้าม commit หรือ push ขึ้น GitHub ห้ามอัปโหลดขึ้นบริการออนไลน์ใด ๆ (โฟลเดอร์ `runs\` และ `deploy\` ใน repo ถูกตั้งให้ git ไม่เก็บอยู่แล้ว)
- **API key** ใส่ใน environment variable เท่านั้น ห้ามเขียนลงไฟล์ ห้ามส่งในแชต ห้าม commit
- **มี 3 จุดที่ต้องรอผู้ดูแลอนุมัติ** ห้ามข้าม:
  1. ค่าใช้จ่าย embedding (ขั้นที่ 14)
  2. ค่าใช้จ่าย LLM (ขั้นที่ 16)
  3. ผลทั้งหมดก่อนเปิดเว็บให้ประชาชน (ขั้นที่ 21)
- **เจอ error ที่ขึ้นต้นด้วย `privacy:` ให้หยุดทันที** ห้ามเผยแพร่ แจ้งผู้ดูแล (ขั้นที่ 18)
- ขั้นไหนติดปัญหา ให้หยุด จดข้อความ error ทั้งบรรทัด แล้วถามผู้ดูแล อย่าแก้โค้ดเอง
- คำสั่งในคู่มือนี้พิมพ์ใน PowerShell บน Windows ตัวอย่างใช้ repo ที่ `D:\tci-research-atlas` และข้อมูลที่ `D:\atlas-data` ถ้าเครื่องใช้ที่อื่น ให้เปลี่ยน path ตาม
- ถ้าคำสั่งใดสงสัยว่ามีตัวเลือกอะไร พิมพ์ `--help` ต่อท้าย เช่น `uv run atlas quarterly --help`

## ภาพรวมทั้งหมด

| ขั้นที่ | งาน | ครั้งแรกเท่านั้น? |
|---|---|---|
| 1–7 | **งาน 1:** เตรียมคลังบทความ | ทำทุกรอบ (รอบหลังเร็วขึ้นมาก) |
| 8 | รับสิ่งที่ต้องใช้จากผู้ดูแล | ครั้งแรก |
| 9–12 | ติดตั้งโปรแกรม ตั้ง key ตั้งค่า และลองเชื่อมต่อ | ครั้งแรก |
| 13 | ตรวจคลังบนเครื่องรันงาน | ทุกรอบ |
| 14–15 | embedding ครั้งใหญ่ (ขออนุมัติก่อน) | ครั้งแรก (รอบหลังทำในขั้นที่ 17 เอง) |
| 16 | ดูค่าใช้จ่าย LLM (ขออนุมัติก่อน) | ทุกรอบที่ใช้ LLM |
| 17 | รันทั้งรอบด้วยคำสั่งเดียว | ทุกรอบ |
| 18–20 | อ่านผลตรวจ ตรวจเว็บในเครื่อง ตรวจชื่อหัวข้อ | ทุกรอบ |
| 21 | ส่งผู้ดูแลอนุมัติก่อนเปิดสาธารณะ | ทุกรอบ |
| 22 | เตรียมเซิร์ฟเวอร์กับทีม IT | ครั้งแรก |
| 23–24 | อัปโหลดขึ้นเซิร์ฟเวอร์ และตรวจหลังขึ้นเว็บ | ทุกรอบ |
| 25 | สำรองข้อมูล | ทุกรอบ |
| 26–27 | รอบถัดไป และการย้อนกลับ | เมื่อถึงเวลา |

---

# งาน 1: เตรียมคลังบทความ (ขั้นที่ 1–7)

รายละเอียดทุกข้ออยู่ใน [`docs/corpus/README.md`](corpus/README.md) ส่วนนี้สรุปลำดับงาน

## ขั้นที่ 1: ติดตั้งโปรแกรมสำหรับตรวจคลัง (ครั้งแรก)

- **ทำไม:** ต้องมีโปรแกรม `atlas profile` ไว้ตรวจไฟล์ที่เตรียม
- **ทำ:** ตาม README หัวข้อ 12 ข้อ 1–4 (ติดตั้ง Git, uv, `git clone` แล้ว `uv sync`) ใช้เวลาประมาณ 15 นาที
- **ที่ควรเห็น:** คำสั่ง `uv run atlas profile ..\docs\corpus\example` จบด้วยบรรทัด
  ```
  [profile] OK — nothing to fix
  ```
- **ถ้าไม่เป็นอย่างนั้น:** ปิดแล้วเปิด PowerShell ใหม่ (หลังติดตั้ง uv หน้าต่างเดิมยังไม่รู้จักคำสั่ง `uv`) แล้วลองอีกครั้ง ถ้ายังไม่ได้ ส่งข้อความ error ให้ผู้ดูแล

## ขั้นที่ 2: อัปเดตโปรแกรมก่อนเริ่มงานทุกสัปดาห์

- **ทำไม:** คู่มือและโปรแกรมอาจถูกปรับ ถ้าใช้รุ่นเก่า ผลตรวจอาจไม่ตรงกับเครื่องรันงาน
- **คำสั่ง:**
  ```powershell
  cd D:\tci-research-atlas
  git pull
  cd pipeline
  uv sync
  ```
- **ที่ควรเห็น:** `git pull` ขึ้น `Already up to date.` หรือรายการไฟล์ที่อัปเดต ไม่มีคำว่า `error` หรือ `conflict`
- **ถ้าไม่เป็นอย่างนั้น:** ถ้าขึ้นว่ามีไฟล์ในเครื่องที่ถูกแก้ (`Your local changes … would be overwritten`) อย่าลบเอง ถามผู้ดูแล

## ขั้นที่ 3: ทำนำร่อง

- **ทำไม:** ลองกับข้อมูลชุดเล็กก่อน จะเจอปัญหาเร็วและแก้ง่าย
- **ทำ:** บทความประมาณ 1,000 เรื่องจาก 3 วารสาร พร้อมไฟล์ประกอบครบ ตาม README หัวข้อ 13 ข้อ 1
- **ที่ควรเห็น:** `atlas profile` จบด้วย `[profile] OK — nothing to fix` แล้วส่งให้ผู้ดูแลดู

## ขั้นที่ 4: ทำทั้งคลัง

- **ทำ:** ใช้หลักเดียวกับนำร่อง และเตรียมไฟล์ประกอบให้ครบ (README หัวข้อ 11):
  - `journals.csv` (บังคับ)
  - `institutions_aliases.csv` (แนะนำมาก) ต้องครอบคลุมแถวสังกัดอย่างน้อย 80% ตัวเลขนี้อยู่ในรายงาน `atlas profile`
  - `province_population.csv` เริ่มจาก [`docs/corpus/province_population.template.csv`](corpus/province_population.template.csv) ที่มีครบ 77 จังหวัดแล้ว เติมจำนวนประชากรและปี **ให้ครบทุกแถว** (แถวที่ว่างทำให้ตรวจไม่ผ่าน)
  - `ror.zip` (ถ้าทำได้)
  - `README.txt` บันทึกที่มาข้อมูลและการตัดสินใจ

## ขั้นที่ 5: ตรวจรอบสุดท้าย

- **ทำไม:** ให้แน่ใจว่าคลังพร้อม ก่อนส่งไปรันจริงที่เสียเงิน
- **คำสั่ง:**
  ```powershell
  cd D:\tci-research-atlas\pipeline
  uv run atlas profile D:\atlas-data\corpus\2026Q4 --md D:\atlas-data\profile.md --aliases-todo D:\atlas-data\aliases_todo.csv
  ```
  - `--md` เขียนรายงานลงไฟล์ (เปิดด้วย Notepad หรือ VS Code)
  - `--aliases-todo` เขียนรายชื่อสังกัดที่พบบ่อยแต่ยังไม่มีใน `institutions_aliases.csv` ไว้เติมต่อ
- **ที่ควรเห็น:** บรรทัดสุดท้ายบนหน้าจอเป็น `[profile] OK — nothing to fix`
- **ถ้าไม่เป็นอย่างนั้น:** หน้าจอจะขึ้น `[profile] fix before the hand-over:` ตามด้วยรายการที่ต้องแก้ และใน `profile.md` ส่วน "Companion files" มีหัวข้อ "ต้องแก้ก่อนส่ง" แก้ที่ไฟล์ต้นทาง แล้วตรวจใหม่จนผ่าน

## ขั้นที่ 6: วางคลังให้เป็นระเบียบ

- แยกโฟลเดอร์ตามรอบ และไม่แก้คลังของรอบเก่า:
  ```
  D:\atlas-data\corpus\2026Q4\articles\part-0001.jsonl.gz …
  D:\atlas-data\corpus\2026Q4\journals.csv  (+ ไฟล์ประกอบอื่น + README.txt)
  ```
- ไฟล์ประกอบต้องอยู่ข้างโฟลเดอร์ `articles\` (ไม่ใช่ข้างใน) โปรแกรมจึงหาเจอเอง

## ขั้นที่ 7: แจ้งผู้ดูแล

- แจ้งว่าเสร็จ แนบ `profile.md` ของรอบสุดท้าย ส่งผ่านช่องทางภายในองค์กรเท่านั้น แล้วไปงาน 2

---

# งาน 2: รันวิเคราะห์ แล้วเปิดเว็บบนเซิร์ฟเวอร์ขององค์กร (ขั้นที่ 8–27)

## ขั้นที่ 8: สิ่งที่ต้องได้รับจากผู้ดูแลก่อนเริ่ม

เช็กให้ครบ ขาดข้อไหน ขอก่อน อย่าเดา

- [ ] **API key สำหรับ embedding** (และ LLM ถ้าจะใช้) ส่งผ่านช่องทางที่ปลอดภัย พร้อมค่า `base_url` (ที่อยู่ของบริการ), ชื่อ `model` และ `dimensions`
- [ ] **วงเงินที่อนุมัติ** สำหรับ embedding ครั้งใหญ่ และสำหรับ LLM ต่อรอบ พร้อมราคาต่อ 1 ล้าน token ของบริการ LLM (ใช้คำนวณค่าใช้จ่าย)
- [ ] **ที่อยู่เว็บสาธารณะ** เช่น `https://atlas.tci-thailand.org/` (ใส่ใน `publish.site_url`)
- [ ] **ผู้ติดต่อฝ่าย IT** ที่ดูแลเซิร์ฟเวอร์เว็บ และวิธีอัปโหลดไฟล์ (เช่น SFTP, โฟลเดอร์แชร์)
- [ ] **ชื่อผู้ตรวจและอนุมัติ** ก่อนเปิดเว็บ (ขั้นที่ 21)
- [ ] **เครื่องรันงาน:** RAM ≥ 16 GB ที่ว่างบนดิสก์ ≥ 50 GB ต่ออินเทอร์เน็ตได้ตลอดหลายชั่วโมงตอน embedding ครั้งแรก

## ขั้นที่ 9: ติดตั้งเครื่องมือ (ครั้งแรก)

- **ทำไม:** งาน 2 ต้องใช้ Node.js เพิ่ม (โปรแกรมสร้างหน้าเว็บ) และส่วนเสริมของ pipeline สำหรับคลังขนาดใหญ่
- **ทำ:**
  1. ติดตั้ง Git และ uv ตามขั้นที่ 1 (ถ้ายังไม่มี)
  2. ติดตั้ง **Node.js 24** จาก <https://nodejs.org> (เลือกรุ่น 24) แล้วปิดและเปิด PowerShell ใหม่
  3. ติดตั้งส่วนของโปรแกรม:
     ```powershell
     cd D:\tci-research-atlas\pipeline
     uv sync --extra api --extra fast --extra leiden
     cd ..\web
     npm ci
     ```
     - `--extra api` = ส่วนที่ใช้เรียกบริการ embedding ผ่านอินเทอร์เน็ต
     - `--extra fast` = ตัวจัดกลุ่มที่เร็วพอสำหรับบทความหลายแสนเรื่อง (ค่าเริ่มของระบบใช้ตัวนี้)
     - `npm ci` = ติดตั้งส่วนประกอบของหน้าเว็บตามรายการที่ล็อกไว้
- **ที่ควรเห็น:** `node --version` ขึ้น `v24.…` · `npm ci` จบด้วย `added … packages` ไม่มีคำว่า `ERR!`
- **ถ้าไม่เป็นอย่างนั้น:** ถ้า `node` ไม่รู้จัก ให้ปิดแล้วเปิด PowerShell ใหม่ ถ้า `npm ci` ขึ้น `ERR!` ส่งข้อความให้ผู้ดูแล

## ขั้นที่ 10: ตั้ง API key (ครั้งแรก)

- **ทำไม:** โปรแกรมอ่าน key จาก environment variable เท่านั้น ไม่มี key อยู่ในไฟล์ใด จึงไม่หลุดไปกับไฟล์
- **คำสั่ง:**
  ```powershell
  setx ATLAS_EMBED_API_KEY "ใส่-key-ที่ได้รับ"
  setx ATLAS_LLM_API_KEY   "ใส่-key-ที่ได้รับ"
  ```
  - `setx` เก็บค่าไว้ถาวรสำหรับผู้ใช้คนนี้ ถ้าไม่ใช้ LLM ข้ามบรรทัดที่สอง ใช้ key เดียวกันได้ถ้าผู้ดูแลบอกว่าได้
- **แล้วปิดและเปิด PowerShell ใหม่** (หน้าต่างเดิมยังไม่เห็นค่า) จากนั้นตรวจโดยไม่แสดง key บนจอ:
  ```powershell
  if ($env:ATLAS_EMBED_API_KEY) { "ตั้งแล้ว" } else { "ยังไม่ได้ตั้ง" }
  ```
- **ที่ควรเห็น:** `SUCCESS: Specified value was saved.` หลัง `setx` และ `ตั้งแล้ว` หลังเปิดหน้าต่างใหม่
- **ถ้าไม่เป็นอย่างนั้น:** ขึ้น `ยังไม่ได้ตั้ง` แปลว่ายังใช้หน้าต่างเดิม หรือพิมพ์ชื่อผิด ลองใหม่

## ขั้นที่ 11: สร้างและแก้ไฟล์ตั้งค่า (ครั้งแรก)

- **ทำไม:** บอกโปรแกรมว่าจะเก็บงานไว้ที่ไหน ใช้บริการใด และเว็บจะอยู่ที่อยู่ไหน
- **คำสั่ง:**
  ```powershell
  cd D:\tci-research-atlas\pipeline
  copy config.example.yaml config.yaml
  ```
  ไฟล์ `config.yaml` ไม่เข้า git อยู่แล้ว
- **แก้ `config.yaml`** (ด้วย Notepad หรือ VS Code) เฉพาะค่าเหล่านี้ ค่าอื่นคงไว้ ระวังการย่อหน้า (ใช้ช่องว่าง ห้ามใช้ Tab):

  ```yaml
  pipeline:
    work_dir: D:/atlas-data/work          # งานระหว่างทาง ลบได้เสมอ
    output_dir: D:/atlas-data/output      # ผลลัพธ์ของทุกรอบ ห้ามลบ (ใช้ย้อนกลับ)
    state_dir: D:/atlas-data/state        # ห้ามลบ! เก็บ embedding และคำตอบ LLM ที่จ่ายเงินไปแล้ว
  input:
    path: D:/atlas-data/corpus/2026Q4     # หรือใส่ --corpus ตอนรัน
  embedding:
    provider: api                         # ห้ามใช้ lite กับข้อมูลจริง
    api:
      base_url: ...                       # ตามที่ผู้ดูแลให้
      model: ...
      dimensions: ...                     # ตามที่ผู้ดูแลให้ (bge-m3 ใช้ null)
  publish:
    site_url: https://atlas.tci-thailand.org/   # ที่อยู่เว็บสาธารณะจริงจากขั้นที่ 8 ลงท้ายด้วย /
  ```

  - `publish.site_url` สำคัญมาก: ระบบใช้ค่านี้ตอนสร้างหน้าเว็บ ใส่ในลิงก์หลักของเว็บ (canonical), `sitemap.xml`, `robots.txt`, รูปปกตอนแชร์ และฟีดข่าว ถ้าไม่ตั้งหรือผิด ลิงก์เหล่านี้จะชี้ผิดที่
  - คงบรรทัด `overrides_path: ./registry/label_overrides.csv` ใต้ `labeling:` ไว้ (ใช้ในขั้นที่ 20)

- **ถ้าผู้ดูแลอนุมัติให้ใช้ LLM** แก้ส่วนเหล่านี้ (หาหัวข้อเดิมในไฟล์แล้วแก้ค่า ไม่ต้องเพิ่มซ้ำ):
  ```yaml
  labeling:
    provider: llm
  narrative:
    provider: llm
  llm:
    budget_usd: ...                       # วงเงินต่อรอบที่ได้รับอนุมัติ (ตัวเลข USD)
    endpoints:
      default:
        base_url: ...
        price_per_mtok_in: ...            # ราคาของผู้ให้บริการ (จำเป็นเมื่อตั้ง budget_usd)
        price_per_mtok_out: ...
    tasks:
      label:     { model: ... }
      merge:     { model: ... }
      narrative: { model: ... }
      brief:     { model: ... }
  ```
  ถ้าไม่ใช้ LLM ไม่ต้องแก้ส่วนนี้ ระบบใช้ชื่อหัวข้อจากคำสำคัญ และประโยคแม่แบบจากตัวเลข (ส่วนบันทึกวิธีวิจัย `methods.provider` ให้เปิดเฉพาะเมื่อผู้ดูแลสั่ง)

- **ถ้าไม่เป็นอย่างนั้น:** ถ้าคำสั่งถัดไปขึ้น error เรื่อง config (เช่น `Extra inputs are not permitted` หรือ `validation error`) แปลว่าพิมพ์ชื่อค่าผิดหรือย่อหน้าผิด ตรวจบรรทัดที่ error บอก

## ขั้นที่ 12: ลองเชื่อมต่อบริการ (ครั้งแรก ไม่เสียเงินหรือเสียน้อยมาก)

- **ทำไม:** ให้รู้ทันทีว่า key, ที่อยู่ และชื่อโมเดลถูก ก่อนเริ่มงานยาวหลายชั่วโมง
- **คำสั่ง embedding** (ยิงคำขอ 1 ครั้ง):
  ```powershell
  cd D:\tci-research-atlas\pipeline
  uv run atlas embed -c config.yaml --check
  ```
- **ที่ควรเห็น:**
  ```
  [check] OK  model=BAAI/bge-m3  dim=1024  latency=420 ms
  [check] base_url=https://…  store_id=api|BAAI/bge-m3|None  $ATLAS_EMBED_API_KEY: set
  ```
- **คำสั่ง LLM** (ถ้าใช้ — คำขอเล็ก 1 ครั้งต่อโมเดล):
  ```powershell
  uv run atlas llm -c config.yaml --check
  ```
  ที่ควรเห็น: ทุกบรรทัดขึ้นต้นด้วย `OK` และมี `json=True thai=True`
- **ถ้าไม่เป็นอย่างนั้น:** ขึ้น `[check] FAILED` หรือบรรทัด `FAIL` แปลว่า key, `base_url` หรือ `model` ผิด ส่งข้อความทั้งบรรทัดให้ผู้ดูแล (ห้ามส่ง key)

## ขั้นที่ 13: ตรวจคลังอีกครั้งบนเครื่องรันงาน (ทุกรอบ ไม่เสียเงิน)

- **ทำไม:** เครื่องรันงานอาจได้ไฟล์ไม่ครบระหว่างคัดลอก และคำสั่งนี้เตรียมไฟล์ตั้งค่าของรอบนี้ให้ด้วย
- **คำสั่ง:**
  ```powershell
  cd D:\tci-research-atlas\pipeline
  uv run atlas quarterly --corpus D:\atlas-data\corpus\2026Q4 --release 2026Q4 --prepare
  ```
  - `--corpus` = โฟลเดอร์คลังของรอบนี้
  - `--release` = ชื่อรอบ รูป `YYYYQn` ห้ามเปลี่ยนกลางทาง และรอบใหม่ต้องไม่เก่ากว่ารอบก่อน
  - `--prepare` = ตรวจคลังแล้วหยุด ยังไม่รันงานที่เสียเงิน
  - ผลอยู่ที่ `D:\tci-research-atlas\runs\2026Q4\` เช่น `config.yaml` (ไฟล์ตั้งค่าของรอบนี้ = `config.yaml` ของคุณ + คลัง + ชื่อรอบ + ไฟล์ประกอบในโฟลเดอร์คลัง), `profile.md`, `corpus_manifest.json` (รายชื่อไฟล์คลังพร้อมรหัสตรวจสอบ)
- **ที่ควรเห็น:** บรรทัดท้าย ๆ คล้ายนี้
  ```
  [profile] OK — nothing to fix
  [quarterly] prepared: D:\tci-research-atlas\runs\2026Q4\config.yaml — first big embedding: uv run atlas embed -c … --check / --dry-run / --background
  ```
- **ถ้าไม่เป็นอย่างนั้น:** ขึ้น `[quarterly] STOPPED: the corpus check found problems …` ให้เปิด `runs\2026Q4\profile.md` ดูหัวข้อ "ต้องแก้ก่อนส่ง" และรายการท้ายหน้าจอ ส่งกลับทีมเตรียมคลัง (งาน 1) แก้แล้วรันคำสั่งเดิมซ้ำ
- **หมายเหตุ:** ถ้าแก้ `config.yaml` หลังจากนี้ ให้รันคำสั่งนี้ซ้ำ เพื่อสร้าง `runs\2026Q4\config.yaml` ใหม่

## ขั้นที่ 14: ดูค่าใช้จ่าย embedding แล้วขออนุมัติ (ครั้งแรก — จุดอนุมัติที่ 1)

- **ทำไม:** embedding ทั้งคลังเสียเงินจริงและใช้เวลาหลายชั่วโมง ผู้ดูแลต้องเห็นตัวเลขก่อน
- **คำสั่ง** (ไม่เรียกบริการ ไม่เสียเงิน — ถ้ายังไม่เคยอ่านคลัง จะอ่านคลังก่อน อาจใช้เวลาสักพัก):
  ```powershell
  uv run atlas embed -c ..\runs\2026Q4\config.yaml --dry-run
  ```
- **ที่ควรเห็น:**
  ```
  [dry-run] provider=api  store_id=api|BAAI/bge-m3|None  (no API call is made)
    documents      : 498,213
    unique texts   : 497,980
    cached         : 0
    to embed       : 497,980
    characters     : 612,345,678 (Thai 401,234,567)
    ~tokens        : 464,567,890 (rough: Thai ≈ 1 token/char, other ≈ 0.3)
    requests       : ~15,562 (batch_size 32, max_batch_chars 60000)
  ```
  (ตัวเลขนี้เป็นตัวอย่าง)
- **ส่งตัวเลข `to embed`, `~tokens` และ `requests` ให้ผู้ดูแลอนุมัติ** แล้วรอคำตอบ ห้ามไปขั้นถัดไปก่อนได้รับอนุมัติ
- **ถ้าไม่เป็นอย่างนั้น:** ขึ้น error ตอนอ่านคลัง ให้ส่งข้อความให้ผู้ดูแล

## ขั้นที่ 15: embedding ครั้งใหญ่ (ครั้งแรก หลังได้รับอนุมัติ)

- **ทำไม:** ทำครั้งเดียว ผลเก็บถาวรใน `state_dir` รอบต่อไปจ่ายเฉพาะบทความใหม่หรือบทความที่ข้อความเปลี่ยน
- **เริ่มงานแบบเบื้องหลัง** (ปิดหน้าต่างได้):
  ```powershell
  uv run atlas embed -c ..\runs\2026Q4\config.yaml --background
  ```
  ที่ควรเห็น: บรรทัดที่มี `running in the background: PID …` พร้อมคำสั่งดูสถานะและหยุด
- **ดูความคืบหน้า** (เปิดดูกี่ครั้งก็ได้):
  ```powershell
  uv run atlas status -c ..\runs\2026Q4\config.yaml
  ```
  ที่ควรเห็น: บรรทัด `status : running` และ `progress : 120,000 / 497,980 docs (24.1%)` พร้อมอัตราและเวลาที่เหลือ (ETA)
- **เสร็จเมื่อ** status ขึ้น `done`
- **ถ้าไม่เป็นอย่างนั้น:**
  - เน็ตหลุด เครื่องดับ หรือหยุดไปกลางคัน (status `interrupted` หรือ `stopped`): สั่งคำสั่ง `--background` เดิมซ้ำ ระบบทำต่อจากจุดเดิมโดยไม่จ่ายซ้ำ
  - `backing_off` = รอบริการตอบ ระบบลองใหม่เอง ไม่ต้องทำอะไร
  - ต้องการหยุดเอง: `uv run atlas embed-stop -c ..\runs\2026Q4\config.yaml`
  - `failed` หรือ error ถาวร (key ผิด เครดิตหมด) ให้แจ้งผู้ดูแลพร้อมบรรทัด `last error`

## ขั้นที่ 16: ดูค่าใช้จ่าย LLM แล้วขออนุมัติ (ทุกรอบที่ใช้ LLM — จุดอนุมัติที่ 2)

- **ทำไม:** LLM คิดเงินทุกครั้งที่เรียก ผู้ดูแลต้องเห็นตัวเลขก่อน (ถ้าไม่ใช้ LLM ข้ามขั้นนี้)
- **คำสั่ง** (ไม่เรียกบริการ ไม่เสียเงิน):
  ```powershell
  uv run atlas llm -c ..\runs\2026Q4\config.yaml --dry-run
  ```
- **ที่ควรเห็น:** 1 บรรทัดต่องาน เช่น
  ```
  label      <ชื่อโมเดล>: 812 items, 0 cached, 812 to call · ~1,950,000 input tokens, ≤ 487,200 output · cost ≤ 3.1 USD · spent this release 0.0 USD of 10.0
  ```
  ตัวเลขสำคัญคือ `to call` (จำนวนครั้งที่ต้องจ่าย) และ `cost ≤ … USD` (ค่าใช้จ่ายสูงสุด) งานที่ยังไม่มีข้อมูลพอจะขึ้น `skipped — …` ซึ่งปกติ
- **ส่งตัวเลขทุกบรรทัดให้ผู้ดูแลอนุมัติ** แล้วรอคำตอบ
- **ถ้าไม่เป็นอย่างนั้น:** ขึ้น `cost unknown (set price_per_mtok_in/out)` แปลว่ายังไม่ได้ใส่ราคาในขั้นที่ 11

## ขั้นที่ 17: รันทั้งรอบด้วยคำสั่งเดียว (ทุกรอบ)

- **ทำไม:** คำสั่งนี้ทำทุกอย่างต่อกัน: ตรวจคลัง → embedding เฉพาะส่วนที่ยังไม่มี → ถามยืนยันค่า LLM → วิเคราะห์ → ตรวจผล → สร้างหน้าเว็บ → วางข้อมูลลงเว็บ → ทำชุดไฟล์พร้อมอัปโหลด
- **คำสั่ง:**
  ```powershell
  cd D:\tci-research-atlas\pipeline
  uv run atlas quarterly --corpus D:\atlas-data\corpus\2026Q4 --release 2026Q4 --build-web
  ```
  - `--build-web` = สร้างหน้าเว็บใหม่ด้วยที่อยู่ใน `publish.site_url` (ใส่ทุกครั้งในรอบแรก หลัง `git pull` ที่มีการแก้หน้าเว็บ และเมื่อเปลี่ยนที่อยู่เว็บ ถ้าไม่แน่ใจ ใส่ไว้เสมอ)
- **ระหว่างทางจะเห็น:** หัวขั้นทีละขั้น เช่น `[quarterly] == corpus ==`, `== profile ==`, `== embed (dry run) ==`, `== embed ==`, `== llm (dry run) ==`, `== run ==`, `== validate ==`, `== web build ==`, `== publish ==`, `== deploy package ==`
- **คำถามยืนยัน LLM** (ถ้าใช้ LLM):
  ```
  pay for the LLM calls estimated above (details in …\runs\2026Q4\llm_dryrun.txt)? [y/N]:
  ```
  ตอบ `y` **เฉพาะเมื่อตัวเลขตรงกับที่ผู้ดูแลอนุมัติในขั้นที่ 16** ถ้าไม่แน่ใจ กด Enter (= ไม่) แล้วคำสั่งจะหยุดโดยยังไม่เสียเงิน
- **หมายเหตุ:** ขั้น embed ในคำสั่งนี้ไม่ถามยืนยัน ถ้ารอบนี้มีบทความใหม่จำนวนมากผิดปกติ ให้ทำขั้นที่ 14 ก่อนเสมอ
- **ใช้เวลา:** ประมาณ 1–2 ชั่วโมงสำหรับ 500,000 เรื่อง (ไม่รวม embedding ครั้งแรก) ปล่อยให้รันจนจบ
- **ที่ควรเห็นเมื่อเสร็จ:** สรุปผลบนจอ และบรรทัดสุดท้าย
  ```
  [quarterly] done — upload D:\tci-research-atlas\deploy\2026Q4\site (or a zip in D:\tci-research-atlas\deploy); the round is archived in D:\tci-research-atlas\runs\2026Q4
  ```
  ไฟล์ที่ได้:
  - `runs\2026Q4\summary.md` ตัวเลขสำคัญ เวลาแต่ละขั้น คำเตือน
  - `runs\2026Q4\validate.txt` ผลตรวจก่อนเผยแพร่
  - `deploy\2026Q4\site\` เว็บทั้งเว็บพร้อมอัปโหลด
  - `deploy\atlas-site-2026Q4.zip` (เว็บทั้งเว็บ) และ `deploy\atlas-data-2026Q4.zip` (เฉพาะข้อมูล)
- **ถ้าไม่เป็นอย่างนั้น:** ขึ้น `[quarterly] STOPPED: …` อ่านข้อความ แก้ตามที่บอก แล้วสั่งคำสั่งเดิมซ้ำ ส่วนที่จ่ายเงินไปแล้วไม่ถูกจ่ายซ้ำ ข้อความที่พบบ่อยอยู่ในตาราง "เมื่อเจอปัญหา" ท้ายคู่มือ

## ขั้นที่ 18: อ่านผลตรวจ (ทุกรอบ)

- **ทำไม:** ก่อนให้ใครเห็นตัวเลข ต้องแน่ใจว่าไม่มีข้อผิดพลาดและไม่มีข้อมูลส่วนบุคคลหลุด
- **เปิด `runs\2026Q4\validate.txt`** บรรทัดแรกบอกผล:
  - `atlas validate: OK — …` = ผ่าน
  - `atlas validate: WARNINGS — …` = มีคำเตือน (บรรทัด `WARN …`) อ่านให้ครบทุกบรรทัด และจดไว้ส่งผู้ดูแล
  - `atlas validate: ERRORS — …` = มีข้อผิดพลาด (บรรทัด `ERROR …`) คำสั่งในขั้นที่ 17 จะหยุดเองและไม่วางข้อมูลลงเว็บ
- **ถ้ามีบรรทัด `ERROR privacy: …` ห้ามเผยแพร่เด็ดขาด** (แปลว่ามีอีเมล ORCID หรือชื่อคนติดอยู่ในไฟล์ที่จะเผยแพร่) แจ้งผู้ดูแลทันทีพร้อมส่งบรรทัดนั้น วิธีแก้ที่มักใช้ (ทำเมื่อผู้ดูแลเห็นด้วย):
  - **ชื่อสถาบันที่มีชื่อคนติดมา** (เช่น "สมชาย ใจดี มหาวิทยาลัยมหิดล"): เติมแถวใน `institutions_aliases.csv` ของคลัง ให้สังกัดแบบนั้นชี้ไปสถาบันที่ถูก แล้วรันขั้นที่ 17 ซ้ำ
  - **ชื่อหน่วยงานจริงที่บังเอิญตรงกับชื่อผู้แต่ง:** ใส่สตริงนั้นใน `validation.privacy_allow` ของ `config.yaml` **เฉพาะเมื่อผู้ดูแลตรวจแล้วอนุญาต** แล้วรันขั้นที่ 17 ซ้ำ
  - **อีเมลหรือ ORCID:** หาว่ามาจากช่องไหนของคลัง แก้ที่ต้นทาง แล้วรันซ้ำ
- **เปิด `runs\2026Q4\summary.md`:** จำนวนบทความต้องใกล้เคียงกับใน `profile.md`
- **เปิด `runs\2026Q4\pipeline.log`** หาบรรทัดเหล่านี้ แล้วจดไว้รายงาน:
  - บรรทัดที่ขึ้นต้นด้วย `[ingest]` และมี `records → … articles (left out: duplicates …, year outside …, no title …` = จำนวนที่ตัดทิ้งแต่ละเหตุผล
  - บรรทัดที่ขึ้นต้นด้วย `[cluster]` = จำนวนหัวข้อ (`… topics`), กลุ่ม (`groups`) และสัดส่วนบทความที่ไม่ได้อยู่ในหัวข้อใด (`unassigned …%`) รอบที่จัดหัวข้อใหม่ทั้งชุดจะมี `N raw clusters → M topics` ด้วย ถ้าหัวข้อน้อยมากเทียบกับจำนวนบทความ หรือ unassigned สูงมาก ให้แจ้งผู้ดูแล

## ขั้นที่ 19: ตรวจเว็บบนเครื่องตัวเอง (ทุกรอบ ประมาณ 30 นาที)

- **ทำไม:** ดูเว็บแบบเดียวกับที่ประชาชนจะเห็น ก่อนอัปโหลดจริง
- **คำสั่ง** (เปิดเซิร์ฟเวอร์ทดสอบในเครื่อง เห็นได้เฉพาะเครื่องนี้):
  ```powershell
  cd D:\tci-research-atlas\web
  node scripts/serve.mjs --site ..\deploy\2026Q4\site
  ```
  ที่ควรเห็น: `[serve] http://127.0.0.1:4173/  site=..\deploy\2026Q4\site` แล้วเปิด <http://127.0.0.1:4173/> ในเบราว์เซอร์ (เลือกพอร์ตอื่นได้ด้วย `--port 4180`) หยุดเซิร์ฟเวอร์ด้วย Ctrl+C
- **ตรวจ 10 จุดนี้:**
  - [ ] หน้าแรกขึ้นชื่อรอบ `2026Q4` และ **ไม่มีป้าย "ข้อมูลตัวอย่าง"** ที่หน้าใดเลย
  - [ ] หน้า "สรุปผู้บริหาร" (`#/brief`) ตัวเลขแสดงครบ ไม่มีค่าว่างหรือ NaN
  - [ ] หน้า "สถานะหัวข้อ" (`#/emerging`) มีหัวข้อที่ "กำลังเกิดใหม่" กดเข้าหัวข้อหนึ่งแล้วมีกราฟและตาราง
  - [ ] ชื่อหัวข้ออ่านรู้เรื่อง ไม่ใช่ชุดคำสับสน (ถ้าใช้ LLM ดูขั้นที่ 20)
  - [ ] หน้า "สถาบัน" (`#/institutions`) มีชื่อมหาวิทยาลัยจริง ไม่มีชื่อคน อีเมล หรือที่อยู่
  - [ ] หน้า "แผนที่จังหวัด" (`#/regions`) มีตัวเลข และตารางจังหวัดครบ 77 จังหวัด
  - [ ] หน้า "ค้นหาบทความ" (`#/search`) ค้นคำไทยที่ใช้บ่อย (เช่น "ผู้สูงอายุ") ได้ผล และลิงก์ไปบทความเปิดได้
  - [ ] สลับภาษาไทย/English ได้
  - [ ] ย่อหน้าต่างให้แคบเท่ามือถือ แล้วไม่ต้องเลื่อนซ้าย-ขวา
  - [ ] ไม่มีหน้าขาว หน้าที่ไม่มีข้อมูลต้องบอกเหตุผล
- **ถ้าพบชื่อสถาบันที่ผิดหรือซ้ำ:** เติมแถวใน `institutions_aliases.csv` ของคลัง (ชื่อเรียก → สถาบัน) ตาม [corpus/README หัวข้อ 11.2](corpus/README.md) แล้วรันขั้นที่ 17 ซ้ำ

## ขั้นที่ 20: ตรวจชื่อหัวข้อ (ทุกรอบที่ใช้ LLM)

- **ทำไม:** ชื่อหัวข้อที่เครื่องตั้งอาจผิด บรรณาธิการช่วยตรวจประมาณ 50 หัวข้อต่อรอบ
- **ส่งออกไฟล์ให้บรรณาธิการ:**
  ```powershell
  cd D:\tci-research-atlas\pipeline
  uv run atlas review export -c ..\runs\2026Q4\config.yaml
  ```
  ที่ควรเห็น: `wrote …\output\review\2026Q4_label_review.csv` (เปิดใน Excel ได้) บรรณาธิการกรอกคอลัมน์ `name_th_fixed` / `name_en_fixed` ในแถวที่ต้องแก้
- **นำไฟล์ที่แก้แล้วกลับเข้า:**
  ```powershell
  uv run atlas review import <ไฟล์.csv> -c ..\runs\2026Q4\config.yaml
  ```
  ที่ควรเห็น: `N corrections from M reviewed topics → …label_overrides.csv …`
- **จากนั้นรันขั้นที่ 17 ซ้ำ** (ชื่อรอบเดิม) ให้ชื่อใหม่ขึ้นเว็บ คำตอบ LLM เดิมมาจาก cache ไม่จ่ายซ้ำ
- **ถ้าไม่เป็นอย่างนั้น:** ขึ้น `set labeling.overrides_path in the config` แปลว่าลบบรรทัด `overrides_path` ออกจาก `config.yaml` ให้ใส่กลับ (ขั้นที่ 11) แล้วทำขั้นที่ 13 ใหม่

## ขั้นที่ 21: ส่งผู้ดูแลอนุมัติก่อนเปิดสาธารณะ (ทุกรอบ — จุดอนุมัติที่ 3 ห้ามข้าม)

เมื่อเปิดสาธารณะแล้ว ผู้บริหารและประชาชนจะนำตัวเลขไปอ้างอิง ส่งข้อมูลต่อไปนี้ให้ผู้ดูแล และรอคำตอบ "อนุมัติ" ก่อนไปขั้นที่ 22

- ไฟล์ `summary.md`, `validate.txt`, `profile.md` ของรอบนี้
- ค่าที่จดจาก `pipeline.log` ในขั้นที่ 18 (จำนวนที่ตัดทิ้ง และบรรทัด `[cluster]`)
- ผลตรวจ 10 จุดในขั้นที่ 19 (ผ่านครบหรือไม่ ข้อไหนมีปัญหา)
- ภาพหน้าจอ: หน้าแรก, สรุปผู้บริหาร, หน้าสถาบัน (ขนาดเดสก์ท็อปและมือถือ)
- ถ้าใช้ LLM: ยืนยันว่าบรรณาธิการตรวจชื่อหัวข้อแล้ว (ขั้นที่ 20)

## ขั้นที่ 22: เตรียมเซิร์ฟเวอร์กับทีม IT (ครั้งแรก)

- **ทำไม:** เว็บนี้เป็น static site ทีม IT ต้องตั้งเซิร์ฟเวอร์ให้ส่งไฟล์ถูกชนิด เร็ว และไม่ค้างข้อมูลเก่า
- **ส่งข้อมูลนี้ให้ทีม IT** พร้อม [ภาคผนวก ก](#ภาคผนวก-ก-ตัวอย่างการตั้งค่าเซิร์ฟเวอร์-ให้ทีม-it-ปรับใช้):
  - ไม่ต้องมีฐานข้อมูล PHP Node.js หรือโปรแกรมใดบนเซิร์ฟเวอร์ ส่งไฟล์อย่างเดียว
  - วางที่รากของโดเมน หรือโฟลเดอร์ย่อย (เช่น `https://www.example.go.th/atlas/`) ก็ได้ เพราะเว็บโหลดไฟล์ทุกไฟล์แบบอ้างอิงจากตำแหน่งของตัวเอง
  - ที่อยู่ของแต่ละหน้าใช้ `#` (เช่น `…/#/topics/T000123`) เซิร์ฟเวอร์จึง **ไม่ต้องตั้ง rewrite** ใด ๆ
  - ต้องมี HTTPS
  - ที่อยู่สุดท้ายต้องตรงกับ `publish.site_url` (ขั้นที่ 11) ทุกตัวอักษร
  - ขนาดรวมของเว็บหลายร้อย MB เมื่อใช้ข้อมูลจริง (ดัชนีค้นหาและแผนที่บทความเป็นส่วนใหญ่) และโตขึ้นเล็กน้อยทุกรอบ
- **ตกลงวิธีอัปโหลด** กับทีม IT เช่น SFTP (โปรแกรม WinSCP), `robocopy` ไปโฟลเดอร์แชร์ หรือ `rsync` ตัวอย่างอยู่ในขั้นที่ 23

## ขั้นที่ 23: อัปโหลดขึ้นเซิร์ฟเวอร์ (ทุกรอบ หลังได้รับอนุมัติเท่านั้น)

- **ทำไม:** ข้อมูลรอบใหม่จะเห็นได้เมื่อไฟล์ขึ้นเซิร์ฟเวอร์ครบ
- **อัปโหลดอะไร:**
  - **ครั้งแรก หรือเมื่อหน้าเว็บถูก build ใหม่** (ใช้ `--build-web` ในขั้นที่ 17): ทุกไฟล์ใน `deploy\2026Q4\site\` (หรือแตก `deploy\atlas-site-2026Q4.zip` ซึ่งมีไฟล์ชุดเดียวกัน)
  - **รอบถัดไปที่หน้าเว็บไม่เปลี่ยน:** เฉพาะ `deploy\atlas-data-2026Q4.zip` (แตกในเครื่องก่อน ได้ `data\` และ `atlas-offline.html`) ข้างใน `data\` มีรอบเก่าด้วย เว็บจึงเทียบกับรอบก่อนได้
  - ถ้าไม่แน่ใจว่าหน้าเว็บเปลี่ยนไหม ให้อัปโหลดทั้งเว็บ
- **ลำดับการอัปโหลด** (ผู้อ่านจะไม่เห็นเว็บครึ่ง ๆ กลาง ๆ):
  1. โฟลเดอร์ `assets\` และไฟล์อื่น ๆ ที่รากเว็บ ยกเว้น `index.html` และ `atlas-offline.html`
  2. `data\2026Q4\` (รอบใหม่) และโฟลเดอร์รอบอื่นใน `data\`
  3. `data\feeds\` (ถ้ามี)
  4. **ท้ายสุด:** `data\latest.json`, `atlas-offline.html` และ `index.html`

  เหตุผล: หน้าเว็บอ่าน `data\latest.json` ก่อน ไฟล์นี้บอกว่ารอบล่าสุดคือรอบไหน (เช่น `{"release": "2026Q4", "path": "2026Q4/manifest.json", …}`) แล้วจึงไปโหลดไฟล์ใน `data\2026Q4\` ถ้า `latest.json` ขึ้นก่อน ผู้อ่านบางคนจะเจอไฟล์ที่ยังไม่ครบ
- **อย่าลบไฟล์บนเซิร์ฟเวอร์ที่ไม่มีในเครื่อง** (เช่น ไฟล์ใน `assets\` ของรุ่นก่อน) ผู้อ่านที่เปิดหน้าเก่าค้างไว้ยังใช้อยู่ และไม่มีผลเสีย และอย่าเขียนทับไฟล์ตั้งค่าของเซิร์ฟเวอร์ (`.htaccess` / `web.config`) ที่ทีม IT วางไว้
- **ตัวอย่างคำสั่ง** (ให้ทีม IT ยืนยันปลายทางก่อนใช้):
  - Windows ไปโฟลเดอร์แชร์ของเซิร์ฟเวอร์ (`\\webserver\atlas` เป็นตัวอย่าง):
    ```powershell
    $src = "D:\tci-research-atlas\deploy\2026Q4\site"
    $dst = "\\webserver\atlas"
    robocopy $src $dst /E /XF index.html latest.json atlas-offline.html
    robocopy "$src\data" "$dst\data" latest.json
    robocopy $src $dst index.html atlas-offline.html
    ```
    `robocopy` จบด้วยรหัส 0–7 = ปกติ (8 ขึ้นไป = มีไฟล์คัดลอกไม่ได้)
  - Linux / macOS หรือ Git Bash ที่มี `rsync` (`user@webserver:/var/www/atlas/` เป็นตัวอย่าง):
    ```bash
    SRC=/d/tci-research-atlas/deploy/2026Q4/site/
    DST=user@webserver:/var/www/atlas/
    rsync -av --exclude index.html --exclude data/latest.json --exclude atlas-offline.html "$SRC" "$DST"
    rsync -av "${SRC}data/latest.json" "${DST}data/"
    rsync -av "${SRC}index.html" "${SRC}atlas-offline.html" "$DST"
    ```
  - WinSCP: ลากโฟลเดอร์ตามลำดับข้างบน เก็บ `data\latest.json`, `atlas-offline.html` และ `index.html` ไว้ลากเป็นรอบสุดท้าย

## ขั้นที่ 24: ตรวจหลังขึ้นเว็บ (ทุกรอบ ทำทันที)

เปิดเว็บสาธารณะในหน้าต่างส่วนตัว (Incognito / InPrivate — ไม่มี cache ของเบราว์เซอร์) แล้วเช็ก:

- [ ] หน้าแรกขึ้นรอบ `2026Q4` และ **ไม่มีป้าย "ข้อมูลตัวอย่าง"**
- [ ] `<ที่อยู่เว็บ>/data/latest.json` เปิดได้ และ `"release"` เป็น `"2026Q4"`
- [ ] `<ที่อยู่เว็บ>/robots.txt` เปิดได้ บรรทัด `Sitemap:` เป็นที่อยู่เว็บจริง และ **ไม่มีบรรทัดที่เป็น `Disallow: /` เฉย ๆ** (บรรทัด `Disallow: /offline-template.html` มีได้ เป็นปกติ)
- [ ] `<ที่อยู่เว็บ>/sitemap.xml` เปิดได้ และมีที่อยู่เว็บจริง
- [ ] ดูซอร์สของหน้าแรก (Ctrl+U) ค้นคำว่า `noindex` ต้องไม่เจอ และ `rel="canonical"` ต้องเป็นที่อยู่เว็บจริง (ถ้าเป็นที่อยู่อื่น แปลว่าลืม `--build-web` หรือ `publish.site_url` ผิด)
- [ ] ตรวจการตั้งค่าเซิร์ฟเวอร์ (ใน PowerShell ใช้ `curl.exe` ไม่ใช่ `curl`):
  ```powershell
  curl.exe -sI https://<ที่อยู่เว็บ>/data/latest.json
  curl.exe -sI -H "Accept-Encoding: gzip" https://<ที่อยู่เว็บ>/data/2026Q4/topics.json
  ```
  ที่ควรเห็น: `HTTP/… 200`, `Content-Type: application/json`, `Cache-Control: no-cache` และบรรทัดที่สองมี `Content-Encoding: gzip` (หรือ `br`)
- [ ] เปิดจากมือถือจริง 1 เครื่อง แล้วลองแชร์ลิงก์ใน LINE ต้องขึ้นรูปปกพร้อมโลโก้ TCI
- [ ] รายงานผู้ดูแลพร้อมลิงก์เว็บ

ถ้าหน้าแรกยังเป็นรอบเก่า: กด Ctrl+F5 ตรวจว่า `data/latest.json` บนเซิร์ฟเวอร์เป็นไฟล์ใหม่ และ `Cache-Control` ไม่ใช่ค่ายาว (ภาคผนวก ก) ถ้ายังไม่หาย แจ้งผู้ดูแลทันที

**ส่วนที่ผู้ดูแลทำเอง** (ใช้บัญชี Google ของผู้ดูแล): ยืนยันเว็บใน Google Search Console และส่ง `sitemap.xml` ตาม [`docs/OPERATIONS.md` §22](OPERATIONS.md)

## ขั้นที่ 25: สำรองข้อมูล (ทุกรอบ)

สำรองไปที่เก็บภายในองค์กร (ไม่ใช่ GitHub):

- `D:\atlas-data\state\` ทั้งโฟลเดอร์ ถ้าหาย ต้องจ่ายค่า embedding และ LLM ใหม่ทั้งหมด และประวัติหัวข้อข้ามรอบขาด
- `D:\atlas-data\output\` (มีข้อมูลเต็มของทุกรอบ ใช้ย้อนกลับในขั้นที่ 27)
- `D:\tci-research-atlas\runs\2026Q4\`
- `D:\tci-research-atlas\deploy\atlas-data-2026Q4.zip`
- คลัง `D:\atlas-data\corpus\2026Q4\` (เก็บอย่างน้อย 2 รอบล่าสุด)
- `D:\tci-research-atlas\pipeline\registry\` (ชื่อหัวข้อที่บรรณาธิการแก้)

## ขั้นที่ 26: รอบถัดไป (ทุก 3 เดือน)

ทำตามลำดับเดิม แต่ข้ามขั้นที่ทำครั้งเดียว:

1. ขั้นที่ 2 (`git pull` + `uv sync --extra api --extra fast --extra leiden` + `npm ci` ใน `web`)
2. ขั้นที่ 3–7 กับคลังชุดใหม่ (ใช้โฟลเดอร์ใหม่ เช่น `D:\atlas-data\corpus\2027Q1`)
3. ขั้นที่ 13 ด้วยชื่อรอบใหม่ (`--release 2027Q1`) — ชื่อรอบใหม่ต้องไม่เก่ากว่ารอบก่อน
4. ขั้นที่ 14 อีกครั้ง เพื่อดูจำนวนบทความใหม่ที่ต้องจ่าย (ปกติน้อยกว่าครั้งแรกมาก) และขออนุมัติถ้าผู้ดูแลกำหนด
5. ขั้นที่ 16–25 (ไม่ต้องทำขั้นที่ 15 เพราะขั้นที่ 17 embed เฉพาะบทความใหม่ให้เอง)

## ขั้นที่ 27: ย้อนกลับเป็นรอบก่อน (เมื่อผู้ดูแลสั่ง)

- **ทำไม:** ถ้าพบปัญหาในรอบใหม่หลังเปิดเว็บ ต้องกลับไปแสดงรอบก่อนชั่วคราว
- **ห้ามแก้ `data/latest.json` บนเซิร์ฟเวอร์เอง** เพราะรอบเก่าบนเว็บถูกตัดให้เหลือเฉพาะไฟล์ที่ใช้เทียบ (หน้าวารสาร สถาบัน และการค้นหาของรอบนั้นจะเสีย)
- **คำสั่ง** (ในเครื่องรันงาน ซึ่งยังมีข้อมูลเต็มของรอบก่อนใน `output\data\2026Q3\`):
  ```powershell
  cd D:\tci-research-atlas\pipeline
  uv run atlas publish -c ..\runs\2026Q3\config.yaml --release 2026Q3 --set-latest --site ..\deploy\2026Q4\site
  ```
  - `--release 2026Q3` = รอบที่จะกลับไปแสดง
  - `--set-latest` = ให้ `latest.json` ชี้รอบนี้ แม้มีรอบที่ใหม่กว่าอยู่บนเว็บ
  - `--site` = โฟลเดอร์เว็บชุดล่าสุดที่อัปโหลดไป
  - คำสั่งตรวจรอบนั้นอีกครั้งก่อนวาง ถ้าขึ้น `refused: validation exit code 1` และผู้ดูแลยืนยันว่าคำเตือนเหล่านั้นยอมรับแล้ว ให้เติม `--allow-warnings`
- **ที่ควรเห็น:** บรรทัด `latest:` และ `offline:` ชี้ไฟล์ในโฟลเดอร์ `..\deploy\2026Q4\site`
- **แล้วอัปโหลดตามลำดับในขั้นที่ 23:** `data\2026Q3\` ก่อน แล้ว `data\latest.json` และ `atlas-offline.html` ท้ายสุด จากนั้นตรวจตามขั้นที่ 24 (`"release"` ต้องเป็น `"2026Q3"`)
- รอบถัดไปที่รันตามปกติจะกลับมาชี้รอบใหม่สุดเอง

---

# เมื่อเจอปัญหา

| อาการ | ทำอย่างไร |
|---|---|
| `atlas profile` ไม่ผ่าน | อ่านรายการท้ายหน้าจอ (`[profile] fix before the hand-over:`) และหัวข้อ "ต้องแก้ก่อนส่ง" ใน `profile.md` แก้ไฟล์ต้นทาง แล้วตรวจใหม่ |
| `atlas embed --check` ขึ้น `FAILED` | key, `base_url` หรือ `model` ผิด แจ้งผู้ดูแลพร้อมข้อความ error |
| embedding ค้าง หรือเน็ตหลุด | สั่งคำสั่ง embed เดิมซ้ำ ทำต่อจากเดิมและไม่จ่ายซ้ำ |
| `[quarterly] STOPPED: …` | อ่านข้อความ แก้ตามนั้น แล้วสั่งคำสั่งเดิมซ้ำ |
| `[quarterly] WARNING: embedding.provider is api but ATLAS_EMBED_API_KEY is not set` | ยังไม่ได้ตั้ง key หรือยังใช้หน้าต่างเดิม ทำขั้นที่ 10 แล้วเปิด PowerShell ใหม่ |
| `STOPPED: LLM cost not confirmed …` | ตอบไม่ หรือกด Enter ตอนถามยืนยัน ยังไม่เสียเงิน รันใหม่เมื่อได้รับอนุมัติ |
| `validate` มี `ERROR` โดยเฉพาะ `privacy:` | **ห้ามเผยแพร่** แจ้งผู้ดูแลทันที (วิธีแก้ดูขั้นที่ 18) |
| `NOTICE: work_dir holds the unfinished round …` | รอบก่อนยังไม่เสร็จ ระบบกำลังทำรอบนั้นต่อ เกิดเมื่อไม่ได้ใส่ `--release` ถ้าตั้งใจทำรอบใหม่ ให้ใส่ `--release <รอบใหม่>` |
| `STOPPED: … embedding provider 'lite' (tests only) …` | ใช้ embedding สำหรับทดสอบอยู่ แก้ `embedding.provider` ใน `config.yaml` เป็น `api` (หรือ `local`) แล้วทำขั้นที่ 13 ใหม่ |
| `STOPPED: Node.js (npm) is needed …` | ยังไม่ได้ติดตั้ง Node.js ทำขั้นที่ 9 |
| เว็บขึ้น "ข้อมูลตัวอย่าง" หรือรอบเก่าหลังอัปโหลด | Ctrl+F5 ตรวจ `data/latest.json` บนเซิร์ฟเวอร์ และการตั้ง cache (ภาคผนวก ก) ถ้ายังไม่หายแจ้งผู้ดูแล |
| `curl.exe -sI …` ไม่มี `application/json` หรือ `no-cache` | ส่งภาคผนวก ก ให้ทีม IT ตั้งค่า |
| รายละเอียดอื่น ๆ | [`docs/OPERATIONS.md` §3 Troubleshooting](OPERATIONS.md) |

---

# ภาคผนวก ก: ตัวอย่างการตั้งค่าเซิร์ฟเวอร์ (ให้ทีม IT ปรับใช้)

ตัวอย่างนี้เป็น **จุดเริ่มต้น** ทีม IT ต้องปรับชื่อโดเมน path ใบรับรอง HTTPS และนโยบายความปลอดภัยขององค์กรเอง

**สิ่งที่เว็บต้องการ:**

| เรื่อง | ค่าที่ต้องการ |
|---|---|
| HTTPS | บังคับ (`http://` ส่งต่อไป `https://`) |
| rewrite | ไม่ต้องมี (หน้าใช้ `#/…`) |
| MIME type | `.html` text/html · `.js` text/javascript (หรือ application/javascript) · `.css` text/css · `.json` application/json · `.woff2` font/woff2 · `.png` image/png · `.xml` application/xml (หรือ text/xml; ใช้กับ `sitemap.xml` และฟีด `data/feeds/*.xml`) · `.txt` text/plain — ทุกชนิดที่เป็นข้อความใช้ UTF-8 |
| การบีบอัด | gzip หรือ brotli สำหรับ `.json`, `.js`, `.css`, `.html`, `.xml` (ไฟล์ JSON ของข้อมูลเล็กลงหลายเท่า) |
| cache นาน | **เฉพาะ** โฟลเดอร์ `assets/` (ชื่อไฟล์มีรหัสเปลี่ยนทุกครั้งที่ build) → `Cache-Control: public, max-age=31536000, immutable` |
| ไม่ cache นาน | ไฟล์อื่นทั้งหมด โดยเฉพาะ `index.html`, `data/latest.json`, `data/**`, `atlas-offline.html`, `robots.txt`, `sitemap.xml` → `Cache-Control: no-cache` (เบราว์เซอร์ถามเซิร์ฟเวอร์ทุกครั้งว่าไฟล์เปลี่ยนไหม ถ้าไม่เปลี่ยนก็ไม่ดาวน์โหลดซ้ำ) เพื่อให้รอบใหม่ขึ้นทันที |
| header อื่น | ถ้าองค์กรตั้ง Content-Security-Policy ต้องทดสอบให้หน้าเว็บยังทำงาน (หน้าแรกมีสคริปต์ JSON-LD ในหน้าและไอคอนแบบ `data:`) — เว็บไม่โหลดอะไรจากเซิร์ฟเวอร์ภายนอก |

### Nginx

```nginx
# ตัวอย่าง — ปรับ server_name, path และใบรับรองตามเครื่องจริง
server {
    listen 80;
    server_name atlas.example.go.th;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    http2 on;                                   # Nginx รุ่นเก่ากว่า 1.25.1: ใช้ "listen 443 ssl http2;" แทนสองบรรทัดนี้
    server_name atlas.example.go.th;
    ssl_certificate     /etc/ssl/atlas/fullchain.pem;
    ssl_certificate_key /etc/ssl/atlas/privkey.pem;

    root  /var/www/atlas;                       # โฟลเดอร์ที่วางไฟล์จาก deploy/<รอบ>/site/
    index index.html;
    charset utf-8;
    charset_types text/css text/plain text/javascript application/javascript application/json application/xml text/xml;
    # MIME type: ใช้ mime.types ที่ include ไว้ใน http { } (รุ่นใหม่มี json และ woff2 แล้ว — ตรวจด้วย curl -I)

    gzip on;
    gzip_min_length 1024;
    gzip_types text/css text/plain text/javascript application/javascript application/json application/xml text/xml image/svg+xml;

    location /assets/ {
        add_header Cache-Control "public, max-age=31536000, immutable";
        try_files $uri =404;
    }
    location / {
        add_header Cache-Control "no-cache";
        try_files $uri $uri/ =404;
    }
}
```

ถ้าวางในโฟลเดอร์ย่อย เช่น `https://www.example.go.th/atlas/` ให้ใช้ `location /atlas/assets/ { … }` และ `location /atlas/ { … }` โดยให้ `root` ชี้โฟลเดอร์ที่อยู่เหนือ `atlas/`

### Apache (ไฟล์ `.htaccess` ที่รากของเว็บ — ต้องเปิด `AllowOverride` และโมดูล `mod_headers`, `mod_deflate`)

```apache
# ตัวอย่าง — ไฟล์นี้ไม่อยู่ในชุด deploy วางบนเซิร์ฟเวอร์ครั้งเดียว และอย่าลบตอนอัปโหลดรอบใหม่
AddDefaultCharset utf-8
AddCharset utf-8 .js .css .json .xml .txt
AddType text/javascript .js
AddType application/json .json
AddType font/woff2 .woff2
AddType application/xml .xml

<IfModule mod_deflate.c>
  AddOutputFilterByType DEFLATE text/html text/css text/plain text/javascript application/javascript application/json application/xml text/xml image/svg+xml
</IfModule>

<IfModule mod_headers.c>
  Header set Cache-Control "no-cache"
  <If "%{REQUEST_URI} =~ m#/assets/#">
    Header set Cache-Control "public, max-age=31536000, immutable"
  </If>
</IfModule>
```

การบังคับ HTTPS ให้ตั้งที่ VirtualHost ของพอร์ต 80 (`Redirect permanent / https://atlas.example.go.th/`)

### IIS (ไฟล์ `web.config` ที่รากของเว็บ)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!-- ตัวอย่าง — ไฟล์นี้ไม่อยู่ในชุด deploy วางบนเซิร์ฟเวอร์ครั้งเดียว และอย่าลบตอนอัปโหลดรอบใหม่ -->
<configuration>
  <system.webServer>
    <staticContent>
      <remove fileExtension=".json" />
      <mimeMap fileExtension=".json" mimeType="application/json; charset=utf-8" />
      <remove fileExtension=".woff2" />
      <mimeMap fileExtension=".woff2" mimeType="font/woff2" />
      <clientCache cacheControlMode="DisableCache" />
    </staticContent>
    <urlCompression doStaticCompression="true" />
  </system.webServer>
  <location path="assets">
    <system.webServer>
      <staticContent>
        <clientCache cacheControlMode="UseMaxAge" cacheControlMaxAge="365.00:00:00" />
      </staticContent>
    </system.webServer>
  </location>
</configuration>
```

- `DisableCache` ทำให้ IIS ส่ง `Cache-Control: no-cache` ส่วน `assets` ได้ cache 1 ปี
- การบีบอัดไฟล์ `application/json` ต้องเพิ่มชนิดนี้ใน `staticTypes` ของ `httpCompression` ระดับเซิร์ฟเวอร์ (ทีม IT ทำใน IIS Manager หรือ `applicationHost.config`) และต้องติดตั้ง Static Content Compression
- การบังคับ HTTPS ตั้งใน IIS (HTTP Redirect หรือ URL Rewrite ของทีม IT)

### ตรวจหลังตั้งค่า

```powershell
curl.exe -sI https://<ที่อยู่เว็บ>/
curl.exe -sI https://<ที่อยู่เว็บ>/data/latest.json
curl.exe -sI -H "Accept-Encoding: gzip" https://<ที่อยู่เว็บ>/data/<รอบ>/topics.json
```

- หน้าแรกและ `latest.json` ต้องมี `Cache-Control: no-cache`
- `latest.json` ต้องมี `Content-Type: application/json`
- บรรทัดที่สามต้องมี `Content-Encoding: gzip` (หรือ `br`)
- ไฟล์ใน `assets/` (ดูชื่อไฟล์ได้จากโฟลเดอร์ `deploy\<รอบ>\site\assets\`) ต้องมี `max-age=31536000`

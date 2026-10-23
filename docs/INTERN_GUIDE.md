# คู่มือนักศึกษาฝึกงาน: เตรียมคลังบทความ → รันวิเคราะห์ → เปิดเว็บให้ประชาชนใช้

มี 2 งาน ทำตามลำดับ งาน 2 เริ่มได้เมื่องาน 1 ผ่านเกณฑ์ครบ

| งาน | ผลที่ต้องได้ | เอกสารหลัก |
|---|---|---|
| **1. เตรียมคลังบทความ (corpus)** | โฟลเดอร์คลังที่ `atlas profile` ขึ้นว่า OK | [`docs/corpus/README.md`](corpus/README.md) |
| **2. รันวิเคราะห์ + เอาเว็บขึ้นสาธารณะ** | เว็บ TCI Research Atlas ที่ประชาชนเปิดใช้ได้ ด้วยข้อมูลจริง | คู่มือนี้ + [`docs/OPERATIONS.md`](OPERATIONS.md) |

ข้อควรจำ:
- **ข้อมูลบทความมีชื่อผู้แต่ง (ข้อมูลส่วนบุคคล)** เก็บในเครื่องหรือโฟลเดอร์ภายในองค์กรเท่านั้น ห้าม commit หรือ push ข้อมูลจริงขึ้น GitHub ห้ามอัปโหลดขึ้นบริการออนไลน์ใด ๆ
- **API key** (ใช้จ่ายเงินจริง) ใส่ใน environment variable เท่านั้น ห้ามเขียนลงไฟล์ ห้ามส่งในแชต ห้าม commit
- **ทุกขั้นที่เสียเงิน** (embedding, LLM) ต้องดู `--dry-run` และส่งตัวเลขให้ผู้ดูแลอนุมัติก่อนกดรันจริง
- ขั้นไหนติดปัญหา หยุด จดข้อความ error ทั้งบรรทัด แล้วถามผู้ดูแล อย่าลองแก้ค่าในโค้ดเอง
- คำสั่งทุกตัวใน PowerShell บน Windows (macOS/Linux ใช้เหมือนกันใน Terminal)

---

# งาน 1: เตรียมคลังบทความ (corpus)

ทำตาม [`docs/corpus/README.md`](corpus/README.md) โดยสรุปขั้นตอนได้ดังนี้

1. **ติดตั้งโปรแกรมครั้งแรก** (README หัวข้อ 12): Git, uv, `git clone` repo, `uv sync` ใช้เวลาประมาณ 15 นาที
2. **อัปเดตเป็นรุ่นล่าสุดก่อนเริ่มงานทุกสัปดาห์:**
   ```powershell
   cd D:\tci-research-atlas
   git pull
   cd pipeline
   uv sync --extra api --extra fast --extra leiden
   ```
3. **ทำนำร่อง:** บทความประมาณ 1,000 เรื่องจาก 3 วารสาร พร้อมไฟล์ประกอบครบ ตรวจด้วย `atlas profile` จนขึ้น `[profile] OK — nothing to fix` แล้วส่งให้ผู้ดูแลดู
4. **ทำทั้งคลัง** ด้วยหลักเดียวกัน:
   - ไฟล์ประกอบ: `journals.csv`, `institutions_aliases.csv`, `province_population.csv`, `ror.zip` (ถ้าทำได้) และ `README.txt` ที่บันทึกการตัดสินใจ
   - `institutions_aliases.csv` ต้องครอบคลุมแถวสังกัดอย่างน้อย 80% (`atlas profile` บอกให้)
5. **ตรวจรอบสุดท้าย:**
   ```powershell
   cd D:\tci-research-atlas\pipeline
   uv run atlas profile D:\atlas-data\corpus\2026Q4 --md D:\atlas-data\profile.md --aliases-todo D:\atlas-data\aliases_todo.csv
   ```
   ต้องจบด้วย `[profile] OK — nothing to fix` และไม่มีรายการ "ต้องแก้ก่อนส่ง"
6. **วางคลังให้เป็นระเบียบ:** แยกโฟลเดอร์ตามรอบ ไม่แก้คลังของรอบเก่า
   ```
   D:\atlas-data\corpus\2026Q4\articles\part-0001.jsonl.gz …
   D:\atlas-data\corpus\2026Q4\journals.csv  (+ ไฟล์ประกอบอื่น + README.txt)
   ```
7. แจ้งผู้ดูแลว่าเสร็จ พร้อมแนบ `profile.md` แล้วไปงาน 2

---

# งาน 2: รันวิเคราะห์ แล้วเอาเว็บขึ้นสาธารณะ

## 2.0 สิ่งที่ต้องได้รับจากผู้ดูแลก่อนเริ่ม

เช็กให้ครบ ถ้าขาดข้อไหน ขอก่อน อย่าเดา

- [ ] **API key สำหรับ embedding** (และ LLM ถ้าจะใช้) ส่งผ่านช่องทางที่ปลอดภัย พร้อมค่า `base_url`, ชื่อ `model` และ `dimensions` ที่ใช้
- [ ] **วงเงินที่อนุมัติ** สำหรับ embedding ครั้งใหญ่ และสำหรับ LLM ต่อรอบ
- [ ] **วิธีเผยแพร่เว็บ** ว่าใช้ทางไหน:
  - **ทาง A: GitHub Pages** (เว็บสาธารณะที่ `https://santipongth.github.io/tci-research-atlas/`) ต้องได้สิทธิ์ Write ใน repo และบัญชี GitHub ที่ล็อกอิน `gh` ได้ หรือส่งไฟล์ zip ให้ผู้ดูแลกดเอง
  - **ทาง B: เซิร์ฟเวอร์ขององค์กร** ต้องรู้ที่อยู่เว็บจริง (เช่น `https://atlas.tci-thailand.org/`) และวิธีอัปโหลดไฟล์ขึ้นเซิร์ฟเวอร์
- [ ] **ที่อยู่เว็บสาธารณะที่จะใช้** (`publish.site_url`)
- [ ] **ชื่อผู้ที่จะตรวจและอนุมัติก่อนเปิดเว็บ** (ขั้น 2.7)
- [ ] เครื่องรันงาน: RAM ≥ 16 GB, ที่ว่างบนดิสก์ ≥ 50 GB, ต่ออินเทอร์เน็ตได้ตลอด 2–3 ชั่วโมงแรก

## 2.1 ติดตั้งเครื่องมือครบ (ครั้งแรกครั้งเดียว)

1. **Node.js 24** (ใช้ build เว็บ): ดาวน์โหลดจาก <https://nodejs.org> เลือก LTS ที่เป็น 24 ตรวจ: `node --version`
2. **ถ้าใช้ทาง A:** ติดตั้ง GitHub CLI <https://cli.github.com> แล้ว `gh auth login` (เลือก GitHub.com → HTTPS → Login with a web browser)
3. ติดตั้งส่วนของโปรแกรม:
   ```powershell
   cd D:\tci-research-atlas\pipeline
   uv sync --extra api --extra fast --extra leiden
   cd ..\web
   npm ci
   ```

## 2.2 ตั้งค่า (ครั้งแรกครั้งเดียว)

1. **ตั้ง API key** (ค่าถาวรต่อผู้ใช้เครื่องนี้) แล้วปิดและเปิด PowerShell ใหม่ ซึ่งหน้าต่างเดิมยังไม่เห็นค่า:
   ```powershell
   setx ATLAS_EMBED_API_KEY "ใส่-key-ที่ได้รับ"
   setx ATLAS_LLM_API_KEY   "ใส่-key-ที่ได้รับ"
   ```
   (ใช้ key เดียวกันได้ถ้าผู้ดูแลบอกว่าได้ ถ้าไม่ใช้ LLM ข้ามบรรทัดที่สอง)
2. **สร้างไฟล์ตั้งค่า:**
   ```powershell
   cd D:\tci-research-atlas\pipeline
   copy config.example.yaml config.yaml
   ```
   ไฟล์นี้อยู่ใน `.gitignore` อยู่แล้ว (ไม่เข้า git)
3. **แก้ `config.yaml`** เฉพาะค่าเหล่านี้ ค่าอื่นใช้ค่าเดิม:

   ```yaml
   pipeline:
     work_dir: D:/atlas-data/work          # ลบได้เสมอ
     output_dir: D:/atlas-data/output
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
     site_url: https://santipongth.github.io/tci-research-atlas/   # หรือที่อยู่เว็บจริงของทาง B
   ```

   **ถ้าผู้ดูแลอนุมัติให้ใช้ LLM** (ตั้งชื่อหัวข้อและเขียนคำอธิบายภาษาง่าย) ให้เพิ่ม:
   ```yaml
   labeling:  { provider: llm }
   narrative: { provider: llm }
   llm:
     budget_usd: ...                       # วงเงินต่อรอบที่ได้รับอนุมัติ
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
   (ถ้าไม่ใช้ LLM ไม่ต้องใส่อะไรเพิ่ม ระบบใช้ประโยคแม่แบบจากตัวเลข)
4. **ลองเช็กว่า key และปลายทางใช้ได้** ใช้เวลาไม่กี่วินาที ไม่เสียเงินมาก:
   ```powershell
   uv run atlas embed -c config.yaml --check
   ```
   ถ้าขึ้น error เรื่อง key / URL / model ให้แจ้งผู้ดูแลก่อนไปต่อ

## 2.3 ตรวจคลังอีกครั้งบนเครื่องรันงาน

```powershell
cd D:\tci-research-atlas\pipeline
uv run atlas quarterly --corpus D:/atlas-data/corpus/2026Q4 --release 2026Q4 --prepare
```

- คำสั่งนี้ตรวจคลัง สร้าง `runs/2026Q4/config.yaml` และหยุด ยังไม่เสียเงิน
- เปิด `runs/2026Q4/profile.md` ต้องไม่มีรายการ "ต้องแก้ก่อนส่ง"
- **ชื่อรอบ** (`--release`) ต้องอยู่ในรูป `YYYYQn` เช่น `2026Q4` และห้ามเปลี่ยนกลางทาง

## 2.4 Embedding ครั้งใหญ่ (ครั้งแรกครั้งเดียว) ต้องขออนุมัติค่าใช้จ่ายก่อน

ใช้เวลาหลายชั่วโมง รอบต่อ ๆ ไปจ่ายเฉพาะบทความใหม่

1. **ดูจำนวนและค่าใช้จ่ายโดยประมาณ** (ไม่เสียเงิน):
   ```powershell
   uv run atlas embed -c ..\runs\2026Q4\config.yaml --dry-run
   ```
   **ส่งตัวเลขที่ได้ (จำนวนเรื่อง, token, จำนวน request) ให้ผู้ดูแลอนุมัติ** รอคำตอบก่อนไปข้อต่อไป
2. **เริ่มรัน** เบื้องหลัง ปิดหน้าต่างได้เลย:
   ```powershell
   uv run atlas embed -c ..\runs\2026Q4\config.yaml --background
   ```
3. **ดูความคืบหน้า** (เปิดดูกี่ครั้งก็ได้):
   ```powershell
   uv run atlas status -c ..\runs\2026Q4\config.yaml
   ```
4. **ถ้าเน็ตหลุด เครื่องดับ หรือหยุดไปกลางคัน** สั่งคำสั่งใน ข้อ 2 ซ้ำ ระบบทำต่อจากจุดเดิมโดยไม่จ่ายซ้ำ ส่วนวิธีหยุดเอง: `uv run atlas embed-stop -c ..\runs\2026Q4\config.yaml`
5. **เสร็จเมื่อ** `atlas status` ขึ้น `done` ถ้าขึ้น `failed` หรือ error ถาวร (key ผิด เครดิตหมด) ให้แจ้งผู้ดูแล

## 2.5 รันทั้งรอบด้วยคำสั่งเดียว

**ถ้าใช้ LLM:** ดูค่าใช้จ่ายก่อน และส่งให้ผู้ดูแลอนุมัติ:
```powershell
uv run atlas llm -c ..\runs\2026Q4\config.yaml --dry-run
```
(คำสั่ง `atlas quarterly` จะแสดงตัวเลขเดียวกันและถามยืนยันก่อนจ่ายอีกชั้นหนึ่ง ตอบ `y` เฉพาะเมื่อผู้ดูแลอนุมัติแล้ว)

**รัน** (ใช้ `--build-web` เพื่อให้เว็บที่ build มีที่อยู่สาธารณะที่ถูกต้อง):
```powershell
cd D:\tci-research-atlas\pipeline
uv run atlas quarterly --corpus D:/atlas-data/corpus/2026Q4 --release 2026Q4 --build-web
```

- ใช้เวลาประมาณ 1–2 ชั่วโมงสำหรับ 500,000 เรื่อง (ไม่รวม embedding) ปล่อยให้รันจนจบ
- **ถ้าหยุดกลางทาง** อ่านข้อความ `STOPPED:` แก้ตามที่บอก แล้วสั่งคำสั่งเดิมซ้ำ ส่วนที่จ่ายเงินไปแล้วไม่ถูกจ่ายซ้ำ
- **เมื่อเสร็จ** ได้:
  - `runs\2026Q4\summary.md`: ตัวเลขสำคัญและเวลาแต่ละขั้น
  - `runs\2026Q4\validate.txt`: ผลตรวจก่อนเผยแพร่
  - `deploy\2026Q4\site\`: เว็บพร้อมอัปโหลด
  - `deploy\atlas-site-2026Q4.zip` และ `deploy\atlas-data-2026Q4.zip`

**ถ้า `validate.txt` มีบรรทัด `ERROR` ที่ขึ้นต้นด้วย `privacy:` ห้ามเผยแพร่เด็ดขาด** แจ้งผู้ดูแลทันทีพร้อมส่งบรรทัดนั้น (หมายถึงมีอีเมล ORCID หรือชื่อคนติดอยู่ในไฟล์ที่จะเผยแพร่)

## 2.6 ตรวจผลบนเครื่อง (ประมาณ 30 นาที)

1. **อ่าน `runs\2026Q4\summary.md` และ `validate.txt`:**
   - `validate` ต้องเป็น OK หรือ WARNINGS ที่อ่านครบแล้ว ห้ามมี ERROR
   - จำนวนบทความต้องใกล้เคียงกับจำนวนใน `profile.md`
   - ดูบรรทัดใน `runs\2026Q4\pipeline.log` ที่ขึ้นต้นด้วย `[ingest]` และ `[cluster]` จด 2 ตัวเลขนี้ไว้รายงาน:
     - จำนวนที่ตัดทิ้งแต่ละเหตุผล (ซ้ำ, ปีผิด, ไม่มีชื่อเรื่อง)
     - "N raw clusters → M topics" และสัดส่วนของหัวข้อที่ใหญ่สุด (ถ้าเหลือหัวข้อน้อยมากเทียบกับจำนวนบทความ ให้แจ้งผู้ดูแล)
2. **เปิดเว็บบนเครื่อง:**
   ```powershell
   cd D:\tci-research-atlas\web
   node scripts/serve.mjs --site ..\deploy\2026Q4\site
   ```
   แล้วเปิด <http://127.0.0.1:4173/>
3. **ตรวจ 10 จุดนี้:**
   - [ ] หน้าแรกขึ้นชื่อรอบ `2026Q4` และ **ไม่มีป้าย "ข้อมูลตัวอย่าง"** ที่หน้าใดเลย
   - [ ] กด "สรุปผู้บริหาร" ตัวเลขแสดงครบ ไม่มีค่าว่างหรือ NaN
   - [ ] "กำลังมา" → แท็บ "กำลังเกิดใหม่" มีรายการ กดเข้าหัวข้อหนึ่งแล้วมีกราฟและตาราง
   - [ ] ชื่อหัวข้ออ่านรู้เรื่อง ไม่ใช่ชุดคำสับสน (ถ้ามี LLM ให้ส่งไฟล์ตรวจชื่อ ดูข้อ 2.7)
   - [ ] "ใครทำเรื่องอะไร" → สถาบัน: มีชื่อมหาวิทยาลัยจริง ไม่มีชื่อคน อีเมล หรือที่อยู่
   - [ ] แผนที่จังหวัดมีตัวเลขครบ และตารางจังหวัดครบ 77 จังหวัด
   - [ ] ค้นหาคำไทยที่ใช้บ่อย (เช่น "ผู้สูงอายุ") ได้ผล และลิงก์ไปบทความที่เปิดได้
   - [ ] สลับภาษาไทย/English ได้
   - [ ] เปิดบนมือถือ (หรือย่อหน้าต่างให้แคบ) แล้วไม่ต้องเลื่อนซ้าย-ขวา
   - [ ] ไม่มีหน้าขาว หน้าที่ไม่มีข้อมูลต้องบอกเหตุผล
4. **ถ้าพบชื่อสถาบันที่ผิดหรือซ้ำ:** เติมแถวใน `institutions_aliases.csv` ของคลัง (alias → สถาบัน) ตาม [corpus/README หัวข้อ 11.2](corpus/README.md) แล้วรัน `atlas quarterly` เดิมอีกครั้ง

## 2.7 ส่งผู้ดูแลอนุมัติก่อนเปิดสาธารณะ (ห้ามข้าม)

เมื่อเปิดสาธารณะแล้วผู้บริหารและประชาชนจะอ้างอิงตัวเลข ส่งข้อมูลต่อไปนี้ให้ผู้ดูแลและรอคำตอบ "อนุมัติ" ก่อนไปขั้น 2.8

- ไฟล์ `summary.md`, `validate.txt`, `profile.md`
- ค่า 2 ตัวจากข้อ 2.6 (จำนวนที่ตัดทิ้ง และ "raw clusters → topics")
- ผลตรวจ 10 จุด (ติ๊กครบหรือไม่ ข้อไหนมีปัญหา)
- ภาพหน้าจอ: หน้าแรก, สรุปผู้บริหาร, หน้าสถาบัน (บนเดสก์ท็อปและมือถือ)
- **ถ้าใช้ LLM:** ไฟล์ตรวจชื่อหัวข้อประมาณ 50 รายการ:
  ```powershell
  uv run atlas review export -c ..\runs\2026Q4\config.yaml
  ```
  ผู้ดูแลหรือบรรณาธิการแก้ชื่อที่ผิดในไฟล์ CSV แล้วนำกลับเข้า:
  ```powershell
  uv run atlas review import <ไฟล์.csv> -c ..\runs\2026Q4\config.yaml
  ```
  จากนั้นสั่ง `atlas quarterly` เดิมอีกครั้งให้ชื่อใหม่ขึ้นเว็บ

## 2.8 เปิดเว็บให้ประชาชน เมื่อได้รับอนุมัติแล้วเท่านั้น

### ทาง A: GitHub Pages

1. **สร้าง GitHub Release ที่แนบไฟล์ข้อมูล:**
   ```powershell
   cd D:\tci-research-atlas
   bash scripts/package_release.sh --upload
   ```
   (รันใน Git Bash ที่ติดมากับ Git for Windows) ได้ Release ชื่อ `data-2026Q4` ที่แนบ `atlas-site-data-2026Q4.zip` ซึ่งมีเฉพาะข้อมูลที่เผยแพร่ได้ (ไม่มีชื่อผู้แต่งและไม่มีบทคัดย่อ) สคริปต์ปฏิเสธข้อมูลตัวอย่างให้เอง
2. **สั่ง deploy:** เปิด <https://github.com/santipongth/tci-research-atlas/actions/workflows/pages.yml> → ปุ่ม **Run workflow** → ช่อง `data_release` ใส่ `data-2026Q4` → **Run workflow** → รอจน ✓ สีเขียว (ประมาณ 3–5 นาที) หรือสั่งจาก terminal:
   ```powershell
   gh workflow run pages.yml --ref main -f data_release=data-2026Q4
   ```
3. **ถ้าไม่มีสิทธิ์ Write:** ส่งไฟล์ `atlas-site-data-2026Q4.zip` (อยู่ที่รากของ repo) ให้ผู้ดูแล ผู้ดูแลจะทำข้อ 1–2 เอง

### ทาง B: เซิร์ฟเวอร์ขององค์กร

1. อัปโหลด **ทุกไฟล์ในโฟลเดอร์** `deploy\2026Q4\site\` ขึ้นรากของเว็บ (หรือแตก `deploy\atlas-site-2026Q4.zip` ที่นั่น) ไม่ต้องมีฐานข้อมูลหรือโปรแกรมฝั่งเซิร์ฟเวอร์ ไฟล์ static ล้วน
2. ตั้ง HTTPS ให้เรียบร้อย
3. ที่อยู่ที่ใช้ต้องตรงกับ `publish.site_url` ที่ตั้งไว้ใน 2.2 (ถ้าเปลี่ยน ให้แก้แล้วรัน `atlas quarterly --build-web` ใหม่ก่อนอัปโหลด)

### ตรวจหลังขึ้นเว็บ (ทั้งสองทาง ทำทันที)

เปิดเว็บสาธารณะในหน้าต่างที่ไม่เคยเปิดมาก่อน (Incognito) แล้วเช็ก:

- [ ] หน้าแรกขึ้นรอบ `2026Q4` **ไม่มีป้าย "ข้อมูลตัวอย่าง"** (ถ้ายังเห็นป้าย ให้ Ctrl+F5 หรือรอ 5 นาทีให้ cache หมด ถ้ายังไม่หาย แจ้งผู้ดูแลทันที)
- [ ] `<ที่อยู่เว็บ>/data/latest.json` เปิดได้ และ `release` เป็น `2026Q4`
- [ ] `<ที่อยู่เว็บ>/robots.txt` และ `<ที่อยู่เว็บ>/sitemap.xml` เปิดได้ และ `robots.txt` ไม่มีบรรทัด `Disallow: /`
- [ ] ดูซอร์สของหน้าแรก (Ctrl+U) ค้นคำว่า `noindex` ต้องไม่เจอ
- [ ] ลองเปิดจากมือถือจริง 1 เครื่อง และลองแชร์ลิงก์ใน LINE ต้องขึ้นรูปปกพร้อมโลโก้ TCI
- [ ] รายงานผู้ดูแลพร้อมลิงก์เว็บ

**ส่วนที่ผู้ดูแลต้องทำเอง** (ใช้บัญชี Google ของผู้ดูแล): ยืนยันเว็บใน Google Search Console และส่ง `sitemap.xml` ตาม [`docs/OPERATIONS.md` §22](OPERATIONS.md)

## 2.9 เก็บงาน

- **สำรองข้อมูล** ไปที่เก็บภายในองค์กร (ไม่ใช่ GitHub):
  - `D:\atlas-data\state\` ทั้งโฟลเดอร์ ถ้าหายต้องจ่ายค่า embedding และ LLM ใหม่ทั้งหมด
  - `runs\2026Q4\`
  - `deploy\atlas-data-2026Q4.zip`
  - คลัง `D:\atlas-data\corpus\2026Q4\`
- **รอบต่อไป (ทุก 3 เดือน)** ทำเฉพาะ: ได้คลังชุดใหม่ → ตรวจด้วย `atlas profile` → `atlas quarterly --corpus … --release <รอบใหม่>` → ตรวจ → ขออนุมัติ → เผยแพร่ โดยไม่ต้องทำ embedding ครั้งใหญ่ซ้ำ (จ่ายเฉพาะบทความใหม่) และรอบใหม่ต้องใช้ชื่อรอบที่ไม่เก่ากว่ารอบก่อน
- **ถ้าต้องถอนเว็บกลับเป็นรอบก่อน:** ทาง A สั่ง Run workflow ใหม่ด้วย `data_release` ของรอบก่อน (เช่น `data-2026Q3`) ทาง B แก้ `data/latest.json` บนเซิร์ฟเวอร์ให้ชี้รอบก่อน

---

# เมื่อเจอปัญหา

| อาการ | ทำอย่างไร |
|---|---|
| `atlas profile` ไม่ผ่าน | อ่านหัวข้อ "ต้องแก้ก่อนส่ง" ท้าย `profile.md` แก้ไฟล์ต้นทาง แล้วตรวจใหม่ |
| `atlas embed --check` ขึ้น error | key, `base_url` หรือ `model` ผิด แจ้งผู้ดูแลและส่งข้อความ error |
| embedding ค้าง หรือเน็ตหลุด | สั่งคำสั่ง embed เดิมซ้ำ ทำต่อจากเดิมและไม่จ่ายซ้ำ |
| `atlas quarterly` ขึ้น `STOPPED: …` | อ่านข้อความ แก้ตามนั้น แล้วสั่งคำสั่งเดิมซ้ำ |
| `validate` มี `ERROR` โดยเฉพาะ `privacy:` | **ห้ามเผยแพร่** แจ้งผู้ดูแลทันที |
| `STOPPED: … embedding provider 'lite'` | ใช้ embedding ทดสอบอยู่ ตรวจ `embedding.provider` ใน config ต้องเป็น `api` (หรือ `local`) |
| เว็บยังขึ้น "ข้อมูลตัวอย่าง" หลังเผยแพร่ | Ctrl+F5 / รอ 5 นาที ถ้ายังไม่หายแจ้งผู้ดูแล |
| รายละเอียดอื่น ๆ | [`docs/OPERATIONS.md` §3 Troubleshooting](OPERATIONS.md) |

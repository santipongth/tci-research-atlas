# OPERATIONS — คู่มือปฏิบัติการรายไตรมาส

> **รอบปกติใช้คำสั่งเดียว:** `atlas quarterly` (หรือดับเบิลคลิก `scripts\quarterly_run.cmd` บน Windows)
> คำสั่งนี้ทำงานตั้งแต่รับคลังบทความไปจนได้โฟลเดอร์เว็บที่อัปโหลดขึ้น host ได้ทันที และเก็บทุกอย่างของรอบไว้ใน `runs/<รอบ>/`
> คนต้องทำเองแค่ 3 จุด: วางคลัง → ตอบ "y" ยืนยันค่า LLM → อ่านสรุปแล้วอัปโหลด
> §1 คือขั้นตอนหลักฉบับเดียวของรอบไตรมาส คู่มือนักศึกษาฝึกงาน ([`INTERN_GUIDE.md`](INTERN_GUIDE.md)) อธิบายขั้นเดียวกันแบบละเอียดทีละขั้น พร้อมจุดขออนุมัติ และวิธีตั้งค่าเซิร์ฟเวอร์ขององค์กร

## 0. เตรียมเครื่อง (ครั้งแรกครั้งเดียว)

1. **ติดตั้งโปรแกรม:**
   - [uv](https://docs.astral.sh/uv/) (จัดการ Python ให้เอง)
   - Node.js 24 (ใช้ build เว็บ)
   - Git
2. **เครื่อง:** RAM ≥ 16 GB และพื้นที่ว่าง ≥ 50 GB สำหรับคลัง 500,000 เรื่อง (store embedding ใช้ราว 2–4 GB)
3. **ติดตั้ง pipeline:**
   ```bash
   cd pipeline
   uv sync --extra api --extra fast --extra leiden   # embedding ผ่าน API (แนะนำ) — หรือ --extra local ถ้ามี GPU; fast = ตัวจัดกลุ่มที่เร็วพอสำหรับ 500K
   cp config.example.yaml config.yaml
   ```
4. **แก้ `pipeline/config.yaml`** เฉพาะค่าเหล่านี้ ค่าอื่นใช้ค่าเริ่มต้นได้:

   | ค่า | ใส่อะไร |
   |---|---|
   | `input.path` | โฟลเดอร์คลังปัจจุบัน เช่น `D:/atlas-data/corpus/current` (ใส่ `--corpus` ตอนรันแทนก็ได้) |
   | `pipeline.state_dir` | โฟลเดอร์ถาวร **ห้ามลบ** เช่น `D:/atlas-data/state` (เก็บ embedding และ cache LLM ที่จ่ายเงินไปแล้ว ควร backup) |
   | `pipeline.work_dir`, `pipeline.output_dir` | โฟลเดอร์ทำงาน เช่น `D:/atlas-data/work` และ `D:/atlas-data/output` |
   | `embedding.provider` + `embedding.api.*` | `api` + ปลายทางและโมเดล (ดู §1A) |
   | `labeling.provider`, `narrative.provider` | `llm` เมื่อต้องการชื่อหัวข้อและคำอธิบายจาก LLM (ดู §6) ไม่ใช้ใส่ `"off"` หรือ `template` |
   | `publish.site_url` | ที่อยู่เว็บจริง เช่น `https://atlas.tci-thailand.org/` (`atlas quarterly` ส่งค่านี้ให้ตอน build เว็บ จึงใช้กับลิงก์ canonical, `sitemap.xml`, `robots.txt`, การ์ดตอนแชร์ และฟีด) |
   | `labeling.overrides_path` | คงค่าจาก `config.example.yaml` (`./registry/label_overrides.csv`) ไว้ ถ้าว่าง `atlas review import` ใช้ไม่ได้ |

   ทุกครั้งที่ `atlas quarterly` รัน ระบบสร้าง `runs/<รอบ>/config.yaml` ใหม่จาก `config.yaml` นี้ ถ้าแก้ `config.yaml` แล้วจะใช้คำสั่งแบบ `-c ../runs/<รอบ>/config.yaml` ต่อ ให้รัน `atlas quarterly … --prepare` ใหม่ก่อน

5. **ตั้ง API key ใน env var เท่านั้น** ห้ามเขียนลงไฟล์ใด ๆ:
   ```powershell
   setx ATLAS_EMBED_API_KEY "..."   # embedding
   setx ATLAS_LLM_API_KEY "..."     # LLM (ใช้ key เดียวกันได้)
   ```
   ตั้งแล้วเปิดหน้าต่างใหม่ เพราะหน้าต่างเดิมยังไม่เห็นค่า
6. **ครั้งแรก:** ทำ embedding ครั้งใหญ่ทั้งคลังตาม §1.2 ก่อน

## 1. รอบรันรายไตรมาส (step-by-step)

### 1.1 รับและวางคลังบทความ

1. **ตรวจไฟล์ที่ได้รับ:** ทีมข้อมูลส่งคลังรูปแบบ 1.0 ตามคู่มือ [`docs/corpus/README.md`](corpus/README.md) คือโฟลเดอร์ `articles/*.jsonl.gz` + `journals.csv` + `README.txt`
   - อาจมีไฟล์เพิ่ม: `institutions_aliases.csv`, `province_population.csv`, `ror.zip`
   - `atlas quarterly` ใช้ไฟล์ประกอบในโฟลเดอร์คลังแทนค่าใน config.yaml ให้เอง
   - รายการสังกัดที่ยังไม่มีใน `institutions_aliases.csv` อยู่ที่ `runs/<รอบ>/aliases_todo.csv` ส่งกลับให้ทีมข้อมูลเติมได้
2. **วางคลังแยกโฟลเดอร์ตามรอบ นอก git** และห้ามแก้คลังของรอบเก่า:
   ```
   D:/atlas-data/corpus/2026Q4/articles/…
   D:/atlas-data/corpus/2026Q4/journals.csv
   ```
3. **ตรวจคุณภาพก่อน:** ใช้เวลาไม่กี่นาที ไม่เสียเงิน
   ```bash
   cd pipeline
   uv run atlas quarterly --corpus D:/atlas-data/corpus/2026Q4 --release 2026Q4 --prepare
   ```
   - คำสั่งนี้สร้าง `runs/2026Q4/config.yaml` จดรายการไฟล์คลัง ตรวจคลัง แล้วหยุด ยังไม่เสียเงิน
   - คำสั่งหยุดพร้อม `STOPPED:` เมื่อบรรทัดที่ผิดเกิน `input.max_error_ratio` (ค่าเริ่ม 1%) หรือไฟล์ประกอบมีปัญหา (เช่น ไม่มี `journals.csv`, `journal_key` ในบทความไม่มีแถวใน `journals.csv`, `province_population.csv` ไม่ครบ 77 จังหวัด) รายการที่ต้องแก้อยู่ในหัวข้อ "ต้องแก้ก่อนส่ง" ของส่วน "Companion files" ใน `profile.md` และท้ายหน้าจอหลังบรรทัด `[profile] fix before the hand-over:`
   - เปิด `runs/2026Q4/profile.md` ดูดังนี้:
     - **บรรทัดที่ผิด** (ส่วน "Files with errors"): ส่งรายการ `ไฟล์:บรรทัด` กลับทีมข้อมูล
     - **ช่วงปีและยอดต่อปี:** เทียบรอบก่อนแล้วต้องสมเหตุสมผล
     - **วารสารที่อัปโหลดย้อนหลังในปีเดียว**
     - **% ความครบ:** โดยเฉพาะ abstract และสังกัด
   - คลังเดิมเป็นไฟล์ `.md` ของ ThaiJO ใช้ต่อได้เลย (ระบบดูรูปแบบจากโฟลเดอร์เอง) หรือแปลงเป็นรูปแบบใหม่ด้วย `uv run atlas corpus convert <โฟลเดอร์ .md> --out <โฟลเดอร์ใหม่>`

### 1.2 Embedding ครั้งใหญ่ (ครั้งแรกครั้งเดียว — หรือเมื่อเปลี่ยนโมเดล)

คลัง 500,000 เรื่องต้องแปลงเป็นเวกเตอร์ครั้งเดียว ใช้เวลาหลายชั่วโมง รอบต่อ ๆ ไปจ่ายเฉพาะบทความใหม่หรือบทความที่ข้อความเปลี่ยน รายละเอียดเต็มอยู่ใน §1A

```bash
cd pipeline
uv run atlas embed -c ../runs/2026Q4/config.yaml --check        # ยิง 1 request: key / URL / โมเดลถูกไหม
uv run atlas embed -c ../runs/2026Q4/config.yaml --dry-run      # จำนวนเรื่อง ตัวอักษร token และ request ที่ต้องจ่าย (ไม่ยิง API)
uv run atlas embed -c ../runs/2026Q4/config.yaml --background   # เริ่มงาน แล้วปิดหน้าต่างได้เลย
uv run atlas status -c ../runs/2026Q4/config.yaml               # ดูความคืบหน้าและเวลาที่เหลือ (เปิดดูได้เรื่อย ๆ)
```

- `runs/2026Q4/config.yaml` ได้มาจาก `--prepare` ในข้อ 1.1 คือ config ของคุณ + คลัง ชื่อรอบ และไฟล์ประกอบของรอบนี้
- `--check` ใช้กับ `embedding.provider: api` เท่านั้น ส่วน `provider: local` ข้าม `--check` ได้ (ใช้ `--dry-run` / `--background` ได้เหมือนกัน) และถ้าไม่ embed ล่วงหน้า ขั้น `run` ของ `atlas quarterly` จะ embed ให้เอง
- **ก่อนเริ่มจริง:** ส่งตัวเลขจาก `--dry-run` (จำนวนที่ต้อง embed, ~token, จำนวน request) ให้ผู้ดูแลอนุมัติค่าใช้จ่าย
- **เน็ตหลุด / server ล่ม / ปิดเครื่อง:** สั่งคำสั่ง `--background` เดิมอีกครั้ง ระบบทำต่อจากจุดเดิมโดยไม่จ่ายซ้ำ
- **หยุดเอง:** `uv run atlas embed-stop -c ../runs/2026Q4/config.yaml`
- เมื่อ `atlas status` ขึ้น `done` ไปข้อ 1.3 ได้เลย

### 1.3 รันรอบ: คำสั่งเดียว

```bash
cd pipeline
uv run atlas quarterly --corpus D:/atlas-data/corpus/2026Q4 --release 2026Q4
```

หรือจาก root ของ repo: `bash scripts/quarterly_run.sh --corpus D:/atlas-data/corpus/2026Q4 --release 2026Q4` (สคริปต์นี้ส่งตัวเลือกทุกตัวต่อให้ `atlas quarterly` ตรง ๆ ไม่ได้รับ path ของ config เป็นอาร์กิวเมนต์แรก — จะใช้ config อื่นให้ใส่ `--config <path แบบเต็ม>`) บน Windows ดับเบิลคลิก `scripts\quarterly_run.cmd` ได้เมื่อตั้ง `input.path` ใน config ไว้แล้ว (หรือพิมพ์ `scripts\quarterly_run.cmd --corpus … --release …`)

**ชื่อรอบเมื่อไม่ใส่ `--release`:** ใช้ไตรมาสของวันนี้ ยกเว้นเมื่อ work_dir มีรอบที่เริ่มแล้วแต่ยังไม่เสร็จ (ยังไม่มี `output/data/<รอบนั้น>/manifest.json` และยังไม่มี `runs/<รอบนั้น>/summary.md`) ระบบจะทำรอบนั้นต่อ พร้อมขึ้น `NOTICE: work_dir holds the unfinished round …` ถ้าตั้งใจเริ่มรอบใหม่ ให้ใส่ `--release <รอบใหม่>` · config: ถ้าไม่ใส่ `--config` ใช้ `pipeline/config.yaml` (ถ้ามี)

คำสั่งนี้ทำทีละขั้นและหยุดทันทีเมื่อมีปัญหา (ขึ้น `[quarterly] STOPPED: …` พร้อมบอกวิธีแก้):

| ขั้น | ทำอะไร | ผลอยู่ที่ |
|---|---|---|
| config | รวม config ของคุณกับคลัง (ดูรูปแบบจากโฟลเดอร์เอง) ชื่อรอบ และไฟล์ประกอบที่วางในโฟลเดอร์คลัง (`journals.csv`, `institutions_aliases.csv`, `province_population.csv`, `ror.zip` — ชนะค่าใน config.yaml) | `runs/<รอบ>/config.yaml` |
| corpus | จดรายชื่อไฟล์ ขนาด และ sha256 ของคลังที่อ่าน (คลัง .md จดแค่จำนวนและขนาด) | `runs/<รอบ>/corpus_manifest.json` |
| profile | ตรวจคุณภาพคลังและไฟล์ประกอบ หยุดถ้าบรรทัดที่ผิดเกิน `input.max_error_ratio` หรือไฟล์ประกอบต้องแก้ (ข้ามเมื่อ `input.format: table`) | `profile.md`, `profile.json`, `aliases_todo.csv`, `profile.log` |
| embed | (เฉพาะ `provider: api`) `atlas embed --dry-run` แล้ว `atlas embed` เฉพาะเรื่องที่ยังไม่มี — **ไม่ถามยืนยัน** จึงต้องขออนุมัติตัวเลขจาก §1.2 ก่อน (`provider: local` embed ในขั้น run) | `embed_dryrun.txt`, `embed.log` |
| llm | (เมื่อ `labeling`, `narrative` หรือ `methods.provider` เป็น `llm`) `atlas llm --dry-run` แล้ว **ถามยืนยันก่อนจ่าย** `[y/N]` ตอบ `y` เพื่อไปต่อ | `llm_dryrun.txt` |
| run | `atlas run` ครบทุกขั้น | `pipeline.log` |
| validate | ตรวจรอบก่อนเผยแพร่: exit 2 = หยุด, exit 1 = มีคำเตือน (ไปต่อ เว้นแต่ใส่ `--strict`) | `validate.txt` |
| web | build เว็บ (`npm ci` เมื่อยังไม่มี `node_modules` + `npm run build` โดยส่ง `publish.site_url` เป็น `ATLAS_SITE_URL`) เมื่อ `web/dist` ยังไม่มี `index.html` หรือ `offline-template.html` หรือเมื่อใส่ `--build-web` | `web_build.log` |
| publish | `atlas publish --site web/dist --allow-warnings` (ไม่ใส่ `--allow-warnings` เมื่อใช้ `--strict`): วางข้อมูลรอบใหม่ + รอบก่อน ๆ + `atlas-offline.html` ลงเว็บ | `publish.log` |
| deploy | คัดลอก `web/dist` ทั้งโฟลเดอร์ไปเป็นชุดพร้อมอัปโหลดและทำ zip 2 ไฟล์ (ปฏิเสธเมื่อรอบล่าสุดเป็นข้อมูลทดสอบ `fixture`/`lite`) | `deploy/<รอบ>/site/`, `deploy/atlas-site-<รอบ>.zip`, `deploy/atlas-data-<รอบ>.zip` |
| summary | ตัวเลขสำคัญ เวลาแต่ละขั้น คำเตือน และวิธีอัปโหลด และคัดลอกไฟล์ชั้นบนสุดของ `output/` มาเก็บ | `runs/<รอบ>/summary.md` |

**ถ้าหยุดกลางทาง:** แก้ตามข้อความที่ขึ้น แล้ว **สั่งคำสั่งเดิมอีกครั้ง** ส่วนที่จ่ายเงินไปแล้ว (embedding, คำตอบ LLM) ไม่ถูกจ่ายซ้ำ

**ตัวเลือกทั้งหมด** (ตรวจได้ด้วย `uv run atlas quarterly --help`):

| ตัวเลือก | ผล |
|---|---|
| `--corpus <โฟลเดอร์>` | คลังของรอบนี้ (ไม่ใส่ = `input.path` ใน config) |
| `--release`, `-r` `YYYYQn` | ชื่อรอบ (ไม่ใส่ = ตามกฎด้านบน) |
| `--config`, `-c` | config ที่ใช้ (ไม่ใส่ = `pipeline/config.yaml`) |
| `--yes`, `-y` | ไม่ถามก่อนจ่ายค่า LLM (ใช้กับงานตั้งเวลา) งบสูงสุดยังคุมด้วย `llm.budget_usd` |
| `--strict` | หยุดเมื่อ validate มีคำเตือนด้วย |
| `--build-web` | build เว็บใหม่แม้มี `web/dist` แล้ว (หลังอัปเดตโค้ดเว็บ หรือเปลี่ยน `publish.site_url`) |
| `--prepare` | หยุดหลังตรวจคลัง |
| `--runs-dir`, `--deploy-dir`, `--site` | ย้ายที่เก็บรอบ (`runs/`), ชุดอัปโหลด (`deploy/`) หรือเว็บที่ build แล้ว (`web/dist`) |

### 1.4 ตรวจผลก่อนเผยแพร่ (10 นาที)

1. **อ่าน `runs/<รอบ>/summary.md` และ `validate.txt`:**
   - จำนวนบทความต้องเพิ่มขึ้นสมเหตุสมผล
   - อ่านคำเตือนให้ครบ
2. **เปิดเว็บในเครื่อง:**
   ```bash
   cd web && node scripts/serve.mjs --site ../deploy/<รอบ>/site
   ```
   แล้วเปิด <http://127.0.0.1:4173/>
3. **ตรวจหน้าเว็บ:**
   - **ภาพรวม (`/overview`):** แถบหัวต้องแสดงชื่อรอบใหม่ ต้อง **ไม่มี** ป้าย "ข้อมูลตัวอย่าง" มีการ์ดตัวเลข 4 ใบ และไม่มีแถบแจ้งปัญหา; กด "พิมพ์ / บันทึก PDF" แล้วภาพก่อนพิมพ์ได้ A4 2 หน้า (หน้านี้เป็นสรุปผู้บริหาร)
   - **หัวข้อวิจัย (`/topics`):** การ์ด "อะไรเปลี่ยนจากรอบก่อน" — หัวข้อใหม่ หัวข้อที่ยุติ และหัวข้อที่เปลี่ยนสถานะต้องอธิบายได้ (ผู้บริหารใช้ส่วนนี้); กดปุ่มสถานะแล้วรายการเปลี่ยนตาม และลองคลิก 1 หัวข้อ หน้าหัวข้อต้องมีกราฟ
   - **หน้าอื่นในเมนูซ้าย:** เปิดได้ทุกหน้า ไม่มีหน้าขาว การ์ดที่ไม่มีข้อมูลต้องหายไปหรือบอกเหตุผล
4. **ตรวจชื่อหัวข้อที่ LLM ตั้ง (ทุกรอบ ประมาณ 50 หัวข้อ):**
   - ส่งออกไฟล์ให้บรรณาธิการแก้: `uv run atlas review export -c ../runs/<รอบ>/config.yaml`
   - นำไฟล์ที่แก้แล้วกลับเข้า: `uv run atlas review import <csv> -c ../runs/<รอบ>/config.yaml`
   - จากนั้นรัน `atlas quarterly` เดิมอีกครั้ง (ชื่อรอบเดิม) เพื่อให้ชื่อใหม่ขึ้นเว็บ — คำตอบ LLM มาจาก cache ไม่จ่ายซ้ำ; หรือทำเฉพาะขั้นที่เกี่ยวตาม §7
5. **ขออนุมัติก่อนขึ้นเว็บ:** ส่ง `summary.md`, `validate.txt` และผลตรวจหน้าเว็บให้ผู้ดูแล และรอคำตอบก่อนข้อ 1.5 ถ้า `validate.txt` มีบรรทัด `ERROR privacy: …` ห้ามเผยแพร่ (§3)

### 1.5 ขึ้นเว็บ (copy แล้วเสร็จ)

เว็บเป็นไฟล์ static ล้วน (ไม่มีฐานข้อมูล ไม่มีโปรแกรมฝั่งเซิร์ฟเวอร์) วางที่โฟลเดอร์ย่อยใดก็ได้ และใช้ URL แบบ `#/…` จึงไม่ต้องตั้ง rewrite บนเซิร์ฟเวอร์ — ตัวอย่างการตั้งค่า Nginx / Apache / IIS (HTTPS, MIME type, การบีบอัด, cache) อยู่ใน [`INTERN_GUIDE.md` ภาคผนวก ก](INTERN_GUIDE.md)

- **ครั้งแรก หรือเมื่อโค้ดเว็บเปลี่ยน:** อัปโหลดทุกไฟล์ใน `deploy/<รอบ>/site/` ขึ้นโฟลเดอร์ของเว็บบน host หรือแตก `atlas-site-<รอบ>.zip` ที่นั่น
  - host อะไรก็ได้ที่ให้ไฟล์ static: IIS, Apache, Nginx, S3 หรือ GitHub Pages
  - `publish.site_url` ต้องตรงกับที่อยู่จริง และเว็บต้อง build ด้วยค่านั้น (`atlas quarterly --build-web` เมื่อค่าเปลี่ยน)
- **รอบถัดไป (โค้ดเว็บเดิม):** ใช้ `atlas-data-<รอบ>.zip`
  - zip มีแค่ `data/` + `atlas-offline.html` (รอบเก่ายังอยู่ใน `data/` เว็บจึงเทียบกับรอบก่อนได้)
- **ลำดับการอัปโหลด** (ผู้อ่านจะไม่เห็นเว็บครึ่ง ๆ กลาง ๆ): `data/<รอบใหม่>/` และโฟลเดอร์รอบอื่นใน `data/` ก่อน → `data/feeds/` → `data/latest.json` กับ `atlas-offline.html` เป็นไฟล์สุดท้าย (เว็บอ่าน `latest.json` ก่อนแล้วจึงไปโหลด `data/<รอบ>/…`); เมื่ออัปโหลดทั้งเว็บ ให้ `assets/` ขึ้นก่อน `index.html`
- **GitHub Pages:** `bash scripts/package_release.sh --upload` แล้วไปที่ Actions → Pages → Run workflow → ใส่ `data_release` (§21)
- **หลังขึ้นเว็บ:** เปิดเว็บจริงในหน้าต่างส่วนตัว (Incognito) หน้าแรกต้องแสดงรอบใหม่และไม่มีป้าย "ข้อมูลตัวอย่าง"; `<เว็บ>/data/latest.json` ต้องมี `"release"` เป็นรอบใหม่ ถ้าไม่ขึ้น ดูหัวข้อ "หน้าเว็บยังเป็นข้อมูลเก่า" ใน §3
- **ย้อนกลับ:** ห้ามแก้ `data/latest.json` บน host เอง — ทำตาม §5

### 1.6 เก็บรอบรัน

- `runs/<รอบ>/` เก็บไว้ครบแล้ว: config ที่ใช้จริง, รายการไฟล์คลัง (sha256), profile, log, validate, summary และไฟล์ชั้นบนสุดของ `output/` (เช่น `manifest.json`)
- **backup ทุกรอบ:**
  - `runs/<รอบ>/`
  - `deploy/atlas-data-<รอบ>.zip`
  - **`state_dir` ทั้งโฟลเดอร์** ซึ่งมี embedding, cache LLM และ ID หัวข้อของทุกรอบ ถ้าหาย ต้องจ่ายใหม่และประวัติหัวข้อขาด
- เก็บคลังของแต่ละรอบไว้อย่างน้อย 2 รอบล่าสุด เผื่อต้องรันซ้ำ

### 1.7 ทำเองทีละคำสั่ง (เมื่อต้องการคุมแต่ละขั้น)

คำสั่งเดียวกับที่ `atlas quarterly` เรียกให้ ใช้ config ของรอบจาก `--prepare` (มีคลัง ชื่อรอบ และไฟล์ประกอบของคลังแล้ว — ถ้าใช้ `config.yaml` ตรง ๆ ต้องตั้ง `input.path`, `pipeline.release`, `journals.registry_path` และ `institutions.aliases_path` / `population_path` / `ror_path` เอง เพราะคำสั่งเดี่ยวไม่หาไฟล์ประกอบในโฟลเดอร์คลังให้):

```bash
cd pipeline
uv run atlas quarterly --corpus <คลัง> --release <รอบ> --prepare   # → ../runs/<รอบ>/config.yaml + profile.md
uv run atlas embed -c ../runs/<รอบ>/config.yaml --dry-run && uv run atlas embed -c ../runs/<รอบ>/config.yaml
uv run atlas llm -c ../runs/<รอบ>/config.yaml --dry-run    # ดูค่าใช้จ่ายก่อนทุกครั้ง
uv run atlas run -c ../runs/<รอบ>/config.yaml
uv run atlas validate -c ../runs/<รอบ>/config.yaml         # 0 = ผ่าน, 1 = มีคำเตือน, 2 = ห้ามเผยแพร่
cd ../web && npm ci && ATLAS_SITE_URL=<publish.site_url> npm run build && cd ../pipeline
uv run atlas publish -c ../runs/<รอบ>/config.yaml --site ../web/dist   # + --allow-warnings เมื่อ validate exit 1 และอ่านคำเตือนแล้ว
```

(ตรวจคลังอย่างเดียวโดยไม่สร้าง config รอบ: `uv run atlas profile <คลัง> --md profile.md --aliases-todo aliases_todo.csv`)

สิ่งที่ควรรู้ตอนทำเอง:

- **ผลลัพธ์ที่ต้องดูตอนจบ:**
  - `output/manifest.json` → `counts.total_articles` และ `ingest_errors` (ควรเป็น 0)
  - `embedding_provider` ต้องเป็น `local` หรือ `api` **ห้ามเผยแพร่ผลจาก `lite`**
  - `n_labels_fallback`, `trimmed_years` / `as_of_year` และ `n_orgs_unverified`
- **รอบข้อมูลผูกกับ work_dir:**
  - ขั้น `cluster` บันทึกชื่อรอบไว้ใน `work/04_topics_meta.json` ขั้นหลังจากนั้นเขียนได้เฉพาะรอบนั้น
  - ถ้าแก้ `pipeline.release` กลางทาง ระบบปฏิเสธ (exit 2) ไม่มีรอบผีหรือการเขียนทับรอบเก่า
  - export รอบเดิมซ้ำได้ไฟล์เหมือนเดิมทุกไบต์
- **รอบก่อนหน้าตามมาด้วย:**
  - publish คัดลอกรอบก่อน ๆ ตามสาย `previous_release` จาก `output/data/` ให้เอง เช่น หลัง `npm run build` ล้าง `dist/data` เว็บจึงเทียบ Δ ได้
  - รอบก่อน ๆ ที่มีบน site แล้วไม่ถูกเขียนทับ ส่วนรอบที่กำลัง publish ถูกแทนที่ทั้งโฟลเดอร์ (publish รอบเดิมซ้ำได้)
  - รอบที่เก่ากว่า `publish.keep_full_releases` (ค่าเริ่ม 1 = เก็บครบเฉพาะรอบใหม่สุด) ถูกตัดเหลือ `manifest.json`, `overview.json`, `topics.json`, `taxonomy.json`, `diff.json` และโฟลเดอร์ `topics/`
- **`latest.json` ชี้รอบใหม่สุดเสมอ:** publish รอบที่เก่ากว่าจะวางโฟลเดอร์ให้ แต่ไม่ย้าย `latest.json` และไม่สร้าง `atlas-offline.html` ใหม่ (ต้องการย้ายจริงใช้ `--set-latest` — §5)
- **`atlas-offline.html`:** ใส่ไฟล์รายละเอียดหัวข้อ → วารสาร → สถาบัน จนถึง `export.offline_max_mb` (60 MB) ไม่มี `search/` และ `galaxy.json` (และ `match.json` ถ้าเปิดสร้างไว้) (§12)
- **ห้ามเปลี่ยนชื่อโฟลเดอร์รอบ:** `atlas validate` เป็น error เมื่อ `manifest.release` ไม่ตรงกับชื่อโฟลเดอร์ ชื่อรอบต้องเป็นรูป YYYYQn
- **`atlas-offline.html`:** เว็บทั้งหน้าในไฟล์เดียว เปิดได้โดยไม่ต่อเน็ต
- **ไฟล์แนบ GitHub Release:** `--tarball` ได้ `output/releases/atlas-data-<รอบ>.tar.gz` + sha256 + release notes และพิมพ์คำสั่ง `gh release create` ให้คนสั่งเอง (ไม่อัปโหลดให้)
- **ฟีด Atom:** ต้องตั้ง `publish.site_url` (§19)
- **workflow `.github/workflows/pages.yml`:** ไม่ใส่ `data_release` = เว็บสาธิตที่ใช้ข้อมูลสังเคราะห์ มีป้าย "ข้อมูลตัวอย่าง" ทุกหน้า และตั้ง noindex (§21)

## 1A. รัน embedding ครั้งใหญ่ผ่าน API (ลงทุนครั้งเดียว)

ใช้ตอน embed คลังทั้งหมด (250K–500K เรื่อง) ครั้งแรกด้วย BGE-M3 (หรือโมเดลอื่น) ผ่าน endpoint แบบ OpenAI-compatible (`POST {base_url}/embeddings`)
เวกเตอร์เก็บถาวรใน `state/embeddings/<store>/` — รอบไตรมาสถัดไปจ่ายเฉพาะบทความใหม่/ที่ข้อความเปลี่ยน

ลำดับที่ใช้จริง: `atlas quarterly --corpus <คลัง> --release <รอบ> --prepare` (ได้ `runs/<รอบ>/config.yaml`) → ทำข้อ 1–7 ด้านล่างด้วย `-c ../runs/<รอบ>/config.yaml` → `atlas quarterly` เดิม (ขั้น embed จะขึ้น `0 to embed`) — ข้อความที่ถูกทำความสะอาดใหม่ (เช่น ย้ายจาก .md มาเป็นรูปแบบ 1.0) นับเป็นข้อความใหม่และถูก embed ใหม่ เพราะ store ใช้ hash ของข้อความเป็น key — `--dry-run` บอกจำนวนที่ต้องจ่ายจริงเสมอ

**1) ตั้ง key — env var เท่านั้น ห้ามใส่ใน config หรือไฟล์ใด ๆ**

```powershell
$env:ATLAS_EMBED_API_KEY = "..."        # PowerShell: เฉพาะหน้าต่างนี้ (รวม --background ที่สั่งจากหน้าต่างนี้)
setx ATLAS_EMBED_API_KEY "..."          # จำถาวร — แล้วเปิดหน้าต่างใหม่ (หน้าต่างเดิมยังไม่เห็นค่า)
```

```bash
export ATLAS_EMBED_API_KEY=...          # bash
```

server ในองค์กรที่ไม่ใช้ key: ไม่ต้องตั้ง (ระบบส่ง request โดยไม่มี `Authorization`; ถ้า server ต้องใช้ key จะตอบ 401 และระบบบอกชื่อ env var ที่ต้องตั้ง)

**2) config** (`config.yaml` — key อื่นใช้ค่าเริ่มต้นได้ ดูคำอธิบายครบใน `config.example.yaml`)

```yaml
embedding:
  provider: api
  api:
    base_url: http://my-server:8080/v1    # self-hosted TEI/vLLM/Infinity/Ollama; DeepInfra: https://api.deepinfra.com/v1/openai
    api_key_env: ATLAS_EMBED_API_KEY      # "ชื่อ" env var — ไม่ใช่ตัว key
    model: BAAI/bge-m3                    # ตรวจชื่อโมเดลกับผู้ให้บริการ (บางเจ้าใช้ bge-m3)
    dimensions: null                      # bge-m3 = 1024 เสมอ — อย่าส่ง dimensions
    store_id: null                        # null → "api|BAAI/bge-m3|None" (ไม่ผูก base_url)
    concurrency: 4                        # request พร้อมกัน (429 บ่อย → ลด หรือตั้ง requests_per_minute)
    max_retries: null                     # null = retry error ชั่วคราวไม่จำกัด
```

**3) ตรวจก่อนรันจริง**

```bash
uv run atlas embed -c config.yaml --check      # ยิง 1 request: model, มิติ, latency — key/URL/โมเดลผิดรู้ทันที (exit 2)
uv run atlas embed -c config.yaml --dry-run    # นับ เอกสาร / cached / ต้อง embed / ตัวอักษร / ~token / จำนวน request — ไม่ยิง API
```

(`--dry-run` และการรันจริงจะ ingest + preprocess ให้ก่อนถ้ายังไม่มี `work/02_docs`)

**4) รัน**

```bash
uv run atlas embed -c config.yaml                 # หน้าต่างนี้: แถบความคืบหน้า + retry / ตัดข้อความ / เหตุการณ์ล่าสุด
uv run atlas embed -c config.yaml --background    # เบื้องหลัง: พิมพ์ PID แล้วปิดหน้าต่างได้เลย; log อยู่ที่ <store>/run.log
```

- server ล่ม / 5xx / 429 / 408 / timeout / เน็ตหลุด / คำตอบผิดรูป → **รอแล้วลองใหม่ไม่จำกัด** (exponential backoff + jitter สูงสุด `backoff_max` = 5 นาที/ครั้ง, เคารพ `Retry-After`) — ไม่ต้องเฝ้า
- key ผิด (401/403), base_url หรือโมเดลผิด (404), request ไม่ถูกต้อง (400/422 อื่น), **เครดิต/โควตาหมด** (402 หรือ 429 ที่บอก `insufficient_quota`/billing — แต่ 429 ที่พูดถึง rate limit ต่อนาที/วัน ยังรอแล้วลองใหม่), base_url ถูก **redirect** (3xx — ไม่ follow เพื่อไม่ส่ง key ไปที่อื่น; ระบบบอก URL ปลายทางให้ตั้งเป็น base_url) → **หยุดทันที** (exit 2) พร้อมบอกวิธีแก้ — ไม่วนเปล่า
- server ตอบผิดรูปแบบ **แบบเดิมซ้ำ 3 ครั้ง** สำหรับ batch เดียว → แบ่ง batch; ถ้าเหลือข้อความเดียวแล้วยังผิด → หยุด (exit 2) พร้อมบอกปัญหา (ไม่วนไม่รู้จบกับคำตอบเสียแบบเดิม)
- ส่ง key ผ่าน `http://` ไปเครื่องที่ไม่ใช่ localhost → ขึ้น WARNING หนึ่งครั้ง (ควรใช้ `https://` เว้นแต่เป็นเครือข่ายภายในที่เชื่อถือได้)
- `--background` เฝ้า process ลูก ~3 วินาที: ถ้าตายทันที (config ผิด, 401 ใน request แรก, มีอีกตัวรันอยู่) จะพิมพ์ exit code + ท้าย `run.log` และจบด้วย exit code นั้น — ไม่ใช่บอกว่า "รันแล้ว"
- server บอกว่าใหญ่เกิน (413 หรือ 400/422 ที่พูดถึง token/length) → แบ่ง batch ครึ่งอัตโนมัติ; ข้อความเดี่ยวยาวเกิน → ตัดครึ่งซ้ำได้ถึง `min_text_chars` (นับใน `truncated`)

**5) ดูสถานะ** (เปิดอีกหน้าต่างได้ระหว่างรัน)

```bash
uv run atlas status -c config.yaml               # = atlas embed-status
```

แสดง: สถานะ (`running` / `backing_off` = รอ server / `hung` = process ยังอยู่แต่ไม่มี heartbeat นานกว่า `lock_stale_seconds` / `stopped` / `interrupted` = process ตายกลางคัน / `done` / `failed`), PID ยังทำงานไหม (ตรวจเวลาเริ่ม process ด้วย จึงไม่สับสนเมื่อ Windows นำ PID เดิมไปใช้ใหม่), ความคืบหน้า, อัตรา, ETA, จำนวน retry/ตัดข้อความ, error ล่าสุด, จำนวนเวกเตอร์ใน store, journal ที่รอ, จำนวนข้อความที่ถูกตัดสะสม (`truncated.parquet`) — ระหว่างรัน ตัวเลขเหล่านี้มาจาก `progress.json` (อัปเดตทุก ~5 วินาที) **status ไม่เปิดไฟล์ store ของงานที่กำลังรัน** จึงสั่งดูถี่แค่ไหนก็ไม่ขวาง checkpoint บน Windows

**6) หยุด**

- หน้าต่างที่รันอยู่: **Ctrl-C ครั้งเดียว** = หยุดส่งงานใหม่ รอ request ที่ค้างให้ตอบ บันทึกทุกอย่าง แล้วออก (exit 130); **กดอีกครั้ง** = ไม่รอ request ที่ค้าง: บันทึกเฉพาะที่ได้ผลแล้วลง store แล้วออกทันที (exit 130 — ข้อความของ request ที่ทิ้งไป จะถูกส่งใหม่รอบหน้า) — บน Windows การกดสองครั้งติดกันเร็วมากอาจนับเป็นครั้งเดียว: ถ้ายังไม่ออก ให้รอสักครู่แล้วกดอีกครั้ง
- **หยุดด้วย Ctrl-C เท่านั้น อย่าใช้ Ctrl-Break**: Ctrl-Break ทำให้ `uv run` จบทันที (หน้าต่างกลับมาที่ prompt) ขณะที่ Python ยังหยุดงานต่ออยู่เบื้องหลัง — ดูสถานะด้วย `atlas status` แล้วรอให้ขึ้น `stopped` ก่อนรันใหม่
- รันเบื้องหลัง: `uv run atlas embed-stop -c config.yaml` (สถานะเป็น `stopped`) — สั่งได้แม้งานยังอยู่ช่วง ingest: จะหยุดทันทีที่ถึงขั้น embed (คำขอหยุดที่เก่ากว่าเวลาเริ่ม process ถูกทิ้งเอง)
- ฉุกเฉิน — ปิดหน้าต่าง / `taskkill /F /PID <pid>` / process crash: เสียได้แค่ request ที่ยังไม่ตอบ (≤ 2 × `concurrency` batch) เพราะทุก batch ที่ได้ผลถูกเขียนลง `journal.bin` ทันที
- **ไฟดับ / เครื่องดับกะทันหัน**: เสียเพิ่มได้อีก**ไม่เกินราว 10 วินาทีล่าสุด**ของผลที่อยู่ใน `journal.bin` (journal fsync ลงดิสก์อย่างช้าทุก 10 วินาที; ส่วนที่เข้า store แล้วถูก fsync ก่อนแทนที่ index เสมอ) — รันคำสั่งเดิมแล้วระบบจ่ายเฉพาะส่วนที่หายนั้นใหม่

**7) ทำต่อ = รันคำสั่งเดิมอีกครั้ง**

```bash
uv run atlas embed -c config.yaml
```

ระบบอ่าน `journal.bin` คืนเข้า store (`[embed] recovered N vectors from journal`) แล้ว embed เฉพาะที่ store ยังไม่มี — ไม่จ่ายซ้ำ. การกันรันซ้อนใช้ OS lock บนไฟล์ `<store>/.lock` ที่ process ถือไว้ตลอดการรัน: process ตาย (ปิดหน้าต่าง/taskkill/crash) → OS ปล่อย lock ทันที รันใหม่ได้เลยไม่ต้องรอ; process ที่ยังอยู่ (แม้ค้าง) **ไม่ถูกแย่ง lock เด็ดขาด** — `run.lock` เป็นแค่ข้อมูลให้ `atlas status` อ่าน
เสร็จแล้วรัน `uv run atlas run -c config.yaml` ตามปกติ — ขั้น embed จะขึ้น `0 to embed` และใช้เวกเตอร์จาก store

**8) ย้าย server / เปลี่ยนโมเดล**

- `store_id` ไม่ผูก `base_url`: ย้ายไป server ที่ให้บริการ **โมเดลเดียวกันด้วยการตั้งค่าเดียวกัน** (ไม่ quantize/ตัดข้อความ/normalize ต่างไป) → แก้แค่ `base_url` ใช้ store เดิมต่อได้
- server ใหม่ให้เวกเตอร์ต่างไป (โมเดล, quantization, มิติ) → ตั้ง `store_id` ใหม่ (เช่น `bge-m3-deepinfra`) = store ใหม่, embed ใหม่ทั้งคลัง — ห้ามผสมเวกเตอร์ต่างที่มาใน store เดียว
- ถ้ามิติไม่ตรง store เดิม ระบบหยุดเอง: `store เดิมเป็นมิติ X แต่ server ตอบ Y — ตั้ง store_id ใหม่`

**exit codes**: 0 เสร็จ · 1 ล้ม (เช่น ตั้ง `max_retries` แล้ว retry หมด; หรือบันทึกลง store ตอนจบไม่ได้ เช่น ดิสก์เต็ม หรือมีโปรแกรมเปิด `index.parquet` ค้าง — ผลอยู่ใน `journal.bin` ครบ รันคำสั่งเดิมอีกครั้ง) · 2 config/error ถาวร (key, URL, redirect, โมเดล, โควตาหมด, มิติไม่ตรง, ระบบไฟล์ล็อกไฟล์ไม่ได้) · 3 มี process อื่นถือ store นี้อยู่ (กำลังรัน หรือ hung) · 130 ถูกหยุด (ทำต่อได้)

## 2. ตั้งเวลารันอัตโนมัติ (ไม่บังคับ — คนยังต้องตรวจผลตาม §1.4 ก่อนอัปโหลด)

ทีมข้อมูลต้องวางคลังของรอบนั้นไว้ที่ `input.path` ก่อนถึงเวลารัน และงานตั้งเวลาต้องใส่ `--yes` เพราะไม่มีคนตอบคำถามยืนยันค่า LLM (งบยังคุมด้วย `llm.budget_usd`) ชื่อรอบ = ไตรมาสของวันที่รัน (ตามกฎใน §1.3)

```cron
# 01:00 วันที่ 1 ของเดือน 1,4,7,10 (สร้างโฟลเดอร์ logs/ ไว้ก่อน)
0 1 1 1,4,7,10 * cd /path/to/tci-research-atlas && bash scripts/quarterly_run.sh --yes >> logs/quarterly.log 2>&1
```

Windows Task Scheduler: **อย่าใช้ `scripts\quarterly_run.cmd`** เพราะท้ายไฟล์มีคำสั่ง `pause` ที่รอคนกดปุ่ม งานจึงค้างไม่จบ ให้ตั้งโปรแกรมเป็น `cmd.exe` อาร์กิวเมนต์ `/c uv run atlas quarterly --yes >> ..\logs\quarterly.log 2>&1` และเริ่มใน (Start in) `<repo>\pipeline` (บัญชีที่รันงานต้องเห็น env var ของ key และหา `uv` เจอใน PATH)

## 3. Troubleshooting

| อาการ | สาเหตุที่พบบ่อย | วิธีแก้ |
|---|---|---|
| `atlas profile` ฟ้องไฟล์อ่านไม่ได้/ฟิลด์ว่างมาก | รูปแบบ .md จาก ThaiJO เปลี่ยน (หรือใช้ `input.format: table` แล้ว mapping คอลัมน์ผิด) | ดูรายงาน profile; ถ้าเป็นตาราง แก้ `input.columns` ใน config.yaml |
| embed ค้าง/ล่มกลางทาง/ปิดหน้าต่าง | API timeout, OOM, process ถูกฆ่า | รันคำสั่งเดิมได้เลย — ทุก batch ที่ได้ผลอยู่ใน `journal.bin` ทันที (เข้า store ทุก `checkpoint_every`) ทำต่อจากจุดเดิมโดยไม่จ่ายซ้ำ; ไฟดับอาจเสียผล ~10 วินาทีล่าสุด (§1A) |
| `atlas embed` exit 2 | key ไม่ได้ตั้ง/ผิด (401/403), `base_url`/`model` ผิด (404), request ไม่ถูกต้อง (400/422), base_url ถูก redirect (3xx), เครดิต/โควตาหมด (402, 429 `insufficient_quota`/billing), server ตอบผิดรูปแบบเดิมซ้ำกับข้อความเดียว, มิติไม่ตรง store เดิม, ข้อความยาวเกินแม้ตัดถึง `min_text_chars`, `base_url` ผิดรูป (port/scheme) | อ่านข้อความ error (บอกวิธีแก้ทั้งไทย/อังกฤษ) → แก้ env var/config (redirect: ตั้ง base_url เป็น URL ปลายทางที่แสดง; โควตา: เติมเงินกับผู้ให้บริการ) → `atlas embed --check` → รันใหม่ |
| `atlas embed` exit 2 `this filesystem does not support file locking` | `state_dir` อยู่บน network share / ระบบไฟล์ที่ล็อกไฟล์ไม่ได้ (กันรันซ้อนไม่ได้) | ย้าย `pipeline.state_dir` ไปไว้บนดิสก์ในเครื่อง |
| `atlas embed` exit 1 `could not save into the store … kept in journal.bin` | ตอนจบบันทึกลง store ไม่ได้: ดิสก์เต็ม/I-O error หรือมีโปรแกรมอื่นเปิด `index.parquet` ค้างนานเกิน 1 นาที | แก้สาเหตุ (เพิ่มพื้นที่ดิสก์, ปิดโปรแกรมนั้น หรือยกเว้น `state/` จาก antivirus/backup) แล้วรันคำสั่งเดิม — journal ถูก replay ไม่จ่ายซ้ำ |
| `atlas embed` exit 3 `กำลังรันอยู่ (PID …)` หรือ `hung` | มี process อื่นถือ OS lock ของ store นี้อยู่ (lock หลุดเองทันทีเมื่อ process ตาย ไม่ต้องรอ) | `atlas status` ดู PID/ความคืบหน้า; ถ้าตั้งใจให้รันตัวเดียวก็รอให้จบ หรือ `atlas embed-stop`; ถ้าเป็น `hung` ดูหัวข้อถัดไป |
| สถานะ `hung` (process ยังอยู่แต่ไม่มี heartbeat นานกว่า `lock_stale_seconds`) | main thread ค้าง เช่น หน้าต่าง console ถูกคลิกค้าง (QuickEdit หยุดการพิมพ์), ดิสก์/แชร์ค้าง, เครื่อง sleep | กด Esc/Enter ในหน้าต่างนั้นถ้าเป็น QuickEdit; ถ้ายังไม่ขยับ `taskkill /F /PID <pid>` แล้วรันคำสั่งเดิม (journal recover ให้) — ระบบไม่แย่ง lock จาก process ที่ยังอยู่เอง |
| `atlas embed` exit 130 | Ctrl-C หรือ `atlas embed-stop` | ปกติ — รันคำสั่งเดิมเพื่อทำต่อ |
| กด Ctrl-Break แล้ว prompt กลับมาทันที แต่ `atlas status` ยังขึ้น running | Ctrl-Break ปิด `uv run` ทันที ขณะที่ Python ยังหยุดงานอยู่เบื้องหลัง | รอจน `atlas status` ขึ้น `stopped`/`interrupted` แล้วค่อยรันใหม่; ครั้งหน้าใช้ Ctrl-C |
| retry ไม่จบ / สถานะ `backing_off` นาน | server ปลายทางล่ม คิวเต็ม หรือติด rate limit | `atlas status` → `last error` (เช่น `HTTP 503`, `URLError: ... refused`) แล้วแก้ที่ server — runner ทำต่อเองเมื่อ server กลับมา; 429 บ่อย → ลด `concurrency` หรือตั้ง `requests_per_minute`; ไม่อยากรอไม่จำกัด → ตั้ง `max_retries` |
| log/status ขึ้น `checkpoint postponed N times — something holds index.parquet` | โปรแกรมอื่น (antivirus, backup, ตัวเปิดไฟล์) เปิด `index.parquet` ค้างไว้นาน | ไม่ต้องทำอะไร — ผลอยู่ใน `journal.bin` และเข้า store เมื่อไฟล์ว่าง (หลังเลื่อน 3 ครั้งติด ระบบจะไม่เขียน shard ซ้ำจนกว่าไฟล์จะว่างจริง); ถ้าเกิดบ่อย ให้ยกเว้นโฟลเดอร์ `state/` จากการสแกน |
| สถานะ `interrupted` | process ตายกลางคัน (ปิดหน้าต่าง/ไฟดับ/taskkill) | รันคำสั่งเดิม — journal ถูก recover อัตโนมัติ |
| topic ออกมาใหญ่เกิน/เล็กเกิน | hdbscan_min_cluster_size ไม่เหมาะ | ปรับ `clustering.fine.hdbscan_min_cluster_size` (หรือ `clustering.n_groups` สำหรับกลุ่มใหญ่) แล้วรัน `uv run atlas run -c config.yaml -s cluster -s label -s series -s emerging -s forecast -s layout -s export` |
| ทุกหัวข้อขึ้น DECLINING | ปีล่าสุดข้อมูลยังไม่ครบ แต่ backfill guard ไม่ตัด (เช่น รันย้อนหลังด้วย `as_of_year` ผิด) | ดู log `[series] … looks incomplete` และ `meta.trimmed_years`; ตรวจ `emerging.as_of_year` (null = ปีของ snapshot ตอน cluster) หรือตั้ง `emerging.min_year_complete` เอง |
| `meta.trimmed_years` มีหลายปี / `last_complete_year` ต่ำกว่าที่คิด | ปีที่กำลังดำเนินอยู่ไม่นับเสมอ, ฉบับลงวันที่ล่วงหน้า, หรือปีล่าสุดยอด < 60% ของ median 3 ปีก่อน (ตัดได้สูงสุด `backfill_max_trim` = 2 ปี) | ปกติ — ดูตาราง "Articles per year" ใน profile; ถ้าข้อมูลครบจริงแล้ว ตั้ง `emerging.min_year_complete` |
| `RuntimeError: N of M files failed to read/parse (ratio … > input.max_error_ratio …)` (หรือ "ไม่มีไฟล์ใด parse ได้") | สัดส่วนไฟล์ที่อ่าน/parse ไม่ได้เกินเพดาน `input.max_error_ratio` (default 0.01) — มักเป็น parser/layout เปลี่ยน ไม่ใช่ไฟล์เสียแค่ไม่กี่ไฟล์; ingest หยุดเพื่อไม่ให้เผยแพร่คลังที่ขาดหายเงียบ ๆ | เปิด `work/01_ingest_errors.parquet` (คอลัมน์ path + error; error 3 ชนิดแรกอยู่ในข้อความ) หรือรัน `atlas profile <โฟลเดอร์>` ดู "Files with errors" (มีบรรทัด ⚠ เมื่อเกินเพดาน) → แก้ไฟล์/parser แล้วรัน `-s ingest` ใหม่; ถ้ายอมรับการสูญเสียนี้จริง ให้ปรับ `input.max_error_ratio` ใน config.yaml โดยตั้งใจ (แล้วบันทึกเหตุผล) |
| `atlas validate`/`publish` ขึ้น `privacy: …` (error) | พบอีเมล/ORCID ในไฟล์ที่จะเผยแพร่ หรือชื่อ-นามสกุลผู้แต่งอยู่ในสตริงชื่อสถาบัน/เจ้าของวารสาร (`atlas/privacy.py`) | **ห้ามเผยแพร่** — ดูไฟล์และสตริงที่ error บอก; ถ้าเป็นชื่อสถาบันที่มีชื่อคนติดมา ให้เติมแถวใน `institutions_aliases.csv` (alias → สถาบันที่ถูก) แล้วรัน `-s institutions -s export` ใหม่; ถ้าตรวจแล้วเป็นชื่อหน่วยงานจริงที่บังเอิญตรงกับชื่อผู้แต่ง ให้ใส่สตริงนั้นใน `validation.privacy_allow` |
| `config.yaml` ไม่ผ่าน: `emerging.definition_version` … `Input should be 4` | config.yaml คัดลอกมาก่อนนิยาม v4 (2026-10-24: เกณฑ์สถาบันนับสถาบันหลังรวมชื่อ) | แก้เป็น `definition_version: 4` และเพิ่ม `breadth.org_unit: institution` ตาม `config.example.yaml` แล้วรันตั้งแต่ขั้น `series` (`-s series -s emerging …` หรือทั้งสาย) — สถานะบางหัวข้ออาจเปลี่ยนจากรอบก่อน (ดู `docs/EMERGING_SPEC.md` "การเปลี่ยนแปลง v4") |
| `RuntimeError: 07_emerging … orgs_unverified` ตอน `-s export` | work_dir สร้างก่อน definition v3 (ตาราง emerging ไม่มี flag `orgs_unverified`) — export ไม่เดาค่าให้ เพราะจะทำให้ความกว้างที่ยังไม่ตรวจดูเหมือนตรวจแล้ว | รัน `uv run atlas run -c config.yaml -s emerging -s forecast -s export` |
| log ขึ้น `[ingest] WARNING: N files could not be read or parsed` | ไฟล์เสีย/ถูกล็อก/สิทธิ์ไม่พอ, โฟลเดอร์ชื่อลงท้าย `.md`, หรือ layout ที่ parser ไม่รองรับ | ดู `work/01_ingest_errors` (path + error) หรือส่วน "Files with errors" ใน profile; แก้/ลบไฟล์แล้วรัน `-s ingest` ใหม่ — ไฟล์ที่มีไบต์เพี้ยนเล็กน้อยไม่ถูกข้าม แต่ได้ flag `decode_replaced` |
| log ขึ้น `[embed] WARNING: embedding.provider is 'lite'` | config ใช้ `lite` (สำหรับ CI) กับคลังจริง | เปลี่ยนเป็น `embedding.provider: local` (หรือ `api`) แล้วรันใหม่ — อย่าเผยแพร่ผลจาก lite |
| `ValueError: HDBSCAN found no clusters in N documents` | `hdbscan_min_cluster_size` ใหญ่เกินคลัง หรือ embedding ผิดปกติ (เช่น lite/โมเดลผิด) | ลด `clustering.fine.hdbscan_min_cluster_size` / `hdbscan_min_samples`; ตรวจ `work/03_meta.json` (model_id) — pipeline จะไม่รวมทุกอย่างเป็นหัวข้อเดียวเงียบ ๆ อีกแล้ว (ยกเว้นคลังจิ๋ว < 2 × min_cluster_size) |
| label เป็นภาษาอังกฤษหมด | โมเดลไม่ถนัดไทย | เปลี่ยนโมเดลใน `llm.tasks.label.model` (เช่น typhoon / gpt-4o / gemini-2.0-flash) แล้ว `atlas llm --check` — cache key (model + prompt) เปลี่ยน เฉพาะ label จะถูกสร้างใหม่ |
| หน้าเว็บยังเป็นข้อมูลเก่า | latest.json ยังชี้รอบเก่า (อัปโหลดไม่ครบ หรือ publish รอบที่เก่ากว่าโดยไม่ใส่ `--set-latest`) หรือเซิร์ฟเวอร์/CDN ตั้ง cache นานให้ `index.html`, `data/` หรือ `atlas-offline.html` | ตรวจ `data/latest.json` บน host; hard-refresh (เว็บขอข้อมูลแบบ no-cache อยู่แล้ว); ให้ทีม IT ตั้ง cache ตาม `INTERN_GUIDE.md` ภาคผนวก ก (cache นานได้เฉพาะ `assets/`) |
| แถบ "ยังไม่มีชุดข้อมูล" / "รุ่นของข้อมูลไม่ตรง" | ไม่มี `data/latest.json` หรือ schema ไม่ใช่ 2.x | รัน `atlas publish --site` ใหม่ / อัปเดตเว็บให้ตรงรุ่น |
| forecast ไม่มีบาง topic | ประวัติ < 6 ปี, ไม่ผ่าน skill gate (ดีกว่า naive ไม่พอ) หรือมีจุด backtest ซื่อสัตย์น้อยกว่า `forecast.min_honest_points` | เป็นเรื่องปกติ (`forecast.min_history_years`, `forecast.min_skill`, `forecast.min_honest_points`); ใน contract v2 (`topics.json`) ประวัติสั้น/LOW_DATA = `forecast: null`, ไม่ผ่าน gate = `forecast.show: false` (ไม่มีเส้น — เว็บขึ้น "แนวโน้มไม่แน่นอน"); `forecast_uncertain` มีเฉพาะไฟล์เก่า `atlas_data.json` (v1.1) · forecast รายหัวข้อ (share × ยอดรวมที่พยากรณ์) **ไม่ได้ปรับให้ผลรวมเท่ายอดรวมของคลัง** — รวมทุกหัวข้อแล้วไม่จำเป็นต้องเท่า `corpus_forecast` |
| หัวข้อเกือบทั้งหมดเป็น LOW_DATA | corpus เล็ก/ช่วงปีสั้น หรือ `min_articles_recent` สูงไป | ตรวจรายงาน profile; ปรับ `emerging.min_articles_recent` เฉพาะเมื่อมีเหตุผล (กระทบนิยาม ต้อง bump `definition_version`) |
| หัวข้อขึ้น WATCH เยอะ | WATCH = โตตามเกณฑ์ EMERGING แต่**ไม่ผ่านเกณฑ์ความกว้าง**: วารสาร < `breadth.min_journals`, สถาบัน < `breadth.min_orgs` (เมื่อข้อมูลสังกัดพอ) หรือบทความจากวารสารที่เพิ่งเข้าระบบ ≥ `breadth.max_new_journal_share` — มักเกิดจากวารสารเข้ามาอัปโหลดย้อนหลังเป็นชุด (journal-entry bias); คำอธิบายหัวข้อ/บทสรุปบอกเหตุผลรายหัวข้อ (เช่น "มาจาก 2 วารสาร", "วารสารที่เพิ่งเข้าระบบ 60%") | ดู profile หัวข้อ "วารสารที่อัปโหลดย้อนหลัง"; WATCH คือสัญญาณเตือน ไม่ใช่ข้อสรุป |
| `atlas llm` exit 130 / ข้อความ budget | งบ `llm.budget_usd` หมด, Ctrl-C หรือ `atlas llm-stop` | ปกติ — เพิ่มงบแล้วรันคำสั่งเดิม ทำต่อจาก cache (§6) |
| `atlas llm` exit 2 | key/model/URL/โควตาผิด | อ่านข้อความ error → แก้ `ATLAS_LLM_API_KEY` / `llm.endpoints` → `atlas llm --check` |
| `atlas llm` exit 3 | มีงาน LLM อื่นรันอยู่ | `atlas status` ดู PID; รอ หรือ `atlas llm-stop` |
| กลุ่มบนแผนที่ไม่ใช่สาขา OpenAlex (`taxonomy.source: agglomerative`, รหัส `G…`) | OpenAlex ล่ม/งบรายวันหมด (429) หรือปิด `taxonomy.source` → ใช้กลุ่ม agglomerative ที่**ตั้งชื่อตามหัวข้อที่ใหญ่ที่สุดของกลุ่ม** พร้อมเหตุผลใน `10_taxonomy_meta.json` | ตั้ง `OPENALEX_API_KEY` หรือรอวันถัดไป แล้ว `atlas run -s taxonomy …` ต่อ (cache คงอยู่; §9) |
| กลุ่มชื่อ "ยังไม่จัดสาขา (กลุ่ม N)" / "Unmapped group N" | `10_taxonomy` **เก่ากว่า** การ cluster ล่าสุด (เช่น รัน `-s cluster` ใหม่แต่ไม่ได้รัน `-s taxonomy`) — หัวข้อที่ taxonomy เดิมไม่รู้จักถูกใส่กลุ่มสำรองชื่อนี้ (ไม่ได้เกิดจาก OpenAlex ล่ม) | รัน `atlas run -c config.yaml -s taxonomy -s label -s layout -s export` |
| `[run] ERROR: work_dir was clustered for X but pipeline.release is Y` (exit 2) | แก้ `pipeline.release` หลังขั้น cluster แล้วรันขั้นหลัง ๆ ต่อ — ข้อมูลใน work_dir เป็นของรอบ X | ตั้ง `pipeline.release: X` (หรือ null) เพื่อรันรอบ X ต่อ หรือรันตั้งแต่ `-s cluster` ใหม่เพื่อทำรอบ Y (ไม่มีอะไรถูกเขียนตอนถูกปฏิเสธ) |
| `atlas run` ปฏิเสธรอบเก่า / ขึ้นว่าไม่มี state หัวข้อรอบก่อน | รันรอบที่เก่ากว่ารอบที่มีอยู่แล้ว หรือ `state/releases/` ของรอบก่อนหายไป | ใช้ชื่อรอบใหม่ที่ไม่เก่ากว่ารอบล่าสุด; กู้ `state/releases/<รอบก่อน>/` จากสำรอง — ID หัวข้อไม่ถูกใช้ซ้ำ ระบบไม่เดาแทน |
| `provider: off` ใน YAML ไม่ทำงานตามคาด | YAML อ่าน `off` เปล่า ๆ เป็น false | ใส่เครื่องหมายคำพูด: `provider: "off"` |
| Windows แสดงภาษาไทยเพี้ยนใน console | console เป็น cp1252 | ทั้ง `uv run atlas …` และ `python -m atlas.pipeline` ตั้ง stdout/stderr เป็น UTF-8 ให้แล้ว (รวมตอน redirect ลงไฟล์) |
| อยากปรับนิยาม emerging | — | แก้ `config.yaml → emerging:` + `docs/EMERGING_SPEC.md` + `tests/test_emerging.py` พร้อมกัน แล้วรัน `uv run atlas run -c config.yaml -s emerging -s forecast -s export` (ฟรี ไม่แตะ API) |

## 4. งบประมาณโดยประมาณต่อรอบ (corpus ~200K เรื่อง — 500K เรื่อง คูณประมาณ 2.5)

| รายการ | API mode | Local mode |
|---|---|---|
| Embedding รอบแรก | ~$10–20 | ฟรี (GPU 2–4 ชม.) |
| Embedding รอบต่อไป | เฉพาะบทความใหม่/ที่ข้อความเปลี่ยน (เวกเตอร์เดิมอยู่ใน `state/embeddings`) | ฟรี |
| LLM (ชื่อ · คู่ซ้ำ · คำอธิบาย · บทสรุป) | ~$1–3 (เฉพาะ topic ที่ยังไม่มีใน cache; คุมด้วย `llm.budget_usd`) | ฟรี (ถ้ารันเอง) |
| **รวม/ไตรมาส** | **~$15–25** | **~0** |

## 5. การย้อนกลับ (rollback)

- เว็บ: deploy commit ก่อนหน้าอีกครั้งผ่าน GitHub Pages (Run workflow โดยเลือก branch/tag ของโค้ดเก่า) หรือวางชุด `deploy/<รอบ>/site/` เวอร์ชันเก่ากลับ
- ข้อมูล: รอบเก่าบนเว็บถูกตัดเหลือเฉพาะไฟล์ที่ใช้เทียบ (`publish.keep_full_releases`) จึง**ห้ามแก้ `data/latest.json` ให้ชี้รอบเก่าเอง** (หน้าวารสาร/สถาบัน/แผนที่บทความของรอบนั้นจะไม่มีไฟล์) ให้วางรอบนั้นกลับเต็มรอบแทน ในเครื่องที่ยังมี `output/data/<รอบก่อน>/` ครบ:

  ```bash
  cd pipeline
  uv run atlas publish -c ../runs/<รอบก่อน>/config.yaml --release <รอบก่อน> --set-latest --site ../deploy/<รอบล่าสุด>/site
  ```

  - publish ตรวจรอบนั้นอีกครั้ง ถ้ามีแต่คำเตือนที่เคยยอมรับแล้วให้เติม `--allow-warnings`
  - ผล: `data/<รอบก่อน>/` กลับมาครบทุกไฟล์, `data/latest.json` และ `atlas-offline.html` ชี้รอบก่อน, ฟีดเขียนใหม่ รอบล่าสุดยังอยู่ใน `data/` (ไม่ถูกตัด)
  - อัปโหลดตามลำดับใน §1.5: `data/<รอบก่อน>/` ก่อน แล้ว `data/latest.json` กับ `atlas-offline.html` ท้ายสุด
  - รอบถัดไปที่ publish ตามปกติ (ใหม่กว่า) จะย้าย `latest.json` กลับมาเอง
- GitHub Pages: Run workflow ด้วย `data_release` ของรอบก่อน (zip ของรอบนั้นมี `latest.json` ชี้รอบนั้นอยู่แล้ว)

## 6. LLM ผ่าน API (ชื่อหัวข้อ · คู่ที่อาจซ้ำ · คำอธิบาย · บทสรุปผู้บริหาร)

ทุกงานใช้ปลายทางแบบ OpenAI-compatible (`POST {base_url}/chat/completions`) เช่น OpenRouter, Typhoon, DeepInfra หรือ vLLM/LiteLLM ขององค์กร — ตั้งใน `config.yaml → llm.endpoints` และเลือกโมเดลต่องานใน `llm.tasks.{label, merge, narrative, brief}` · `narrative.provider` ดีฟอลต์ `template` (ประโยคแม่แบบ ไม่เรียก LLM) — ตั้งเป็น `llm` เมื่อพร้อม

```powershell
$env:ATLAS_LLM_API_KEY = "sk-..."        # หรือ setx ATLAS_LLM_API_KEY "sk-..." แล้วเปิดหน้าต่างใหม่ (bash: export ...)
uv run atlas llm -c config.yaml --check  # 1 คำขอเล็กต่อโมเดล: ตอบได้ไหม, เป็น JSON ไหม, ภาษาไทยครบไหม
uv run atlas llm -c config.yaml --dry-run   # ต่องาน: กี่ call, มีใน cache กี่ตัว, token ขาเข้า, ค่าใช้จ่ายสูงสุด, งบที่ใช้ไปในรอบนี้
uv run atlas llm -c config.yaml          # รัน step label + methods (เมื่อ methods.provider: llm) + narrate แล้วต้อง `atlas run -s export` + publish (atlas run ทั้งสายรวมขั้นเหล่านี้อยู่แล้ว); --background = รันเบื้องหลัง ปิดหน้าต่างได้
uv run atlas status -c config.yaml       # ความคืบหน้า embedding + LLM
uv run atlas llm-stop -c config.yaml     # หยุดหลัง call ที่กำลังทำเสร็จ (exit 130) — รันคำสั่งเดิม = ทำต่อ
```

- **cache = journal**: ทุก call ที่เสร็จถูกบันทึกทันทีใน `state/llm_cache/<task>.jsonl` → ปิดหน้าต่าง/ไฟดับ/รันซ้ำ = จ่ายเฉพาะที่ยังไม่เสร็จ; รอบถัดไปจ่ายเฉพาะหัวข้อที่เนื้อหาเปลี่ยน
- **งบ**: `llm.budget_usd` ต่อรอบข้อมูล รวมทุกงาน (ต้องใส่ `price_per_mtok_in/out` ของปลายทาง) — call ถัดไปอาจเกินงบ = หยุดอย่างสะอาด (exit 130, step นั้นไม่เขียนผลครึ่ง ๆ กลาง ๆ); เพิ่มงบแล้วรันคำสั่งเดิม = ทำต่อจาก cache
- **server ล่ม/429**: ลองใหม่เองไม่จำกัด (backoff + Retry-After; ตั้ง `max_retries` = ครบแล้วหัวข้อนั้นใช้ fallback และถูกถามใหม่รอบหน้า) · **key/model/URL/โควตาผิด**: หยุดทันที exit 2 พร้อมบอกสิ่งที่ต้องแก้ · มีงาน LLM อื่นรันอยู่: exit 3 (ดู `atlas status`; lock เป็น OS lock แบบเดียวกับ embedding — process ตาย = ปล่อยเอง)
- JSON ผิดรูปแบบ → ขอให้แก้ ≤ `llm.max_repairs` (2) ครั้ง → fallback
- **ตรวจคำอธิบาย (grounding)**: ข้อความถูกปฏิเสธและเขียนใหม่ 1 ครั้ง (`llm.max_regenerations`) แล้วใช้ประโยคแม่แบบ เมื่อมี (ก) ตัวเลขหลักที่ไม่อยู่ในข้อมูลของหัวข้อ (ข) คำบอกจำนวนเท่า — ตัวเลข ("5 เท่า", "3 times", "12-fold", "5x") หรือตัวอักษรไทย/อังกฤษ ("สามเท่า", "สิบสองเท่า", "ร้อยเท่า", "five times", "hundredfold", "tripled", "doubled") — ที่ไม่ตรงกับ**อัตราส่วน**ในข้อมูล (ค่า "(x เท่า)" = share_ratio ของหัวข้อ ตรงตัวหรือปัด 1 ตำแหน่ง) เลขความยาวช่วงปีหรือจำนวนบทความใช้อ้างเป็น "เท่า" ไม่ได้ (ค) คำบอกจำนวนเท่าใด ๆ ในหัวข้อที่ไม่มีช่วงฐานเปรียบเทียบ (`no_baseline`) (ง) คำบอกทิศทางผิดในประโยคอัตราโต (เช่น เขียน "ลดลง" ให้หัวข้อที่โต; ในบทสรุปผู้บริหาร ประโยคที่เอ่ยหลายหัวข้อตรวจเมื่อมีตัวเลขอัตรา 1 ตัวเท่านั้น) — จำนวน fallback ทุกงานอยู่ใน `manifest.json → llm` และ `atlas validate` เตือนก่อนเผยแพร่
- prompts อยู่ใน `prompts/topic_label.th.md`, `topic_merge.th.md`, `topic_narrative.th.md`, `executive_brief.th.md`, `topic_methods.th.md`
- **น้ำเสียงของ prompt เปลี่ยนใน commit 9f1f50b (web refresh, 2026-10-23):** `topic_narrative.th`, `executive_brief.th` และ `topic_methods.th` มีบล็อก "ภาษาและน้ำเสียง" (ภาษาง่าย เริ่มด้วยตัวอย่าง ปีแทน "ช่วงฐาน/ช่วงล่าสุด" ชื่อสถานะไทย/อังกฤษ คำต้องห้าม) อยู่ใน "Prompt (master)" → `prompt_version` และ cache key ของ 3 งานนี้เปลี่ยน รอบ `atlas llm` ถัดไปจึง**เขียนคำอธิบายหัวข้อ บทสรุปผู้บริหาร และบันทึกวิธีวิจัย (เมื่อ `methods.provider: llm`) ใหม่ทั้งหมด** (ไม่ได้มาจาก cache เดิม — รัน `atlas llm --dry-run` ดูจำนวน call และค่าใช้จ่ายก่อน และตั้ง `llm.budget_usd` ให้พอ) · `topic_label.th` **ไม่ได้แก้** ชื่อหัวข้อจึงยังมาจาก cache/ชื่อเดิม ไม่เสียค่าตั้งชื่อใหม่ · ประโยคแม่แบบ (fallback และ `narrative.provider: template`) เปลี่ยนถ้อยคำใน commit เดียวกันและตรวจด้วย `narrative.jargon_in` แล้ว; ข้อความจาก LLM ตรวจทั้ง grounding และ `jargon_in` (ไม่ผ่าน = เขียนใหม่ 1 ครั้ง แล้วใช้ประโยคแม่แบบ — ดูจำนวน fallback ใน log) — เปิดหน้าหัวข้อบางหน้าและ `/brief` บนเว็บที่ build ไว้ ดูว่าน้ำเสียงใหม่อ่านง่ายจริงก่อนเผยแพร่
- **ชื่อหัวข้อข้ามไตรมาส**: หัวข้อที่ lineage เป็น `continue` และคำสำคัญผู้เขียน + คำเด่น c-TF-IDF ยังทับซ้อนกับชุดคำตอนตั้งชื่อ ≥ `labeling.reuse_min_jaccard` (Jaccard, ค่าเริ่ม 0.5) ใช้ชื่อเดิมของรอบก่อน (`label_source: reused`, ไม่เรียก LLM — นับใน `manifest.labels.reused`); หัวข้อใหม่/แยก/รวม และหัวข้อที่คำเปลี่ยนมากได้ชื่อใหม่; ชื่อจาก fallback คำสำคัญไม่ถูกเก็บต่อ (ถาม LLM ใหม่) และชื่อที่บรรณาธิการแก้ (overrides) ยังชนะเสมอ — ชื่อของแต่ละรอบเก็บไว้ที่ `state/releases/<release>/labels.parquet`
- **ค่าใช้จ่ายใน manifest**: `manifest.llm[].cost_usd` = ยอดรวมของรอบข้อมูลนั้นทั้งหมด (รวมทุกครั้งที่รัน จาก journal) · `this_run_cost_usd` = เฉพาะการรันครั้งล่าสุด
- ครั้งแรกที่ใช้ P1: label cache ของ P0 (`state/label_cache.parquet`) ไม่ถูกใช้แล้ว → ทุกหัวข้อถูกตั้งชื่อใหม่ 1 ครั้ง แล้วลบไฟล์เก่าได้

## 7. คนตรวจชื่อหัวข้อ (ทุกรอบ ~50 หัวข้อ)

```bash
uv run atlas review export -c config.yaml         # → output/review/<release>_label_review.csv (เปิดใน Excel ได้ทันที)
#   บรรณาธิการกรอก name_th_fixed / name_en_fixed / reviewer / note ในแถวที่ต้องแก้
uv run atlas review import output/review/2026Q4_label_review.csv -c config.yaml   # → labeling.overrides_path
uv run atlas run -c config.yaml -s label -s narrate -s export                      # ใช้ชื่อใหม่ทันที
uv run atlas publish -c config.yaml --site ../web/dist                              # วางรอบที่แก้แล้วลงเว็บ (แทนที่โฟลเดอร์รอบเดิม)
```

(ในรอบไตรมาส ใช้ `-c ../runs/<รอบ>/config.yaml` หรือรัน `atlas quarterly` เดิมซ้ำแทน 2 บรรทัดสุดท้าย — §1.4; `import` ต้องมี `labeling.overrides_path` ใน config)

- ตัวอย่างที่ส่งตรวจ: ชื่อที่ LLM ทำไม่ได้ (ใช้คำสำคัญแทน) + คู่หัวข้อที่อาจซ้ำ มาก่อน แล้วสุ่มที่เหลือแบบทำซ้ำได้ (หัวข้อที่แก้แล้วไม่ถูกสุ่มซ้ำ)
- ไฟล์ overrides ผูกกับ ID ถาวร (T000123) → ชื่อที่แก้ชนะชื่อจาก LLM ทุกไตรมาส; ID ที่ถูกรวม/เลิกใช้ถูกแจ้งเตือนตอน label
- `pipeline/registry/` ไม่เข้า git (เป็นชื่อหัวข้อจากข้อมูลจริง) — สำรองไว้พร้อม `pipeline/state/`
- คู่ที่อาจซ้ำไม่ถูกรวมอัตโนมัติ: ถ้าเห็นด้วยว่าซ้ำ ให้ตั้งชื่อให้ชัดผ่าน overrides หรือรอ refit รายปีโดยลด `clustering.merge_similarity`

## 8. เลือกโมเดล embedding / อัลกอริทึมจัดกลุ่มด้วยตัวเลข (bake-off)

```bash
uv run atlas bakeoff -c config.yaml --kind all --out ../logs/bakeoff.md                 # ใช้ work_dir ปัจจุบัน
uv run atlas bakeoff -c configs/ci.yaml --truth .ci/synth/_truth.csv --out bakeoff.md   # corpus สังเคราะห์ (มีคำตอบ)
```

ใส่ผู้สมัครใน `bakeoff.embedding_candidates` (api ใช้ runner เดียวกับ embed — แยก store ต่อโมเดล จ่ายครั้งเดียว)

คอลัมน์ในรายงาน:
- embedding: `journal_knn_acc` = kNN ทายวารสารของบทความจากเพื่อนบ้านที่กันไว้ · `subfield_knn_acc` = kNN ทาย subfield OpenAlex บนงานอ้างอิงไทย (ว่างถ้าไม่มี reference) · `truth_purity` = สัดส่วนเพื่อนบ้านที่เป็นหัวข้อจริงเดียวกัน (เฉพาะ synthetic ที่มี `--truth`)
- clustering: `ari_stability` = ARI เฉลี่ยระหว่าง seed (1 = เหมือนกันทุกครั้ง; เกณฑ์ ≥ 0.8) · `ari_vs_first` = สองอัลกอริทึมเห็นตรงกันแค่ไหน · `npmi` = coherence ของคำเด่นของแต่ละหัวข้อ · `purity` = ความบริสุทธิ์เทียบเฉลย (synthetic เท่านั้น)

บรรทัด "best" ในรายงาน (embedding: จัดอันดับด้วยค่าเฉลี่ยของ `journal_knn_acc`, `subfield_knn_acc` และ `truth_purity` เท่าที่มีในรอบนั้น) เป็นจุดเริ่มต้น **ไม่ใช่คำตัดสิน** (advisory) — ผู้ปฏิบัติงานเป็นคนเลือก (เลือก embedding ด้วย journal/subfield accuracy; เลือกอัลกอริทึมที่ ARI stability ≥ 0.8 แล้วดู purity/NPMI) และการเปลี่ยนโมเดล embedding = store ใหม่ + embed ใหม่ทั้งคลัง (ค่าใช้จ่ายรอบแรกอีกครั้ง) รวมถึง fit หัวข้อใหม่ทั้งก้อน

## 9. OpenAlex สำหรับกลุ่มบนแผนที่ (taxonomy)

- key เป็น **ทางเลือก**: `OPENALEX_API_KEY` (ส่งเป็น `Authorization: Bearer` เท่านั้น ไม่อยู่ใน cache/log/ข้อความ error) — ไม่ตั้ง = โหมด keyless
- keyless: งบ ~$0.10/วัน, 10 req/s (เราจำกัดที่ 8 = `requests_per_second_keyless`) · มี key: ~$1/วัน, 30 req/s (เราจำกัดที่ 25 = `requests_per_second_keyed`) และดึงได้หลายหน้า (`max_pages_keyed`)
- งบรายวันหมด (HTTP 429) = หยุดอย่างสะอาด เก็บที่ดึงได้แล้วไว้ใน `state/openalex/` และ taxonomy ถอยไปใช้กลุ่ม agglomerative พร้อมบันทึกเหตุผล (แต่ละกลุ่มตั้งชื่อตามหัวข้อที่ใหญ่ที่สุดของกลุ่ม; ชื่อ "ยังไม่จัดสาขา (กลุ่ม N)" เกิดเฉพาะเมื่อ `10_taxonomy` เก่ากว่าการ cluster) — ตั้ง key หรือรอวันถัดไปแล้วรัน `-s taxonomy` ซ้ำ ทำต่อจาก cache (ใช้ร่วมกันทั้งสองโหมด)

## 10. ทะเบียนวารสาร (ไม่บังคับ)

รายชื่อวารสารอย่างเป็นทางการของ TCI ยังไม่มี → ชื่อวารสารมาจากคลังบทความ (`<server>:<OJS path>`, เช่น `so02:BECJournal`) ถ้าอยากให้ชื่อเต็ม ISSN กลุ่ม TCI และสถาบันเจ้าของ ให้ทำไฟล์ทะเบียนเอง (ไม่ scrape หน้าวารสาร):

```bash
cp pipeline/registry/journals.example.csv pipeline/registry/journals.csv   # แล้วแก้ใน Excel/ตัวแก้ไข UTF-8
```

- คอลัมน์: `journal_key, name_th, name_en, issn, eissn, tci_tier, tci_field, publisher_org, url` — ต้องมี `journal_key`; คอลัมน์อื่นว่างได้
- การจับคู่: ใช้ key เต็ม (`so02:BECJournal`) หรือ OJS path เปล่า (`BECJournal`) เมื่อมีวารสารเดียวในคลังที่ path นั้น; แถวที่ไม่มีในคลังเป็นแค่คำเตือน
- **หยุดรัน (`RegistryError` บอกเลขแถว):** UTF-8 อ่านไม่ได้, CSV ผิดรูป, header ไม่มี `journal_key`, คอลัมน์ที่ไม่รู้จัก, `journal_key` ซ้ำ, `tci_tier` นอก 1–3, สองแถวชี้วารสารเดียวกัน
- `publisher_org` = เจ้าของที่ TCI ให้ (source `registry`); ถ้าไม่ให้ ระบบ **อนุมาน** จากสถาบันที่เซ็นชื่อมากสุด (≥ `journals.owner_min_share`) และเว็บติดป้าย "อนุมาน / inferred" เสมอ
- `registry/journals.csv` ถูก git-ignore — เก็บสำรองพร้อม `state/`
- เมื่อไม่มีทะเบียน เว็บแสดงชื่อ OJS และข้อความ "ยังไม่มีชื่อเต็มในทะเบียนวารสาร"; `journals.inhouse_flag_share` ดีฟอลต์ null (ไม่มีเครื่องหมาย "สูงกว่าเกณฑ์") จนกว่า TCI ยืนยันเกณฑ์

## 11. บันทึกวิธีวิจัยด้วย LLM (ไม่บังคับ)

ดีฟอลต์ `methods.provider: "off"` — การ์ดวิธีวิจัยใน `/journals` และหน้าวารสารใช้ตัวเลขจาก lexicon เท่านั้น (เว็บรุ่น dashboard ยังไม่แสดงบันทึกรายหัวข้อ แม้ `methods.json` จะมี) ถ้าต้องการบันทึกสั้น ๆ ต่อหัวข้อ (≤ 50 หัวข้อใหญ่สุด, ระดับหัวข้อเท่านั้น, ตรวจตัวเลขด้วย grounding, ล้มเหลว = ใช้แม่แบบ):

```bash
# config.yaml: methods.provider: llm  +  llm.tasks.methods.model: <โมเดล>
uv run atlas llm -c config.yaml --dry-run --task methods   # ประมาณ call/token/ค่าใช้จ่าย ไม่เรียก API
uv run atlas llm -c config.yaml                            # รันจริง (cache + งบ + หยุด/ทำต่อ เหมือนงาน LLM อื่น)
```

prompt อยู่ที่ `prompts/topic_methods.th.md` ไฟล์เดียว

## 12. HTML เดี่ยว (`atlas-offline.html`) ไม่มีแผนที่บทความทุกเรื่อง (`/galaxy`)

ไฟล์ใหญ่ไม่ใส่ในไฟล์ออฟไลน์ (`export.offline_exclude: [match.json, search, galaxy.json]` — ชื่อโฟลเดอร์ `search` = ทุกไฟล์ใต้ `search/`): แถวบทความใน `search/` และจุดของกาแล็กซี (ขนาดตามคลัง ดู §17) และ `match.json` (≤ 5 MB — ตั้งแต่ 2026-10-24 ไม่ถูกสร้างโดยค่าเริ่มต้นอยู่แล้ว เพราะ `match.enabled: false`) — หน้า `/galaxy` ในไฟล์นั้นแสดง "ฉบับออฟไลน์ไม่มีส่วนนี้ ต้องใช้เว็บไซต์ออนไลน์" หน้าอื่นทำงานครบ ถ้าอยากใส่ในไฟล์ออฟไลน์ให้เอาออกจากรายการ (ไฟล์จะใหญ่ขึ้นมาก) · ฉบับออฟไลน์ไม่มีฟีด (ฟีดอยู่บนเว็บเท่านั้น) และกราฟฝัง (`/embed/*`) ต้องใช้จากเว็บออนไลน์

## 13. ทะเบียนชื่อสถาบัน (ไม่บังคับ แต่แนะนำ)

ชื่อสถาบันมาจากสังกัดในบทความ ซึ่งสะกดหลายแบบ — ตารางที่ผู้ดูแลคัดเองรวมชื่อให้เป็นสถาบันเดียว (วิทยาเขต ชื่อย่อ ชื่อภาษาอังกฤษ):

```bash
cp pipeline/registry/institutions_aliases.example.csv pipeline/registry/institutions_aliases.csv   # แก้ด้วยตัวแก้ไข UTF-8
```

- คอลัมน์: `alias, inst_id, name_th, name_en, type, province, country, ror` — ต้องมี `alias` และ `inst_id` (ตัวพิมพ์เล็ก ตัวเลข ขีด เช่น `crru`; ห้ามขึ้นต้น `ror-`); หลายแถวที่ `inst_id` เดียวกันรวมเป็นสถาบันเดียว; `type` ∈ university · rajabhat · rajamangala · hospital · government · research · company · other; `province` เป็นรหัส ISO เช่น `TH-57`; `country` รหัส 2 ตัวอักษร
- การจับคู่: ตัดวรรณยุกต์ ช่องว่าง เครื่องหมาย และตัวพิมพ์ก่อน แล้ว alias ต้องเท่ากับชื่อองค์กรหรือปรากฏในสังกัด — เลือกที่ซ้ายสุดแล้วยาวสุด; alias ที่สั้นกว่า `institutions.alias_min_chars` (4) ถูกปฏิเสธ จึงต้องเขียนวิทยาเขตราชภัฏ/ราชมงคลและชื่อย่อ ("มรภ.เชียงราย", "มทร.ล้านนา") เป็นแถวของตัวเอง
- **หยุดรัน (พร้อมเลขแถว):** UTF-8 อ่านไม่ได้, คอลัมน์ที่ไม่รู้จัก, ไม่มี `alias`/`inst_id`, `inst_id` ผิดรูป, alias สั้นเกินไป, alias เดียวชี้สองสถาบัน, `type`/`province`/`country` ไม่อยู่ในชุดที่รู้จัก, ค่าขัดแย้งกันระหว่างแถวของ `inst_id` เดียวกัน
- ลำดับตัดสินสถาบัน: ตารางชื่อ → สังกัดที่ระบุประเทศต่างประเทศ → ROR → ชื่อตามที่เขียนในบทความ; id ที่เผยแพร่คงที่ข้ามรอบ (`inst_id` / `ror-<id>` / `o` + 10 hex)
- ไฟล์นี้ถูก git-ignore — เก็บสำรองพร้อม `state/`

### ROR (ไม่บังคับ)

ดาวน์โหลด ROR data dump ล่าสุดจาก Zenodo (สัญญาอนุญาต CC0) ไว้ในเครื่อง แล้วตั้ง `institutions.ror_path` เป็นไฟล์ .json หรือ .zip นั้น — รอบแรกสร้างแคชเฉพาะประเทศที่ `state/ror/<dump>.<country>.json` ครั้งเดียว; ROR จับคู่ด้วยชื่อเต็ม/ชื่อแสดง/ชื่ออื่น ไม่ใช้ตัวย่อ (กำกวม) ไม่ตั้ง = ข้ามขั้น ROR

## 14. ประชากรรายจังหวัด (ไม่บังคับ)

`pipeline/registry/province_population.csv` (`code,population,year` — เช่น สถิติทะเบียนราษฎรของกรมการปกครอง) ทำให้หน้า `/places` และหน้าจังหวัด (`/province/<รหัส>`) มีตัวชี้วัด "บทความต่อประชากรแสนคน" จังหวัดที่ไม่มีในตารางแสดง "–" ไม่ตั้ง = หน้าแสดงเฉพาะจำนวนบทความ

## 15. ไทยเทียบโลก (OpenAlex)

ขั้น `benchmark` เรียก OpenAlex 16 ครั้งต่อรอบ (4 domain × ช่วงล่าสุด/ฐาน × โลก/ไทย) ผ่านตัวดึงเดียวกับ taxonomy (แคชใน `state/openalex`) — ใช้ได้โดยไม่มี key; `OPENALEX_API_KEY` เพิ่มโควตา. ถ้าปิด (`benchmark.enabled: false`), รันแบบ offline (`ATLAS_OFFLINE=1`), แผนที่ไม่ผูกกับ subfield ของ OpenAlex หรือ API ผิดพลาด → ไม่มี `global.json` และ `manifest.skipped_modules.global` บอกเหตุผล (หน้า `/goals` แสดงเหตุผลนั้นแทนการ์ดไทยเทียบโลก) ขั้นอื่นไม่ล้ม

## 16. SDG และกรอบไทย

เป้าหมายและคำสำคัญอยู่ที่ `pipeline/atlas/data/frameworks.yaml` (SDG 17 · BCG 3 · แผนด้าน ววน. 2566–2570 4 แพลตฟอร์ม · หมุดหมายแผนฯ 13 13 ข้อ) — แก้คำสำคัญได้ หรือชี้ `sdg.frameworks_path` ไปไฟล์ของผู้ดูแล; `sdg.method` = `lexical` (ค่าเริ่ม — นับคำสำคัญ) | `embedding` | `auto` (embedding เมื่อใช้ provider api/local และมี centroid). **ก่อนเปิด embedding:** รันจริงครั้งแรกด้วย `embedding` ในโฟลเดอร์ทดลอง ดูการกระจายคะแนนใน `work/16_topic_goals` แล้วตั้ง `sdg.min_similarity` ให้เหมาะกับโมเดล (0.45 เป็นค่าตั้งต้นที่ยังไม่ได้ปรับกับข้อมูลจริง — ตั้งต่ำไปจะดูเหมือนครอบคลุมเป้าหมายเกินจริง). หลังแก้: `uv run atlas run -c config.yaml -s sdg -s export`. ผลเป็นการจัดกลุ่มโดยเครื่องเพื่อดูภาพรวม ไม่ใช่การจัดประเภทอย่างเป็นทางการ (เว็บบอกไว้ในหน้า)

**ตัวช่วยตั้งเกณฑ์ (P4):** เมื่อ `sdg.method` เป็น embedding ขั้น `sdg` เขียน cosine ทุกคู่หัวข้อ × เป้าหมายลง `work/16_topic_goal_scores` แล้ว

```bash
uv run atlas sdg-scores -c config.yaml     # อ่านอย่างเดียว ไม่เผยแพร่อะไร
```

พิมพ์ควอนไทล์ของคะแนน (q00…q100) และตารางเกณฑ์ 0.30…0.60 (ทีละ 0.05): `links` = คู่หัวข้อ–เป้าหมายที่คะแนนถึงเกณฑ์, `kept` = หลังจำกัด `max_goals_per_topic` ต่อกรอบ (= ที่ `sdg.json` จะแสดง), จำนวนหัวข้อและเป้าหมายที่ถูกครอบคลุม — เลือกเกณฑ์ที่ไม่ทำให้เกือบทุกหัวข้อผูกกับเป้าหมาย แล้วตั้ง `sdg.min_similarity` และรัน `-s sdg -s export`; ถ้าใช้ lexical จะได้ข้อความ `embedding scores not computed (method lexical)`

**เพิ่มในรายการตรวจรายไตรมาส:** ตรวจรายชื่อสถาบันใน `/places` (กด "แสดงเพิ่ม") หาชื่อที่ควรรวม (สะกดต่างกันแยกเป็นหลายแถว) แล้วเพิ่มในทะเบียนชื่อสถาบัน; ดูแผนที่จังหวัดใน `/places` ว่า coverage ของจังหวัดสมเหตุสมผล; เปิด `/goals` ว่าการ์ดไทยเทียบโลกและหัวข้อที่พึ่งสถาบันหรือวารสารเดียวมีข้อมูลหรือบอกเหตุผลที่ข้าม

## 17. แถวบทความ (`search`) และกาแล็กซี

ขั้น `search` (หลัง `references`) เขียนแถวบทความแบบสถิต (id, ชื่อเรื่อง TH/EN, ปี, วารสาร, หัวข้อ, DOI, ลิงก์ — ไม่มีบทคัดย่อ ไม่มีชื่อผู้แต่ง) → `search/meta.json`, `search/docs-<NNN>.json` (ไฟล์ละ `search.docs_per_shard` = 2,000 บทความ) และ `galaxy.json` (สเปกใน `docs/DATA_SPEC.md` §9) ที่หน้า `/galaxy` ใช้

- **ดัชนีคำปิดโดยค่าเริ่มต้น** (`search.word_index: false` ตั้งแต่ 2026-10-24 เพราะเว็บไม่มีกล่องค้นหาแล้ว): ไม่มี `search/vocab.json` และ `search/idx-<NNN>.json`; `search/meta.json` บอก 0 คำ และ 0 index shard ตั้ง `true` = สร้างดัชนีจาก **ชื่อเรื่อง TH/EN + คำสำคัญของผู้แต่ง** เหมือนเดิม (`search.index_shards` ไฟล์ ค่าเริ่ม 64) contract ไม่เปลี่ยน แต่เว็บรุ่นนี้ไม่มีหน้าที่อ่านไฟล์เหล่านี้
- log ของขั้นนี้บอกขนาด: `[search] N article rows (search.word_index is false — no word index) in Xs, D doc shards of ≤ 2,000; galaxy: G placed` — ดูทุกรอบว่าจำนวนบทความสมเหตุสมผล (เฉพาะบทความในช่วงที่วิเคราะห์ที่มีชื่อเรื่อง จึงน้อยกว่า `kpis.articles` ได้) · เมื่อเปิดดัชนีคำ log เป็น `[search] N articles, T tokens, P postings … 64 index shards (a–b tokens each) …` ให้ดูด้วยว่า token แต่ละ shard ไม่เอียงมาก
- `galaxy.json` ≈ 20 ไบต์ต่อบทความก่อน gzip (ประมาณการ: 250K บทความ ≈ 5 MB) โหลดเมื่อเปิด `/galaxy` เท่านั้น พร้อม doc shard ของจุดที่ผู้อ่านเลือก
- ปรับขนาด: doc shard ใหญ่ไป → ลด `docs_per_shard` (ไฟล์มากขึ้นแต่เล็กลง); เมื่อเปิดดัชนีคำแล้ว `vocab.json` ใหญ่เกิน → เพิ่ม `search.min_df` (เช่น 2 = ตัดคำที่พบบทความเดียว) — ไม่กระทบนิยามใด ๆ รัน `-s search -s export` ใหม่ได้
- **การตัดคำ** (`atlas.search_index`) ยังตรึงด้วย `tests/fixtures/search_parity.json` ฝั่ง pytest — ถ้าแก้ normalisation/stopword/กฎ token ต้องรัน `uv run python scripts/make_search_parity.py` (ใน `pipeline/`) และเพิ่ม `TOKENIZER_VERSION`
- ปิด: `search.enabled: false` (หน้า `/galaxy` บอกเหตุผล); ปิดเฉพาะกาแล็กซี: `layout.galaxy: false` → `skipped_modules.galaxy = "layout.galaxy is false"`

### ปรับขนาดจุดของกาแล็กซีกับข้อมูลจริง (ทำในรอบจริงรอบแรก)

ขนาดและความทึบของจุดคำนวณจากจำนวนจุด (`pointSize` / `pointAlpha` ใน `web/src/lib/galaxyGl.ts`) — ค่าตั้งต้นทดสอบกับข้อมูลสังเคราะห์ ~600 จุดเท่านั้น รอบจริงรอบแรกให้เปิด `/galaxy` บนจอปกติและมือถือ: จุดทับกันจนเป็นก้อนสีเดียว → ลดขนาด/ความทึบ; กลุ่มเล็กมองไม่เห็นตอนซูมออก → เพิ่มขนาดขั้นต่ำ — เป็นการแก้โค้ดเว็บ (build ใหม่ครั้งเดียว) ไม่ใช่ข้อมูล

## 18. การอ้างอิง (`references`): เกณฑ์ที่ต้องผ่านก่อนเผยแพร่

ขั้น `references` นับรายการอ้างอิงจาก `01_references` (ไม่นับการอ้างตัวเองและฉบับแปลซ้ำ) แล้วคำนวณแนวปฏิบัติการอ้างอิงรายวารสาร (D7) และ "ถูกอ้างใน TCI" (R12 — จับคู่รายการอ้างอิงกับบทความในคลังด้วย DOI ก่อน แล้วชื่อเรื่องตรงตัวหลัง normalise) มีประตูสองชั้น:

1. **coverage** = สัดส่วนบทความในช่วงที่วิเคราะห์ที่มีรายการอ้างอิงที่นับได้ ≥ 1 รายการ — ต่ำกว่า `references.min_coverage` (0.5) → ไม่มี `references.json` และ `manifest.skipped_modules.references` เป็นข้อความเช่น `reference coverage 12.3% of 4,210 articles 2015–2025 (< references.min_coverage 50.0%)` การ์ด "บทความที่ถูกอ้างใน TCI มากที่สุด" ของ `/journals` ไม่แสดง และหน้าหัวข้อซ่อน "ถูกอ้างใน TCI"
2. **จับคู่ภายในคลัง** ได้น้อยกว่า `references.min_internal_matches` (20) → `references.json` ยังมีส่วนรายวารสาร แต่ `internal: null` + `internal_reason` (เช่น `12 references matched a corpus article (< references.min_internal_matches 20)`); `cited_in_tci` ของหัวข้อเป็น null

เหตุผลที่ข้ามแปลว่า **คลังรอบนี้มีรายการอ้างอิงที่ parse ได้น้อยเกินจะสรุป** (มักเพราะไฟล์ ThaiJO ไม่มีส่วนอ้างอิง หรือรูปแบบที่ parser อ่านไม่ได้) ไม่ใช่ pipeline ล้ม — ดูบรรทัด `[references]` ใน log และ `work/19_refs_meta.json` (coverage, จำนวนที่จับคู่ด้วย DOI/ชื่อเรื่อง); อย่าลดเกณฑ์เพียงเพื่อให้หน้าแสดงผล เพราะตัวเลขจากคลังที่ครอบคลุมต่ำทำให้วารสารที่ข้อมูลไม่ครบดูเหมือนอ้างอิงน้อย — ถ้าจะลดต้องตัดสินใจกับเจ้าของข้อมูลและบันทึกเหตุผล ไฟล์ที่เผยแพร่ไม่มีข้อความรายการอ้างอิงหรือชื่อผู้แต่ง (`top_articles` มีแค่ชื่อเรื่อง วารสาร ปี ลิงก์ จำนวน)

## 19. ฟีด Atom (`publish.site_url`)

```yaml
publish:
  site_url: https://<user>.github.io/<repo>/   # ที่อยู่สาธารณะของเว็บ (ลิงก์ในฟีดเป็น absolute)
  feed_max_entries: 12                         # รอบสูงสุดต่อฟีด ใหม่สุดก่อน
```

- `atlas publish --site <dir>` เขียน `data/feeds/releases.xml` (หนึ่ง entry ต่อรอบบนเว็บ: headline + จำนวนหัวข้อใหม่/หายไป/เปลี่ยนสถานะจาก `diff.json`, ลิงก์หน้าหัวข้อวิจัย `#/topics`) และ `data/feeds/topics/<รหัสหัวข้อ>.xml` ทุกหัวข้อของรอบใหม่สุด (สถานะ บทความช่วงล่าสุด อัตราโต ต่อรอบ; ลิงก์ `#/topics/<รหัส>`); ฟีดของหัวข้อที่ไม่อยู่ในรอบใหม่สุดถูกลบ
- สร้างจากไฟล์ที่อยู่บนเว็บเท่านั้น → publish ซ้ำได้ไบต์เดิม; publish รอบที่เก่ากว่า (ไม่ย้าย latest) ยังอัปเดตฟีดและตั้ง `feeds: true` ใน latest ที่มีอยู่
- เว็บแสดงลิงก์ฟีด (แถบหัวของ `/topics` และหน้าหัวข้อ) เฉพาะเมื่อ `latest.json.feeds` เป็น true; HTML ออฟไลน์ไม่มีฟีด
- เว็บสาธิต (Pages + ข้อมูลสังเคราะห์) ไม่ต้องตั้ง — fixture ตั้ง `feeds: false`

## 20. แนวโน้มคำสำคัญ (`kwtrends`) และกราฟฝัง

- ขั้น `kwtrends` นับคำสำคัญของผู้แต่ง (ไทย/อังกฤษแยกกัน) ต่อปีของอนุกรมเวลา เก็บ `kwtrends.max_keywords` (3,000) คำที่พบ ≥ `kwtrends.min_count` (5) บทความ และจับคู่คำไทย↔อังกฤษตามตำแหน่งเมื่อรายการยาวเท่ากัน (อภิธานศัพท์ต่อหัวข้อและทั้งคลัง) — อภิธานศัพท์ต่อหัวข้อแสดงในหน้าหัวข้อ (หน้า `/keywords` ถูกตัดใน dashboard redesign ส่วน `kwtrends.json` ยังถูกสร้าง แต่ไม่มีหน้าใดอ่านแล้ว; การ์ด "คำสำคัญที่กำลังโต" ใน `/topics` มาจาก `keywords.json`); ถ้าอภิธานศัพท์มีคู่คำแปลก ๆ มาก แสดงว่าบางวารสารเรียงคำสำคัญสองภาษาไม่ตรงกัน — เพิ่ม `kwtrends.glossary_min_pairs`
- กราฟฝัง: `<เว็บ>/#/embed/topic/<รหัส>` และ `<เว็บ>/#/embed/emerging` ยังใช้ใน `<iframe>` ได้ (กราฟ emerging ลิงก์ไป `#/topics`) แต่ไม่มีปุ่มคัดลอกโค้ดบนหน้าแล้ว — เขียน `<iframe src="…">` เอง; ใช้ได้เฉพาะเว็บออนไลน์; ข้อมูลสังเคราะห์ยังมีป้าย "ข้อมูลตัวอย่าง" ในกรอบที่ฝัง

**เพิ่มในรายการตรวจรายไตรมาส (P4):** `/galaxy` ว่าจุดแสดงและคลิกแล้วได้บทความ; `/journals` ว่าการ์ดบทความที่ถูกอ้างใน TCI มากที่สุดมีข้อมูล (ไม่มี = ดู coverage ใน `manifest.skipped_modules`); `/topics` ว่าคำสำคัญที่กำลังโตสมเหตุสมผล; ถ้าตั้ง `site_url` เปิด `data/feeds/releases.xml` ว่ามีรอบใหม่

## 21. ขึ้นเว็บด้วยข้อมูลจริง (เลิกใช้ข้อมูลตัวอย่าง)

เว็บสาธิตบน GitHub Pages ใช้ข้อมูลสังเคราะห์ จึงมีป้าย "ข้อมูลตัวอย่าง" และไม่ให้เครื่องมือค้นหาเก็บหน้า (noindex) เมื่อรอบข้อมูลมาจากคลังจริง ป้ายนี้หายเองทุกหน้า (เว็บดูจาก `manifest.embedding_provider` — `fixture`/`lite` = ตัวอย่าง) และอ้างอิงได้จริง ขั้นตอน (บนเครื่องที่มีคลังบทความ):

1. ตั้ง `publish.site_url` เป็นที่อยู่ของ Pages (`https://santipongth.github.io/tci-research-atlas/`) เพื่อให้มีฟีด — workflow build เว็บเองด้วยที่อยู่นี้ (ค่าเริ่มของ `ATLAS_SITE_URL`)
2. รันรอบจริงตาม §1 (`uv run atlas quarterly --corpus … --release …` หรือ `bash scripts/quarterly_run.sh --corpus … --release …`; embedding แบบ `local` หรือ `api` — ห้าม `lite`) รวมการดูค่าใช้จ่าย (§1.2, §6) การตรวจผลและชื่อหัวข้อ (§1.4, §7) — เมื่อจบ `web/dist` มีข้อมูลรอบจริง + `atlas-offline.html` แล้ว (validate ผ่านในตัว; เปิดดูในเครื่อง: `cd web && node scripts/serve.mjs --site dist`)
3. `bash scripts/package_release.sh --upload` (จาก root ของ repo, ต้อง `gh auth login` แล้ว) → zip `web/dist/data` + `atlas-offline.html` เป็น `atlas-site-data-<รอบ>.zip` ที่ root ของ repo แล้วสร้าง/อัปเดต GitHub Release `data-<รอบ>` (มีเฉพาะไฟล์ที่เผยแพร่: ไม่มีชื่อผู้แต่ง/บทคัดย่อ; สคริปต์ปฏิเสธรอบที่เป็นข้อมูลตัวอย่าง) — ไม่ใส่ `--upload` = ทำแค่ zip
4. GitHub → Actions → Pages → Run workflow → ใส่ `data_release` = `data-<รอบ>` (หรือ `gh workflow run pages.yml --ref main -f data_release=data-<รอบ>`) → workflow รัน `npm ci`, `npm test`, `npm run build` แล้วแตก zip ลง `dist/` และ deploy → เว็บจริงขึ้นแทนเว็บสาธิต (workflow ปฏิเสธ zip ที่เป็นข้อมูลตัวอย่าง) — ไม่ใส่ `data_release` = กลับเป็นเว็บสาธิต
5. ถ้าต้องการให้ Google เก็บหน้าเว็บจริง: เว็บที่ build ปกติไม่มี noindex — มีเฉพาะเว็บสาธิต (`stage:demo`) และไฟล์ offline template (§22)

ทำเองแบบแยกขั้น (ไม่ใช้ `atlas quarterly`): หลัง `atlas run` + `atlas validate` ใช้ `bash scripts/import_atlas.sh` (build เว็บ + `atlas publish --site web/dist` ด้วย `pipeline/config.yaml`; ถ้าจะใส่ config อื่นให้ใช้ path แบบเต็ม เพราะสคริปต์ย้ายไปที่ `pipeline/` ก่อนเรียก publish) แล้วทำข้อ 3–4

รอบถัดไป: ทำข้อ 2–4 ซ้ำ (รอบก่อนหน้าถูกคัดลอกตามสาย `previous_release` ให้เองเพื่อเทียบ Δ). ย้อนกลับ: Run workflow อีกครั้งด้วยแท็กรอบก่อน (§5)


## 22. ให้ Google เก็บเว็บเข้าดัชนี (SEO)

- `npm run build` ใส่ข้อมูลสำหรับเครื่องมือค้นหาให้เองใน `dist/index.html`: ชื่อหน้า คำอธิบาย ลิงก์ canonical การ์ดตอนแชร์ (Open Graph / Twitter พร้อม `og-image.png` ขนาด 1200×630) และ schema.org แบบ WebSite + Organization + Dataset ซึ่งทำให้ข้อมูลไปขึ้นใน Google Dataset Search ได้ นอกจากนี้ยังสร้าง `robots.txt` และ `sitemap.xml` ให้ด้วย (ทั้งหมดอยู่ใน plugin `atlasSeo` ของ `web/vite.config.ts`)
- ที่อยู่เว็บสาธารณะมาจาก env `ATLAS_SITE_URL` ถ้าไม่ตั้ง จะใช้ `https://santipongth.github.io/tci-research-atlas/` — `atlas quarterly` ตั้งค่านี้จาก `publish.site_url` ให้ตอน build (ขั้น web) ย้ายโดเมนเมื่อไรต้อง build ใหม่ทุกครั้ง (`atlas quarterly --build-web`)
- ไฟล์ HTML ออฟไลน์ไม่มีแท็กเหล่านี้ และติด `noindex` ไว้เสมอ
- **ตราบใดที่เว็บยังใช้ข้อมูลตัวอย่าง** `npm run stage:demo` จะเปลี่ยนแท็กเป็น `noindex` เพราะการให้ Google เก็บตัวเลขสังเคราะห์เข้าดัชนีจะทำให้คนเข้าใจผิด เว็บจะเริ่มถูกเก็บเข้าดัชนีหลังขึ้นด้วยข้อมูลจริงตาม §21
- หลังขึ้นด้วยข้อมูลจริงแล้ว ให้ทำต่อดังนี้:
  1. เข้า Google Search Console → Add property แบบ URL prefix ใส่ที่อยู่เว็บ
  2. ยืนยันความเป็นเจ้าของด้วยวิธี HTML tag โดยใส่ `<meta name="google-site-verification" …>` ใน `web/index.html` แล้ว build และ deploy ใหม่
  3. ส่ง `sitemap.xml` ในเมนู Sitemaps
  4. ใช้ URL Inspection → Request indexing ที่หน้าแรก
- ข้อจำกัด: เว็บใช้ HashRouter (`#/topics/…`) ซึ่ง Google ถือว่าเป็นหน้าเดียว จึงเก็บเข้าดัชนีได้เฉพาะหน้าแรก ถ้าอยากให้หน้าหัวข้อ จังหวัด และวารสารแต่ละหน้าขึ้นผลค้นหาด้วย ต้องเปลี่ยนเป็น URL แบบ path (ดู `docs/ROADMAP.md`)

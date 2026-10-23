# แบรนด์ TCI (brand)

ทุกอย่างที่เกี่ยวกับแบรนด์อยู่ที่ `brand.ts` ไฟล์เดียว

- **โลโก้ TCI บนแถบหัวเว็บ:** `BRAND.logo` ใช้ไฟล์ `src/assets/brand/partners/tci.png` (โลโก้ทางการ, `temporary: false`)
- **โลโก้ผู้จัดทำในส่วนท้ายเว็บ:** `PARTNERS` = TCI · NECTEC · สวทช. ตามลำดับที่เจ้าของโครงการกำหนด ไฟล์อยู่ใน `src/assets/brand/partners/`
- **เปลี่ยนหรือเพิ่มโลโก้:** วางไฟล์ PNG/SVG ใน `src/assets/brand/partners/` แล้ว import ใน `brand.ts` พร้อมข้อความ `alt` ทั้งไทยและอังกฤษ และขนาดจริง (`width`, `height`) ส่วนที่เหลือไม่ต้องแก้: Vite ใส่ hash ให้ไฟล์ในเว็บ และฝังเป็น data URI ในไฟล์ `atlas-offline.html` ให้เอง
- **ข้อความ "เครื่องหมายชั่วคราว":** แสดงในส่วนท้ายเว็บเฉพาะเมื่อ `temporary: true` ซึ่งตอนนี้ไม่ใช้แล้ว
- **รูปตอนแชร์ลิงก์ (`public/og-image.png`, 1200×630):** มีโลโก้ TCI · NECTEC · สวทช. อยู่ในรูป ถ้าเปลี่ยนโลโก้ต้องทำรูปนี้ใหม่ด้วย
- **สีและตัวอักษร:** อยู่ใน `DESIGN.md` (ที่รากของ repo) และ `src/styles/tokens.css` เช่น น้ำเงิน TCI `#283894`, ส้มเน้น `--accent-mark` และฟอนต์ Sarabun

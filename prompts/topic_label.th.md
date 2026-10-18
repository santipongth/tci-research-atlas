# Prompt: ตั้งชื่อหัวข้อวิจัย (topic labeling)

> **สถานะ: ใช้งานจริง** — สำเนาฝังอยู่ใน `pipeline/atlas/label.py` (ตัวแปร `PROMPT_TEMPLATE`)
> แก้ไฟล์นี้แล้วต้อง sync กลับเข้าโค้ดด้วย (และในทางกลับกัน) — การเปลี่ยน prompt เปลี่ยน `cache_key` (hash ของ model + prompt) → label ทุก topic จะถูกสร้างใหม่ในรอบถัดไป (จ่ายค่า API อีกครั้ง)

## บริบทการใช้

- เรียกต่อ **fine topic** 1 ครั้ง — input คือ top c-TF-IDF terms + ชื่อบทความตัวแทน
- inputs: `{keywords}` = top author keywords (คั่นด้วย "; "), `{terms}` = c-TF-IDF words (คั่นด้วย "; "), `{titles}` = MMR representative titles (บรรทัดละ 1 ชื่อเรื่อง)
- cache key = sha256(model + prompt) (ตัดเหลือ 16 hex) เก็บใน `state/label_cache.parquet` — เปลี่ยน prompt หรือ model หรือ members ของ topic → label ถูกสร้างใหม่เฉพาะ topic นั้น
- ผลที่คาด: **JSON เท่านั้น** ตาม schema — โค้ด parse ด้วย `json.loads` + ตัด markdown fence ออก

## Prompt (master)

```
คุณคือบรรณาธิการวารสารวิชาการไทย ช่วยตั้งชื่อหัวข้อวิจัย (research topic) จากข้อมูลต่อไปนี้

คำสำคัญที่ผู้เขียนใช้บ่อยในกลุ่มนี้: {keywords}
คำเด่นจากเนื้อหา (c-TF-IDF): {terms}

ตัวอย่างชื่อเรื่องบทความที่เป็นตัวแทนของกลุ่ม:
{titles}

ตอบกลับเป็น JSON เท่านั้น ตาม schema นี้ ห้ามมีข้อความอื่น:
{
  "name_th": "ชื่อหัวข้อภาษาไทย กระชับ ไม่เกิน 8 คำ",
  "name_en": "Concise English topic name, max 6 words",
  "description": "คำอธิบาย 1 บรรทัดว่าหัวข้อนี้ครอบคลุมงานวิจัยแบบไหน",
  "keywords": ["คำสำคัญ", "4-6", "คำ"]
}
```

## แนวทางปรับแต่ง (ถ้าจำเป็น)

- ถ้าชื่อไทยออกมายาว/เป็นทางการเกิน → เติมบรรทัด "ใช้ภาษาที่บรรณาธิการวารสารใช้จริง ไม่ใช่ภาษาแปล" ท้าย prompt
- ถ้า description ว่างบ่อย (โมเดลอ่อน) → แยกเป็น 2 ขั้น: ขอ name ก่อน แล้วค่อยขอ description จาก name+terms
- ทดสอบ prompt ใหม่กับ 5–10 topic ก่อนรันจริงทั้งหมด (ดูผลใน `work/05_labels.parquet`)

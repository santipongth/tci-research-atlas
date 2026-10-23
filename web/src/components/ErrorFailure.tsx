import { useI18n } from '../lib/i18n'

/** What replaces a page that failed to render (see ErrorBoundary). `shell`: the site's header and menu failed too. */
export function ErrorFailure({ chunk, shell = false }: { chunk: boolean; shell?: boolean }) {
  const { pick } = useI18n()
  return (
    <div className="container">
      <div className="banner" role="alert">
        <h1>{chunk ? pick('เว็บมีรุ่นใหม่แล้ว', 'The site has been updated') : pick('หน้านี้แสดงไม่สำเร็จ', 'This page could not be shown')}</h1>
        <p>
          {chunk
            ? pick('โหลดหน้านี้ใหม่เพื่อใช้รุ่นล่าสุด', 'Reload this page to get the latest version.')
            : shell
              ? pick('เกิดข้อผิดพลาดตอนแสดงหน้านี้ ลองโหลดใหม่อีกครั้ง', 'Something went wrong while showing this page. Try reloading it.')
              : pick('เกิดข้อผิดพลาดตอนแสดงหน้านี้ ลองโหลดใหม่ หรือเลือกหน้าอื่นจากเมนู', 'Something went wrong while showing this page. Reload it, or pick another page from the menu.')}
        </p>
        <p className="mt-2">
          <button type="button" className="btn" onClick={() => window.location.reload()}>{pick('โหลดใหม่', 'Reload')}</button>
        </p>
      </div>
    </div>
  )
}

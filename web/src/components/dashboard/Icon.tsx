/** The dashboard's drawn icon set: one 24-unit grid, a 1.75 stroke, round ends (decorative: always aria-hidden). */
const PATHS = {
  overview: 'M4 4h7v7H4zM13 4h7v4h-7zM13 10h7v10h-7zM4 13h7v7H4z',
  topics: 'M3 17l6-6 4 4 8-8M15 7h6v6',
  places: 'M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21zM12 12a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z',
  journals: 'M3 5.5C5.5 4 8.5 4 12 6c3.5-2 6.5-2 9-.5V19c-2.5-1.5-5.5-1.5-9 .5-3.5-2-6.5-2-9-.5zM12 6v13.5',
  goals: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 16.5a4.5 4.5 0 1 0 0-9 4.5 4.5 0 0 0 0 9zM12 12.5a.5.5 0 1 0 0-1 .5.5 0 0 0 0 1z',
  atlas: 'M9 4 3 6.5v13.5l6-2.5 6 2.5 6-2.5V4l-6 2.5zM9 4v13.5M15 6.5V20',
  galaxy: 'M5 7.5a1.5 1.5 0 1 0 0-.01M12 5a1 1 0 1 0 0-.01M18.5 9a2 2 0 1 0 0-.01M8.5 14a2 2 0 1 0 0-.01M15 16.5a1.5 1.5 0 1 0 0-.01M5.5 19.5a1 1 0 1 0 0-.01M19 19a1 1 0 1 0 0-.01',
  brief: 'M6 3h8l4 4v14H6zM14 3v4h4M9 11h6M9 14.5h6M9 18h4',
  about: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .8-1 1.5v.7M12 17h.01',
  articles: 'M6 3h8l4 4v14H6zM14 3v4h4M9 12h6M9 16h6',
  layers: 'M12 3 3 8l9 5 9-5zM3 12.5l9 5 9-5M3 17l9 5 9-5',
  building: 'M4 21V6l8-3 8 3v15M4 21h16M9 21v-4h6v4M8 9h.01M12 9h.01M16 9h.01M8 13h.01M12 13h.01M16 13h.01',
  menu: 'M4 6.5h16M4 12h16M4 17.5h16',
  close: 'M6 6l12 12M18 6 6 18',
  more: 'M5 12h.01M12 12h.01M19 12h.01',
  arrow: 'M5 12h14M13 6l6 6-6 6',
  download: 'M12 4v11M7.5 10.5 12 15l4.5-4.5M4.5 16.5V20h15v-3.5',
  table: 'M4 5h16v14H4zM4 10h16M4 14.5h16M10 10v9',
  chart: 'M4 4v16h16M8 16v-5M12 16V8M16 16v-3',
  info: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 11v5.5M12 7.5h.01',
} as const

export type IconName = keyof typeof PATHS

export function Icon({ name, size = 20, className }: { name: IconName; size?: number; className?: string }) {
  return (
    <svg className={className ? `ico ${className}` : 'ico'} viewBox="0 0 24 24" width={size} height={size} aria-hidden="true" focusable="false">
      <path d={PATHS[name]} fill="none" stroke="currentColor" strokeWidth={['more'].includes(name) ? 3 : 1.75} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

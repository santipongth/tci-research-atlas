import type { ReactNode } from 'react'
import type { GoalTile } from './execLayout'

export interface GoalTileView extends GoalTile {
  /** "SDG 3" or "1" */
  code: string
  name: string
  /** the share as printed ("11.8% ของบทความ") */
  shareText: string
  /** the topic list shown when the tile opens */
  list: ReactNode
}

/**
 * A grid of goal tiles: the goal number, its name, the topic count as the big number and a small share bar (ink on a
 * paper-tint track; the percentage is always printed). A tile with topics opens in place (a native disclosure, full row
 * while open) to list them; a goal with no topic is a dashed outline that says so. Ink and one blue only — never the
 * official SDG colours or icons.
 */
export function GoalTiles({ tiles, label, countWord, emptyText }: {
  tiles: readonly GoalTileView[]
  label: string
  countWord: (n: number) => string
  emptyText: string
}) {
  const head = (g: GoalTileView) => (
    <>
      <span className="gt-code">{g.code}</span>
      <span className="gt-name">{g.name}</span>
    </>
  )
  return (
    <ul className="gt" aria-label={label}>
      {tiles.map((g) =>
        g.count > 0 ? (
          <li key={g.id} className="gt-tile">
            <details>
              <summary>
                {head(g)}
                <span className="gt-count">
                  <b>{g.count}</b> {countWord(g.count)}
                </span>
                <span className="gt-share">
                  <span className="gt-bar" aria-hidden="true"><i style={{ width: `${Math.max(2, g.frac * 100)}%` }} /></span>
                  <span>{g.shareText}</span>
                </span>
                <svg className="gt-chev" viewBox="0 0 12 8" width="12" height="8" aria-hidden="true" focusable="false">
                  <path d="M1 1.5l5 5 5-5" fill="none" stroke="currentColor" strokeWidth="1.8" />
                </svg>
              </summary>
              <div className="gt-list">{g.list}</div>
            </details>
          </li>
        ) : (
          <li key={g.id} className="gt-tile is-empty">
            <div className="gt-static">
              {head(g)}
              <span className="gt-none">{emptyText}</span>
            </div>
          </li>
        ),
      )}
    </ul>
  )
}

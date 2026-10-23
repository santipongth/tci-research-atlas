import { Fragment } from 'react'

/** Text in which `phrase` never breaks across lines in Thai (a headline must not split "งานวิจัย | ไทย"); other words wrap as usual. */
export function KeepTogether({ text, phrase }: { text: string; phrase: string }) {
  const parts = text.split(phrase)
  return (
    <>
      {parts.map((part, i) => (
        <Fragment key={i}>
          {i > 0 ? <span className="story-q">{phrase}</span> : null}
          {part}
        </Fragment>
      ))}
    </>
  )
}

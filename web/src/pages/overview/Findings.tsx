import { SegmentText } from '../../components/SegmentText'
import type { AtlasRelease } from '../../data/release'
import { segmentHeadline } from '../../lib/highlight'

/** Executive points from the brief (template or grounded LLM text); topic names become links. */
export function Findings({ release, bullets }: { release: AtlasRelease; bullets: readonly string[] }) {
  return (
    <ol className="points">
      {bullets.map((b, i) => (
        <li className="point" key={i}>
          <p>
            <SegmentText segments={segmentHeadline(b, release.topics, { figures: false })} mark={false} />
          </p>
        </li>
      ))}
    </ol>
  )
}

import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { StoryLines, type StorySeries } from '../../charts/StoryLines'
import { DataTable, type Column } from '../../components/DataTable'
import { Figure } from '../../components/Figure'
import type { AtlasRelease } from '../../data/release'
import type { Topic } from '../../data/types'
import { fmtDate, fmtInt, fmtNum, fmtSignedPct } from '../../lib/format'
import { useI18n } from '../../lib/i18n'
import { pickRisers } from '../../lib/story'
import { figureCsv } from '../../lib/tableCsv'
import { overviewCodec } from '../../lib/urlState'
import { useDocumentTitle } from '../../lib/useDocumentTitle'
import { useUrlState } from '../../lib/useUrlState'

interface YearRow {
  year: number
  values: (number | null)[]
}

/**
 * The front door as a data story: the reader's question as the page h1, the answer in one sentence (the topic name
 * links to it), one number, then the chart that proves it — the fastest-growing topics, the answer in TCI blue.
 */
export function StoryHero({ release, children }: { release: AtlasRelease; children?: ReactNode }) {
  const { t, lang, name } = useI18n()
  const [state, update] = useUrlState(overviewCodec)
  const question = t('ov.q').split('|')
  useDocumentTitle(question.join(' '))
  const ov = release.overview
  const risers = pickRisers(release.topics, 5)
  const leader: Topic | undefined = risers[0]
  const years = release.series.years
  const series: StorySeries[] = risers.map((tp) => ({ id: tp.id, label: name(tp), values: (release.series.topics[tp.id] ?? []).map((v) => (Number.isFinite(v) ? v : null)) }))
  // the number in plain words: "2.1 เท่า" once the share at least doubles a year, else "+29%"
  const g = leader?.metrics.share_growth ?? 0
  const times = g >= 1 ? fmtNum(1 + g, 1) : null
  const growth = times ? t('ov.heroTimes', { m: times }) : fmtSignedPct(g, 0)
  const followers = risers.slice(1, 3).map((tp) => name(tp))
  const answer = !leader
    ? t('ov.answerNone')
    : followers.length === 2
      ? t('ov.answer', { topic: name(leader), b: followers[0], c: followers[1] })
      : t('ov.answerOne', { topic: name(leader) })
  const at = leader ? answer.indexOf(name(leader)) : -1
  const rows: YearRow[] = years.map((year, k) => ({ year, values: series.map((s) => s.values[k] ?? null) }))
  const columns: Column<YearRow>[] = [
    { key: 'year', csvHeader: 'year', header: t('col.year'), rowHeader: true, cell: (r) => String(r.year), sortValue: (r) => r.year },
    ...series.map((s, i): Column<YearRow> => ({ key: s.id, csvHeader: s.id, header: s.label, numeric: true, cell: (r) => fmtInt(r.values[i]), sortValue: (r) => r.values[i], csv: (r) => r.values[i] })),
  ]
  const tableTitle = t('table.n', { n: 1, title: t('ov.story.table') })
  return (
    <section className="story" aria-labelledby="story-h">
      <div className="story-text">
        <h1 id="story-h">
          {question.map((part, i) => (
            <span key={i} className="story-q">
              {i > 0 ? ' ' : ''}
              {part}
            </span>
          ))}
        </h1>
        <p className="story-answer">
          {leader && at >= 0 ? (
            <>
              {answer.slice(0, at)}
              <Link to={`/topics/${leader.id}`}>{name(leader)}</Link>
              {answer.slice(at + name(leader).length)}
            </>
          ) : (
            answer
          )}
        </p>
        {leader ? (
          <p className="story-num">
            <span className="story-big">{growth}</span>
            <span className="story-unit">{times ? t('ov.heroUnitTimes', { topic: name(leader), m: times }) : t('ov.heroUnit', { topic: name(leader) })}</span>
          </p>
        ) : null}
        <p className="story-by">
          {t('ov.byline', { articles: fmtInt(ov.kpis.articles), year: ov.last_complete_year, date: fmtDate(ov.generated_at, lang) })}
        </p>
        {children}
      </div>
      {series.length >= 2 && leader ? (
        <div className="story-fig">
          <Figure
            id="fig-story"
            number={1}
            title={t('ov.story.fig', { n: fmtInt(series.length), a: years[0], b: years[years.length - 1] })}
            tableTitle={tableTitle}
            csv={figureCsv(`atlas-${ov.release}-fastest-growing.csv`, rows, columns)}
            how={<p>{t('ov.story.how', { n: fmtInt(series.length) })}</p>}
            source={t('source.line', { release: ov.release })}
            view={state.sto}
            onView={(v) => update({ sto: v })}
            chart={
              <StoryLines
                years={years}
                series={series}
                initial={leader.id}
                format={(v) => fmtInt(v)}
                label={t('ov.story.label', { n: fmtInt(series.length), topic: name(leader) })}
                note={(s) => {
                  // the rise over the last three years with articles, e.g. "จาก 18 เรื่องในปี 2022 เป็น 95 เรื่องในปี 2024"
                  const last = s.values.reduce<number>((a, v, k) => (v !== null ? k : a), -1)
                  let first = Math.max(0, last - 2)
                  while (first < last && !((s.values[first] ?? 0) > 0)) first++
                  return t('ov.story.note', { a: fmtInt(s.values[first]), y0: years[first], b: fmtInt(s.values[last]), y1: years[last] })
                }}
              />
            }
            table={<DataTable caption={tableTitle} rows={rows} columns={columns} rowKey={(r) => String(r.year)} stack={false} />}
          />
          <p className="story-more">
            <Link to="/emerging">{t('ov.story.more')}</Link>
          </p>
        </div>
      ) : null}
    </section>
  )
}

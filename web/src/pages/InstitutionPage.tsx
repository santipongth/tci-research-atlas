import { Link, useParams } from 'react-router'
import { DataTable, type Column } from '../components/DataTable'
import { InstitutionLink } from '../components/InstitutionLink'
import { ModuleFile } from '../components/ModuleFile'
import { OnThisPage } from '../components/OnThisPage'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { ShareBar } from '../components/ShareBar'
import { TopicLink } from '../components/TopicLink'
import { useReleaseFile } from '../data/atlasContext'
import { MODULE_FILES, type AtlasRelease } from '../data/release'
import type { CountryCount, InstitutionDetail, InstitutionSummary, InstitutionsFile, Partner, Topic, TopicShare } from '../data/types'
import { instName, otherInstName } from '../lib/executive'
import { DASH, fmtInt, fmtNum, fmtPct } from '../lib/format'
import { useI18n } from '../lib/i18n'
import type { StrKey } from '../strings'

export default function InstitutionPage() {
  const { id } = useParams()
  const { t } = useI18n()
  return (
    <RequireRelease title={t('in.title')}>
      {(release) => (
        <ModuleFile<InstitutionsFile> release={release} module="institutions" path={MODULE_FILES.institutions} title={t('in.title')}>
          {(file) => <InstitutionView release={release} file={file} id={id ?? ''} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

function InstitutionView({ release, file, id }: { release: AtlasRelease; file: InstitutionsFile; id: string }) {
  const { t } = useI18n()
  const inst = file.institutions.find((i) => i.id === id)
  if (!inst) {
    return (
      <div className="container">
        <PageHeader title={t('in.notFound', { id: id || DASH })} lede={t('in.notFound.body')} />
        <p className="mt-6"><Link to="/institutions">{t('in.back')}</Link></p>
      </div>
    )
  }
  return <InstitutionContent key={inst.id} release={release} file={file} inst={inst} />
}

function InstitutionContent({ release, file, inst }: { release: AtlasRelease; file: InstitutionsFile; inst: InstitutionSummary }) {
  const { t, lang } = useI18n()
  const detailFile = useReleaseFile<InstitutionDetail>(`institutions/${inst.id}.json`)
  const detail = detailFile.status === 'ready' ? detailFile.data : null
  const byId = new Map(file.institutions.map((i) => [i.id, i]))
  const topicOf = (tid: string): Topic | undefined => release.topicById.get(tid)
  const topics = (detail?.topics ?? []).filter((s) => topicOf(s.topic))
  const signals = topics.map((s) => topicOf(s.topic) as Topic).filter((tp) => tp.status === 'EMERGING' || tp.status === 'WATCH')
  const partners = (detail?.partners ?? []).filter((p) => byId.has(p.id))
  const countries = detail?.countries ?? []
  const suggested = (detail?.suggested ?? []).filter((s) => byId.has(s.id))
  const years = detail?.years ?? []
  const shown = instName(inst, lang)
  const other = otherInstName(inst, lang)
  const province = (file.province_names ?? []).find((p) => p.code === inst.province)
  const place = province ? (lang === 'en' ? province.name_en : province.name_th) : inst.country && inst.country !== 'TH' ? t('in.abroad', { c: inst.country }) : t('in.unplaced')
  const w = file.window
  const r = file.recent
  const rel = release.overview.release
  const toc = [
    { id: 'numbers', label: t('in.numbers.h') },
    ...(topics.length ? [{ id: 'topics', label: t('in.topics.h') }] : []),
    ...(partners.length ? [{ id: 'partners', label: t('in.partners.h') }] : []),
    ...(countries.length ? [{ id: 'abroad', label: t('in.countries.h') }] : []),
    ...(suggested.length ? [{ id: 'suggested', label: t('in.suggest.h') }] : []),
    ...(years.length ? [{ id: 'years', label: t('in.years.h') }] : []),
  ]
  const maxShare = Math.max(0.0001, ...topics.map((s) => s.share))
  const topicColumns: Column<TopicShare>[] = [
    { key: 'topic', csvHeader: 'topic_id', header: t('col.topic'), rowHeader: true, cell: (s) => <TopicLink topic={topicOf(s.topic) as Topic} showStatus />, sortValue: (s) => s.topic, csv: (s) => s.topic },
    { key: 'count', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (s) => fmtInt(s.count), sortValue: (s) => s.count },
    { key: 'share', csvHeader: 'share', header: t('col.share'), numeric: true, cell: (s) => <ShareBar value={s.share} max={maxShare} />, sortValue: (s) => s.share },
  ]
  const partnerColumns: Column<Partner>[] = [
    { key: 'name', csvHeader: 'institution_id', header: t('col.institution'), rowHeader: true, cell: (p) => <InstitutionLink inst={byId.get(p.id) as InstitutionSummary} />, sortValue: (p) => instName(byId.get(p.id) as InstitutionSummary, lang).text, csv: (p) => p.id },
    { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (p) => fmtInt(p.articles), sortValue: (p) => p.articles },
  ]
  const countryColumns: Column<CountryCount>[] = [
    { key: 'name', csvHeader: 'country', header: t('in.col.country'), rowHeader: true, cell: (c) => (lang === 'en' ? c.name_en : c.name_th), csv: (c) => c.code },
    { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (c) => fmtInt(c.articles), sortValue: (c) => c.articles },
  ]
  const yearColumns: Column<{ year: number; articles: number }>[] = [
    { key: 'year', csvHeader: 'year', header: t('col.year'), rowHeader: true, cell: (y) => String(y.year), sortValue: (y) => y.year },
    { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (y) => fmtInt(y.articles), sortValue: (y) => y.articles },
  ]
  return (
    <div className="container">
      <PageHeader title={shown.text} titleLang={shown.lang ?? undefined}>
        {other ? <p className="tp-alt" lang={lang === 'en' ? 'th' : 'en'}>{other}</p> : null}
        <div className="j-tags">
          <span className="tp-badge">{t(`in.type.${inst.type ?? 'other'}` as StrKey)}</span>
          <span>{place}</span>
          <span className="tp-sub">{t(`in.source.${inst.source}` as StrKey)}</span>
          {inst.ror ? (
            <a href={`https://ror.org/${inst.ror}`} target="_blank" rel="noopener noreferrer">ROR<span className="sr-only"> {t('newTab')}</span></a>
          ) : null}
        </div>
      </PageHeader>
      <div className="layout">
        <div className="main-col">
          <Section id="numbers" title={t('in.numbers.h')}>
            <dl className="summary">
              <div>
                <dt>{t('col.articles')}</dt>
                <dd>{fmtInt(inst.articles)}<small>{t('in.articlesSub', { a: w.start, b: w.end, all: fmtInt(inst.articles_total) })}</small></dd>
              </div>
              <div>
                <dt>{t('in.col.recent')}</dt>
                <dd>{fmtInt(inst.articles_recent ?? 0)}<small>{t('in.recentSub', { a: r.start, b: r.end })}</small></dd>
              </div>
              <div>
                <dt>{t('in.col.intl')}</dt>
                <dd>{fmtPct(inst.intl_share ?? null, 0)}<small>{t('in.intlSub')}</small></dd>
              </div>
              <div>
                <dt>{t('in.col.partners')}</dt>
                <dd>{fmtInt(inst.partners ?? 0)}<small>{t('in.partnersSub')}</small></dd>
              </div>
              <div>
                <dt>{t('col.topic')}</dt>
                <dd>{fmtInt(inst.topics ?? 0)}<small>{t('in.topicsSub')}</small></dd>
              </div>
            </dl>
          </Section>

          {topics.length ? (
            <Section id="topics" title={t('in.topics.h')}>
              <DataTable caption={t('table.n', { n: 1, title: t('in.topics.table') })} rows={topics} columns={topicColumns} rowKey={(s) => s.topic} defaultSort={{ key: 'count', dir: 'desc' }} csvFilename={`atlas-${rel}-${inst.id}-topics.csv`} />
              {signals.length ? (
                <>
                  <h3 className="mt-6">{t('in.emerging')}</h3>
                  <ul className="opp-list">
                    {signals.map((tp) => (
                      <li key={tp.id}><TopicLink topic={tp} showStatus /></li>
                    ))}
                  </ul>
                </>
              ) : null}
            </Section>
          ) : null}

          {partners.length ? (
            <Section id="partners" title={t('in.partners.h')}>
              <DataTable caption={t('table.n', { n: 2, title: t('in.partners.table') })} rows={partners} columns={partnerColumns} rowKey={(p) => p.id} defaultSort={{ key: 'articles', dir: 'desc' }} csvFilename={`atlas-${rel}-${inst.id}-partners.csv`} />
            </Section>
          ) : null}

          {countries.length ? (
            <Section id="abroad" title={t('in.countries.h')}>
              <DataTable caption={t('table.n', { n: 3, title: t('in.countries.table') })} rows={countries} columns={countryColumns} rowKey={(c) => c.code} stack={false} csvFilename={`atlas-${rel}-${inst.id}-countries.csv`} />
            </Section>
          ) : null}

          {suggested.length ? (
            <Section id="suggested" title={t('in.suggest.h')} intro={t('in.suggest.intro', { a: w.start, b: w.end })}>
              <ul className="sug-list">
                {suggested.map((s) => (
                  <li key={s.id}>
                    <InstitutionLink inst={byId.get(s.id) as InstitutionSummary} />
                    <span className="sug-topics">
                      <span className="topic-sub">{t('in.suggest.sub', { s: fmtNum(s.similarity, 2) })}</span>
                      {(s.topics ?? []).map((tid) => topicOf(tid)).filter((tp): tp is Topic => tp !== undefined).map((tp) => (
                        <TopicLink key={tp.id} topic={tp} />
                      ))}
                    </span>
                  </li>
                ))}
              </ul>
            </Section>
          ) : null}

          {years.length ? (
            <Section id="years" title={t('in.years.h')}>
              <DataTable caption={t('table.n', { n: 4, title: t('in.years.table') })} rows={years} columns={yearColumns} rowKey={(y) => String(y.year)} stack={false} defaultSort={{ key: 'year', dir: 'asc' }} csvFilename={`atlas-${rel}-${inst.id}-years.csv`} />
            </Section>
          ) : null}
          {detailFile.status === 'loading' ? <p className="loading" role="status">{t('loading')}</p> : null}
        </div>
        <aside className="rail" aria-label={t('onThisPage')}>
          <OnThisPage items={toc} />
          <p className="mt-6"><Link to="/institutions">{t('in.back')}</Link></p>
        </aside>
      </div>
    </div>
  )
}

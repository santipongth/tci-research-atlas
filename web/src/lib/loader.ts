/**
 * Atlas data loader — tries the pipeline-exported live dataset first
 * (`/data/atlas_data.json`, produced by tci-atlas-pipeline and dropped into
 * web/public/data/), falls back to the bundled static dataset (atlas.ts).
 *
 * This is what makes the site a "live dashboard": the team reruns the batch
 * every quarter, copies the new atlas_data.json in, redeploys — no code change.
 */
import {
  GROUPS, LINKS, NODES, TOTAL_ARTICLES, TOTAL_FIELDS, TOTAL_GROUPS,
  type AtlasGroup, type AtlasLink, type AtlasNode, type TopicForecast,
} from '../data/atlas'

export interface AtlasData {
  groups: AtlasGroup[]
  nodes: AtlasNode[]
  links: AtlasLink[]
  totalArticles: number
  totalFields: number
  totalGroups: number
  /** true = loaded from pipeline export; false = bundled fallback */
  dynamic: boolean
  lastCompleteYear?: number
  generatedAt?: string
}

export const STATIC_DATA: AtlasData = {
  groups: GROUPS,
  nodes: NODES,
  links: LINKS,
  totalArticles: TOTAL_ARTICLES,
  totalFields: TOTAL_FIELDS,
  totalGroups: TOTAL_GROUPS,
  dynamic: false,
}

interface RawNode {
  nodeId: string; kind: 'group' | 'topic'; group?: string
  th: string; en: string; description?: string; keywords?: string
  articles: number; color: string; x: number; y: number; r: number
  rank?: number; nTopics?: number
  status?: AtlasNode['status']; emerging_score?: number | null
  cagr_recent?: number | null; burst_years?: string
  forecast?: TopicForecast | null
}

interface RawAtlas {
  meta: { total_articles: number; total_topics: number; total_groups: number; last_complete_year?: number; generated_at?: string }
  groups: Array<{ id: string; th: string; en: string; color: string; articles: number; rank?: number }>
  nodes: RawNode[]
  links: Array<{ s: string; t: string }>
}

function normalize(raw: RawAtlas): AtlasData {
  const groups: AtlasGroup[] = raw.groups.map((g, i) => {
    const memberCount = raw.nodes.filter((n) => n.kind === 'topic' && n.group === g.id).length
    return { id: g.id, th: g.th, en: g.en, color: g.color, articles: g.articles, rank: g.rank ?? i + 1, fieldCount: memberCount }
  })
  const nodes: AtlasNode[] = raw.nodes.map((n) => ({
    id: n.nodeId,
    kind: n.kind === 'group' ? 'group' : 'field',
    group: n.group,
    th: n.th,
    en: n.en,
    articles: n.articles,
    color: n.color,
    x: n.x,
    y: n.y,
    r: n.r,
    rank: n.rank,
    nFields: n.nTopics,
    status: n.status,
    emergingScore: n.emerging_score ?? null,
    burstYears: n.burst_years ?? '',
    description: n.description ?? '',
    keywords: n.keywords ?? '',
    forecast: n.forecast ?? null,
  }))
  return {
    groups,
    nodes,
    links: raw.links.map((l) => ({ s: l.s, t: l.t })),
    totalArticles: raw.meta.total_articles,
    totalFields: raw.meta.total_topics,
    totalGroups: raw.meta.total_groups,
    dynamic: true,
    lastCompleteYear: raw.meta.last_complete_year,
    generatedAt: raw.meta.generated_at,
  }
}

export async function loadAtlas(): Promise<AtlasData> {
  try {
    const res = await fetch('/data/atlas_data.json', { cache: 'no-cache' })
    if (!res.ok) throw new Error(String(res.status))
    const raw = (await res.json()) as RawAtlas
    if (!raw.nodes?.length || !raw.groups?.length) throw new Error('empty dataset')
    console.info(`[atlas] live dataset loaded (${raw.meta.total_articles.toLocaleString()} articles, generated ${raw.meta.generated_at})`)
    return normalize(raw)
  } catch {
    console.info('[atlas] no /data/atlas_data.json — using bundled dataset')
    return STATIC_DATA
  }
}

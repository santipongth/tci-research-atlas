import { describe, expect, it } from 'vitest'
import type { Topic } from '../data/types'
import { pickIdeas } from './ideas'

const tp = (id: string, status: Topic['status'], score: number, group = 'G1'): Topic =>
  ({ id, status, score, group, th: id, en: id, metrics: {} }) as unknown as Topic

const TOPICS = [
  tp('w1', 'WATCH', 50),
  tp('e1', 'EMERGING', 40),
  tp('e2', 'EMERGING', 70, 'G2'),
  tp('h1', 'HOT', 90),
  tp('h2', 'HOT', 80),
  tp('s1', 'STABLE', 10),
  tp('d1', 'DECLINING', 5),
  tp('l1', 'LOW_DATA', 0),
]

describe('pickIdeas', () => {
  it('lists emerging, then watch, then rising topics few institutions work on; never stable, declining or low data', () => {
    const ideas = pickIdeas(TOPICS, new Map([['h2', 3], ['e1', 2], ['s1', 1]]))
    expect(ideas.map((i) => [i.topic.id, i.kind])).toEqual([['e2', 'emerging'], ['e1', 'emerging'], ['w1', 'watch'], ['h2', 'few']])
    expect(ideas.find((i) => i.topic.id === 'e1')?.institutions).toBe(2)
  })
  it('narrows to one field', () => {
    expect(pickIdeas(TOPICS, new Map(), 'G2').map((i) => i.topic.id)).toEqual(['e2'])
    expect(pickIdeas([], new Map())).toEqual([])
  })
})

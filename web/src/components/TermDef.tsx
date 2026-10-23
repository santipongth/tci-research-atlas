import { useRelease } from '../data/atlasContext'
import { defKey, glossaryVars, type GlossaryTerm } from '../lib/glossary'
import { useStrings } from '../lib/i18n'
import { glossaryDefs } from '../strings/glossaryDefs'

/** A glossary definition, its figures filled from the release. Its own chunk: loaded with the first `Term` on a page. */
export default function TermDef({ term }: { term: GlossaryTerm }) {
  const s = useStrings(glossaryDefs)
  return <>{s(defKey(term), glossaryVars(useRelease()))}</>
}

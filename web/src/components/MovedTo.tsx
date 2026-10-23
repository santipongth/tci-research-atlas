import { Navigate, useLocation } from 'react-router'

/** A retired route: replace it with the page that now carries its content, keeping the query when it still means something. */
export function MovedTo({ to, keepQuery = false }: { to: string; keepQuery?: boolean }) {
  const { search } = useLocation()
  return <Navigate to={{ pathname: to, search: keepQuery ? search : '' }} replace />
}

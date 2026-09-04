import { useCallback, useEffect, useState } from 'react'

import { ApiError } from '../api/client'

interface State<T> {
  data: T | null
  loading: boolean
  error: string | null
}

/** Small load-with-loading-and-error helper, so every page handles all three
 *  states instead of only the happy one. */
export function useAsync<T>(loader: () => Promise<T>, deps: unknown[] = []) {
  const [state, setState] = useState<State<T>>({ data: null, loading: true, error: null })

  const run = useCallback(() => {
    let cancelled = false
    setState((previous) => ({ ...previous, loading: true, error: null }))
    loader()
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: null })
      })
      .catch((caught: unknown) => {
        if (cancelled) return
        setState({
          data: null,
          loading: false,
          error: caught instanceof ApiError ? caught.message : 'Something went wrong.',
        })
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  useEffect(run, [run])

  return { ...state, reload: run }
}

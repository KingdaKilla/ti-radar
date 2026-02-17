import { useState, useCallback, useRef } from 'react'
import { fetchRadar } from '../api'

/**
 * Custom Hook fuer die Radar-Analyse.
 * Verwaltet Loading, Error und Result State.
 */
export function useRadar() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const lastParamsRef = useRef(null)

  const analyze = useCallback(async (technology, years = 10) => {
    setLoading(true)
    setError(null)
    lastParamsRef.current = { technology, years }

    try {
      const result = await fetchRadar(technology, years)
      setData(result)
    } catch (err) {
      setError(err.message)
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [])

  const retry = useCallback(() => {
    if (lastParamsRef.current) {
      analyze(lastParamsRef.current.technology, lastParamsRef.current.years)
    }
  }, [analyze])

  return { data, loading, error, analyze, retry }
}

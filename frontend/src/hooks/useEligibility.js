import { useState } from 'react'
import { checkEligibility } from '../services/api.js'

export function useEligibility() {
  const [results, setResults] = useState([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  async function run(profile) {
    setIsLoading(true)
    setError('')

    try {
      const response = await checkEligibility(profile)
      setResults(response.results || [])
      setTotal(response.total_estimated_monthly_usd || 0)
      return response
    } catch (err) {
      setError(err.message || 'Eligibility check failed')
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  return { results, total, isLoading, error, run }
}

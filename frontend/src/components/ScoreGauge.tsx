import { useEffect, useState } from 'react'

import { GradeBadge, scoreGradient } from './common'

interface Props {
  score: number
  grade?: string | null
  size?: number
}

/** Big animated dial. Plain SVG with a gradient stroke -- no chart library. */
export function ScoreGauge({ score, grade, size = 200 }: Props) {
  const target = Math.max(0, Math.min(100, score))
  const [shown, setShown] = useState(0)

  // Count the number up on mount; the arc follows the same value.
  useEffect(() => {
    let frame = 0
    const start = performance.now()
    const duration = 1100
    const tick = (now: number) => {
      const t = Math.min((now - start) / duration, 1)
      const eased = 1 - Math.pow(1 - t, 3)
      setShown(target * eased)
      if (t < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [target])

  const stroke = 14
  const radius = size / 2 - stroke
  const circumference = 2 * Math.PI * radius
  // Leave a gap at the bottom so it reads as a dial rather than a pie.
  const arc = circumference * 0.75
  const filled = (shown / 100) * arc
  const [from, to] = scoreGradient(target / 100)
  const gradientId = `gauge-${Math.round(target * 100)}`

  return (
    <div className="flex flex-col items-center">
      <div className="relative">
        <svg
          width={size}
          height={size}
          role="img"
          aria-label={`Score ${Math.round(target)} out of 100`}
          className="-rotate-[225deg]"
        >
          <defs>
            <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={from} />
              <stop offset="100%" stopColor={to} />
            </linearGradient>
          </defs>

          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#e2e8f0"
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={`${arc} ${circumference - arc}`}
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={`url(#${gradientId})`}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={`${filled} ${circumference - filled}`}
          />
        </svg>

        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="font-extrabold tabular-nums tracking-tight text-ink"
            style={{ fontSize: size * 0.28, lineHeight: 1 }}
          >
            {Math.round(shown)}
          </span>
          <span className="mt-1 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
            out of 100
          </span>
        </div>
      </div>

      {grade && (
        <div className="mt-3 flex items-center gap-2">
          <GradeBadge grade={grade} />
          <span className="text-sm font-medium text-muted">Grade</span>
        </div>
      )}
    </div>
  )
}

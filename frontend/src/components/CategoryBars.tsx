import type { CategoryScore } from '../types'
import { categoryStyle } from './common'

export function CategoryBars({ categories }: { categories: CategoryScore[] }) {
  return (
    <ul className="space-y-5">
      {categories.map((category, index) => {
        const fraction = category.max_score ? category.score / category.max_score : 0
        const style = categoryStyle(category.key)
        const { Icon } = style

        return (
          <li
            key={category.key}
            className="animate-fade-up"
            style={{ animationDelay: `${index * 60}ms` }}
          >
            <div className="mb-2 flex items-center gap-3">
              <span
                className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${style.gradient} text-white shadow-sm`}
              >
                <Icon className="h-4 w-4" />
              </span>

              <span className="flex-1 text-sm font-semibold text-slate-800">{category.label}</span>

              <span className="shrink-0 text-sm font-bold tabular-nums text-slate-700">
                {category.score}
                <span className="font-medium text-slate-400"> / {category.max_score}</span>
              </span>
            </div>

            <div className="ml-12 h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
              <div
                className={`h-full rounded-full bg-gradient-to-r ${style.gradient}`}
                style={{
                  width: `${Math.max(fraction * 100, 2)}%`,
                  transition: 'width 900ms cubic-bezier(.21,1.02,.73,1)',
                  transitionDelay: `${index * 60}ms`,
                }}
              />
            </div>

            {category.justification && (
              <p className="ml-12 mt-2 text-xs leading-relaxed text-muted">
                {category.justification}
              </p>
            )}
          </li>
        )
      })}
    </ul>
  )
}

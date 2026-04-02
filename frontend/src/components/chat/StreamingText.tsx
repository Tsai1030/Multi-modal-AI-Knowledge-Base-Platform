'use client'

import { cn } from '@/lib/utils'

interface StreamingTextProps {
  content: string
  className?: string
}

export function StreamingText({ content, className }: StreamingTextProps) {
  return (
    <span className={cn('font-mono text-sm', className)}>
      {content}
      <span className="ml-0.5 inline-block h-[1em] w-[2px] animate-pulse bg-current align-middle opacity-80" />
    </span>
  )
}

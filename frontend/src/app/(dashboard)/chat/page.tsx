import { MessageSquarePlus } from 'lucide-react'

export default function ChatDefaultPage() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
      <div className="flex size-14 items-center justify-center rounded-2xl border border-border bg-muted">
        <MessageSquarePlus className="size-7 text-muted-foreground" />
      </div>
      <div className="flex flex-col gap-1">
        <h2 className="text-base font-semibold">開始一段對話</h2>
        <p className="text-sm text-muted-foreground">
          從左側選擇已有對話，或點擊「新對話」開始
        </p>
      </div>
    </div>
  )
}

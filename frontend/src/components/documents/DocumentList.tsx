'use client'

import { useEffect, useState, useCallback } from 'react'
import { toast } from 'sonner'
import { Trash2, RefreshCw } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { documentApi } from '@/lib/api'
import type { Document, DocumentStatus } from '@/types/document'

const STATUS_CONFIG: Record<DocumentStatus, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
  pending: { label: '等待中', variant: 'secondary' },
  processing: { label: '處理中', variant: 'outline' },
  completed: { label: '完成', variant: 'default' },
  failed: { label: '失敗', variant: 'destructive' },
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

interface DocumentListProps {
  refreshTrigger: number
}

export function DocumentList({ refreshTrigger }: DocumentListProps) {
  const [docs, setDocs] = useState<Document[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [deleteTarget, setDeleteTarget] = useState<Document | null>(null)

  const load = useCallback(async () => {
    try {
      const data = await documentApi.list()
      setDocs(data.documents)
    } catch {
      toast.error('載入文件列表失敗')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load, refreshTrigger])

  // Poll processing docs every 3s
  useEffect(() => {
    const hasProcessing = docs.some((d) => d.status === 'processing' || d.status === 'pending')
    if (!hasProcessing) return
    const timer = setInterval(load, 3000)
    return () => clearInterval(timer)
  }, [docs, load])

  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      await documentApi.delete(deleteTarget.id)
      setDocs((prev) => prev.filter((d) => d.id !== deleteTarget.id))
      toast.success('文件已刪除')
    } catch {
      toast.error('刪除失敗')
    } finally {
      setDeleteTarget(null)
    }
  }

  if (isLoading) {
    return (
      <div className="flex flex-col gap-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full rounded-lg" />
        ))}
      </div>
    )
  }

  if (docs.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
        尚無文件，請上傳檔案
      </div>
    )
  }

  return (
    <>
      <div className="flex flex-col gap-2">
        {docs.map((doc) => {
          const status = STATUS_CONFIG[doc.status]
          const isProcessing = doc.status === 'processing' || doc.status === 'pending'

          return (
            <div
              key={doc.id}
              className="flex items-center gap-3 rounded-lg border border-border bg-card px-4 py-3"
            >
              <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                <div className="flex items-center gap-2">
                  <span className="truncate text-sm font-medium">{doc.title}</span>
                  <Badge variant={status.variant} className="shrink-0 text-xs">
                    {isProcessing && <RefreshCw className="mr-1 size-3 animate-spin" />}
                    {status.label}
                  </Badge>
                </div>
                <span className="text-xs text-muted-foreground">
                  {doc.filename} · {formatBytes(doc.file_size)} ·{' '}
                  {new Date(doc.created_at).toLocaleDateString('zh-TW')}
                </span>
              </div>
              <Button
                variant="ghost"
                className="size-8 shrink-0 p-0 text-muted-foreground hover:text-destructive"
                onClick={() => setDeleteTarget(doc)}
              >
                <Trash2 className="size-4" />
              </Button>
            </div>
          )
        })}
      </div>

      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>刪除文件</AlertDialogTitle>
            <AlertDialogDescription>
              確定刪除「{deleteTarget?.title}」？此操作無法復原。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              刪除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}

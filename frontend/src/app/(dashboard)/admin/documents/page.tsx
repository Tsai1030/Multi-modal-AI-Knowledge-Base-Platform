'use client'

import { useEffect, useState, useCallback } from 'react'
import { toast } from 'sonner'
import { Trash2, RefreshCw } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
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
import { adminApi, documentApi } from '@/lib/api'
import type { Document, DocumentStatus } from '@/types/document'

const STATUS_CONFIG: Record<DocumentStatus, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
  pending: { label: '等待中', variant: 'secondary' },
  processing: { label: '處理中', variant: 'outline' },
  completed: { label: '完成', variant: 'default' },
  failed: { label: '失敗', variant: 'destructive' },
}

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function AdminDocumentsPage() {
  const [docs, setDocs] = useState<Document[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [deleteTarget, setDeleteTarget] = useState<Document | null>(null)

  const load = useCallback(async () => {
    try {
      const data = await adminApi.listAllDocuments(0, 200)
      setDocs(data.documents)
    } catch {
      toast.error('載入文件列表失敗')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

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

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <div className="mx-auto w-full max-w-5xl flex-1 px-6 py-8">
        <div className="flex items-center justify-between pb-4">
          <div className="flex flex-col gap-1">
            <h1 className="text-lg font-semibold tracking-tight">所有文件</h1>
            <p className="text-sm text-muted-foreground">查看並管理所有用戶上傳的文件</p>
          </div>
          <Button variant="outline" className="gap-2" onClick={load}>
            <RefreshCw className="size-4" />
            重新整理
          </Button>
        </div>

        <Separator className="mb-6" />

        {isLoading ? (
          <div className="flex flex-col gap-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-14 w-full rounded-lg" />
            ))}
          </div>
        ) : docs.length === 0 ? (
          <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
            尚無文件
          </div>
        ) : (
          <div className="overflow-hidden rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">標題</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">檔名</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">大小</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">狀態</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">上傳時間</th>
                  <th className="px-4 py-3 text-right font-medium text-muted-foreground">操作</th>
                </tr>
              </thead>
              <tbody>
                {docs.map((doc, i) => {
                  const status = STATUS_CONFIG[doc.status]
                  const isProcessing = doc.status === 'processing' || doc.status === 'pending'
                  return (
                    <tr key={doc.id} className={`border-b border-border last:border-0 ${i % 2 === 0 ? '' : 'bg-muted/20'}`}>
                      <td className="max-w-[200px] truncate px-4 py-3 font-medium">{doc.title}</td>
                      <td className="max-w-[150px] truncate px-4 py-3 text-muted-foreground">{doc.filename}</td>
                      <td className="px-4 py-3 text-muted-foreground">{formatBytes(doc.file_size)}</td>
                      <td className="px-4 py-3">
                        <Badge variant={status.variant} className="gap-1 text-xs">
                          {isProcessing && <RefreshCw className="size-3 animate-spin" />}
                          {status.label}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {new Date(doc.created_at).toLocaleDateString('zh-TW')}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Button
                          variant="ghost"
                          className="size-8 p-0 text-muted-foreground hover:text-destructive"
                          onClick={() => setDeleteTarget(doc)}
                        >
                          <Trash2 className="size-4" />
                        </Button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
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
    </div>
  )
}

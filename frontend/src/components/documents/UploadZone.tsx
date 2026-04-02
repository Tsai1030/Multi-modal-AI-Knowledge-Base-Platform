'use client'

import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { toast } from 'sonner'
import { Upload, X } from 'lucide-react'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { documentApi } from '@/lib/api'
import { cn } from '@/lib/utils'

const ACCEPTED_TYPES = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
  'text/markdown': ['.md'],
  'text/plain': ['.txt'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/png': ['.png'],
}

const FORMAT_LABELS = ['PDF', 'DOCX', 'PPTX', 'XLSX', 'MD', 'TXT', 'JPG', 'PNG']

interface UploadingFile {
  name: string
  progress: number
  done: boolean
  error: boolean
}

interface UploadZoneProps {
  onUploaded: () => void
}

export function UploadZone({ onUploaded }: UploadZoneProps) {
  const [uploading, setUploading] = useState<UploadingFile[]>([])

  const onDrop = useCallback(
    async (files: File[]) => {
      if (!files.length) return

      const entries: UploadingFile[] = files.map((f) => ({
        name: f.name,
        progress: 0,
        done: false,
        error: false,
      }))
      setUploading(entries)

      await Promise.all(
        files.map(async (file, i) => {
          try {
            // Simulate progress with fake ticks while uploading
            const ticker = setInterval(() => {
              setUploading((prev) =>
                prev.map((u, idx) =>
                  idx === i && !u.done ? { ...u, progress: Math.min(u.progress + 15, 85) } : u
                )
              )
            }, 300)

            await documentApi.upload(file)
            clearInterval(ticker)
            setUploading((prev) =>
              prev.map((u, idx) => (idx === i ? { ...u, progress: 100, done: true } : u))
            )
            toast.success(`${file.name} 上傳成功`)
          } catch (err: unknown) {
            setUploading((prev) =>
              prev.map((u, idx) => (idx === i ? { ...u, error: true, done: true } : u))
            )
            const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '上傳失敗'
            toast.error(`${file.name}: ${msg}`)
          }
        })
      )

      onUploaded()
      setTimeout(() => setUploading([]), 2000)
    },
    [onUploaded]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    multiple: true,
  })

  return (
    <div className="flex flex-col gap-3">
      <div
        {...getRootProps()}
        className={cn(
          'flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-10 text-center transition-colors cursor-pointer',
          isDragActive
            ? 'border-foreground/40 bg-muted'
            : 'border-border hover:border-foreground/20 hover:bg-muted/40'
        )}
      >
        <input {...getInputProps()} />
        <Upload className="size-8 text-muted-foreground" />
        <div className="flex flex-col gap-1">
          <p className="text-sm font-medium">
            {isDragActive ? '放開以上傳' : '拖拉檔案至此，或點擊選擇'}
          </p>
          <p className="text-xs text-muted-foreground">支援多檔同時上傳</p>
        </div>
        <div className="flex flex-wrap justify-center gap-1.5">
          {FORMAT_LABELS.map((fmt) => (
            <Badge key={fmt} variant="secondary" className="text-xs">
              {fmt}
            </Badge>
          ))}
        </div>
      </div>

      {/* Upload progress list */}
      {uploading.length > 0 && (
        <div className="flex flex-col gap-2">
          {uploading.map((u, i) => (
            <div key={i} className="flex flex-col gap-1 rounded-lg border border-border p-3">
              <div className="flex items-center justify-between">
                <span className="truncate text-sm">{u.name}</span>
                <span
                  className={cn(
                    'text-xs',
                    u.error ? 'text-destructive' : u.done ? 'text-green-500' : 'text-muted-foreground'
                  )}
                >
                  {u.error ? '失敗' : u.done ? '完成' : `${u.progress}%`}
                </span>
              </div>
              {!u.error && <Progress value={u.progress} className="h-1" />}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

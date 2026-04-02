'use client'

import { useCallback, useState } from 'react'
import { Upload } from 'lucide-react'
import { useDropzone } from 'react-dropzone'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
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

      const entries: UploadingFile[] = files.map((file) => ({
        name: file.name,
        progress: 0,
        done: false,
        error: false,
      }))
      setUploading(entries)

      await Promise.all(
        files.map(async (file, index) => {
          let ticker: ReturnType<typeof setInterval> | null = null

          try {
            ticker = setInterval(() => {
              setUploading((prev) =>
                prev.map((item, itemIndex) =>
                  itemIndex === index && !item.done
                    ? { ...item, progress: Math.min(item.progress + 15, 85) }
                    : item
                )
              )
            }, 300)

            await documentApi.upload(file)

            if (ticker) clearInterval(ticker)
            setUploading((prev) =>
              prev.map((item, itemIndex) =>
                itemIndex === index ? { ...item, progress: 100, done: true } : item
              )
            )
            toast.success(`${file.name} 上傳成功`)
          } catch (error: unknown) {
            if (ticker) clearInterval(ticker)
            setUploading((prev) =>
              prev.map((item, itemIndex) =>
                itemIndex === index ? { ...item, error: true, done: true } : item
              )
            )

            const message =
              (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
              '上傳失敗'
            toast.error(`${file.name}: ${message}`)
          }
        })
      )

      onUploaded()
      window.setTimeout(() => setUploading([]), 2000)
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
          'cursor-pointer rounded-[1.75rem] border-2 border-dashed p-10 text-center transition-colors',
          'flex flex-col items-center justify-center gap-3',
          isDragActive
            ? 'border-foreground/40 bg-muted'
            : 'border-border hover:border-foreground/20 hover:bg-muted/40'
        )}
      >
        <input {...getInputProps()} />
        <div className="flex size-14 items-center justify-center rounded-2xl border border-border bg-background/80">
          <Upload className="text-muted-foreground" />
        </div>
        <div className="flex flex-col gap-1">
          <p className="text-sm font-medium">
            {isDragActive ? '放開以上傳檔案' : '拖曳檔案到這裡，或點擊選擇檔案'}
          </p>
          <p className="text-xs text-muted-foreground">
            支援 PDF、Office 文件、Markdown、文字與圖片格式
          </p>
        </div>
        <div className="flex flex-wrap justify-center gap-1.5">
          {FORMAT_LABELS.map((format) => (
            <Badge key={format} variant="secondary" className="text-xs">
              {format}
            </Badge>
          ))}
        </div>
      </div>

      {uploading.length > 0 && (
        <div className="flex flex-col gap-2">
          {uploading.map((item, index) => (
            <div
              key={`${item.name}-${index}`}
              className="flex flex-col gap-1 rounded-2xl border border-border/70 bg-card/80 p-3"
            >
              <div className="flex items-center justify-between gap-3">
                <span className="truncate text-sm">{item.name}</span>
                <span
                  className={cn(
                    'text-xs',
                    item.error
                      ? 'text-destructive'
                      : item.done
                        ? 'text-foreground'
                        : 'text-muted-foreground'
                  )}
                >
                  {item.error ? '失敗' : item.done ? '完成' : `${item.progress}%`}
                </span>
              </div>
              {!item.error && <Progress value={item.progress} className="h-1" />}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

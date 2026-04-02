'use client'

import { useState } from 'react'
import { DocumentList } from '@/components/documents/DocumentList'
import { UploadZone } from '@/components/documents/UploadZone'
import { Separator } from '@/components/ui/separator'

export default function DocumentsPage() {
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col px-6 py-8">
        <div className="flex flex-col gap-1 pb-4">
          <h1 className="text-lg font-semibold tracking-tight">文件庫</h1>
          <p className="text-sm text-muted-foreground">
            上傳並管理知識庫文件，系統會在背景完成解析與索引。
          </p>
        </div>

        <Separator className="mb-6" />

        <div className="flex flex-col gap-6">
          <UploadZone onUploaded={() => setRefreshTrigger((value) => value + 1)} />
          <div className="flex flex-col gap-3">
            <h2 className="text-sm font-medium text-muted-foreground">最近文件</h2>
            <DocumentList refreshTrigger={refreshTrigger} />
          </div>
        </div>
      </div>
    </div>
  )
}

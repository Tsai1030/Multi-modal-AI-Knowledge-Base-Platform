'use client'

import { useState } from 'react'
import { UploadZone } from '@/components/documents/UploadZone'
import { DocumentList } from '@/components/documents/DocumentList'
import { Separator } from '@/components/ui/separator'

export default function DocumentsPage() {
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <div className="mx-auto w-full max-w-3xl flex-1 px-6 py-8">
        <div className="flex flex-col gap-1 pb-4">
          <h1 className="text-lg font-semibold tracking-tight">文件庫</h1>
          <p className="text-sm text-muted-foreground">
            上傳文件至知識庫，AI 將從中擷取相關內容回答問題
          </p>
        </div>

        <Separator className="mb-6" />

        <div className="flex flex-col gap-6">
          <UploadZone onUploaded={() => setRefreshTrigger((n) => n + 1)} />
          <div className="flex flex-col gap-3">
            <h2 className="text-sm font-medium text-muted-foreground">已上傳文件</h2>
            <DocumentList refreshTrigger={refreshTrigger} />
          </div>
        </div>
      </div>
    </div>
  )
}

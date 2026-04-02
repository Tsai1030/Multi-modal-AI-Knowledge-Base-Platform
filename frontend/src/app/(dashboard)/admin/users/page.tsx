'use client'

import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Shield, ShieldOff, UserCheck, UserX } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { adminApi } from '@/lib/api'
import { useAuthStore } from '@/store/authStore'
import type { UserPublic } from '@/types/auth'

export default function AdminUsersPage() {
  const [users, setUsers] = useState<UserPublic[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const { user: currentUser } = useAuthStore()

  useEffect(() => {
    adminApi.listUsers()
      .then(setUsers)
      .catch(() => toast.error('載入用戶列表失敗'))
      .finally(() => setIsLoading(false))
  }, [])

  const handleToggleRole = async (u: UserPublic) => {
    const newRole = u.role === 'admin' ? 'user' : 'admin'
    try {
      const updated = await adminApi.updateRole(u.id, { role: newRole })
      setUsers((prev) => prev.map((x) => (x.id === u.id ? updated : x)))
      toast.success(`已將 ${u.full_name} 設為 ${newRole}`)
    } catch {
      toast.error('更新角色失敗')
    }
  }

  const handleToggleStatus = async (u: UserPublic) => {
    try {
      const updated = await adminApi.updateStatus(u.id, { is_active: !u.is_active })
      setUsers((prev) => prev.map((x) => (x.id === u.id ? updated : x)))
      toast.success(`帳號已${updated.is_active ? '啟用' : '停用'}`)
    } catch {
      toast.error('更新狀態失敗')
    }
  }

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl flex-1 px-6 py-8">
        <div className="flex flex-col gap-1 pb-4">
          <h1 className="text-lg font-semibold tracking-tight">用戶管理</h1>
          <p className="text-sm text-muted-foreground">管理所有用戶的角色與帳號狀態</p>
        </div>

        <Separator className="mb-6" />

        {isLoading ? (
          <div className="flex flex-col gap-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-14 w-full rounded-lg" />
            ))}
          </div>
        ) : (
          <div className="overflow-hidden rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">名稱</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Email</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">角色</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">狀態</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">加入時間</th>
                  <th className="px-4 py-3 text-right font-medium text-muted-foreground">操作</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u, i) => (
                  <tr
                    key={u.id}
                    className={`border-b border-border last:border-0 ${i % 2 === 0 ? '' : 'bg-muted/20'}`}
                  >
                    <td className="px-4 py-3 font-medium">{u.full_name}</td>
                    <td className="px-4 py-3 text-muted-foreground">{u.email}</td>
                    <td className="px-4 py-3">
                      <Badge variant={u.role === 'admin' ? 'default' : 'secondary'}>
                        {u.role === 'admin' ? 'Admin' : 'User'}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={u.is_active ? 'default' : 'destructive'}>
                        {u.is_active ? '啟用' : '停用'}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {new Date(u.created_at).toLocaleDateString('zh-TW')}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        {u.id !== currentUser?.id && (
                          <>
                            <Tooltip>
                              <TooltipTrigger
                                render={
                                  <Button
                                    variant="ghost"
                                    className="size-8 p-0"
                                    onClick={() => handleToggleRole(u)}
                                  />
                                }
                              >
                                {u.role === 'admin' ? (
                                  <ShieldOff className="size-4 text-muted-foreground" />
                                ) : (
                                  <Shield className="size-4 text-muted-foreground" />
                                )}
                              </TooltipTrigger>
                              <TooltipContent>
                                {u.role === 'admin' ? '降為一般用戶' : '提升為管理員'}
                              </TooltipContent>
                            </Tooltip>

                            <Tooltip>
                              <TooltipTrigger
                                render={
                                  <Button
                                    variant="ghost"
                                    className="size-8 p-0"
                                    onClick={() => handleToggleStatus(u)}
                                  />
                                }
                              >
                                {u.is_active ? (
                                  <UserX className="size-4 text-muted-foreground" />
                                ) : (
                                  <UserCheck className="size-4 text-muted-foreground" />
                                )}
                              </TooltipTrigger>
                              <TooltipContent>
                                {u.is_active ? '停用帳號' : '啟用帳號'}
                              </TooltipContent>
                            </Tooltip>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

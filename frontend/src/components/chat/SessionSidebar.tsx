'use client'

import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { toast } from 'sonner'
import {
  Plus,
  MessageSquare,
  FileText,
  Settings,
  LogOut,
  MoreHorizontal,
  Pencil,
  Trash2,
  Shield,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
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
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { useChatStore } from '@/store/chatStore'
import { useAuthStore } from '@/store/authStore'
import { cn } from '@/lib/utils'
import type { ChatSession } from '@/types/session'

const MODE_OPTIONS = [
  { value: 'hybrid', label: 'Hybrid' },
  { value: 'local', label: 'Local' },
  { value: 'global', label: 'Global' },
] as const

function formatRelativeTime(dateStr: string | null): string {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return '剛剛'
  if (mins < 60) return `${mins} 分鐘前`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} 小時前`
  return `${Math.floor(hours / 24)} 天前`
}

export function SessionSidebar() {
  const router = useRouter()
  const pathname = usePathname()
  const { sessions, loadSessions, createSession, deleteSession, renameSession } = useChatStore()
  const { user, logout } = useAuthStore()

  const [deleteTarget, setDeleteTarget] = useState<ChatSession | null>(null)
  const [renameTarget, setRenameTarget] = useState<ChatSession | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const [modeOpen, setModeOpen] = useState(false)

  useEffect(() => {
    loadSessions().catch(() => {})
  }, [loadSessions])

  const handleNewSession = async (mode: string) => {
    setModeOpen(false)
    try {
      const session = await createSession(mode)
      router.push(`/chat/${session.id}`)
    } catch {
      toast.error('建立對話失敗')
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      await deleteSession(deleteTarget.id)
      if (pathname.includes(deleteTarget.id)) router.push('/chat')
      toast.success('對話已刪除')
    } catch {
      toast.error('刪除失敗')
    } finally {
      setDeleteTarget(null)
    }
  }

  const handleRename = async () => {
    if (!renameTarget || !renameValue.trim()) return
    try {
      await renameSession(renameTarget.id, renameValue.trim())
      toast.success('已重新命名')
    } catch {
      toast.error('重新命名失敗')
    } finally {
      setRenameTarget(null)
    }
  }

  const handleLogout = async () => {
    await logout()
    router.push('/login')
  }

  const currentSessionId = pathname.match(/\/chat\/([^/]+)/)?.[1] ?? null

  return (
    <aside className="flex h-full w-64 flex-col bg-sidebar text-sidebar-foreground">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-4">
        <div className="flex size-6 items-center justify-center rounded bg-sidebar-foreground/10">
          <span className="font-mono text-xs font-bold text-sidebar-foreground">R</span>
        </div>
        <span className="truncate font-medium text-sm tracking-tight">RAG Platform</span>
      </div>

      <Separator className="bg-sidebar-border" />

      {/* New Chat Button */}
      <div className="px-3 py-3">
        <DropdownMenu open={modeOpen} onOpenChange={setModeOpen}>
          <DropdownMenuTrigger
            render={
              <Button
                variant="outline"
                className="w-full justify-start gap-2 border-sidebar-border bg-transparent text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              />
            }
          >
            <Plus data-icon="inline-start" className="size-4" />
            新對話
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-44">
            {MODE_OPTIONS.map((opt) => (
              <DropdownMenuItem key={opt.value} onSelect={() => handleNewSession(opt.value)}>
                {opt.label} 模式
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Session List */}
      <ScrollArea className="flex-1 px-2">
        <div className="flex flex-col gap-0.5 py-1">
          {sessions.length === 0 && (
            <p className="px-2 py-6 text-center text-xs text-sidebar-foreground/40">
              尚無對話記錄
            </p>
          )}
          {sessions.map((session) => {
            const isActive = session.id === currentSessionId
            return (
              <div
                key={session.id}
                className={cn(
                  'group relative flex items-center gap-2 rounded-md px-2 py-2 text-sm cursor-pointer transition-colors',
                  isActive
                    ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                    : 'text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground'
                )}
                onClick={() => router.push(`/chat/${session.id}`)}
              >
                <MessageSquare className="size-4 shrink-0 opacity-60" />
                <span className="flex-1 truncate">{session.title}</span>
                <div className="hidden group-hover:flex items-center">
                  <DropdownMenu>
                    <DropdownMenuTrigger
                      render={
                        <Button
                          variant="ghost"
                          className="size-6 p-0 text-sidebar-foreground/60 hover:text-sidebar-foreground"
                          onClick={(e) => e.stopPropagation()}
                        />
                      }
                    >
                      <MoreHorizontal className="size-3.5" />
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem
                        onSelect={() => {
                          setRenameTarget(session)
                          setRenameValue(session.title)
                        }}
                      >
                        <Pencil className="size-4" />
                        重新命名
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        className="text-destructive focus:text-destructive"
                        onSelect={() => setDeleteTarget(session)}
                      >
                        <Trash2 className="size-4" />
                        刪除
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
                {isActive && (
                  <span className="ml-auto text-xs opacity-40 group-hover:hidden">
                    {session.message_count}
                  </span>
                )}
              </div>
            )
          })}
        </div>
      </ScrollArea>

      <Separator className="bg-sidebar-border" />

      {/* Bottom Nav */}
      <nav className="flex flex-col gap-0.5 px-2 py-2">
        <NavItem
          href="/documents"
          icon={<FileText className="size-4" />}
          label="文件庫"
          active={pathname.startsWith('/documents')}
          onClick={() => router.push('/documents')}
        />
        {user?.role === 'admin' && (
          <NavItem
            href="/admin/users"
            icon={<Shield className="size-4" />}
            label="管理後台"
            active={pathname.startsWith('/admin')}
            onClick={() => router.push('/admin/users')}
          />
        )}
      </nav>

      <Separator className="bg-sidebar-border" />

      {/* User Footer */}
      <div className="flex items-center gap-2 px-3 py-3">
        <Avatar className="size-7 shrink-0">
          <AvatarFallback className="bg-sidebar-accent text-sidebar-accent-foreground text-xs">
            {user?.full_name?.[0]?.toUpperCase() ?? 'U'}
          </AvatarFallback>
        </Avatar>
        <div className="flex min-w-0 flex-1 flex-col">
          <span className="truncate text-xs font-medium text-sidebar-foreground">
            {user?.full_name}
          </span>
          <span className="truncate text-xs text-sidebar-foreground/50">{user?.email}</span>
        </div>
        <Tooltip>
          <TooltipTrigger
            render={
              <Button
                variant="ghost"
                className="size-7 p-0 text-sidebar-foreground/50 hover:text-sidebar-foreground"
                onClick={handleLogout}
              />
            }
          >
            <LogOut className="size-4" />
          </TooltipTrigger>
          <TooltipContent side="right">登出</TooltipContent>
        </Tooltip>
      </div>

      {/* Delete Confirm */}
      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>刪除對話</AlertDialogTitle>
            <AlertDialogDescription>
              確定刪除「{deleteTarget?.title}」？此操作無法復原。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              刪除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Rename Dialog */}
      <Dialog open={!!renameTarget} onOpenChange={(open) => !open && setRenameTarget(null)}>
        <DialogContent className="sm:max-w-xs">
          <DialogHeader>
            <DialogTitle>重新命名對話</DialogTitle>
          </DialogHeader>
          <Input
            value={renameValue}
            onChange={(e) => setRenameValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleRename()}
            autoFocus
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setRenameTarget(null)}>
              取消
            </Button>
            <Button onClick={handleRename} disabled={!renameValue.trim()}>
              儲存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </aside>
  )
}

function NavItem({
  icon,
  label,
  active,
  onClick,
}: {
  href: string
  icon: React.ReactNode
  label: string
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex w-full items-center gap-2 rounded-md px-2 py-2 text-sm transition-colors',
        active
          ? 'bg-sidebar-accent text-sidebar-accent-foreground'
          : 'text-sidebar-foreground/60 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground'
      )}
    >
      {icon}
      {label}
    </button>
  )
}

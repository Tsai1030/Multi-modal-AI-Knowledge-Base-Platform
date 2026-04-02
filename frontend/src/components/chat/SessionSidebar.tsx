'use client'

import { useEffect, useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import {
  ChevronLeft,
  ChevronRight,
  FileText,
  LogOut,
  MessageSquare,
  MoreHorizontal,
  Pencil,
  Plus,
  Shield,
  Trash2,
  X,
} from 'lucide-react'
import { toast } from 'sonner'
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
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/store/authStore'
import { useChatStore } from '@/store/chatStore'
import type { ChatSession } from '@/types/session'

const MODE_OPTIONS = [
  { value: 'hybrid', label: 'Hybrid' },
  { value: 'local', label: 'Local' },
  { value: 'global', label: 'Global' },
] as const

function formatRelativeTime(dateString: string | null): string {
  if (!dateString) return '尚未提問'

  const diffMs = Date.now() - new Date(dateString).getTime()
  const minutes = Math.floor(diffMs / 60000)
  if (minutes < 1) return '剛剛'
  if (minutes < 60) return `${minutes} 分鐘前`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} 小時前`

  return `${Math.floor(hours / 24)} 天前`
}

function useIsMobile() {
  const [isMobile, setIsMobile] = useState(false)
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 767px)')
    setIsMobile(mq.matches)
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])
  return isMobile
}

export function SessionSidebar() {
  const router = useRouter()
  const pathname = usePathname()
  const { sessions, loadSessions, createSession, deleteSession, renameSession } = useChatStore()
  const { user, logout } = useAuthStore()

  const isMobile = useIsMobile()
  const [collapsed, setCollapsed] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<ChatSession | null>(null)
  const [renameTarget, setRenameTarget] = useState<ChatSession | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const [modeOpen, setModeOpen] = useState(false)

  useEffect(() => {
    void loadSessions().catch(() => undefined)
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
      if (pathname.includes(deleteTarget.id)) {
        router.push('/chat')
      }
      toast.success('對話已刪除')
    } catch {
      toast.error('刪除對話失敗')
    } finally {
      setDeleteTarget(null)
    }
  }

  const handleRename = async () => {
    if (!renameTarget || !renameValue.trim()) return
    try {
      await renameSession(renameTarget.id, renameValue.trim())
      toast.success('對話名稱已更新')
    } catch {
      toast.error('更新名稱失敗')
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
    <>
      {/* Mobile backdrop */}
      {isMobile && !collapsed && (
        <div
          className="fixed inset-0 z-30 bg-black/40 md:hidden"
          onClick={() => setCollapsed(true)}
        />
      )}

      {/* Mobile open button — two-line hamburger, visible only when sidebar is hidden */}
      {isMobile && collapsed && (
        <button
          type="button"
          onClick={() => setCollapsed(false)}
          className="fixed left-3 top-4 z-50 flex size-9 flex-col items-start justify-center gap-1.5 rounded-lg border border-sidebar-border bg-sidebar px-2 shadow-md md:hidden"
          aria-label="開啟側欄"
        >
          <span className="h-0.5 w-5 rounded-full bg-sidebar-foreground" />
          <span className="h-0.5 w-3 rounded-full bg-sidebar-foreground" />
        </button>
      )}

      <aside
        className={cn(
          'flex h-full flex-col bg-sidebar text-sidebar-foreground',
          isMobile
            ? 'fixed inset-y-0 left-0 z-40 w-72 transition-transform duration-300 ease-in-out'
            : 'relative transition-[width] duration-300 ease-in-out',
          isMobile
            ? collapsed ? '-translate-x-full' : 'translate-x-0'
            : collapsed ? 'w-14' : 'w-72'
        )}
      >
      {/* Desktop toggle button */}
      {!isMobile && (
        <button
          type="button"
          onClick={() => setCollapsed((prev) => !prev)}
          className="absolute -right-3 top-5 z-10 flex size-6 items-center justify-center rounded-full border border-sidebar-border bg-sidebar text-sidebar-foreground/60 shadow-sm transition hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
          aria-label={collapsed ? '展開側欄' : '收合側欄'}
        >
          {collapsed ? <ChevronRight className="size-3.5" /> : <ChevronLeft className="size-3.5" />}
        </button>
      )}

      {/* Header */}
      <div className={cn('flex items-center gap-3 px-3 py-4', collapsed && 'justify-center px-0')}>
        <div className="flex size-8 shrink-0 items-center justify-center rounded-2xl bg-sidebar-accent text-sm font-semibold text-sidebar-accent-foreground">
          R
        </div>
        {!collapsed && (
          <div className="min-w-0 flex-1 overflow-hidden">
            <p className="truncate text-sm font-medium">RAG Platform</p>
            <p className="truncate text-xs text-sidebar-foreground/50">Knowledge Workspace</p>
          </div>
        )}
        {/* Mobile close button */}
        {isMobile && !collapsed && (
          <button
            type="button"
            onClick={() => setCollapsed(true)}
            className="ml-auto flex size-8 shrink-0 items-center justify-center rounded-lg text-sidebar-foreground/60 transition hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
            aria-label="收合側欄"
          >
            <X className="size-4" />
          </button>
        )}
      </div>

      <Separator className="bg-sidebar-border" />

      {/* New session button */}
      <div className={cn('px-3 py-3', collapsed && 'flex justify-center px-2')}>
        {collapsed ? (
          <Tooltip>
            <DropdownMenu open={modeOpen} onOpenChange={setModeOpen}>
              <TooltipTrigger
                render={
                  <DropdownMenuTrigger
                    render={
                      <Button
                        variant="outline"
                        size="icon"
                        className="size-9 border-sidebar-border bg-transparent text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                      />
                    }
                  />
                }
              >
                <Plus className="size-4" />
              </TooltipTrigger>
              <DropdownMenuContent align="start" className="w-44">
                {MODE_OPTIONS.map((option) => (
                  <DropdownMenuItem
                    key={option.value}
                    onClick={() => void handleNewSession(option.value)}
                  >
                    {option.label}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
            <TooltipContent side="right">新對話</TooltipContent>
          </Tooltip>
        ) : (
          <DropdownMenu open={modeOpen} onOpenChange={setModeOpen}>
            <DropdownMenuTrigger
              render={
                <Button
                  variant="outline"
                  className="w-full justify-start gap-2 border-sidebar-border bg-transparent text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                />
              }
            >
              <Plus data-icon="inline-start" />
              新對話
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-44">
              {MODE_OPTIONS.map((option) => (
                <DropdownMenuItem
                  key={option.value}
                  onClick={() => void handleNewSession(option.value)}
                >
                  {option.label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>

      {/* Session list */}
      <ScrollArea className="flex-1 px-2">
        <div className="flex flex-col gap-1 py-2">
          {!collapsed && sessions.length === 0 && (
            <div className="rounded-2xl border border-sidebar-border bg-sidebar-accent/40 px-3 py-4 text-center text-xs text-sidebar-foreground/55">
              尚未建立任何對話
            </div>
          )}

          {sessions.map((session) => {
            const isActive = session.id === currentSessionId

            if (collapsed) {
              return (
                <Tooltip key={session.id}>
                  <TooltipTrigger
                    render={
                      <button
                        type="button"
                        onClick={() => router.push(`/chat/${session.id}`)}
                        className={cn(
                          'flex w-full items-center justify-center rounded-xl p-2 transition',
                          isActive
                            ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                            : 'text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground'
                        )}
                      />
                    }
                  >
                    <MessageSquare className="size-4 shrink-0" />
                  </TooltipTrigger>
                  <TooltipContent side="right" className="max-w-48">
                    <p className="text-xs font-medium">{session.title}</p>
                    <p className="text-xs opacity-60">{formatRelativeTime(session.last_message_at)}</p>
                  </TooltipContent>
                </Tooltip>
              )
            }

            return (
              <div
                key={session.id}
                className={cn(
                  'group cursor-pointer rounded-2xl px-3 py-3 transition',
                  isActive
                    ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                    : 'hover:bg-sidebar-accent/60'
                )}
                onClick={() => router.push(`/chat/${session.id}`)}
              >
                <div className="flex items-start gap-2">
                  <MessageSquare className="mt-0.5 shrink-0 opacity-70" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start gap-2">
                      <span className="truncate text-sm font-medium">{session.title}</span>
                      <DropdownMenu>
                        <DropdownMenuTrigger
                          render={
                            <Button
                              variant="ghost"
                              className="ml-auto hidden size-7 p-0 text-sidebar-foreground/55 hover:text-sidebar-foreground group-hover:flex"
                              onClick={(event) => event.stopPropagation()}
                            />
                          }
                        >
                          <MoreHorizontal />
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            onClick={() => {
                              setRenameTarget(session)
                              setRenameValue(session.title)
                            }}
                          >
                            <Pencil />
                            重新命名
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-destructive focus:text-destructive"
                            onClick={() => setDeleteTarget(session)}
                          >
                            <Trash2 />
                            刪除
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                    <div className="mt-1 flex items-center justify-between gap-3 text-xs text-sidebar-foreground/55">
                      <span>{session.query_mode}</span>
                      <span>{formatRelativeTime(session.last_message_at)}</span>
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </ScrollArea>

      <Separator className="bg-sidebar-border" />

      {/* Nav items */}
      <nav className="flex flex-col gap-1 px-2 py-2">
        <NavItem
          label="文件庫"
          icon={<FileText />}
          active={pathname.startsWith('/documents')}
          collapsed={collapsed}
          onClick={() => router.push('/documents')}
        />
        {user?.role === 'admin' && (
          <NavItem
            label="管理後台"
            icon={<Shield />}
            active={pathname.startsWith('/admin')}
            collapsed={collapsed}
            onClick={() => router.push('/admin/users')}
          />
        )}
      </nav>

      <Separator className="bg-sidebar-border" />

      {/* User section */}
      <div className={cn('flex items-center gap-2 px-3 py-3', collapsed && 'justify-center px-2')}>
        <Tooltip>
          <TooltipTrigger render={<span className="shrink-0" />}>
            <Avatar className="size-8 cursor-default">
              <AvatarFallback className="bg-sidebar-accent text-sidebar-accent-foreground text-xs">
                {user?.full_name?.[0]?.toUpperCase() ?? 'U'}
              </AvatarFallback>
            </Avatar>
          </TooltipTrigger>
          {collapsed && (
            <TooltipContent side="right">
              <p className="text-xs font-medium">{user?.full_name}</p>
              <p className="text-xs opacity-60">{user?.email}</p>
            </TooltipContent>
          )}
        </Tooltip>

        {!collapsed && (
          <>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-medium">{user?.full_name}</p>
              <p className="truncate text-xs text-sidebar-foreground/50">{user?.email}</p>
            </div>
            <Tooltip>
              <TooltipTrigger
                render={
                  <Button
                    variant="ghost"
                    className="size-8 p-0 text-sidebar-foreground/55 hover:text-sidebar-foreground"
                    onClick={handleLogout}
                  />
                }
              >
                <LogOut />
              </TooltipTrigger>
              <TooltipContent side="right">登出</TooltipContent>
            </Tooltip>
          </>
        )}

        {collapsed && (
          <Tooltip>
            <TooltipTrigger
              render={
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-8 text-sidebar-foreground/55 hover:text-sidebar-foreground"
                  onClick={handleLogout}
                />
              }
            >
              <LogOut className="size-4" />
            </TooltipTrigger>
            <TooltipContent side="right">登出</TooltipContent>
          </Tooltip>
        )}
      </div>

      {/* Dialogs */}
      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>刪除對話</AlertDialogTitle>
            <AlertDialogDescription>
              確定要刪除「{deleteTarget?.title}」嗎？所有訊息紀錄都會一併移除。
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

      <Dialog open={!!renameTarget} onOpenChange={(open) => !open && setRenameTarget(null)}>
        <DialogContent className="sm:max-w-xs">
          <DialogHeader>
            <DialogTitle>重新命名對話</DialogTitle>
          </DialogHeader>
          <Input
            value={renameValue}
            onChange={(event) => setRenameValue(event.target.value)}
            onKeyDown={(event) => event.key === 'Enter' && void handleRename()}
            autoFocus
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setRenameTarget(null)}>
              取消
            </Button>
            <Button onClick={() => void handleRename()} disabled={!renameValue.trim()}>
              儲存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </aside>
    </>
  )
}

function NavItem({
  icon,
  label,
  active,
  collapsed,
  onClick,
}: {
  icon: React.ReactNode
  label: string
  active: boolean
  collapsed: boolean
  onClick: () => void
}) {
  if (collapsed) {
    return (
      <Tooltip>
        <TooltipTrigger
          render={
            <button
              type="button"
              onClick={onClick}
              className={cn(
                'flex w-full items-center justify-center rounded-xl p-2 transition',
                active
                  ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                  : 'text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground'
              )}
            />
          }
        >
          {icon}
        </TooltipTrigger>
        <TooltipContent side="right">{label}</TooltipContent>
      </Tooltip>
    )
  }

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm transition',
        active
          ? 'bg-sidebar-accent text-sidebar-accent-foreground'
          : 'text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground'
      )}
    >
      {icon}
      {label}
    </button>
  )
}

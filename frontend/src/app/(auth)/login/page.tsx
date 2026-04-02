'use client'

import { Suspense, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Field, FieldLabel, FieldError } from '@/components/ui/field'
import { authApi } from '@/lib/api'
import { useAuthStore } from '@/store/authStore'

interface LoginForm {
  email: string
  password: string
}

function LoginForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { setAuth } = useAuthStore()
  const [isLoading, setIsLoading] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>()

  const onSubmit = async (data: LoginForm) => {
    setIsLoading(true)
    try {
      const tokenData = await authApi.login(data)
      await fetch('/api/auth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: tokenData.access_token }),
      })
      const meRes = await fetch('/api/auth/me', { cache: 'no-store' })
      const { user, token } = await meRes.json()
      setAuth(user, token)

      const next = searchParams.get('next') ?? '/chat'
      router.push(next)
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        '登入失敗，請確認帳號密碼'
      toast.error(message)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Card className="w-full max-w-sm border-border/60">
      <CardHeader className="space-y-1">
        <CardTitle className="text-xl font-semibold tracking-tight">登入</CardTitle>
        <CardDescription className="text-muted-foreground">
          輸入您的帳號密碼以繼續
        </CardDescription>
      </CardHeader>

      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent className="flex flex-col gap-4">
          <Field data-invalid={!!errors.email}>
            <FieldLabel htmlFor="email">電子郵件</FieldLabel>
            <Input
              id="email"
              type="email"
              placeholder="you@example.com"
              autoComplete="email"
              aria-invalid={!!errors.email}
              {...register('email', {
                required: '請輸入電子郵件',
                pattern: { value: /\S+@\S+\.\S+/, message: '格式不正確' },
              })}
            />
            {errors.email && <FieldError>{errors.email.message}</FieldError>}
          </Field>

          <Field data-invalid={!!errors.password}>
            <FieldLabel htmlFor="password">密碼</FieldLabel>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              autoComplete="current-password"
              aria-invalid={!!errors.password}
              {...register('password', { required: '請輸入密碼' })}
            />
            {errors.password && <FieldError>{errors.password.message}</FieldError>}
          </Field>
        </CardContent>

        <CardFooter className="flex flex-col gap-3">
          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading && <Loader2 data-icon="inline-start" className="animate-spin" />}
            {isLoading ? '登入中…' : '登入'}
          </Button>
          <p className="text-center text-sm text-muted-foreground">
            還沒有帳號？{' '}
            <Link href="/signup" className="text-foreground underline underline-offset-4 hover:opacity-80">
              立即註冊
            </Link>
          </p>
        </CardFooter>
      </form>
    </Card>
  )
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  )
}

'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
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

interface SignupForm {
  full_name: string
  email: string
  password: string
}

export default function SignupPage() {
  const router = useRouter()
  const { setAuth } = useAuthStore()
  const [isLoading, setIsLoading] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm<SignupForm>()

  const password = watch('password', '')

  const getPasswordStrength = (pw: string) => {
    if (!pw) return null
    if (pw.length < 6) return { label: '太短', color: 'text-destructive' }
    if (pw.length < 8 || !/[0-9]/.test(pw) || !/[a-zA-Z]/.test(pw))
      return { label: '普通', color: 'text-yellow-500' }
    return { label: '強', color: 'text-green-500' }
  }

  const strength = getPasswordStrength(password)

  const onSubmit = async (data: SignupForm) => {
    setIsLoading(true)
    try {
      await authApi.signup(data)
      // Auto-login after signup
      const tokenData = await authApi.login({ email: data.email, password: data.password })
      await fetch('/api/auth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: tokenData.access_token }),
      })
      const meRes = await fetch('/api/auth/me', { cache: 'no-store' })
      const { user, token } = await meRes.json()
      setAuth(user, token)
      router.push('/chat')
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        '註冊失敗，請稍後再試'
      toast.error(message)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Card className="w-full max-w-sm border-border/60">
      <CardHeader className="space-y-1">
        <CardTitle className="text-xl font-semibold tracking-tight">建立帳號</CardTitle>
        <CardDescription className="text-muted-foreground">
          填寫以下資訊以建立您的帳號
        </CardDescription>
      </CardHeader>

      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent className="flex flex-col gap-4">
          <Field data-invalid={!!errors.full_name}>
            <FieldLabel htmlFor="full_name">姓名</FieldLabel>
            <Input
              id="full_name"
              placeholder="您的名字"
              aria-invalid={!!errors.full_name}
              {...register('full_name', { required: '請輸入姓名' })}
            />
            {errors.full_name && <FieldError>{errors.full_name.message}</FieldError>}
          </Field>

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
            <FieldLabel htmlFor="password">
              <span>密碼</span>
              {strength && (
                <span className={`ml-2 text-xs font-normal ${strength.color}`}>
                  強度：{strength.label}
                </span>
              )}
            </FieldLabel>
            <Input
              id="password"
              type="password"
              placeholder="至少 8 字元，含字母與數字"
              autoComplete="new-password"
              aria-invalid={!!errors.password}
              {...register('password', {
                required: '請輸入密碼',
                minLength: { value: 8, message: '至少 8 個字元' },
                validate: {
                  hasLetter: (v) => /[a-zA-Z]/.test(v) || '需包含英文字母',
                  hasNumber: (v) => /[0-9]/.test(v) || '需包含數字',
                },
              })}
            />
            {errors.password && <FieldError>{errors.password.message}</FieldError>}
          </Field>
        </CardContent>

        <CardFooter className="flex flex-col gap-3">
          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading && <Loader2 data-icon="inline-start" className="animate-spin" />}
            {isLoading ? '建立中…' : '建立帳號'}
          </Button>
          <p className="text-center text-sm text-muted-foreground">
            已有帳號？{' '}
            <Link href="/login" className="text-foreground underline underline-offset-4 hover:opacity-80">
              前往登入
            </Link>
          </p>
        </CardFooter>
      </form>
    </Card>
  )
}

'use client'

import Link from 'next/link'
import BlurText from '@/components/BlurText'
import Galaxy from '@/components/Galaxy'

export default function LandingPage() {
  return (
    <div className="relative h-screen w-full overflow-hidden bg-black">
      <div className="absolute inset-0">
        <Galaxy
          transparent={false}
          mouseRepulsion={false}
          hueShift={200}
          density={1.2}
          glowIntensity={0.4}
          twinkleIntensity={0.5}
          rotationSpeed={0.03}
          speed={0.6}
        />
      </div>

      <div className="relative z-10 flex h-full flex-col items-center justify-center px-4">
        <section className="flex flex-col items-center gap-8 text-center">
          <div className="flex flex-col items-center gap-1">
            <BlurText
              text="Multi-modal AI"
              delay={120}
              animateBy="words"
              direction="top"
              className="justify-center text-4xl font-bold tracking-tight text-white sm:text-5xl"
            />
            <BlurText
              text="Knowledge Base Platform"
              delay={120}
              animateBy="words"
              direction="top"
              stepDuration={0.4}
              className="justify-center text-4xl font-bold tracking-tight text-white sm:text-5xl"
              animationFrom={{ filter: 'blur(10px)', opacity: 0, y: -50 }}
            />
          </div>

          <div className="flex gap-4">
            <Link
              href="/login"
              className="flex h-11 items-center justify-center rounded-2xl border border-white/40 px-8 text-sm font-medium text-white backdrop-blur-sm transition hover:bg-white/10"
            >
              登入
            </Link>
            <Link
              href="/signup"
              className="flex h-11 items-center justify-center rounded-2xl bg-white px-8 text-sm font-medium text-black transition hover:bg-white/90"
            >
              註冊
            </Link>
          </div>
        </section>
      </div>
    </div>
  )
}

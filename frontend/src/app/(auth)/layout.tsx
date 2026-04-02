'use client'

import Galaxy from '@/components/Galaxy'

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative flex min-h-full items-center justify-center overflow-hidden bg-black px-4">
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
      <div className="relative z-10 w-full max-w-sm">
        {children}
      </div>
    </div>
  )
}

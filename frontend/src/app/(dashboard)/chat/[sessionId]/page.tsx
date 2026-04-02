import { ChatWindow } from '@/components/chat/ChatWindow'

interface PageProps {
  params: Promise<{ sessionId: string }>
}

export default async function SessionPage({ params }: PageProps) {
  const { sessionId } = await params
  return <ChatWindow sessionId={sessionId} queryMode="hybrid" />
}

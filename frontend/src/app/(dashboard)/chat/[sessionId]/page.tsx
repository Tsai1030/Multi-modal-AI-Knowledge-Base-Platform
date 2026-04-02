import { ChatWindow } from '@/components/chat/ChatWindow'

export default async function ChatSessionPage({
  params,
}: {
  params: Promise<{ sessionId: string }>
}) {
  const { sessionId } = await params
  return <ChatWindow sessionId={sessionId} />
}

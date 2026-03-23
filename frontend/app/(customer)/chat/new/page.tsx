'use client'

import React, { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useConversations } from '@/hooks/useConversations'
import { PageLoader } from '@/components/ui/LoadingSpinner'

export default function NewChatPage() {
  const router = useRouter()
  const { createConversation } = useConversations()

  useEffect(() => {
    const create = async () => {
      try {
        const conv = await createConversation()
        router.replace(`/chat/${conv.id}`)
      } catch {
        router.replace('/chat')
      }
    }
    create()
  }, [createConversation, router])

  return <PageLoader label="Creating new conversation..." />
}

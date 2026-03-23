'use client'

import { useState, useCallback, useEffect } from 'react'
import { Conversation, ConversationDetail, Message } from '@/types'
import { conversationsApi, messagesApi } from '@/lib/api'

export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchConversations = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await conversationsApi.list()
      setConversations(data)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load conversations'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchConversations()
  }, [fetchConversations])

  const createConversation = useCallback(
    async (subject?: string): Promise<Conversation> => {
      const conv = await conversationsApi.create({ subject, channel: 'web' })
      setConversations((prev) => [conv, ...prev])
      return conv
    },
    []
  )

  const sendMessage = useCallback(
    async (
      conversationId: string,
      content: string
    ): Promise<{ user_message: Message; ai_message: Message }> => {
      return messagesApi.send(conversationId, content)
    },
    []
  )

  const deleteConversation = useCallback(async (id: string) => {
    await conversationsApi.delete(id)
    setConversations((prev) => prev.filter((c) => c.id !== id))
  }, [])

  return {
    conversations,
    loading,
    error,
    fetchConversations,
    createConversation,
    sendMessage,
    deleteConversation,
  }
}

export function useConversationDetail(id: string) {
  const [conversation, setConversation] = useState<ConversationDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchConversation = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      const data = await conversationsApi.getById(id)
      setConversation(data)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load conversation'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    fetchConversation()
  }, [fetchConversation])

  const addMessages = useCallback((userMsg: Message, aiMsg: Message) => {
    setConversation((prev) => {
      if (!prev) return prev
      return {
        ...prev,
        messages: [...prev.messages, userMsg, aiMsg],
      }
    })
  }, [])

  return { conversation, loading, error, fetchConversation, addMessages }
}

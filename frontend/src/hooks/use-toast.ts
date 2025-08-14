import { useState, useCallback } from 'react'

export interface Toast {
  id: string
  title?: string
  description?: string
  action?: React.ReactElement
  variant?: 'default' | 'destructive'
}

export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([])

  const toast = useCallback(
    ({
      title,
      description,
      action,
      variant = 'default',
      ...props
    }: Omit<Toast, 'id'>) => {
      const id = Math.random().toString(36).substr(2, 9)
      const newToast: Toast = {
        id,
        title,
        description,
        action,
        variant,
        ...props,
      }

      setToasts((prevToasts) => [...prevToasts, newToast])

      // Auto-dismiss after 5 seconds
      setTimeout(() => {
        setToasts((prevToasts) => prevToasts.filter((t) => t.id !== id))
      }, 5000)

      return id
    },
    []
  )

  const dismiss = useCallback((toastId?: string) => {
    if (toastId) {
      setToasts((prevToasts) => prevToasts.filter((t) => t.id !== toastId))
    } else {
      setToasts([])
    }
  }, [])

  return {
    toasts,
    toast,
    dismiss,
  }
}
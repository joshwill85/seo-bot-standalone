import { createContext, useContext, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '@/lib/supabase'
import type { User, Session } from '@supabase/supabase-js'
import type { AuthUser } from '@/types'

interface AuthContextType {
  user: AuthUser | null
  session: Session | null
  loading: boolean
  signIn: (email: string, password: string) => Promise<{ user?: AuthUser; error?: string }>
  signUp: (data: {
    email: string
    password: string
    firstName: string
    lastName: string
    phone?: string
  }) => Promise<{ user?: AuthUser; error?: string }>
  signOut: () => Promise<void>
  isAdmin: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      if (session?.user) {
        fetchUserProfile(session.user)
      } else {
        setLoading(false)
      }
    })

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (_event, session) => {
      setSession(session)
      
      if (session?.user) {
        await fetchUserProfile(session.user)
      } else {
        setUser(null)
        setLoading(false)
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  const fetchUserProfile = async (_authUser: User) => {
    try {
      // Call our Edge Function to get user profile
      const response = await fetch('/api/auth/profile', {
        headers: {
          'Authorization': `Bearer ${(await supabase.auth.getSession()).data.session?.access_token}`,
          'Content-Type': 'application/json',
        },
      })

      if (response.ok) {
        const { user: userData } = await response.json()
        setUser({
          id: userData.id.toString(),
          email: userData.email,
          firstName: userData.first_name,
          lastName: userData.last_name,
          role: userData.role,
          isActive: userData.is_active,
          emailVerified: userData.email_verified,
          createdAt: userData.created_at,
          lastLogin: userData.last_login,
        })
      } else {
        console.error('Failed to fetch user profile')
        await supabase.auth.signOut()
      }
    } catch (error) {
      console.error('Error fetching user profile:', error)
      await supabase.auth.signOut()
    } finally {
      setLoading(false)
    }
  }

  const signIn = async (email: string, password: string) => {
    try {
      setLoading(true)
      
      // Demo admin login for development
      if (email.toLowerCase() === 'admin@demo.com' && password === 'admin123') {
        const demoAdminUser: AuthUser = {
          id: 'admin-demo',
          email: 'admin@demo.com',
          firstName: 'Demo',
          lastName: 'Admin',
          role: 'admin' as const,
          isActive: true,
          emailVerified: true,
          createdAt: new Date().toISOString(),
          lastLogin: new Date().toISOString(),
        }
        setUser(demoAdminUser)
        navigate('/admin')
        return { user: demoAdminUser }
      }

      // Demo business owner login
      if (email.toLowerCase() === 'demo@business.com' && password === 'demo123') {
        const demoBusinessUser: AuthUser = {
          id: 'business-demo',
          email: 'demo@business.com',
          firstName: 'Demo',
          lastName: 'Business',
          role: 'business_owner' as const,
          isActive: true,
          emailVerified: true,
          createdAt: new Date().toISOString(),
          lastLogin: new Date().toISOString(),
        }
        setUser(demoBusinessUser)
        navigate('/dashboard')
        return { user: demoBusinessUser }
      }
      
      const { data, error } = await supabase.auth.signInWithPassword({
        email: email.toLowerCase(),
        password,
      })

      if (error) {
        return { error: error.message }
      }

      if (data.user) {
        await fetchUserProfile(data.user)
        navigate('/dashboard')
        return { user: user || undefined }
      }

      return { error: 'Login failed' }
    } catch (error) {
      return { error: 'An unexpected error occurred' }
    } finally {
      setLoading(false)
    }
  }

  const signUp = async (data: {
    email: string
    password: string
    firstName: string
    lastName: string
    phone?: string
  }) => {
    try {
      setLoading(true)

      // Call our Edge Function for registration
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: data.email.toLowerCase(),
          password: data.password,
          first_name: data.firstName,
          last_name: data.lastName,
          phone: data.phone,
        }),
      })

      const result = await response.json()

      if (!response.ok) {
        return { error: result.error || 'Registration failed' }
      }

      // Sign in the user after successful registration
      const signInResult = await signIn(data.email, data.password)
      return signInResult
    } catch (error) {
      return { error: 'An unexpected error occurred' }
    } finally {
      setLoading(false)
    }
  }

  const signOut = async () => {
    try {
      setLoading(true)
      await supabase.auth.signOut()
      setUser(null)
      setSession(null)
      navigate('/')
    } catch (error) {
      console.error('Error signing out:', error)
    } finally {
      setLoading(false)
    }
  }

  const isAdmin = user?.role === 'admin'

  const value = {
    user,
    session,
    loading,
    signIn,
    signUp,
    signOut,
    isAdmin,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
import { serve } from 'https://deno.land/std@0.208.0/http/server.ts'
import { createDatabaseClient } from '../_shared/database.ts'
import { validateUserRegistration } from '../_shared/validation.ts'
import { handleCors, createResponse, createErrorResponse } from '../_shared/cors.ts'
import { AppError } from '../_shared/types.ts'

serve(async (req) => {
  const origin = req.headers.get('Origin')

  // Handle CORS
  if (req.method === 'OPTIONS') {
    return new Response(null, { status: 200, headers: handleCors(req) })
  }

  try {
    const url = new URL(req.url)
    const path = url.pathname.split('/').pop()

    switch (path) {
      case 'register':
        return await handleRegister(req, origin)
      case 'login':
        return await handleLogin(req, origin)
      case 'profile':
        return await handleProfile(req, origin)
      default:
        return createErrorResponse('Not found', 404, origin)
    }
  } catch (error) {
    console.error('Auth function error:', error)
    
    if (error instanceof AppError) {
      return createErrorResponse(error.message, error.statusCode, origin, error.details)
    }
    
    return createErrorResponse('Internal server error', 500, origin)
  }
})

async function handleRegister(req: Request, origin?: string) {
  if (req.method !== 'POST') {
    return createErrorResponse('Method not allowed', 405, origin)
  }

  const data = await req.json()
  
  // Validate input
  validateUserRegistration(data)

  const supabase = createDatabaseClient()

  // Check if user already exists
  const { data: existingUser } = await supabase
    .from('users')
    .select('id')
    .eq('email', data.email.toLowerCase())
    .single()

  if (existingUser) {
    return createErrorResponse('Email already registered', 400, origin)
  }

  // Create auth user
  const { data: authUser, error: authError } = await supabase.auth.admin.createUser({
    email: data.email.toLowerCase(),
    password: data.password,
    email_confirm: true,
  })

  if (authError) {
    throw new AppError(`Registration failed: ${authError.message}`, 'REGISTRATION_ERROR', 400)
  }

  // Create user record
  const { data: user, error: userError } = await supabase
    .from('users')
    .insert({
      id: parseInt(authUser.user.id),
      email: data.email.toLowerCase(),
      password_hash: '', // We use Supabase Auth for password management
      first_name: data.first_name,
      last_name: data.last_name,
      phone: data.phone || null,
      role: 'business_owner',
      is_active: true,
      email_verified: true,
    })
    .select()
    .single()

  if (userError) {
    // Clean up auth user if database insert fails
    await supabase.auth.admin.deleteUser(authUser.user.id)
    throw new AppError(`User creation failed: ${userError.message}`, 'USER_CREATION_ERROR', 500)
  }

  // Generate session
  const { data: session, error: sessionError } = await supabase.auth.admin.generateLink({
    type: 'magiclink',
    email: data.email.toLowerCase(),
  })

  if (sessionError) {
    throw new AppError(`Session creation failed: ${sessionError.message}`, 'SESSION_ERROR', 500)
  }

  return createResponse({
    message: 'User registered successfully',
    user: {
      id: user.id,
      email: user.email,
      first_name: user.first_name,
      last_name: user.last_name,
      role: user.role,
    },
  }, 201, origin)
}

async function handleLogin(req: Request, origin?: string) {
  if (req.method !== 'POST') {
    return createErrorResponse('Method not allowed', 405, origin)
  }

  const { email, password } = await req.json()

  if (!email || !password) {
    return createErrorResponse('Email and password required', 400, origin)
  }

  const supabase = createDatabaseClient()

  // Authenticate with Supabase Auth
  const { data: authData, error: authError } = await supabase.auth.signInWithPassword({
    email: email.toLowerCase(),
    password,
  })

  if (authError) {
    return createErrorResponse('Invalid email or password', 401, origin)
  }

  // Get user details from our database
  const { data: user, error: userError } = await supabase
    .from('users')
    .select('*')
    .eq('id', authData.user.id)
    .single()

  if (userError || !user) {
    return createErrorResponse('User not found', 404, origin)
  }

  if (!user.is_active) {
    return createErrorResponse('Account is deactivated', 401, origin)
  }

  // Update last login
  await supabase
    .from('users')
    .update({ last_login: new Date().toISOString() })
    .eq('id', user.id)

  return createResponse({
    message: 'Login successful',
    user: {
      id: user.id,
      email: user.email,
      first_name: user.first_name,
      last_name: user.last_name,
      role: user.role,
      is_active: user.is_active,
      email_verified: user.email_verified,
    },
    session: authData.session,
  }, 200, origin)
}

async function handleProfile(req: Request, origin?: string) {
  if (req.method !== 'GET') {
    return createErrorResponse('Method not allowed', 405, origin)
  }

  const authHeader = req.headers.get('Authorization')
  if (!authHeader?.startsWith('Bearer ')) {
    return createErrorResponse('Missing authorization header', 401, origin)
  }

  const token = authHeader.substring(7)
  const supabase = createDatabaseClient()

  // Verify token and get user
  const { data: { user: authUser }, error: authError } = await supabase.auth.getUser(token)

  if (authError || !authUser) {
    return createErrorResponse('Invalid token', 401, origin)
  }

  // Get user details from our database
  const { data: user, error: userError } = await supabase
    .from('users')
    .select('id, email, first_name, last_name, phone, role, is_active, email_verified, created_at, last_login')
    .eq('id', authUser.id)
    .single()

  if (userError || !user) {
    return createErrorResponse('User not found', 404, origin)
  }

  return createResponse({
    user,
  }, 200, origin)
}
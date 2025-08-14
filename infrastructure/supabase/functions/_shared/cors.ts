const ALLOWED_ORIGINS = [
  'http://localhost:8080',
  'http://127.0.0.1:8080',
  'https://seo-bot-standalone.vercel.app',
  // Add your actual domain here when ready
]

export function corsHeaders(origin?: string) {
  const allowOrigin = origin && ALLOWED_ORIGINS.includes(origin) 
    ? origin 
    : ALLOWED_ORIGINS[0]

  return {
    'Access-Control-Allow-Origin': allowOrigin,
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Credentials': 'true',
  }
}

export function handleCors(request: Request) {
  const origin = request.headers.get('Origin')
  
  // Handle preflight requests
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      status: 200,
      headers: corsHeaders(origin),
    })
  }

  return corsHeaders(origin)
}

export function createResponse(
  data: any, 
  status: number = 200,
  origin?: string
) {
  return new Response(
    JSON.stringify(data),
    {
      status,
      headers: {
        'Content-Type': 'application/json',
        ...corsHeaders(origin),
      },
    }
  )
}

export function createErrorResponse(
  message: string,
  status: number = 500,
  origin?: string,
  details?: any
) {
  return createResponse(
    {
      error: message,
      details,
    },
    status,
    origin
  )
}
// Service Worker for SEO Bot frontend caching
const CACHE_NAME = 'seo-bot-v1';
const STATIC_CACHE = 'seo-bot-static-v1';
const DYNAMIC_CACHE = 'seo-bot-dynamic-v1';

// Assets to cache immediately
const STATIC_ASSETS = [
  '/',
  '/manifest.json',
  // Add critical CSS and JS files here when known
];

// API endpoints to cache
const API_CACHE_PATTERNS = [
  /\/api\/health/,
  /\/api\/dashboard/,
  /\/api\/keywords/,
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('Service Worker installing...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .catch((error) => {
        console.error('Failed to cache static assets:', error);
      })
  );
  
  // Force the waiting service worker to become the active service worker
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('Service Worker activating...');
  
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  
  // Ensure the service worker takes control of all clients
  return self.clients.claim();
});

// Fetch event - handle requests with caching strategy
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }
  
  // Skip chrome-extension requests
  if (url.protocol === 'chrome-extension:') {
    return;
  }
  
  // Handle different types of requests
  if (isStaticAsset(request)) {
    event.respondWith(handleStaticAsset(request));
  } else if (isAPIRequest(request)) {
    event.respondWith(handleAPIRequest(request));
  } else if (isPageRequest(request)) {
    event.respondWith(handlePageRequest(request));
  }
});

// Check if request is for a static asset
function isStaticAsset(request) {
  const url = new URL(request.url);
  return url.pathname.match(/\.(js|css|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot)$/);
}

// Check if request is for API
function isAPIRequest(request) {
  const url = new URL(request.url);
  return url.pathname.startsWith('/api/');
}

// Check if request is for a page
function isPageRequest(request) {
  const url = new URL(request.url);
  return request.headers.get('accept')?.includes('text/html');
}

// Handle static assets with cache-first strategy
async function handleStaticAsset(request) {
  try {
    const cacheResponse = await caches.match(request);
    if (cacheResponse) {
      return cacheResponse;
    }
    
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.error('Static asset fetch failed:', error);
    
    // Return cached version if available
    const cacheResponse = await caches.match(request);
    if (cacheResponse) {
      return cacheResponse;
    }
    
    // Return offline fallback for images
    if (request.url.match(/\.(png|jpg|jpeg|gif|svg)$/)) {
      return new Response(
        '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200"><rect width="200" height="200" fill="#f0f0f0"/><text x="100" y="100" text-anchor="middle" fill="#666">Image Offline</text></svg>',
        { headers: { 'Content-Type': 'image/svg+xml' } }
      );
    }
    
    throw error;
  }
}

// Handle API requests with network-first strategy
async function handleAPIRequest(request) {
  try {
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok && shouldCacheAPI(request)) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.error('API request failed:', error);
    
    // Try to return cached version for specific endpoints
    if (shouldCacheAPI(request)) {
      const cacheResponse = await caches.match(request);
      if (cacheResponse) {
        console.log('Returning cached API response for:', request.url);
        return cacheResponse;
      }
    }
    
    // Return error response
    return new Response(
      JSON.stringify({ 
        error: 'Network request failed', 
        message: 'Please check your internet connection',
        offline: true 
      }),
      { 
        status: 503,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

// Handle page requests with network-first, fallback to cache
async function handlePageRequest(request) {
  try {
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.error('Page request failed:', error);
    
    // Try cache first
    const cacheResponse = await caches.match(request);
    if (cacheResponse) {
      return cacheResponse;
    }
    
    // Fallback to index.html for SPA routing
    const indexResponse = await caches.match('/');
    if (indexResponse) {
      return indexResponse;
    }
    
    // Ultimate fallback
    return new Response(
      `<!DOCTYPE html>
      <html>
        <head>
          <title>SEO Bot - Offline</title>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
            .offline { max-width: 400px; margin: 0 auto; }
          </style>
        </head>
        <body>
          <div class="offline">
            <h1>You're Offline</h1>
            <p>Please check your internet connection and try again.</p>
            <button onclick="location.reload()">Retry</button>
          </div>
        </body>
      </html>`,
      { headers: { 'Content-Type': 'text/html' } }
    );
  }
}

// Determine if API request should be cached
function shouldCacheAPI(request) {
  const url = new URL(request.url);
  return API_CACHE_PATTERNS.some(pattern => pattern.test(url.pathname));
}

// Handle background sync for offline actions
self.addEventListener('sync', (event) => {
  if (event.tag === 'background-sync') {
    console.log('Background sync triggered');
    event.waitUntil(handleBackgroundSync());
  }
});

async function handleBackgroundSync() {
  // Handle any offline actions that need to be synced
  // For example, send queued analytics events or form submissions
  console.log('Performing background sync...');
}

// Handle push notifications (if needed)
self.addEventListener('push', (event) => {
  if (event.data) {
    const data = event.data.json();
    
    const options = {
      body: data.body || 'New notification from SEO Bot',
      icon: '/icon-192x192.png',
      badge: '/badge-72x72.png',
      tag: data.tag || 'default',
      requireInteraction: false,
      actions: data.actions || []
    };
    
    event.waitUntil(
      self.registration.showNotification(data.title || 'SEO Bot', options)
    );
  }
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  
  if (event.action === 'open_app') {
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});
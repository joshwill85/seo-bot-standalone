import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const isProduction = mode === 'production'
  
  return {
    plugins: [
      react({
        // Optimize React in production
        ...(isProduction && {
          babel: {
            plugins: [
              // Remove PropTypes in production
              ['babel-plugin-transform-react-remove-prop-types', { removeImport: true }],
              // Remove development-only code
              ['babel-plugin-transform-remove-console', { exclude: ['error', 'warn'] }]
            ]
          }
        })
      })
    ],
    server: {
      port: 8080,
      host: true,
    },
    preview: {
      port: 8080,
      host: true,
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
        '@/components': path.resolve(__dirname, './src/components'),
        '@/lib': path.resolve(__dirname, './src/lib'),
        '@/hooks': path.resolve(__dirname, './src/hooks'),
        '@/types': path.resolve(__dirname, './src/types'),
        '@/stores': path.resolve(__dirname, './src/stores'),
        '@/pages': path.resolve(__dirname, './src/pages'),
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: isProduction ? false : true,
      minify: isProduction ? 'esbuild' : false,
      target: 'es2020',
      cssCodeSplit: true,
      
      // Chunk optimization
      rollupOptions: {
        output: {
          manualChunks: {
            // Vendor chunks
            'react-vendor': ['react', 'react-dom'],
            'router-vendor': ['react-router-dom'],
            'ui-vendor': ['@radix-ui/react-icons', '@radix-ui/react-slot', '@radix-ui/react-toast'],
            'query-vendor': ['@tanstack/react-query'],
            'chart-vendor': ['recharts'],
            'supabase-vendor': ['@supabase/supabase-js'],
            'stripe-vendor': ['@stripe/stripe-js'],
            
            // App chunks
            'components': [
              './src/components/CampaignManager.tsx',
              './src/components/SEODashboard.tsx'
            ],
            'pages': [
              './src/pages/dashboard.tsx',
              './src/pages/businesses.tsx',
              './src/pages/reports.tsx'
            ]
          },
          
          // Optimize chunk naming
          chunkFileNames: (chunkInfo) => {
            const facadeModuleId = chunkInfo.facadeModuleId
            ? chunkInfo.facadeModuleId.split('/').pop()?.replace('.tsx', '').replace('.ts', '')
            : 'chunk'
            return `js/${facadeModuleId}-[hash].js`
          },
          entryFileNames: 'js/[name]-[hash].js',
          assetFileNames: (assetInfo) => {
            const info = assetInfo.name?.split('.') || []
            const ext = info[info.length - 1]
            if (/png|jpe?g|svg|gif|tiff|bmp|ico/i.test(ext)) {
              return `images/[name]-[hash][extname]`
            }
            if (/css/i.test(ext)) {
              return `css/[name]-[hash][extname]`
            }
            return `assets/[name]-[hash][extname]`
          }
        }
      },
      
      // Bundle analyzer in development
      ...(mode === 'analyze' && {
        rollupOptions: {
          plugins: [
            // Add bundle analyzer plugin if needed
          ]
        }
      })
    },
    
    // Environment variables
    define: {
      'process.env': {},
      __APP_VERSION__: JSON.stringify(process.env.npm_package_version || '1.0.0'),
      __BUILD_DATE__: JSON.stringify(new Date().toISOString()),
    },
    
    // Optimize dependencies
    optimizeDeps: {
      include: [
        'react',
        'react-dom',
        'react-router-dom',
        '@supabase/supabase-js',
        '@tanstack/react-query',
        'zustand'
      ],
      exclude: ['@vite/client', '@vite/env']
    },
    
    // Performance
    esbuild: {
      // Remove console logs in production
      ...(isProduction && {
        drop: ['console', 'debugger'],
        legalComments: 'none'
      })
    }
  }
})
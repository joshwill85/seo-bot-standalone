# 🚀 SEO Bot Migration Plan: Flask → Keyprompt Tech Stack

## Overview
Migrating seo-bot-standalone from Python Flask to match keyprompt's modern serverless architecture using Vite + React + TypeScript + Supabase Edge Functions.

## Current vs Target Architecture

### Before (Flask-based)
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Static HTML   │    │   Python Flask  │    │ SQLite/Supabase │
│   + Tailwind    │───▶│   + SQLAlchemy  │───▶│   (Python)      │
│   (Marketing)   │    │   + JWT + Stripe│    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### After (Keyprompt-style)
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Vite + React   │    │  Supabase Edge  │    │    Supabase     │
│  + TypeScript   │───▶│   Functions     │───▶│   Postgres      │
│  + Radix UI     │    │  (Serverless)   │    │   (Managed)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Migration Phases

### ✅ Phase 1: Frontend Foundation (COMPLETED)
- [x] Vite + React + TypeScript setup
- [x] Tailwind CSS + custom Florida theme
- [x] Radix UI component library
- [x] React Router for SPA navigation
- [x] TanStack Query for state management
- [x] Zustand for auth state
- [x] ESLint + Prettier configuration

### 🔄 Phase 2: Component Library (IN PROGRESS)
- [ ] Implement all UI components with Radix UI
- [ ] Create Florida-themed design system
- [ ] Build reusable business components
- [ ] Form components with validation
- [ ] Charts and analytics components

### ⏳ Phase 3: Supabase Edge Functions
- [ ] Migrate auth endpoints
- [ ] Migrate business management APIs
- [ ] Migrate SEO tools integration
- [ ] Migrate payment processing
- [ ] Migrate admin functionality

### ⏳ Phase 4: Client-Side Integration
- [ ] Supabase JS client setup
- [ ] Auth context with Supabase Auth
- [ ] Real-time subscriptions
- [ ] Client-side Stripe integration
- [ ] Row Level Security implementation

### ⏳ Phase 5: Testing & Deployment
- [ ] Playwright E2E tests
- [ ] Component testing
- [ ] Vercel deployment configuration
- [ ] Environment variable setup
- [ ] Domain and DNS configuration

## Key Technology Changes

### Frontend Stack
| Component | Before | After |
|-----------|--------|-------|
| Framework | Static HTML | Vite + React + TypeScript |
| Styling | Tailwind CDN | Tailwind CSS + PostCSS |
| Components | Custom HTML | Radix UI + Custom |
| State | jQuery/Vanilla | TanStack Query + Zustand |
| Routing | Server-side | React Router (SPA) |
| Build | None | Vite (HMR, bundling) |

### Backend Stack
| Component | Before | After |
|-----------|--------|-------|
| Runtime | Python Flask | Deno (Edge Functions) |
| Database | SQLAlchemy ORM | Supabase JS client |
| Auth | JWT + bcrypt | Supabase Auth |
| Payments | Stripe Python SDK | Stripe JS + webhooks |
| Deployment | Gunicorn/Docker | Serverless functions |

### Database & Auth
| Component | Before | After |
|-----------|--------|-------|
| Database | SQLite/Postgres | Supabase Postgres |
| Auth | Server-side JWT | Supabase Auth (client) |
| Sessions | Flask sessions | Supabase sessions |
| Permissions | Manual ACL | Row Level Security |
| Real-time | Polling | Supabase Realtime |

## File Structure

### New Frontend Structure
```
src/
├── components/          # Reusable components
│   ├── ui/             # Radix UI primitives
│   ├── auth/           # Authentication components
│   ├── business/       # Business-specific components
│   ├── charts/         # Analytics components
│   └── forms/          # Form components
├── pages/              # Route components
│   ├── auth/           # Login, register
│   ├── dashboard/      # Main dashboard
│   ├── businesses/     # Business management
│   ├── reports/        # SEO reports
│   └── admin/          # Admin panel
├── hooks/              # Custom React hooks
├── lib/                # Utilities and config
├── stores/             # Zustand stores
├── types/              # TypeScript definitions
└── styles/             # Global styles
```

### New Backend Structure
```
supabase/
├── functions/          # Edge Functions
│   ├── auth/           # Authentication functions
│   ├── businesses/     # Business management
│   ├── seo-tools/      # SEO analysis functions
│   ├── payments/       # Stripe integration
│   └── admin/          # Admin functions
├── migrations/         # Database migrations
└── seed.sql           # Initial data
```

## Migration Commands

### 1. Install Dependencies
```bash
npm install
```

### 2. Setup Environment
```bash
cp .env.example .env.local
# Edit .env.local with your Supabase credentials
```

### 3. Database Setup
```bash
# Run SQL schema in Supabase dashboard
cat website/api/supabase_schema.sql
```

### 4. Development Server
```bash
npm run dev  # Runs on localhost:8080 (matches keyprompt)
```

### 5. Build for Production
```bash
npm run build
```

### 6. Deploy to Vercel
```bash
vercel --prod
```

## Environment Variables

### Frontend (.env.local)
```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_...
VITE_APP_URL=https://centralfloridaseo.com
```

### Supabase Edge Functions
```env
STRIPE_SECRET_KEY=sk_test_...
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

## Benefits of Migration

### Performance
- ⚡ **Faster loading**: Vite HMR + code splitting
- 🎯 **Better UX**: SPA navigation + optimistic updates
- 📱 **Mobile-first**: Responsive Radix UI components
- 🚀 **Edge deployment**: Global CDN distribution

### Developer Experience
- 🛠️ **Type safety**: Full TypeScript coverage
- 🔄 **Hot reloading**: Instant feedback during development
- 📦 **Modern tooling**: ESLint, Prettier, Playwright
- 🧪 **Better testing**: Component + E2E tests

### Scalability
- 🌐 **Serverless**: Auto-scaling Edge Functions
- 🔐 **Built-in auth**: Supabase Auth with RLS
- 💾 **Managed database**: Automatic backups + scaling
- 💳 **Better payments**: Client-side Stripe integration

### Maintenance
- 📚 **Consistent stack**: Matches keyprompt architecture
- 🔧 **Shared tooling**: Same build process + deployment
- 👥 **Team efficiency**: Unified development experience
- 🐛 **Easier debugging**: Better error handling + logging

## Migration Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Frontend Foundation | ✅ Complete | - |
| Component Library | 3 days | Phase 1 |
| Edge Functions | 4 days | Supabase setup |
| Client Integration | 3 days | Phase 2 + 3 |
| Testing & Deploy | 2 days | All phases |
| **Total** | **~2 weeks** | - |

## Risk Mitigation

### Parallel Development
- Keep Flask API running during migration
- Gradual feature migration
- Feature flags for A/B testing

### Data Migration
- Export existing data from SQLite/Postgres
- Import to Supabase with proper user mapping
- Validate data integrity

### Performance Testing
- Load testing with realistic data
- SEO tools performance benchmarks
- Payment processing verification

## Next Steps

1. **Complete Component Library** (Next priority)
2. **Setup Supabase Edge Functions**
3. **Migrate core API endpoints**
4. **Implement client-side auth**
5. **Setup Playwright tests**
6. **Deploy to Vercel**

## Questions & Decisions

### Outstanding Items
- [ ] Should we migrate the existing Python SEO tools to TypeScript/Edge Functions?
- [ ] How to handle long-running SEO analysis (Edge Functions have 60s limit)?
- [ ] Migration strategy for existing user data?
- [ ] Subdomain strategy (api.centralfloridaseo.com vs functions)?

### Migration Strategy Options
1. **Big Bang**: Switch entirely at once
2. **Gradual**: Migrate feature by feature
3. **Proxy**: Route requests between old/new systems

**Recommendation**: Gradual migration with feature flags for safety.
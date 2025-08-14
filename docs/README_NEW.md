# Central Florida SEO Services

Professional SEO services platform built with modern web technologies, designed specifically for Central Florida businesses.

## 🚀 Tech Stack

- **Frontend**: Vite + React + TypeScript + Tailwind CSS
- **UI Components**: Radix UI + Custom Florida-themed design system  
- **Backend**: Supabase Edge Functions (Deno)
- **Database**: Supabase Postgres with Row Level Security
- **Authentication**: Supabase Auth
- **Payments**: Stripe (client-side integration)
- **Deployment**: Vercel (frontend) + Supabase (functions)
- **Testing**: Playwright E2E + Vitest unit tests

## 🏗️ Architecture

This project follows the same architecture pattern as keyprompt:

```
Frontend (Vite SPA) → Supabase Edge Functions → Supabase Postgres
                  ↘
                   Stripe (client-side)
```

## 🛠️ Development Setup

### Prerequisites

- Node.js 18+ and npm
- Supabase CLI (optional, for local development)
- Git

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd seo-bot-standalone
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Environment setup**:
   ```bash
   cp .env.local.example .env.local
   # Edit .env.local with your credentials
   ```

4. **Database setup**:
   - Create a new Supabase project
   - Run the SQL schema from `website/api/supabase_schema.sql` in the Supabase SQL editor
   - Update your `.env.local` with the project credentials

5. **Start development server**:
   ```bash
   npm run dev
   ```

   The app will be available at `http://localhost:8080` (matching keyprompt's port)

## 📁 Project Structure

```
src/
├── components/          # Reusable React components
│   ├── ui/             # Radix UI primitives & base components
│   ├── auth/           # Authentication components
│   ├── business/       # Business management components
│   ├── charts/         # Analytics and reporting components
│   └── forms/          # Form components with validation
├── pages/              # Route components (React Router)
│   ├── auth/           # Login, register pages
│   ├── dashboard/      # Main dashboard
│   ├── businesses/     # Business management pages
│   ├── reports/        # SEO reports and analytics
│   └── admin/          # Admin panel
├── hooks/              # Custom React hooks
├── lib/                # Utilities, Supabase client, helpers
├── stores/             # Zustand state management
├── types/              # TypeScript type definitions
└── styles/             # Global CSS and Tailwind config

supabase/               # Supabase configuration
├── functions/          # Edge Functions (backend API)
├── migrations/         # Database migrations
└── config.toml         # Supabase configuration
```

## 🎨 Design System

### Florida-Themed Color Palette

- **Florida Blue**: Primary brand color (#3b82f6)
- **Florida Orange**: Accent color (#f97316) 
- **Florida Green**: Success/growth color (#22c55e)
- **Gradients**: Custom Florida sunset gradients

### Components

Built with Radix UI for accessibility and customized with Florida branding:

- Modern card layouts with subtle shadows
- Responsive navigation with mobile-first design
- Interactive charts for analytics
- Forms with real-time validation
- Loading states and error handling

## 💳 Pricing Strategy

**20% below market rates** to stay competitive:

| Plan | Monthly | Yearly | Features |
|------|---------|--------|----------|
| **Starter** | $64 | $688 | Basic SEO, 50 keywords, 1 business |
| **Professional** | $240 | $2,592 | Advanced SEO, 500 keywords, 3 businesses |
| **Enterprise** | $480 | $5,184 | Full suite, unlimited keywords, 10 businesses |

All plans include a **14-day free trial**.

## 🔧 Available Scripts

- `npm run dev` - Start development server (port 8080)
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run lint:fix` - Fix ESLint errors
- `npm run type-check` - TypeScript type checking
- `npm run test` - Run Playwright E2E tests
- `npm run test:ui` - Run tests with UI
- `npm run test:debug` - Debug tests

## 🚢 Deployment

### Vercel (Recommended)

1. **Connect to Vercel**:
   ```bash
   vercel
   ```

2. **Set environment variables** in Vercel dashboard:
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_ANON_KEY`
   - `VITE_STRIPE_PUBLISHABLE_KEY`

3. **Deploy**:
   ```bash
   vercel --prod
   ```

### Supabase Edge Functions

1. **Install Supabase CLI**:
   ```bash
   npm install -g supabase
   ```

2. **Deploy functions**:
   ```bash
   supabase functions deploy
   ```

## 🧪 Testing

### E2E Testing with Playwright

```bash
# Run all tests
npm run test

# Run tests in UI mode
npm run test:ui

# Run specific test file
npx playwright test auth.spec.ts

# Debug tests
npm run test:debug
```

### Test Coverage

- User authentication flows
- Business creation and management
- SEO report generation
- Payment processing
- Admin panel functionality

## 🔐 Security

### Authentication & Authorization

- **Supabase Auth**: Email/password authentication
- **Row Level Security**: Database-level access control
- **JWT tokens**: Secure API communication
- **Role-based access**: Business owner vs admin permissions

### Data Protection

- **HTTPS everywhere**: All communication encrypted
- **Input validation**: Client and server-side validation
- **SQL injection protection**: Parameterized queries via Supabase
- **CORS configuration**: Restricted origins

## 📊 SEO Tools Integration

### Available Tools

- **Website Audits**: Technical SEO analysis
- **Keyword Research**: Local and national keyword discovery
- **Performance Monitoring**: Core Web Vitals tracking
- **Accessibility Checks**: WCAG compliance auditing
- **Content Analysis**: Content optimization recommendations
- **Competitor Analysis**: SERP analysis and insights

### Real-time Processing

- **Async execution**: Long-running SEO tasks
- **Progress tracking**: Real-time status updates
- **Result caching**: Optimized performance
- **Error handling**: Graceful failure recovery

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow TypeScript best practices
- Write tests for new features
- Use conventional commit messages
- Ensure accessibility compliance
- Optimize for performance

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

- **Email**: support@centralfloridaseo.com
- **Phone**: +1-407-SEO-GROW
- **Documentation**: [Link to docs]
- **Issues**: [GitHub Issues]

## 🗺️ Roadmap

### Q1 2024
- [ ] Complete migration from Flask to Supabase Edge Functions
- [ ] Launch beta with select Central Florida businesses
- [ ] Implement advanced SEO analysis features

### Q2 2024  
- [ ] White-label reporting for agencies
- [ ] Multi-location business support
- [ ] Advanced competitor tracking

### Q3 2024
- [ ] API access for enterprise customers
- [ ] Custom integrations (Google Analytics, Search Console)
- [ ] Automated content optimization

---

Built with ❤️ for Central Florida businesses by the SEO Bot team.
# Central Florida SEO Services - Supabase Integration

## Setup Instructions

### 1. Supabase Project Setup

1. **Access your Supabase Dashboard**:
   - Go to [https://supabase.com/dashboard](https://supabase.com/dashboard)
   - Select your "SEO-Bot" organization
   - Create a new project or use existing one

2. **Get Your Credentials**:
   - Go to Project Settings → API
   - Copy the following values:
     - `Project URL` (SUPABASE_URL)
     - `anon/public key` (SUPABASE_ANON_KEY)  
     - `service_role/secret key` (SUPABASE_SERVICE_ROLE_KEY)

3. **Database Setup**:
   - Go to SQL Editor in your Supabase dashboard
   - Copy and paste the contents of `supabase_schema.sql`
   - Execute the script to create all tables and functions

### 2. Environment Configuration

1. **Create your `.env` file**:
   ```bash
   cp .env.example .env
   ```

2. **Update the `.env` file with your credentials**:
   ```env
   # Supabase Configuration
   SUPABASE_URL=https://your-project-ref.supabase.co
   SUPABASE_ANON_KEY=your-supabase-anon-key
   SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
   
   # Other configurations...
   SECRET_KEY=your-secret-key-change-in-production
   JWT_SECRET_KEY=your-jwt-secret-key-change-in-production
   STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
   ```

### 3. Installation & Running

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Supabase version**:
   ```bash
   python app_supabase.py
   ```

## Database Schema

The database includes the following tables:

- **users**: User accounts (business owners and admin)
- **businesses**: Business profiles and subscription info
- **seo_reports**: SEO audit results and reports
- **seo_logs**: Historical activity logs

## Key Features

### Row Level Security (RLS)
- Users can only access their own data
- Admins have full access to all data
- System can insert/update reports and logs

### Analytics Views
- `business_analytics`: Aggregated business performance data
- `get_business_insights()`: Function for detailed business insights

### Pricing Plans (20% below market)
- **Starter**: $64/month (vs $80+ market rate)
- **Professional**: $240/month (vs $300+ market rate)
- **Enterprise**: $480/month (vs $600+ market rate)

## API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `GET /api/auth/profile` - Get user profile

### Business Management
- `POST /api/businesses` - Create business
- `GET /api/businesses` - Get user's businesses
- `GET /api/businesses/<id>` - Get specific business
- `GET /api/businesses/<id>/analytics` - Get business analytics

### SEO Tools
- `POST /api/seo/audit/<business_id>` - Run full SEO audit
- `POST /api/seo/keywords/<business_id>` - Research keywords
- `GET /api/seo/reports/<business_id>` - Get reports
- `GET /api/seo/logs/<business_id>` - Get activity logs

### Payments
- `GET /api/payments/plans` - Get pricing plans
- `POST /api/payments/subscribe` - Create subscription
- `GET /api/payments/subscription/<business_id>` - Get subscription status
- `POST /api/payments/webhook` - Stripe webhook handler

### Admin
- `GET /api/admin/dashboard` - Admin dashboard data

## File Structure

```
website/api/
├── app_supabase.py              # Main Flask app (Supabase version)
├── supabase_client.py           # Supabase client and operations
├── seo_tools_supabase.py        # SEO tools endpoints (Supabase)
├── payments_supabase.py         # Payment endpoints (Supabase)
├── supabase_schema.sql          # Database schema
├── requirements.txt             # Dependencies
├── .env.example                 # Environment template
└── README_SUPABASE.md          # This file
```

## Deployment Options

### Option 1: Use Supabase Version (Recommended)
Replace the original files with Supabase versions:
```bash
cp app_supabase.py app.py
cp seo_tools_supabase.py seo_tools.py
cp payments_supabase.py payments.py
```

### Option 2: Run Supabase Version Directly
```bash
python app_supabase.py
```

## Security Notes

1. **Environment Variables**: Never commit real API keys to version control
2. **Row Level Security**: Enabled on all tables for data isolation
3. **JWT Tokens**: Used for API authentication
4. **CORS**: Configured for your domain only
5. **Stripe Webhooks**: Verify signatures for security

## Monitoring & Logging

- All SEO actions are logged to `seo_logs` table
- Payment events are tracked via Stripe webhooks
- Business analytics provide insights into usage patterns
- Admin dashboard shows system-wide metrics

## Support

The system includes comprehensive error handling and logging. Check the logs for debugging information if you encounter issues.

For Supabase-specific issues, refer to the [Supabase Documentation](https://supabase.com/docs).
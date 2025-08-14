import { Search, BarChart3, Zap, Target, Globe, TrendingUp, FileText, Award, Users } from 'lucide-react'

const features = [
  {
    icon: Search,
    title: "Smart Keyword Intelligence",
    description: "AI-powered keyword research that goes beyond basic tools with intent-based scoring and local Central Florida market analysis.",
    benefits: [
      "Intent-based keyword scoring (0-10 business value ratings)",
      "Local Central Florida keyword discovery with competition analysis",
      "Semantic clustering that groups related keywords into content themes",
      "SERP gap analysis showing opportunities competitors miss"
    ]
  },
  {
    icon: Zap,
    title: "AI-Powered Technical SEO Auditing", 
    description: "Comprehensive website health checks that identify revenue-impacting issues with 100+ automated checkpoints.",
    benefits: [
      "Core Web Vitals monitoring and optimization recommendations",
      "Performance budget analysis with speed improvements",
      "Accessibility compliance (WCAG AA standards) for broader reach",
      "Mobile-first optimization ensuring perfect mobile experience"
    ]
  },
  {
    icon: FileText,
    title: "Content Strategy & Optimization",
    description: "Transform content creation from guesswork to science with AI-generated briefs and competitor analysis.",
    benefits: [
      "AI content brief generation analyzing top-ranking competitors",
      "Topic expertise scoring ensuring Google E-A-T compliance",
      "Content gap identification showing exactly what to create",
      "Internal linking optimization for maximum SEO impact"
    ]
  },
  {
    icon: BarChart3,
    title: "Real-Time Performance Monitoring",
    description: "Stay ahead of issues before they impact rankings with 24/7 automated monitoring and instant alerts.",
    benefits: [
      "Live SEO dashboard with real-time ranking tracking",
      "Automated alerts for keyword position changes",
      "Technical issue detection with instant notifications",
      "Traffic source analysis with conversion tracking"
    ]
  },
  {
    icon: Target,
    title: "Advanced Competitive Intelligence",
    description: "Know exactly what your competitors are doing and beat them with comprehensive market analysis.",
    benefits: [
      "Content strategy reverse-engineering from top performers",
      "Keyword overlap analysis revealing market opportunities",
      "SERP feature optimization (featured snippets, PAA)",
      "Local competition analysis for Central Florida markets"
    ]
  },
  {
    icon: TrendingUp,
    title: "Business-Focused Analytics",
    description: "Reports that connect SEO efforts directly to revenue with ROI tracking and performance forecasting.",
    benefits: [
      "ROI tracking linking organic traffic to business goals",
      "Lead attribution showing which keywords drive customers",
      "Revenue impact analysis for SEO improvements",
      "Performance forecasting with growth projections"
    ]
  }
]

const stats = [
  { label: "Average Traffic Increase", value: "40-80%", description: "within 6 months" },
  { label: "Technical Issues Identified", value: "100+", description: "automated checkpoints" },
  { label: "Keywords Tracked", value: "1,000+", description: "per business" },
  { label: "Central Florida Businesses", value: "500+", description: "trust our platform" }
]

const testimonials = [
  {
    quote: "Our organic traffic increased 67% in just 4 months. The keyword insights were game-changing for our Orlando restaurant.",
    author: "Maria Rodriguez",
    title: "Owner, Sabor Latino Restaurant",
    location: "Orlando, FL"
  },
  {
    quote: "Finally, an SEO tool that actually shows ROI. We can track every lead back to specific keywords and content.",
    author: "James Mitchell", 
    title: "Marketing Director, Central FL Law Group",
    location: "Tampa, FL"
  }
]

export default function FeaturesPage() {
  return (
    <>
      {/* SEO Meta Tags */}
      <title>SEO Features - Advanced Tools for Central Florida Businesses | Central Florida SEO</title>
      <meta name="description" content="Discover our comprehensive SEO platform features: AI-powered keyword research, technical auditing, content optimization, and real-time monitoring for Central Florida businesses." />
      <meta name="keywords" content="SEO tools, keyword research, technical SEO, Central Florida SEO, Orlando SEO, Tampa SEO" />
      
      <main className="min-h-screen bg-gradient-to-br from-florida-blue-50 to-white">
        {/* Hero Section */}
        <header className="relative bg-florida-blue-900 text-white py-16 lg:py-24">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center">
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6">
                Advanced SEO Features
                <span className="block text-florida-orange-400 mt-2">Built for Florida Businesses</span>
              </h1>
              <p className="text-xl md:text-2xl text-florida-blue-100 max-w-3xl mx-auto leading-relaxed">
                Comprehensive SEO tools that combine cutting-edge AI technology with proven methodologies 
                to help Central Florida businesses dominate local search results.
              </p>
            </div>
          </div>
          
          {/* Background Pattern */}
          <div className="absolute inset-0 bg-gradient-to-r from-florida-blue-900/50 to-florida-blue-800/50" />
          <div className="absolute inset-0 opacity-20" style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.05'%3E%3Cpath d='M30 30c0-11.046-8.954-20-20-20s-20 8.954-20 20 8.954 20 20 20 20-8.954 20-20zm0 0c0 11.046 8.954 20 20 20s20-8.954 20-20-8.954-20-20-20-20 8.954-20 20z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`
          }} />
        </header>

        {/* Stats Section */}
        <section className="py-12 bg-white border-b border-gray-200" aria-labelledby="stats-heading">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 id="stats-heading" className="sr-only">Platform Statistics</h2>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
              {stats.map((stat, index) => (
                <div key={index} className="text-center">
                  <div className="text-3xl lg:text-4xl font-bold text-florida-blue-900 mb-2">
                    {stat.value}
                  </div>
                  <div className="text-lg font-semibold text-gray-900 mb-1">
                    {stat.label}
                  </div>
                  <div className="text-sm text-gray-600">
                    {stat.description}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Features Grid */}
        <section className="py-16 lg:py-24" aria-labelledby="features-heading">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
              <h2 id="features-heading" className="text-3xl lg:text-4xl font-bold text-gray-900 mb-6">
                Everything You Need to Dominate Local Search
              </h2>
              <p className="text-xl text-gray-600 max-w-3xl mx-auto">
                Our comprehensive SEO platform provides all the tools and insights needed to outrank 
                competitors and attract more customers in the Central Florida market.
              </p>
            </div>

            <div className="grid lg:grid-cols-2 gap-12">
              {features.map((feature, index) => (
                <article key={index} className="bg-white rounded-2xl shadow-lg p-8 hover:shadow-xl transition-shadow duration-300">
                  <div className="flex items-start space-x-4">
                    <div className="flex-shrink-0">
                      <div className="w-12 h-12 bg-florida-orange-100 rounded-lg flex items-center justify-center">
                        <feature.icon className="w-6 h-6 text-florida-orange-600" aria-hidden="true" />
                      </div>
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-xl font-bold text-gray-900 mb-3">
                        {feature.title}
                      </h3>
                      <p className="text-gray-600 mb-6 leading-relaxed">
                        {feature.description}
                      </p>
                      <ul className="space-y-3">
                        {feature.benefits.map((benefit, benefitIndex) => (
                          <li key={benefitIndex} className="flex items-start space-x-3">
                            <div className="flex-shrink-0 w-5 h-5 bg-florida-green-100 rounded-full flex items-center justify-center mt-0.5">
                              <div className="w-2 h-2 bg-florida-green-600 rounded-full" aria-hidden="true" />
                            </div>
                            <span className="text-gray-700 leading-relaxed">{benefit}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* Why Central Florida Section */}
        <section className="py-16 bg-florida-blue-50" aria-labelledby="local-expertise-heading">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 id="local-expertise-heading" className="text-3xl lg:text-4xl font-bold text-gray-900 mb-6">
                Built Specifically for Central Florida Markets
              </h2>
              <p className="text-xl text-gray-600 max-w-3xl mx-auto">
                Unlike generic SEO tools, our platform understands the unique challenges and opportunities 
                in Orlando, Tampa, Miami, and surrounding Central Florida markets.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8">
              <div className="bg-white rounded-xl p-6 shadow-md">
                <Globe className="w-8 h-8 text-florida-blue-600 mb-4" aria-hidden="true" />
                <h3 className="text-lg font-semibold text-gray-900 mb-3">Local Market Focus</h3>
                <p className="text-gray-600">
                  Keyword research and competition analysis specifically calibrated for Central Florida 
                  search patterns and local business competition.
                </p>
              </div>
              
              <div className="bg-white rounded-xl p-6 shadow-md">
                <Users className="w-8 h-8 text-florida-orange-600 mb-4" aria-hidden="true" />
                <h3 className="text-lg font-semibold text-gray-900 mb-3">Small Business Friendly</h3>
                <p className="text-gray-600">
                  Affordable pricing starting at $64/month (20% below market rates) with enterprise-level 
                  features accessible to every local business.
                </p>
              </div>
              
              <div className="bg-white rounded-xl p-6 shadow-md">
                <Award className="w-8 h-8 text-florida-green-600 mb-4" aria-hidden="true" />
                <h3 className="text-lg font-semibold text-gray-900 mb-3">Proven Results</h3>
                <p className="text-gray-600">
                  Track record of helping 500+ Central Florida businesses achieve 40-80% traffic 
                  increases within 6 months.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Testimonials */}
        <section className="py-16" aria-labelledby="testimonials-heading">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 id="testimonials-heading" className="text-3xl lg:text-4xl font-bold text-center text-gray-900 mb-12">
              What Central Florida Businesses Say
            </h2>
            
            <div className="grid md:grid-cols-2 gap-8">
              {testimonials.map((testimonial, index) => (
                <blockquote key={index} className="bg-white rounded-xl p-8 shadow-lg">
                  <div className="text-lg text-gray-700 mb-6 italic leading-relaxed">
                    "{testimonial.quote}"
                  </div>
                  <div className="flex items-center space-x-4">
                    <div className="w-12 h-12 bg-florida-blue-100 rounded-full flex items-center justify-center">
                      <span className="text-florida-blue-700 font-semibold text-lg">
                        {testimonial.author.split(' ').map(n => n[0]).join('')}
                      </span>
                    </div>
                    <div>
                      <div className="font-semibold text-gray-900">{testimonial.author}</div>
                      <div className="text-gray-600">{testimonial.title}</div>
                      <div className="text-sm text-gray-500">{testimonial.location}</div>
                    </div>
                  </div>
                </blockquote>
              ))}
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-16 bg-gradient-to-r from-florida-blue-900 to-florida-blue-800" aria-labelledby="cta-heading">
          <div className="max-w-4xl mx-auto text-center px-4 sm:px-6 lg:px-8">
            <h2 id="cta-heading" className="text-3xl lg:text-4xl font-bold text-white mb-6">
              Ready to Transform Your Online Presence?
            </h2>
            <p className="text-xl text-florida-blue-100 mb-8 leading-relaxed">
              Join 500+ Central Florida businesses using our platform to dominate local search results 
              and attract more customers.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <a 
                href="/pricing" 
                className="inline-flex items-center justify-center px-8 py-4 bg-florida-orange-500 text-white font-semibold rounded-lg hover:bg-florida-orange-600 transition-colors duration-200 focus:ring-4 focus:ring-florida-orange-300 focus:outline-none"
                aria-describedby="cta-description"
              >
                View Pricing Plans
              </a>
              <a 
                href="/contact" 
                className="inline-flex items-center justify-center px-8 py-4 bg-transparent border-2 border-white text-white font-semibold rounded-lg hover:bg-white hover:text-florida-blue-900 transition-colors duration-200 focus:ring-4 focus:ring-white focus:outline-none"
                aria-describedby="cta-description"
              >
                Schedule Free Consultation
              </a>
            </div>
            <p id="cta-description" className="text-sm text-florida-blue-200 mt-4">
              Start with our free SEO health check • No long-term contracts • Cancel anytime
            </p>
          </div>
        </section>
      </main>
    </>
  )
}
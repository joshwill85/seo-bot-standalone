import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { 
  TrendingUp, 
  Target, 
  BarChart3, 
  Users, 
  CheckCircle, 
  ArrowRight,
  Star,
  MapPin
} from 'lucide-react'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-florida-blue-50 via-white to-florida-orange-50">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-gradient-to-br from-florida-blue-600 to-florida-orange-600 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-gray-900">Central Florida SEO</span>
          </div>
          
          <nav className="hidden md:flex items-center space-x-6">
            <Link to="/features" className="text-gray-600 hover:text-gray-900 transition-colors">Features</Link>
            <Link to="/pricing" className="text-gray-600 hover:text-gray-900 transition-colors">Pricing</Link>
            <Link to="/about" className="text-gray-600 hover:text-gray-900 transition-colors">About</Link>
            <Link to="/contact" className="text-gray-600 hover:text-gray-900 transition-colors">Contact</Link>
          </nav>

          <div className="flex items-center space-x-3">
            <Link to="/login">
              <Button variant="ghost">Sign In</Button>
            </Link>
            <Link to="/register">
              <Button variant="florida">Get Started</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-20 lg:py-32">
        <div className="container mx-auto px-4 text-center">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-center justify-center mb-6">
              <div className="bg-florida-blue-100 text-florida-blue-700 px-3 py-1 rounded-full text-sm font-medium flex items-center">
                <MapPin className="w-4 h-4 mr-1" />
                Proudly Serving Central Florida
              </div>
            </div>
            
            <h1 className="text-4xl lg:text-6xl font-bold text-gray-900 mb-6">
              Grow Your <span className="text-gradient">Local Business</span> with 
              Professional SEO Services
            </h1>
            
            <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
              Boost your search rankings, drive more customers, and dominate your local market 
              with our proven SEO strategies designed specifically for Central Florida businesses.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
              <Link to="/register">
                <Button size="xl" variant="florida" className="group">
                  Start Free Trial
                  <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
                </Button>
              </Link>
              <Link to="/pricing">
                <Button size="xl" variant="outline">
                  View Pricing
                </Button>
              </Link>
            </div>

            <div className="flex items-center justify-center space-x-8 text-sm text-gray-500">
              <div className="flex items-center">
                <CheckCircle className="w-4 h-4 text-green-500 mr-2" />
                14-day free trial
              </div>
              <div className="flex items-center">
                <CheckCircle className="w-4 h-4 text-green-500 mr-2" />
                No setup fees
              </div>
              <div className="flex items-center">
                <CheckCircle className="w-4 h-4 text-green-500 mr-2" />
                Cancel anytime
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-white">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-4xl font-bold text-gray-900 mb-4">
              Everything You Need to Succeed Online
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Our comprehensive SEO platform provides all the tools and insights 
              you need to outrank your competition.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            <div className="group p-6 rounded-xl border border-gray-200 hover:border-florida-blue-300 hover:shadow-lg transition-all duration-300">
              <div className="w-12 h-12 bg-florida-blue-100 rounded-lg flex items-center justify-center mb-4 group-hover:bg-florida-blue-200 transition-colors">
                <Target className="w-6 h-6 text-florida-blue-600" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Local SEO Optimization</h3>
              <p className="text-gray-600">
                Dominate local search results and attract customers in your area with 
                targeted local SEO strategies.
              </p>
            </div>

            <div className="group p-6 rounded-xl border border-gray-200 hover:border-florida-orange-300 hover:shadow-lg transition-all duration-300">
              <div className="w-12 h-12 bg-florida-orange-100 rounded-lg flex items-center justify-center mb-4 group-hover:bg-florida-orange-200 transition-colors">
                <BarChart3 className="w-6 h-6 text-florida-orange-600" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Performance Analytics</h3>
              <p className="text-gray-600">
                Track your progress with detailed analytics and insights that show 
                exactly how your SEO efforts are paying off.
              </p>
            </div>

            <div className="group p-6 rounded-xl border border-gray-200 hover:border-florida-green-300 hover:shadow-lg transition-all duration-300">
              <div className="w-12 h-12 bg-florida-green-100 rounded-lg flex items-center justify-center mb-4 group-hover:bg-florida-green-200 transition-colors">
                <Users className="w-6 h-6 text-florida-green-600" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Expert Support</h3>
              <p className="text-gray-600">
                Get personalized guidance from our team of SEO experts who understand 
                the Central Florida market.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Preview */}
      <section className="py-20 bg-gray-50">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-4xl font-bold text-gray-900 mb-4">
              Transparent, Competitive Pricing
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Our prices are 20% below market rates, giving you professional SEO 
              services at an unbeatable value.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            <div className="bg-white rounded-xl p-6 border border-gray-200 hover:shadow-lg transition-shadow">
              <div className="text-center">
                <h3 className="text-xl font-semibold text-gray-900 mb-2">Starter</h3>
                <div className="text-3xl font-bold text-gray-900 mb-1">$64<span className="text-lg text-gray-500">/mo</span></div>
                <p className="text-gray-500 mb-6">Perfect for small businesses</p>
                <ul className="space-y-3 text-left">
                  <li className="flex items-center">
                    <CheckCircle className="w-4 h-4 text-green-500 mr-3" />
                    <span className="text-gray-600">Basic SEO Audit</span>
                  </li>
                  <li className="flex items-center">
                    <CheckCircle className="w-4 h-4 text-green-500 mr-3" />
                    <span className="text-gray-600">50 Keywords Research</span>
                  </li>
                  <li className="flex items-center">
                    <CheckCircle className="w-4 h-4 text-green-500 mr-3" />
                    <span className="text-gray-600">Monthly Reporting</span>
                  </li>
                </ul>
              </div>
            </div>

            <div className="bg-white rounded-xl p-6 border-2 border-florida-blue-500 hover:shadow-lg transition-shadow relative">
              <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                <div className="bg-florida-blue-500 text-white px-3 py-1 rounded-full text-sm font-medium">
                  Most Popular
                </div>
              </div>
              <div className="text-center">
                <h3 className="text-xl font-semibold text-gray-900 mb-2">Professional</h3>
                <div className="text-3xl font-bold text-gray-900 mb-1">$240<span className="text-lg text-gray-500">/mo</span></div>
                <p className="text-gray-500 mb-6">For growing businesses</p>
                <ul className="space-y-3 text-left">
                  <li className="flex items-center">
                    <CheckCircle className="w-4 h-4 text-green-500 mr-3" />
                    <span className="text-gray-600">Comprehensive SEO Audit</span>
                  </li>
                  <li className="flex items-center">
                    <CheckCircle className="w-4 h-4 text-green-500 mr-3" />
                    <span className="text-gray-600">500 Keywords Research</span>
                  </li>
                  <li className="flex items-center">
                    <CheckCircle className="w-4 h-4 text-green-500 mr-3" />
                    <span className="text-gray-600">Weekly Reporting</span>
                  </li>
                </ul>
              </div>
            </div>

            <div className="bg-white rounded-xl p-6 border border-gray-200 hover:shadow-lg transition-shadow">
              <div className="text-center">
                <h3 className="text-xl font-semibold text-gray-900 mb-2">Enterprise</h3>
                <div className="text-3xl font-bold text-gray-900 mb-1">$480<span className="text-lg text-gray-500">/mo</span></div>
                <p className="text-gray-500 mb-6">For established businesses</p>
                <ul className="space-y-3 text-left">
                  <li className="flex items-center">
                    <CheckCircle className="w-4 h-4 text-green-500 mr-3" />
                    <span className="text-gray-600">Full SEO Suite</span>
                  </li>
                  <li className="flex items-center">
                    <CheckCircle className="w-4 h-4 text-green-500 mr-3" />
                    <span className="text-gray-600">Unlimited Keywords</span>
                  </li>
                  <li className="flex items-center">
                    <CheckCircle className="w-4 h-4 text-green-500 mr-3" />
                    <span className="text-gray-600">Daily Reporting</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>

          <div className="text-center mt-12">
            <Link to="/pricing">
              <Button size="lg" variant="florida">
                View All Plans & Features
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Social Proof */}
      <section className="py-20 bg-white">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-4xl font-bold text-gray-900 mb-4">
              Trusted by Central Florida Businesses
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
            <div className="text-center">
              <div className="flex justify-center mb-4">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} className="w-5 h-5 text-yellow-400 fill-current" />
                ))}
              </div>
              <p className="text-gray-600 mb-4">
                "Our website traffic increased by 150% in just 3 months. The team knows the local market inside and out."
              </p>
              <div className="font-semibold text-gray-900">Sarah M.</div>
              <div className="text-gray-500 text-sm">Restaurant Owner, Orlando</div>
            </div>

            <div className="text-center">
              <div className="flex justify-center mb-4">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} className="w-5 h-5 text-yellow-400 fill-current" />
                ))}
              </div>
              <p className="text-gray-600 mb-4">
                "Finally ranking #1 for our main keywords. The ROI has been incredible for our business."
              </p>
              <div className="font-semibold text-gray-900">Mike T.</div>
              <div className="text-gray-500 text-sm">HVAC Contractor, Tampa</div>
            </div>

            <div className="text-center">
              <div className="flex justify-center mb-4">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} className="w-5 h-5 text-yellow-400 fill-current" />
                ))}
              </div>
              <p className="text-gray-600 mb-4">
                "Professional service with results that speak for themselves. Highly recommend!"
              </p>
              <div className="font-semibold text-gray-900">Lisa K.</div>
              <div className="text-gray-500 text-sm">Dental Practice, St. Petersburg</div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-r from-florida-blue-600 to-florida-orange-600">
        <div className="container mx-auto px-4 text-center">
          <div className="max-w-3xl mx-auto">
            <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4">
              Ready to Dominate Your Local Market?
            </h2>
            <p className="text-xl text-white/90 mb-8">
              Join hundreds of Central Florida businesses that trust us with their SEO success.
              Start your free trial today and see results in 30 days or less.
            </p>
            <Link to="/register">
              <Button size="xl" className="bg-white text-gray-900 hover:bg-gray-100">
                Start Your Free Trial
                <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center space-x-2 mb-4">
                <div className="w-8 h-8 bg-gradient-to-br from-florida-blue-600 to-florida-orange-600 rounded-lg flex items-center justify-center">
                  <TrendingUp className="w-5 h-5 text-white" />
                </div>
                <span className="text-xl font-bold">Central Florida SEO</span>
              </div>
              <p className="text-gray-400">
                Helping Central Florida businesses grow through professional SEO services.
              </p>
            </div>

            <div>
              <h4 className="font-semibold mb-4">Services</h4>
              <ul className="space-y-2 text-gray-400">
                <li><Link to="/features" className="hover:text-white">Local SEO</Link></li>
                <li><Link to="/features" className="hover:text-white">Keyword Research</Link></li>
                <li><Link to="/features" className="hover:text-white">Content Optimization</Link></li>
                <li><Link to="/features" className="hover:text-white">Analytics & Reporting</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold mb-4">Company</h4>
              <ul className="space-y-2 text-gray-400">
                <li><Link to="/about" className="hover:text-white">About Us</Link></li>
                <li><Link to="/pricing" className="hover:text-white">Pricing</Link></li>
                <li><Link to="/contact" className="hover:text-white">Contact</Link></li>
                <li><Link to="/contact" className="hover:text-white">Support</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold mb-4">Contact</h4>
              <ul className="space-y-2 text-gray-400">
                <li>Email: hello@centralfloridaseo.com</li>
                <li>Phone: +1-407-SEO-GROW</li>
                <li>Orlando, FL</li>
              </ul>
            </div>
          </div>

          <div className="border-t border-gray-800 mt-8 pt-8 text-center text-gray-400">
            <p>&copy; 2024 Central Florida SEO. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
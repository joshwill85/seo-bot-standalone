import { Check, Star, ArrowRight, Shield, Zap, BarChart3 } from 'lucide-react'
import Header from '@/components/Header'

const plans = [
  {
    name: "Professional",
    price: "$149",
    period: "per month",
    description: "Perfect for small businesses ready to dominate local search",
    popular: false,
    features: [
      "15 Automated SEO Services (Keyword, Content, Technical)",
      "Monthly technical audits with automated fixes",
      "Keyword research & tracking (up to 500 keywords)",
      "Content optimization & meta tag automation",
      "Local SEO optimization & citation building", 
      "Google Business Profile management",
      "Basic competitor monitoring",
      "Monthly performance reports",
      "Email support with 24-hour response",
      "Mobile optimization & Core Web Vitals"
    ],
    cta: "Get Started",
    icon: BarChart3
  },
  {
    name: "Business",
    price: "$299",
    period: "per month", 
    description: "Complete automation for growing businesses and agencies",
    popular: true,
    features: [
      "All 39 Automated SEO Services (9 Categories)",
      "Advanced keyword research with clustering",
      "Content strategy automation & calendar generation",
      "Complete technical SEO audit automation",
      "Advanced link building & outreach automation",
      "Comprehensive local SEO automation",
      "Advanced competitor analysis & monitoring",
      "Conversion optimization automation",
      "Real-time analytics & automated reporting",
      "Priority email & chat support"
    ],
    cta: "Get Started",
    icon: Zap
  },
  {
    name: "Enterprise",
    price: "$599",
    period: "per month",
    description: "White-label platform for agencies and enterprise clients",
    popular: false,
    features: [
      "Everything in Business Plan, plus:",
      "White-label dashboard & reporting",
      "API access for custom integrations",
      "Multi-client management dashboard",
      "Advanced automation scheduling",
      "Custom workflow automation",
      "Dedicated account manager",
      "Priority phone support", 
      "Custom onboarding & training",
      "Revenue sharing opportunities",
      "Unlimited client projects"
    ],
    cta: "Get Started",
    icon: Shield
  }
]

const testimonials = [
  {
    quote: "Switched from a $2,000/month agency to their Business plan. 39 automated services vs 5 manual ones - saved $1,700/month!",
    author: "Mike Chen",
    title: "Owner, Orlando Web Design",
    savings: "$1,700/month"
  },
  {
    quote: "Their Enterprise plan gives us everything we need to manage 50+ client campaigns. The white-label reporting and automation is incredible.",
    author: "Sarah Martinez", 
    title: "Digital Marketing Director",
    company: "Tampa Marketing Group"
  },
  {
    quote: "The automated technical audits found issues our $3,000/month agency never caught. ROI paid for itself in 2 weeks.",
    author: "David Rodriguez",
    title: "CEO, Miami Law Firm"
  }
]

const faqs = [
  {
    question: "Why are your prices 75% below market rates?",
    answer: "We focus specifically on the Florida market and use advanced AI automation, allowing us to offer enterprise-level services at small business prices."
  },
  {
    question: "Do you require long-term contracts?",
    answer: "No contracts required! Month-to-month service with 30 days notice to cancel. We earn your business every month."
  },
  {
    question: "What if I'm not satisfied with results?",
    answer: "We offer a 60-day money-back guarantee. If you don't see measurable improvements in your SEO metrics, we'll refund your investment."
  }
]

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-florida-blue-50 to-white">
        <Header />
        
        {/* Hero Section */}
        <section className="bg-florida-blue-900 text-white py-16 lg:py-20">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6">
              Honest SEO Pricing
              <span className="block text-florida-orange-400 mt-2">75% Below Market Rates</span>
            </h1>
            <p className="text-xl md:text-2xl text-florida-blue-100 max-w-3xl mx-auto leading-relaxed mb-8">
              Professional SEO services designed specifically for Central Florida businesses. 
              No contracts, no hidden fees, just results.
            </p>
            <div className="flex items-center justify-center space-x-4 text-florida-blue-200">
              <Check className="w-5 h-5" />
              <span>No Long-Term Contracts</span>
              <Check className="w-5 h-5" />
              <span>60-Day Money-Back Guarantee</span>
              <Check className="w-5 h-5" />
              <span>Local Florida Expertise</span>
            </div>
          </div>
        </section>

        {/* Pricing Cards */}
        <section className="py-16 lg:py-24">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid lg:grid-cols-3 gap-8">
              {plans.map((plan, index) => (
                <div key={index} className={`relative bg-white rounded-2xl shadow-xl border flex flex-col h-full transition-all duration-300 hover:shadow-2xl ${plan.popular ? 'border-florida-orange-500 shadow-florida-orange-100' : 'border-gray-200 hover:border-florida-blue-300'}`}>
                  {plan.popular && (
                    <div className="absolute -top-4 left-1/2 transform -translate-x-1/2 z-10">
                      <div className="bg-gradient-to-r from-florida-orange-500 to-florida-orange-600 text-white px-6 py-2 rounded-full text-sm font-bold shadow-lg">
                        <div className="flex items-center space-x-2">
                          <Star className="w-4 h-4 fill-current" />
                          <span>MOST POPULAR</span>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  <div className={`p-8 flex-grow flex flex-col ${plan.popular ? 'pt-12' : ''}`}>
                    <div className="flex items-center space-x-3 mb-4">
                      <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                        plan.popular ? 'bg-florida-orange-100' : 'bg-florida-blue-100'
                      }`}>
                        <plan.icon className={`w-6 h-6 ${
                          plan.popular ? 'text-florida-orange-600' : 'text-florida-blue-600'
                        }`} />
                      </div>
                      <div>
                        <h3 className="text-2xl font-bold text-gray-900">{plan.name}</h3>
                      </div>
                    </div>
                    
                    <div className="mb-6">
                      <div className="flex items-baseline space-x-2">
                        <span className="text-4xl lg:text-5xl font-bold text-gray-900">{plan.price}</span>
                        <span className="text-lg text-gray-600">/{plan.period}</span>
                      </div>
                      <p className="text-gray-600 mt-2 leading-relaxed">{plan.description}</p>
                    </div>

                    <ul className="space-y-3 mb-8 flex-grow">
                      {plan.features.map((feature, featureIndex) => (
                        <li key={featureIndex} className="flex items-start space-x-3">
                          <div className="flex-shrink-0 w-5 h-5 bg-florida-green-100 rounded-full flex items-center justify-center mt-0.5">
                            <Check className="w-3 h-3 text-florida-green-600" />
                          </div>
                          <span className={`text-gray-700 leading-relaxed ${feature.startsWith('Everything in') ? 'font-semibold text-florida-blue-900' : ''}`}>
                            {feature}
                          </span>
                        </li>
                      ))}
                    </ul>

                    <div className="mt-auto">
                      <button className={`w-full py-4 px-6 rounded-lg font-semibold transition-colors duration-200 flex items-center justify-center space-x-2 ${
                        plan.popular 
                          ? 'bg-florida-orange-500 text-white hover:bg-florida-orange-600' 
                          : 'bg-florida-blue-600 text-white hover:bg-florida-blue-700'
                      }`}>
                        <span>{plan.cta}</span>
                        <ArrowRight className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            
            <div className="text-center mt-12">
              <p className="text-lg text-gray-600 mb-6">
                Need a custom solution? We work with enterprise clients and agencies.
              </p>
              <a 
                href="/contact" 
                className="inline-flex items-center space-x-2 text-florida-blue-600 hover:text-florida-blue-700 font-semibold"
              >
                <span>Contact us for custom pricing</span>
                <ArrowRight className="w-5 h-5" />
              </a>
            </div>
          </div>
        </section>

        {/* Comparison Section */}
        <section className="py-16 bg-florida-blue-50">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-3xl lg:text-4xl font-bold text-gray-900 mb-6">
                How We Compare to Traditional SEO Agencies
              </h2>
              <p className="text-xl text-gray-600">
                Same enterprise-level results at a fraction of the cost
              </p>
            </div>

            <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-florida-blue-900 text-white">
                    <tr>
                      <th className="px-6 py-4 text-left">Service</th>
                      <th className="px-6 py-4 text-center">Traditional Agency</th>
                      <th className="px-6 py-4 text-center bg-florida-orange-500">Central Florida SEO</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    <tr>
                      <td className="px-6 py-4 font-semibold">Monthly SEO Service</td>
                      <td className="px-6 py-4 text-center text-gray-600">$800 - $2,500</td>
                      <td className="px-6 py-4 text-center font-semibold text-florida-orange-600">$149 - $599</td>
                    </tr>
                    <tr className="bg-gray-50">
                      <td className="px-6 py-4 font-semibold">SEO Services Included</td>
                      <td className="px-6 py-4 text-center text-gray-600">5-10 Manual Services</td>
                      <td className="px-6 py-4 text-center font-semibold text-florida-orange-600">39 Automated Services</td>
                    </tr>
                    <tr>
                      <td className="px-6 py-4 font-semibold">Contract Requirement</td>
                      <td className="px-6 py-4 text-center text-gray-600">6-12 months</td>
                      <td className="px-6 py-4 text-center font-semibold text-florida-green-600">Month-to-month</td>
                    </tr>
                    <tr className="bg-gray-50">
                      <td className="px-6 py-4 font-semibold">Local Market Expertise</td>
                      <td className="px-6 py-4 text-center text-gray-600">Limited</td>
                      <td className="px-6 py-4 text-center font-semibold text-florida-green-600">Central Florida Focus</td>
                    </tr>
                    <tr>
                      <td className="px-6 py-4 font-semibold">Reporting Frequency</td>
                      <td className="px-6 py-4 text-center text-gray-600">Monthly</td>
                      <td className="px-6 py-4 text-center font-semibold text-florida-green-600">Real-time Dashboard</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </section>

        {/* Testimonials */}
        <section className="py-16">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl lg:text-4xl font-bold text-center text-gray-900 mb-12">
              What Our Clients Say About Our Pricing
            </h2>
            
            <div className="grid md:grid-cols-3 gap-8">
              {testimonials.map((testimonial, index) => (
                <blockquote key={index} className="bg-white rounded-xl p-6 shadow-lg">
                  <div className="text-gray-700 mb-4 italic leading-relaxed">
                    "{testimonial.quote}"
                  </div>
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-florida-blue-100 rounded-full flex items-center justify-center">
                      <span className="text-florida-blue-700 font-semibold">
                        {testimonial.author.split(' ').map(n => n[0]).join('')}
                      </span>
                    </div>
                    <div>
                      <div className="font-semibold text-gray-900">{testimonial.author}</div>
                      <div className="text-sm text-gray-600">{testimonial.title}</div>
                      {testimonial.company && (
                        <div className="text-sm text-gray-500">{testimonial.company}</div>
                      )}
                      {testimonial.savings && (
                        <div className="text-sm font-semibold text-florida-green-600">
                          Saves {testimonial.savings}
                        </div>
                      )}
                    </div>
                  </div>
                </blockquote>
              ))}
            </div>
          </div>
        </section>

        {/* FAQ Section */}
        <section className="py-16 bg-florida-blue-50">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl lg:text-4xl font-bold text-center text-gray-900 mb-12">
              Pricing Questions & Answers
            </h2>
            
            <div className="space-y-6">
              {faqs.map((faq, index) => (
                <div key={index} className="bg-white rounded-lg p-6 shadow-md">
                  <h3 className="text-lg font-semibold text-gray-900 mb-3">
                    {faq.question}
                  </h3>
                  <p className="text-gray-700 leading-relaxed">
                    {faq.answer}
                  </p>
                </div>
              ))}
            </div>
            
            <div className="text-center mt-8">
              <a 
                href="/faq" 
                className="inline-flex items-center space-x-2 text-florida-blue-600 hover:text-florida-blue-700 font-semibold"
              >
                <span>View all FAQs</span>
                <ArrowRight className="w-5 h-5" />
              </a>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-16 bg-gradient-to-r from-florida-blue-900 to-florida-blue-800 text-white">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="text-3xl lg:text-4xl font-bold mb-6">
              Ready to Start Growing Your Business?
            </h2>
            <p className="text-xl text-florida-blue-100 mb-8 leading-relaxed">
              Join 500+ Central Florida businesses using our affordable SEO services to dominate local search results.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <a 
                href="/contact" 
                className="inline-flex items-center justify-center px-8 py-4 bg-florida-orange-500 text-white font-semibold rounded-lg hover:bg-florida-orange-600 transition-colors"
              >
                Start with Free Consultation
              </a>
              <a 
                href="/faq" 
                className="inline-flex items-center justify-center px-8 py-4 bg-transparent border-2 border-white text-white font-semibold rounded-lg hover:bg-white hover:text-florida-blue-900 transition-colors"
              >
                Have Questions? View FAQ
              </a>
            </div>
            <p className="text-sm text-florida-blue-200 mt-4">
              No contracts • 60-day guarantee • Cancel anytime
            </p>
          </div>
        </section>
      </div>
    )
}
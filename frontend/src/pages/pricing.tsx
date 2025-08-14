import { Check, Star, ArrowRight, Shield, Zap, BarChart3 } from 'lucide-react'

const plans = [
  {
    name: "SEO Audit",
    price: "$64",
    period: "one-time",
    description: "Perfect for businesses wanting to understand their current SEO status",
    popular: false,
    features: [
      "Complete technical SEO audit (100+ checkpoints)",
      "Keyword opportunity analysis (up to 500 keywords)",
      "Competitor analysis (top 5 competitors)",
      "Local citation audit for Central Florida",
      "Google Business Profile optimization review",
      "Prioritized action plan with ROI estimates",
      "1-hour consultation call",
      "Mobile & Core Web Vitals assessment"
    ],
    cta: "Get SEO Audit",
    icon: BarChart3
  },
  {
    name: "Growth SEO",
    price: "$199",
    period: "per month",
    description: "Ideal for businesses ready to implement ongoing SEO improvements",
    popular: true,
    features: [
      "Everything in SEO Audit, plus:",
      "Monthly technical audits with issue prioritization",
      "Keyword research and tracking (up to 1,000 keywords)",
      "Content optimization recommendations",
      "Local SEO monitoring and improvement",
      "Google Business Profile management",
      "Monthly performance reports",
      "Bi-weekly strategy calls (30 mins)",
      "Email support with 24-hour response",
      "Competitor monitoring and alerts"
    ],
    cta: "Start Growth Plan",
    icon: Zap
  },
  {
    name: "Enterprise SEO",
    price: "$399",
    period: "per month",
    description: "For businesses serious about dominating their Central Florida market",
    popular: false,
    features: [
      "Everything in Growth SEO, plus:",
      "Advanced competitor intelligence",
      "Custom content brief generation",
      "Advanced technical monitoring with alerts",
      "Unlimited keyword tracking",
      "Weekly strategy sessions (60 mins)",
      "Priority phone and email support",
      "White-label reporting for agencies",
      "API access for custom integrations",
      "Dedicated account manager",
      "Custom dashboard and analytics"
    ],
    cta: "Go Enterprise",
    icon: Shield
  }
]

const testimonials = [
  {
    quote: "Switched from a $2,000/month agency to Central Florida SEO's Growth plan. Same results, 90% less cost!",
    author: "Mike Chen",
    title: "Owner, Orlando Web Design",
    savings: "$1,800/month"
  },
  {
    quote: "Their Enterprise plan gives us everything we need to manage 50+ client campaigns. The white-label reporting is perfect.",
    author: "Sarah Martinez", 
    title: "Digital Marketing Director",
    company: "Tampa Marketing Group"
  },
  {
    quote: "The SEO audit found 23 critical issues our previous agency missed. ROI paid for itself in the first month.",
    author: "David Rodriguez",
    title: "CEO, Miami Law Firm"
  }
]

const faqs = [
  {
    question: "Why are your prices 20% below market rates?",
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
    <>
      <title>SEO Pricing - Affordable Plans for Central Florida Businesses | Central Florida SEO</title>
      <meta name="description" content="Transparent SEO pricing starting at $64. Professional SEO services for Orlando, Tampa, and Miami businesses. No contracts, 20% below market rates." />
      
      <main className="min-h-screen bg-gradient-to-br from-florida-blue-50 to-white">
        {/* Hero Section */}
        <header className="bg-florida-blue-900 text-white py-16 lg:py-20">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6">
              Honest SEO Pricing
              <span className="block text-florida-orange-400 mt-2">20% Below Market Rates</span>
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
        </header>

        {/* Pricing Cards */}
        <section className="py-16 lg:py-24">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid lg:grid-cols-3 gap-8">
              {plans.map((plan, index) => (
                <div key={index} className={`relative bg-white rounded-2xl shadow-lg overflow-hidden ${plan.popular ? 'ring-2 ring-florida-orange-500 transform scale-105' : ''}`}>
                  {plan.popular && (
                    <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                      <div className="bg-florida-orange-500 text-white px-4 py-1 rounded-full text-sm font-semibold flex items-center space-x-1">
                        <Star className="w-4 h-4 fill-current" />
                        <span>Most Popular</span>
                      </div>
                    </div>
                  )}
                  
                  <div className="p-8">
                    <div className="flex items-center space-x-3 mb-4">
                      <div className="w-12 h-12 bg-florida-blue-100 rounded-lg flex items-center justify-center">
                        <plan.icon className="w-6 h-6 text-florida-blue-600" />
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

                    <ul className="space-y-3 mb-8">
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
                      <td className="px-6 py-4 text-center font-semibold text-florida-orange-600">$199 - $399</td>
                    </tr>
                    <tr className="bg-gray-50">
                      <td className="px-6 py-4 font-semibold">SEO Audit</td>
                      <td className="px-6 py-4 text-center text-gray-600">$500 - $1,200</td>
                      <td className="px-6 py-4 text-center font-semibold text-florida-orange-600">$64</td>
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
      </main>
    </>
  )
}
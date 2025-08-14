import { ChevronDownIcon, ChevronUpIcon } from 'lucide-react'
import { useState } from 'react'

const faqCategories = [
  {
    title: "Local SEO Basics",
    faqs: [
      {
        question: "What is local SEO and why do Central Florida businesses need it?",
        answer: "Local SEO is the process of optimizing your online presence to attract more business from relevant local searches in Central Florida. When someone searches for 'restaurants near me' or 'Orlando plumber,' local SEO helps your business appear in those results. For Central Florida businesses, this is crucial because 46% of all Google searches are seeking local information, and 76% of people who search for something nearby visit a business within a day."
      },
      {
        question: "How long does it take to see SEO results in the Orlando/Tampa market?",
        answer: "Most Central Florida businesses start seeing initial improvements within 30-90 days, with significant results typically appearing in 3-6 months. Local SEO often shows faster results than national SEO because you're competing in a smaller geographic area. We've helped Orlando restaurants rank on page 1 in as little as 8 weeks, and Tampa law firms see 40% traffic increases within 4 months."
      },
      {
        question: "What's the difference between SEO and Google Ads for local businesses?",
        answer: "SEO provides long-term organic visibility that builds over time, while Google Ads gives immediate visibility but stops when you stop paying. For Central Florida businesses, we recommend a combination: Google Ads for immediate results while building your SEO foundation. SEO typically costs 60% less than PPC long-term and generates 5x more clicks than paid ads."
      }
    ]
  },
  {
    title: "Our SEO Services",
    faqs: [
      {
        question: "What's included in your SEO audit for Central Florida businesses?",
        answer: "Our comprehensive SEO audit includes: technical SEO analysis (100+ checkpoints), local citation audit, Google Business Profile optimization review, competitor analysis, keyword opportunity assessment, content gap analysis, and mobile/Core Web Vitals evaluation. You'll receive a prioritized action plan with ROI estimates for each recommendation, plus a 1-hour consultation to discuss findings."
      },
      {
        question: "Do you work with businesses outside of Central Florida?",
        answer: "While we specialize in Central Florida markets (Orlando, Tampa, Miami, Jacksonville, and surrounding areas), we do work with businesses in other Florida markets. Our local expertise and understanding of Florida consumer behavior gives us an advantage, but our SEO strategies work nationwide. However, our pricing and case studies are specifically calibrated for Florida markets."
      },
      {
        question: "How do you measure SEO success for local businesses?",
        answer: "We track metrics that matter to your bottom line: local keyword rankings, Google Business Profile views and actions, organic traffic growth, phone calls and form submissions from organic search, online reviews and ratings, and most importantly - revenue attribution from organic search. Our dashboard shows real-time data with monthly detailed reports."
      }
    ]
  },
  {
    title: "Pricing & Packages",
    faqs: [
      {
        question: "Why are your prices 20% below market rates?",
        answer: "We believe quality SEO should be accessible to every Central Florida business, not just large corporations. By focusing specifically on the Florida market and leveraging our advanced AI-powered platform, we can offer enterprise-level services at small business prices. Our $64-$399 monthly packages provide better value than agencies charging $2,000+ per month."
      },
      {
        question: "Do you require long-term contracts?",
        answer: "No long-term contracts required! We offer month-to-month services because we're confident in our results. Most clients stay with us because they see real ROI, not because they're locked into a contract. You can cancel anytime with 30 days notice, though we recommend at least 6 months to see substantial results."
      },
      {
        question: "What's the difference between your Growth and Enterprise packages?",
        answer: "Growth Package ($199/month) is perfect for small to medium Central Florida businesses and includes monthly audits, keyword tracking up to 1,000 keywords, content recommendations, and bi-weekly calls. Enterprise Package ($399/month) adds advanced competitor intelligence, custom content briefs, unlimited keyword tracking, weekly strategy sessions, and white-label reporting for agencies."
      }
    ]
  },
  {
    title: "Technical Questions",
    faqs: [
      {
        question: "Will SEO work for my industry in Central Florida?",
        answer: "Yes! We've successfully helped businesses across industries: restaurants, law firms, medical practices, HVAC companies, real estate agents, retail stores, and more. Every business that serves local customers can benefit from SEO. In fact, competitive industries often see the biggest ROI because the cost of customer acquisition through SEO is much lower than traditional advertising."
      },
      {
        question: "How do you handle Google algorithm updates?",
        answer: "Our AI-powered platform monitors algorithm changes in real-time and automatically adjusts strategies. We follow Google's best practices and focus on creating genuine value for users, which protects against algorithm penalties. When updates happen, we analyze the impact on your rankings within 24 hours and make necessary adjustments."
      },
      {
        question: "Can you guarantee first page rankings on Google?",
        answer: "We don't guarantee specific rankings because Google's algorithm has over 200 ranking factors and changes frequently. However, we do guarantee measurable improvements in your online visibility, organic traffic, and lead generation. Our track record shows 85% of clients achieve first-page rankings for their target keywords within 6 months."
      }
    ]
  },
  {
    title: "Getting Started",
    faqs: [
      {
        question: "What information do you need to get started?",
        answer: "To begin, we need: your website URL, Google Analytics and Search Console access (we'll help set these up if needed), Google Business Profile access, a list of your main services and target locations, and your top 3 competitors. We'll handle the technical setup and provide step-by-step guidance for everything else."
      },
      {
        question: "How involved do I need to be in the SEO process?",
        answer: "We handle 90% of the technical work, but your input is valuable for content strategy and local market insights. Expect to spend about 2-3 hours per month: initial consultation, monthly strategy calls, and reviewing/approving content recommendations. We'll send you clear action items and handle implementation."
      },
      {
        question: "Do you work with WordPress, Shopify, or other platforms?",
        answer: "Yes! Our platform works with all major website platforms: WordPress, Shopify, Squarespace, Wix, custom HTML sites, and more. We provide platform-specific recommendations and can implement technical changes regardless of your website's technology stack."
      }
    ]
  }
]

function FAQItem({ faq, isOpen, onToggle }: { faq: any, isOpen: boolean, onToggle: () => void }) {
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        className="w-full px-6 py-4 text-left bg-white hover:bg-gray-50 focus:bg-gray-50 focus:outline-none transition-colors duration-200"
        onClick={onToggle}
        aria-expanded={isOpen}
      >
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 pr-4">
            {faq.question}
          </h3>
          {isOpen ? (
            <ChevronUpIcon className="w-5 h-5 text-florida-blue-600 flex-shrink-0" />
          ) : (
            <ChevronDownIcon className="w-5 h-5 text-florida-blue-600 flex-shrink-0" />
          )}
        </div>
      </button>
      
      {isOpen && (
        <div className="px-6 pb-4 bg-gray-50">
          <p className="text-gray-700 leading-relaxed">
            {faq.answer}
          </p>
        </div>
      )}
    </div>
  )
}

export default function FAQPage() {
  const [openItems, setOpenItems] = useState<string[]>([])

  const toggleItem = (categoryIndex: number, faqIndex: number) => {
    const itemId = `${categoryIndex}-${faqIndex}`
    setOpenItems(prev => 
      prev.includes(itemId) 
        ? prev.filter(id => id !== itemId)
        : [...prev, itemId]
    )
  }

  return (
    <>
      <title>FAQ - Central Florida SEO Services | Common Questions Answered</title>
      <meta name="description" content="Get answers to common SEO questions for Central Florida businesses. Learn about local SEO, pricing, services, and how to get started with professional SEO in Orlando, Tampa, and Miami." />
      
      <main className="min-h-screen bg-gradient-to-br from-florida-blue-50 to-white">
        {/* Hero Section */}
        <header className="bg-florida-blue-900 text-white py-16 lg:py-20">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h1 className="text-4xl md:text-5xl font-bold mb-6">
              Frequently Asked Questions
            </h1>
            <p className="text-xl text-florida-blue-100 leading-relaxed">
              Everything you need to know about SEO services for Central Florida businesses
            </p>
          </div>
        </header>

        {/* Quick Contact CTA */}
        <section className="py-8 bg-florida-orange-50 border-b border-florida-orange-100">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <p className="text-lg text-gray-700 mb-4">
              Don't see your question answered? We're here to help!
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <a 
                href="/contact" 
                className="inline-flex items-center justify-center px-6 py-3 bg-florida-blue-600 text-white font-semibold rounded-lg hover:bg-florida-blue-700 transition-colors"
              >
                Get Free Consultation
              </a>
              <a 
                href="tel:407-736-4769" 
                className="inline-flex items-center justify-center px-6 py-3 border-2 border-florida-blue-600 text-florida-blue-600 font-semibold rounded-lg hover:bg-florida-blue-600 hover:text-white transition-colors"
              >
                Call (407) 736-4769
              </a>
            </div>
          </div>
        </section>

        {/* FAQ Content */}
        <section className="py-16">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            {faqCategories.map((category, categoryIndex) => (
              <div key={categoryIndex} className="mb-12">
                <h2 className="text-2xl font-bold text-gray-900 mb-6 border-b border-gray-200 pb-3">
                  {category.title}
                </h2>
                
                <div className="space-y-4">
                  {category.faqs.map((faq, faqIndex) => (
                    <FAQItem
                      key={faqIndex}
                      faq={faq}
                      isOpen={openItems.includes(`${categoryIndex}-${faqIndex}`)}
                      onToggle={() => toggleItem(categoryIndex, faqIndex)}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Bottom CTA */}
        <section className="py-16 bg-florida-blue-900 text-white">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="text-3xl font-bold mb-6">
              Ready to Get Started with SEO?
            </h2>
            <p className="text-xl text-florida-blue-100 mb-8">
              Join 500+ Central Florida businesses using our platform to dominate local search results
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <a 
                href="/pricing" 
                className="inline-flex items-center justify-center px-8 py-4 bg-florida-orange-500 text-white font-semibold rounded-lg hover:bg-florida-orange-600 transition-colors"
              >
                View Pricing Plans
              </a>
              <a 
                href="/contact" 
                className="inline-flex items-center justify-center px-8 py-4 bg-transparent border-2 border-white text-white font-semibold rounded-lg hover:bg-white hover:text-florida-blue-900 transition-colors"
              >
                Get Free SEO Audit
              </a>
            </div>
          </div>
        </section>
      </main>
    </>
  )
}
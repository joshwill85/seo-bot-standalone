import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Button, 
  Typography, 
  Space, 
  Row, 
  Col, 
  Divider, 
  Modal, 
  Form, 
  Input, 
  Select, 
  DatePicker, 
  Switch,
  Badge,
  Tooltip,
  Collapse,
  message,
  Spin,
  Alert,
  Tag,
  Progress
} from 'antd';
import {
  InfoCircleOutlined,
  PlayCircleOutlined,
  SettingOutlined,
  SearchOutlined,
  FileTextOutlined,
  ToolOutlined,
  LinkOutlined,
  EnvironmentOutlined,
  EyeOutlined,
  TrophyOutlined,
  BarChartOutlined,
  RocketOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;
const { Option } = Select;

interface Customer {
  id: string;
  name: string;
  email: string;
  website: string;
  subscription_tier: string;
  industry: string;
  location: string;
  created_at: string;
}

interface SEOService {
  id: string;
  name: string;
  category: string;
  description: string;
  plain_explanation: string;
  technical_explanation: string;
  requires_input: boolean;
  input_fields: InputField[];
  estimated_time: string;
  automation_level: 'instant' | 'background' | 'scheduled';
  subscription_tiers: string[];
}

interface InputField {
  name: string;
  type: 'text' | 'url' | 'select' | 'number' | 'date' | 'textarea';
  label: string;
  required: boolean;
  options?: string[];
  placeholder?: string;
  validation?: string;
}

interface CustomerProfileManagerProps {
  customerId: string;
}

const CustomerProfileManager: React.FC<CustomerProfileManagerProps> = ({ customerId }) => {
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [services, setServices] = useState<Record<string, SEOService[]>>({});
  const [loading, setLoading] = useState(true);
  const [executingServices, setExecutingServices] = useState<Set<string>>(new Set());
  const [infoModal, setInfoModal] = useState<{
    visible: boolean;
    service?: SEOService;
  }>({ visible: false });
  const [inputModal, setInputModal] = useState<{
    visible: boolean;
    service?: SEOService;
  }>({ visible: false });
  const [form] = Form.useForm();

  // All 39 SEO Services with complete details
  const seoServices: Record<string, SEOService[]> = {
    keyword_research: [
      {
        id: 'discover_keywords',
        name: 'Discover New Keywords',
        category: 'keyword_research',
        description: 'Find 100+ keyword opportunities using advanced algorithms',
        plain_explanation: 'We automatically search for new keywords your customers might use to find your business. This helps you discover opportunities you might have missed and find new ways to attract visitors to your website.',
        technical_explanation: 'Uses semantic analysis, competitor keyword extraction, and search suggestion APIs to identify high-opportunity keywords. Analyzes search volume, competition, and relevance scores using machine learning algorithms.',
        requires_input: true,
        input_fields: [
          { name: 'seed_keywords', type: 'textarea', label: 'Seed Keywords', required: true, placeholder: 'Enter 3-5 main keywords separated by commas' },
          { name: 'target_location', type: 'text', label: 'Target Location', required: false, placeholder: 'City, State or Country' },
          { name: 'language', type: 'select', label: 'Language', required: true, options: ['English', 'Spanish', 'French', 'German'] }
        ],
        estimated_time: '15-30 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      },
      {
        id: 'keyword_gaps',
        name: 'Find Keyword Gaps',
        category: 'keyword_research',
        description: 'Identify competitor keyword advantages and missed opportunities',
        plain_explanation: 'We analyze what keywords your competitors are ranking for that you\'re not. This shows you exactly what opportunities you\'re missing and helps you catch up to or surpass your competition.',
        technical_explanation: 'Performs competitive keyword analysis using SERP data, identifies keyword gaps through set theory operations, and calculates opportunity scores based on search volume and ranking difficulty.',
        requires_input: true,
        input_fields: [
          { name: 'competitor_urls', type: 'textarea', label: 'Competitor URLs', required: true, placeholder: 'Enter 3-5 competitor websites, one per line' },
          { name: 'analysis_depth', type: 'select', label: 'Analysis Depth', required: true, options: ['Basic', 'Comprehensive', 'Deep Dive'] }
        ],
        estimated_time: '20-45 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      },
      {
        id: 'keyword_rankings',
        name: 'Update Keyword Rankings',
        category: 'keyword_research',
        description: 'Fresh ranking data and position tracking',
        plain_explanation: 'We check where your website currently ranks for your target keywords in Google search results. This helps you track your progress and see which keywords need more work.',
        technical_explanation: 'Performs automated SERP position tracking using headless browser automation, tracks ranking fluctuations, and provides historical ranking data analysis with trend detection.',
        requires_input: false,
        input_fields: [],
        estimated_time: '10-20 minutes',
        automation_level: 'background',
        subscription_tiers: ['starter', 'professional', 'enterprise']
      },
      {
        id: 'keyword_clusters',
        name: 'Create Keyword Clusters',
        category: 'keyword_research',
        description: 'Organize keywords into content themes and topic clusters',
        plain_explanation: 'We group related keywords together to help you create focused content. Instead of targeting random keywords, you\'ll have organized groups that work together to improve your rankings.',
        technical_explanation: 'Uses semantic similarity algorithms and NLP techniques to cluster keywords by topical relevance, creates content pillar strategies, and optimizes internal linking architecture.',
        requires_input: true,
        input_fields: [
          { name: 'keyword_list', type: 'textarea', label: 'Keywords to Cluster', required: true, placeholder: 'Enter keywords separated by commas' },
          { name: 'cluster_size', type: 'select', label: 'Cluster Size', required: true, options: ['Small (5-10)', 'Medium (10-20)', 'Large (20-30)'] }
        ],
        estimated_time: '25-40 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      },
      {
        id: 'local_keywords',
        name: 'Local Keyword Research',
        category: 'keyword_research',
        description: 'Location-specific keyword discovery and local search optimization',
        plain_explanation: 'We find keywords that people in your area are searching for. This is perfect for local businesses who want to attract nearby customers searching for services "near me".',
        technical_explanation: 'Performs geo-targeted keyword research using location-based search data, analyzes local search intent, and identifies location-specific long-tail opportunities.',
        requires_input: true,
        input_fields: [
          { name: 'business_location', type: 'text', label: 'Business Location', required: true, placeholder: 'City, State' },
          { name: 'service_radius', type: 'number', label: 'Service Radius (miles)', required: true, placeholder: '25' },
          { name: 'business_type', type: 'text', label: 'Business Type', required: true, placeholder: 'restaurant, dentist, plumber, etc.' }
        ],
        estimated_time: '20-35 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      }
    ],
    content_strategy: [
      {
        id: 'content_calendar',
        name: 'Generate Content Calendar',
        category: 'content_strategy',
        description: '3-month SEO-optimized content planning',
        plain_explanation: 'We create a complete 3-month plan of what content to write and when to publish it. Each piece is designed to target specific keywords and attract your ideal customers.',
        technical_explanation: 'Generates content calendars based on keyword seasonality, search volume trends, and competitive content gaps. Includes content types, target keywords, and publishing schedules.',
        requires_input: true,
        input_fields: [
          { name: 'content_frequency', type: 'select', label: 'Content Frequency', required: true, options: ['Weekly', 'Bi-weekly', 'Monthly'] },
          { name: 'content_types', type: 'select', label: 'Content Types', required: true, options: ['Blog Posts', 'Videos', 'Infographics', 'All Types'] },
          { name: 'target_audience', type: 'text', label: 'Target Audience', required: true, placeholder: 'small business owners, homeowners, etc.' }
        ],
        estimated_time: '30-45 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      },
      {
        id: 'content_brief',
        name: 'Create Content Brief',
        category: 'content_strategy',
        description: 'SEO-optimized content briefs with keyword targeting',
        plain_explanation: 'We create detailed instructions for writing content that will rank well in Google. Each brief tells you exactly what to write about, which keywords to use, and how to structure your content.',
        technical_explanation: 'Generates comprehensive content briefs including target keywords, semantic keywords, content structure, word count recommendations, and SERP analysis of top-ranking pages.',
        requires_input: true,
        input_fields: [
          { name: 'target_keyword', type: 'text', label: 'Target Keyword', required: true, placeholder: 'Main keyword to target' },
          { name: 'content_type', type: 'select', label: 'Content Type', required: true, options: ['Blog Post', 'Landing Page', 'Product Page', 'Service Page'] },
          { name: 'target_word_count', type: 'number', label: 'Target Word Count', required: false, placeholder: '1500' }
        ],
        estimated_time: '15-25 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      },
      {
        id: 'content_audit',
        name: 'Audit Existing Content',
        category: 'content_strategy',
        description: 'Performance analysis and optimization recommendations',
        plain_explanation: 'We analyze all your existing content to see what\'s working and what\'s not. You\'ll get specific recommendations on how to improve your content to get more traffic and better rankings.',
        technical_explanation: 'Performs comprehensive content audits including traffic analysis, keyword cannibalization detection, content gap identification, and optimization recommendations based on search performance.',
        requires_input: false,
        input_fields: [],
        estimated_time: '45-60 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      },
      {
        id: 'meta_optimization',
        name: 'Optimize Meta Tags',
        category: 'content_strategy',
        description: 'Title tags, meta descriptions, and header optimization',
        plain_explanation: 'We optimize the titles and descriptions that appear in Google search results. Better meta tags mean more people will click on your website when they see it in search results.',
        technical_explanation: 'Analyzes and optimizes title tags, meta descriptions, and header tags for optimal CTR and keyword targeting. Uses SERP analysis to create compelling, click-worthy meta content.',
        requires_input: false,
        input_fields: [],
        estimated_time: '30-45 minutes',
        automation_level: 'background',
        subscription_tiers: ['starter', 'professional', 'enterprise']
      },
      {
        id: 'content_clusters',
        name: 'Build Content Clusters',
        category: 'content_strategy',
        description: 'Topic cluster strategies and internal linking plans',
        plain_explanation: 'We organize your content into related groups and create a linking strategy between them. This helps Google understand your expertise and can significantly boost your rankings.',
        technical_explanation: 'Creates topic cluster architecture with pillar pages and supporting content, optimizes internal linking structure, and develops content hierarchies for topical authority.',
        requires_input: true,
        input_fields: [
          { name: 'main_topics', type: 'textarea', label: 'Main Topics', required: true, placeholder: 'Enter 3-5 main topics your business covers' },
          { name: 'cluster_depth', type: 'select', label: 'Cluster Depth', required: true, options: ['Shallow (2 levels)', 'Medium (3 levels)', 'Deep (4+ levels)'] }
        ],
        estimated_time: '40-60 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      }
    ],
    technical_seo: [
      {
        id: 'technical_audit',
        name: 'Run Technical Audit',
        category: 'technical_seo',
        description: 'Comprehensive 18-category technical SEO audit',
        plain_explanation: 'We check your website for technical problems that might be hurting your Google rankings. This includes loading speed, mobile-friendliness, broken links, and many other technical factors.',
        technical_explanation: 'Performs comprehensive technical SEO audit covering crawlability, indexability, site architecture, Core Web Vitals, structured data, and 18 additional technical categories.',
        requires_input: false,
        input_fields: [],
        estimated_time: '60-90 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      },
      {
        id: 'site_speed',
        name: 'Check Site Speed',
        category: 'technical_seo',
        description: 'Core Web Vitals analysis and performance optimization',
        plain_explanation: 'We test how fast your website loads and identify what\'s slowing it down. Faster websites rank better in Google and provide a better experience for your visitors.',
        technical_explanation: 'Analyzes Core Web Vitals (LCP, FID, CLS), performs Lighthouse audits, identifies performance bottlenecks, and provides specific optimization recommendations.',
        requires_input: false,
        input_fields: [],
        estimated_time: '20-30 minutes',
        automation_level: 'background',
        subscription_tiers: ['starter', 'professional', 'enterprise']
      },
      {
        id: 'mobile_audit',
        name: 'Audit Mobile Optimization',
        category: 'technical_seo',
        description: 'Mobile-friendliness and responsive design analysis',
        plain_explanation: 'We check how well your website works on phones and tablets. Since most people search on mobile devices, having a mobile-friendly site is crucial for good rankings.',
        technical_explanation: 'Performs mobile usability testing, responsive design analysis, mobile page speed testing, and mobile-specific SEO factor evaluation.',
        requires_input: false,
        input_fields: [],
        estimated_time: '25-35 minutes',
        automation_level: 'background',
        subscription_tiers: ['starter', 'professional', 'enterprise']
      },
      {
        id: 'indexability_check',
        name: 'Check Page Indexability',
        category: 'technical_seo',
        description: 'Search engine crawlability and indexation issues',
        plain_explanation: 'We make sure Google can find and properly index all your important pages. If Google can\'t see your pages, they won\'t show up in search results.',
        technical_explanation: 'Analyzes robots.txt, XML sitemaps, meta robots tags, canonical tags, and crawl accessibility to ensure optimal search engine indexation.',
        requires_input: false,
        input_fields: [],
        estimated_time: '30-40 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      },
      {
        id: 'schema_audit',
        name: 'Audit Schema Markup',
        category: 'technical_seo',
        description: 'Structured data opportunities and implementation',
        plain_explanation: 'We add special code to your website that helps Google understand your content better. This can lead to rich snippets in search results, like star ratings or price information.',
        technical_explanation: 'Audits existing structured data implementation, identifies schema markup opportunities, validates JSON-LD and microdata, and recommends schema types for enhanced SERP features.',
        requires_input: false,
        input_fields: [],
        estimated_time: '35-45 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      }
    ],
    link_building: [
      {
        id: 'link_opportunities',
        name: 'Find Link Opportunities',
        category: 'link_building',
        description: 'High-quality backlink prospect identification',
        plain_explanation: 'We find websites that might link to your content. Quality backlinks from other websites are one of the strongest ranking factors in Google\'s algorithm.',
        technical_explanation: 'Identifies high-authority link prospects using competitor backlink analysis, content gap analysis, and domain authority metrics to find relevant linking opportunities.',
        requires_input: true,
        input_fields: [
          { name: 'target_topics', type: 'textarea', label: 'Target Topics', required: true, placeholder: 'Topics you want links for' },
          { name: 'min_domain_authority', type: 'number', label: 'Minimum Domain Authority', required: false, placeholder: '30' },
          { name: 'target_regions', type: 'text', label: 'Target Regions', required: false, placeholder: 'US, UK, etc.' }
        ],
        estimated_time: '45-60 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      },
      {
        id: 'competitor_backlinks',
        name: 'Analyze Competitor Backlinks',
        category: 'link_building',
        description: 'Competitive backlink intelligence and analysis',
        plain_explanation: 'We analyze where your competitors are getting their backlinks from. This shows you exactly which websites you should target for your own link building efforts.',
        technical_explanation: 'Performs comprehensive competitor backlink analysis, identifies high-value link sources, analyzes anchor text distribution, and discovers competitor link building strategies.',
        requires_input: true,
        input_fields: [
          { name: 'competitor_domains', type: 'textarea', label: 'Competitor Domains', required: true, placeholder: 'Enter competitor websites, one per line' },
          { name: 'analysis_timeframe', type: 'select', label: 'Analysis Timeframe', required: true, options: ['Last 3 months', 'Last 6 months', 'Last year'] }
        ],
        estimated_time: '30-45 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      },
      {
        id: 'broken_links',
        name: 'Find Broken Links',
        category: 'link_building',
        description: 'Broken link building opportunities and outreach targets',
        plain_explanation: 'We find broken links on other websites that you could replace with links to your content. This is a win-win: you get a backlink and they fix their broken link.',
        technical_explanation: 'Identifies broken external links on relevant websites, matches broken links with suitable replacement content, and creates outreach opportunities for link acquisition.',
        requires_input: true,
        input_fields: [
          { name: 'target_niches', type: 'textarea', label: 'Target Niches', required: true, placeholder: 'Industries or topics related to your business' },
          { name: 'max_prospects', type: 'number', label: 'Max Prospects', required: false, placeholder: '50' }
        ],
        estimated_time: '40-55 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      },
      {
        id: 'build_citations',
        name: 'Build Citations',
        category: 'link_building',
        description: 'Directory submissions and local citation building',
        plain_explanation: 'We submit your business information to online directories and citation sites. This helps with local SEO and provides consistent business information across the web.',
        technical_explanation: 'Automates citation building across high-authority business directories, ensures NAP consistency, and monitors citation quality and accuracy.',
        requires_input: true,
        input_fields: [
          { name: 'business_name', type: 'text', label: 'Business Name', required: true, placeholder: 'Exact business name' },
          { name: 'business_address', type: 'textarea', label: 'Business Address', required: true, placeholder: 'Full business address' },
          { name: 'business_phone', type: 'text', label: 'Business Phone', required: true, placeholder: '(555) 123-4567' },
          { name: 'business_category', type: 'text', label: 'Business Category', required: true, placeholder: 'restaurant, law firm, etc.' }
        ],
        estimated_time: '60-90 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      },
      {
        id: 'monitor_backlinks',
        name: 'Monitor Backlinks',
        category: 'link_building',
        description: 'Link tracking, quality assessment, and alert systems',
        plain_explanation: 'We continuously monitor your backlinks to track new links, identify lost links, and alert you to any low-quality or potentially harmful links pointing to your site.',
        technical_explanation: 'Monitors backlink profile changes, tracks link quality metrics, identifies toxic links, and provides automated alerts for significant backlink changes.',
        requires_input: false,
        input_fields: [],
        estimated_time: 'Ongoing',
        automation_level: 'scheduled',
        subscription_tiers: ['professional', 'enterprise']
      }
    ],
    local_seo: [
      {
        id: 'gmb_optimization',
        name: 'Optimize Google My Business',
        category: 'local_seo',
        description: 'Complete GMB optimization and management',
        plain_explanation: 'We optimize your Google My Business profile to help you show up in local search results and Google Maps. This is crucial for attracting nearby customers.',
        technical_explanation: 'Optimizes GMB profile completeness, manages categories and attributes, optimizes business description and services, and implements GMB posting strategy.',
        requires_input: true,
        input_fields: [
          { name: 'gmb_url', type: 'url', label: 'Google My Business URL', required: false, placeholder: 'Your GMB profile URL' },
          { name: 'primary_category', type: 'text', label: 'Primary Business Category', required: true, placeholder: 'Restaurant, Dentist, etc.' },
          { name: 'service_areas', type: 'textarea', label: 'Service Areas', required: false, placeholder: 'Areas you serve' }
        ],
        estimated_time: '45-60 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      },
      {
        id: 'citation_audit',
        name: 'Audit Local Citations',
        category: 'local_seo',
        description: 'NAP consistency checking and citation optimization',
        plain_explanation: 'We check that your business name, address, and phone number are consistent across all online directories. Inconsistent information can hurt your local rankings.',
        technical_explanation: 'Audits NAP (Name, Address, Phone) consistency across major citation sources, identifies citation gaps and inconsistencies, and provides correction recommendations.',
        requires_input: false,
        input_fields: [],
        estimated_time: '30-45 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      },
      {
        id: 'location_pages',
        name: 'Create Location Pages',
        category: 'local_seo',
        description: 'Location-specific landing page optimization',
        plain_explanation: 'We create or optimize pages specifically for each location you serve. This helps you rank for "services near me" searches in multiple areas.',
        technical_explanation: 'Creates location-specific landing pages with optimized content, local keywords, and structured data markup for multi-location businesses.',
        requires_input: true,
        input_fields: [
          { name: 'locations', type: 'textarea', label: 'Business Locations', required: true, placeholder: 'Enter each location on a new line' },
          { name: 'services_offered', type: 'textarea', label: 'Services Offered', required: true, placeholder: 'Services available at each location' }
        ],
        estimated_time: '60-90 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      },
      {
        id: 'review_monitoring',
        name: 'Monitor Reviews',
        category: 'local_seo',
        description: 'Review tracking, management, and response strategies',
        plain_explanation: 'We monitor reviews across all platforms and help you respond appropriately. Good reviews and review management are important ranking factors for local search.',
        technical_explanation: 'Monitors reviews across Google, Yelp, Facebook, and other platforms, provides review response templates, and tracks review sentiment and trends.',
        requires_input: false,
        input_fields: [],
        estimated_time: 'Ongoing',
        automation_level: 'scheduled',
        subscription_tiers: ['professional', 'enterprise']
      },
      {
        id: 'local_schema',
        name: 'Optimize Local Schema',
        category: 'local_seo',
        description: 'Local business structured data implementation',
        plain_explanation: 'We add special code to your website that tells Google exactly what type of business you are, your location, hours, and services. This helps with local search visibility.',
        technical_explanation: 'Implements LocalBusiness schema markup, optimizes business hours and contact information, and adds location-specific structured data for enhanced local search presence.',
        requires_input: false,
        input_fields: [],
        estimated_time: '20-30 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      }
    ],
    competitor_analysis: [
      {
        id: 'discover_competitors',
        name: 'Discover Competitors',
        category: 'competitor_analysis',
        description: 'Automatic competitor identification and analysis',
        plain_explanation: 'We identify who your real SEO competitors are - not just your business competitors, but websites that compete with you for the same keywords in search results.',
        technical_explanation: 'Uses keyword overlap analysis and SERP competition to identify organic search competitors, analyzes competitor domain authority and topical relevance.',
        requires_input: false,
        input_fields: [],
        estimated_time: '25-35 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      },
      {
        id: 'competitor_content',
        name: 'Analyze Competitor Content',
        category: 'competitor_analysis',
        description: 'Content strategy analysis and gap identification',
        plain_explanation: 'We analyze what type of content your competitors are creating and how well it\'s performing. This shows you what content gaps you can fill to outrank them.',
        technical_explanation: 'Performs competitor content analysis including content types, publishing frequency, content performance metrics, and identifies content gap opportunities.',
        requires_input: true,
        input_fields: [
          { name: 'competitor_list', type: 'textarea', label: 'Competitors to Analyze', required: true, placeholder: 'Enter competitor websites, one per line' },
          { name: 'content_types', type: 'select', label: 'Content Types to Analyze', required: true, options: ['Blog Posts', 'Product Pages', 'Service Pages', 'All Content'] }
        ],
        estimated_time: '40-55 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      },
      {
        id: 'technical_comparison',
        name: 'Compare Technical SEO',
        category: 'competitor_analysis',
        description: 'Technical performance comparison and benchmarking',
        plain_explanation: 'We compare your website\'s technical performance against your competitors. This shows you where you\'re falling behind and what technical improvements could give you an advantage.',
        technical_explanation: 'Benchmarks technical SEO performance including site speed, mobile optimization, structured data implementation, and technical best practices against competitors.',
        requires_input: true,
        input_fields: [
          { name: 'competitors_to_compare', type: 'textarea', label: 'Competitors for Comparison', required: true, placeholder: 'Enter up to 5 competitor websites' },
          { name: 'comparison_metrics', type: 'select', label: 'Metrics to Compare', required: true, options: ['Site Speed', 'Mobile Performance', 'Technical SEO', 'All Metrics'] }
        ],
        estimated_time: '35-50 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      },
      {
        id: 'competitor_monitoring',
        name: 'Monitor Competitor Changes',
        category: 'competitor_analysis',
        description: 'Competitive tracking and opportunity alerts',
        plain_explanation: 'We continuously monitor your competitors for changes in their SEO strategy, new content, and ranking improvements. You\'ll get alerts when opportunities arise.',
        technical_explanation: 'Monitors competitor ranking changes, new content publication, backlink acquisition, and technical modifications with automated alerting for strategic opportunities.',
        requires_input: false,
        input_fields: [],
        estimated_time: 'Ongoing',
        automation_level: 'scheduled',
        subscription_tiers: ['professional', 'enterprise']
      }
    ],
    conversion_optimization: [
      {
        id: 'funnel_audit',
        name: 'Audit Conversion Funnels',
        category: 'conversion_optimization',
        description: 'Conversion path analysis and optimization',
        plain_explanation: 'We analyze the path visitors take on your website from first visit to becoming a customer. We identify where people are dropping off and how to improve conversion rates.',
        technical_explanation: 'Analyzes user journey and conversion paths, identifies funnel drop-off points, performs conversion rate analysis, and provides optimization recommendations.',
        requires_input: true,
        input_fields: [
          { name: 'conversion_goals', type: 'textarea', label: 'Conversion Goals', required: true, placeholder: 'Purchase, signup, contact form, etc.' },
          { name: 'analytics_access', type: 'select', label: 'Analytics Access', required: true, options: ['Google Analytics', 'Other Platform', 'Need Setup'] }
        ],
        estimated_time: '50-70 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      },
      {
        id: 'landing_page_optimization',
        name: 'Optimize Landing Pages',
        category: 'conversion_optimization',
        description: 'Page optimization for conversion improvement',
        plain_explanation: 'We optimize your landing pages to convert more visitors into customers. This includes improving headlines, calls-to-action, page layout, and removing friction points.',
        technical_explanation: 'Performs landing page conversion optimization including A/B testing recommendations, CRO best practices implementation, and user experience improvements.',
        requires_input: true,
        input_fields: [
          { name: 'target_pages', type: 'textarea', label: 'Pages to Optimize', required: true, placeholder: 'URLs of landing pages to optimize' },
          { name: 'optimization_focus', type: 'select', label: 'Optimization Focus', required: true, options: ['Lead Generation', 'Sales', 'Engagement', 'All Areas'] }
        ],
        estimated_time: '45-60 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      },
      {
        id: 'form_optimization',
        name: 'Optimize Forms',
        category: 'conversion_optimization',
        description: 'Form completion rates and user experience enhancement',
        plain_explanation: 'We analyze and optimize your contact forms, signup forms, and checkout processes to reduce abandonment and increase completions.',
        technical_explanation: 'Analyzes form completion rates, identifies friction points, optimizes form fields and layout, and implements form optimization best practices.',
        requires_input: false,
        input_fields: [],
        estimated_time: '30-45 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      },
      {
        id: 'mobile_conversions',
        name: 'Mobile Conversion Optimization',
        category: 'conversion_optimization',
        description: 'Mobile-specific conversion optimization',
        plain_explanation: 'We optimize your website specifically for mobile users to convert better on phones and tablets. Mobile optimization is crucial since most traffic comes from mobile devices.',
        technical_explanation: 'Optimizes mobile conversion paths, improves mobile UX, analyzes mobile-specific conversion barriers, and implements mobile-first conversion strategies.',
        requires_input: false,
        input_fields: [],
        estimated_time: '40-55 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      }
    ],
    analytics_reporting: [
      {
        id: 'seo_reporting',
        name: 'Generate SEO Reports',
        category: 'analytics_reporting',
        description: 'Comprehensive performance reports and insights',
        plain_explanation: 'We create detailed reports showing your SEO progress, including rankings, traffic, and performance metrics. Perfect for tracking progress and sharing with stakeholders.',
        technical_explanation: 'Generates comprehensive SEO performance reports including organic traffic, keyword rankings, technical health, and competitive benchmarking with actionable insights.',
        requires_input: true,
        input_fields: [
          { name: 'report_frequency', type: 'select', label: 'Report Frequency', required: true, options: ['Weekly', 'Monthly', 'Quarterly'] },
          { name: 'report_recipients', type: 'textarea', label: 'Report Recipients', required: false, placeholder: 'Email addresses for report delivery' },
          { name: 'custom_metrics', type: 'textarea', label: 'Custom Metrics', required: false, placeholder: 'Specific metrics to track' }
        ],
        estimated_time: '30-45 minutes',
        automation_level: 'scheduled',
        subscription_tiers: ['professional', 'enterprise']
      },
      {
        id: 'roi_calculation',
        name: 'Calculate ROI',
        category: 'analytics_reporting',
        description: 'SEO investment analysis and return calculations',
        plain_explanation: 'We calculate the return on investment from your SEO efforts, showing you exactly how much revenue your SEO is generating compared to what you\'re spending.',
        technical_explanation: 'Calculates SEO ROI using conversion tracking, revenue attribution, organic traffic value, and cost analysis to demonstrate SEO investment returns.',
        requires_input: true,
        input_fields: [
          { name: 'monthly_seo_budget', type: 'number', label: 'Monthly SEO Budget', required: true, placeholder: '5000' },
          { name: 'average_order_value', type: 'number', label: 'Average Order Value', required: false, placeholder: '150' },
          { name: 'conversion_rate', type: 'number', label: 'Website Conversion Rate (%)', required: false, placeholder: '2.5' }
        ],
        estimated_time: '25-35 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      },
      {
        id: 'serp_features',
        name: 'Track SERP Features',
        category: 'analytics_reporting',
        description: 'Featured snippet opportunities and monitoring',
        plain_explanation: 'We monitor opportunities for featured snippets, image packs, and other special search result features that can dramatically increase your visibility.',
        technical_explanation: 'Tracks SERP feature opportunities including featured snippets, image packs, local packs, and knowledge panels with optimization recommendations.',
        requires_input: false,
        input_fields: [],
        estimated_time: 'Ongoing',
        automation_level: 'scheduled',
        subscription_tiers: ['professional', 'enterprise']
      }
    ],
    automation_management: [
      {
        id: 'setup_schedules',
        name: 'Setup Automated Schedules',
        category: 'automation_management',
        description: 'Configure daily, weekly, monthly automation',
        plain_explanation: 'We set up automated schedules for your SEO tasks so they run automatically without you having to remember. You can schedule daily, weekly, or monthly SEO maintenance.',
        technical_explanation: 'Configures automated workflow schedules using cron jobs and task queues, sets up monitoring and alerting for automated tasks, and manages execution priorities.',
        requires_input: true,
        input_fields: [
          { name: 'automation_preferences', type: 'select', label: 'Automation Level', required: true, options: ['Minimal', 'Moderate', 'Aggressive'] },
          { name: 'preferred_schedule', type: 'select', label: 'Preferred Schedule', required: true, options: ['Daily', 'Weekly', 'Monthly', 'Custom'] },
          { name: 'notification_email', type: 'text', label: 'Notification Email', required: true, placeholder: 'Email for automation alerts' }
        ],
        estimated_time: '20-30 minutes',
        automation_level: 'instant',
        subscription_tiers: ['professional', 'enterprise']
      },
      {
        id: 'manage_alerts',
        name: 'Manage Alerts & Notifications',
        category: 'automation_management',
        description: 'Custom alert systems and notification preferences',
        plain_explanation: 'We set up custom alerts to notify you about important SEO changes, opportunities, or issues that need attention. Stay informed without having to constantly check.',
        technical_explanation: 'Configures custom alerting systems for ranking changes, technical issues, backlink changes, and competitive movements with customizable thresholds and delivery methods.',
        requires_input: true,
        input_fields: [
          { name: 'alert_types', type: 'select', label: 'Alert Types', required: true, options: ['Ranking Changes', 'Technical Issues', 'New Opportunities', 'All Alerts'] },
          { name: 'alert_frequency', type: 'select', label: 'Alert Frequency', required: true, options: ['Immediate', 'Daily Summary', 'Weekly Summary'] },
          { name: 'alert_methods', type: 'select', label: 'Alert Methods', required: true, options: ['Email', 'SMS', 'Dashboard Only'] }
        ],
        estimated_time: '15-25 minutes',
        automation_level: 'instant',
        subscription_tiers: ['professional', 'enterprise']
      },
      {
        id: 'bulk_optimization',
        name: 'Bulk Site Optimization',
        category: 'automation_management',
        description: 'Site-wide SEO execution and batch processing',
        plain_explanation: 'We run multiple SEO optimizations across your entire website at once. This is perfect for implementing site-wide improvements efficiently.',
        technical_explanation: 'Executes batch SEO optimizations including site-wide meta tag updates, internal linking improvements, and technical SEO fixes using automated processing.',
        requires_input: true,
        input_fields: [
          { name: 'optimization_scope', type: 'select', label: 'Optimization Scope', required: true, options: ['Entire Site', 'Specific Section', 'Priority Pages'] },
          { name: 'optimization_types', type: 'select', label: 'Optimization Types', required: true, options: ['Technical SEO', 'Content Optimization', 'All Optimizations'] }
        ],
        estimated_time: '90-120 minutes',
        automation_level: 'background',
        subscription_tiers: ['professional', 'enterprise']
      }
    ]
  };

  // Category icons and colors
  const categoryConfig = {
    keyword_research: { icon: <SearchOutlined />, color: '#1890ff', title: 'Keyword Research & Strategy' },
    content_strategy: { icon: <FileTextOutlined />, color: '#52c41a', title: 'Content Strategy & Optimization' },
    technical_seo: { icon: <ToolOutlined />, color: '#fa8c16', title: 'Technical SEO Auditing' },
    link_building: { icon: <LinkOutlined />, color: '#722ed1', title: 'Link Building & Authority' },
    local_seo: { icon: <EnvironmentOutlined />, color: '#13c2c2', title: 'Local SEO Optimization' },
    competitor_analysis: { icon: <EyeOutlined />, color: '#eb2f96', title: 'Competitor Analysis & Intelligence' },
    conversion_optimization: { icon: <TrophyOutlined />, color: '#f5222d', title: 'Conversion Rate Optimization' },
    analytics_reporting: { icon: <BarChartOutlined />, color: '#faad14', title: 'Analytics & Performance Reporting' },
    automation_management: { icon: <SettingOutlined />, color: '#666', title: 'Automation & Workflow Management' }
  };

  useEffect(() => {
    fetchCustomerData();
    setServices(seoServices);
    setLoading(false);
  }, [customerId]);

  const fetchCustomerData = async () => {
    try {
      const response = await fetch(`/api/v1/customers/${customerId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });
      const data = await response.json();
      setCustomer(data);
    } catch (error) {
      console.error('Failed to fetch customer data:', error);
      message.error('Failed to load customer data');
    }
  };

  const executeService = async (service: SEOService, parameters: Record<string, any> = {}) => {
    setExecutingServices(prev => new Set(prev).add(service.id));
    
    try {
      const response = await fetch('/api/v1/dashboard/execute-workflow', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          button_id: service.id,
          parameters: {
            customer_id: customerId,
            website: customer?.website,
            ...parameters
          },
          priority: 'normal'
        })
      });

      if (!response.ok) {
        throw new Error('Failed to execute service');
      }

      const result = await response.json();
      message.success(`${service.name} started successfully`);
      
    } catch (error: any) {
      console.error('Failed to execute service:', error);
      message.error(error.message || 'Failed to execute service');
    } finally {
      setExecutingServices(prev => {
        const updated = new Set(prev);
        updated.delete(service.id);
        return updated;
      });
    }
  };

  const executeAllServices = async (category?: string) => {
    const servicesToExecute = category 
      ? services[category] || []
      : Object.values(services).flat();

    const availableServices = servicesToExecute.filter(service => 
      customer?.subscription_tier && service.subscription_tiers.includes(customer.subscription_tier)
    );

    if (availableServices.length === 0) {
      message.warning('No services available for your subscription tier');
      return;
    }

    message.info(`Starting ${availableServices.length} SEO services...`);

    // Execute services with rate limiting
    for (const service of availableServices) {
      if (!service.requires_input) {
        await executeService(service);
        // Small delay to prevent overwhelming the system
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }
  };

  const handleServiceWithInput = (service: SEOService) => {
    if (service.requires_input) {
      setInputModal({ visible: true, service });
    } else {
      executeService(service);
    }
  };

  const handleInputSubmit = async (values: any) => {
    if (inputModal.service) {
      await executeService(inputModal.service, values);
      setInputModal({ visible: false });
      form.resetFields();
    }
  };

  const renderServiceCard = (service: SEOService) => {
    const isExecuting = executingServices.has(service.id);
    const isAvailable = customer?.subscription_tier && service.subscription_tiers.includes(customer.subscription_tier);
    const categoryConf = categoryConfig[service.category as keyof typeof categoryConfig];

    return (
      <Card
        key={service.id}
        size="small"
        hoverable={isAvailable}
        className={`service-card ${!isAvailable ? 'disabled' : ''}`}
        actions={[
          <Tooltip title="Service Information">
            <Button
              type="text"
              icon={<InfoCircleOutlined />}
              onClick={() => setInfoModal({ visible: true, service })}
            />
          </Tooltip>,
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            loading={isExecuting}
            disabled={!isAvailable || isExecuting}
            onClick={() => handleServiceWithInput(service)}
          >
            {isExecuting ? 'Running...' : 'Launch'}
          </Button>
        ]}
      >
        <Card.Meta
          title={
            <Space>
              {service.name}
              <Badge 
                color={categoryConf?.color} 
                text={service.automation_level}
                style={{ fontSize: '10px' }}
              />
            </Space>
          }
          description={
            <div>
              <Paragraph ellipsis={{ rows: 2 }} style={{ marginBottom: 8, fontSize: '12px' }}>
                {service.description}
              </Paragraph>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text type="secondary" style={{ fontSize: '11px' }}>
                  ⏱️ {service.estimated_time}
                </Text>
                {service.requires_input && (
                  <Tag color="blue" style={{ fontSize: '10px' }}>
                    Requires Input
                  </Tag>
                )}
              </div>
              {!isAvailable && (
                <Alert
                  message="Upgrade Required"
                  type="warning"
                  size="small"
                  style={{ marginTop: 8 }}
                />
              )}
            </div>
          }
        />
      </Card>
    );
  };

  const renderInputForm = () => {
    if (!inputModal.service) return null;

    return (
      <Form
        form={form}
        layout="vertical"
        onFinish={handleInputSubmit}
      >
        {inputModal.service.input_fields.map((field) => (
          <Form.Item
            key={field.name}
            name={field.name}
            label={field.label}
            rules={[{ required: field.required, message: `${field.label} is required` }]}
          >
            {field.type === 'textarea' ? (
              <Input.TextArea 
                placeholder={field.placeholder}
                rows={3}
              />
            ) : field.type === 'select' ? (
              <Select placeholder={field.placeholder}>
                {field.options?.map(option => (
                  <Option key={option} value={option}>{option}</Option>
                ))}
              </Select>
            ) : field.type === 'number' ? (
              <Input 
                type="number"
                placeholder={field.placeholder}
              />
            ) : field.type === 'url' ? (
              <Input 
                type="url"
                placeholder={field.placeholder}
              />
            ) : field.type === 'date' ? (
              <DatePicker style={{ width: '100%' }} />
            ) : (
              <Input 
                placeholder={field.placeholder}
              />
            )}
          </Form.Item>
        ))}
      </Form>
    );
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>Loading customer profile...</div>
      </div>
    );
  }

  return (
    <div className="customer-profile-manager">
      {/* Customer Header */}
      <Card style={{ marginBottom: 24 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Title level={3} style={{ margin: 0 }}>
              {customer?.name}
            </Title>
            <Text type="secondary">
              {customer?.website} • {customer?.subscription_tier} Plan
            </Text>
          </Col>
          <Col>
            <Space>
              <Button 
                type="primary" 
                icon={<RocketOutlined />}
                size="large"
                onClick={() => executeAllServices()}
              >
                Launch All Available Services
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Service Categories */}
      <Collapse defaultActiveKey={Object.keys(services)} ghost>
        {Object.entries(services).map(([categoryKey, categoryServices]) => {
          const categoryConf = categoryConfig[categoryKey as keyof typeof categoryConfig];
          const availableCount = categoryServices.filter(service => 
            customer?.subscription_tier && service.subscription_tiers.includes(customer.subscription_tier)
          ).length;

          return (
            <Panel
              key={categoryKey}
              header={
                <Space>
                  {categoryConf?.icon}
                  <Title level={4} style={{ margin: 0 }}>
                    {categoryConf?.title}
                  </Title>
                  <Badge count={availableCount} style={{ backgroundColor: categoryConf?.color }} />
                  <Button 
                    size="small"
                    type="link"
                    onClick={(e) => {
                      e.stopPropagation();
                      executeAllServices(categoryKey);
                    }}
                  >
                    Launch All
                  </Button>
                </Space>
              }
            >
              <Row gutter={[16, 16]}>
                {categoryServices.map((service) => (
                  <Col xs={24} sm={12} md={8} lg={6} key={service.id}>
                    {renderServiceCard(service)}
                  </Col>
                ))}
              </Row>
            </Panel>
          );
        })}
      </Collapse>

      {/* Service Info Modal */}
      <Modal
        title={`${infoModal.service?.name} - Service Information`}
        open={infoModal.visible}
        onCancel={() => setInfoModal({ visible: false })}
        width={700}
        footer={[
          <Button key="close" onClick={() => setInfoModal({ visible: false })}>
            Close
          </Button>,
          <Button 
            key="launch" 
            type="primary"
            onClick={() => {
              if (infoModal.service) {
                setInfoModal({ visible: false });
                handleServiceWithInput(infoModal.service);
              }
            }}
          >
            Launch Service
          </Button>
        ]}
      >
        {infoModal.service && (
          <div>
            <Title level={5}>Plain Language Explanation</Title>
            <Paragraph>{infoModal.service.plain_explanation}</Paragraph>
            
            <Title level={5}>Technical Explanation</Title>
            <Paragraph>{infoModal.service.technical_explanation}</Paragraph>
            
            <Row gutter={16}>
              <Col span={12}>
                <Text strong>Estimated Time:</Text> {infoModal.service.estimated_time}
              </Col>
              <Col span={12}>
                <Text strong>Automation Level:</Text> {infoModal.service.automation_level}
              </Col>
            </Row>
            
            <Divider />
            
            <Text strong>Available in Plans:</Text>
            <div style={{ marginTop: 8 }}>
              {infoModal.service.subscription_tiers.map(tier => (
                <Tag key={tier} color="blue">{tier}</Tag>
              ))}
            </div>
            
            {infoModal.service.requires_input && (
              <>
                <Divider />
                <Text strong>Required Inputs:</Text>
                <ul style={{ marginTop: 8 }}>
                  {infoModal.service.input_fields.map(field => (
                    <li key={field.name}>
                      <Text>{field.label}</Text>
                      {field.required && <Text type="danger"> *</Text>}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}
      </Modal>

      {/* Input Modal */}
      <Modal
        title={`Configure ${inputModal.service?.name}`}
        open={inputModal.visible}
        onCancel={() => {
          setInputModal({ visible: false });
          form.resetFields();
        }}
        footer={[
          <Button key="cancel" onClick={() => {
            setInputModal({ visible: false });
            form.resetFields();
          }}>
            Cancel
          </Button>,
          <Button key="submit" type="primary" onClick={() => form.submit()}>
            Launch Service
          </Button>
        ]}
      >
        {renderInputForm()}
      </Modal>

      <style>{`
        .service-card {
          height: 100%;
          transition: all 0.3s ease;
        }
        
        .service-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }
        
        .service-card.disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        
        .service-card.disabled:hover {
          transform: none;
          box-shadow: none;
        }
        
        .customer-profile-manager .ant-collapse-header {
          padding: 16px !important;
        }
        
        .customer-profile-manager .ant-collapse-content {
          padding: 0 16px 16px 16px;
        }
      `}</style>
    </div>
  );
};

export default CustomerProfileManager;
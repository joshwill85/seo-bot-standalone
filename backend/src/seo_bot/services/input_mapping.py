"""Customer input mapping to automated SEO services."""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class BusinessType(Enum):
    LOCAL_SERVICE = "local_service"
    ECOMMERCE = "ecommerce"
    SAAS = "saas"
    CONTENT_SITE = "content_site"
    PROFESSIONAL_SERVICES = "professional_services"
    HEALTHCARE = "healthcare"
    LEGAL = "legal"
    REAL_ESTATE = "real_estate"
    RESTAURANT = "restaurant"
    RETAIL = "retail"


class ServiceTier(Enum):
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


@dataclass
class CustomerInputs:
    """Complete customer onboarding inputs mapped to SEO automation."""
    
    # Business Information
    business_name: str
    business_type: BusinessType
    primary_domain: str
    additional_domains: List[str] = None
    business_description: str = ""
    target_locations: List[str] = None  # For local SEO
    business_phone: str = ""
    business_address: str = ""
    
    # Industry & Competition
    primary_industry: str
    industry_keywords: List[str] = None
    competitor_domains: List[str] = None
    target_audience: str = ""
    
    # SEO Goals & Strategy
    primary_goals: List[str] = None  # ["increase_traffic", "improve_rankings", "generate_leads"]
    target_keywords: List[str] = None
    content_topics: List[str] = None
    geographic_targets: List[str] = None
    
    # Technical Information
    cms_platform: str = ""  # wordpress, shopify, custom, etc.
    google_analytics_id: str = ""
    google_search_console_property: str = ""
    google_my_business_id: str = ""
    
    # Service Preferences
    service_tier: ServiceTier
    automation_frequency: str = "daily"  # daily, weekly, monthly
    reporting_frequency: str = "weekly"
    
    # Content Strategy
    brand_voice: str = "professional"  # professional, casual, authoritative, friendly
    content_types_needed: List[str] = None  # ["blog_posts", "service_pages", "location_pages"]
    content_calendar_topics: List[str] = None
    
    # Link Building Preferences
    link_building_aggressive: bool = False
    citation_building_needed: bool = True
    guest_posting_topics: List[str] = None


class ServiceMapping:
    """Maps customer inputs to automated SEO service configurations."""
    
    @staticmethod
    def map_to_services(inputs: CustomerInputs) -> Dict[str, Any]:
        """Map customer inputs to complete automated SEO service configuration."""
        
        service_config = {
            "keyword_research": ServiceMapping._configure_keyword_research(inputs),
            "content_strategy": ServiceMapping._configure_content_strategy(inputs),
            "technical_seo": ServiceMapping._configure_technical_seo(inputs),
            "local_seo": ServiceMapping._configure_local_seo(inputs),
            "link_building": ServiceMapping._configure_link_building(inputs),
            "competitor_analysis": ServiceMapping._configure_competitor_analysis(inputs),
            "conversion_optimization": ServiceMapping._configure_conversion_optimization(inputs),
            "reporting": ServiceMapping._configure_reporting(inputs),
            "automation_schedules": ServiceMapping._configure_automation_schedules(inputs)
        }
        
        return service_config
    
    @staticmethod
    def _configure_keyword_research(inputs: CustomerInputs) -> Dict[str, Any]:
        """Configure automated keyword research based on business type and goals."""
        
        keyword_strategies = {
            BusinessType.LOCAL_SERVICE: {
                "seed_patterns": [
                    "{service} near me",
                    "{service} in {location}",
                    "best {service} {location}",
                    "{service} {location} reviews",
                    "emergency {service}",
                    "24/7 {service}",
                    "cheap {service}",
                    "professional {service}"
                ],
                "intent_focus": ["commercial", "local"],
                "competition_level": "local",
                "volume_threshold": 50
            },
            BusinessType.ECOMMERCE: {
                "seed_patterns": [
                    "buy {product}",
                    "{product} for sale",
                    "best {product}",
                    "{product} reviews",
                    "{product} comparison",
                    "cheap {product}",
                    "{product} deals",
                    "{brand} {product}"
                ],
                "intent_focus": ["commercial", "transactional"],
                "competition_level": "national",
                "volume_threshold": 100
            },
            BusinessType.SAAS: {
                "seed_patterns": [
                    "{solution} software",
                    "best {solution} tool",
                    "{solution} platform",
                    "{solution} vs {competitor}",
                    "how to {use_case}",
                    "{solution} pricing",
                    "{solution} features",
                    "{solution} alternative"
                ],
                "intent_focus": ["informational", "commercial"],
                "competition_level": "global", 
                "volume_threshold": 200
            }
        }
        
        strategy = keyword_strategies.get(inputs.business_type, keyword_strategies[BusinessType.LOCAL_SERVICE])
        
        return {
            "automation_enabled": True,
            "discovery_frequency": "weekly",
            "seed_keywords": inputs.target_keywords or [],
            "expansion_patterns": strategy["seed_patterns"],
            "intent_targeting": strategy["intent_focus"],
            "competition_analysis": strategy["competition_level"],
            "volume_threshold": strategy["volume_threshold"],
            "clustering_enabled": True,
            "ranking_tracking": True,
            "opportunity_identification": True,
            "seasonal_adjustments": inputs.business_type in [BusinessType.RETAIL, BusinessType.RESTAURANT],
            "local_modifiers": inputs.target_locations or [],
            "industry_terms": inputs.industry_keywords or [],
            "negative_keywords": ["free", "diy"] if inputs.business_type == BusinessType.PROFESSIONAL_SERVICES else []
        }
    
    @staticmethod
    def _configure_content_strategy(inputs: CustomerInputs) -> Dict[str, Any]:
        """Configure automated content strategy based on business goals."""
        
        content_strategies = {
            BusinessType.LOCAL_SERVICE: {
                "content_types": ["service_pages", "location_pages", "blog_posts", "faq_pages"],
                "content_calendar": "monthly",
                "topics": ["how_to_guides", "cost_guides", "emergency_tips", "maintenance_tips"],
                "posting_frequency": "weekly"
            },
            BusinessType.ECOMMERCE: {
                "content_types": ["product_descriptions", "category_pages", "buying_guides", "comparison_posts"],
                "content_calendar": "weekly",
                "topics": ["product_reviews", "buying_guides", "how_to_use", "trends"],
                "posting_frequency": "3x_weekly"
            },
            BusinessType.SAAS: {
                "content_types": ["feature_pages", "use_case_studies", "blog_posts", "whitepapers"],
                "content_calendar": "weekly",
                "topics": ["tutorials", "industry_insights", "case_studies", "feature_updates"],
                "posting_frequency": "2x_weekly"
            }
        }
        
        strategy = content_strategies.get(inputs.business_type, content_strategies[BusinessType.LOCAL_SERVICE])
        
        return {
            "automation_enabled": True,
            "content_types": strategy["content_types"],
            "generation_frequency": strategy["content_calendar"],
            "brand_voice": inputs.brand_voice,
            "target_topics": inputs.content_topics or strategy["topics"],
            "posting_schedule": strategy["posting_frequency"],
            "seo_optimization": True,
            "internal_linking": True,
            "meta_tag_generation": True,
            "schema_markup": True,
            "image_optimization": True,
            "content_audit_frequency": "monthly",
            "content_refresh_automation": True,
            "user_intent_matching": True,
            "competitor_content_analysis": True,
            "content_performance_tracking": True
        }
    
    @staticmethod
    def _configure_technical_seo(inputs: CustomerInputs) -> Dict[str, Any]:
        """Configure automated technical SEO based on platform and business needs."""
        
        return {
            "automation_enabled": True,
            "crawl_frequency": "weekly",
            "site_speed_monitoring": True,
            "mobile_optimization": True,
            "core_web_vitals_tracking": True,
            "schema_markup_automation": True,
            "xml_sitemap_management": True,
            "robots_txt_optimization": True,
            "internal_linking_optimization": True,
            "duplicate_content_detection": True,
            "broken_link_monitoring": True,
            "redirect_management": True,
            "ssl_monitoring": True,
            "cms_platform": inputs.cms_platform,
            "platform_specific_optimizations": True,
            "structured_data_testing": True,
            "page_experience_optimization": True,
            "indexability_monitoring": True,
            "canonical_tag_management": True,
            "hreflang_setup": len(inputs.geographic_targets or []) > 1,
            "technical_audit_frequency": "monthly"
        }
    
    @staticmethod
    def _configure_local_seo(inputs: CustomerInputs) -> Dict[str, Any]:
        """Configure automated local SEO for location-based businesses."""
        
        if inputs.business_type not in [BusinessType.LOCAL_SERVICE, BusinessType.RESTAURANT, BusinessType.RETAIL, BusinessType.HEALTHCARE, BusinessType.LEGAL]:
            return {"automation_enabled": False}
        
        return {
            "automation_enabled": True,
            "google_my_business_optimization": True,
            "citation_building": inputs.citation_building_needed,
            "location_page_generation": True,
            "local_keyword_tracking": True,
            "review_monitoring": True,
            "local_directory_submissions": True,
            "nap_consistency_monitoring": True,
            "local_competitor_tracking": True,
            "service_area_optimization": True,
            "local_schema_markup": True,
            "business_hours_management": True,
            "location_specific_content": True,
            "local_link_building": True,
            "reputation_management": True,
            "local_search_rank_tracking": True,
            "target_locations": inputs.target_locations or [],
            "business_info": {
                "name": inputs.business_name,
                "phone": inputs.business_phone,
                "address": inputs.business_address
            }
        }
    
    @staticmethod
    def _configure_link_building(inputs: CustomerInputs) -> Dict[str, Any]:
        """Configure automated link building strategy."""
        
        return {
            "automation_enabled": True,
            "strategy_aggressiveness": "moderate" if not inputs.link_building_aggressive else "aggressive",
            "prospect_identification": True,
            "outreach_automation": True,
            "relationship_building": True,
            "content_promotion": True,
            "broken_link_building": True,
            "resource_page_targeting": True,
            "guest_posting": len(inputs.guest_posting_topics or []) > 0,
            "guest_posting_topics": inputs.guest_posting_topics or [],
            "digital_pr": inputs.service_tier == ServiceTier.ENTERPRISE,
            "competitor_backlink_analysis": True,
            "link_monitoring": True,
            "disavow_management": True,
            "anchor_text_optimization": True,
            "link_velocity_management": True,
            "quality_threshold": "high",
            "monthly_link_targets": {
                ServiceTier.STARTER: 5,
                ServiceTier.PROFESSIONAL: 15,
                ServiceTier.ENTERPRISE: 30
            }[inputs.service_tier]
        }
    
    @staticmethod
    def _configure_competitor_analysis(inputs: CustomerInputs) -> Dict[str, Any]:
        """Configure automated competitor analysis."""
        
        return {
            "automation_enabled": True,
            "monitoring_frequency": "weekly",
            "competitor_domains": inputs.competitor_domains or [],
            "auto_discovery": True,
            "keyword_gap_analysis": True,
            "content_gap_analysis": True,
            "backlink_analysis": True,
            "technical_comparison": True,
            "ranking_comparison": True,
            "content_strategy_analysis": True,
            "social_media_monitoring": True,
            "ad_intelligence": inputs.service_tier == ServiceTier.ENTERPRISE,
            "competitive_alerts": True,
            "market_share_tracking": True,
            "opportunity_identification": True,
            "threat_assessment": True,
            "benchmark_reporting": True
        }
    
    @staticmethod
    def _configure_conversion_optimization(inputs: CustomerInputs) -> Dict[str, Any]:
        """Configure automated conversion optimization."""
        
        return {
            "automation_enabled": True,
            "cro_testing": inputs.service_tier in [ServiceTier.PROFESSIONAL, ServiceTier.ENTERPRISE],
            "landing_page_optimization": True,
            "user_experience_monitoring": True,
            "conversion_funnel_analysis": True,
            "form_optimization": True,
            "call_to_action_testing": True,
            "page_load_optimization": True,
            "mobile_conversion_optimization": True,
            "local_conversion_optimization": inputs.business_type == BusinessType.LOCAL_SERVICE,
            "ecommerce_optimization": inputs.business_type == BusinessType.ECOMMERCE,
            "lead_generation_optimization": inputs.business_type == BusinessType.PROFESSIONAL_SERVICES,
            "analytics_integration": True,
            "goal_tracking": True,
            "attribution_modeling": inputs.service_tier == ServiceTier.ENTERPRISE
        }
    
    @staticmethod
    def _configure_reporting(inputs: CustomerInputs) -> Dict[str, Any]:
        """Configure automated reporting based on customer preferences."""
        
        return {
            "automation_enabled": True,
            "frequency": inputs.reporting_frequency,
            "delivery_method": "email_and_dashboard",
            "report_types": [
                "keyword_rankings",
                "traffic_analytics", 
                "technical_audit",
                "content_performance",
                "link_building_progress",
                "local_seo_performance" if inputs.business_type == BusinessType.LOCAL_SERVICE else None,
                "conversion_metrics",
                "competitor_comparison",
                "roi_analysis"
            ],
            "custom_metrics": True,
            "white_label": inputs.service_tier == ServiceTier.ENTERPRISE,
            "client_access": True,
            "automated_insights": True,
            "action_recommendations": True,
            "performance_alerts": True
        }
    
    @staticmethod
    def _configure_automation_schedules(inputs: CustomerInputs) -> Dict[str, Any]:
        """Configure all automation schedules based on customer preferences."""
        
        frequency_map = {
            "daily": {
                "keyword_tracking": "daily",
                "technical_monitoring": "daily",
                "competitor_monitoring": "daily"
            },
            "weekly": {
                "keyword_tracking": "daily",
                "technical_monitoring": "weekly", 
                "competitor_monitoring": "weekly"
            },
            "monthly": {
                "keyword_tracking": "weekly",
                "technical_monitoring": "monthly",
                "competitor_monitoring": "monthly"
            }
        }
        
        schedule = frequency_map[inputs.automation_frequency]
        
        return {
            "keyword_research": {
                "discovery": "weekly",
                "analysis": schedule["keyword_tracking"],
                "ranking_updates": schedule["keyword_tracking"]
            },
            "content_generation": {
                "brief_creation": "weekly",
                "content_audit": "monthly",
                "optimization": "weekly"
            },
            "technical_seo": {
                "site_crawl": schedule["technical_monitoring"],
                "performance_check": "daily",
                "audit": "monthly"
            },
            "local_seo": {
                "citation_monitoring": "weekly",
                "review_monitoring": "daily",
                "gmb_optimization": "weekly"
            },
            "link_building": {
                "prospect_research": "weekly",
                "outreach": "daily",
                "monitoring": "weekly"
            },
            "competitor_analysis": {
                "monitoring": schedule["competitor_monitoring"],
                "analysis": "weekly",
                "reporting": "monthly"
            },
            "reporting": {
                "performance_reports": inputs.reporting_frequency,
                "alert_notifications": "immediate",
                "dashboard_updates": "daily"
            }
        }
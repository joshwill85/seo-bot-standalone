"""Service button to automated workflow mapping system."""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from .keyword_automation import AdvancedKeywordResearch
from .content_automation import ContentAutomationEngine
from .technical_seo_automation import TechnicalSEOAutomation
from .link_building_automation import LinkBuildingAutomation
from .local_seo_automation import LocalSEOAutomation
from .competitor_analysis_automation import CompetitorAnalysisAutomation
from .conversion_optimization_automation import ConversionOptimizationAutomation


class ServiceCategory(Enum):
    KEYWORD_RESEARCH = "keyword_research"
    CONTENT_STRATEGY = "content_strategy"
    TECHNICAL_SEO = "technical_seo"
    LINK_BUILDING = "link_building"
    LOCAL_SEO = "local_seo"
    COMPETITOR_ANALYSIS = "competitor_analysis"
    CONVERSION_OPTIMIZATION = "conversion_optimization"
    ANALYTICS_REPORTING = "analytics_reporting"
    AUTOMATION_MANAGEMENT = "automation_management"


@dataclass
class ServiceButton:
    button_id: str
    button_text: str
    button_description: str
    category: ServiceCategory
    workflow_function: str
    parameters_required: List[str]
    estimated_completion_time: str
    automation_level: str  # "instant", "background", "scheduled"
    prerequisites: List[str]
    output_deliverables: List[str]


class ServiceButtonMapping:
    """Maps every service button to its automated workflow."""
    
    def __init__(self):
        self.service_buttons = self._initialize_all_service_buttons()
        self.workflow_mappings = self._create_workflow_mappings()
    
    def _initialize_all_service_buttons(self) -> Dict[str, ServiceButton]:
        """Initialize all service buttons with their automation workflows."""
        
        buttons = {}
        
        # KEYWORD RESEARCH SERVICE BUTTONS
        buttons["discover_keywords"] = ServiceButton(
            button_id="discover_keywords",
            button_text="🔍 Discover New Keywords",
            button_description="Find 100+ new keyword opportunities based on your business and competitors",
            category=ServiceCategory.KEYWORD_RESEARCH,
            workflow_function="execute_keyword_discovery_workflow",
            parameters_required=["seed_keywords", "project_id"],
            estimated_completion_time="5-10 minutes",
            automation_level="background",
            prerequisites=["business_profile_complete"],
            output_deliverables=["keyword_opportunity_report", "search_volume_data", "competition_analysis"]
        )
        
        buttons["analyze_keyword_gaps"] = ServiceButton(
            button_id="analyze_keyword_gaps",
            button_text="📊 Find Keyword Gaps",
            button_description="Discover keywords your competitors rank for but you don't",
            category=ServiceCategory.KEYWORD_RESEARCH,
            workflow_function="execute_keyword_gap_analysis_workflow",
            parameters_required=["competitor_domains", "project_id"],
            estimated_completion_time="10-15 minutes",
            automation_level="background",
            prerequisites=["competitor_domains_added"],
            output_deliverables=["keyword_gap_report", "opportunity_matrix", "content_recommendations"]
        )
        
        buttons["track_keyword_rankings"] = ServiceButton(
            button_id="track_keyword_rankings",
            button_text="📈 Update Keyword Rankings",
            button_description="Get fresh ranking data for all tracked keywords",
            category=ServiceCategory.KEYWORD_RESEARCH,
            workflow_function="execute_ranking_update_workflow",
            parameters_required=["project_id", "keywords_list"],
            estimated_completion_time="3-5 minutes",
            automation_level="background",
            prerequisites=["keywords_added_to_tracking"],
            output_deliverables=["ranking_report", "position_changes", "serp_features_detected"]
        )
        
        buttons["cluster_keywords"] = ServiceButton(
            button_id="cluster_keywords",
            button_text="🎯 Create Keyword Clusters",
            button_description="Group related keywords into content clusters for better strategy",
            category=ServiceCategory.KEYWORD_RESEARCH,
            workflow_function="execute_keyword_clustering_workflow",
            parameters_required=["keywords_list", "project_id"],
            estimated_completion_time="5-8 minutes",
            automation_level="background",
            prerequisites=["keyword_list_exists"],
            output_deliverables=["keyword_clusters", "content_cluster_strategy", "pillar_content_plan"]
        )
        
        buttons["local_keyword_research"] = ServiceButton(
            button_id="local_keyword_research",
            button_text="📍 Local Keyword Research",
            button_description="Find location-specific keywords for your service areas",
            category=ServiceCategory.KEYWORD_RESEARCH,
            workflow_function="execute_local_keyword_research_workflow",
            parameters_required=["target_locations", "services_list", "project_id"],
            estimated_completion_time="8-12 minutes",
            automation_level="background",
            prerequisites=["target_locations_set"],
            output_deliverables=["local_keyword_list", "location_page_strategy", "gmb_keyword_targets"]
        )
        
        # CONTENT STRATEGY SERVICE BUTTONS
        buttons["generate_content_calendar"] = ServiceButton(
            button_id="generate_content_calendar",
            button_text="📅 Generate Content Calendar",
            button_description="Create a 3-month content calendar with topics and schedules",
            category=ServiceCategory.CONTENT_STRATEGY,
            workflow_function="execute_content_calendar_workflow",
            parameters_required=["target_keywords", "business_type", "posting_frequency"],
            estimated_completion_time="10-15 minutes",
            automation_level="background",
            prerequisites=["keyword_research_complete"],
            output_deliverables=["3_month_content_calendar", "content_themes", "posting_schedule"]
        )
        
        buttons["create_content_brief"] = ServiceButton(
            button_id="create_content_brief",
            button_text="📝 Create Content Brief",
            button_description="Generate detailed content brief with outline, keywords, and optimization",
            category=ServiceCategory.CONTENT_STRATEGY,
            workflow_function="execute_content_brief_workflow",
            parameters_required=["target_keyword", "content_type", "project_id"],
            estimated_completion_time="5-8 minutes",
            automation_level="background",
            prerequisites=["target_keywords_selected"],
            output_deliverables=["content_brief", "seo_outline", "meta_tags", "internal_link_suggestions"]
        )
        
        buttons["audit_existing_content"] = ServiceButton(
            button_id="audit_existing_content",
            button_text="🔍 Audit Existing Content",
            button_description="Comprehensive analysis of your current content performance",
            category=ServiceCategory.CONTENT_STRATEGY,
            workflow_function="execute_content_audit_workflow",
            parameters_required=["domain", "project_id"],
            estimated_completion_time="15-20 minutes",
            automation_level="background",
            prerequisites=["domain_connected"],
            output_deliverables=["content_audit_report", "optimization_opportunities", "content_refresh_plan"]
        )
        
        buttons["optimize_meta_tags"] = ServiceButton(
            button_id="optimize_meta_tags",
            button_text="🏷️ Optimize Meta Tags",
            button_description="Generate optimized title tags and meta descriptions for all pages",
            category=ServiceCategory.CONTENT_STRATEGY,
            workflow_function="execute_meta_optimization_workflow",
            parameters_required=["page_urls", "target_keywords", "project_id"],
            estimated_completion_time="8-12 minutes",
            automation_level="background",
            prerequisites=["pages_crawled"],
            output_deliverables=["optimized_meta_tags", "title_tag_suggestions", "meta_description_templates"]
        )
        
        buttons["create_content_clusters"] = ServiceButton(
            button_id="create_content_clusters",
            button_text="🎯 Build Content Clusters",
            button_description="Create topic clusters with pillar content and supporting articles",
            category=ServiceCategory.CONTENT_STRATEGY,
            workflow_function="execute_content_clustering_workflow",
            parameters_required=["keyword_clusters", "project_id"],
            estimated_completion_time="12-18 minutes",
            automation_level="background",
            prerequisites=["keyword_clustering_complete"],
            output_deliverables=["content_cluster_strategy", "pillar_content_plan", "internal_link_architecture"]
        )
        
        # TECHNICAL SEO SERVICE BUTTONS
        buttons["run_technical_audit"] = ServiceButton(
            button_id="run_technical_audit",
            button_text="🔧 Run Technical SEO Audit",
            button_description="Comprehensive technical SEO audit with prioritized fix recommendations",
            category=ServiceCategory.TECHNICAL_SEO,
            workflow_function="execute_technical_audit_workflow",
            parameters_required=["domain", "project_id"],
            estimated_completion_time="20-30 minutes",
            automation_level="background",
            prerequisites=["domain_verified"],
            output_deliverables=["technical_audit_report", "prioritized_issues", "implementation_roadmap"]
        )
        
        buttons["check_site_speed"] = ServiceButton(
            button_id="check_site_speed",
            button_text="⚡ Check Site Speed",
            button_description="Analyze page speed and Core Web Vitals performance",
            category=ServiceCategory.TECHNICAL_SEO,
            workflow_function="execute_speed_audit_workflow",
            parameters_required=["page_urls", "project_id"],
            estimated_completion_time="5-10 minutes",
            automation_level="background",
            prerequisites=["pages_accessible"],
            output_deliverables=["speed_audit_report", "cwv_scores", "optimization_recommendations"]
        )
        
        buttons["audit_mobile_optimization"] = ServiceButton(
            button_id="audit_mobile_optimization",
            button_text="📱 Audit Mobile Optimization",
            button_description="Check mobile-friendliness and mobile user experience",
            category=ServiceCategory.TECHNICAL_SEO,
            workflow_function="execute_mobile_audit_workflow",
            parameters_required=["domain", "project_id"],
            estimated_completion_time="8-12 minutes",
            automation_level="background",
            prerequisites=["domain_accessible"],
            output_deliverables=["mobile_audit_report", "usability_issues", "mobile_optimization_plan"]
        )
        
        buttons["check_indexability"] = ServiceButton(
            button_id="check_indexability",
            button_text="🗂️ Check Page Indexability",
            button_description="Verify which pages can be indexed by search engines",
            category=ServiceCategory.TECHNICAL_SEO,
            workflow_function="execute_indexability_audit_workflow",
            parameters_required=["domain", "project_id"],
            estimated_completion_time="10-15 minutes",
            automation_level="background",
            prerequisites=["sitemap_available"],
            output_deliverables=["indexability_report", "blocked_pages", "indexing_recommendations"]
        )
        
        buttons["audit_schema_markup"] = ServiceButton(
            button_id="audit_schema_markup",
            button_text="📋 Audit Schema Markup",
            button_description="Check structured data implementation and opportunities",
            category=ServiceCategory.TECHNICAL_SEO,
            workflow_function="execute_schema_audit_workflow",
            parameters_required=["domain", "business_type", "project_id"],
            estimated_completion_time="8-12 minutes",
            automation_level="background",
            prerequisites=["business_type_set"],
            output_deliverables=["schema_audit_report", "schema_opportunities", "implementation_guide"]
        )
        
        # LINK BUILDING SERVICE BUTTONS
        buttons["find_link_opportunities"] = ServiceButton(
            button_id="find_link_opportunities",
            button_text="🔗 Find Link Opportunities",
            button_description="Discover high-quality link building opportunities in your industry",
            category=ServiceCategory.LINK_BUILDING,
            workflow_function="execute_link_discovery_workflow",
            parameters_required=["industry", "target_locations", "project_id"],
            estimated_completion_time="15-25 minutes",
            automation_level="background",
            prerequisites=["industry_set"],
            output_deliverables=["link_opportunities", "outreach_targets", "contact_information"]
        )
        
        buttons["analyze_competitor_backlinks"] = ServiceButton(
            button_id="analyze_competitor_backlinks",
            button_text="🕵️ Analyze Competitor Backlinks",
            button_description="Find link opportunities by analyzing competitor backlink profiles",
            category=ServiceCategory.LINK_BUILDING,
            workflow_function="execute_competitor_backlink_workflow",
            parameters_required=["competitor_domains", "project_id"],
            estimated_completion_time="12-18 minutes",
            automation_level="background",
            prerequisites=["competitor_domains_added"],
            output_deliverables=["backlink_gap_analysis", "replicable_links", "outreach_strategy"]
        )
        
        buttons["find_broken_links"] = ServiceButton(
            button_id="find_broken_links",
            button_text="🔗💔 Find Broken Link Opportunities",
            button_description="Identify broken link building opportunities in your niche",
            category=ServiceCategory.LINK_BUILDING,
            workflow_function="execute_broken_link_workflow",
            parameters_required=["industry_keywords", "project_id"],
            estimated_completion_time="20-30 minutes",
            automation_level="background",
            prerequisites=["industry_keywords_set"],
            output_deliverables=["broken_link_prospects", "outreach_templates", "replacement_content_suggestions"]
        )
        
        buttons["build_citations"] = ServiceButton(
            button_id="build_citations",
            button_text="📋 Build Business Citations",
            button_description="Submit business to high-authority directories and citation sites",
            category=ServiceCategory.LINK_BUILDING,
            workflow_function="execute_citation_building_workflow",
            parameters_required=["business_info", "target_locations", "project_id"],
            estimated_completion_time="30-45 minutes",
            automation_level="background",
            prerequisites=["business_info_complete"],
            output_deliverables=["citation_submission_report", "nap_consistency_check", "directory_listings"]
        )
        
        buttons["monitor_backlinks"] = ServiceButton(
            button_id="monitor_backlinks",
            button_text="👁️ Monitor Backlink Profile",
            button_description="Track new and lost backlinks, identify toxic links",
            category=ServiceCategory.LINK_BUILDING,
            workflow_function="execute_backlink_monitoring_workflow",
            parameters_required=["domain", "project_id"],
            estimated_completion_time="5-8 minutes",
            automation_level="background",
            prerequisites=["domain_verified"],
            output_deliverables=["backlink_report", "new_links_found", "toxic_links_identified"]
        )
        
        # LOCAL SEO SERVICE BUTTONS
        buttons["optimize_google_my_business"] = ServiceButton(
            button_id="optimize_google_my_business",
            button_text="🏢 Optimize Google My Business",
            button_description="Complete GMB profile optimization with posts and Q&A management",
            category=ServiceCategory.LOCAL_SEO,
            workflow_function="execute_gmb_optimization_workflow",
            parameters_required=["business_info", "gmb_account_id", "project_id"],
            estimated_completion_time="20-30 minutes",
            automation_level="background",
            prerequisites=["gmb_account_connected"],
            output_deliverables=["gmb_optimization_report", "profile_completeness_score", "posting_schedule"]
        )
        
        buttons["audit_local_citations"] = ServiceButton(
            button_id="audit_local_citations",
            button_text="📍 Audit Local Citations",
            button_description="Check NAP consistency across all citation platforms",
            category=ServiceCategory.LOCAL_SEO,
            workflow_function="execute_citation_audit_workflow",
            parameters_required=["business_name", "business_address", "business_phone", "project_id"],
            estimated_completion_time="15-20 minutes",
            automation_level="background",
            prerequisites=["business_info_complete"],
            output_deliverables=["citation_audit_report", "nap_inconsistencies", "citation_opportunities"]
        )
        
        buttons["create_location_pages"] = ServiceButton(
            button_id="create_location_pages",
            button_text="📍 Create Location Pages",
            button_description="Generate location-specific pages for all service areas",
            category=ServiceCategory.LOCAL_SEO,
            workflow_function="execute_location_page_workflow",
            parameters_required=["target_locations", "services_list", "project_id"],
            estimated_completion_time="25-35 minutes",
            automation_level="background",
            prerequisites=["target_locations_set"],
            output_deliverables=["location_page_strategy", "page_templates", "local_seo_optimization"]
        )
        
        buttons["monitor_online_reviews"] = ServiceButton(
            button_id="monitor_online_reviews",
            button_text="⭐ Monitor Online Reviews",
            button_description="Track reviews across all platforms and get response suggestions",
            category=ServiceCategory.LOCAL_SEO,
            workflow_function="execute_review_monitoring_workflow",
            parameters_required=["business_profiles", "project_id"],
            estimated_completion_time="8-12 minutes",
            automation_level="background",
            prerequisites=["review_platforms_connected"],
            output_deliverables=["review_summary", "response_suggestions", "reputation_score"]
        )
        
        buttons["optimize_local_schema"] = ServiceButton(
            button_id="optimize_local_schema",
            button_text="🏗️ Optimize Local Schema",
            button_description="Implement local business schema markup for better local search visibility",
            category=ServiceCategory.LOCAL_SEO,
            workflow_function="execute_local_schema_workflow",
            parameters_required=["business_info", "locations", "services", "project_id"],
            estimated_completion_time="12-18 minutes",
            automation_level="background",
            prerequisites=["business_info_complete"],
            output_deliverables=["schema_markup_code", "local_seo_schema", "implementation_guide"]
        )
        
        # COMPETITOR ANALYSIS SERVICE BUTTONS
        buttons["discover_competitors"] = ServiceButton(
            button_id="discover_competitors",
            button_text="🔍 Discover Competitors",
            button_description="Automatically find your main SEO competitors",
            category=ServiceCategory.COMPETITOR_ANALYSIS,
            workflow_function="execute_competitor_discovery_workflow",
            parameters_required=["target_keywords", "industry", "target_locations"],
            estimated_completion_time="15-20 minutes",
            automation_level="background",
            prerequisites=["keyword_research_started"],
            output_deliverables=["competitor_list", "competitive_landscape", "threat_assessment"]
        )
        
        buttons["analyze_competitor_content"] = ServiceButton(
            button_id="analyze_competitor_content",
            button_text="📄 Analyze Competitor Content",
            button_description="Deep dive into competitor content strategies and find gaps",
            category=ServiceCategory.COMPETITOR_ANALYSIS,
            workflow_function="execute_competitor_content_workflow",
            parameters_required=["competitor_domains", "project_id"],
            estimated_completion_time="20-30 minutes",
            automation_level="background",
            prerequisites=["competitors_identified"],
            output_deliverables=["content_gap_analysis", "content_opportunities", "topic_recommendations"]
        )
        
        buttons["compare_technical_seo"] = ServiceButton(
            button_id="compare_technical_seo",
            button_text="⚙️ Compare Technical SEO",
            button_description="Compare your technical SEO performance against competitors",
            category=ServiceCategory.COMPETITOR_ANALYSIS,
            workflow_function="execute_technical_comparison_workflow",
            parameters_required=["competitor_domains", "your_domain", "project_id"],
            estimated_completion_time="18-25 minutes",
            automation_level="background",
            prerequisites=["competitors_identified"],
            output_deliverables=["technical_comparison", "competitive_advantages", "improvement_areas"]
        )
        
        buttons["monitor_competitor_changes"] = ServiceButton(
            button_id="monitor_competitor_changes",
            button_text="👁️ Monitor Competitor Changes",
            button_description="Track competitor website changes, new content, and ranking movements",
            category=ServiceCategory.COMPETITOR_ANALYSIS,
            workflow_function="execute_competitor_monitoring_workflow",
            parameters_required=["competitor_domains", "project_id"],
            estimated_completion_time="10-15 minutes",
            automation_level="background",
            prerequisites=["competitors_identified"],
            output_deliverables=["change_detection_report", "new_content_alerts", "ranking_movements"]
        )
        
        # CONVERSION OPTIMIZATION SERVICE BUTTONS
        buttons["audit_conversion_funnels"] = ServiceButton(
            button_id="audit_conversion_funnels",
            button_text="🎯 Audit Conversion Funnels",
            button_description="Analyze conversion paths and identify drop-off points",
            category=ServiceCategory.CONVERSION_OPTIMIZATION,
            workflow_function="execute_funnel_audit_workflow",
            parameters_required=["domain", "conversion_goals", "project_id"],
            estimated_completion_time="15-25 minutes",
            automation_level="background",
            prerequisites=["analytics_connected"],
            output_deliverables=["funnel_analysis", "drop_off_points", "optimization_recommendations"]
        )
        
        buttons["optimize_landing_pages"] = ServiceButton(
            button_id="optimize_landing_pages",
            button_text="🎨 Optimize Landing Pages",
            button_description="Get recommendations to improve landing page conversion rates",
            category=ServiceCategory.CONVERSION_OPTIMIZATION,
            workflow_function="execute_landing_page_optimization_workflow",
            parameters_required=["page_urls", "conversion_goals", "project_id"],
            estimated_completion_time="12-18 minutes",
            automation_level="background",
            prerequisites=["key_pages_identified"],
            output_deliverables=["page_optimization_plan", "ab_test_suggestions", "copy_recommendations"]
        )
        
        buttons["optimize_forms"] = ServiceButton(
            button_id="optimize_forms",
            button_text="📝 Optimize Forms",
            button_description="Analyze and optimize forms for better completion rates",
            category=ServiceCategory.CONVERSION_OPTIMIZATION,
            workflow_function="execute_form_optimization_workflow",
            parameters_required=["form_pages", "project_id"],
            estimated_completion_time="10-15 minutes",
            automation_level="background",
            prerequisites=["forms_identified"],
            output_deliverables=["form_analysis", "optimization_suggestions", "ab_test_plan"]
        )
        
        buttons["analyze_mobile_conversions"] = ServiceButton(
            button_id="analyze_mobile_conversions",
            button_text="📱 Analyze Mobile Conversions",
            button_description="Identify mobile-specific conversion optimization opportunities",
            category=ServiceCategory.CONVERSION_OPTIMIZATION,
            workflow_function="execute_mobile_conversion_workflow",
            parameters_required=["domain", "project_id"],
            estimated_completion_time="12-18 minutes",
            automation_level="background",
            prerequisites=["mobile_analytics_available"],
            output_deliverables=["mobile_conversion_analysis", "mobile_optimization_plan", "mobile_testing_strategy"]
        )
        
        # ANALYTICS & REPORTING SERVICE BUTTONS
        buttons["generate_seo_report"] = ServiceButton(
            button_id="generate_seo_report",
            button_text="📊 Generate SEO Report",
            button_description="Comprehensive SEO performance report with insights and recommendations",
            category=ServiceCategory.ANALYTICS_REPORTING,
            workflow_function="execute_seo_reporting_workflow",
            parameters_required=["project_id", "date_range"],
            estimated_completion_time="8-12 minutes",
            automation_level="background",
            prerequisites=["data_collection_active"],
            output_deliverables=["seo_performance_report", "trend_analysis", "action_recommendations"]
        )
        
        buttons["calculate_seo_roi"] = ServiceButton(
            button_id="calculate_seo_roi",
            button_text="💰 Calculate SEO ROI",
            button_description="Calculate return on investment for your SEO efforts",
            category=ServiceCategory.ANALYTICS_REPORTING,
            workflow_function="execute_roi_calculation_workflow",
            parameters_required=["project_id", "investment_data", "revenue_data"],
            estimated_completion_time="5-8 minutes",
            automation_level="background",
            prerequisites=["conversion_tracking_active"],
            output_deliverables=["roi_analysis", "performance_attribution", "projection_models"]
        )
        
        buttons["track_serp_features"] = ServiceButton(
            button_id="track_serp_features",
            button_text="🎯 Track SERP Features",
            button_description="Monitor featured snippets, local pack, and other SERP feature opportunities",
            category=ServiceCategory.ANALYTICS_REPORTING,
            workflow_function="execute_serp_tracking_workflow",
            parameters_required=["tracked_keywords", "project_id"],
            estimated_completion_time="8-12 minutes",
            automation_level="background",
            prerequisites=["keyword_tracking_active"],
            output_deliverables=["serp_feature_report", "opportunity_analysis", "optimization_guide"]
        )
        
        # AUTOMATION MANAGEMENT SERVICE BUTTONS
        buttons["setup_automation_schedule"] = ServiceButton(
            button_id="setup_automation_schedule",
            button_text="⏰ Setup Automation Schedule",
            button_description="Configure automated SEO tasks and reporting schedules",
            category=ServiceCategory.AUTOMATION_MANAGEMENT,
            workflow_function="execute_automation_setup_workflow",
            parameters_required=["automation_preferences", "project_id"],
            estimated_completion_time="5-10 minutes",
            automation_level="instant",
            prerequisites=["project_setup_complete"],
            output_deliverables=["automation_schedule", "task_calendar", "notification_settings"]
        )
        
        buttons["manage_alert_settings"] = ServiceButton(
            button_id="manage_alert_settings",
            button_text="🔔 Manage Alert Settings",
            button_description="Configure alerts for ranking changes, technical issues, and opportunities",
            category=ServiceCategory.AUTOMATION_MANAGEMENT,
            workflow_function="execute_alert_management_workflow",
            parameters_required=["alert_preferences", "project_id"],
            estimated_completion_time="3-5 minutes",
            automation_level="instant",
            prerequisites=["project_active"],
            output_deliverables=["alert_configuration", "notification_preferences", "escalation_rules"]
        )
        
        buttons["bulk_optimization"] = ServiceButton(
            button_id="bulk_optimization",
            button_text="⚡ Run Bulk Optimization",
            button_description="Execute multiple SEO optimizations across your entire site",
            category=ServiceCategory.AUTOMATION_MANAGEMENT,
            workflow_function="execute_bulk_optimization_workflow",
            parameters_required=["optimization_types", "project_id"],
            estimated_completion_time="45-90 minutes",
            automation_level="background",
            prerequisites=["audit_data_available"],
            output_deliverables=["bulk_optimization_report", "implementation_status", "performance_impact"]
        )
        
        return buttons
    
    def _create_workflow_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Create detailed workflow mappings for each service button."""
        
        mappings = {}
        
        # Example detailed workflow mapping
        mappings["discover_keywords"] = {
            "workflow_steps": [
                {
                    "step": 1,
                    "action": "Initialize keyword research engine",
                    "function": "AdvancedKeywordResearch.__init__",
                    "estimated_time": "5 seconds"
                },
                {
                    "step": 2,
                    "action": "Analyze seed keywords",
                    "function": "AdvancedKeywordResearch._analyze_seed_keywords",
                    "estimated_time": "30 seconds"
                },
                {
                    "step": 3,
                    "action": "Discover keyword variations",
                    "function": "AdvancedKeywordResearch._discover_keyword_variations",
                    "estimated_time": "90 seconds"
                },
                {
                    "step": 4,
                    "action": "Analyze competitor keywords",
                    "function": "AdvancedKeywordResearch._analyze_competitor_keywords",
                    "estimated_time": "120 seconds"
                },
                {
                    "step": 5,
                    "action": "Find question keywords",
                    "function": "AdvancedKeywordResearch._discover_question_keywords",
                    "estimated_time": "60 seconds"
                },
                {
                    "step": 6,
                    "action": "Identify long-tail opportunities",
                    "function": "AdvancedKeywordResearch._find_long_tail_opportunities",
                    "estimated_time": "90 seconds"
                },
                {
                    "step": 7,
                    "action": "Generate final report",
                    "function": "compile_keyword_research_report",
                    "estimated_time": "15 seconds"
                }
            ],
            "success_criteria": [
                "minimum_100_keywords_found",
                "competitor_analysis_complete",
                "search_volume_data_available",
                "difficulty_scores_calculated"
            ],
            "error_handling": [
                "insufficient_seed_keywords_error",
                "competitor_data_unavailable_warning",
                "api_rate_limit_retry_logic"
            ],
            "output_format": {
                "primary_deliverable": "keyword_opportunity_report.json",
                "supplementary_files": ["search_volume_data.csv", "competition_analysis.pdf"],
                "dashboard_widgets": ["keyword_overview", "opportunity_matrix", "trend_chart"]
            }
        }
        
        # Add workflow mappings for all other buttons
        for button_id, button in self.service_buttons.items():
            if button_id not in mappings:
                mappings[button_id] = self._generate_generic_workflow_mapping(button)
        
        return mappings
    
    def _generate_generic_workflow_mapping(self, button: ServiceButton) -> Dict[str, Any]:
        """Generate a generic workflow mapping for buttons without specific mappings."""
        
        return {
            "workflow_steps": [
                {
                    "step": 1,
                    "action": f"Initialize {button.category.value} automation",
                    "function": f"initialize_{button.button_id}_workflow",
                    "estimated_time": "10 seconds"
                },
                {
                    "step": 2,
                    "action": f"Execute {button.workflow_function}",
                    "function": button.workflow_function,
                    "estimated_time": button.estimated_completion_time
                },
                {
                    "step": 3,
                    "action": "Generate deliverables",
                    "function": "compile_workflow_results",
                    "estimated_time": "30 seconds"
                }
            ],
            "success_criteria": [
                "workflow_completed_successfully",
                "deliverables_generated",
                "results_saved_to_database"
            ],
            "error_handling": [
                "parameter_validation_error",
                "external_api_error",
                "timeout_error"
            ],
            "output_format": {
                "primary_deliverable": f"{button.button_id}_report.json",
                "supplementary_files": button.output_deliverables,
                "dashboard_widgets": [f"{button.button_id}_summary"]
            }
        }
    
    def get_button_by_id(self, button_id: str) -> Optional[ServiceButton]:
        """Get service button by ID."""
        return self.service_buttons.get(button_id)
    
    def get_buttons_by_category(self, category: ServiceCategory) -> List[ServiceButton]:
        """Get all buttons in a specific category."""
        return [button for button in self.service_buttons.values() if button.category == category]
    
    def get_workflow_mapping(self, button_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow mapping for a specific button."""
        return self.workflow_mappings.get(button_id)
    
    def get_all_service_buttons(self) -> Dict[str, ServiceButton]:
        """Get all service buttons."""
        return self.service_buttons
    
    def get_dashboard_layout(self) -> Dict[str, List[ServiceButton]]:
        """Get organized dashboard layout by category."""
        
        layout = {}
        for category in ServiceCategory:
            layout[category.value] = self.get_buttons_by_category(category)
        
        return layout
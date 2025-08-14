"""
AI-Assisted Content Generation for Local SEO
Automates the creation of high-quality, locally-optimized content at scale
"""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from pathlib import Path

class ContentType(Enum):
    BLOG_POST = "blog_post"
    SERVICE_PAGE = "service_page"
    LOCATION_PAGE = "location_page"
    FAQ_CONTENT = "faq_content"
    META_DESCRIPTION = "meta_description"
    TITLE_TAG = "title_tag"
    SOCIAL_MEDIA = "social_media"
    EMAIL_CONTENT = "email_content"
    PRESS_RELEASE = "press_release"
    LANDING_PAGE = "landing_page"

class ContentCategory(Enum):
    EDUCATIONAL = "educational"
    PROMOTIONAL = "promotional"
    SEASONAL = "seasonal"
    NEWS = "news"
    HOW_TO = "how_to"
    LOCAL_EVENTS = "local_events"
    CUSTOMER_STORIES = "customer_stories"
    INDUSTRY_INSIGHTS = "industry_insights"

@dataclass
class ContentRequest:
    """Content generation request specification"""
    content_type: ContentType
    category: ContentCategory
    topic: str
    target_keywords: List[str]
    location: str
    business_type: str
    word_count_target: int
    tone: str  # professional, friendly, authoritative, conversational
    include_cta: bool
    seo_focus: List[str]  # local, technical, informational
    deadline: Optional[datetime] = None

@dataclass
class GeneratedContent:
    """Generated content with metadata"""
    content_id: str
    content_type: ContentType
    title: str
    content: str
    meta_description: str
    target_keywords: List[str]
    word_count: int
    seo_score: float
    readability_score: float
    local_optimization_score: float
    schema_markup: Optional[Dict[str, Any]] = None
    generated_at: datetime = datetime.now()

class AIContentGenerator:
    """Advanced AI-powered content generation for local SEO"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.content_templates = self._load_content_templates()
        self.seo_patterns = self._initialize_seo_patterns()
        self.local_content_rules = self._initialize_local_rules()
        
    def _load_content_templates(self) -> Dict[ContentType, Dict[str, Any]]:
        """Load content generation templates for different types"""
        
        return {
            ContentType.BLOG_POST: {
                'structure': ['introduction', 'problem', 'solution', 'benefits', 'local_context', 'conclusion', 'cta'],
                'min_word_count': 800,
                'optimal_word_count': 1200,
                'h2_count': 3,
                'h3_count': 2,
                'local_keyword_density': 0.02,
                'seo_requirements': ['local_keywords', 'service_mentions', 'location_references']
            },
            
            ContentType.SERVICE_PAGE: {
                'structure': ['hero', 'service_overview', 'benefits', 'process', 'local_focus', 'testimonials', 'cta'],
                'min_word_count': 600,
                'optimal_word_count': 1000,
                'h2_count': 4,
                'h3_count': 3,
                'local_keyword_density': 0.03,
                'seo_requirements': ['service_keywords', 'location_modifiers', 'trust_signals']
            },
            
            ContentType.LOCATION_PAGE: {
                'structure': ['local_intro', 'services_offered', 'area_expertise', 'local_testimonials', 'contact_info'],
                'min_word_count': 500,
                'optimal_word_count': 800,
                'h2_count': 3,
                'h3_count': 2,
                'local_keyword_density': 0.04,
                'seo_requirements': ['city_keywords', 'neighborhood_mentions', 'local_landmarks']
            },
            
            ContentType.FAQ_CONTENT: {
                'structure': ['question', 'direct_answer', 'detailed_explanation', 'local_context'],
                'min_word_count': 100,
                'optimal_word_count': 200,
                'local_keyword_density': 0.03,
                'seo_requirements': ['conversational_keywords', 'voice_search_optimization']
            }
        }
    
    def _initialize_seo_patterns(self) -> Dict[str, List[str]]:
        """Initialize SEO optimization patterns"""
        
        return {
            'local_modifiers': [
                'in {city}', 'near {city}', '{city} area', 'serving {city}',
                'local {city}', '{city} residents', '{city} businesses',
                '{city} and surrounding areas'
            ],
            
            'trust_signals': [
                'licensed and insured', 'family-owned', 'serving {city} since {year}',
                'trusted by {city} residents', 'award-winning', 'certified professionals',
                'free estimates', '24/7 service', 'satisfaction guaranteed'
            ],
            
            'action_words': [
                'call today', 'schedule now', 'get started', 'contact us',
                'free consultation', 'request quote', 'book online', 'learn more'
            ],
            
            'local_business_benefits': [
                'quick response times', 'local expertise', 'community knowledge',
                'personalized service', 'established reputation', 'nearby location'
            ]
        }
    
    def _initialize_local_rules(self) -> Dict[str, Any]:
        """Initialize local SEO optimization rules"""
        
        return {
            'keyword_placement': {
                'title_tag': ['primary_keyword', 'location'],
                'h1': ['primary_keyword', 'location'],
                'first_paragraph': ['primary_keyword', 'location', 'business_name'],
                'last_paragraph': ['call_to_action', 'contact_info']
            },
            
            'content_requirements': {
                'local_references_min': 3,
                'service_mentions_min': 2,
                'contact_info_placements': 2,
                'internal_links_min': 2,
                'external_authority_links': 1
            },
            
            'schema_markup_types': {
                'LocalBusiness': ['name', 'address', 'phone', 'hours', 'services'],
                'Article': ['headline', 'author', 'datePublished', 'description'],
                'FAQPage': ['questions', 'answers'],
                'HowTo': ['name', 'description', 'steps']
            }
        }
    
    async def generate_content_batch(
        self, 
        content_requests: List[ContentRequest],
        business_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate multiple pieces of content efficiently"""
        
        generation_results = {
            'total_requested': len(content_requests),
            'successfully_generated': 0,
            'failed_generation': 0,
            'generated_content': [],
            'total_word_count': 0,
            'average_seo_score': 0,
            'content_calendar': []
        }
        
        business_name = business_data.get('business_name', 'Your Business')
        location = business_data.get('location', 'your area')
        services = business_data.get('services', [])
        
        # Process each content request
        for request in content_requests:
            try:
                generated_content = await self._generate_single_content(
                    request, business_data
                )
                
                generation_results['generated_content'].append(generated_content)
                generation_results['successfully_generated'] += 1
                generation_results['total_word_count'] += generated_content.word_count
                
                # Add to content calendar if needed
                if request.deadline:
                    generation_results['content_calendar'].append({
                        'content_id': generated_content.content_id,
                        'title': generated_content.title,
                        'type': generated_content.content_type.value,
                        'deadline': request.deadline.isoformat(),
                        'status': 'generated'
                    })
                    
            except Exception as e:
                self.logger.error(f"Failed to generate content for {request.topic}: {e}")
                generation_results['failed_generation'] += 1
        
        # Calculate average SEO score
        if generation_results['generated_content']:
            avg_seo = sum(c.seo_score for c in generation_results['generated_content'])
            generation_results['average_seo_score'] = avg_seo / len(generation_results['generated_content'])
        
        return generation_results
    
    async def _generate_single_content(
        self, 
        request: ContentRequest,
        business_data: Dict[str, Any]
    ) -> GeneratedContent:
        """Generate a single piece of content"""
        
        business_name = business_data.get('business_name', 'Your Business')
        location = request.location or business_data.get('location', 'your area')
        phone = business_data.get('phone', '(XXX) XXX-XXXX')
        website = business_data.get('website', 'https://yourwebsite.com')
        
        # Get content template
        template = self.content_templates.get(request.content_type, {})
        
        # Generate content based on type
        if request.content_type == ContentType.BLOG_POST:
            content_data = await self._generate_blog_post(request, business_data, template)
        elif request.content_type == ContentType.SERVICE_PAGE:
            content_data = await self._generate_service_page(request, business_data, template)
        elif request.content_type == ContentType.LOCATION_PAGE:
            content_data = await self._generate_location_page(request, business_data, template)
        elif request.content_type == ContentType.FAQ_CONTENT:
            content_data = await self._generate_faq_content(request, business_data, template)
        else:
            content_data = await self._generate_generic_content(request, business_data, template)
        
        # Calculate SEO scores
        seo_score = await self._calculate_seo_score(content_data, request)
        readability_score = await self._calculate_readability_score(content_data['content'])
        local_optimization_score = await self._calculate_local_seo_score(content_data, location, business_name)
        
        # Generate schema markup if applicable
        schema_markup = await self._generate_schema_markup(request, content_data, business_data)
        
        generated_content = GeneratedContent(
            content_id=f"{request.content_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            content_type=request.content_type,
            title=content_data['title'],
            content=content_data['content'],
            meta_description=content_data['meta_description'],
            target_keywords=request.target_keywords,
            word_count=len(content_data['content'].split()),
            seo_score=seo_score,
            readability_score=readability_score,
            local_optimization_score=local_optimization_score,
            schema_markup=schema_markup
        )
        
        return generated_content
    
    async def _generate_blog_post(
        self, 
        request: ContentRequest,
        business_data: Dict[str, Any],
        template: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate a blog post optimized for local SEO"""
        
        business_name = business_data.get('business_name', 'Your Business')
        location = request.location
        primary_keyword = request.target_keywords[0] if request.target_keywords else request.topic
        
        # Generate title variations and select best
        title_options = [
            f"The Complete Guide to {request.topic} in {location}",
            f"{request.topic}: What {location} Residents Need to Know",
            f"Expert {request.topic} Services in {location} - {business_name}",
            f"Top {request.topic} Tips for {location} Homeowners"
        ]
        
        title = title_options[0]  # In production, would use AI to select best
        
        # Generate content sections
        introduction = await self._generate_introduction(request, business_name, location)
        problem_section = await self._generate_problem_section(request, location)
        solution_section = await self._generate_solution_section(request, business_name, location)
        benefits_section = await self._generate_benefits_section(request, business_name)
        local_context = await self._generate_local_context(request, location, business_name)
        conclusion = await self._generate_conclusion(request, business_name, location)
        
        # Combine sections
        content_sections = [
            introduction,
            problem_section,
            solution_section,
            benefits_section,
            local_context,
            conclusion
        ]
        
        if request.include_cta:
            cta_section = await self._generate_cta_section(business_name, business_data)
            content_sections.append(cta_section)
        
        content = '\n\n'.join(content_sections)
        
        # Generate meta description
        meta_description = f"Expert {request.topic} services in {location}. {business_name} provides professional solutions for {location} residents. Contact us today for a free consultation!"
        
        return {
            'title': title,
            'content': content,
            'meta_description': meta_description[:160]  # Limit to 160 chars
        }
    
    async def _generate_introduction(self, request: ContentRequest, business_name: str, location: str) -> str:
        """Generate engaging introduction paragraph"""
        
        topic = request.topic
        primary_keyword = request.target_keywords[0] if request.target_keywords else topic
        
        if request.category == ContentCategory.HOW_TO:
            intro = f"If you're a {location} resident dealing with {topic.lower()}, you're not alone. Many homeowners in the {location} area face this challenge, but with the right approach, it's completely manageable. At {business_name}, we've helped hundreds of {location} families successfully handle {topic.lower()}, and we're here to share our expertise with you."
        
        elif request.category == ContentCategory.EDUCATIONAL:
            intro = f"Understanding {topic.lower()} is crucial for {location} property owners. Whether you're a longtime resident or new to the {location} area, having comprehensive knowledge about {primary_keyword.lower()} can save you time, money, and frustration. {business_name} has been serving the {location} community for years, and we've compiled this guide to help you make informed decisions."
        
        else:
            intro = f"When it comes to {topic.lower()} in {location}, you want to work with professionals who understand the unique needs of our community. {business_name} has been proudly serving {location} residents, providing expert {primary_keyword.lower()} services that deliver real results. Let's explore what you need to know about {topic.lower()} in our area."
        
        return intro
    
    async def _generate_problem_section(self, request: ContentRequest, location: str) -> str:
        """Generate problem/challenge section"""
        
        topic = request.topic
        
        section_title = f"## Common {topic} Challenges in {location}"
        
        # Generate location-specific challenges
        challenges = [
            f"The unique climate conditions in {location} can create specific {topic.lower()} issues",
            f"Local building codes and regulations in {location} add complexity to {topic.lower()} projects",
            f"Finding reliable, licensed professionals in the {location} area can be challenging",
            f"Understanding the specific needs of {location} properties requires local expertise"
        ]
        
        problem_content = f"{section_title}\n\n"
        problem_content += f"Residents of {location} face several unique challenges when it comes to {topic.lower()}:\n\n"
        
        for i, challenge in enumerate(challenges, 1):
            problem_content += f"{i}. **{challenge.split(',')[0]}**: {challenge}\n"
        
        problem_content += f"\nThese challenges require a deep understanding of both {topic.lower()} and the specific needs of the {location} community."
        
        return problem_content
    
    async def _generate_solution_section(self, request: ContentRequest, business_name: str, location: str) -> str:
        """Generate solution-focused section"""
        
        topic = request.topic
        primary_keyword = request.target_keywords[0] if request.target_keywords else topic
        
        section_title = f"## Professional {topic} Solutions in {location}"
        
        solution_content = f"{section_title}\n\n"
        solution_content += f"At {business_name}, we've developed comprehensive solutions specifically for {location} residents:\n\n"
        
        # Generate solution points
        solutions = [
            f"**Local Expertise**: Our team understands the unique {primary_keyword.lower()} needs in {location}",
            f"**Comprehensive Service**: We handle every aspect of {topic.lower()} from consultation to completion",
            f"**Quality Guarantee**: All our {primary_keyword.lower()} work comes with a satisfaction guarantee",
            f"**Emergency Response**: We provide 24/7 emergency {topic.lower()} services throughout {location}"
        ]
        
        for solution in solutions:
            solution_content += f"- {solution}\n"
        
        solution_content += f"\nOur proven approach has helped hundreds of {location} families successfully resolve their {topic.lower()} challenges."
        
        return solution_content
    
    async def _generate_service_page(
        self,
        request: ContentRequest,
        business_data: Dict[str, Any],
        template: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate service page content"""
        
        business_name = business_data.get('business_name', 'Your Business')
        location = request.location
        service = request.topic
        phone = business_data.get('phone', '(XXX) XXX-XXXX')
        
        title = f"Professional {service} Services in {location} | {business_name}"
        
        # Hero section
        hero = f"# Expert {service} Services in {location}\n\n"
        hero += f"When you need reliable {service.lower()} in {location}, {business_name} delivers exceptional results with personalized service. Our experienced team has been serving the {location} community with professional {service.lower()} solutions that you can trust."
        
        # Service overview
        overview = f"## Comprehensive {service} Solutions\n\n"
        overview += f"Our {service.lower()} services in {location} include:\n\n"
        
        service_list = [
            f"Complete {service.lower()} installation and setup",
            f"Expert {service.lower()} repair and maintenance",
            f"Emergency {service.lower()} services available 24/7",
            f"Free {service.lower()} consultations and estimates"
        ]
        
        for service_item in service_list:
            overview += f"- {service_item}\n"
        
        # Benefits section
        benefits = f"## Why Choose {business_name} for {service} in {location}?\n\n"
        benefits += f"- **Local Expertise**: Deep knowledge of {location} area requirements\n"
        benefits += f"- **Licensed & Insured**: Fully certified {service.lower()} professionals\n"
        benefits += f"- **Satisfaction Guarantee**: We stand behind all our {service.lower()} work\n"
        benefits += f"- **Competitive Pricing**: Fair, transparent pricing for all {service.lower()} services\n"
        
        # Call to action
        cta = f"## Schedule Your {service} Service Today\n\n"
        cta += f"Ready to get started with professional {service.lower()} in {location}? Contact {business_name} today for a free consultation. Call {phone} or fill out our online form to schedule your service."
        
        content = '\n\n'.join([hero, overview, benefits, cta])
        
        meta_description = f"Professional {service.lower()} services in {location}. {business_name} offers expert {service.lower()} solutions with guaranteed satisfaction. Call {phone} today!"
        
        return {
            'title': title,
            'content': content,
            'meta_description': meta_description[:160]
        }
    
    async def _generate_location_page(
        self,
        request: ContentRequest,
        business_data: Dict[str, Any], 
        template: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate location-specific landing page content"""
        
        business_name = business_data.get('business_name', 'Your Business')
        location = request.location
        services = business_data.get('services', ['services'])
        phone = business_data.get('phone', '(XXX) XXX-XXXX')
        
        title = f"{business_name} - Serving {location} | Professional Local Services"
        
        # Local introduction
        intro = f"# {business_name} Proudly Serves {location}\n\n"
        intro += f"For years, {business_name} has been the trusted choice for residents and businesses throughout {location}. Our commitment to exceptional service and local expertise has made us a cornerstone of the {location} community."
        
        # Services in location
        services_section = f"## Our Services in {location}\n\n"
        services_section += f"We provide comprehensive services throughout the {location} area:\n\n"
        
        for service in services[:5]:  # Top 5 services
            services_section += f"- **{service}**: Professional {service.lower()} services throughout {location}\n"
        
        # Area expertise
        expertise = f"## Why {location} Chooses {business_name}\n\n"
        expertise += f"Our deep understanding of the {location} area sets us apart:\n\n"
        expertise += f"- **Local Knowledge**: We understand the unique needs of {location} properties\n"
        expertise += f"- **Community Commitment**: Active members of the {location} business community\n"
        expertise += f"- **Fast Response**: Quick response times throughout the {location} area\n"
        expertise += f"- **Licensed & Insured**: Fully certified to work in {location}\n"
        
        # Contact section
        contact = f"## Contact {business_name} in {location}\n\n"
        contact += f"Ready to experience the {business_name} difference? We're here to serve all your needs in {location}. Call us at {phone} for immediate assistance or to schedule a free consultation."
        
        content = '\n\n'.join([intro, services_section, expertise, contact])
        
        meta_description = f"{business_name} serves {location} with professional services. Local expertise, fast response, satisfaction guaranteed. Call {phone} today!"
        
        return {
            'title': title,
            'content': content,
            'meta_description': meta_description[:160]
        }
    
    async def _generate_faq_content(
        self,
        request: ContentRequest,
        business_data: Dict[str, Any],
        template: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate FAQ content optimized for voice search"""
        
        business_name = business_data.get('business_name', 'Your Business')
        location = request.location
        topic = request.topic
        phone = business_data.get('phone', '(XXX) XXX-XXXX')
        
        # Generate question-answer pairs
        faq_pairs = []
        
        # Common FAQ patterns for local businesses
        faq_templates = [
            {
                'question': f"What {topic.lower()} services do you offer in {location}?",
                'answer': f"We provide comprehensive {topic.lower()} services throughout {location}, including emergency repairs, routine maintenance, installations, and consultations. Our experienced team serves residential and commercial customers in the {location} area."
            },
            {
                'question': f"How much does {topic.lower()} cost in {location}?",
                'answer': f"{topic} costs in {location} vary based on the scope of work needed. We provide free estimates for all {topic.lower()} projects. Contact {business_name} at {phone} for a personalized quote based on your specific needs."
            },
            {
                'question': f"Do you offer emergency {topic.lower()} services in {location}?",
                'answer': f"Yes! {business_name} provides 24/7 emergency {topic.lower()} services throughout {location}. Our emergency response team is available for urgent situations. Call {phone} immediately for emergency assistance."
            },
            {
                'question': f"Are you licensed for {topic.lower()} work in {location}?",
                'answer': f"Absolutely. {business_name} is fully licensed and insured for all {topic.lower()} work in {location}. Our certifications and insurance coverage protect both our customers and our team during all projects."
            }
        ]
        
        title = f"Frequently Asked Questions About {topic} in {location}"
        
        # Format FAQ content
        content = f"# {title}\n\n"
        
        for i, faq in enumerate(faq_templates, 1):
            content += f"## {faq['question']}\n\n"
            content += f"{faq['answer']}\n\n"
        
        # Add contact information
        content += f"## Have More Questions?\n\n"
        content += f"If you have additional questions about {topic.lower()} in {location}, don't hesitate to contact {business_name}. Our knowledgeable team is here to help! Call {phone} or visit our website for more information."
        
        meta_description = f"Get answers to common {topic.lower()} questions in {location}. {business_name} provides expert guidance and professional services. Call {phone} today!"
        
        return {
            'title': title,
            'content': content,
            'meta_description': meta_description[:160]
        }
    
    async def _calculate_seo_score(self, content_data: Dict[str, str], request: ContentRequest) -> float:
        """Calculate SEO optimization score for generated content"""
        
        title = content_data['title']
        content = content_data['content']
        meta_desc = content_data['meta_description']
        
        score_factors = []
        
        # Title optimization (20%)
        title_score = 0
        if request.target_keywords:
            primary_keyword = request.target_keywords[0].lower()
            if primary_keyword in title.lower():
                title_score += 0.7
            if len(title) <= 60:
                title_score += 0.3
        score_factors.append(title_score * 0.2)
        
        # Content keyword optimization (25%)
        keyword_score = 0
        if request.target_keywords:
            for keyword in request.target_keywords:
                keyword_count = content.lower().count(keyword.lower())
                content_words = len(content.split())
                keyword_density = keyword_count / content_words if content_words > 0 else 0
                
                # Optimal keyword density: 1-3%
                if 0.01 <= keyword_density <= 0.03:
                    keyword_score += 0.5 / len(request.target_keywords)
                elif keyword_density > 0:
                    keyword_score += 0.3 / len(request.target_keywords)
        score_factors.append(keyword_score * 0.25)
        
        # Content length (15%)
        word_count = len(content.split())
        length_score = 0
        if word_count >= 800:
            length_score = 1.0
        elif word_count >= 500:
            length_score = 0.7
        elif word_count >= 300:
            length_score = 0.5
        score_factors.append(length_score * 0.15)
        
        # Meta description (10%)
        meta_score = 0
        if len(meta_desc) <= 160 and len(meta_desc) >= 120:
            meta_score += 0.5
        if request.target_keywords and request.target_keywords[0].lower() in meta_desc.lower():
            meta_score += 0.5
        score_factors.append(meta_score * 0.1)
        
        # Header structure (15%)
        header_score = 0
        h2_count = content.count('## ')
        h3_count = content.count('### ')
        if h2_count >= 2:
            header_score += 0.5
        if h3_count >= 1:
            header_score += 0.3
        if content.count('# ') == 1:  # Single H1
            header_score += 0.2
        score_factors.append(header_score * 0.15)
        
        # Local SEO elements (15%)
        local_score = 0
        location = request.location.lower()
        if location in content.lower():
            location_mentions = content.lower().count(location)
            if 3 <= location_mentions <= 8:
                local_score = 1.0
            elif location_mentions > 0:
                local_score = 0.6
        score_factors.append(local_score * 0.15)
        
        total_score = sum(score_factors)
        return round(total_score * 100, 1)  # Return as percentage
    
    async def _calculate_readability_score(self, content: str) -> float:
        """Calculate readability score (simplified Flesch Reading Ease)"""
        
        sentences = len(re.findall(r'[.!?]+', content))
        words = len(content.split())
        syllables = self._count_syllables(content)
        
        if sentences == 0 or words == 0:
            return 0
        
        # Simplified Flesch Reading Ease formula
        avg_sentence_length = words / sentences
        avg_syllables_per_word = syllables / words
        
        reading_ease = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)
        
        # Convert to 0-100 scale where 100 is most readable
        return max(0, min(100, reading_ease))
    
    def _count_syllables(self, text: str) -> int:
        """Simple syllable counting for readability calculation"""
        
        words = text.lower().split()
        syllable_count = 0
        
        for word in words:
            # Remove punctuation
            word = re.sub(r'[^a-z]', '', word)
            if not word:
                continue
                
            # Simple syllable estimation
            vowels = 'aeiouy'
            syllables = 0
            prev_char_was_vowel = False
            
            for char in word:
                if char in vowels:
                    if not prev_char_was_vowel:
                        syllables += 1
                    prev_char_was_vowel = True
                else:
                    prev_char_was_vowel = False
            
            # Handle silent e
            if word.endswith('e') and syllables > 1:
                syllables -= 1
            
            # Every word has at least 1 syllable
            syllables = max(1, syllables)
            syllable_count += syllables
        
        return syllable_count
    
    async def _calculate_local_seo_score(self, content_data: Dict[str, str], location: str, business_name: str) -> float:
        """Calculate local SEO optimization score"""
        
        content = content_data['content']
        title = content_data['title']
        
        local_factors = []
        
        # Location mentions (30%)
        location_score = 0
        location_mentions = content.lower().count(location.lower())
        if 3 <= location_mentions <= 8:
            location_score = 1.0
        elif location_mentions > 0:
            location_score = 0.6
        local_factors.append(location_score * 0.3)
        
        # Business name mentions (20%)
        business_score = 0
        business_mentions = content.lower().count(business_name.lower())
        if 2 <= business_mentions <= 5:
            business_score = 1.0
        elif business_mentions > 0:
            business_score = 0.7
        local_factors.append(business_score * 0.2)
        
        # Local keywords in title (25%)
        title_local_score = 0
        if location.lower() in title.lower():
            title_local_score += 0.7
        if business_name.lower() in title.lower():
            title_local_score += 0.3
        local_factors.append(title_local_score * 0.25)
        
        # Contact information (15%)
        contact_score = 0
        if 'phone' in content.lower() or 'call' in content.lower():
            contact_score += 0.5
        if 'contact' in content.lower():
            contact_score += 0.3
        if 'address' in content.lower():
            contact_score += 0.2
        local_factors.append(min(1.0, contact_score) * 0.15)
        
        # Service area references (10%)
        area_score = 0
        area_keywords = ['serving', 'area', 'community', 'local', 'nearby', 'region']
        for keyword in area_keywords:
            if keyword in content.lower():
                area_score += 0.2
        local_factors.append(min(1.0, area_score) * 0.1)
        
        total_local_score = sum(local_factors)
        return round(total_local_score * 100, 1)
    
    async def _generate_schema_markup(
        self,
        request: ContentRequest,
        content_data: Dict[str, str],
        business_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Generate appropriate schema markup for content"""
        
        if request.content_type == ContentType.BLOG_POST:
            return {
                '@context': 'https://schema.org',
                '@type': 'Article',
                'headline': content_data['title'],
                'description': content_data['meta_description'],
                'author': {
                    '@type': 'Organization',
                    'name': business_data.get('business_name', 'Your Business')
                },
                'datePublished': datetime.now().isoformat(),
                'dateModified': datetime.now().isoformat()
            }
        
        elif request.content_type == ContentType.FAQ_CONTENT:
            return {
                '@context': 'https://schema.org',
                '@type': 'FAQPage',
                'mainEntity': [
                    {
                        '@type': 'Question',
                        'name': 'Sample FAQ Question',
                        'acceptedAnswer': {
                            '@type': 'Answer',
                            'text': 'Sample FAQ Answer'
                        }
                    }
                ]
            }
        
        elif request.content_type == ContentType.SERVICE_PAGE:
            return {
                '@context': 'https://schema.org',
                '@type': 'Service',
                'name': request.topic,
                'description': content_data['meta_description'],
                'provider': {
                    '@type': 'LocalBusiness',
                    'name': business_data.get('business_name', 'Your Business'),
                    'address': business_data.get('address', {}),
                    'telephone': business_data.get('phone', ''),
                    'url': business_data.get('website', '')
                },
                'areaServed': request.location
            }
        
        return None
    
    async def create_content_calendar(
        self,
        business_data: Dict[str, Any],
        months_ahead: int = 3
    ) -> Dict[str, Any]:
        """Generate a comprehensive content calendar"""
        
        calendar_data = {
            'period': f"{months_ahead} months",
            'total_content_pieces': 0,
            'monthly_breakdown': {},
            'content_schedule': [],
            'topics_covered': [],
            'estimated_effort_hours': 0
        }
        
        business_name = business_data.get('business_name', 'Your Business')
        location = business_data.get('location', 'your area')
        services = business_data.get('services', [])
        
        # Generate content ideas for each month
        for month_offset in range(months_ahead):
            target_date = datetime.now() + timedelta(days=30 * month_offset)
            month_name = target_date.strftime('%B %Y')
            
            monthly_content = []
            
            # Weekly blog posts (4 per month)
            blog_topics = [
                f"Common {services[0] if services else 'Service'} Issues in {location}",
                f"Seasonal Maintenance Tips for {location} Homeowners",
                f"Why Choose Local {services[0] if services else 'Services'} in {location}",
                f"{business_name} Success Stories from {location}"
            ]
            
            for i, topic in enumerate(blog_topics):
                content_item = {
                    'type': 'blog_post',
                    'title': topic,
                    'target_date': (target_date + timedelta(days=7 * i)).isoformat(),
                    'estimated_words': 1000,
                    'estimated_hours': 3,
                    'keywords': [services[0] if services else 'service', location],
                    'category': 'educational'
                }
                monthly_content.append(content_item)
            
            # Monthly service spotlight (1 per month)
            if services:
                service_spotlight = {
                    'type': 'service_page',
                    'title': f"Professional {services[month_offset % len(services)]} in {location}",
                    'target_date': (target_date + timedelta(days=15)).isoformat(),
                    'estimated_words': 800,
                    'estimated_hours': 2.5,
                    'keywords': [services[month_offset % len(services)], location],
                    'category': 'promotional'
                }
                monthly_content.append(service_spotlight)
            
            # FAQ updates (2 per month)
            faq_topics = [
                f"Pricing and Cost Information",
                f"Emergency Services Availability"
            ]
            
            for j, faq_topic in enumerate(faq_topics):
                faq_content = {
                    'type': 'faq_content',
                    'title': f"FAQ: {faq_topic}",
                    'target_date': (target_date + timedelta(days=10 + 14 * j)).isoformat(),
                    'estimated_words': 300,
                    'estimated_hours': 1,
                    'keywords': [location, faq_topic.lower()],
                    'category': 'informational'
                }
                monthly_content.append(faq_content)
            
            calendar_data['monthly_breakdown'][month_name] = {
                'content_pieces': len(monthly_content),
                'estimated_hours': sum(item['estimated_hours'] for item in monthly_content),
                'content_types': list(set(item['type'] for item in monthly_content))
            }
            
            calendar_data['content_schedule'].extend(monthly_content)
        
        # Calculate totals
        calendar_data['total_content_pieces'] = len(calendar_data['content_schedule'])
        calendar_data['estimated_effort_hours'] = sum(
            item['estimated_hours'] for item in calendar_data['content_schedule']
        )
        calendar_data['topics_covered'] = list(set(
            item['title'] for item in calendar_data['content_schedule']
        ))
        
        return calendar_data

# Integration function
async def integrate_ai_content_generation():
    """Integration function for AI content generation"""
    
    # Initialize content generator
    content_generator = AIContentGenerator()
    
    # Sample business data
    business_data = {
        'business_name': 'Orlando Professional Services',
        'location': 'Orlando, FL',
        'phone': '(407) 555-0123',
        'website': 'https://orlandoproservices.com',
        'services': ['HVAC Repair', 'Plumbing Services', 'Electrical Work', 'Home Maintenance']
    }
    
    # Create content requests
    content_requests = [
        ContentRequest(
            content_type=ContentType.BLOG_POST,
            category=ContentCategory.HOW_TO,
            topic='HVAC Maintenance',
            target_keywords=['HVAC maintenance Orlando', 'Orlando HVAC service'],
            location='Orlando, FL',
            business_type='home_services',
            word_count_target=1200,
            tone='professional',
            include_cta=True,
            seo_focus=['local', 'educational']
        ),
        ContentRequest(
            content_type=ContentType.SERVICE_PAGE,
            category=ContentCategory.PROMOTIONAL,
            topic='Emergency Plumbing',
            target_keywords=['emergency plumber Orlando', '24/7 plumbing Orlando'],
            location='Orlando, FL',
            business_type='plumbing',
            word_count_target=800,
            tone='professional',
            include_cta=True,
            seo_focus=['local', 'conversion']
        ),
        ContentRequest(
            content_type=ContentType.FAQ_CONTENT,
            category=ContentCategory.EDUCATIONAL,
            topic='Common Electrical Issues',
            target_keywords=['electrical problems Orlando', 'electrician Orlando'],
            location='Orlando, FL',
            business_type='electrical',
            word_count_target=400,
            tone='friendly',
            include_cta=True,
            seo_focus=['local', 'voice_search']
        )
    ]
    
    # Generate content batch
    print("🤖 Generating AI-powered content...")
    generation_results = await content_generator.generate_content_batch(content_requests, business_data)
    print(f"Successfully generated {generation_results['successfully_generated']} pieces of content")
    print(f"Total words: {generation_results['total_word_count']}")
    print(f"Average SEO score: {generation_results['average_seo_score']:.1f}%")
    
    # Create content calendar
    print("📅 Creating content calendar...")
    calendar_results = await content_generator.create_content_calendar(business_data, months_ahead=3)
    print(f"Planned {calendar_results['total_content_pieces']} pieces over {calendar_results['period']}")
    print(f"Estimated effort: {calendar_results['estimated_effort_hours']} hours")
    
    return {
        'content_generation': generation_results,
        'content_calendar': calendar_results
    }

if __name__ == "__main__":
    asyncio.run(integrate_ai_content_generation())
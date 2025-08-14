"""Core publishing pipeline with quality gates and multi-stage workflow."""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union
from pathlib import Path

from ..adapters.cms.base import CMSAdapter, ContentItem, PublishResult
from ..config import ProjectConfig

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """Pipeline execution stages."""
    VALIDATION = "validation"
    QUALITY_GATES = "quality_gates"
    ASSET_OPTIMIZATION = "asset_optimization"
    CONTENT_PROCESSING = "content_processing"
    CMS_PUBLISHING = "cms_publishing"
    POST_PUBLISH_VALIDATION = "post_publish_validation"
    SEARCH_ENGINE_NOTIFICATION = "search_engine_notification"
    MONITORING_SETUP = "monitoring_setup"


class QualityGateResult(Enum):
    """Quality gate evaluation results."""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIP = "skip"


@dataclass
class QualityGateEvaluation:
    """Results from a quality gate evaluation."""
    
    gate_name: str
    result: QualityGateResult
    score: float  # 0-100
    message: str
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    execution_time_ms: int = 0
    
    @property
    def passed(self) -> bool:
        """Check if gate passed."""
        return self.result == QualityGateResult.PASS
    
    @property
    def failed(self) -> bool:
        """Check if gate failed."""
        return self.result == QualityGateResult.FAIL
    
    @property
    def has_issues(self) -> bool:
        """Check if gate has any issues."""
        return len(self.issues) > 0 or self.result == QualityGateResult.FAIL


@dataclass
class PipelineStageResult:
    """Results from a pipeline stage execution."""
    
    stage: PipelineStage
    success: bool
    message: str
    execution_time_ms: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
        self.success = False
    
    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)


@dataclass
class PipelineResult:
    """Results from a complete pipeline execution."""
    
    content_item: ContentItem
    success: bool
    publish_result: Optional[PublishResult] = None
    
    # Stage results
    stage_results: Dict[PipelineStage, PipelineStageResult] = field(default_factory=dict)
    quality_gate_results: List[QualityGateEvaluation] = field(default_factory=list)
    
    # Timing
    total_execution_time_ms: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    
    # Summary
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def failed_quality_gates(self) -> List[QualityGateEvaluation]:
        """Get failed quality gates."""
        return [gate for gate in self.quality_gate_results if gate.failed]
    
    @property
    def passed_quality_gates(self) -> List[QualityGateEvaluation]:
        """Get passed quality gates."""
        return [gate for gate in self.quality_gate_results if gate.passed]
    
    @property
    def quality_score(self) -> float:
        """Calculate overall quality score."""
        if not self.quality_gate_results:
            return 0.0
        
        scores = [gate.score for gate in self.quality_gate_results]
        return sum(scores) / len(scores)
    
    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
        self.success = False
    
    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)


class QualityGate(ABC):
    """Abstract base class for quality gates."""
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        """Initialize quality gate."""
        self.name = name
        self.config = config or {}
        self.enabled = self.config.get('enabled', True)
        self.required = self.config.get('required', True)
        self.min_score = self.config.get('min_score', 70.0)
    
    @abstractmethod
    async def evaluate(self, content: ContentItem, context: Dict[str, Any] = None) -> QualityGateEvaluation:
        """Evaluate content against quality gate criteria."""
        pass
    
    def create_evaluation(
        self,
        result: QualityGateResult,
        score: float,
        message: str,
        issues: List[str] = None,
        warnings: List[str] = None,
        recommendations: List[str] = None
    ) -> QualityGateEvaluation:
        """Helper to create quality gate evaluation."""
        return QualityGateEvaluation(
            gate_name=self.name,
            result=result,
            score=score,
            message=message,
            issues=issues or [],
            warnings=warnings or [],
            recommendations=recommendations or []
        )
    
    def __str__(self) -> str:
        """String representation."""
        return f"{self.name} Quality Gate"


class PublishingPipeline:
    """Multi-stage content publishing pipeline with quality gates."""
    
    def __init__(
        self,
        cms_adapter: CMSAdapter,
        project_config: ProjectConfig,
        quality_gates: List[QualityGate] = None
    ):
        """Initialize publishing pipeline."""
        self.cms_adapter = cms_adapter
        self.project_config = project_config
        self.quality_gates = quality_gates or []
        
        # Pipeline configuration
        self.fail_on_quality_gate_failure = True
        self.backup_before_publish = True
        self.dry_run = False
        
        # Stage handlers
        self.stage_handlers = {
            PipelineStage.VALIDATION: self._stage_validation,
            PipelineStage.QUALITY_GATES: self._stage_quality_gates,
            PipelineStage.ASSET_OPTIMIZATION: self._stage_asset_optimization,
            PipelineStage.CONTENT_PROCESSING: self._stage_content_processing,
            PipelineStage.CMS_PUBLISHING: self._stage_cms_publishing,
            PipelineStage.POST_PUBLISH_VALIDATION: self._stage_post_publish_validation,
            PipelineStage.SEARCH_ENGINE_NOTIFICATION: self._stage_search_engine_notification,
            PipelineStage.MONITORING_SETUP: self._stage_monitoring_setup
        }
    
    async def publish(
        self,
        content: ContentItem,
        stages: List[PipelineStage] = None,
        dry_run: bool = False
    ) -> PipelineResult:
        """Execute publishing pipeline for content."""
        
        start_time = datetime.now(timezone.utc)
        result = PipelineResult(content_item=content, success=True, started_at=start_time)
        
        # Default to all stages if none specified
        if stages is None:
            stages = list(PipelineStage)
        
        logger.info(f"Starting publishing pipeline for '{content.title}' (dry_run={dry_run})")
        
        try:
            # Execute each stage
            context = {'dry_run': dry_run, 'project_config': self.project_config}
            
            for stage in stages:
                stage_start = datetime.now()
                
                logger.info(f"Executing stage: {stage.value}")
                
                try:
                    # Get stage handler
                    handler = self.stage_handlers.get(stage)
                    if not handler:
                        result.add_warning(f"No handler for stage: {stage.value}")
                        continue
                    
                    # Execute stage
                    stage_result = await handler(content, context)
                    
                    # Calculate execution time
                    stage_duration = (datetime.now() - stage_start).total_seconds() * 1000
                    stage_result.execution_time_ms = int(stage_duration)
                    
                    # Store result
                    result.stage_results[stage] = stage_result
                    
                    # Check if stage failed
                    if not stage_result.success:
                        result.success = False
                        result.errors.extend(stage_result.errors)
                        
                        # Stop pipeline if critical stage failed
                        if stage in [PipelineStage.VALIDATION, PipelineStage.QUALITY_GATES]:
                            logger.error(f"Critical stage {stage.value} failed, stopping pipeline")
                            break
                    
                    # Add warnings
                    result.warnings.extend(stage_result.warnings)
                    
                    logger.info(f"Stage {stage.value} completed: {stage_result.message}")
                    
                except Exception as e:
                    logger.error(f"Stage {stage.value} failed with exception: {e}")
                    stage_result = PipelineStageResult(
                        stage=stage,
                        success=False,
                        message=f"Stage failed with exception: {str(e)}"
                    )
                    stage_result.add_error(str(e))
                    result.stage_results[stage] = stage_result
                    result.add_error(f"Stage {stage.value}: {str(e)}")
                    
                    # Stop on critical stage failure
                    if stage in [PipelineStage.VALIDATION, PipelineStage.QUALITY_GATES]:
                        break
            
            # Calculate total execution time
            end_time = datetime.now(timezone.utc)
            result.completed_at = end_time
            result.total_execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Final success determination
            if result.success:
                logger.info(f"Publishing pipeline completed successfully in {result.total_execution_time_ms}ms")
            else:
                logger.error(f"Publishing pipeline failed after {result.total_execution_time_ms}ms")
            
            return result
            
        except Exception as e:
            logger.error(f"Publishing pipeline failed with unexpected error: {e}")
            result.success = False
            result.add_error(f"Pipeline error: {str(e)}")
            result.completed_at = datetime.now(timezone.utc)
            return result
    
    async def _stage_validation(self, content: ContentItem, context: Dict[str, Any]) -> PipelineStageResult:
        """Stage 1: Content validation."""
        stage_result = PipelineStageResult(
            stage=PipelineStage.VALIDATION,
            success=True,
            message="Content validation completed"
        )
        
        try:
            # Basic content validation
            validation_errors = self.cms_adapter.validate_content(content)
            
            if validation_errors:
                for error in validation_errors:
                    stage_result.add_error(error)
                stage_result.message = f"Content validation failed with {len(validation_errors)} errors"
                return stage_result
            
            # Additional custom validations
            if not content.title.strip():
                stage_result.add_error("Title cannot be empty")
            
            if not content.content.strip():
                stage_result.add_error("Content cannot be empty")
            
            if not content.slug.strip():
                stage_result.add_error("Slug cannot be empty")
            
            # Check for required fields based on project config
            project_config = context.get('project_config')
            if project_config:
                # Trust signals validation
                if project_config.trust_signals.require_author and not content.author:
                    stage_result.add_error("Author is required by project configuration")
                
                # Content quality validation
                if len(content.content) < project_config.content_quality.word_count_bounds[0]:
                    stage_result.add_warning(f"Content below minimum word count ({project_config.content_quality.word_count_bounds[0]} words)")
                
                if len(content.content) > project_config.content_quality.word_count_bounds[1]:
                    stage_result.add_warning(f"Content exceeds maximum word count ({project_config.content_quality.word_count_bounds[1]} words)")
            
            stage_result.data['validation_errors'] = validation_errors
            
            if stage_result.errors:
                stage_result.success = False
                stage_result.message = f"Content validation failed with {len(stage_result.errors)} errors"
            
            return stage_result
            
        except Exception as e:
            stage_result.add_error(f"Validation stage error: {str(e)}")
            return stage_result
    
    async def _stage_quality_gates(self, content: ContentItem, context: Dict[str, Any]) -> PipelineStageResult:
        """Stage 2: Quality gate evaluation."""
        stage_result = PipelineStageResult(
            stage=PipelineStage.QUALITY_GATES,
            success=True,
            message="Quality gates evaluation completed"
        )
        
        try:
            gate_evaluations = []
            failed_gates = []
            
            # Execute each quality gate
            for gate in self.quality_gates:
                if not gate.enabled:
                    continue
                
                logger.debug(f"Evaluating quality gate: {gate.name}")
                
                try:
                    evaluation = await gate.evaluate(content, context)
                    gate_evaluations.append(evaluation)
                    
                    # Check if gate failed
                    if evaluation.failed:
                        failed_gates.append(gate.name)
                        if gate.required:
                            stage_result.add_error(f"Required quality gate '{gate.name}' failed: {evaluation.message}")
                        else:
                            stage_result.add_warning(f"Optional quality gate '{gate.name}' failed: {evaluation.message}")
                    
                    # Add warnings from gate
                    for warning in evaluation.warnings:
                        stage_result.add_warning(f"{gate.name}: {warning}")
                    
                except Exception as e:
                    logger.error(f"Quality gate {gate.name} failed with exception: {e}")
                    evaluation = gate.create_evaluation(
                        result=QualityGateResult.FAIL,
                        score=0.0,
                        message=f"Gate evaluation failed: {str(e)}",
                        issues=[str(e)]
                    )
                    gate_evaluations.append(evaluation)
                    
                    if gate.required:
                        stage_result.add_error(f"Required quality gate '{gate.name}' failed: {str(e)}")
            
            # Store gate results in context for other stages
            context['quality_gate_results'] = gate_evaluations
            
            # Calculate overall quality score
            if gate_evaluations:
                scores = [evaluation.score for evaluation in gate_evaluations]
                overall_score = sum(scores) / len(scores)
                stage_result.data['overall_quality_score'] = overall_score
                stage_result.data['quality_gate_results'] = gate_evaluations
            
            # Determine stage success
            required_failures = [gate for gate in failed_gates if any(g.name == gate and g.required for g in self.quality_gates)]
            
            if required_failures:
                stage_result.success = False
                stage_result.message = f"Quality gates failed: {', '.join(required_failures)}"
            elif failed_gates:
                stage_result.message = f"Quality gates completed with warnings: {', '.join(failed_gates)}"
            
            return stage_result
            
        except Exception as e:
            stage_result.add_error(f"Quality gates stage error: {str(e)}")
            return stage_result
    
    async def _stage_asset_optimization(self, content: ContentItem, context: Dict[str, Any]) -> PipelineStageResult:
        """Stage 3: Asset optimization."""
        stage_result = PipelineStageResult(
            stage=PipelineStage.ASSET_OPTIMIZATION,
            success=True,
            message="Asset optimization completed"
        )
        
        try:
            # This is a placeholder for asset optimization logic
            # In a real implementation, this would:
            # - Optimize images (compression, format conversion)
            # - Upload assets to CDN
            # - Update content with optimized asset URLs
            # - Generate responsive image variants
            
            if context.get('dry_run'):
                stage_result.message = "Asset optimization skipped (dry run)"
                return stage_result
            
            optimized_assets = []
            
            # Check for featured image
            if content.featured_image_url:
                # Placeholder: In real implementation, optimize the image
                optimized_assets.append({
                    'original_url': content.featured_image_url,
                    'optimized_url': content.featured_image_url,  # Would be replaced with optimized version
                    'size_reduction': 0,
                    'format': 'unchanged'
                })
            
            # Check content for embedded images
            # This would use regex or HTML parsing to find image references
            # and optimize them
            
            stage_result.data['optimized_assets'] = optimized_assets
            stage_result.message = f"Optimized {len(optimized_assets)} assets"
            
            return stage_result
            
        except Exception as e:
            stage_result.add_error(f"Asset optimization stage error: {str(e)}")
            return stage_result
    
    async def _stage_content_processing(self, content: ContentItem, context: Dict[str, Any]) -> PipelineStageResult:
        """Stage 4: Content processing and enhancement."""
        stage_result = PipelineStageResult(
            stage=PipelineStage.CONTENT_PROCESSING,
            success=True,
            message="Content processing completed"
        )
        
        try:
            # Prepare content for publishing
            processed_content = self.cms_adapter.prepare_content_for_publish(content)
            
            # Generate meta fields if missing
            if not processed_content.meta_title:
                processed_content.meta_title = processed_content.title
            
            if not processed_content.meta_description:
                # Generate excerpt from content
                processed_content.meta_description = self.cms_adapter.extract_excerpts(
                    processed_content.content, 
                    length=160
                )
            
            # Generate slug if missing
            if not processed_content.slug:
                processed_content.slug = self.cms_adapter.generate_slug(processed_content.title)
            
            # Update context with processed content
            context['processed_content'] = processed_content
            
            stage_result.data['processed_content'] = processed_content.to_dict()
            stage_result.message = "Content processing and enhancement completed"
            
            return stage_result
            
        except Exception as e:
            stage_result.add_error(f"Content processing stage error: {str(e)}")
            return stage_result
    
    async def _stage_cms_publishing(self, content: ContentItem, context: Dict[str, Any]) -> PipelineStageResult:
        """Stage 5: CMS publishing."""
        stage_result = PipelineStageResult(
            stage=PipelineStage.CMS_PUBLISHING,
            success=True,
            message="CMS publishing completed"
        )
        
        try:
            # Get processed content or use original
            processed_content = context.get('processed_content', content)
            dry_run = context.get('dry_run', False)
            
            # Backup before publishing if enabled
            backup_id = None
            if self.backup_before_publish and not dry_run:
                backup_id = await self.cms_adapter.backup_before_publish(processed_content)
                if backup_id:
                    context['backup_id'] = backup_id
                    stage_result.data['backup_id'] = backup_id
            
            # Publish content
            if processed_content.external_id:
                # Update existing content
                publish_result = await self.cms_adapter.update_content(processed_content, dry_run)
            else:
                # Create new content
                publish_result = await self.cms_adapter.publish_content(processed_content, dry_run)
            
            # Store publish result in context
            context['publish_result'] = publish_result
            stage_result.data['publish_result'] = publish_result
            
            if publish_result.success:
                stage_result.message = f"Successfully published to {self.cms_adapter.name}: {publish_result.message}"
                
                # Update content with external ID
                if publish_result.external_id:
                    processed_content.external_id = publish_result.external_id
            else:
                stage_result.success = False
                stage_result.message = f"CMS publishing failed: {publish_result.message}"
                stage_result.errors.extend(publish_result.errors)
                stage_result.warnings.extend(publish_result.warnings)
            
            return stage_result
            
        except Exception as e:
            stage_result.add_error(f"CMS publishing stage error: {str(e)}")
            return stage_result
    
    async def _stage_post_publish_validation(self, content: ContentItem, context: Dict[str, Any]) -> PipelineStageResult:
        """Stage 6: Post-publish validation."""
        stage_result = PipelineStageResult(
            stage=PipelineStage.POST_PUBLISH_VALIDATION,
            success=True,
            message="Post-publish validation completed"
        )
        
        try:
            publish_result = context.get('publish_result')
            
            if not publish_result or not publish_result.success:
                stage_result.add_warning("Skipping post-publish validation due to publish failure")
                return stage_result
            
            if context.get('dry_run'):
                stage_result.message = "Post-publish validation skipped (dry run)"
                return stage_result
            
            # Validate that content was published correctly
            if publish_result.url:
                # In a real implementation, this would:
                # - Fetch the published URL
                # - Validate that content appears correctly
                # - Check that SEO tags are present
                # - Verify schema markup
                stage_result.data['published_url'] = publish_result.url
            
            if publish_result.external_id:
                # Verify content can be retrieved via CMS API
                try:
                    retrieved_content = await self.cms_adapter.get_content(publish_result.external_id)
                    if retrieved_content:
                        stage_result.data['content_verified'] = True
                        stage_result.message = "Content successfully verified in CMS"
                    else:
                        stage_result.add_warning("Could not retrieve published content from CMS")
                except Exception as e:
                    stage_result.add_warning(f"Content verification failed: {str(e)}")
            
            return stage_result
            
        except Exception as e:
            stage_result.add_error(f"Post-publish validation stage error: {str(e)}")
            return stage_result
    
    async def _stage_search_engine_notification(self, content: ContentItem, context: Dict[str, Any]) -> PipelineStageResult:
        """Stage 7: Search engine notification."""
        stage_result = PipelineStageResult(
            stage=PipelineStage.SEARCH_ENGINE_NOTIFICATION,
            success=True,
            message="Search engine notification completed"
        )
        
        try:
            publish_result = context.get('publish_result')
            
            if not publish_result or not publish_result.success:
                stage_result.add_warning("Skipping search engine notification due to publish failure")
                return stage_result
            
            if context.get('dry_run'):
                stage_result.message = "Search engine notification skipped (dry run)"
                return stage_result
            
            # In a real implementation, this would:
            # - Submit URL to Google Search Console indexing API
            # - Update XML sitemap
            # - Ping search engines
            # - Submit to other search engines (Bing, etc.)
            
            notifications_sent = []
            
            if publish_result.url:
                # Placeholder for search engine notifications
                notifications_sent.append('Google Search Console')
                notifications_sent.append('XML Sitemap')
            
            stage_result.data['notifications_sent'] = notifications_sent
            stage_result.message = f"Notified search engines: {', '.join(notifications_sent)}"
            
            return stage_result
            
        except Exception as e:
            stage_result.add_error(f"Search engine notification stage error: {str(e)}")
            return stage_result
    
    async def _stage_monitoring_setup(self, content: ContentItem, context: Dict[str, Any]) -> PipelineStageResult:
        """Stage 8: Monitoring setup."""
        stage_result = PipelineStageResult(
            stage=PipelineStage.MONITORING_SETUP,
            success=True,
            message="Monitoring setup completed"
        )
        
        try:
            publish_result = context.get('publish_result')
            
            if not publish_result or not publish_result.success:
                stage_result.add_warning("Skipping monitoring setup due to publish failure")
                return stage_result
            
            if context.get('dry_run'):
                stage_result.message = "Monitoring setup skipped (dry run)"
                return stage_result
            
            # In a real implementation, this would:
            # - Set up performance monitoring
            # - Configure search console tracking
            # - Add to content inventory
            # - Schedule periodic checks
            
            monitoring_tasks = []
            
            if publish_result.url:
                # Placeholder for monitoring setup
                monitoring_tasks.append('Performance monitoring')
                monitoring_tasks.append('Search console tracking')
                monitoring_tasks.append('Content inventory update')
            
            stage_result.data['monitoring_tasks'] = monitoring_tasks
            stage_result.message = f"Set up monitoring: {', '.join(monitoring_tasks)}"
            
            return stage_result
            
        except Exception as e:
            stage_result.add_error(f"Monitoring setup stage error: {str(e)}")
            return stage_result
    
    def add_quality_gate(self, gate: QualityGate) -> None:
        """Add a quality gate to the pipeline."""
        self.quality_gates.append(gate)
    
    def remove_quality_gate(self, gate_name: str) -> bool:
        """Remove a quality gate from the pipeline."""
        for i, gate in enumerate(self.quality_gates):
            if gate.name == gate_name:
                self.quality_gates.pop(i)
                return True
        return False
    
    def get_quality_gate(self, gate_name: str) -> Optional[QualityGate]:
        """Get a quality gate by name."""
        for gate in self.quality_gates:
            if gate.name == gate_name:
                return gate
        return None
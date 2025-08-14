"""Statistical CTR Testing Framework.

Provides Bayesian and frequentist A/B testing for titles and meta descriptions
with sequential test management, early stopping rules, and automated winner selection.
"""

import asyncio
import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

import numpy as np
from scipy import stats
from scipy.stats import beta, norm, chi2_contingency
import pandas as pd

from ..config import CTRTestingConfig, Settings
from ..models import CTRTest, AlertSeverity


logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """CTR test status values."""
    PLANNED = "planned"
    RUNNING = "running"
    STOPPED_EARLY = "stopped_early"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TestOutcome(Enum):
    """CTR test outcome values."""
    CONTROL_WINS = "control"
    VARIANT_WINS = "variant"
    INCONCLUSIVE = "inconclusive"
    INSUFFICIENT_DATA = "insufficient_data"


class TestMethod(Enum):
    """Statistical test methods."""
    FREQUENTIST = "frequentist"
    BAYESIAN = "bayesian"
    SEQUENTIAL = "sequential"


@dataclass
class CTRTestResults:
    """Results of a CTR test analysis."""
    test_id: str
    test_name: str
    status: TestStatus
    method: TestMethod
    
    # Control group metrics
    control_impressions: int
    control_clicks: int
    control_ctr: float
    control_confidence_interval: Tuple[float, float]
    
    # Variant group metrics
    variant_impressions: int
    variant_clicks: int
    variant_ctr: float
    variant_confidence_interval: Tuple[float, float]
    
    # Statistical analysis
    p_value: float
    confidence_level: float
    is_significant: bool
    effect_size: float  # CTR improvement
    practical_significance: bool
    
    # Test conclusion
    winner: TestOutcome
    winner_probability: float  # For Bayesian tests
    expected_improvement: float
    
    # Power analysis
    statistical_power: float
    sample_size_achieved: int
    sample_size_required: int
    
    # Test metadata
    test_duration_days: int
    early_stopping_triggered: bool
    stop_reason: Optional[str]
    recommendation: str


@dataclass
class PowerAnalysisResult:
    """Power analysis for sample size calculation."""
    minimum_detectable_effect: float
    required_sample_size: int
    expected_test_duration_days: int
    statistical_power: float
    baseline_ctr: float
    alpha: float
    
    # Traffic estimates
    estimated_daily_impressions: int
    estimated_total_impressions: int


class BayesianCTRTest:
    """Bayesian A/B testing for CTR experiments."""
    
    def __init__(self, 
                 alpha_prior: float = 1.0,
                 beta_prior: float = 1.0,
                 practical_significance_threshold: float = 0.01):
        """Initialize Bayesian CTR test.
        
        Args:
            alpha_prior: Prior alpha parameter for Beta distribution
            beta_prior: Prior beta parameter for Beta distribution
            practical_significance_threshold: Minimum meaningful CTR improvement
        """
        self.alpha_prior = alpha_prior
        self.beta_prior = beta_prior
        self.practical_significance_threshold = practical_significance_threshold
    
    def analyze_test(self, 
                     control_clicks: int,
                     control_impressions: int,
                     variant_clicks: int,
                     variant_impressions: int,
                     confidence_level: float = 0.95) -> Dict:
        """Perform Bayesian analysis of CTR test."""
        
        # Calculate posterior distributions
        control_alpha = self.alpha_prior + control_clicks
        control_beta = self.beta_prior + control_impressions - control_clicks
        
        variant_alpha = self.alpha_prior + variant_clicks
        variant_beta = self.beta_prior + variant_impressions - variant_clicks
        
        # Create posterior Beta distributions
        control_posterior = beta(control_alpha, control_beta)
        variant_posterior = beta(variant_alpha, variant_beta)
        
        # Calculate credible intervals
        alpha_level = 1 - confidence_level
        control_ci = control_posterior.interval(confidence_level)
        variant_ci = variant_posterior.interval(confidence_level)
        
        # Monte Carlo simulation for probability calculations
        n_samples = 100000
        control_samples = control_posterior.rvs(n_samples)
        variant_samples = variant_posterior.rvs(n_samples)
        
        # Probability that variant is better than control
        prob_variant_better = np.mean(variant_samples > control_samples)
        
        # Expected improvement
        improvement_samples = (variant_samples - control_samples) / control_samples
        expected_improvement = np.mean(improvement_samples)
        
        # Probability of practical significance
        prob_practical_significance = np.mean(
            improvement_samples >= self.practical_significance_threshold
        )
        
        # Calculate Bayes Factor
        bayes_factor = self._calculate_bayes_factor(
            control_clicks, control_impressions,
            variant_clicks, variant_impressions
        )
        
        return {
            'control_ctr_mean': control_alpha / (control_alpha + control_beta),
            'variant_ctr_mean': variant_alpha / (variant_alpha + variant_beta),
            'control_credible_interval': control_ci,
            'variant_credible_interval': variant_ci,
            'probability_variant_better': prob_variant_better,
            'expected_improvement': expected_improvement,
            'probability_practical_significance': prob_practical_significance,
            'bayes_factor': bayes_factor,
            'control_posterior_params': (control_alpha, control_beta),
            'variant_posterior_params': (variant_alpha, variant_beta)
        }
    
    def _calculate_bayes_factor(self,
                                control_clicks: int,
                                control_impressions: int,
                                variant_clicks: int,
                                variant_impressions: int) -> float:
        """Calculate Bayes Factor for model comparison."""
        # Simplified Bayes Factor calculation
        # In practice, would use more sophisticated methods
        
        control_ctr = control_clicks / control_impressions if control_impressions > 0 else 0
        variant_ctr = variant_clicks / variant_impressions if variant_impressions > 0 else 0
        
        if control_ctr == 0 or variant_ctr == 0:
            return 1.0
        
        # Approximate Bayes Factor using likelihood ratio
        likelihood_ratio = (variant_ctr / control_ctr) ** variant_clicks * \
                          ((1 - variant_ctr) / (1 - control_ctr)) ** (variant_impressions - variant_clicks)
        
        return min(likelihood_ratio, 1000.0)  # Cap at reasonable value


class FrequentistCTRTest:
    """Frequentist A/B testing for CTR experiments."""
    
    def __init__(self, alpha: float = 0.05):
        """Initialize frequentist CTR test.
        
        Args:
            alpha: Type I error rate (significance level)
        """
        self.alpha = alpha
    
    def analyze_test(self,
                     control_clicks: int,
                     control_impressions: int,
                     variant_clicks: int,
                     variant_impressions: int,
                     confidence_level: float = 0.95) -> Dict:
        """Perform frequentist analysis of CTR test."""
        
        # Calculate sample CTRs
        control_ctr = control_clicks / control_impressions if control_impressions > 0 else 0
        variant_ctr = variant_clicks / variant_impressions if variant_impressions > 0 else 0
        
        # Chi-square test for independence
        contingency_table = np.array([
            [control_clicks, control_impressions - control_clicks],
            [variant_clicks, variant_impressions - variant_clicks]
        ])
        
        chi2_stat, p_value, dof, expected = chi2_contingency(contingency_table)
        
        # Two-proportion z-test
        pooled_ctr, z_stat, z_p_value = self._two_proportion_z_test(
            control_clicks, control_impressions,
            variant_clicks, variant_impressions
        )
        
        # Confidence intervals for CTRs
        control_ci = self._proportion_confidence_interval(
            control_clicks, control_impressions, confidence_level
        )
        variant_ci = self._proportion_confidence_interval(
            variant_clicks, variant_impressions, confidence_level
        )
        
        # Effect size (relative improvement)
        relative_improvement = (variant_ctr - control_ctr) / control_ctr if control_ctr > 0 else 0
        
        # Cohen's h for effect size
        cohens_h = 2 * (np.arcsin(np.sqrt(variant_ctr)) - np.arcsin(np.sqrt(control_ctr)))
        
        return {
            'control_ctr': control_ctr,
            'variant_ctr': variant_ctr,
            'control_confidence_interval': control_ci,
            'variant_confidence_interval': variant_ci,
            'chi2_statistic': chi2_stat,
            'chi2_p_value': p_value,
            'z_statistic': z_stat,
            'z_p_value': z_p_value,
            'relative_improvement': relative_improvement,
            'cohens_h': cohens_h,
            'pooled_ctr': pooled_ctr,
            'is_significant': min(p_value, z_p_value) < self.alpha
        }
    
    def _two_proportion_z_test(self,
                               x1: int, n1: int,
                               x2: int, n2: int) -> Tuple[float, float, float]:
        """Perform two-proportion z-test."""
        p1 = x1 / n1 if n1 > 0 else 0
        p2 = x2 / n2 if n2 > 0 else 0
        
        # Pooled proportion
        pooled_p = (x1 + x2) / (n1 + n2) if (n1 + n2) > 0 else 0
        
        # Standard error
        se = np.sqrt(pooled_p * (1 - pooled_p) * (1/n1 + 1/n2))
        
        if se == 0:
            return pooled_p, 0, 1.0
        
        # Z-statistic
        z = (p2 - p1) / se
        
        # Two-tailed p-value
        p_value = 2 * (1 - norm.cdf(abs(z)))
        
        return pooled_p, z, p_value
    
    def _proportion_confidence_interval(self,
                                        x: int, n: int,
                                        confidence_level: float) -> Tuple[float, float]:
        """Calculate confidence interval for proportion using Wilson score."""
        if n == 0:
            return (0, 0)
        
        p = x / n
        z = norm.ppf(1 - (1 - confidence_level) / 2)
        
        # Wilson score interval
        denominator = 1 + z**2 / n
        center = (p + z**2 / (2 * n)) / denominator
        margin = z * np.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denominator
        
        return (max(0, center - margin), min(1, center + margin))


class SequentialCTRTest:
    """Sequential testing with early stopping rules."""
    
    def __init__(self,
                 alpha: float = 0.05,
                 beta: float = 0.20,
                 minimum_detectable_effect: float = 0.10):
        """Initialize sequential CTR test.
        
        Args:
            alpha: Type I error rate
            beta: Type II error rate (1 - power)
            minimum_detectable_effect: Minimum effect size to detect
        """
        self.alpha = alpha
        self.beta = beta
        self.minimum_detectable_effect = minimum_detectable_effect
    
    def should_stop_early(self,
                          control_clicks: int,
                          control_impressions: int,
                          variant_clicks: int,
                          variant_impressions: int,
                          current_day: int,
                          max_days: int) -> Tuple[bool, str]:
        """Check if test should stop early."""
        
        # Minimum sample size check
        if control_impressions < 100 or variant_impressions < 100:
            return False, "Insufficient sample size"
        
        # Calculate current CTRs
        control_ctr = control_clicks / control_impressions
        variant_ctr = variant_clicks / variant_impressions
        
        # Sequential probability ratio test
        likelihood_ratio = self._calculate_likelihood_ratio(
            control_clicks, control_impressions,
            variant_clicks, variant_impressions
        )
        
        # Early stopping boundaries
        upper_bound = (1 - self.beta) / self.alpha
        lower_bound = self.beta / (1 - self.alpha)
        
        if likelihood_ratio >= upper_bound:
            return True, "Strong evidence for variant superiority"
        elif likelihood_ratio <= lower_bound:
            return True, "Strong evidence for control superiority"
        
        # Futility check - unlikely to reach significance
        if current_day >= max_days * 0.7:  # After 70% of planned duration
            projected_power = self._estimate_final_power(
                control_clicks, control_impressions,
                variant_clicks, variant_impressions,
                current_day, max_days
            )
            
            if projected_power < 0.5:  # Unlikely to achieve significance
                return True, "Futility - unlikely to achieve significance"
        
        return False, "Continue test"
    
    def _calculate_likelihood_ratio(self,
                                    control_clicks: int,
                                    control_impressions: int,
                                    variant_clicks: int,
                                    variant_impressions: int) -> float:
        """Calculate likelihood ratio for sequential testing."""
        control_ctr = control_clicks / control_impressions if control_impressions > 0 else 0
        variant_ctr = variant_clicks / variant_impressions if variant_impressions > 0 else 0
        
        if control_ctr == 0 or variant_ctr == 0:
            return 1.0
        
        # Likelihood under alternative hypothesis (variant better)
        theta_alt = control_ctr * (1 + self.minimum_detectable_effect)
        
        # Likelihood ratio approximation
        if variant_ctr > control_ctr:
            lr = (variant_ctr / theta_alt) ** variant_clicks * \
                 ((1 - variant_ctr) / (1 - theta_alt)) ** (variant_impressions - variant_clicks)
        else:
            lr = (control_ctr / theta_alt) ** control_clicks * \
                 ((1 - control_ctr) / (1 - theta_alt)) ** (control_impressions - control_clicks)
        
        return min(lr, 1000.0)  # Cap at reasonable value
    
    def _estimate_final_power(self,
                              control_clicks: int,
                              control_impressions: int,
                              variant_clicks: int,
                              variant_impressions: int,
                              current_day: int,
                              max_days: int) -> float:
        """Estimate power if test continues to completion."""
        
        # Project final sample sizes
        growth_factor = max_days / current_day if current_day > 0 else 1
        projected_control_impressions = int(control_impressions * growth_factor)
        projected_variant_impressions = int(variant_impressions * growth_factor)
        
        # Current effect size
        control_ctr = control_clicks / control_impressions if control_impressions > 0 else 0
        variant_ctr = variant_clicks / variant_impressions if variant_impressions > 0 else 0
        
        # Power calculation
        return self._calculate_power(
            control_ctr, projected_control_impressions,
            variant_ctr, projected_variant_impressions
        )
    
    def _calculate_power(self,
                         control_ctr: float,
                         control_n: int,
                         variant_ctr: float,
                         variant_n: int) -> float:
        """Calculate statistical power for given parameters."""
        
        if control_ctr == 0 or variant_ctr == 0:
            return 0.0
        
        # Pooled standard error
        pooled_ctr = (control_ctr + variant_ctr) / 2
        se = np.sqrt(pooled_ctr * (1 - pooled_ctr) * (1/control_n + 1/variant_n))
        
        if se == 0:
            return 0.0
        
        # Effect size
        effect_size = abs(variant_ctr - control_ctr)
        
        # Z-score for power calculation
        z_alpha = norm.ppf(1 - self.alpha/2)
        z_beta = (effect_size - z_alpha * se) / se
        
        return norm.cdf(z_beta)


class CTRTestManager:
    """Manages CTR testing lifecycle and analysis."""
    
    def __init__(self, 
                 settings: Settings,
                 ctr_config: CTRTestingConfig):
        """Initialize CTR test manager."""
        self.settings = settings
        self.ctr_config = ctr_config
        
        # Initialize test engines
        self.bayesian_test = BayesianCTRTest(
            practical_significance_threshold=ctr_config.min_improvement_threshold
        )
        self.frequentist_test = FrequentistCTRTest(
            alpha=1 - ctr_config.statistical_significance
        )
        self.sequential_test = SequentialCTRTest(
            alpha=1 - ctr_config.statistical_significance,
            minimum_detectable_effect=ctr_config.min_improvement_threshold
        )
    
    def calculate_sample_size(self,
                              baseline_ctr: float,
                              minimum_detectable_effect: float,
                              power: float = 0.80,
                              alpha: float = 0.05) -> PowerAnalysisResult:
        """Calculate required sample size for CTR test."""
        
        # Calculate effect size (difference in CTRs)
        effect_size = baseline_ctr * minimum_detectable_effect
        variant_ctr = baseline_ctr + effect_size
        
        # Pooled CTR for sample size calculation
        pooled_ctr = (baseline_ctr + variant_ctr) / 2
        
        # Sample size calculation using formula for two proportions
        z_alpha = norm.ppf(1 - alpha/2)
        z_beta = norm.ppf(power)
        
        # Sample size per group
        n_per_group = (z_alpha * np.sqrt(2 * pooled_ctr * (1 - pooled_ctr)) + 
                       z_beta * np.sqrt(baseline_ctr * (1 - baseline_ctr) + 
                                       variant_ctr * (1 - variant_ctr))) ** 2 / effect_size ** 2
        
        n_per_group = int(np.ceil(n_per_group))
        total_sample_size = n_per_group * 2
        
        # Estimate test duration based on traffic
        # This would typically come from historical GSC data
        estimated_daily_impressions = 1000  # Placeholder
        estimated_duration_days = max(
            self.ctr_config.test_duration_days,
            total_sample_size / estimated_daily_impressions
        )
        
        return PowerAnalysisResult(
            minimum_detectable_effect=minimum_detectable_effect,
            required_sample_size=total_sample_size,
            expected_test_duration_days=int(estimated_duration_days),
            statistical_power=power,
            baseline_ctr=baseline_ctr,
            alpha=alpha,
            estimated_daily_impressions=estimated_daily_impressions,
            estimated_total_impressions=total_sample_size
        )
    
    async def analyze_ctr_test(self,
                               test: CTRTest,
                               method: TestMethod = TestMethod.BAYESIAN) -> CTRTestResults:
        """Analyze a CTR test using specified method."""
        
        logger.info(f"Analyzing CTR test {test.test_name} using {method.value} method")
        
        # Validate test has sufficient data
        if test.control_impressions < 50 or test.variant_impressions < 50:
            return self._create_insufficient_data_result(test)
        
        # Perform analysis based on method
        if method == TestMethod.BAYESIAN:
            analysis_result = self.bayesian_test.analyze_test(
                test.control_clicks, test.control_impressions,
                test.variant_clicks, test.variant_impressions,
                test.confidence_level
            )
            return self._create_bayesian_result(test, analysis_result)
            
        elif method == TestMethod.FREQUENTIST:
            analysis_result = self.frequentist_test.analyze_test(
                test.control_clicks, test.control_impressions,
                test.variant_clicks, test.variant_impressions,
                test.confidence_level
            )
            return self._create_frequentist_result(test, analysis_result)
            
        elif method == TestMethod.SEQUENTIAL:
            # Check for early stopping
            current_day = (datetime.now(timezone.utc) - test.started_at).days if test.started_at else 0
            should_stop, reason = self.sequential_test.should_stop_early(
                test.control_clicks, test.control_impressions,
                test.variant_clicks, test.variant_impressions,
                current_day, test.duration_days
            )
            
            # Use Bayesian analysis for final results
            analysis_result = self.bayesian_test.analyze_test(
                test.control_clicks, test.control_impressions,
                test.variant_clicks, test.variant_impressions,
                test.confidence_level
            )
            
            result = self._create_bayesian_result(test, analysis_result)
            result.early_stopping_triggered = should_stop
            result.stop_reason = reason
            
            return result
        
        else:
            raise ValueError(f"Unknown test method: {method}")
    
    def _create_bayesian_result(self, test: CTRTest, analysis: Dict) -> CTRTestResults:
        """Create test result from Bayesian analysis."""
        
        # Determine winner based on probability
        prob_variant_better = analysis['probability_variant_better']
        confidence_threshold = test.confidence_level
        
        if prob_variant_better >= confidence_threshold:
            winner = TestOutcome.VARIANT_WINS
        elif prob_variant_better <= (1 - confidence_threshold):
            winner = TestOutcome.CONTROL_WINS
        else:
            winner = TestOutcome.INCONCLUSIVE
        
        # Check for practical significance
        practical_significance = analysis['probability_practical_significance'] >= 0.75
        
        return CTRTestResults(
            test_id=test.id,
            test_name=test.test_name,
            status=TestStatus(test.status),
            method=TestMethod.BAYESIAN,
            control_impressions=test.control_impressions,
            control_clicks=test.control_clicks,
            control_ctr=analysis['control_ctr_mean'],
            control_confidence_interval=analysis['control_credible_interval'],
            variant_impressions=test.variant_impressions,
            variant_clicks=test.variant_clicks,
            variant_ctr=analysis['variant_ctr_mean'],
            variant_confidence_interval=analysis['variant_credible_interval'],
            p_value=1 - prob_variant_better,  # Approximate for reporting
            confidence_level=test.confidence_level,
            is_significant=prob_variant_better >= confidence_threshold or prob_variant_better <= (1 - confidence_threshold),
            effect_size=analysis['expected_improvement'],
            practical_significance=practical_significance,
            winner=winner,
            winner_probability=prob_variant_better if winner == TestOutcome.VARIANT_WINS else (1 - prob_variant_better),
            expected_improvement=analysis['expected_improvement'],
            statistical_power=0.8,  # Would calculate based on sample size
            sample_size_achieved=test.control_impressions + test.variant_impressions,
            sample_size_required=1000,  # Would calculate based on power analysis
            test_duration_days=(datetime.now(timezone.utc) - test.started_at).days if test.started_at else 0,
            early_stopping_triggered=False,
            stop_reason=None,
            recommendation=self._generate_recommendation(winner, analysis['expected_improvement'], practical_significance)
        )
    
    def _create_frequentist_result(self, test: CTRTest, analysis: Dict) -> CTRTestResults:
        """Create test result from frequentist analysis."""
        
        # Determine winner
        if analysis['is_significant']:
            if analysis['variant_ctr'] > analysis['control_ctr']:
                winner = TestOutcome.VARIANT_WINS
            else:
                winner = TestOutcome.CONTROL_WINS
        else:
            winner = TestOutcome.INCONCLUSIVE
        
        # Check practical significance
        practical_significance = abs(analysis['relative_improvement']) >= self.ctr_config.min_improvement_threshold
        
        return CTRTestResults(
            test_id=test.id,
            test_name=test.test_name,
            status=TestStatus(test.status),
            method=TestMethod.FREQUENTIST,
            control_impressions=test.control_impressions,
            control_clicks=test.control_clicks,
            control_ctr=analysis['control_ctr'],
            control_confidence_interval=analysis['control_confidence_interval'],
            variant_impressions=test.variant_impressions,
            variant_clicks=test.variant_clicks,
            variant_ctr=analysis['variant_ctr'],
            variant_confidence_interval=analysis['variant_confidence_interval'],
            p_value=analysis['z_p_value'],
            confidence_level=test.confidence_level,
            is_significant=analysis['is_significant'],
            effect_size=analysis['relative_improvement'],
            practical_significance=practical_significance,
            winner=winner,
            winner_probability=1 - analysis['z_p_value'] if analysis['is_significant'] else 0.5,
            expected_improvement=analysis['relative_improvement'],
            statistical_power=0.8,  # Would calculate based on sample size
            sample_size_achieved=test.control_impressions + test.variant_impressions,
            sample_size_required=1000,  # Would calculate based on power analysis
            test_duration_days=(datetime.now(timezone.utc) - test.started_at).days if test.started_at else 0,
            early_stopping_triggered=False,
            stop_reason=None,
            recommendation=self._generate_recommendation(winner, analysis['relative_improvement'], practical_significance)
        )
    
    def _create_insufficient_data_result(self, test: CTRTest) -> CTRTestResults:
        """Create result for test with insufficient data."""
        return CTRTestResults(
            test_id=test.id,
            test_name=test.test_name,
            status=TestStatus(test.status),
            method=TestMethod.BAYESIAN,
            control_impressions=test.control_impressions,
            control_clicks=test.control_clicks,
            control_ctr=test.control_ctr,
            control_confidence_interval=(0, 0),
            variant_impressions=test.variant_impressions,
            variant_clicks=test.variant_clicks,
            variant_ctr=test.variant_ctr,
            variant_confidence_interval=(0, 0),
            p_value=1.0,
            confidence_level=test.confidence_level,
            is_significant=False,
            effect_size=0.0,
            practical_significance=False,
            winner=TestOutcome.INSUFFICIENT_DATA,
            winner_probability=0.5,
            expected_improvement=0.0,
            statistical_power=0.0,
            sample_size_achieved=test.control_impressions + test.variant_impressions,
            sample_size_required=1000,
            test_duration_days=0,
            early_stopping_triggered=False,
            stop_reason="Insufficient data for analysis",
            recommendation="Continue test to gather more data"
        )
    
    def _generate_recommendation(self, 
                                 winner: TestOutcome,
                                 improvement: float,
                                 practical_significance: bool) -> str:
        """Generate recommendation based on test results."""
        
        if winner == TestOutcome.VARIANT_WINS and practical_significance:
            return f"Implement variant - shows {improvement:.1%} improvement with practical significance"
        elif winner == TestOutcome.VARIANT_WINS:
            return f"Variant wins but improvement ({improvement:.1%}) may not be practically significant"
        elif winner == TestOutcome.CONTROL_WINS:
            return "Keep control version - variant did not improve performance"
        elif winner == TestOutcome.INSUFFICIENT_DATA:
            return "Continue test to gather sufficient data for analysis"
        else:
            return "Results inconclusive - consider extending test duration or trying different variant"
    
    async def auto_rollback_test(self, test: CTRTest, result: CTRTestResults) -> bool:
        """Automatically rollback test if variant shows negative results."""
        
        if (result.winner == TestOutcome.CONTROL_WINS and 
            result.is_significant and
            result.practical_significance):
            
            logger.warning(f"Auto-rolling back test {test.test_name} - variant shows significant negative impact")
            
            # In a real implementation, this would:
            # 1. Update CMS to use control version
            # 2. Mark test as cancelled
            # 3. Send alert to team
            
            return True
        
        return False
    
    async def export_test_results(self, 
                                  results: CTRTestResults,
                                  output_path: str) -> bool:
        """Export test results to file."""
        try:
            import json
            
            results_data = {
                'test_id': results.test_id,
                'test_name': results.test_name,
                'status': results.status.value,
                'method': results.method.value,
                'control_metrics': {
                    'impressions': results.control_impressions,
                    'clicks': results.control_clicks,
                    'ctr': results.control_ctr,
                    'confidence_interval': results.control_confidence_interval
                },
                'variant_metrics': {
                    'impressions': results.variant_impressions,
                    'clicks': results.variant_clicks,
                    'ctr': results.variant_ctr,
                    'confidence_interval': results.variant_confidence_interval
                },
                'statistical_analysis': {
                    'p_value': results.p_value,
                    'confidence_level': results.confidence_level,
                    'is_significant': results.is_significant,
                    'effect_size': results.effect_size,
                    'practical_significance': results.practical_significance
                },
                'conclusion': {
                    'winner': results.winner.value,
                    'winner_probability': results.winner_probability,
                    'expected_improvement': results.expected_improvement,
                    'recommendation': results.recommendation
                },
                'test_metadata': {
                    'duration_days': results.test_duration_days,
                    'early_stopping_triggered': results.early_stopping_triggered,
                    'stop_reason': results.stop_reason,
                    'sample_size_achieved': results.sample_size_achieved,
                    'sample_size_required': results.sample_size_required,
                    'statistical_power': results.statistical_power
                }
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"CTR test results exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export CTR test results: {e}")
            return False


async def run_ctr_analysis(test_id: str,
                           settings: Settings,
                           ctr_config: CTRTestingConfig,
                           method: TestMethod = TestMethod.BAYESIAN) -> CTRTestResults:
    """Run CTR test analysis."""
    
    manager = CTRTestManager(settings, ctr_config)
    
    # In a real implementation, this would load test from database
    # For now, create a placeholder test
    from datetime import datetime, timezone
    
    test = CTRTest(
        id=test_id,
        test_name="Sample CTR Test",
        status="running",
        control_impressions=1000,
        control_clicks=50,
        variant_impressions=1000,
        variant_clicks=60,
        confidence_level=0.95,
        started_at=datetime.now(timezone.utc) - timedelta(days=7),
        duration_days=14
    )
    
    results = await manager.analyze_ctr_test(test, method)
    
    # Check for auto-rollback
    if await manager.auto_rollback_test(test, results):
        logger.info("Test auto-rolled back due to negative results")
    
    return results
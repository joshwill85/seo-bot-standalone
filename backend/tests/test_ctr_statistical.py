"""Unit tests for statistical CTR testing framework."""

import pytest
import numpy as np
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from src.seo_bot.ctr.statistical_tests import (
    BayesianCTRTest,
    FrequentistCTRTest,
    SequentialCTRTest,
    CTRTestManager,
    CTRTestResults,
    PowerAnalysisResult,
    TestStatus,
    TestOutcome,
    TestMethod
)
from src.seo_bot.config import CTRTestingConfig, Settings
from src.seo_bot.models import CTRTest


@pytest.fixture
def ctr_config():
    """Create test CTR configuration."""
    return CTRTestingConfig(
        statistical_significance=0.95,
        min_sample_size=200,
        max_tests_per_week=15,
        min_improvement_threshold=0.15,
        test_duration_days=14,
        position_stability_threshold=2.0
    )


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings()


@pytest.fixture
def sample_ctr_test():
    """Create sample CTR test data."""
    return CTRTest(
        id="test_123",
        test_name="Sample Title Test",
        test_type="title",
        control_title="Original Title",
        variant_title="New Improved Title",
        status="running",
        started_at=datetime.now(timezone.utc) - timedelta(days=7),
        duration_days=14,
        control_impressions=1000,
        control_clicks=50,
        control_ctr=0.05,
        control_avg_position=10.0,
        variant_impressions=1000,
        variant_clicks=60,
        variant_ctr=0.06,
        variant_avg_position=10.2,
        confidence_level=0.95
    )


class TestBayesianCTRTest:
    """Test Bayesian CTR testing functionality."""
    
    def test_bayesian_test_initialization(self):
        """Test Bayesian test initialization."""
        test = BayesianCTRTest(alpha_prior=1.0, beta_prior=1.0)
        
        assert test.alpha_prior == 1.0
        assert test.beta_prior == 1.0
        assert test.practical_significance_threshold == 0.01
    
    def test_bayesian_analysis_basic(self):
        """Test basic Bayesian analysis."""
        test = BayesianCTRTest()
        
        result = test.analyze_test(
            control_clicks=50,
            control_impressions=1000,
            variant_clicks=60,
            variant_impressions=1000,
            confidence_level=0.95
        )
        
        assert 'control_ctr_mean' in result
        assert 'variant_ctr_mean' in result
        assert 'probability_variant_better' in result
        assert 'expected_improvement' in result
        assert 'control_credible_interval' in result
        assert 'variant_credible_interval' in result
        
        # Check that CTRs are reasonable
        assert 0.04 < result['control_ctr_mean'] < 0.06
        assert 0.05 < result['variant_ctr_mean'] < 0.07
    
    def test_bayesian_analysis_clear_winner(self):
        """Test Bayesian analysis with clear winner."""
        test = BayesianCTRTest()
        
        # Clear variant winner
        result = test.analyze_test(
            control_clicks=50,
            control_impressions=1000,
            variant_clicks=100,  # Much higher
            variant_impressions=1000,
            confidence_level=0.95
        )
        
        # Variant should be clearly better
        assert result['probability_variant_better'] > 0.95
        assert result['expected_improvement'] > 0.5  # Over 50% improvement
    
    def test_bayesian_analysis_no_difference(self):
        """Test Bayesian analysis with no significant difference."""
        test = BayesianCTRTest()
        
        # Same performance
        result = test.analyze_test(
            control_clicks=50,
            control_impressions=1000,
            variant_clicks=50,
            variant_impressions=1000,
            confidence_level=0.95
        )
        
        # Should be around 50% probability
        assert 0.4 < result['probability_variant_better'] < 0.6
        assert abs(result['expected_improvement']) < 0.1
    
    def test_bayes_factor_calculation(self):
        """Test Bayes factor calculation."""
        test = BayesianCTRTest()
        
        # Test with different scenarios
        bf1 = test._calculate_bayes_factor(50, 1000, 60, 1000)
        bf2 = test._calculate_bayes_factor(50, 1000, 100, 1000)
        
        assert isinstance(bf1, float)
        assert isinstance(bf2, float)
        assert bf1 > 0
        assert bf2 > bf1  # Stronger effect should have higher BF


class TestFrequentistCTRTest:
    """Test frequentist CTR testing functionality."""
    
    def test_frequentist_test_initialization(self):
        """Test frequentist test initialization."""
        test = FrequentistCTRTest(alpha=0.05)
        
        assert test.alpha == 0.05
    
    def test_frequentist_analysis_basic(self):
        """Test basic frequentist analysis."""
        test = FrequentistCTRTest()
        
        result = test.analyze_test(
            control_clicks=50,
            control_impressions=1000,
            variant_clicks=60,
            variant_impressions=1000,
            confidence_level=0.95
        )
        
        assert 'control_ctr' in result
        assert 'variant_ctr' in result
        assert 'z_p_value' in result
        assert 'chi2_p_value' in result
        assert 'is_significant' in result
        assert 'relative_improvement' in result
        
        # Check CTR calculations
        assert result['control_ctr'] == 0.05
        assert result['variant_ctr'] == 0.06
        assert result['relative_improvement'] == 0.2  # 20% improvement
    
    def test_two_proportion_z_test(self):
        """Test two-proportion z-test."""
        test = FrequentistCTRTest()
        
        pooled_p, z_stat, p_value = test._two_proportion_z_test(50, 1000, 60, 1000)
        
        assert 0.05 < pooled_p < 0.06  # Pooled proportion
        assert isinstance(z_stat, float)
        assert 0 <= p_value <= 1
    
    def test_proportion_confidence_interval(self):
        """Test proportion confidence interval calculation."""
        test = FrequentistCTRTest()
        
        ci = test._proportion_confidence_interval(50, 1000, 0.95)
        
        assert len(ci) == 2
        assert ci[0] < ci[1]  # Lower bound < upper bound
        assert 0 <= ci[0] <= 1
        assert 0 <= ci[1] <= 1
        assert ci[0] < 0.05 < ci[1]  # True proportion should be in interval
    
    def test_significance_detection(self):
        """Test significance detection."""
        test = FrequentistCTRTest(alpha=0.05)
        
        # Clear difference - should be significant
        result_significant = test.analyze_test(
            control_clicks=50,
            control_impressions=1000,
            variant_clicks=100,
            variant_impressions=1000
        )
        
        # No difference - should not be significant
        result_not_significant = test.analyze_test(
            control_clicks=50,
            control_impressions=1000,
            variant_clicks=51,
            variant_impressions=1000
        )
        
        assert result_significant['is_significant']
        assert not result_not_significant['is_significant']


class TestSequentialCTRTest:
    """Test sequential CTR testing functionality."""
    
    def test_sequential_test_initialization(self):
        """Test sequential test initialization."""
        test = SequentialCTRTest(alpha=0.05, beta=0.20, minimum_detectable_effect=0.10)
        
        assert test.alpha == 0.05
        assert test.beta == 0.20
        assert test.minimum_detectable_effect == 0.10
    
    def test_early_stopping_insufficient_data(self):
        """Test early stopping with insufficient data."""
        test = SequentialCTRTest()
        
        should_stop, reason = test.should_stop_early(
            control_clicks=5,
            control_impressions=50,  # Too small
            variant_clicks=6,
            variant_impressions=50,
            current_day=3,
            max_days=14
        )
        
        assert not should_stop
        assert "Insufficient sample size" in reason
    
    def test_early_stopping_clear_winner(self):
        """Test early stopping with clear winner."""
        test = SequentialCTRTest(minimum_detectable_effect=0.1)
        
        # Variant is clearly much better
        should_stop, reason = test.should_stop_early(
            control_clicks=50,
            control_impressions=1000,
            variant_clicks=150,  # 3x better
            variant_impressions=1000,
            current_day=5,
            max_days=14
        )
        
        # May stop early if evidence is strong enough
        assert isinstance(should_stop, bool)
        assert isinstance(reason, str)
    
    def test_futility_stopping(self):
        """Test futility-based early stopping."""
        test = SequentialCTRTest()
        
        # Test late in the experiment with similar performance
        should_stop, reason = test.should_stop_early(
            control_clicks=50,
            control_impressions=1000,
            variant_clicks=51,  # Tiny difference
            variant_impressions=1000,
            current_day=12,  # 85% through 14-day test
            max_days=14
        )
        
        # Might stop for futility
        if should_stop:
            assert "futility" in reason.lower()
    
    def test_likelihood_ratio_calculation(self):
        """Test likelihood ratio calculation."""
        test = SequentialCTRTest(minimum_detectable_effect=0.1)
        
        lr = test._calculate_likelihood_ratio(50, 1000, 60, 1000)
        
        assert isinstance(lr, float)
        assert lr > 0
        assert lr <= 1000  # Should be capped
    
    def test_power_estimation(self):
        """Test statistical power estimation."""
        test = SequentialCTRTest()
        
        power = test._estimate_final_power(
            control_clicks=50,
            control_impressions=500,
            variant_clicks=60,
            variant_impressions=500,
            current_day=7,
            max_days=14
        )
        
        assert 0 <= power <= 1
    
    def test_calculate_power(self):
        """Test power calculation."""
        test = SequentialCTRTest()
        
        power = test._calculate_power(
            control_ctr=0.05,
            control_n=1000,
            variant_ctr=0.06,
            variant_n=1000
        )
        
        assert 0 <= power <= 1


class TestCTRTestManager:
    """Test CTR test manager functionality."""
    
    def test_manager_initialization(self, settings, ctr_config):
        """Test manager initialization."""
        manager = CTRTestManager(settings, ctr_config)
        
        assert manager.settings == settings
        assert manager.ctr_config == ctr_config
        assert isinstance(manager.bayesian_test, BayesianCTRTest)
        assert isinstance(manager.frequentist_test, FrequentistCTRTest)
        assert isinstance(manager.sequential_test, SequentialCTRTest)
    
    def test_sample_size_calculation(self, settings, ctr_config):
        """Test sample size calculation."""
        manager = CTRTestManager(settings, ctr_config)
        
        result = manager.calculate_sample_size(
            baseline_ctr=0.05,
            minimum_detectable_effect=0.15,
            power=0.80,
            alpha=0.05
        )
        
        assert isinstance(result, PowerAnalysisResult)
        assert result.minimum_detectable_effect == 0.15
        assert result.baseline_ctr == 0.05
        assert result.statistical_power == 0.80
        assert result.alpha == 0.05
        assert result.required_sample_size > 0
        assert result.expected_test_duration_days > 0
    
    @pytest.mark.asyncio
    async def test_analyze_ctr_test_bayesian(self, settings, ctr_config, sample_ctr_test):
        """Test CTR test analysis with Bayesian method."""
        manager = CTRTestManager(settings, ctr_config)
        
        results = await manager.analyze_ctr_test(sample_ctr_test, TestMethod.BAYESIAN)
        
        assert isinstance(results, CTRTestResults)
        assert results.test_id == sample_ctr_test.id
        assert results.test_name == sample_ctr_test.test_name
        assert results.method == TestMethod.BAYESIAN
        assert results.control_impressions == sample_ctr_test.control_impressions
        assert results.variant_impressions == sample_ctr_test.variant_impressions
        assert results.winner in [TestOutcome.CONTROL_WINS, TestOutcome.VARIANT_WINS, TestOutcome.INCONCLUSIVE]
    
    @pytest.mark.asyncio
    async def test_analyze_ctr_test_frequentist(self, settings, ctr_config, sample_ctr_test):
        """Test CTR test analysis with frequentist method."""
        manager = CTRTestManager(settings, ctr_config)
        
        results = await manager.analyze_ctr_test(sample_ctr_test, TestMethod.FREQUENTIST)
        
        assert isinstance(results, CTRTestResults)
        assert results.method == TestMethod.FREQUENTIST
        assert 0 <= results.p_value <= 1
        assert isinstance(results.is_significant, bool)
    
    @pytest.mark.asyncio
    async def test_analyze_ctr_test_sequential(self, settings, ctr_config, sample_ctr_test):
        """Test CTR test analysis with sequential method."""
        manager = CTRTestManager(settings, ctr_config)
        
        results = await manager.analyze_ctr_test(sample_ctr_test, TestMethod.SEQUENTIAL)
        
        assert isinstance(results, CTRTestResults)
        assert results.method == TestMethod.SEQUENTIAL
        assert isinstance(results.early_stopping_triggered, bool)
        assert isinstance(results.stop_reason, (str, type(None)))
    
    @pytest.mark.asyncio
    async def test_analyze_insufficient_data(self, settings, ctr_config):
        """Test analysis with insufficient data."""
        manager = CTRTestManager(settings, ctr_config)
        
        # Create test with insufficient data
        insufficient_test = CTRTest(
            id="test_insufficient",
            test_name="Insufficient Data Test",
            status="running",
            control_impressions=10,  # Too small
            control_clicks=1,
            variant_impressions=10,
            variant_clicks=1,
            confidence_level=0.95
        )
        
        results = await manager.analyze_ctr_test(insufficient_test, TestMethod.BAYESIAN)
        
        assert results.winner == TestOutcome.INSUFFICIENT_DATA
        assert "insufficient data" in results.stop_reason.lower()
    
    def test_create_bayesian_result(self, settings, ctr_config, sample_ctr_test):
        """Test creating Bayesian test result."""
        manager = CTRTestManager(settings, ctr_config)
        
        # Mock analysis result
        analysis = {
            'control_ctr_mean': 0.05,
            'variant_ctr_mean': 0.06,
            'control_credible_interval': (0.04, 0.06),
            'variant_credible_interval': (0.05, 0.07),
            'probability_variant_better': 0.85,
            'expected_improvement': 0.2,
            'probability_practical_significance': 0.75
        }
        
        result = manager._create_bayesian_result(sample_ctr_test, analysis)
        
        assert isinstance(result, CTRTestResults)
        assert result.control_ctr == analysis['control_ctr_mean']
        assert result.variant_ctr == analysis['variant_ctr_mean']
        assert result.winner_probability == 0.85
    
    def test_create_frequentist_result(self, settings, ctr_config, sample_ctr_test):
        """Test creating frequentist test result."""
        manager = CTRTestManager(settings, ctr_config)
        
        # Mock analysis result
        analysis = {
            'control_ctr': 0.05,
            'variant_ctr': 0.06,
            'control_confidence_interval': (0.04, 0.06),
            'variant_confidence_interval': (0.05, 0.07),
            'z_p_value': 0.03,
            'is_significant': True,
            'relative_improvement': 0.2
        }
        
        result = manager._create_frequentist_result(sample_ctr_test, analysis)
        
        assert isinstance(result, CTRTestResults)
        assert result.method == TestMethod.FREQUENTIST
        assert result.p_value == 0.03
        assert result.is_significant
        assert result.winner == TestOutcome.VARIANT_WINS
    
    def test_generate_recommendation(self, settings, ctr_config):
        """Test recommendation generation."""
        manager = CTRTestManager(settings, ctr_config)
        
        # Test different scenarios
        rec1 = manager._generate_recommendation(TestOutcome.VARIANT_WINS, 0.20, True)
        rec2 = manager._generate_recommendation(TestOutcome.VARIANT_WINS, 0.05, False)
        rec3 = manager._generate_recommendation(TestOutcome.CONTROL_WINS, -0.10, True)
        rec4 = manager._generate_recommendation(TestOutcome.INCONCLUSIVE, 0.05, False)
        
        assert "implement variant" in rec1.lower()
        assert "wins but" in rec2.lower()
        assert "keep control" in rec3.lower()
        assert "inconclusive" in rec4.lower()
    
    @pytest.mark.asyncio
    async def test_auto_rollback_test(self, settings, ctr_config, sample_ctr_test):
        """Test automatic test rollback."""
        manager = CTRTestManager(settings, ctr_config)
        
        # Create result that should trigger rollback
        bad_result = CTRTestResults(
            test_id=sample_ctr_test.id,
            test_name=sample_ctr_test.test_name,
            status=TestStatus.RUNNING,
            method=TestMethod.BAYESIAN,
            control_impressions=1000,
            control_clicks=100,
            control_ctr=0.10,
            control_confidence_interval=(0.08, 0.12),
            variant_impressions=1000,
            variant_clicks=50,  # Much worse
            variant_ctr=0.05,
            variant_confidence_interval=(0.04, 0.06),
            p_value=0.01,
            confidence_level=0.95,
            is_significant=True,
            effect_size=-0.50,  # -50% - very bad
            practical_significance=True,
            winner=TestOutcome.CONTROL_WINS,
            winner_probability=0.99,
            expected_improvement=-0.50,
            statistical_power=0.99,
            sample_size_achieved=2000,
            sample_size_required=1000,
            test_duration_days=7,
            early_stopping_triggered=False,
            stop_reason=None,
            recommendation="Keep control"
        )
        
        should_rollback = await manager.auto_rollback_test(sample_ctr_test, bad_result)
        
        assert should_rollback
    
    @pytest.mark.asyncio
    async def test_export_test_results(self, settings, ctr_config, sample_ctr_test, tmp_path):
        """Test exporting test results."""
        manager = CTRTestManager(settings, ctr_config)
        
        # Create sample results
        results = await manager.analyze_ctr_test(sample_ctr_test, TestMethod.BAYESIAN)
        
        output_path = tmp_path / "test_results.json"
        
        success = await manager.export_test_results(results, str(output_path))
        
        assert success
        assert output_path.exists()
        
        # Verify content
        import json
        with open(output_path, 'r') as f:
            exported_data = json.load(f)
        
        assert exported_data['test_id'] == results.test_id
        assert exported_data['method'] == results.method.value
        assert 'control_metrics' in exported_data
        assert 'variant_metrics' in exported_data
        assert 'conclusion' in exported_data


if __name__ == "__main__":
    pytest.main([__file__])
#!/usr/bin/env python3
"""
Production Validator for NFL Parlay Strategist Agent

Validates that all required components and configurations are available
for production deployment of JIRA-NFL-009.
"""

import os
import logging
import sys
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    CRITICAL = "CRITICAL"    # Must pass for production
    WARNING = "WARNING"      # Should pass but not blocking
    INFO = "INFO"           # Nice to have


@dataclass
class ValidationResult:
    """Result of a production validation check."""
    name: str
    level: ValidationLevel
    passed: bool
    message: str
    details: Dict[str, Any] = None


class ProductionValidator:
    """
    Validates production readiness for NFL Parlay Strategist Agent.
    
    Checks environment variables, dependencies, component availability,
    and configuration completeness.
    """
    
    def __init__(self):
        self.results: List[ValidationResult] = []
    
    def validate_all(self) -> Tuple[bool, List[ValidationResult]]:
        """
        Run all production validation checks.
        
        Returns:
            Tuple of (is_production_ready, list_of_results)
        """
        logger.info("Starting production validation for NFL Parlay Strategist Agent")
        
        # Environment validation
        self._validate_environment_variables()
        self._validate_python_environment()
        
        # Dependency validation
        self._validate_core_dependencies()
        self._validate_optional_dependencies()
        
        # Component validation
        self._validate_nfl_components()
        self._validate_api_connectivity()
        
        # Configuration validation
        self._validate_configuration_files()
        self._validate_database_connectivity()
        
        # Security validation
        self._validate_security_settings()
        
        # Determine overall production readiness
        critical_failures = [r for r in self.results if r.level == ValidationLevel.CRITICAL and not r.passed]
        is_production_ready = len(critical_failures) == 0
        
        return is_production_ready, self.results
    
    def _validate_environment_variables(self):
        """Validate required environment variables."""
        required_vars = {
            "THE_ODDS_API_KEY": "Required for odds data fetching",
            "api-football": "Required for NFL data (API Football)"
        }
        
        optional_vars = {
            "ENVIRONMENT": "Should be 'production' for prod deployment",
            "REDIS_URL": "Required for production caching",
            "SENTRY_DSN": "Recommended for error tracking"
        }
        
        # Check required variables
        for var, description in required_vars.items():
            value = os.getenv(var)
            if value:
                self.results.append(ValidationResult(
                    name=f"Environment Variable: {var}",
                    level=ValidationLevel.CRITICAL,
                    passed=True,
                    message=f"✅ {var} is configured",
                    details={"length": len(value), "description": description}
                ))
            else:
                self.results.append(ValidationResult(
                    name=f"Environment Variable: {var}",
                    level=ValidationLevel.CRITICAL,
                    passed=False,
                    message=f"❌ {var} is missing - {description}",
                    details={"description": description}
                ))
        
        # Check optional variables
        for var, description in optional_vars.items():
            value = os.getenv(var)
            if value:
                self.results.append(ValidationResult(
                    name=f"Optional Environment Variable: {var}",
                    level=ValidationLevel.WARNING,
                    passed=True,
                    message=f"✅ {var} is configured",
                    details={"description": description}
                ))
            else:
                self.results.append(ValidationResult(
                    name=f"Optional Environment Variable: {var}",
                    level=ValidationLevel.WARNING,
                    passed=False,
                    message=f"⚠️ {var} is missing - {description}",
                    details={"description": description}
                ))
    
    def _validate_python_environment(self):
        """Validate Python version and environment."""
        # Check Python version
        if sys.version_info >= (3, 8):
            self.results.append(ValidationResult(
                name="Python Version",
                level=ValidationLevel.CRITICAL,
                passed=True,
                message=f"✅ Python {sys.version_info.major}.{sys.version_info.minor} is supported",
                details={"version": sys.version}
            ))
        else:
            self.results.append(ValidationResult(
                name="Python Version",
                level=ValidationLevel.CRITICAL,
                passed=False,
                message=f"❌ Python {sys.version_info.major}.{sys.version_info.minor} is too old (need 3.8+)",
                details={"version": sys.version}
            ))
    
    def _validate_core_dependencies(self):
        """Validate core Python dependencies."""
        core_deps = [
            "fastapi", "uvicorn", "pydantic", "requests", 
            "pandas", "python-dotenv", "aiohttp"
        ]
        
        for dep in core_deps:
            try:
                __import__(dep)
                self.results.append(ValidationResult(
                    name=f"Core Dependency: {dep}",
                    level=ValidationLevel.CRITICAL,
                    passed=True,
                    message=f"✅ {dep} is available"
                ))
            except ImportError:
                self.results.append(ValidationResult(
                    name=f"Core Dependency: {dep}",
                    level=ValidationLevel.CRITICAL,
                    passed=False,
                    message=f"❌ {dep} is missing - install with pip"
                ))
    
    def _validate_optional_dependencies(self):
        """Validate optional dependencies for enhanced functionality."""
        optional_deps = {
            "redis": "Production caching",
            "apscheduler": "NFL game scheduling",
            "celery": "Background task processing",
            "structlog": "Enhanced logging",
            "prometheus_client": "Metrics collection",
            "sentry_sdk": "Error tracking"
        }
        
        for dep, description in optional_deps.items():
            try:
                __import__(dep)
                self.results.append(ValidationResult(
                    name=f"Optional Dependency: {dep}",
                    level=ValidationLevel.WARNING,
                    passed=True,
                    message=f"✅ {dep} is available ({description})"
                ))
            except ImportError:
                self.results.append(ValidationResult(
                    name=f"Optional Dependency: {dep}",
                    level=ValidationLevel.WARNING,
                    passed=False,
                    message=f"⚠️ {dep} is missing - {description}"
                ))
    
    def _validate_nfl_components(self):
        """Validate NFL-specific components."""
        try:
            # Test SportFactory
            sys.path.append('.')
            from tools.sport_factory import SportFactory
            
            nfl_toolkit = SportFactory.create_complete_toolkit("nfl")
            
            for component_name, component in nfl_toolkit.items():
                if "Mock" in type(component).__name__:
                    self.results.append(ValidationResult(
                        name=f"NFL Component: {component_name}",
                        level=ValidationLevel.CRITICAL,
                        passed=False,
                        message=f"❌ {component_name} is using mock implementation",
                        details={"component_type": type(component).__name__}
                    ))
                else:
                    self.results.append(ValidationResult(
                        name=f"NFL Component: {component_name}",
                        level=ValidationLevel.CRITICAL,
                        passed=True,
                        message=f"✅ {component_name} is properly implemented",
                        details={"component_type": type(component).__name__}
                    ))
                    
        except Exception as e:
            self.results.append(ValidationResult(
                name="NFL Components",
                level=ValidationLevel.CRITICAL,
                passed=False,
                message=f"❌ Failed to validate NFL components: {e}"
            ))
    
    def _validate_api_connectivity(self):
        """Validate API connectivity (without making actual calls)."""
        api_endpoints = {
            "THE_ODDS_API_KEY": "https://api.the-odds-api.com/v4/sports/",
            "api-football": "https://api-football-v1.p.rapidapi.com/"
        }
        
        for env_var, endpoint in api_endpoints.items():
            api_key = os.getenv(env_var)
            if api_key:
                # Check key format (basic validation)
                if len(api_key) > 10:  # Basic length check
                    self.results.append(ValidationResult(
                        name=f"API Key Format: {env_var}",
                        level=ValidationLevel.WARNING,
                        passed=True,
                        message=f"✅ {env_var} has valid format",
                        details={"endpoint": endpoint, "key_length": len(api_key)}
                    ))
                else:
                    self.results.append(ValidationResult(
                        name=f"API Key Format: {env_var}",
                        level=ValidationLevel.WARNING,
                        passed=False,
                        message=f"⚠️ {env_var} appears to have invalid format",
                        details={"endpoint": endpoint, "key_length": len(api_key)}
                    ))
    
    def _validate_configuration_files(self):
        """Validate required configuration files."""
        config_files = {
            "config/nfl_markets.json": ValidationLevel.CRITICAL,
            "config/nba_markets.json": ValidationLevel.WARNING,
            "requirements_production.txt": ValidationLevel.WARNING
        }
        
        for file_path, level in config_files.items():
            if os.path.exists(file_path):
                self.results.append(ValidationResult(
                    name=f"Config File: {file_path}",
                    level=level,
                    passed=True,
                    message=f"✅ {file_path} exists"
                ))
            else:
                self.results.append(ValidationResult(
                    name=f"Config File: {file_path}",
                    level=level,
                    passed=False,
                    message=f"{'❌' if level == ValidationLevel.CRITICAL else '⚠️'} {file_path} is missing"
                ))
    
    def _validate_database_connectivity(self):
        """Validate database connectivity."""
        # Check Redis availability
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                import redis
                # Don't actually connect in validation - just check availability
                self.results.append(ValidationResult(
                    name="Redis Configuration",
                    level=ValidationLevel.WARNING,
                    passed=True,
                    message="✅ Redis URL configured and library available"
                ))
            except ImportError:
                self.results.append(ValidationResult(
                    name="Redis Configuration",
                    level=ValidationLevel.WARNING,
                    passed=False,
                    message="⚠️ Redis URL configured but library not available"
                ))
        else:
            self.results.append(ValidationResult(
                name="Redis Configuration",
                level=ValidationLevel.WARNING,
                passed=False,
                message="⚠️ Redis URL not configured - caching will be disabled"
            ))
    
    def _validate_security_settings(self):
        """Validate security-related settings."""
        # Check for debug mode
        debug_indicators = [
            os.getenv("DEBUG") == "True",
            os.getenv("FLASK_DEBUG") == "1",
            os.getenv("DJANGO_DEBUG") == "True"
        ]
        
        if any(debug_indicators):
            self.results.append(ValidationResult(
                name="Debug Mode",
                level=ValidationLevel.CRITICAL,
                passed=False,
                message="❌ Debug mode is enabled - disable for production"
            ))
        else:
            self.results.append(ValidationResult(
                name="Debug Mode",
                level=ValidationLevel.CRITICAL,
                passed=True,
                message="✅ Debug mode is disabled"
            ))
        
        # Check for production environment flag
        if os.getenv("ENVIRONMENT") == "production":
            self.results.append(ValidationResult(
                name="Production Environment",
                level=ValidationLevel.INFO,
                passed=True,
                message="✅ ENVIRONMENT=production is set"
            ))
        else:
            self.results.append(ValidationResult(
                name="Production Environment",
                level=ValidationLevel.INFO,
                passed=False,
                message="ℹ️ ENVIRONMENT=production is not set"
            ))
    
    def print_summary(self):
        """Print a formatted summary of validation results."""
        critical_results = [r for r in self.results if r.level == ValidationLevel.CRITICAL]
        warning_results = [r for r in self.results if r.level == ValidationLevel.WARNING]
        info_results = [r for r in self.results if r.level == ValidationLevel.INFO]
        
        critical_passed = sum(1 for r in critical_results if r.passed)
        warning_passed = sum(1 for r in warning_results if r.passed)
        
        print("🔍 NFL Parlay Strategist Agent - Production Validation")
        print("=" * 60)
        
        print(f"\n📊 Summary:")
        print(f"   Critical: {critical_passed}/{len(critical_results)} passed")
        print(f"   Warning:  {warning_passed}/{len(warning_results)} passed")
        print(f"   Info:     {len(info_results)} checks")
        
        # Show failed critical checks
        failed_critical = [r for r in critical_results if not r.passed]
        if failed_critical:
            print(f"\n❌ Critical Issues (MUST FIX):")
            for result in failed_critical:
                print(f"   • {result.message}")
        
        # Show failed warnings
        failed_warnings = [r for r in warning_results if not r.passed]
        if failed_warnings:
            print(f"\n⚠️ Warnings (SHOULD FIX):")
            for result in failed_warnings[:5]:  # Show first 5
                print(f"   • {result.message}")
            if len(failed_warnings) > 5:
                print(f"   ... and {len(failed_warnings) - 5} more warnings")
        
        # Overall status
        is_ready = len(failed_critical) == 0
        print(f"\n🎯 Production Readiness: {'✅ READY' if is_ready else '❌ NOT READY'}")
        
        return is_ready


def main():
    """Main function for running production validation."""
    validator = ProductionValidator()
    is_ready, results = validator.validate_all()
    
    # Print detailed summary
    validator.print_summary()
    
    # Exit with appropriate code
    exit_code = 0 if is_ready else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

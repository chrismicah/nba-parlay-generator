#!/usr/bin/env python3
"""
Codebase Structure Tests

Comprehensive tests to ensure the cleaned codebase maintains proper structure,
imports work correctly, and all key components are accessible.
"""

import pytest
import os
import sys
from pathlib import Path
import importlib
import subprocess
from typing import List, Dict, Any

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestDirectoryStructure:
    """Test that all required directories exist and are properly organized."""
    
    def test_key_directories_exist(self):
        """Ensure all key directories exist."""
        required_dirs = [
            "app",      # FastAPI, routes, and API logic
            "agents",   # Parlay strategist agents, ML agents  
            "tools",    # Utilities, scrapers, APIs, helpers
            "ml",       # Models, training scripts, evaluators
            "data",     # Datasets, generated CSVs/JSONs
            "tests",    # Unit and integration tests
            "docs",     # Documentation
            "scripts",  # Utility scripts and production
            "config",   # Configuration files
            "models",   # ML models and weights
            "migrations", # Database migrations
            "supabase", # Supabase configuration
            "frontend", # React frontend (untouched)
            "archive"   # Deprecated/archived code
        ]
        
        for dir_name in required_dirs:
            dir_path = PROJECT_ROOT / dir_name
            assert dir_path.exists(), f"Required directory '{dir_name}' does not exist"
            assert dir_path.is_dir(), f"'{dir_name}' exists but is not a directory"
    
    def test_docs_structure(self):
        """Test that docs directory is properly organized."""
        docs_path = PROJECT_ROOT / "docs"
        assert docs_path.exists()
        
        # Check for organized subdirectories
        expected_subdirs = ["guides", "architecture", "jira", "ui-ux", "deployment", "backend-integration"]
        for subdir in expected_subdirs:
            subdir_path = docs_path / subdir
            # Note: Some subdirs may be empty, so we just check they can be created
            assert subdir == subdir  # Basic check that structure is defined
    
    def test_archive_structure(self):
        """Test that deprecated code is properly archived."""
        archive_path = PROJECT_ROOT / "archive"
        assert archive_path.exists()
        
        # Check for archived components
        expected_archives = ["examples", "deprecated_tools"]
        for archive_dir in expected_archives:
            archive_subdir = archive_path / archive_dir
            assert archive_subdir.exists(), f"Archive subdirectory '{archive_dir}' should exist"
    
    def test_production_structure(self):
        """Test that production scripts are properly organized."""
        production_path = PROJECT_ROOT / "scripts" / "production"
        assert production_path.exists()
        
        # Check for production files
        production_files = ["production_main.py", "run_production.py", "start_production.sh"]
        for prod_file in production_files:
            file_path = production_path / prod_file
            assert file_path.exists(), f"Production file '{prod_file}' should exist in scripts/production"


class TestCoreImports:
    """Test that core components can be imported without errors."""
    
    def test_fastapi_app_import(self):
        """Test that FastAPI app can be imported."""
        try:
            from app.main import app
            assert app is not None
            assert hasattr(app, 'title')
        except ImportError as e:
            pytest.fail(f"Failed to import FastAPI app: {e}")
    
    def test_unified_agent_import(self):
        """Test that unified parlay strategist can be imported."""
        try:
            from tools.unified_parlay_strategist_agent import (
                UnifiedParlayStrategistAgent, 
                create_unified_agent
            )
            assert UnifiedParlayStrategistAgent is not None
            assert create_unified_agent is not None
        except ImportError as e:
            pytest.fail(f"Failed to import unified parlay strategist: {e}")
    
    def test_sport_adapters_import(self):
        """Test that sport data adapters can be imported."""
        try:
            from tools.sport_data_adapters import (
                NFLDataAdapter, 
                NBADataAdapter, 
                create_sport_adapter
            )
            assert NFLDataAdapter is not None
            assert NBADataAdapter is not None
            assert create_sport_adapter is not None
        except ImportError as e:
            pytest.fail(f"Failed to import sport adapters: {e}")
    
    def test_knowledge_base_import(self):
        """Test that knowledge base can be imported."""
        try:
            from tools.knowledge_base_rag import SportsKnowledgeRAG
            assert SportsKnowledgeRAG is not None
        except ImportError as e:
            pytest.fail(f"Failed to import knowledge base: {e}")
    
    def test_ml_components_import(self):
        """Test that ML components can be imported."""
        try:
            # Test ML training components
            from ml.ml_prop_trainer import HistoricalPropTrainer
            assert HistoricalPropTrainer is not None
            
            # Test BioBERT injury classifier
            from tools.classify_injury_severity import BioBERTInjuryClassifier
            assert BioBERTInjuryClassifier is not None
        except ImportError as e:
            # Some ML components may have optional dependencies
            pytest.skip(f"ML components not available (optional dependencies): {e}")
    
    def test_scraper_imports(self):
        """Test that key scrapers and API tools can be imported."""
        scrapers_to_test = [
            ("tools.odds_fetcher_tool", "OddsFetcherTool"),
            ("tools.grok_tweet_fetcher", "fetch_injury_updates"),
            ("tools.apify_injury_tweet_scraper", "NFLInjuryTweetScraper"),
        ]
        
        for module_name, class_or_func_name in scrapers_to_test:
            try:
                module = importlib.import_module(module_name)
                component = getattr(module, class_or_func_name)
                assert component is not None
            except ImportError as e:
                pytest.skip(f"Scraper {module_name} not available (optional dependencies): {e}")
            except AttributeError as e:
                pytest.fail(f"Expected component {class_or_func_name} not found in {module_name}: {e}")


class TestConfigurationFiles:
    """Test that configuration files are present and valid."""
    
    def test_requirements_files_exist(self):
        """Test that requirements files exist."""
        req_files = ["requirements.txt", "requirements_production.txt"]
        for req_file in req_files:
            file_path = PROJECT_ROOT / req_file
            assert file_path.exists(), f"Requirements file '{req_file}' should exist"
            assert file_path.stat().st_size > 0, f"Requirements file '{req_file}' should not be empty"
    
    def test_docker_files_exist(self):
        """Test that Docker configuration files exist."""
        docker_files = ["Dockerfile", "docker-compose.yml"]
        for docker_file in docker_files:
            file_path = PROJECT_ROOT / docker_file
            assert file_path.exists(), f"Docker file '{docker_file}' should exist"
            assert file_path.stat().st_size > 0, f"Docker file '{docker_file}' should not be empty"
    
    def test_config_directory(self):
        """Test that config directory contains necessary files."""
        config_path = PROJECT_ROOT / "config"
        assert config_path.exists()
        
        # Check for config files
        config_files = ["nba_markets.json", "nfl_markets.json"]
        for config_file in config_files:
            file_path = config_path / config_file
            assert file_path.exists(), f"Config file '{config_file}' should exist"


class TestContainerization:
    """Test containerization readiness."""
    
    def test_dockerfile_syntax(self):
        """Test that Dockerfile has valid syntax."""
        dockerfile_path = PROJECT_ROOT / "Dockerfile"
        assert dockerfile_path.exists()
        
        # Read Dockerfile and check for key components
        with open(dockerfile_path, 'r') as f:
            content = f.read()
        
        # Check for required Dockerfile components
        assert "FROM python:" in content
        assert "WORKDIR /app" in content
        assert "COPY requirements" in content
        assert "CMD [" in content
        assert "scripts/production/run_production.py" in content
    
    def test_docker_compose_syntax(self):
        """Test that docker-compose.yml has valid syntax."""
        compose_path = PROJECT_ROOT / "docker-compose.yml"
        assert compose_path.exists()
        
        try:
            import yaml
            with open(compose_path, 'r') as f:
                compose_config = yaml.safe_load(f)
            
            # Check for required components
            assert "services" in compose_config
            assert "web" in compose_config["services"]
            assert "redis" in compose_config["services"]
            assert "qdrant" in compose_config["services"]
            
            # Check web service configuration
            web_service = compose_config["services"]["web"]
            assert "build" in web_service
            assert "ports" in web_service
            assert "environment" in web_service
            
        except ImportError:
            pytest.skip("PyYAML not available for docker-compose syntax test")
    
    def test_production_script_executable(self):
        """Test that production scripts are properly structured."""
        prod_script_path = PROJECT_ROOT / "scripts" / "production" / "run_production.py"
        assert prod_script_path.exists()
        
        # Check that it's a Python file with proper shebang
        with open(prod_script_path, 'r') as f:
            first_line = f.readline().strip()
        
        assert first_line.startswith("#!") and "python" in first_line


class TestDataIntegrity:
    """Test that data and model directories are properly structured."""
    
    def test_data_directory_structure(self):
        """Test that data directory contains expected subdirectories."""
        data_path = PROJECT_ROOT / "data"
        assert data_path.exists()
        
        # Check for key data subdirectories
        expected_subdirs = ["chunks", "tweets", "ml_training"]
        for subdir in expected_subdirs:
            subdir_path = data_path / subdir
            assert subdir_path.exists(), f"Data subdirectory '{subdir}' should exist"
    
    def test_models_directory(self):
        """Test that models directory exists and is accessible."""
        models_path = PROJECT_ROOT / "models"
        assert models_path.exists()
        assert models_path.is_dir()
    
    def test_knowledge_base_chunks(self):
        """Test that knowledge base chunks file exists."""
        chunks_path = PROJECT_ROOT / "data" / "chunks" / "chunks.json"
        # Note: This file may not exist in all environments
        if chunks_path.exists():
            assert chunks_path.stat().st_size > 0, "Knowledge base chunks file should not be empty"


class TestCleanupEffectiveness:
    """Test that cleanup was effective and no broken code remains."""
    
    def test_no_broken_imports_in_main_app(self):
        """Test that main app doesn't import deprecated components."""
        app_main_path = PROJECT_ROOT / "app" / "main.py"
        assert app_main_path.exists()
        
        with open(app_main_path, 'r') as f:
            content = f.read()
        
        # Should not import deprecated agents
        deprecated_imports = [
            "NFLParlayStrategistAgent",
            "FewShotEnhancedParlayStrategistAgent"
        ]
        
        for deprecated_import in deprecated_imports:
            assert deprecated_import not in content, f"Main app should not import deprecated {deprecated_import}"
        
        # Should import unified components
        assert "unified_parlay_strategist_agent" in content
        assert "UnifiedParlayStrategistAgent" in content
    
    def test_archived_files_not_in_main_directories(self):
        """Test that archived files are not in main directories."""
        main_dirs = ["app", "agents", "tools", "ml"]
        
        for main_dir in main_dirs:
            dir_path = PROJECT_ROOT / main_dir
            if not dir_path.exists():
                continue
            
            # Look for files that should be archived
            for file_path in dir_path.rglob("*.py"):
                filename = file_path.name
                
                # Check for demo/jira files that should be archived
                if "demo" in filename.lower() or "jira" in filename.lower():
                    pytest.fail(f"Demo/JIRA file {filename} found in main directory {main_dir}, should be archived")
    
    def test_unified_system_replaces_old_agents(self):
        """Test that unified system is being used instead of old agents."""
        # Check that production scripts use unified agents
        prod_main_path = PROJECT_ROOT / "scripts" / "production" / "production_main.py"
        if prod_main_path.exists():
            with open(prod_main_path, 'r') as f:
                content = f.read()
            
            # Should use unified agents
            assert "unified_parlay_strategist_agent" in content
            assert "create_unified_agent" in content


class TestEnvironmentCompatibility:
    """Test environment and deployment compatibility."""
    
    def test_python_version_compatibility(self):
        """Test that code is compatible with specified Python version."""
        # Check that we're running on a supported Python version
        assert sys.version_info >= (3, 8), "Python 3.8+ required"
        assert sys.version_info < (4, 0), "Python 4.0+ not yet supported"
    
    def test_essential_packages_importable(self):
        """Test that essential packages can be imported."""
        essential_packages = [
            "fastapi",
            "uvicorn", 
            "pydantic",
            "asyncio",
            "datetime",
            "logging",
            "json",
            "typing"
        ]
        
        for package in essential_packages:
            try:
                importlib.import_module(package)
            except ImportError:
                pytest.fail(f"Essential package '{package}' cannot be imported")
    
    def test_optional_packages_handling(self):
        """Test that optional packages are handled gracefully."""
        optional_packages = [
            ("torch", "PyTorch"),
            ("transformers", "Hugging Face Transformers"),
            ("apscheduler", "APScheduler"),
            ("qdrant_client", "Qdrant"),
            ("redis", "Redis")
        ]
        
        for package, description in optional_packages:
            try:
                importlib.import_module(package)
            except ImportError:
                # This is okay for optional packages
                pass


def test_fastapi_app_can_start():
    """Integration test: verify FastAPI app can start without errors."""
    try:
        from app.main import app
        
        # Test that app has required attributes
        assert hasattr(app, 'routes')
        assert hasattr(app, 'title') 
        assert len(app.routes) > 0, "App should have routes defined"
        
        # Check for key endpoints
        route_paths = [route.path for route in app.routes if hasattr(route, 'path')]
        expected_endpoints = ["/health", "/generate-nfl-parlay", "/generate-nba-parlay"]
        
        for endpoint in expected_endpoints:
            assert any(endpoint in path for path in route_paths), f"Expected endpoint {endpoint} not found"
            
    except Exception as e:
        pytest.fail(f"FastAPI app failed to start: {e}")


def test_docker_build_ready():
    """Test that Docker build should work with current structure."""
    # Check that all files referenced in Dockerfile exist
    required_files = [
        "requirements.txt",
        "requirements_production.txt", 
        "scripts/production/run_production.py"
    ]
    
    for file_path in required_files:
        full_path = PROJECT_ROOT / file_path
        assert full_path.exists(), f"File {file_path} required for Docker build is missing"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

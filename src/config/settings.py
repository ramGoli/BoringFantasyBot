"""
Configuration management for the Fantasy Football Auto-Lineup Bot.
Handles loading, validation, and access to application settings.
"""

import os
import yaml
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class YahooAPIConfig:
    """Yahoo API configuration settings."""
    client_id: str
    client_secret: str
    redirect_uri: str


@dataclass
class ExternalAPIConfig:
    """External API configuration settings."""
    weather_api_key: Optional[str] = None
    fantasy_pros_api_key: Optional[str] = None
    numberfire_api_key: Optional[str] = None
    rotowire_api_key: Optional[str] = None
    odds_api_key: Optional[str] = None


@dataclass
class LoggingConfig:
    """Logging configuration settings."""
    level: str = "INFO"
    file: str = "fantasy_bot.log"
    max_size_mb: int = 10
    backup_count: int = 5


@dataclass
class CacheConfig:
    """Cache configuration settings."""
    enabled: bool = True
    ttl_hours: int = 24
    max_size_mb: int = 100


@dataclass
class BotConfig:
    """Main bot configuration settings."""
    risk_tolerance: str
    auto_submit: bool
    notification_email: str
    dry_run_mode: bool
    league_id: str
    team_id: str
    # Decision weights are optional - defaults provided if not specified
    # The bot primarily uses betting data (odds API) for optimization
    injury_weight: float
    matchup_weight: float
    recent_performance_weight: float
    projection_weight: float
    weather_weight: float
    run_daily_at: str
    backup_before_games: bool
    waiver_wire_management: bool
    check_injuries_hourly: bool
    yahoo_api: YahooAPIConfig
    external_apis: ExternalAPIConfig
    logging: LoggingConfig
    cache: CacheConfig


class ConfigManager:
    """Manages application configuration loading and validation."""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._config: Optional[BotConfig] = None
    
    def load_config(self) -> BotConfig:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as file:
            config_data = yaml.safe_load(file)
        
        # Decision weights are optional - bot primarily uses betting data (odds API)
        # If weights are provided, they can be used for additional scoring adjustments
        # Default to 0.0 if not specified (betting data is the primary method)
        
        # Create nested config objects
        yahoo_api_config = YahooAPIConfig(
            client_id=config_data['yahoo_api']['client_id'],
            client_secret=config_data['yahoo_api']['client_secret'],
            redirect_uri=config_data['yahoo_api']['redirect_uri']
        )
        
        external_api_config = ExternalAPIConfig(
            weather_api_key=config_data['external_apis'].get('weather_api_key'),
            fantasy_pros_api_key=config_data['external_apis'].get('fantasy_pros_api_key'),
            numberfire_api_key=config_data['external_apis'].get('numberfire_api_key'),
            rotowire_api_key=config_data['external_apis'].get('rotowire_api_key'),
            odds_api_key=config_data['external_apis'].get('odds_api_key')
        )
        
        logging_config = LoggingConfig(
            level=config_data['logging']['level'],
            file=config_data['logging']['file'],
            max_size_mb=config_data['logging']['max_size_mb'],
            backup_count=config_data['logging']['backup_count']
        )
        
        cache_config = CacheConfig(
            enabled=config_data['cache']['enabled'],
            ttl_hours=config_data['cache']['ttl_hours'],
            max_size_mb=config_data['cache']['max_size_mb']
        )
        
        self._config = BotConfig(
            risk_tolerance=config_data['risk_tolerance'],
            auto_submit=config_data['auto_submit'],
            notification_email=config_data['notification_email'],
            dry_run_mode=config_data['dry_run_mode'],
            league_id=config_data['league_id'],
            team_id=config_data['team_id'],
            # Decision weights are optional - default to 0.0 (betting data is primary method)
            injury_weight=config_data.get('injury_weight', 0.0),
            matchup_weight=config_data.get('matchup_weight', 0.0),
            recent_performance_weight=config_data.get('recent_performance_weight', 0.0),
            projection_weight=config_data.get('projection_weight', 0.0),
            weather_weight=config_data.get('weather_weight', 0.0),
            run_daily_at=config_data.get('run_daily_at', '08:00'),
            backup_before_games=config_data.get('backup_before_games', True),
            waiver_wire_management=config_data.get('waiver_wire_management', True),
            check_injuries_hourly=config_data.get('check_injuries_hourly', True),
            yahoo_api=yahoo_api_config,
            external_apis=external_api_config,
            logging=logging_config,
            cache=cache_config
        )
        
        return self._config
    
    def get_config(self) -> BotConfig:
        """Get the current configuration, loading if necessary."""
        if self._config is None:
            self._config = self.load_config()
        return self._config
    
    def reload_config(self) -> BotConfig:
        """Reload configuration from file."""
        self._config = None
        return self.get_config()


# Global config instance
config_manager = ConfigManager()


def get_config() -> BotConfig:
    """Get the current application configuration."""
    return config_manager.get_config()

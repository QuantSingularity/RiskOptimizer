import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class DatabaseConfig:
    """Database configuration settings."""

    host: str
    port: int
    name: str
    user: str
    password: str
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600

    @property
    def url(self) -> str:
        """Get database URL for SQLAlchemy."""
        # Use SQLite for local development if DB_USE_SQLITE is set
        if os.getenv("DB_USE_SQLITE", "true").lower() == "true":
            db_path = os.getenv("SQLITE_DB_PATH", "riskoptimizer.db")
            return f"sqlite:///{db_path}"
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


@dataclass
class RedisConfig:
    """Redis configuration settings."""

    host: str
    port: int
    db: int = 0
    password: Optional[str] = None
    socket_timeout: int = 30
    socket_connect_timeout: int = 30
    retry_on_timeout: bool = True

    @property
    def url(self) -> str:
        """Get Redis URL."""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


@dataclass
class SecurityConfig:
    """Security configuration settings."""

    secret_key: str
    jwt_secret_key: str
    data_encryption_key: str
    jwt_access_token_expires: int = 3600
    jwt_refresh_token_expires: int = 2592000
    password_hash_rounds: int = 12
    rate_limit_per_minute: int = 60
    max_login_attempts: int = 5
    lockout_time: int = 300


@dataclass
class BlockchainConfig:
    """Blockchain configuration settings."""

    provider_url: str
    portfolio_tracker_address: str
    risk_management_address: str
    gas_limit: int = 500000
    gas_price: int = 20000000000


@dataclass
class CeleryConfig:
    """Celery configuration settings."""

    broker_url: str
    result_backend: str
    task_serializer: str = "json"
    accept_content: Optional[list] = None
    result_serializer: str = "json"
    timezone: str = "UTC"
    enable_utc: bool = True

    def __post_init__(self) -> None:
        if self.accept_content is None:
            self.accept_content = ["json"]


@dataclass
class APIConfig:
    """API configuration settings."""

    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    cors_origins: Optional[list] = None
    max_content_length: int = 16 * 1024 * 1024

    def __post_init__(self) -> None:
        if self.cors_origins is None:
            self.cors_origins = ["*"]


class Config:
    """Main configuration class that aggregates all configuration settings."""

    def __init__(self) -> None:
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.database = self._load_database_config()
        self.redis = self._load_redis_config()
        self.security = self._load_security_config()
        self.blockchain = self._load_blockchain_config()
        self.celery = self._load_celery_config()
        self.api = self._load_api_config()
        self.model_path = self._get_model_path()

    def _load_database_config(self) -> DatabaseConfig:
        """Load database configuration from environment variables."""
        return DatabaseConfig(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            name=os.getenv("DB_NAME", "riskoptimizer"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "postgres"),
            pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
            pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
            pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600")),
        )

    def _load_redis_config(self) -> RedisConfig:
        """Load Redis configuration from environment variables."""
        return RedisConfig(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            password=os.getenv("REDIS_PASSWORD"),
            socket_timeout=int(os.getenv("REDIS_SOCKET_TIMEOUT", "30")),
            socket_connect_timeout=int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "30")),
            retry_on_timeout=os.getenv("REDIS_RETRY_ON_TIMEOUT", "true").lower()
            == "true",
        )

    def _load_security_config(self) -> SecurityConfig:
        """Load security configuration from environment variables."""
        import logging

        from cryptography.fernet import Fernet

        secret_key = os.getenv("SECRET_KEY")
        if not secret_key:
            secret_key = "dev-secret-key-change-in-production"
            if self.environment == "production":
                raise ValueError(
                    "SECRET_KEY environment variable is required in production"
                )
            logging.warning(
                "Using default SECRET_KEY. This is NOT recommended for production."
            )

        jwt_secret_key = os.getenv("JWT_SECRET_KEY")
        if not jwt_secret_key:
            jwt_secret_key = "dev-jwt-secret-key-change-in-production"
            if self.environment == "production":
                raise ValueError(
                    "JWT_SECRET_KEY environment variable is required in production"
                )
            logging.warning(
                "Using default JWT_SECRET_KEY. This is NOT recommended for production."
            )

        data_encryption_key = os.getenv("DATA_ENCRYPTION_KEY")
        if not data_encryption_key:
            data_encryption_key = Fernet.generate_key().decode()
            logging.warning(
                "DATA_ENCRYPTION_KEY not found. A new key has been generated. This is NOT recommended for production."
            )
        return SecurityConfig(
            secret_key=secret_key,
            jwt_secret_key=jwt_secret_key,
            jwt_access_token_expires=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "3600")),
            jwt_refresh_token_expires=int(
                os.getenv("JWT_REFRESH_TOKEN_EXPIRES", "2592000")
            ),
            password_hash_rounds=int(os.getenv("PASSWORD_HASH_ROUNDS", "12")),
            rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
            max_login_attempts=int(os.getenv("MAX_LOGIN_ATTEMPTS", "5")),
            lockout_time=int(os.getenv("LOCKOUT_TIME", "300")),
            data_encryption_key=data_encryption_key,
        )

    def _load_blockchain_config(self) -> BlockchainConfig:
        """Load blockchain configuration from environment variables."""
        return BlockchainConfig(
            provider_url=os.getenv("BLOCKCHAIN_PROVIDER", "http://localhost:8545"),
            portfolio_tracker_address=os.getenv(
                "PORTFOLIO_TRACKER_ADDRESS",
                "0x0000000000000000000000000000000000000000",
            ),
            risk_management_address=os.getenv(
                "RISK_MANAGEMENT_ADDRESS", "0x0000000000000000000000000000000000000000"
            ),
            gas_limit=int(os.getenv("BLOCKCHAIN_GAS_LIMIT", "500000")),
            gas_price=int(os.getenv("BLOCKCHAIN_GAS_PRICE", "20000000000")),
        )

    def _load_celery_config(self) -> CeleryConfig:
        """Load Celery configuration from environment variables."""
        broker_url = os.getenv("CELERY_BROKER_URL", self.redis.url)
        result_backend = os.getenv("CELERY_RESULT_BACKEND", self.redis.url)
        return CeleryConfig(
            broker_url=broker_url,
            result_backend=result_backend,
            task_serializer=os.getenv("CELERY_TASK_SERIALIZER", "json"),
            result_serializer=os.getenv("CELERY_RESULT_SERIALIZER", "json"),
            timezone=os.getenv("CELERY_TIMEZONE", "UTC"),
            enable_utc=os.getenv("CELERY_ENABLE_UTC", "true").lower() == "true",
        )

    def _load_api_config(self) -> APIConfig:
        """Load API configuration from environment variables."""
        cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
        return APIConfig(
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "5000")),
            debug=os.getenv("DEBUG_MODE", "false").lower() == "true",
            cors_origins=cors_origins,
            max_content_length=int(
                os.getenv("MAX_CONTENT_LENGTH", str(16 * 1024 * 1024))
            ),
        )

    def _get_model_path(self) -> str:
        """Get the path to the AI model file."""
        model_path = os.getenv("MODEL_PATH")
        if model_path:
            return model_path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        return os.path.join(project_root, "code", "ai_models", "optimization_model.pkl")

    def validate(self) -> None:
        """Validate configuration settings."""
        import logging

        required_vars = ["SECRET_KEY", "JWT_SECRET_KEY", "DATA_ENCRYPTION_KEY"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )
        if not os.path.exists(self.model_path):
            logging.warning(
                f"Model file not found at: {self.model_path}. "
                f"AI optimization features will be unavailable. "
                f"To enable AI features, train and place a model file at this location."
            )


config = Config()

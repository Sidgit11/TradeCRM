from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database (Neon)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/tradyon_outreach"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Clerk Auth
    CLERK_SECRET_KEY: str = ""
    CLERK_PUBLISHABLE_KEY: str = ""
    CLERK_JWT_ISSUER: str = ""

    # AI Models
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""

    # Enrichment pipeline
    PERPLEXITY_API_KEY: str = ""
    FIRECRAWL_API_KEY: str = ""
    APOLLO_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # WhatsApp (Gupshup)
    GUPSHUP_PARTNER_EMAIL: str = ""
    GUPSHUP_PARTNER_SECRET: str = ""
    GUPSHUP_HSM_USERID: str = ""
    GUPSHUP_HSM_PASSWORD: str = ""
    GUPSHUP_TWOWAY_USERID: str = ""
    GUPSHUP_TWOWAY_PASSWORD: str = ""
    GUPSHUP_WABA_NUMBER: str = ""
    GUPSHUP_API_KEY: str = ""
    GUPSHUP_APP_ID: str = ""
    GUPSHUP_WEBHOOK_SECRET: str = ""
    GUPSHUP_WEBHOOK_URL: str = ""

    # Email Provider — set EMAIL_PROVIDER to: sendgrid, resend, ses, smtp, or log
    EMAIL_PROVIDER: str = "log"
    SENDGRID_API_KEY: str = ""
    RESEND_API_KEY: str = ""
    # AWS SES (if using ses provider)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_SES_REGION: str = "us-east-1"
    # Generic SMTP (if using smtp provider)
    SMTP_HOST: str = ""
    SMTP_PORT: str = "587"
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: str = "true"

    # Gmail OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"

    # Microsoft OAuth
    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    MICROSOFT_REDIRECT_URI: str = "http://localhost:8000/auth/microsoft/callback"

    # Web Search
    BRAVE_SEARCH_API_KEY: str = ""

    # TradeGenie (Dify)
    DIFY_API_KEY: str = ""
    DIFY_BASE_URL: str = ""

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_STARTER_PRICE_ID: str = ""
    STRIPE_GROWTH_PRICE_ID: str = ""
    STRIPE_PRO_PRICE_ID: str = ""

    # App
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"
    ENCRYPTION_KEY: str = ""

    # Dev mode — bypasses auth, uses a test user
    DEV_MODE: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

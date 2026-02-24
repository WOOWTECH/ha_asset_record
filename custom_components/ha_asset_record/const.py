"""Constants for Ha Asset Record integration."""

from typing import Final

DOMAIN: Final = "ha_asset_record"

# Storage
STORAGE_KEY: Final = DOMAIN
STORAGE_VERSION: Final = 1

# Platforms
PLATFORMS: Final = ["datetime", "text", "number"]

# Asset fields
FIELD_NAME: Final = "name"
FIELD_PURCHASE_AT: Final = "purchase_at"
FIELD_WARRANTY_UNTIL: Final = "warranty_until"
FIELD_BRAND: Final = "brand"
FIELD_CATEGORY: Final = "category"
FIELD_MANUAL_MD: Final = "manual_md"
FIELD_MAINTENANCE_MD: Final = "maintenance_md"
FIELD_VALUE: Final = "value"

# Number entity limits
VALUE_MIN: Final = 0
VALUE_MAX: Final = 99999999
VALUE_STEP: Final = 1

# Text entity max length (for state, full content in raw_content attribute)
TEXT_MAX_LENGTH: Final = 255

# Attribute keys
ATTR_RAW_CONTENT: Final = "raw_content"
ATTR_ASSET_ID: Final = "asset_id"

# Options flow actions
ACTION_CREATE_ASSET: Final = "create_asset"
ACTION_DELETE_ASSET: Final = "delete_asset"

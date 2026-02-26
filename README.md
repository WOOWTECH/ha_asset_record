# Ha Asset Record

A Home Assistant custom component for managing and tracking your home assets, including appliances, electronics, and other valuable items.

## Features

- **Asset Management Dashboard**: A beautiful sidebar panel for managing all your assets
- **Track Key Information**: 
  - Name, Brand, Category
  - Purchase date and price/value
  - Warranty expiration tracking
  - Manual and maintenance notes (Markdown supported)
- **Warranty Alerts**: Visual indicators for expired or soon-to-expire warranties
- **Search & Filter**: Quickly find assets by name, brand, or category
- **Multi-language Support**: English and Traditional Chinese (zh-Hant)
- **Home Assistant Integration**: Each asset creates entities that can be used in automations

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner and select "Custom repositories"
4. Add this repository URL: `https://github.com/WOOWTECH/ha_asset_record`
5. Select "Integration" as the category
6. Click "Add"
7. Search for "Ha Asset Record" and install it
8. Restart Home Assistant

### Manual Installation

1. Download the `ha_asset_record` folder from the `custom_components` directory
2. Copy it to your Home Assistant's `custom_components` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** > **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Ha Asset Record" or "Device Record"
4. Follow the setup wizard

## Usage

After installation, a new "Device Record" panel will appear in your Home Assistant sidebar. From there you can:

1. **Add Assets**: Click the "+" button to add a new asset
2. **Edit Assets**: Click on any asset in the table to edit its details
3. **Delete Assets**: Use the delete button in the edit dialog
4. **Search**: Use the search bar to filter assets by name, brand, or category

## Requirements

- Home Assistant 2025.12.0 or newer

## Support

If you encounter any issues or have feature requests, please [open an issue](https://github.com/WOOWTECH/ha_asset_record/issues).

## License

This project is licensed under the [GPL-3.0 License](LICENSE).

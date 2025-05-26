# InnerArchitect Internationalization (i18n) Framework

This framework provides comprehensive internationalization and localization capabilities for The Inner Architect application.

## Features

- **Enhanced language detection**: Detect user's language from browser settings
- **Locale-aware formatting**: Format dates, times, numbers, and currencies according to locale conventions
- **Translation management**: Easily manage translations with a robust message catalog system
- **Pluralization support**: Handle different plural forms across languages
- **RTL support**: Right-to-left language support for Arabic and other RTL languages
- **Region-specific localization**: Support for regional variants of languages (e.g., US English vs. UK English)
- **Translation fallback**: Graceful fallback to base language or English when translations are missing
- **Template components**: Reusable template components for i18n-aware UI elements
- **Command-line tools**: Extract, update, and manage translations from the command line

## Getting Started

### Using Translations in Templates

```html
<!-- Basic translation -->
{{ t('key', 'Default text') }}

<!-- Shorthand for g.translate -->
{{ translate('key', 'Default text') }}

<!-- Import components -->
{% import 'i18n_components.html' as i18n %}

<!-- Use components -->
{{ i18n.format_date_component(date_value) }}
{{ i18n.format_currency_component(amount) }}
{{ i18n.language_selector() }}

<!-- Language-specific content -->
{% call i18n.language_specific('es') %}
    This content only appears in Spanish
{% endcall %}

<!-- RTL-specific content -->
{% call i18n.rtl_only() %}
    This content only appears for RTL languages
{% endcall %}
```

### Using Translations in Python Code

```python
from i18n.translations import get_translation

# Get a translation
translated_text = get_translation('key', 'Default text', 'fr')

# Format a date
from i18n.formatting import format_date
formatted_date = format_date(datetime.now(), locale='de')

# Format a number
from i18n.formatting import format_number
formatted_number = format_number(1234.56, decimal_places=2, locale='fr')
```

### Managing Translations

The i18n framework provides a command-line tool for managing translations:

```bash
# Extract translation strings from templates and Python files
python -m i18n.cli extract

# Update translation files with new strings
python -m i18n.cli update

# Create a new translation file
python -m i18n.cli create fr

# Show translation status
python -m i18n.cli status

# Initialize translations directory and config
python -m i18n.cli init
```

## Architecture

The i18n framework consists of several modules:

- **translations.py**: Core translation functionality
- **formatting.py**: Locale-aware formatting
- **message_catalog.py**: Message extraction and management
- **flask_integration.py**: Flask integration
- **template_components.py**: Template components
- **cli.py**: Command-line tools

## Supported Languages

The framework supports the following languages:

- English (en)
- Spanish (es)
- French (fr)
- German (de)
- Chinese (zh)
- Japanese (ja)
- Russian (ru)
- Portuguese (pt)
- Arabic (ar)
- Hindi (hi)
- Korean (ko)
- Italian (it)

## Regional Variants

Regional variants are also supported:

- English: US (en-US), UK (en-GB), Canada (en-CA), Australia (en-AU)
- Spanish: Spain (es-ES), Mexico (es-MX), Argentina (es-AR)
- French: France (fr-FR), Canada (fr-CA)
- Portuguese: Brazil (pt-BR), Portugal (pt-PT)
- Chinese: China (zh-CN), Taiwan (zh-TW)

## Best Practices

1. **Use keys, not English text**: Always use translation keys instead of English text directly
2. **Provide default text**: Always provide default text for translations
3. **Use components**: Use the provided template components for internationalized UI elements
4. **Test with RTL languages**: Always test your UI with RTL languages
5. **Use formatters**: Use the provided formatters for dates, numbers, and currencies
6. **Extract translations regularly**: Regularly extract translations to keep them up to date

## Demo

Visit the [i18n demo page](/i18n-demo) to see the framework in action.
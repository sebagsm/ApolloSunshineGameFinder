# ApolloSunshineGameFinder
# Steam to Apollo Game Scanner

Automatically scan Steam games and add them to Apollo/Sunshine for game streaming.

## Features
- Auto-detects Steam installation
- Scans multiple Steam libraries
- Adds games with Apollo's virtual display support
- Prevents duplicate entries

## Requirements
- Python 3.6+
- Windows (for registry detection)
- Apollo or Sunshine installed

## Usage

### Basic usage (auto-detect Steam):
```bash
python steam_sunshine_scanner.py
```

### Custom Steam library paths:
```bash
python steam_sunshine_scanner.py --steam-path "D:\SteamLibrary" "E:\Games\Steam"
```

### Custom Apollo config location:
```bash
python steam_sunshine_scanner.py --config "C:\Program Files\Apollo\config"
```

### Verbose mode for debugging:
```bash
python steam_sunshine_scanner.py --verbose
```

## Options
- `--steam-path PATH [PATH ...]` - Specify custom Steam library locations
- `--config PATH` - Custom Apollo/Sunshine config path
- `--no-virtual-display` - Disable virtual display feature
- `--verbose` - Enable detailed output
- `--help` - Show help message

## Important
**Restart Apollo/Sunshine after running the script for changes to take effect!**

## License
MIT License

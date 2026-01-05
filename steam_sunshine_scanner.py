#!/usr/bin/env python3
"""
Steam to Apollo/Sunshine Game Scanner
Scans for installed Steam games and adds them to Apollo's apps list
Apollo is a Sunshine fork with enhanced features including virtual display support
"""

import json
import os
import re
import sys
import argparse
import winreg
from pathlib import Path
from typing import List, Dict, Optional

class SteamScanner:
    def __init__(self, custom_paths: Optional[List[str]] = None):
        self.steam_path = self.get_steam_path()
        self.library_folders = []
        self.custom_paths = custom_paths or []
        
    def get_steam_path(self) -> Optional[str]:
        """Get Steam installation path from Windows registry"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                r"Software\Valve\Steam")
            steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
            winreg.CloseKey(key)
            return steam_path.replace('/', '\\')
        except Exception as e:
            print(f"Error finding Steam path: {e}")
            return None
    
    def parse_vdf(self, file_path: str) -> Dict:
        """Parse Valve Data File (VDF) format with improved parsing"""
        result = {}
        stack = [result]
        current_key = None
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Split into lines for processing
                lines = content.split('\n')
                
                for line in lines:
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('//'):
                        continue
                    
                    # Check for opening brace (start of new section)
                    if line == '{':
                        if current_key and len(stack) > 0:
                            new_dict = {}
                            stack[-1][current_key] = new_dict
                            stack.append(new_dict)
                            current_key = None
                        continue
                    
                    # Check for closing brace (end of section)
                    if line == '}':
                        if len(stack) > 1:
                            stack.pop()
                        continue
                    
                    # Parse key-value pairs
                    # Pattern: "key"		"value"
                    matches = re.findall(r'"([^"]*)"', line)
                    
                    if len(matches) == 2:
                        # Key-value pair
                        key, value = matches[0], matches[1]
                        if len(stack) > 0:
                            stack[-1][key] = value
                    elif len(matches) == 1:
                        # Just a key (section name)
                        current_key = matches[0]
                        
        except Exception as e:
            print(f"Error parsing VDF {file_path}: {e}")
        
        return result
    
    def get_library_folders(self) -> List[str]:
        """Get all Steam library folders"""
        folders = []
        
        # Add custom paths first
        if self.custom_paths:
            print(f"Using custom Steam library paths:")
            for path in self.custom_paths:
                if os.path.exists(path):
                    folders.append(path)
                    print(f"  ✓ {path}")
                else:
                    print(f"  ✗ {path} (not found)")
        
        # If no custom paths or we want to also scan default locations
        if not self.custom_paths and self.steam_path:
            folders.append(self.steam_path)
            vdf_path = os.path.join(self.steam_path, 'steamapps', 'libraryfolders.vdf')
            
            if os.path.exists(vdf_path):
                data = self.parse_vdf(vdf_path)
                if 'libraryfolders' in data:
                    for key, value in data['libraryfolders'].items():
                        if isinstance(value, dict) and 'path' in value:
                            folders.append(value['path'].replace('\\\\', '\\'))
        
        self.library_folders = folders
        return folders
    
    def scan_games(self, verbose: bool = False) -> List[Dict]:
        """Scan all library folders for installed games"""
        games = []
        
        if not self.library_folders:
            self.get_library_folders()
        
        if verbose:
            print("\n--- Detailed Scan ---")
        
        for folder in self.library_folders:
            steamapps = os.path.join(folder, 'steamapps')
            
            if verbose:
                print(f"\nChecking: {folder}")
                print(f"  steamapps path: {steamapps}")
                print(f"  exists: {os.path.exists(steamapps)}")
            
            if not os.path.exists(steamapps):
                if verbose:
                    print(f"  ✗ steamapps folder not found")
                continue
            
            manifest_files = [f for f in os.listdir(steamapps) 
                            if f.startswith('appmanifest_') and f.endswith('.acf')]
            
            if verbose:
                print(f"  Found {len(manifest_files)} manifest files")
            
            for file in manifest_files:
                manifest_path = os.path.join(steamapps, file)
                if verbose:
                    print(f"    Processing: {file}")
                
                game_info = self.parse_manifest(manifest_path, verbose=verbose)
                if game_info:
                    games.append(game_info)
                    if verbose:
                        print(f"      ✓ Added: {game_info['name']}")
                elif verbose:
                    print(f"      ✗ Failed to parse")
        
        return games
    
    def parse_manifest(self, manifest_path: str, verbose: bool = False) -> Optional[Dict]:
        """Parse a Steam app manifest file"""
        data = self.parse_vdf(manifest_path)
        
        if verbose:
            print(f"      Parsed data keys: {list(data.keys())}")
        
        if 'AppState' not in data:
            if verbose:
                print(f"      ✗ No 'AppState' key found")
            return None
        
        app_state = data['AppState']
        app_id = app_state.get('appid', '')
        name = app_state.get('name', 'Unknown')
        install_dir = app_state.get('installdir', '')
        
        if verbose:
            print(f"      App ID: {app_id}")
            print(f"      Name: {name}")
            print(f"      Install Dir: {install_dir}")
        
        if not app_id or not name:
            if verbose:
                print(f"      ✗ Missing app_id or name")
            return None
        
        return {
            'name': name,
            'app_id': app_id,
            'install_dir': install_dir,
            'exe_path': f'steam://rungameid/{app_id}'
        }

class ApolloIntegration:
    """Integration for Apollo (Sunshine fork) with enhanced virtual display support"""
    
    def __init__(self, config_path: Optional[str] = None, verbose: bool = False):
        self.verbose = verbose
        if config_path:
            # If user provides a directory, append apps.json
            if os.path.isdir(config_path):
                self.config_path = os.path.join(config_path, 'apps.json')
                if self.verbose:
                    print(f"Config path is a directory, using: {self.config_path}")
            else:
                self.config_path = config_path
        else:
            # Default Apollo config location (same as Sunshine)
            self.config_path = os.path.join(
                os.getenv('PROGRAMDATA', 'C:\\ProgramData'),
                'Sunshine',  # Apollo uses same directory structure
                'apps.json'
            )
        
        if self.verbose:
            print(f"\nApollo config path: {self.config_path}")
            print(f"Config file exists: {os.path.exists(self.config_path)}")
    
    def load_apps(self) -> Dict:
        """Load existing Apollo apps configuration"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if self.verbose:
                        print(f"Loaded existing config with {len(config.get('apps', []))} apps")
                    return config
            except Exception as e:
                print(f"Error loading config: {e}")
        else:
            if self.verbose:
                print("No existing config found, will create new one")
        
        return {"apps": []}
    
    def save_apps(self, config: Dict):
        """Save Apollo apps configuration"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            print(f"✓ Configuration saved to {self.config_path}")
            
            if self.verbose:
                print(f"Total apps in config: {len(config.get('apps', []))}")
        except Exception as e:
            print(f"✗ Error saving config: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
    
    def add_games(self, games: List[Dict], enable_virtual_display: bool = True):
        """
        Add Steam games to Apollo configuration
        
        Args:
            games: List of game dictionaries
            enable_virtual_display: Enable Apollo's virtual display feature (recommended)
        """
        config = self.load_apps()
        
        if "apps" not in config:
            config["apps"] = []
        
        existing_names = {app.get('name', '') for app in config['apps']}
        added = 0
        
        if self.verbose:
            print(f"\nExisting apps in config: {len(existing_names)}")
            if existing_names:
                print(f"Existing app names: {list(existing_names)[:5]}...")  # Show first 5
        
        for game in games:
            if game['name'] not in existing_names:
                apollo_app = {
                    "name": game['name'],
                    "output": "",
                    "cmd": "",
                    "detached": [game['exe_path']],
                    "image-path": ""
                }
                
                # Apollo-specific: Enable virtual display for better resolution matching
                # This utilizes Apollo's SudoVDA integration for automatic resolution/framerate matching
                if enable_virtual_display:
                    apollo_app["virtual-display"] = True
                
                config['apps'].append(apollo_app)
                added += 1
                print(f"Added: {game['name']}" + 
                      (" [Virtual Display Enabled]" if enable_virtual_display else ""))
            else:
                if self.verbose:
                    print(f"Skipped (already exists): {game['name']}")
        
        if added > 0:
            self.save_apps(config)
            print(f"\n{'='*60}")
            print(f"Total games added: {added}")
            print(f"Virtual display: {'Enabled' if enable_virtual_display else 'Disabled'}")
            print(f"{'='*60}")
        else:
            print("No new games to add (all games already in config)")

def main():
    parser = argparse.ArgumentParser(
        description='Scan Steam games and add them to Apollo/Sunshine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Auto-detect Steam installation
  python script.py
  
  # Specify custom Steam library paths
  python script.py --steam-path "D:\\SteamLibrary" "E:\\Games\\Steam"
  
  # Use custom Apollo config location
  python script.py --config "C:\\Custom\\Path\\apps.json"
  
  # Disable virtual display feature
  python script.py --no-virtual-display
        '''
    )
    
    parser.add_argument(
        '--steam-path',
        nargs='+',
        metavar='PATH',
        help='Custom Steam library path(s). Can specify multiple paths separated by space.'
    )
    
    parser.add_argument(
        '--config',
        metavar='PATH',
        help='Custom Apollo/Sunshine apps.json config path (or directory containing apps.json)'
    )
    
    parser.add_argument(
        '--no-virtual-display',
        action='store_true',
        help='Disable Apollo virtual display feature for added games'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output for debugging'
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("Steam to Apollo Game Scanner")
    print("Apollo: Sunshine fork with Virtual Display support")
    print("="*60)
    print()
    
    # Scan for Steam games
    scanner = SteamScanner(custom_paths=args.steam_path)
    
    if not args.steam_path and not scanner.steam_path:
        print("Error: Could not find Steam installation")
        print("Use --steam-path to specify custom Steam library locations")
        return
    
    if scanner.steam_path and not args.steam_path:
        print(f"Steam path: {scanner.steam_path}")
    
    folders = scanner.get_library_folders()
    print(f"\nFound {len(folders)} library folder(s)")
    
    if not folders:
        print("\nNo Steam library folders found!")
        print("Use --steam-path to specify custom locations")
        return
    
    print("\nScanning for games...")
    games = scanner.scan_games(verbose=args.verbose)
    print(f"Found {len(games)} installed game(s)\n")
    
    if not games:
        print("No games found in the specified locations")
        return
    
    # Add to Apollo with virtual display support
    print("Adding games to Apollo...")
    enable_vd = not args.no_virtual_display
    
    if enable_vd:
        print("Virtual display will be enabled by default for automatic resolution matching\n")
    else:
        print("Virtual display is disabled\n")
    
    apollo = ApolloIntegration(config_path=args.config, verbose=args.verbose)
    apollo.add_games(games, enable_virtual_display=enable_vd)
    
    if enable_vd:
        print("\nNote: Apollo's virtual display feature will automatically match")
        print("your client's resolution and framerate when streaming these games.")
        print("No dummy plugs or manual resolution configuration needed!")
    
    print("\n" + "="*60)
    print("IMPORTANT: Restart Apollo/Sunshine for changes to take effect!")
    print("="*60)

if __name__ == "__main__":
    main()

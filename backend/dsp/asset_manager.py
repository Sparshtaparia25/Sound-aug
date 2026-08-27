import os
import json
import random
from typing import List, Dict, Any

ASSET_DIR = "backend/dsp/assets"

class AssetManager:
    def __init__(self):
        self.noise_manifest: Dict[str, Any] = {}
        self.available_noises: Dict[str, List[str]] = {}
        self._scan_assets()

    def _scan_assets(self):
        # We no longer scan for RIR assets, they are generated procedurally.
        
        # Scan Noises using manifest
        manifest_path = os.path.join(ASSET_DIR, "noise", "manifest.json")
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    self.noise_manifest = json.load(f)
                    
                for asset_id, asset_info in self.noise_manifest.items():
                    profile = asset_info.get("profile")
                    if profile:
                        if profile not in self.available_noises:
                            self.available_noises[profile] = []
                        self.available_noises[profile].append(asset_id)
            except Exception as e:
                print(f"Failed to load noise manifest: {e}")

    def get_available_noise_profiles(self) -> List[str]:
        return list(self.available_noises.keys())

    def get_noise_asset(self, profile: str, seed: int) -> Dict[str, Any]:
        """Returns the full metadata dictionary for the chosen noise asset."""
        if profile not in self.available_noises:
            raise ValueError(f"Noise profile '{profile}' not available or has no assets.")
        assets = self.available_noises[profile]
        rng = random.Random(seed)
        asset_id = rng.choice(assets)
        asset_meta = self.noise_manifest[asset_id]
        asset_meta["id"] = asset_id
        return asset_meta

asset_manager = AssetManager()

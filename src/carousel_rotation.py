# Gestor persistente de rotacion de sistemas de diseno para carruseles.
from __future__ import annotations
import json
import os
from typing import Any, Dict, Optional
from src.design_systems import DESIGN_SYSTEMS, DesignSystem, _stable_hash

class CarouselRotationManager:
    DEFAULT_STATE_FILE = os.path.join('data', 'carousel_rotation.json')

    def __init__(self, state_path: Optional[str] = None) -> None:
        self.state_path = state_path or self.DEFAULT_STATE_FILE
        self._is_custom_path = bool(state_path and state_path != self.DEFAULT_STATE_FILE)
        self._memory_cache: Dict[str, int] = {}

    def _load_state(self) -> Dict[str, int]:
        if not os.path.exists(self.state_path):
            return dict(self._memory_cache)
        try:
            with open(self.state_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self._memory_cache.update({str(k): int(v) for k, v in data.items() if isinstance(v, (int, float))})
        except Exception:
            pass
        return dict(self._memory_cache)

    def _save_state(self, state: Dict[str, int]) -> None:
        self._memory_cache.update(state)
        try:
            dir_name = os.path.dirname(os.path.abspath(self.state_path))
            os.makedirs(dir_name, exist_ok=True)
            temp_file = os.path.join(dir_name, f'.tmp_rot_{os.getpid()}.json')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self._memory_cache, f, indent=2)
            os.replace(temp_file, self.state_path)
        except Exception:
            pass

    def get_next_theme(self, context_key: str = 'global', advance: bool = True, index_offset: int = 0) -> DesignSystem:
        state = self._load_state()
        if context_key in state:
            current_offset = state[context_key]
        else:
            # En GitHub Actions o entornos efímeros, GITHUB_RUN_NUMBER da la secuencia monotónica real
            run_num_env = os.getenv("GITHUB_RUN_NUMBER")
            if not self._is_custom_path and run_num_env and run_num_env.isdigit():
                seed_base = context_key.split("/")[0].strip().lower() if context_key and "/" in context_key else (context_key or "").strip().lower()
                current_offset = int(run_num_env) + (_stable_hash(seed_base) if seed_base else 0)
            else:
                current_offset = 0

        system_index = (current_offset + index_offset) % len(DESIGN_SYSTEMS)
        chosen_system = DESIGN_SYSTEMS[system_index]
        if advance:
            state[context_key] = (current_offset + 1) % len(DESIGN_SYSTEMS)
            self._save_state(state)
        return chosen_system

    def get_current_theme(self, context_key: str = 'global', index_offset: int = 0) -> DesignSystem:
        return self.get_next_theme(context_key=context_key, advance=False, index_offset=index_offset)

_GLOBAL_ROTATION_MANAGER: Optional[CarouselRotationManager] = None

def get_next_rotating_theme(context_key: str = 'global', state_path: Optional[str] = None, index_offset: int = 0) -> DesignSystem:
    global _GLOBAL_ROTATION_MANAGER
    if _GLOBAL_ROTATION_MANAGER is None or (state_path and _GLOBAL_ROTATION_MANAGER.state_path != state_path):
        _GLOBAL_ROTATION_MANAGER = CarouselRotationManager(state_path=state_path)
    return _GLOBAL_ROTATION_MANAGER.get_next_theme(context_key=context_key, index_offset=index_offset)

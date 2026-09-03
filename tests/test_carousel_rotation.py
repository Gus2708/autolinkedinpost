import os
import json
import pytest
from pathlib import Path
from src.design_systems import DESIGN_SYSTEMS

def test_rotation_manager_cycles_sequentially(tmp_path):
    from src.carousel_rotation import CarouselRotationManager

    state_file = tmp_path / 'rotation.json'
    manager = CarouselRotationManager(state_path=str(state_file))

    # Cycle 1: should get systems 0 through 5 in exact sequence
    selected_systems = []
    for _ in range(len(DESIGN_SYSTEMS)):
        sys = manager.get_next_theme(context_key='test-project')
        selected_systems.append(sys.id)

    expected_order = [s.id for s in DESIGN_SYSTEMS]
    assert selected_systems == expected_order
    # Ensure all 6 distinct systems were returned without duplicates
    assert len(set(selected_systems)) == 6

def test_rotation_manager_persists_across_instances(tmp_path):
    from src.carousel_rotation import CarouselRotationManager

    state_file = tmp_path / 'rotation.json'
    mgr1 = CarouselRotationManager(state_path=str(state_file))
    first = mgr1.get_next_theme(context_key='test-project')
    second = mgr1.get_next_theme(context_key='test-project')

    # Instance 2 boots from disk (simulating server restart)
    mgr2 = CarouselRotationManager(state_path=str(state_file))
    third = mgr2.get_next_theme(context_key='test-project')

    assert first.id != second.id
    assert second.id != third.id
    assert third.id == DESIGN_SYSTEMS[2].id

def test_rotation_manager_wraps_around_and_isolates_contexts(tmp_path):
    from src.carousel_rotation import CarouselRotationManager

    state_file = tmp_path / 'rotation.json'
    manager = CarouselRotationManager(state_path=str(state_file))

    # Consume full cycle of 6
    for _ in range(6):
        manager.get_next_theme(context_key='proj-a')

    # 7th call must wrap around to first system
    wrapped = manager.get_next_theme(context_key='proj-a')
    assert wrapped.id == DESIGN_SYSTEMS[0].id

    # Another context key starts at 0 independently
    proj_b_first = manager.get_next_theme(context_key='proj-b')
    assert proj_b_first.id == DESIGN_SYSTEMS[0].id


def test_rotation_manager_recovers_from_corrupted_file(tmp_path):
    from src.carousel_rotation import CarouselRotationManager
    from src.design_systems import DESIGN_SYSTEMS

    state_file = tmp_path / 'corrupt.json'
    state_file.write_text('{invalid_json: true', encoding='utf-8')

    mgr = CarouselRotationManager(state_path=str(state_file))
    first = mgr.get_next_theme(context_key='test')
    assert first.id == DESIGN_SYSTEMS[0].id

def test_rotation_manager_current_theme_does_not_advance(tmp_path):
    from src.carousel_rotation import CarouselRotationManager

    state_file = tmp_path / 'rotation.json'
    mgr = CarouselRotationManager(state_path=str(state_file))

    curr1 = mgr.get_current_theme(context_key='test')
    curr2 = mgr.get_current_theme(context_key='test')
    assert curr1.id == curr2.id

    # Now advance
    next1 = mgr.get_next_theme(context_key='test')
    assert next1.id == curr1.id

    # Next current is now different
    curr3 = mgr.get_current_theme(context_key='test')
    assert curr3.id != curr1.id

def test_global_helper_function(tmp_path):
    from src.carousel_rotation import get_next_rotating_theme
    from src.design_systems import DESIGN_SYSTEMS

    state_file = tmp_path / 'helper_rotation.json'
    t1 = get_next_rotating_theme(context_key='bot-chat', state_path=str(state_file))
    t2 = get_next_rotating_theme(context_key='bot-chat', state_path=str(state_file))
    assert t1.id != t2.id
    assert t1.id == DESIGN_SYSTEMS[0].id
    assert t2.id == DESIGN_SYSTEMS[1].id

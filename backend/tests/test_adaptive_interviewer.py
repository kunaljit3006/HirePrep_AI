import pytest
from app.models.conversational_state import BehaviorStrategy, MemoryType
from app.services.behavior_validator import BehaviorValidator
from app.services.memory_manager import MemoryManager

def test_behavior_validator_contradiction_struggling():
    validator = BehaviorValidator()
    # Candidate struggling -> SIMPLIFY wins over CHALLENGE/PROBE_DEEPER
    proposed = ["SIMPLIFY", "CHALLENGE", "PROBE_DEEPER"]
    state = {"current_mastery": "struggling", "cumulative_performance": "average"}
    
    result = validator.validate_and_resolve(proposed, state, [])
    
    assert BehaviorStrategy.SIMPLIFY.value in result
    assert BehaviorStrategy.CHALLENGE.value not in result
    assert BehaviorStrategy.PROBE_DEEPER.value not in result

def test_behavior_validator_contradiction_strong():
    validator = BehaviorValidator()
    # Candidate strong -> CHALLENGE / PROBE_DEEPER win over SIMPLIFY
    proposed = ["SIMPLIFY", "CHALLENGE", "PROBE_DEEPER"]
    state = {"current_mastery": "excelling", "cumulative_performance": "excelling"}
    
    result = validator.validate_and_resolve(proposed, state, [])
    
    assert BehaviorStrategy.SIMPLIFY.value not in result
    assert BehaviorStrategy.CHALLENGE.value in result
    assert BehaviorStrategy.PROBE_DEEPER.value in result

def test_behavior_validator_cooldown():
    validator = BehaviorValidator()
    # If ENCOURAGE was used recently, suppress it
    proposed = ["ENCOURAGE", "SIMPLIFY"]
    recent = ["NO_SPECIAL_BEHAVIOR", "ENCOURAGE"]
    
    result = validator.validate_and_resolve(proposed, {}, recent)
    
    assert BehaviorStrategy.ENCOURAGE.value not in result
    assert BehaviorStrategy.SIMPLIFY.value in result

def test_behavior_validator_neutral():
    validator = BehaviorValidator()
    proposed = ["NO_SPECIAL_BEHAVIOR"]
    
    result = validator.validate_and_resolve(proposed, {}, [])
    assert result == ["NO_SPECIAL_BEHAVIOR"]
    
    # Empty falls back to neutral
    result_empty = validator.validate_and_resolve([], {}, [])
    assert result_empty == ["NO_SPECIAL_BEHAVIOR"]

def test_memory_manager_deterministic_pruning():
    manager = MemoryManager(max_memories=3)
    memory_list = [
        {"id": "1", "content": "A", "turn_index": 1, "value_score": 1, "memory_type": "GENERAL"},
        {"id": "2", "content": "B", "turn_index": 2, "value_score": 5, "memory_type": "TECHNICAL_CLAIM"},
        {"id": "3", "content": "C", "turn_index": 3, "value_score": 2, "memory_type": "GENERAL"}
    ]
    
    # Add a high value memory
    new_memory = {"id": "4", "content": "D", "turn_index": 4, "value_score": 9, "memory_type": "PROJECT_DECISION"}
    pruned = manager.add_memory(memory_list, new_memory)
    
    assert len(pruned) == 3
    # ID 1 (lowest score 1) should be pruned. Kept: 2, 3, 4
    ids = [m["id"] for m in pruned]
    assert "1" not in ids
    assert "2" in ids
    assert "3" in ids
    assert "4" in ids
    
    # Should maintain chronological order based on turn_index
    assert ids == ["2", "3", "4"]

def test_memory_manager_llm_compression_threshold():
    manager = MemoryManager(max_memories=15)
    
    # Create 10 memories with huge text to trigger compression threshold
    memory_list = []
    for i in range(10):
        memory_list.append({
            "id": str(i),
            "content": "A" * 400, # 400 chars each * 10 = 4000 total length
            "turn_index": i,
            "value_score": 5,
            "memory_type": "GENERAL"
        })
        
    class MockLLMService:
        pass
        
    compressed = manager.summarize_if_needed(memory_list, MockLLMService())
    
    # It should have compressed the first 5 into 1, leaving 1 + 5 = 6 memories
    assert len(compressed) == 6
    assert compressed[0]["id"] == "compressed_0"
    assert "Summarized past context: " in compressed[0]["content"]
    assert compressed[1]["id"] == "5"


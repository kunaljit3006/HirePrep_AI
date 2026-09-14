from typing import List, Dict, Any
from app.models.conversational_state import ConversationMemoryItem, MemoryType

class MemoryManager:
    """
    Manages bounded conversation memory for the interviewer.
    Prefers deterministic pruning (retaining high-value memories).
    Only triggers LLM summarization if the context becomes meaningfully too large.
    """
    def __init__(self, max_memories: int = 15):
        self.max_memories = max_memories
        
    def add_memory(self, memory_list: List[Dict[str, Any]], new_memory: Dict[str, Any]) -> List[Dict[str, Any]]:
        memory_list.append(new_memory)
        return self._prune_memories(memory_list)
        
    def _prune_memories(self, memory_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if len(memory_list) <= self.max_memories:
            return memory_list
            
        # Deterministic pruning: Keep high value memories
        # 1. Sort by value_score (descending), then turn_index (descending - newer is better)
        sorted_memories = sorted(memory_list, key=lambda x: (x.get("value_score", 1), x.get("turn_index", 0)), reverse=True)
        
        # 2. Keep the top `max_memories`
        retained = sorted_memories[:self.max_memories]
        
        # 3. Sort them back by turn_index to maintain chronological order
        return sorted(retained, key=lambda x: x.get("turn_index", 0))

    def summarize_if_needed(self, memory_list: List[Dict[str, Any]], llm_service: Any = None) -> List[Dict[str, Any]]:
        """
        Only use LLM compression when the accumulated context itself becomes meaningfully too large 
        and deterministic pruning is insufficient (e.g. the text of the 15 memories is huge).
        """
        # Calculate total text size
        total_length = sum(len(m.get("content", "")) for m in memory_list)
        
        # Arbitrary threshold for "meaningfully too large" (e.g., 2000 chars)
        if total_length > 3000 and llm_service:
            # Here we would call the LLM to compress older memories.
            # For this implementation, we will mock the compression by combining the oldest 5 memories into a single GENERAL memory.
            if len(memory_list) > 5:
                memories_to_compress = memory_list[:5]
                remaining_memories = memory_list[5:]
                
                compressed_content = "Summarized past context: " + " | ".join(m.get("content", "") for m in memories_to_compress)
                
                compressed_memory = {
                    "id": "compressed_" + str(memories_to_compress[0].get("turn_index", 0)),
                    "memory_type": MemoryType.GENERAL.value,
                    "content": compressed_content,
                    "turn_index": memories_to_compress[-1].get("turn_index", 0),
                    "value_score": 5
                }
                
                return [compressed_memory] + remaining_memories
                
        return memory_list

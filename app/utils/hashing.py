from uhashring import HashRing

SHARDS = ["shard0", "shard1", "shard2"]
_hash_ring = HashRing(nodes=SHARDS)

def get_shard_for_key(key: str) -> str:
    """
    Determines the appropriate shard for a given key using consistent hashing.
    """
    return _hash_ring.get_node(key)

import redis
import json
import pickle
import logging
from typing import Dict, List, Optional
import numpy as np

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.client = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=False,
        )
        self._check_connection()

    def _check_connection(self):
        try:
            self.client.ping()
            logger.info("Connected to Redis")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _identity_key(self, global_id: str) -> str:
        return f"identity:{global_id}"

    def _camera_tracks_key(self, camera_id: str) -> str:
        return f"camera:{camera_id}:tracks"

    def _identity_index_key(self, camera_id: str) -> str:
        return f"index:identities:{camera_id}"

    def set_identity(
        self,
        global_id: str,
        embedding: np.ndarray,
        height: float,
        camera_id: str,
        timestamp: float,
        ttl: int = 600,
    ):
        data = {
            "embedding": embedding.tobytes(),
            "emb_shape": json.dumps(embedding.shape),
            "emb_dtype": str(embedding.dtype),
            "height": height,
            "last_camera": camera_id,
            "last_seen_at": timestamp,
            "entry_time": timestamp,
        }

        key = self._identity_key(global_id)
        self.client.hset(key, mapping=data)
        self.client.expire(key, ttl)

        self.client.sadd(self._identity_index_key(camera_id), global_id)

    def get_identity(self, global_id: str) -> Optional[Dict]:
        key = self._identity_key(global_id)
        data = self.client.hgetall(key)

        if not data:
            return None

        shape = tuple(json.loads(data[b"emb_shape"]))
        dtype = np.dtype(data[b"emb_dtype"].decode())
        embedding = np.frombuffer(data[b"embedding"], dtype=dtype).reshape(shape)

        return {
            "global_id": global_id,
            "embedding": embedding,
            "height": float(data[b"height"]),
            "last_camera": data[b"last_camera"].decode(),
            "last_seen_at": float(data[b"last_seen_at"]),
            "entry_time": float(data[b"entry_time"]),
        }

    def update_identity(
        self,
        global_id: str,
        embedding: np.ndarray,
        height: float,
        camera_id: str,
        timestamp: float,
        ttl: int = 600,
    ):
        key = self._identity_key(global_id)
        update = {
            "embedding": embedding.tobytes(),
            "emb_shape": json.dumps(embedding.shape),
            "emb_dtype": str(embedding.dtype),
            "height": height,
            "last_camera": camera_id,
            "last_seen_at": timestamp,
        }
        self.client.hset(key, mapping=update)
        self.client.expire(key, ttl)

        self.client.sadd(self._identity_index_key(camera_id), global_id)

    def link_local_track(
        self, camera_id: str, local_track_id: int, global_id: str
    ):
        self.client.hset(
            self._camera_tracks_key(camera_id), str(local_track_id), global_id
        )

    def unlink_local_track(self, camera_id: str, local_track_id: int):
        self.client.hdel(
            self._camera_tracks_key(camera_id), str(local_track_id)
        )

    def get_local_track_global_id(
        self, camera_id: str, local_track_id: int
    ) -> Optional[str]:
        val = self.client.hget(
            self._camera_tracks_key(camera_id), str(local_track_id)
        )
        return val.decode() if val else None

    def get_identities_for_camera(
        self, camera_id: str
    ) -> List[Dict]:
        global_ids = self.client.smembers(
            self._identity_index_key(camera_id)
        )
        candidates = []

        for gid in global_ids:
            identity = self.get_identity(gid.decode())
            if identity:
                candidates.append(identity)

        return candidates

    def get_active_count(self) -> int:
        return len(self.client.keys("identity:*"))

    def get_all_identities(self) -> List[Dict]:
        identity_keys = self.client.keys("identity:*")
        identities = []

        for key in identity_keys:
            global_id = key.decode().split("identity:")[1]
            identity = self.get_identity(global_id)
            if identity:
                identities.append(identity)

        return identities

    def get_camera_tracks(self, camera_id: str) -> Dict[str, str]:
        data = self.client.hgetall(self._camera_tracks_key(camera_id))
        return {
            k.decode(): v.decode() for k, v in data.items()
        }

    def delete_identity(self, global_id: str):
        key = self._identity_key(global_id)
        self.client.delete(key)
        for pattern in [b"index:identities:*"]:
            for index_key in self.client.scan_iter(pattern):
                self.client.srem(index_key, global_id)

    def flush_camera(self, camera_id: str):
        index_key = self._identity_index_key(camera_id)
        global_ids = self.client.smembers(index_key)
        for gid in global_ids:
            gid_str = gid.decode() if isinstance(gid, bytes) else gid
            self.client.delete(self._identity_key(gid_str))
        self.client.delete(index_key)
        self.client.delete(self._camera_tracks_key(camera_id))

    def reassign_global_id_links(self, old_global_id: str, new_global_id: str):
        for pattern in [b"camera:*:tracks"]:
            for tracks_key in self.client.scan_iter(pattern):
                local_ids = self.client.hgetall(tracks_key)
                for local_track_id, gid in local_ids.items():
                    if gid.decode() == old_global_id:
                        self.client.hset(tracks_key, local_track_id, new_global_id)

"""进程内滑动窗口限流器：按客户端标识限制每分钟请求数。

注意：状态存于进程内存，仅适用于单实例部署；多实例需换用
Redis 等外部存储实现（接口保持 ``check(key, limit_per_minute)`` 不变）。
"""

import threading
import time
from collections import defaultdict, deque

_WINDOW_SECONDS = 60.0
_MAX_TRACKED_KEYS = 10_000


class SlidingWindowRateLimiter:
    """按 key 统计滑动窗口内的命中次数，超过上限返回 False。"""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit_per_minute: int) -> bool:
        """记录一次命中；未超限返回 True，超限返回 False（不记录）。"""
        now = time.monotonic()
        window_start = now - _WINDOW_SECONDS
        with self._lock:
            if limit_per_minute <= 0:  # 0/负数表示不启用
                return True
            hits = self._hits[key]
            while hits and hits[0] < window_start:
                hits.popleft()
            if len(hits) >= limit_per_minute:
                return False
            hits.append(now)
            if len(self._hits) > _MAX_TRACKED_KEYS:
                self._sweep()
            return True

    def reset_all(self) -> None:
        """清空全部计数（测试用）。"""
        with self._lock:
            self._hits.clear()

    def _sweep(self) -> None:
        """Opportunistic 清理空 key，防止 key 无限膨胀。"""
        now = time.monotonic()
        window_start = now - _WINDOW_SECONDS
        for key, hits in list(self._hits.items()):
            while hits and hits[0] < window_start:
                hits.popleft()
            if not hits:
                self._hits.pop(key, None)


RATE_LIMITER = SlidingWindowRateLimiter()

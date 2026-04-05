"""Tests for CircuitBreaker — four-state machine with async lock protection."""

import asyncio
from unittest.mock import patch

import pytest

from contract_reviewer.llm.circuit_breaker import CircuitBreaker, CircuitOpenError


@pytest.fixture()
def breaker() -> CircuitBreaker:
    return CircuitBreaker(failure_threshold=3, recovery_timeout=1.0, name="test")


class TestClosedState:
    """CLOSED 状态行为。"""

    async def test_success_stays_closed(self, breaker: CircuitBreaker) -> None:
        result = await breaker.call(lambda: _async_ok(42))
        assert result == 42
        assert breaker.state == "CLOSED"

    async def test_success_resets_failure_count(self, breaker: CircuitBreaker) -> None:
        """成功调用应重置失败计数。"""
        # 先制造 2 次失败（不超过阈值）
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(lambda: _raise(ValueError("fail")))
        # 一次成功
        await breaker.call(lambda: _async_ok(1))
        assert breaker.state == "CLOSED"
        assert breaker._failure_count == 0


class TestOpenState:
    """CLOSED → OPEN 转换和 OPEN 行为。"""

    async def test_opens_after_threshold(self, breaker: CircuitBreaker) -> None:
        """连续失败达到阈值应打开熔断器。"""
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await breaker.call(lambda: _raise(RuntimeError("boom")))
        assert breaker.state == "OPEN"

    async def test_open_rejects_immediately(self, breaker: CircuitBreaker) -> None:
        """OPEN 状态应直接拒绝，不调用实际函数。"""
        # 打开熔断器
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await breaker.call(lambda: _raise(RuntimeError("boom")))

        with pytest.raises(CircuitOpenError):
            await breaker.call(lambda: _async_ok("should not run"))


class TestRecovery:
    """OPEN → PROBING → CLOSED/OPEN 恢复流程。"""

    async def test_probe_on_recovery_timeout(self) -> None:
        """恢复超时后应进入 PROBING 并发送探测请求。"""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1, name="probe-test")

        # 打开
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await breaker.call(lambda: _raise(RuntimeError()))
        assert breaker.state == "OPEN"

        # 等待恢复超时
        await asyncio.sleep(0.15)

        # 探测成功 → CLOSED
        result = await breaker.call(lambda: _async_ok("recovered"))
        assert result == "recovered"
        assert breaker.state == "CLOSED"

    async def test_probe_failure_reopens(self) -> None:
        """探测失败应重新打开熔断器。"""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1, name="probe-fail")

        for _ in range(2):
            with pytest.raises(RuntimeError):
                await breaker.call(lambda: _raise(RuntimeError()))

        await asyncio.sleep(0.15)

        # 探测失败
        with pytest.raises(RuntimeError):
            await breaker.call(lambda: _raise(RuntimeError("probe fail")))
        assert breaker.state == "OPEN"

    async def test_probing_rejects_concurrent(self) -> None:
        """PROBING 状态下并发请求应被拒绝。"""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1, name="concurrent")

        for _ in range(2):
            with pytest.raises(RuntimeError):
                await breaker.call(lambda: _raise(RuntimeError()))

        await asyncio.sleep(0.15)

        # 模拟: 手动设置为 PROBING（模拟探测进行中）
        breaker._state = "PROBING"
        with pytest.raises(CircuitOpenError, match="probe in progress"):
            await breaker.call(lambda: _async_ok("rejected"))


class TestManualReset:

    async def test_reset_from_open(self, breaker: CircuitBreaker) -> None:
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await breaker.call(lambda: _raise(RuntimeError()))
        assert breaker.state == "OPEN"

        await breaker.reset()
        assert breaker.state == "CLOSED"
        assert breaker._failure_count == 0

        result = await breaker.call(lambda: _async_ok("works"))
        assert result == "works"


# ── 工具函数 ──────────────────────────────────────────


async def _async_ok(value):
    return value


async def _raise(exc):
    raise exc

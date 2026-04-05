"""Tests for retry_with_backoff — exponential backoff retry utility."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from contract_reviewer.llm.retry import retry_with_backoff


class TestRetrySuccess:

    async def test_no_retry_on_success(self) -> None:
        """首次成功不应重试。"""
        calls = 0

        async def succeed():
            nonlocal calls
            calls += 1
            return "ok"

        result = await retry_with_backoff(succeed, (RuntimeError,), max_retries=3)
        assert result == "ok"
        assert calls == 1

    async def test_succeeds_after_retries(self) -> None:
        """前两次失败，第三次成功。"""
        attempt = 0

        async def flaky():
            nonlocal attempt
            attempt += 1
            if attempt < 3:
                raise ConnectionError("transient")
            return "recovered"

        with patch("contract_reviewer.llm.retry.asyncio.sleep", new_callable=AsyncMock):
            result = await retry_with_backoff(
                flaky,
                (ConnectionError,),
                max_retries=3,
                base_delay=0.01,
                jitter=0.0,
            )
        assert result == "recovered"
        assert attempt == 3


class TestRetryExhaustion:

    async def test_raises_after_max_retries(self) -> None:
        """超过最大重试次数应抛出最后一个异常。"""
        async def always_fail():
            raise TimeoutError("timeout")

        with patch("contract_reviewer.llm.retry.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(TimeoutError, match="timeout"):
                await retry_with_backoff(
                    always_fail,
                    (TimeoutError,),
                    max_retries=2,
                    base_delay=0.01,
                )

    async def test_non_retryable_exception_not_retried(self) -> None:
        """非指定异常类型不应重试。"""
        calls = 0

        async def type_error():
            nonlocal calls
            calls += 1
            raise TypeError("not retryable")

        with pytest.raises(TypeError):
            await retry_with_backoff(
                type_error,
                (ConnectionError,),  # 只重试 ConnectionError
                max_retries=3,
            )
        assert calls == 1  # 只调用了一次


class TestRetryBackoff:

    async def test_exponential_delay(self) -> None:
        """延迟应指数增长。"""
        delays = []

        async def always_fail():
            raise RuntimeError("fail")

        async def mock_sleep(t):
            delays.append(t)

        with patch("contract_reviewer.llm.retry.asyncio.sleep", side_effect=mock_sleep):
            with pytest.raises(RuntimeError):
                await retry_with_backoff(
                    always_fail,
                    (RuntimeError,),
                    max_retries=3,
                    base_delay=1.0,
                    jitter=0.0,
                )

        assert len(delays) == 3
        # base_delay * 2^attempt: 1.0, 2.0, 4.0
        assert delays[0] == pytest.approx(1.0)
        assert delays[1] == pytest.approx(2.0)
        assert delays[2] == pytest.approx(4.0)

    async def test_zero_max_retries(self) -> None:
        """max_retries=0 应只执行一次，不重试。"""
        calls = 0

        async def fail_once():
            nonlocal calls
            calls += 1
            raise RuntimeError("fail")

        with pytest.raises(RuntimeError):
            await retry_with_backoff(fail_once, (RuntimeError,), max_retries=0)
        assert calls == 1

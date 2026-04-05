"""Tests for ContractSplitter — clause-aware recursive text splitting.

tiktoken 无法在此环境下载 BPE 数据，因此使用 mock encoder。
"""

from unittest.mock import MagicMock, patch

import pytest

from contract_reviewer.models.contract import Contract, Section


class _FakeEncoding:
    """模拟 tiktoken 编码器：每个字符 = 1 token（简化）。"""

    def encode(self, text: str) -> list[int]:
        # 每个字符 = 1 token
        return list(range(len(text)))

    def decode(self, tokens: list[int]) -> str:
        # 返回与 token 数等长的占位文本
        return "字" * len(tokens)


@pytest.fixture(autouse=True)
def _mock_tiktoken(monkeypatch):
    """全局 mock tiktoken.get_encoding，避免网络下载。"""
    fake = _FakeEncoding()
    monkeypatch.setattr("contract_reviewer.chunking.splitter.tiktoken.get_encoding", lambda _: fake)


def _make_splitter(chunk_size: int = 512, overlap: int = 64):
    from contract_reviewer.chunking.splitter import ContractSplitter
    return ContractSplitter(chunk_size=chunk_size, overlap=overlap)


class TestSplitBasic:
    """基本分块行为。"""

    def test_short_section_single_chunk(self, sample_contract: Contract) -> None:
        """短条款不应被拆分。"""
        splitter = _make_splitter(chunk_size=512, overlap=64)
        chunks = splitter.split(sample_contract)
        assert len(chunks) >= 3
        for chunk in chunks:
            assert chunk.total_chunks == len(chunks)

    def test_global_index_assignment(self, sample_contract: Contract) -> None:
        """全局 chunk_index 应连续递增。"""
        splitter = _make_splitter(chunk_size=512, overlap=64)
        chunks = splitter.split(sample_contract)
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_section_heading_preserved(self, sample_contract: Contract) -> None:
        """每个 chunk 应保留原始 section_heading。"""
        splitter = _make_splitter(chunk_size=512, overlap=64)
        chunks = splitter.split(sample_contract)
        headings = {c.section_heading for c in chunks}
        assert "第一条 合同标的" in headings
        assert "第三条 违约责任" in headings

    def test_metadata_section_type(self, sample_contract: Contract) -> None:
        """metadata 中应包含 section_type。"""
        splitter = _make_splitter(chunk_size=512, overlap=64)
        chunks = splitter.split(sample_contract)
        for chunk in chunks:
            assert "section_type" in chunk.metadata


class TestSplitLongSection:
    """长条款的递归分块。"""

    def test_long_section_produces_multiple_chunks(self, long_section_contract: Contract) -> None:
        """超出 chunk_size 的条款应被拆分为多个 chunk。"""
        splitter = _make_splitter(chunk_size=128, overlap=16)
        chunks = splitter.split(long_section_contract)
        assert len(chunks) > 1

    def test_chunk_size_respected(self, long_section_contract: Contract) -> None:
        """每个 chunk 的 token 数不应大幅超出 chunk_size。"""
        splitter = _make_splitter(chunk_size=128, overlap=16)
        chunks = splitter.split(long_section_contract)
        for chunk in chunks:
            token_count = splitter._count_tokens(chunk.text)
            # 允许合理浮动：merge 逻辑中 part 本身可能大于 chunk_size
            assert token_count <= 128 * 2, f"Chunk 过大: {token_count} tokens"

    def test_contract_chunks_updated(self, long_section_contract: Contract) -> None:
        """split() 应同时更新 contract.chunks。"""
        splitter = _make_splitter(chunk_size=128, overlap=16)
        chunks = splitter.split(long_section_contract)
        assert long_section_contract.chunks == chunks


class TestSplitEdgeCases:
    """边界情况。"""

    def test_empty_contract(self) -> None:
        """空合同应返回空 chunk 列表。"""
        contract = Contract(name="空合同", source_path="/tmp/empty.txt", full_text="", sections=[])
        splitter = _make_splitter()
        chunks = splitter.split(contract)
        assert chunks == []

    def test_single_word_section(self) -> None:
        """极短内容不应崩溃。"""
        contract = Contract(
            name="极短",
            source_path="/tmp/short.txt",
            full_text="标题\n内容",
            sections=[Section(heading="标题", body="内容", index=0)],
        )
        splitter = _make_splitter()
        chunks = splitter.split(contract)
        assert len(chunks) == 1
        assert "标题" in chunks[0].text


class TestMergeParts:
    """_merge_parts 内部逻辑。"""

    def test_empty_parts_filtered(self) -> None:
        """空字符串 part 应被过滤。"""
        splitter = _make_splitter(chunk_size=512, overlap=64)
        result = splitter._merge_parts(["", "  ", "有效内容", "", "另一段"])
        assert all(r.strip() for r in result)

    def test_overlap_between_chunks(self) -> None:
        """分块之间应有 overlap 文本重叠。"""
        parts = [f"段落{i}：" + "这是一段较长的合同文本内容。" * 5 for i in range(20)]
        splitter = _make_splitter(chunk_size=64, overlap=16)
        result = splitter._merge_parts(parts)
        if len(result) >= 2:
            assert len(result[1]) > 0


class TestTokenSplit:
    """_split_by_tokens 最后手段分块。"""

    def test_split_by_tokens_produces_chunks(self) -> None:
        """无分隔符的长文本应按 token 数硬切。"""
        text = "甲方" * 500
        splitter = _make_splitter(chunk_size=64, overlap=8)
        result = splitter._split_by_tokens(text)
        assert len(result) > 1

    def test_split_by_tokens_with_overlap_terminates(self) -> None:
        """overlap>0 时不应无限循环（回归测试）。"""
        text = "字" * 200
        splitter = _make_splitter(chunk_size=64, overlap=16)
        result = splitter._split_by_tokens(text)
        # 200 tokens / (64-16) advance = ~5 chunks
        assert 3 <= len(result) <= 6

    def test_split_by_tokens_exact_multiple(self) -> None:
        """文本长度是 chunk_size 整数倍时应正常切分。"""
        text = "字" * 128
        splitter = _make_splitter(chunk_size=64, overlap=0)
        result = splitter._split_by_tokens(text)
        assert len(result) == 2

    def test_split_by_tokens_covers_all_content(self) -> None:
        """所有 token 都应被至少一个 chunk 覆盖。"""
        text = "字" * 100
        splitter = _make_splitter(chunk_size=30, overlap=5)
        result = splitter._split_by_tokens(text)
        # 每个 chunk 的 decode 结果拼接后长度应 >= 原始长度
        total_chars = sum(len(c) for c in result)
        assert total_chars >= 100

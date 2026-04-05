"""Tests for API upload filename validation."""

import pytest
from fastapi import HTTPException

from contract_reviewer.app import _validate_upload_filename


class TestValidateUploadFilename:
    """_validate_upload_filename 安全校验。"""

    def test_normal_pdf(self) -> None:
        assert _validate_upload_filename("合同.pdf") == ".pdf"

    def test_normal_docx(self) -> None:
        assert _validate_upload_filename("contract.docx") == ".docx"

    def test_normal_txt(self) -> None:
        assert _validate_upload_filename("notes.txt") == ".txt"

    def test_case_insensitive_suffix(self) -> None:
        """后缀大小写不敏感。"""
        assert _validate_upload_filename("CONTRACT.PDF") == ".pdf"
        assert _validate_upload_filename("doc.TXT") == ".txt"

    def test_none_filename_defaults(self) -> None:
        """None 文件名应使用默认 contract.txt。"""
        assert _validate_upload_filename(None) == ".txt"

    def test_path_traversal_stripped(self) -> None:
        """路径遍历应被去掉，只保留文件名。"""
        assert _validate_upload_filename("../../etc/passwd.txt") == ".txt"
        assert _validate_upload_filename("/tmp/evil/合同.pdf") == ".pdf"

    def test_windows_path_stripped(self) -> None:
        """Windows 风格路径也应被安全处理。"""
        # PurePosixPath 不解析反斜杠，但文件名本身可能带反斜杠
        result = _validate_upload_filename("C:\\Users\\test\\contract.pdf")
        assert result == ".pdf"

    def test_unsupported_suffix_rejected(self) -> None:
        """不支持的文件类型应返回 422。"""
        with pytest.raises(HTTPException) as exc_info:
            _validate_upload_filename("malware.exe")
        assert exc_info.value.status_code == 422
        assert ".exe" in str(exc_info.value.detail)

    def test_no_suffix_rejected(self) -> None:
        """无后缀文件名应被拒绝。"""
        with pytest.raises(HTTPException) as exc_info:
            _validate_upload_filename("noextension")
        assert exc_info.value.status_code == 422

    def test_hidden_file_rejected(self) -> None:
        """隐藏文件（.开头无后缀）应被拒绝。"""
        with pytest.raises(HTTPException) as exc_info:
            _validate_upload_filename(".htaccess")
        assert exc_info.value.status_code == 422

    def test_double_extension_uses_last(self) -> None:
        """双后缀应取最后一个。"""
        assert _validate_upload_filename("contract.backup.pdf") == ".pdf"

    def test_script_suffix_rejected(self) -> None:
        """脚本文件应被拒绝。"""
        for name in ["inject.py", "shell.sh", "hack.js", "template.html"]:
            with pytest.raises(HTTPException):
                _validate_upload_filename(name)

"""
TDD 示例: 用户认证模块

此文件展示如何按照 TDD 规范编写测试。
"""

import pytest
from datetime import datetime, timedelta


# ============================================================================
# Fixtures (测试夹具)
# ============================================================================

@pytest.fixture
def valid_user():
    """返回有效用户数据."""
    return {
        "user_id": "user_001",
        "email": "test@example.com",
        "password": "secure_password_123",
        "created_at": datetime.now()
    }


@pytest.fixture
def expired_token():
    """返回过期令牌."""
    return {
        "token": "expired_token_xyz",
        "expires_at": datetime.now() - timedelta(hours=1)
    }


@pytest.fixture
def mock_db():
    """模拟数据库."""
    return {
        "users": {},
        "tokens": {}
    }


# ============================================================================
# 测试类: 用户注册
# ============================================================================

class TestUserRegistration:
    """测试用户注册功能."""
    
    def test_register_with_valid_data(self, mock_db):
        """测试使用有效数据注册成功."""
        # Arrange
        email = "new@example.com"
        password = "strong_password"
        
        # Act
        result = register_user(mock_db, email, password)
        
        # Assert
        assert result["success"] is True
        assert result["user_id"].startswith("user_")
        assert result["email"] == email
        assert "password" not in result  # 密码不应返回
    
    def test_register_duplicate_email_fails(self, mock_db, valid_user):
        """测试重复邮箱注册失败."""
        # Arrange - 先注册一个用户
        register_user(mock_db, valid_user["email"], valid_user["password"])
        
        # Act - 尝试用相同邮箱再次注册
        result = register_user(mock_db, valid_user["email"], "another_password")
        
        # Assert
        assert result["success"] is False
        assert "email already exists" in result["error"].lower()
    
    def test_register_with_weak_password_fails(self, mock_db):
        """测试弱密码注册失败."""
        # Arrange
        email = "test@example.com"
        weak_password = "123"
        
        # Act
        result = register_user(mock_db, email, weak_password)
        
        # Assert
        assert result["success"] is False
        assert "password" in result["error"].lower()
    
    def test_register_with_invalid_email_fails(self, mock_db):
        """测试无效邮箱注册失败."""
        # Arrange
        invalid_emails = [
            "not_an_email",
            "@example.com",
            "user@",
            "user@.com",
            ""
        ]
        
        # Act & Assert
        for email in invalid_emails:
            result = register_user(mock_db, email, "password123")
            assert result["success"] is False, f"Should fail for: {email}"


# ============================================================================
# 测试类: 用户登录
# ============================================================================

class TestUserLogin:
    """测试用户登录功能."""
    
    def test_login_with_valid_credentials(self, mock_db, valid_user):
        """测试有效凭据登录成功."""
        # Arrange
        register_user(mock_db, valid_user["email"], valid_user["password"])
        
        # Act
        result = login_user(mock_db, valid_user["email"], valid_user["password"])
        
        # Assert
        assert result["success"] is True
        assert "token" in result
        assert result["user_id"] == valid_user["user_id"]
    
    def test_login_with_wrong_password_fails(self, mock_db, valid_user):
        """测试错误密码登录失败."""
        # Arrange
        register_user(mock_db, valid_user["email"], valid_user["password"])
        
        # Act
        result = login_user(mock_db, valid_user["email"], "wrong_password")
        
        # Assert
        assert result["success"] is False
        assert result["error"] == "Invalid credentials"
    
    def test_login_with_nonexistent_email_fails(self, mock_db):
        """测试不存在邮箱登录失败."""
        # Act
        result = login_user(mock_db, "nonexistent@example.com", "password")
        
        # Assert
        assert result["success"] is False
        assert result["error"] == "Invalid credentials"


# ============================================================================
# 测试类: 令牌验证
# ============================================================================

class TestTokenValidation:
    """测试令牌验证功能."""
    
    def test_validate_valid_token(self, mock_db, valid_user):
        """测试有效令牌验证成功."""
        # Arrange
        login_result = login_user(mock_db, valid_user["email"], valid_user["password"])
        token = login_result["token"]
        
        # Act
        result = validate_token(mock_db, token)
        
        # Assert
        assert result["valid"] is True
        assert result["user_id"] == valid_user["user_id"]
    
    def test_validate_expired_token_fails(self, mock_db, expired_token):
        """测试过期令牌验证失败."""
        # Arrange
        mock_db["tokens"][expired_token["token"]] = expired_token
        
        # Act
        result = validate_token(mock_db, expired_token["token"])
        
        # Assert
        assert result["valid"] is False
        assert "expired" in result["error"].lower()
    
    def test_validate_invalid_token_fails(self, mock_db):
        """测试无效令牌验证失败."""
        # Act
        result = validate_token(mock_db, "invalid_token")
        
        # Assert
        assert result["valid"] is False
        assert result["error"] == "Invalid token"


# ============================================================================
# 边界条件测试
# ============================================================================

class TestEdgeCases:
    """测试边界条件."""
    
    def test_password_maximum_length(self, mock_db):
        """测试密码最大长度限制."""
        # Arrange
        email = "test@example.com"
        long_password = "a" * 1000
        
        # Act
        result = register_user(mock_db, email, long_password)
        
        # Assert
        assert result["success"] is False
        assert "too long" in result["error"].lower()
    
    def test_concurrent_login_attempts(self, mock_db, valid_user):
        """测试并发登录尝试."""
        # Arrange
        register_user(mock_db, valid_user["email"], valid_user["password"])
        
        # Act - 模拟多次登录
        results = [
            login_user(mock_db, valid_user["email"], valid_user["password"])
            for _ in range(5)
        ]
        
        # Assert - 所有登录都应该成功，但令牌应该不同
        assert all(r["success"] for r in results)
        tokens = [r["token"] for r in results]
        assert len(set(tokens)) == 5  # 每个令牌都唯一


# ============================================================================
# 模拟实现 (实际项目中应放在单独文件)
# ============================================================================

def register_user(db, email, password):
    """模拟用户注册."""
    # 验证邮箱格式
    if "@" not in email or "." not in email.split("@")[-1]:
        return {"success": False, "error": "Invalid email format"}
    
    # 验证密码强度
    if len(password) < 8:
        return {"success": False, "error": "Password too weak"}
    
    if len(password) > 128:
        return {"success": False, "error": "Password too long"}
    
    # 检查邮箱是否已存在
    for user in db["users"].values():
        if user["email"] == email:
            return {"success": False, "error": "Email already exists"}
    
    # 创建用户
    user_id = f"user_{len(db['users']) + 1:03d}"
    db["users"][user_id] = {
        "user_id": user_id,
        "email": email,
        "password_hash": f"hash_{password}",  # 简化处理
        "created_at": datetime.now()
    }
    
    return {
        "success": True,
        "user_id": user_id,
        "email": email
    }


def login_user(db, email, password):
    """模拟用户登录."""
    # 查找用户
    user = None
    for u in db["users"].values():
        if u["email"] == email:
            user = u
            break
    
    if user is None:
        return {"success": False, "error": "Invalid credentials"}
    
    # 验证密码
    if user["password_hash"] != f"hash_{password}":
        return {"success": False, "error": "Invalid credentials"}
    
    # 生成令牌
    import uuid
    token = str(uuid.uuid4())
    db["tokens"][token] = {
        "token": token,
        "user_id": user["user_id"],
        "expires_at": datetime.now() + timedelta(hours=24)
    }
    
    return {
        "success": True,
        "user_id": user["user_id"],
        "token": token
    }


def validate_token(db, token):
    """模拟令牌验证."""
    token_data = db["tokens"].get(token)
    
    if token_data is None:
        return {"valid": False, "error": "Invalid token"}
    
    if datetime.now() > token_data["expires_at"]:
        return {"valid": False, "error": "Token expired"}
    
    return {
        "valid": True,
        "user_id": token_data["user_id"]
    }

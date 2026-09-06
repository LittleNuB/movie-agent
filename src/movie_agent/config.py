"""User-owned connections. Secrets never enter serializable configuration."""

from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, SecretStr, field_validator

from .store import Store, uid

PURPOSES = {"director": "text", "vision": "vision", "image": "image", "video": "video",
            "videoFallback": "video", "voice": "voice", "music": "music", "sfx": "sfx"}
PROTOCOLS = {"openai": "OpenAI 兼容", "ark": "火山方舟图片／视频",
             "minimax_video": "MiniMax 视频 V2", "minimax_audio": "MiniMax 声音 V1",
             "custom": "其他接口（尚未适配）"}
CAPABILITIES = {
    "openai": {"implemented": ["text", "vision", "image_text"], "discovery": "models", "cancel": False},
    "ark": {"implemented": ["image_text", "image_reference", "video_text", "video_first_last", "video_reference"],
            "discovery": "models", "video_seconds": [5, 15], "cancel": False},
    "minimax_video": {"implemented": ["video_text", "video_first_last", "video_reference"],
                      "discovery": "tasks_read_only", "video_seconds": [5, 15], "resolutions": ["2K", "768P"], "cancel": False},
    "minimax_audio": {"implemented": ["voice_system", "music_instrumental"], "discovery": "system_voices", "cancel": False},
    "custom": {"implemented": [], "discovery": None, "cancel": False},
}


class ModelEntry(BaseModel):
    uid: str = Field(default_factory=uid)
    id: str = Field(min_length=1, max_length=200)
    name: str = ""
    capability: Literal["text", "vision", "image", "video", "voice", "music", "sfx"]
    parameters: dict = Field(default_factory=dict)

    @field_validator("parameters")
    @classmethod
    def no_credentials(cls, value):
        def check(item):
            if isinstance(item, dict):
                for name, child in item.items():
                    if str(name).lower().replace("-", "_") in {"api_key", "apikey", "authorization", "password", "secret", "access_token", "headers", "base_url"}:
                        raise ValueError("高级参数不能保存凭据、认证头或覆盖连接地址")
                    check(child)
            elif isinstance(item, list):
                for child in item:
                    check(child)
        check(value)
        return value


class ConnectionInput(BaseModel):
    id: str = Field(default_factory=uid, pattern=r"^[A-Za-z0-9_-]{1,80}$")
    name: str = Field(min_length=1, max_length=100)
    protocol: Literal["openai", "ark", "minimax_video", "minimax_audio", "custom"]
    base_url: str
    no_key: bool = False
    api_key: SecretStr | None = Field(default=None, exclude=True)
    clear_key: bool = Field(default=False, exclude=True)
    models: list[ModelEntry] = Field(default_factory=list)

    @field_validator("base_url")
    @classmethod
    def valid_url(cls, value):
        parsed = urlsplit(value.strip())
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username
                or parsed.password or parsed.query or parsed.fragment):
            raise ValueError("请输入不含账号密码、查询参数的 HTTP(S) API 基础地址")
        return value.strip().rstrip("/")


class WindowsVault:
    """Explicit Windows backend: never falls back to plaintext keyring packages."""
    service = "movie-agent.local.api"

    def __init__(self):
        from keyring.backends.Windows import WinVaultKeyring
        self.backend = WinVaultKeyring()

    def get(self, connection_id):
        return self.backend.get_password(self.service, connection_id)

    def set(self, connection_id, key):
        self.backend.set_password(self.service, connection_id, key)

    def delete(self, connection_id):
        if self.get(connection_id):
            self.backend.delete_password(self.service, connection_id)


@dataclass
class Binding:
    connection_id: str
    protocol: str
    base_url: str
    model: str
    parameters: dict
    key: str = field(repr=False)


class Configuration:
    def __init__(self, store: Store, vault=None):
        self.store = store
        self.vault = vault if vault is not None else WindowsVault()

    def public(self):
        config = self.store.setting("models", {"connections": [], "assignments": {}})
        for c in config["connections"]:
            c["has_key"] = bool(self.vault.get(c["id"]))
        return {**config, "protocols": PROTOCOLS, "purposes": PURPOSES, "capabilities": CAPABILITIES,
                "generation_checks": self.store.setting("generation_checks", {})}

    def save(self, value: ConnectionInput):
        data = self.store.setting("models", {"connections": [], "assignments": {}})
        connection = value.model_dump()
        if value.no_key or value.clear_key:
            self.vault.delete(value.id)
        elif value.api_key and value.api_key.get_secret_value().strip():
            self.vault.set(value.id, value.api_key.get_secret_value().strip())
        data["connections"] = [c for c in data["connections"] if c["id"] != value.id] + [connection]
        self._clean(data)
        self.store.save_setting("models", data)
        return self.public()

    def delete(self, connection_id):
        data = self.store.setting("models", {"connections": [], "assignments": {}})
        self.vault.delete(connection_id)
        data["connections"] = [c for c in data["connections"] if c["id"] != connection_id]
        self._clean(data)
        self.store.save_setting("models", data)
        return self.public()

    @staticmethod
    def _clean(data):
        valid = {f'{c["id"]}/{m["uid"]}': m["capability"] for c in data["connections"] for m in c["models"]}
        data["assignments"] = {p: ref for p, ref in data["assignments"].items()
                               if p in PURPOSES and valid.get(ref) == PURPOSES[p]}

    def assign(self, assignments):
        data = self.store.setting("models", {"connections": [], "assignments": {}})
        data["assignments"] = assignments
        self._clean(data)
        if {k: v for k, v in assignments.items() if v} != data["assignments"]:
            raise ValueError("模型用途与能力不匹配，或连接已被移除")
        self.store.save_setting("models", data)
        return self.public()

    def connection(self, connection_id):
        data = self.store.setting("models", {"connections": [], "assignments": {}})
        for c in data["connections"]:
            if c["id"] == connection_id:
                return c
        raise ValueError("服务连接不存在")

    def binding(self, purpose):
        data = self.store.setting("models", {"connections": [], "assignments": {}})
        ref = data["assignments"].get(purpose)
        if not ref:
            raise ValueError(f"请在模型设置中分配 {purpose} 用途")
        connection_id, model_uid = ref.split("/", 1)
        c = self.connection(connection_id)
        m = next((m for m in c["models"] if m["uid"] == model_uid), None)
        if not m:
            raise ValueError("所选模型已被移除")
        key = self.vault.get(connection_id) or ""
        if not key and not c["no_key"]:
            raise ValueError("请在模型设置中保存 API Key")
        return Binding(c["id"], c["protocol"], c["base_url"], m["id"], m.get("parameters", {}), key)

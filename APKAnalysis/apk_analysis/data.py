import abc
import dataclasses
from typing import Optional

from dataclasses_json import DataClassJsonMixin, config


@dataclasses.dataclass(frozen=True)
class ManifestData(DataClassJsonMixin):
    application_name: str = dataclasses.field(metadata=config(field_name="applicationName"))
    package_name: str = dataclasses.field(metadata=config(field_name="packageName"))
    min_sdk_version: int = dataclasses.field(metadata=config(field_name="minSDKVersion"))
    target_sdk_version: int = dataclasses.field(metadata=config(field_name="targetSDKVersion"))
    version_code: int = dataclasses.field(metadata=config(field_name="versionCode"))
    version_name: str = dataclasses.field(metadata=config(field_name="versionName"))
    use_permissions: list[str] = dataclasses.field(metadata=config(field_name="usePermissions"))


@dataclasses.dataclass(frozen=True)
class APKStrings(DataClassJsonMixin):
    ipv4: list[str]
    uris: list[str]
    embedded_strings: list[str] = dataclasses.field(metadata=config(field_name="embeddedStrings"))
    layout_strings: list[str] = dataclasses.field(metadata=config(field_name="layoutStrings"))
    res_strings: dict[str, str] = dataclasses.field(metadata=config(field_name="resStrings"))
    array_strings: dict[str, list[str]] = dataclasses.field(metadata=config(field_name="arrayStrings"))


@dataclasses.dataclass(frozen=True)
class DexAPIPermissions(DataClassJsonMixin):
    api_call_permissions: list[str] = dataclasses.field(metadata=config(field_name="apiCallPermissions"))
    content_provider_permissions: list[str] = dataclasses.field(metadata=config(field_name="contentProviderPermissions"))


@dataclasses.dataclass(frozen=True)
class Tracker(DataClassJsonMixin):
    id: str
    name: str
    website: Optional[str]
    categories: list[str]

    def __hash__(self):
        return hash(id)

    def __eq__(self, other):
        return isinstance(other, Tracker) and other.id == self.id


@dataclasses.dataclass(frozen=True)
class APKAnalysisResult(DataClassJsonMixin):
    manifest: ManifestData
    strings: APKStrings
    dex_api_permissions: DexAPIPermissions = dataclasses.field(metadata=config(field_name="dexAPIPermissions"))
    trackers: list[Tracker]


@dataclasses.dataclass(frozen=True)
class PermissionComment(DataClassJsonMixin):
    deprecated: bool
    system_api: bool
    test_api: bool
    hide: bool


@dataclasses.dataclass(frozen=True)
class AndroidPermissionGroup(DataClassJsonMixin):
    name: str
    description: Optional[str]
    label: Optional[str]
    priority: Optional[int]
    comment: PermissionComment

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, AndroidPermissionGroup):
            return self.name == other.name
        return False


@dataclasses.dataclass(frozen=True)
class AndroidPermission(DataClassJsonMixin):
    name: str
    description: Optional[str]
    label: Optional[str]
    group: Optional[str]
    protection_levels: list[str]
    permission_flags: list[str]
    priority: Optional[int]
    comment: PermissionComment

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, AndroidPermission):
            return self.name == other.name
        return False


@dataclasses.dataclass(frozen=True)
class AndroidPermissions(DataClassJsonMixin):
    groups: dict[str, AndroidPermissionGroup]
    permissions: dict[str, AndroidPermission]

    def list_groups(self) -> list[AndroidPermissionGroup]:
        return [i for _, i in sorted(self.groups.items(), key=lambda x: x[0])]

    def list_permissions(self) -> list[AndroidPermission]:
        return [i for _, i in sorted(self.permissions.items(), key=lambda x: x[0])]


@dataclasses.dataclass(frozen=True)
class AndroidUriPermission(DataClassJsonMixin):
    type: str
    path: str


@dataclasses.dataclass(frozen=True)
class AndroidProvider(DataClassJsonMixin):
    package: str
    name: str
    authorities: list[str]
    exported: bool
    read_permission: Optional[str]
    write_permission: Optional[str]
    has_uri_permission: bool
    grant_uri_permissions: list[AndroidUriPermission]

    @property
    def all_permissions(self) -> list[str]:
        result = []
        if self.read_permission is not None:
            result.append(self.read_permission)
        if self.write_permission is not None:
            result.append(self.write_permission)
        return result

    def need_permission(self) -> bool:
        return self.read_permission is not None or self.write_permission is not None

    def __hash__(self) -> int:
        return hash(frozenset(self.authorities))


@dataclasses.dataclass(frozen=True)
class AndroidAPI(abc.ABC):
    class_name: str
    name: str
    signature: str
    dalvik_descriptor: str
    api_type: str = dataclasses.field(init=False, default="unknown", metadata=config(field_name="type"))

    @staticmethod
    def api_type_decoder(content: any) -> 'AndroidAPI':
        if isinstance(content, dict) and "type" in content:
            if content["type"] == "method":
                return AndroidAPIMethod.from_dict(content)
            elif content["type"] == "field":
                return AndroidAPIField.from_dict(content)
        raise NotImplementedError(f"Unsupported api type: {content}")


@dataclasses.dataclass(frozen=True)
class AndroidAPIMethod(AndroidAPI, DataClassJsonMixin):
    args: list[str]
    return_value: str
    api_type: str = dataclasses.field(init=False, default="method", metadata=config(field_name="type"))


@dataclasses.dataclass(frozen=True)
class AndroidAPIField(AndroidAPI, DataClassJsonMixin):
    field_type: str
    api_type: str = dataclasses.field(init=False, default="field", metadata=config(field_name="type"))


@dataclasses.dataclass(frozen=True)
class APIPermissionGroup(DataClassJsonMixin):
    permissions: list[str]
    any_of: bool
    conditional: bool


@dataclasses.dataclass(frozen=True)
class AndroidAPIPermission(DataClassJsonMixin):
    api: AndroidAPI = dataclasses.field(metadata=config(decoder=AndroidAPI.api_type_decoder))
    permission_groups: list[APIPermissionGroup]


@dataclasses.dataclass(frozen=True)
class AndroidAPILevel(DataClassJsonMixin):
    name: Optional[str]
    version_range: str
    versions: list[str]
    api: int
    ndk: Optional[int]

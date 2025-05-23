from ..types import Mount
from .base import DictType


def access_mode_type_error(param, param_value, expected):
    return TypeError(
        f"Invalid type for {param} param: expected {expected} "
        f"but found {type(param_value)}"
    )


class CapacityRange(DictType):
    def __init__(self, **kwargs):
        limit_bytes = kwargs.get("limit_bytes", kwargs.get("LimitBytes"))
        required_bytes = kwargs.get("required_bytes", kwargs.get("RequiredBytes"))

        if limit_bytes is not None:
            if not isinstance(limit_bytes, int):
                raise access_mode_type_error("limit_bytes", limit_bytes, "int")
        if required_bytes is not None:
            if not isinstance(required_bytes, int):
                raise access_mode_type_error("required_bytes", required_bytes, "int")

        super().__init__({"RequiredBytes": required_bytes, "LimitBytes": limit_bytes})

    @property
    def limit_bytes(self):
        return self["LimitBytes"]

    @property
    def required_bytes(self):
        return self["RequiredBytes"]

    @limit_bytes.setter
    def limit_bytes(self, value):
        if not isinstance(value, int):
            raise access_mode_type_error("limit_bytes", value, "int")
        self["LimitBytes"] = value

    @required_bytes.setter
    def required_bytes(self, value):
        if not isinstance(value, int):
            raise access_mode_type_error("required_bytes", value, "int")
        self["RequiredBytes"]


class Secret(DictType):
    def __init__(self, **kwargs):
        key = kwargs.get("key", kwargs.get("Key"))
        secret = kwargs.get("secret", kwargs.get("Secret"))

        if key is not None:
            if not isinstance(key, str):
                raise access_mode_type_error("key", key, "str")
        if secret is not None:
            if not isinstance(secret, str):
                raise access_mode_type_error("secret", secret, "str")

        super().__init__({"Key": key, "Secret": secret})

    @property
    def key(self):
        return self["Key"]

    @property
    def secret(self):
        return self["Secret"]

    @key.setter
    def key(self, value):
        if not isinstance(value, str):
            raise access_mode_type_error("key", value, "str")
        self["Key"] = value

    @secret.setter
    def secret(self, value):
        if not isinstance(value, str):
            raise access_mode_type_error("secret", value, "str")
        self["Secret"]


class AccessibilityRequirement(DictType):
    def __init__(self, **kwargs):
        requisite = kwargs.get("requisite", kwargs.get("Requisite"))
        preferred = kwargs.get("preferred", kwargs.get("Preferred"))

        if requisite is not None:
            if not isinstance(requisite, list):
                raise access_mode_type_error("requisite", requisite, "list")
            self["Requisite"] = requisite

        if preferred is not None:
            if not isinstance(preferred, list):
                raise access_mode_type_error("preferred", preferred, "list")
            self["Preferred"] = preferred

        super().__init__({"Requisite": requisite, "Preferred": preferred})

    @property
    def requisite(self):
        return self["Requisite"]

    @property
    def preferred(self):
        return self["Preferred"]

    @requisite.setter
    def requisite(self, value):
        if not isinstance(value, list):
            raise access_mode_type_error("requisite", value, "list")
        self["Requisite"] = value

    @preferred.setter
    def preferred(self, value):
        if not isinstance(value, list):
            raise access_mode_type_error("preferred", value, "list")
        self["Preferred"] = value


class AccessMode(dict):
    def __init__(
        self,
        scope=None,
        sharing=None,
        mount_volume=None,
        availabilty=None,
        secrets=None,
        accessibility_requirements=None,
        capacity_range=None,
    ):
        if scope is not None:
            if not isinstance(scope, str):
                raise access_mode_type_error("scope", scope, "str")
            self["Scope"] = scope

        if sharing is not None:
            if not isinstance(sharing, str):
                raise access_mode_type_error("sharing", sharing, "str")
            self["Sharing"] = sharing

        if mount_volume is not None:
            if not isinstance(mount_volume, str):
                raise access_mode_type_error("mount_volume", mount_volume, "str")
            self["MountVolume"] = Mount.parse_mount_string(mount_volume)

        if availabilty is not None:
            if not isinstance(availabilty, str):
                raise access_mode_type_error("availabilty", availabilty, "str")
            self["Availabilty"] = availabilty

        if secrets is not None:
            if not isinstance(secrets, list):
                raise access_mode_type_error("secrets", secrets, "list")
            self["Secrets"] = []
            for secret in secrets:
                if not isinstance(secret, Secret):
                    secret = Secret(**secret)
                self["Secrets"].append(secret)

        if capacity_range is not None:
            if not isinstance(capacity_range, CapacityRange):
                capacity_range = CapacityRange(**capacity_range)
            self["CapacityRange"] = capacity_range

        if accessibility_requirements is not None:
            if not isinstance(accessibility_requirements, AccessibilityRequirement):
                accessibility_requirements = AccessibilityRequirement(
                    **accessibility_requirements
                )
            self["AccessibilityRequirements"] = accessibility_requirements


class ClusterVolumeSpec(dict):
    def __init__(self, group=None, access_mode=None):
        if group:
            self["Group"] = group

        if access_mode:
            if not isinstance(access_mode, AccessMode):
                raise TypeError("access_mode must be a AccessMode")
            self["AccessMode"] = access_mode

    @property
    def group(self):
        return self["Group"]

    @property
    def access_mode(self):
        return self["AccessMode"]

from functools import lru_cache

from mgeo_geographic_elements_tagging_chinese_base import MGeoElementsTagging

from app.services.constants import RAW_FIELDS


class AddressModelService:
    def __init__(self) -> None:
        self._recognizer: MGeoElementsTagging | None = None

    @property
    def recognizer(self) -> MGeoElementsTagging:
        if self._recognizer is None:
            self._recognizer = MGeoElementsTagging()
        return self._recognizer

    def parse(self, address: str) -> dict[str, str]:
        if not isinstance(address, str) or not address.strip():
            return {field: "" for field in RAW_FIELDS}

        result = self.recognizer.get_elements_tagging(address.strip())
        return {field: str(result.get(field) or "") for field in RAW_FIELDS}


@lru_cache(maxsize=1)
def get_model_service() -> AddressModelService:
    return AddressModelService()

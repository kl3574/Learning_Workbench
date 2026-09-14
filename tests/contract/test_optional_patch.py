import jsonschema
import pytest
from pydantic import ValidationError

from services.api.app.dto import PreferencesPatch


def test_optional_patch_omission_and_null_match_machine_contract():
    schema = PreferencesPatch.model_json_schema()
    jsonschema.validate({}, schema)
    assert PreferencesPatch.model_validate({}).model_fields_set == set()
    for field in schema["properties"]:
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({field: None}, schema)
        with pytest.raises(ValidationError):
            PreferencesPatch.model_validate({field: None})

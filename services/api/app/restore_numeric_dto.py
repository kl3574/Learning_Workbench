"""Closed Restore numeric contracts, PRODUCT_DESIGN §20.14.

These models check shape and intrinsic relationships. The Restore owner must
verify exact original body slices, decimal values, provenance and history in
its transaction; validated client JSON is neither material proof nor approval.
"""
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from packages.contracts import domain_models as dm
from .authoring_dto import (
    AuthoringBlockRef, AuthoringCandidate, AuthoringModel, NonBlank,
    NumericCheckView, NumericPlan, WorkedExampleSymbol,
)


class RestoreNumericSourceSpan(AuthoringModel):
    start_codepoint: Annotated[int, Field(ge=0, le=399999)]
    end_codepoint: Annotated[int, Field(ge=1, le=400000)]
    quote: Annotated[NonBlank, Field(max_length=512)]

    @model_validator(mode='after')
    def bounded_span(self) -> Self:
        if not 1 <= self.end_codepoint - self.start_codepoint <= 512:
            raise ValueError('source span must be a nonempty bounded codepoint interval')
        return self


class RestoreNumericVariableBinding(AuthoringModel):
    variable_name: Annotated[str, Field(pattern=r'^[A-Za-z][A-Za-z0-9_]{0,31}$')]
    value_source: RestoreNumericSourceSpan


class RestoreNumericAssertionBinding(AuthoringModel):
    assertion_id: dm.Id
    expression_source: RestoreNumericSourceSpan
    expected_source: RestoreNumericSourceSpan


class RestoreNumericMaterialWrite(AuthoringModel):
    version: Literal['restore-numeric-material-v1']
    symbols: Annotated[list[WorkedExampleSymbol], Field(min_length=1, max_length=64)]
    plan: NumericPlan
    variable_bindings: Annotated[list[RestoreNumericVariableBinding], Field(max_length=32)]
    assertion_bindings: Annotated[list[RestoreNumericAssertionBinding], Field(min_length=1, max_length=32)]
    reason: Annotated[NonBlank, Field(max_length=2000)]

    @model_validator(mode='after')
    def complete_bindings(self) -> Self:
        names = {symbol.name for symbol in self.symbols}
        if len(names) != len(self.symbols):
            raise ValueError('symbol names must be unique')
        variables = {variable.name for variable in self.plan.variables}
        if not variables <= names:
            raise ValueError('each numeric variable must be a declared symbol')
        bound_variables = [binding.variable_name for binding in self.variable_bindings]
        bound_assertions = [binding.assertion_id for binding in self.assertion_bindings]
        if len(set(bound_variables)) != len(bound_variables) or set(bound_variables) != variables:
            raise ValueError('each numeric variable requires exactly one source binding')
        if (len(set(bound_assertions)) != len(bound_assertions)
                or set(bound_assertions) != {assertion.id for assertion in self.plan.assertions}):
            raise ValueError('each numeric assertion requires exactly one source binding')
        return self


class RestoreNumericMaterialView(AuthoringModel):
    owner: Literal['authoring_restore']
    candidate: AuthoringCandidate
    restore_record_sha256: dm.Sha256
    source_ref: AuthoringBlockRef
    source_material_sha256: dm.Sha256
    body_sha256: dm.Sha256
    material: RestoreNumericMaterialWrite
    numeric_material_sha256: dm.Sha256


class RestoreNumericCheckPreviewWrite(AuthoringModel):
    candidate: AuthoringCandidate
    material: RestoreNumericMaterialWrite


class RestoreNumericCheckView(NumericCheckView):
    owner: Literal['authoring_restore']
    numeric_material_sha256: dm.Sha256

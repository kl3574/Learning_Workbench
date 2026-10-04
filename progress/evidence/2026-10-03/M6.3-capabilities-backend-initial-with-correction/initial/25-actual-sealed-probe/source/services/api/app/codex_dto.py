"""M6.3 capability read projection from PRODUCT_DESIGN appendix A (2193)."""
from pydantic import Field, model_validator

from packages.contracts import domain_models as dm


class CodexFeatures(dm.StrictModel):
    approvals: bool
    interrupt: bool
    artifacts: bool


class CodexSandboxRoot(dm.StrictModel):
    id: dm.Id
    label: str = Field(min_length=1, max_length=240)


class CodexCapabilities(dm.StrictModel):
    available: bool
    authorized: bool
    adapter_version: str | None = Field(min_length=1, max_length=120)
    sandbox_roots: list[CodexSandboxRoot]
    capabilities: CodexFeatures

    @model_validator(mode='after')
    def actual_capabilities(self) -> 'CodexCapabilities':
        if not self.available and (self.authorized or self.sandbox_roots or any(self.capabilities.model_dump().values())):
            raise ValueError('An unavailable broker cannot grant capabilities or sandbox roots.')
        if self.available and (self.adapter_version is None or not self.adapter_version.strip()):
            raise ValueError('An available broker must identify its adapter.')
        if len({item.id for item in self.sandbox_roots}) != len(self.sandbox_roots):
            raise ValueError('Sandbox identities must be unique.')
        if any(not item.label.strip() for item in self.sandbox_roots):
            raise ValueError('Sandbox labels must be nonblank.')
        return self

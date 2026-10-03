"""Strict product shape is separate from upstream CLI protocol claims."""
from copy import deepcopy

from pydantic import ValidationError
import pytest

from services.api.app.codex_dto import CodexCapabilities


def supported():
    return {'available':True,'authorized':False,'adapter_version':'codex-cli/0.160.0',
            'sandbox_roots':[{'id':'workspace_default','label':'隔离 Broker'}],
            'capabilities':{'approvals':False,'interrupt':False,'artifacts':False}}


@pytest.mark.parametrize('field', ['available','authorized','adapter_version','sandbox_roots','capabilities'])
def test_capability_projection_requires_every_declared_field(field):
    value = supported()
    del value[field]
    with pytest.raises(ValidationError):
        CodexCapabilities.model_validate(value)


@pytest.mark.parametrize('path,value', [(('available',),1),(('authorized',),'false'),
    (('capabilities','approvals'),1),(('capabilities','interrupt'),None),
    (('capabilities','artifacts'),0),(('adapter_version',),None),
    (('adapter_version',),' '),(('sandbox_roots',),[{'id':'root','label':' '}]),
    (('sandbox_roots',),[{'id':'root','label':'one'},{'id':'root','label':'two'}])])
def test_untrusted_product_projection_rejects_coercion_and_inconsistent_states(path, value):
    sample = supported()
    parent = sample
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = value
    with pytest.raises(ValidationError):
        CodexCapabilities.model_validate(sample)


@pytest.mark.parametrize('scope', ['top','features','root'])
def test_private_or_unknown_fields_cannot_cross_the_product_boundary(scope):
    sample = supported()
    target = {'top':sample,'features':sample['capabilities'],'root':sample['sandbox_roots'][0]}[scope]
    target['codexHome'] = '/synthetic/private-path'
    with pytest.raises(ValidationError):
        CodexCapabilities.model_validate(sample)


def test_unavailable_cannot_grant_execution_or_root_authority():
    sample = {'available':False,'authorized':False,'adapter_version':None,'sandbox_roots':[],
              'capabilities':{'approvals':False,'interrupt':False,'artifacts':False}}
    assert CodexCapabilities.model_validate(sample).model_dump() == sample
    for field in ('approvals','interrupt','artifacts'):
        changed = deepcopy(sample)
        changed['capabilities'][field] = True
        with pytest.raises(ValidationError):
            CodexCapabilities.model_validate(changed)
    for field, value in [('authorized',True),('sandbox_roots',[{'id':'root','label':'unavailable'}])]:
        changed = {**sample,field:value}
        with pytest.raises(ValidationError):
            CodexCapabilities.model_validate(changed)

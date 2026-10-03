"""Pinned upstream results are not product execution grants."""
import pytest
from services.api.app.infrastructure import codex_probe
from services.api.app.application.errors import ApiError

INIT = {'codexHome':'/synthetic/private/home','platformFamily':'unix','platformOs':'linux','userAgent':'codex_cli_rs/0.160.0'}


def test_real_protocol_projection_discards_private_fields_and_does_not_grant_tools():
    result = codex_probe.project_capabilities(INIT, {'account':None,'requiresOpenaiAuth':True,'workspaceRouting':None})
    assert result == {'available':True,'authorized':False,'adapter_version':'codex-cli/0.160.0',
        'sandbox_roots':[{'id':'workspace_default','label':'此工作区的隔离 Broker 目录'}],
        'capabilities':{'approvals':False,'interrupt':False,'artifacts':False}}
    signed_in = codex_probe.project_capabilities(INIT, {'account':{'type':'chatgpt','email':'synthetic@example.invalid','planType':'unknown'},'requiresOpenaiAuth':True})
    assert signed_in['authorized'] is True
    assert 'synthetic' not in str(signed_in) and 'email' not in str(signed_in)


@pytest.mark.parametrize('account', [{}, {'account':None}, {'account':None,'requiresOpenaiAuth':0},
    {'account':None,'requiresOpenaiAuth':False}, {'account':None,'requiresOpenaiAuth':True,'workspaceRouting':{}}, {'account':{'type':'apiKey','token':'synthetic'},'requiresOpenaiAuth':True}])
def test_missing_unknown_or_unrecognized_auth_is_an_error_not_unauthorized(account):
    with pytest.raises(ApiError) as error:
        codex_probe.project_capabilities(INIT, account)
    assert error.value.code == 'CODEX_PROTOCOL_INVALID'

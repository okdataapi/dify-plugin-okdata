from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from okdata_api import client


class OkdataProvider(ToolProvider):
    """Checks the okdata API key with GET /v1/account, which is free and returns the balance."""

    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        try:
            api_key = client.api_key_from(credentials)
            client.check_key(api_key)
        except client.OkdataError as err:
            raise ToolProviderCredentialValidationError(str(err)) from err

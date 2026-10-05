from unittest.mock import MagicMock, patch

from src.windows_mcp.config import WinRMConnectionConfig
from src.windows_mcp.transports.pypsrp_transport import PyPSRPTransport


def test_pypsrp_transport_returns_text_output():
    config = WinRMConnectionConfig(
        username=r"LAB\test",
        password="secret",
    )

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.execute_ps.return_value = (
        "LAB-PC",
        MagicMock(),
        False,
    )

    with patch(
        "src.windows_mcp.transports.pypsrp_transport.Client",
        return_value=mock_client,
    ):
        transport = PyPSRPTransport(config)

        result = transport.run_powershell(
            target="LAB-PC",
            script=r"$env:COMPUTERNAME",
        )

    assert result == "LAB-PC"
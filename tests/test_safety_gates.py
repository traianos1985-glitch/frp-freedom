import logging
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.bypass.bypass_manager import BypassManager
from src.bypass.types import BypassResult
from src.core.device_manager import DeviceManager
from src.core.samsung_adb_enabler import SamsungADBEnabler
from src.bypass.adb_exploits import ADBExploitManager
from src.bypass.interface_exploits import InterfaceExploitManager
from src.bypass.system_exploits import SystemExploitManager
from src.bypass.hardware_exploits import HardwareExploitManager


def test_bypass_dispatch_is_blocked_before_any_executor_runs():
    manager = BypassManager.__new__(BypassManager)
    manager.logger = logging.getLogger(__name__)
    manager.adb_exploits = Mock()
    manager.interface_exploits = Mock()
    manager.system_exploits = Mock()
    manager.hardware_exploits = Mock()
    manager.progress_callback = None
    callback = Mock()

    result = manager.execute_bypass(
        SimpleNamespace(serial="unit-test-device"), "adb_setup_wizard", callback
    )

    assert result["result"] is BypassResult.FAILED
    assert result["details"] == {"execution_state": "blocked", "frp_status": "unknown"}
    assert "No device command was sent" in result["message"]
    for executor in (
        manager.adb_exploits,
        manager.interface_exploits,
        manager.system_exploits,
        manager.hardware_exploits,
    ):
        executor.execute_method.assert_not_called()
    callback.assert_called_once()


def test_direct_exploit_dispatchers_are_fail_closed():
    device = SimpleNamespace(serial="unit-test-device")
    managers = (
        ADBExploitManager,
        InterfaceExploitManager,
        SystemExploitManager,
        HardwareExploitManager,
    )

    for manager_type in managers:
        manager = manager_type.__new__(manager_type)
        manager.logger = logging.getLogger(__name__)
        result = manager.execute_method(device, "test-method", Mock())
        assert result["result"] is BypassResult.FAILED
        assert result["details"]["execution_state"] == "blocked"
        assert "No device command was sent" in result["message"]


def test_frp_diagnostic_never_infers_state_from_device_access():
    manager = DeviceManager.__new__(DeviceManager)
    manager.logger = logging.getLogger(__name__)

    assert manager._check_frp_status("unit-test-device") == "unknown"


def test_samsung_at_adb_activation_fails_without_opening_serial_port():
    enabler = SamsungADBEnabler.__new__(SamsungADBEnabler)
    enabler.logger = logging.getLogger(__name__)
    callback = Mock()

    with patch("src.core.samsung_adb_enabler.serial.Serial") as serial_open:
        assert enabler.enable_adb("/dev/test-port", callback) is False

    serial_open.assert_not_called()
    callback.assert_called_once()

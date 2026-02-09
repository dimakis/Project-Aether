"""Integration tests for sandbox isolation.

Verifies that gVisor policies are properly enforced:
- Network isolation
- Filesystem restrictions
- Resource limits
- Timeout enforcement

These tests require Podman with gVisor (runsc) runtime configured.
Skip if not available.
"""

import pytest

from src.sandbox.policies import (
    NetworkPolicy,
    PolicyLevel,
    ResourceLimits,
    SandboxPolicy,
    get_policy,
)
from src.sandbox.runner import SandboxRunner


@pytest.fixture
async def runner():
    """Create sandbox runner and check if it's available."""
    runner = SandboxRunner()
    status = await runner.check_runtime()

    if not status["podman_available"]:
        pytest.skip("Podman not available")

    # For sandbox tests, we need gVisor
    # But we can run basic isolation tests without it
    return runner


@pytest.fixture
def network_test_script():
    """Script that tries to access the network."""
    return """
import socket
import sys

try:
    # Try to connect to Google DNS
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex(('8.8.8.8', 53))
    sock.close()

    if result == 0:
        print("NETWORK_ACCESS_ALLOWED")
        sys.exit(0)
    else:
        print("NETWORK_BLOCKED")
        sys.exit(0)
except Exception as e:
    print(f"NETWORK_BLOCKED: {e}")
    sys.exit(0)
"""


@pytest.fixture
def filesystem_write_script():
    """Script that tries to write to various locations."""
    return """
import sys
import os

results = []

# Try to write to root filesystem
test_paths = [
    '/etc/test.txt',
    '/var/test.txt',
    '/home/test.txt',
    '/root/test.txt',
]

for path in test_paths:
    try:
        with open(path, 'w') as f:
            f.write('test')
        results.append(f"WRITE_ALLOWED: {path}")
        os.remove(path)
    except (PermissionError, OSError) as e:
        results.append(f"WRITE_BLOCKED: {path}")

# /tmp should be writable
try:
    with open('/tmp/test.txt', 'w') as f:
        f.write('test')
    results.append("WRITE_ALLOWED: /tmp/test.txt")
    os.remove('/tmp/test.txt')
except Exception:
    results.append("WRITE_BLOCKED: /tmp/test.txt")

print("\\n".join(results))
"""


@pytest.fixture
def memory_test_script():
    """Script that tries to allocate excessive memory."""
    return """
import sys

try:
    # Try to allocate 2GB (should fail with 512MB limit)
    data = bytearray(2 * 1024 * 1024 * 1024)
    print("MEMORY_ALLOCATION_SUCCESS")
except MemoryError:
    print("MEMORY_LIMIT_ENFORCED")
except Exception as e:
    print(f"ERROR: {e}")
"""


@pytest.fixture
def cpu_intensive_script():
    """Script that runs CPU-intensive computation."""
    return """
import time

start = time.time()
# Busy loop
count = 0
while time.time() - start < 10:
    count += 1

print(f"CPU_TEST_COMPLETED: {count} iterations")
"""


class TestNetworkIsolation:
    """Tests for network isolation policies."""

    @pytest.mark.asyncio
    async def test_network_blocked_with_none_policy(self, runner, network_test_script):
        """Network access should be blocked with NetworkPolicy.NONE."""
        status = await runner.check_runtime()
        if not status.get("image_available"):
            pytest.skip("Sandbox image not available")

        policy = SandboxPolicy(
            name="test_no_network",
            level=PolicyLevel.STANDARD,
            network=NetworkPolicy.NONE,
            timeout_seconds=30,
        )

        result = await runner.run(network_test_script, policy=policy)

        if result.exit_code == 125:
            pytest.skip(f"Container failed to start: {result.stderr}")

        # Script should complete (might fail to connect but not crash)
        # The key is network should be blocked
        assert (
            "NETWORK_BLOCKED" in result.stdout
            or result.exit_code != 0
            or "NETWORK_ACCESS_ALLOWED" not in result.stdout
        )

    @pytest.mark.asyncio
    async def test_standard_policy_blocks_network(self, runner, network_test_script):
        """Standard policy should block network access."""
        status = await runner.check_runtime()
        if not status.get("image_available"):
            pytest.skip("Sandbox image not available")

        policy = get_policy("standard")

        result = await runner.run(network_test_script, policy=policy)

        if result.exit_code == 125:
            pytest.skip(f"Container failed to start: {result.stderr}")

        # Network should be blocked
        assert policy.network == NetworkPolicy.NONE
        # Either blocked message or connection failure
        assert "NETWORK_ACCESS_ALLOWED" not in result.stdout


class TestFilesystemIsolation:
    """Tests for filesystem restrictions."""

    @pytest.mark.asyncio
    async def test_readonly_root_filesystem(self, runner, filesystem_write_script):
        """Root filesystem should be read-only."""
        # Check if we can run containers
        status = await runner.check_runtime()
        if not status.get("image_available"):
            pytest.skip(
                "Sandbox image not available - build with: podman build -t aether-sandbox -f infrastructure/podman/Containerfile.sandbox ."
            )

        policy = SandboxPolicy(
            name="test_readonly",
            level=PolicyLevel.STANDARD,
            read_only_root=True,
            timeout_seconds=30,
        )

        result = await runner.run(filesystem_write_script, policy=policy)

        # If container failed to start, skip
        if result.exit_code == 125:
            pytest.skip(f"Container failed to start: {result.stderr}")

        # Protected paths should be blocked
        assert "WRITE_BLOCKED: /etc/test.txt" in result.stdout
        # /tmp should be writable
        assert "WRITE_ALLOWED: /tmp/test.txt" in result.stdout

    @pytest.mark.asyncio
    async def test_temp_dir_available(self, runner):
        """Temp directory should be available for writing."""
        # Check if we can run containers
        status = await runner.check_runtime()
        if not status.get("image_available"):
            pytest.skip("Sandbox image not available")

        script = """
import tempfile
import os

# Create temp file
with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
    f.write('test data')
    temp_path = f.name

# Verify it exists
if os.path.exists(temp_path):
    print("TEMP_DIR_WORKS")
    os.remove(temp_path)
else:
    print("TEMP_DIR_FAILED")
"""
        policy = get_policy("standard")
        result = await runner.run(script, policy=policy)

        # If container failed to start, skip
        if result.exit_code == 125:
            pytest.skip(f"Container failed to start: {result.stderr}")

        assert "TEMP_DIR_WORKS" in result.stdout


class TestResourceLimits:
    """Tests for resource limit enforcement."""

    @pytest.mark.asyncio
    async def test_memory_limit_enforced(self, runner, memory_test_script):
        """Memory limits should be enforced."""
        status = await runner.check_runtime()
        if not status.get("image_available"):
            pytest.skip("Sandbox image not available")

        policy = SandboxPolicy(
            name="test_memory",
            level=PolicyLevel.STANDARD,
            resources=ResourceLimits(memory_mb=256),
            timeout_seconds=30,
        )

        result = await runner.run(memory_test_script, policy=policy)

        if result.exit_code == 125:
            pytest.skip(f"Container failed to start: {result.stderr}")

        # Should either get OOM killed or MemoryError
        assert (
            "MEMORY_LIMIT_ENFORCED" in result.stdout
            or result.exit_code != 0
            or "killed" in result.stderr.lower()
        )

    @pytest.mark.asyncio
    async def test_timeout_enforced(self, runner):
        """Execution timeout should be enforced."""
        status = await runner.check_runtime()
        if not status.get("image_available"):
            pytest.skip("Sandbox image not available")

        script = """
import time
time.sleep(60)  # Sleep for 60 seconds
print("COMPLETED")
"""
        policy = SandboxPolicy(
            name="test_timeout",
            level=PolicyLevel.MINIMAL,
            timeout_seconds=5,  # 5 second timeout
        )

        result = await runner.run(script, policy=policy)

        if result.exit_code == 125:
            pytest.skip(f"Container failed to start: {result.stderr}")

        assert result.timed_out is True
        assert "COMPLETED" not in result.stdout

    def test_policy_levels_have_different_limits(self):
        """Different policy levels should have different resource limits."""
        minimal = get_policy("minimal")
        standard = get_policy("standard")
        extended = get_policy("extended")

        # Verify ascending resource limits
        assert minimal.resources.memory_mb < standard.resources.memory_mb
        assert standard.resources.memory_mb < extended.resources.memory_mb

        assert minimal.timeout_seconds < standard.timeout_seconds
        assert standard.timeout_seconds < extended.timeout_seconds


class TestSecurityCapabilities:
    """Tests for security capability restrictions."""

    @pytest.mark.asyncio
    async def test_no_privilege_escalation(self, runner):
        """Should not be able to escalate privileges."""
        status = await runner.check_runtime()
        if not status.get("image_available"):
            pytest.skip("Sandbox image not available")

        script = """
import os
import sys

# Try to become root
try:
    os.setuid(0)
    print("PRIVILEGE_ESCALATION_SUCCEEDED")
except PermissionError:
    print("PRIVILEGE_ESCALATION_BLOCKED")
except OSError as e:
    print(f"PRIVILEGE_ESCALATION_BLOCKED: {e}")
"""
        policy = get_policy("standard")
        result = await runner.run(script, policy=policy)

        if result.exit_code == 125:
            pytest.skip(f"Container failed to start: {result.stderr}")

        assert "PRIVILEGE_ESCALATION_BLOCKED" in result.stdout

    @pytest.mark.asyncio
    async def test_user_is_nobody(self, runner):
        """Script should run as unprivileged user."""
        status = await runner.check_runtime()
        if not status.get("image_available"):
            pytest.skip("Sandbox image not available")

        script = """
import os
import pwd

uid = os.getuid()
try:
    username = pwd.getpwuid(uid).pw_name
except KeyError:
    username = str(uid)

print(f"USER: {username}")
print(f"UID: {uid}")
"""
        policy = get_policy("standard")
        result = await runner.run(script, policy=policy)

        if result.exit_code == 125:
            pytest.skip(f"Container failed to start: {result.stderr}")

        # Should run as nobody (uid 65534) or similar unprivileged user
        assert "UID: 0" not in result.stdout


class TestPolicyConversion:
    """Tests for policy-to-podman-args conversion."""

    def test_minimal_policy_args(self):
        """Minimal policy should have most restrictive args."""
        policy = get_policy("minimal")
        args = policy.to_podman_args()

        assert "--network=none" in args
        assert "--read-only" in args
        assert "--cap-drop=ALL" in args
        assert "--security-opt=no-new-privileges:true" in args

    def test_memory_limit_in_args(self):
        """Memory limit should be in podman args."""
        policy = SandboxPolicy(
            name="test",
            level=PolicyLevel.STANDARD,
            resources=ResourceLimits(memory_mb=512),
        )
        args = policy.to_podman_args()

        assert "--memory" in args
        assert "512m" in args

    def test_runtime_in_args_when_gvisor_enabled(self):
        """gVisor runtime should be specified when enabled."""
        policy = SandboxPolicy(
            name="test",
            level=PolicyLevel.STANDARD,
            use_gvisor=True,
        )
        args = policy.to_podman_args()

        assert "--runtime" in args
        assert "runsc" in args

    def test_no_runtime_when_gvisor_disabled(self):
        """No runtime specified when gVisor disabled."""
        policy = SandboxPolicy(
            name="test",
            level=PolicyLevel.STANDARD,
            use_gvisor=False,
        )
        args = policy.to_podman_args()

        assert "--runtime" not in args


class TestRuntimeCheck:
    """Tests for runtime availability checking."""

    @pytest.mark.asyncio
    async def test_check_runtime_returns_status(self, runner):
        """check_runtime should return status dict."""
        status = await runner.check_runtime()

        assert "podman_available" in status
        assert "gvisor_available" in status
        assert "image_available" in status
        assert "errors" in status
        assert isinstance(status["errors"], list)

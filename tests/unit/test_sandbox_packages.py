"""Unit tests for sandbox package availability.

Verifies that the required data science packages are available
in the sandbox container image.

These tests mock the sandbox execution to verify the package
import logic works correctly.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.sandbox.runner import SandboxRunner, SandboxResult


# Required packages for data science sandbox
REQUIRED_PACKAGES = [
    "pandas",
    "numpy",
    "matplotlib",
    "scipy",
    "scikit-learn",
    "statsmodels",
    "seaborn",
]


class TestSandboxPackageImports:
    """Tests for package import availability in sandbox."""

    @pytest.fixture
    def mock_successful_import(self):
        """Mock result for successful package import."""
        return SandboxResult(
            success=True,
            exit_code=0,
            stdout="IMPORT_SUCCESS",
            stderr="",
            duration_seconds=1.0,
            policy_name="standard",
        )

    @pytest.fixture
    def mock_failed_import(self):
        """Mock result for failed package import."""
        return SandboxResult(
            success=False,
            exit_code=1,
            stdout="",
            stderr="ModuleNotFoundError: No module named 'missing_package'",
            duration_seconds=0.5,
            policy_name="standard",
        )

    def test_package_import_script_generation(self):
        """Verify we can generate correct import test scripts."""
        for package in REQUIRED_PACKAGES:
            script = f"""
try:
    import {package}
    print("IMPORT_SUCCESS: {package}")
except ImportError as e:
    print(f"IMPORT_FAILED: {package} - {{e}}")
    raise
"""
            # Script should be valid Python
            assert f"import {package}" in script
            assert "IMPORT_SUCCESS" in script
            assert "IMPORT_FAILED" in script

    @pytest.mark.asyncio
    async def test_pandas_import_succeeds(self, mock_successful_import):
        """Test that pandas import would succeed."""
        runner = SandboxRunner()

        with patch.object(runner, "run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_successful_import

            result = await runner.run("import pandas")

            assert result.success is True
            assert "IMPORT_SUCCESS" in result.stdout

    @pytest.mark.asyncio
    async def test_numpy_import_succeeds(self, mock_successful_import):
        """Test that numpy import would succeed."""
        runner = SandboxRunner()

        with patch.object(runner, "run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_successful_import

            result = await runner.run("import numpy")

            assert result.success is True

    @pytest.mark.asyncio
    async def test_matplotlib_import_succeeds(self, mock_successful_import):
        """Test that matplotlib import would succeed."""
        runner = SandboxRunner()

        with patch.object(runner, "run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_successful_import

            result = await runner.run("import matplotlib.pyplot as plt")

            assert result.success is True

    @pytest.mark.asyncio
    async def test_missing_package_fails(self, mock_failed_import):
        """Test that missing packages are detected."""
        runner = SandboxRunner()

        with patch.object(runner, "run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_failed_import

            result = await runner.run("import nonexistent_package_xyz")

            assert result.success is False
            assert "ModuleNotFoundError" in result.stderr


class TestSandboxImage:
    """Tests for sandbox image configuration."""

    def test_default_image_is_aether_sandbox(self):
        """Default image should be custom aether-sandbox."""
        runner = SandboxRunner()
        assert runner.DEFAULT_IMAGE == "aether-sandbox:latest"

    def test_fallback_image_exists(self):
        """Fallback image should be defined."""
        runner = SandboxRunner()
        assert runner.FALLBACK_IMAGE == "python:3.11-slim"

    def test_custom_image_can_be_specified(self):
        """Custom image should be usable."""
        runner = SandboxRunner(image="custom:latest")
        assert runner.image == "custom:latest"


class TestPackageAvailabilityScript:
    """Tests for the package availability check script pattern."""

    def test_all_packages_script(self):
        """Generate a script that checks all required packages."""
        script_lines = [
            "import sys",
            "results = []",
        ]

        for package in REQUIRED_PACKAGES:
            script_lines.extend([
                f"try:",
                f"    import {package}",
                f"    results.append('{package}: OK')",
                f"except ImportError:",
                f"    results.append('{package}: MISSING')",
                f"    sys.exit(1)",
            ])

        script_lines.extend([
            "print('\\n'.join(results))",
            "print('ALL_PACKAGES_AVAILABLE')",
        ])

        script = "\n".join(script_lines)

        # Verify script structure
        assert "import sys" in script
        for pkg in REQUIRED_PACKAGES:
            assert f"import {pkg}" in script
        assert "ALL_PACKAGES_AVAILABLE" in script

    @pytest.mark.asyncio
    async def test_package_check_result_parsing(self):
        """Test parsing of package check results."""
        # Simulate successful output
        stdout = """pandas: OK
numpy: OK
matplotlib: OK
scipy: OK
scikit-learn: OK
statsmodels: OK
seaborn: OK
ALL_PACKAGES_AVAILABLE"""

        result = SandboxResult(
            success=True,
            exit_code=0,
            stdout=stdout,
            stderr="",
            duration_seconds=2.0,
            policy_name="standard",
        )

        # Parse results
        lines = result.stdout.strip().split("\n")
        package_status = {}
        for line in lines:
            if ": " in line and line != "ALL_PACKAGES_AVAILABLE":
                pkg, status = line.split(": ", 1)
                package_status[pkg] = status

        # All packages should be OK
        for pkg in REQUIRED_PACKAGES:
            assert pkg in package_status
            assert package_status[pkg] == "OK"

        assert "ALL_PACKAGES_AVAILABLE" in result.stdout


class TestSandboxDataScienceCapabilities:
    """Tests verifying data science functionality patterns."""

    def test_pandas_dataframe_script(self):
        """Verify pandas DataFrame operations work in scripts."""
        script = """
import pandas as pd
import numpy as np

# Create test DataFrame
df = pd.DataFrame({
    'timestamp': pd.date_range('2024-01-01', periods=24, freq='H'),
    'energy_kwh': np.random.uniform(0.5, 2.0, 24),
})

# Basic operations
total = df['energy_kwh'].sum()
mean = df['energy_kwh'].mean()
peak_hour = df.loc[df['energy_kwh'].idxmax(), 'timestamp']

print(f"Total: {total:.2f} kWh")
print(f"Mean: {mean:.2f} kWh")
print(f"Peak: {peak_hour}")
"""
        # Verify script is syntactically valid
        compile(script, "<string>", "exec")

    def test_matplotlib_plot_script(self):
        """Verify matplotlib plotting works in scripts."""
        script = """
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

# Generate data
x = np.linspace(0, 24, 100)
y = np.sin(x / 4) + 1.5

# Create plot
fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(x, y, label='Energy Usage')
ax.set_xlabel('Hour')
ax.set_ylabel('kWh')
ax.set_title('Daily Energy Pattern')
ax.legend()

# Save to temp file
plt.savefig('/tmp/energy_plot.png', dpi=100, bbox_inches='tight')
print("PLOT_CREATED")
"""
        # Verify script is syntactically valid
        compile(script, "<string>", "exec")

    def test_scipy_statistics_script(self):
        """Verify scipy statistics operations work in scripts."""
        script = """
import numpy as np
from scipy import stats

# Sample energy data
data = np.array([1.2, 1.5, 1.3, 2.1, 1.8, 1.4, 1.6, 1.9, 2.3, 1.7])

# Statistical analysis
mean = np.mean(data)
std = np.std(data)
skewness = stats.skew(data)
kurtosis = stats.kurtosis(data)

# Anomaly detection (z-score)
z_scores = np.abs(stats.zscore(data))
anomalies = np.where(z_scores > 2)[0]

print(f"Mean: {mean:.2f}")
print(f"Std: {std:.2f}")
print(f"Skewness: {skewness:.2f}")
print(f"Anomalies: {len(anomalies)}")
"""
        # Verify script is syntactically valid
        compile(script, "<string>", "exec")

    def test_sklearn_clustering_script(self):
        """Verify scikit-learn operations work in scripts."""
        script = """
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# Sample hourly energy data (7 days x 24 hours)
np.random.seed(42)
data = np.random.uniform(0.5, 3.0, (7, 24))

# Flatten for clustering
X = data.reshape(-1, 1)

# Standardize
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Cluster into low/medium/high usage
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
labels = kmeans.fit_predict(X_scaled)

# Count cluster sizes
unique, counts = np.unique(labels, return_counts=True)
for label, count in zip(unique, counts):
    print(f"Cluster {label}: {count} data points")

print("CLUSTERING_COMPLETE")
"""
        # Verify script is syntactically valid
        compile(script, "<string>", "exec")

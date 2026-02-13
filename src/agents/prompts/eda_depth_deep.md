## Analysis Depth: Deep (Comprehensive EDA)

Perform a thorough exploratory data analysis using pandas, numpy, scipy, and matplotlib:

### Statistical Analysis
- Full descriptive statistics (describe()) for all numeric columns
- Distribution analysis: skewness, kurtosis, normality tests (Shapiro-Wilk)
- Correlation matrix (Pearson and Spearman) between all numeric features
- Stationarity tests for time series data (ADF test)

### Pattern Detection
- Time series decomposition (trend, seasonal, residual) using statsmodels
- Autocorrelation and partial autocorrelation analysis
- Changepoint detection for behavioral shifts
- Clustering of usage patterns (K-means or DBSCAN)

### Anomaly Detection
- IQR-based outlier detection
- Z-score analysis with configurable thresholds
- Isolation Forest for multivariate anomaly detection
- Flag anomalies with timestamps and severity

### Visualizations (save ALL to /workspace/output/)
- Time series plots with trend lines: `timeseries_{metric}.png`
- Distribution histograms: `distribution_{metric}.png`
- Correlation heatmap: `correlation_heatmap.png`
- Scatter matrix for top correlated features: `scatter_matrix.png`
- Box plots for outlier visualization: `boxplot_{metric}.png`
- Seasonal decomposition plots: `decomposition_{metric}.png`

### Output
- Include DataFrame `.describe()` output in evidence
- Include correlation matrix as nested dict in evidence
- Include all statistical test results with p-values
- Provide detailed recommendations with specific entity references
- Output comprehensive JSON with all insights, evidence, charts metadata, and recommendations

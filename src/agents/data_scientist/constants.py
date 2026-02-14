"""Constants for Data Scientist agent."""

from src.graph.state import AnalysisType

# Analysis types that use behavioral (logbook) data vs energy (history) data
BEHAVIORAL_ANALYSIS_TYPES = {
    AnalysisType.BEHAVIOR_ANALYSIS,
    AnalysisType.AUTOMATION_ANALYSIS,
    AnalysisType.AUTOMATION_GAP_DETECTION,
    AnalysisType.CORRELATION_DISCOVERY,
    AnalysisType.DEVICE_HEALTH,
}

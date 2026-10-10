"""AGI Analyst Workspace (AWS) — internal institutional terminal.

Consumes KIP/RSP/engines/CRE/RMS/Replay. Creates no new research logic.
Architecture v1.0.1 locked. No engine redesign.
"""

from app.aws.flags import AwsFlags
from app.aws.service import AwsService

__all__ = ["AwsFlags", "AwsService"]

"""Base pipeline stage — abstract interface for all pipeline stages.

Every pipeline stage (TrendResearcher, ContentGenerator, etc.)
inherits from BaseStage and implements the execute() method.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod

from app.core.models.pipeline import (
    FailureStrategy,
    PipelineContext,
    StageResult,
    StageStatus,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


class BaseStage(ABC):
    """Abstract base class for pipeline stages.

    Every stage in the automation pipeline must:
    1. Have a unique `name` identifier.
    2. Implement `execute(context)` with its core logic.
    3. Optionally override `validate_input()` for pre-checks.
    4. Optionally override `on_failure()` for custom error handling.

    The Orchestrator calls stages in this lifecycle:
        validate_input → execute → (on_failure if error)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this stage.

        Returns:
            Stage name string (e.g., 'trend_researcher', 'content_generator').
        """
        ...

    @abstractmethod
    async def execute(self, context: PipelineContext) -> StageResult:
        """Execute the stage's core logic.

        Args:
            context: Shared pipeline context with inputs and outputs.

        Returns:
            StageResult with status, data, and timing.
        """
        ...

    async def validate_input(self, context: PipelineContext) -> bool:
        """Validate that required inputs are available in context.

        Override this in concrete stages to add pre-execution checks.
        Default implementation always returns True.

        Args:
            context: Pipeline context to validate.

        Returns:
            True if inputs are valid, False otherwise.
        """
        return True

    def on_failure(
        self, context: PipelineContext, error: Exception
    ) -> FailureStrategy:
        """Determine what to do when this stage fails.

        Override in concrete stages for custom failure handling.
        Default behavior is ABORT (stop the pipeline).

        Args:
            context: Pipeline context at time of failure.
            error: The exception that caused the failure.

        Returns:
            FailureStrategy indicating how to proceed.
        """
        return FailureStrategy.ABORT

    async def run(self, context: PipelineContext) -> StageResult:
        """Execute the full stage lifecycle: validate → execute → handle errors.

        This method is called by the Orchestrator. It wraps the
        stage's execute() with validation, timing, and error handling.

        Args:
            context: Shared pipeline context.

        Returns:
            StageResult from execution.
        """
        logger.info(
            "stage starting",
            stage=self.name,
            run_id=str(context.run_id),
        )

        # Validate inputs
        if not await self.validate_input(context):
            result = StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                error="Input validation failed",
            )
            context.add_stage_result(result)
            logger.warning(
                "stage skipped — input validation failed",
                stage=self.name,
                run_id=str(context.run_id),
            )
            return result

        # Execute with timing
        start_time = time.monotonic()
        try:
            result = await self.execute(context)
            result.duration_seconds = time.monotonic() - start_time
            context.add_stage_result(result)

            logger.info(
                "stage completed",
                stage=self.name,
                status=result.status.value,
                duration_seconds=round(result.duration_seconds, 2),
                run_id=str(context.run_id),
            )
            return result

        except Exception as exc:
            duration = time.monotonic() - start_time
            result = StageResult(
                stage_name=self.name,
                status=StageStatus.FAILED,
                error=str(exc),
                duration_seconds=duration,
            )
            context.add_stage_result(result)

            logger.error(
                "stage failed",
                stage=self.name,
                error=str(exc),
                duration_seconds=round(duration, 2),
                run_id=str(context.run_id),
                exc_info=True,
            )

            # Let the stage decide how to handle failure
            strategy = self.on_failure(context, exc)
            if strategy == FailureStrategy.ABORT:
                raise
            elif strategy == FailureStrategy.SKIP:
                result.status = StageStatus.SKIPPED
                return result
            else:
                # RETRY — handled by the orchestrator
                raise

from dataclasses import dataclass, replace
from uuid import UUID, uuid4


class InvalidAssessmentResultScoreError(ValueError):
    pass


class InvalidAssessmentResultMaxScoreError(ValueError):
    pass


class InvalidAssessmentResultFeedbackError(ValueError):
    pass


def validate_score(score: int, max_score: int) -> int:
    if type(score) is not int or score < 0 or score > max_score:
        raise InvalidAssessmentResultScoreError
    return score


def validate_max_score(max_score: int) -> int:
    if type(max_score) is not int or max_score <= 0:
        raise InvalidAssessmentResultMaxScoreError
    return max_score


def normalize_feedback(feedback: str | None) -> str | None:
    if feedback is None:
        return None
    if not isinstance(feedback, str):
        raise InvalidAssessmentResultFeedbackError
    return feedback if feedback.strip() else None


@dataclass(frozen=True, slots=True)
class AssessmentResult:
    id: UUID
    attempt_id: UUID
    score: int
    max_score: int
    feedback: str | None

    def __post_init__(self) -> None:
        validate_max_score(self.max_score)
        validate_score(self.score, self.max_score)
        object.__setattr__(self, "feedback", normalize_feedback(self.feedback))

    @classmethod
    def create(
        cls,
        attempt_id: UUID,
        score: int,
        max_score: int,
        feedback: str | None = None,
    ) -> "AssessmentResult":
        return cls(uuid4(), attempt_id, score, max_score, feedback)

    def correct(self, score: int, feedback: str | None) -> "AssessmentResult":
        return replace(
            self,
            score=validate_score(score, self.max_score),
            feedback=normalize_feedback(feedback),
        )

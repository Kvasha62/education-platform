"""Educational Environment application errors."""


class EnvironmentAlreadyExistsError(Exception):
    pass


class EnvironmentNotFoundError(Exception):
    pass


class CourseNotFoundError(Exception):
    pass


class SectionNotFoundError(Exception):
    pass


class LearningUnitNotFoundError(Exception):
    pass

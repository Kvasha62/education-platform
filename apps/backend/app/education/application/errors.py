"""Educational Environment application errors."""


class EnvironmentAlreadyExistsError(Exception):
    pass


class EnvironmentNotFoundError(Exception):
    pass


class CourseNotFoundError(Exception):
    pass


class PublishedCourseNotFoundError(Exception):
    pass


class SectionNotFoundError(Exception):
    pass


class LearningUnitNotFoundError(Exception):
    pass


class ActivityNotFoundError(Exception):
    pass


class LinkedContentNotFoundError(Exception):
    pass


class LinkedContentUnavailableError(Exception):
    pass

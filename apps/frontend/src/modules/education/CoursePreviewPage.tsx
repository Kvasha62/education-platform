import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../../shared/api'
import { ErrorState, LoadingState } from '../../shared/ui'
import { contentApi, contentKeys } from '../content'
import { StudentContentBody } from '../learning'
import { activityApi } from './activityApi'
import type { Activity } from './activityApi'
import { activityContentApi } from './activityContentApi'
import type { ActivityContentReference, ActivityContentScope } from './activityContentApi'
import { activityContentKeys } from './activityContentQueries'
import { activityKeys } from './activityQueries'
import { courseApi } from './courseApi'
import type { Course } from './courseApi'
import { courseKeys } from './courseQueries'
import { learningUnitApi } from './learningUnitApi'
import type { LearningUnit } from './learningUnitApi'
import { learningUnitKeys } from './learningUnitQueries'
import { sectionApi } from './sectionApi'
import type { Section } from './sectionApi'
import { sectionKeys } from './sectionQueries'

const errorMessage = (error: unknown) =>
  error instanceof ApiError || error instanceof Error ? error.message : 'Request failed.'

interface PreviewNavigationProps {
  teacherSpaceId: string
  courseId: string
}

const ContentPreview = ({ reference }: { reference: ActivityContentReference }) => {
  const body = useQuery({
    queryKey: contentKeys.body(reference.id),
    queryFn: () => contentApi.getBody(reference.id),
    retry: false,
  })

  return (
    <article className="student-content">
      <p className="eyebrow">
        {reference.type ?? 'Unavailable Content'} · {reference.status ?? 'unavailable'}
      </p>
      {body.isPending && <LoadingState label="Loading Content body" />}
      {body.isError && <ErrorState message={errorMessage(body.error)} />}
      {body.isSuccess && <StudentContentBody body={body.data} />}
    </article>
  )
}

interface ActivityPreviewProps extends PreviewNavigationProps {
  sectionId: string
  learningUnitId: string
  activity: Activity
}

const ActivityPreview = ({
  activity,
  courseId,
  learningUnitId,
  sectionId,
  teacherSpaceId,
}: ActivityPreviewProps) => {
  const scope: ActivityContentScope = {
    activityId: activity.id,
    courseId,
    learningUnitId,
    sectionId,
    teacherSpaceId,
  }
  const linked = useQuery({
    queryKey: activityContentKeys.linked(scope),
    queryFn: () => activityContentApi.list(scope),
    retry: false,
  })

  return (
    <li>
      <span>Activity {activity.position + 1}</span>
      <strong>{activity.title}</strong>
      <span>{activity.type}</span>
      {linked.isPending && <LoadingState label="Loading Content" />}
      {linked.isError && <ErrorState message={errorMessage(linked.error)} />}
      {linked.isSuccess && linked.data.length === 0 && (
        <p className="content-empty">No Content attached.</p>
      )}
      {linked.isSuccess && linked.data.length > 0 && (
        <div className="student-content-list">
          {linked.data.map((reference) => (
            <ContentPreview key={reference.id} reference={reference} />
          ))}
        </div>
      )}
    </li>
  )
}

interface UnitPreviewProps extends PreviewNavigationProps {
  sectionId: string
  unit: LearningUnit
}

const UnitPreview = ({ courseId, sectionId, teacherSpaceId, unit }: UnitPreviewProps) => {
  const activities = useQuery({
    queryKey: activityKeys.all(teacherSpaceId, courseId, sectionId, unit.id),
    queryFn: () => activityApi.list(teacherSpaceId, courseId, sectionId, unit.id),
    retry: false,
  })

  return (
    <li>
      <span>Unit {unit.position + 1}</span>
      <strong>{unit.title}</strong>
      {activities.isPending && <LoadingState label="Loading Activities" />}
      {activities.isError && <ErrorState message={errorMessage(activities.error)} />}
      {activities.isSuccess && activities.data.length === 0 && <span>No Activities yet.</span>}
      {activities.isSuccess && activities.data.length > 0 && (
        <ul className="student-activity-list">
          {activities.data.map((activity) => (
            <ActivityPreview
              activity={activity}
              courseId={courseId}
              key={activity.id}
              learningUnitId={unit.id}
              sectionId={sectionId}
              teacherSpaceId={teacherSpaceId}
            />
          ))}
        </ul>
      )}
    </li>
  )
}

interface SectionPreviewProps extends PreviewNavigationProps {
  section: Section
}

const SectionPreview = ({ courseId, section, teacherSpaceId }: SectionPreviewProps) => {
  const units = useQuery({
    queryKey: learningUnitKeys.all(teacherSpaceId, courseId, section.id),
    queryFn: () => learningUnitApi.list(teacherSpaceId, courseId, section.id),
    retry: false,
  })

  return (
    <li>
      <div className="student-section-heading">
        <span>Section {section.position + 1}</span>
        <h2>{section.title}</h2>
      </div>
      {units.isPending && <LoadingState label="Loading Learning Units" />}
      {units.isError && <ErrorState message={errorMessage(units.error)} />}
      {units.isSuccess && units.data.length === 0 && (
        <p className="content-empty">No Learning Units yet.</p>
      )}
      {units.isSuccess && units.data.length > 0 && (
        <ol className="student-unit-list">
          {units.data.map((unit) => (
            <UnitPreview
              courseId={courseId}
              key={unit.id}
              sectionId={section.id}
              teacherSpaceId={teacherSpaceId}
              unit={unit}
            />
          ))}
        </ol>
      )}
    </li>
  )
}

interface CoursePreviewContentProps {
  teacherSpaceId: string
  course: Course
}

const CoursePreviewContent = ({ course, teacherSpaceId }: CoursePreviewContentProps) => {
  const sections = useQuery({
    queryKey: sectionKeys.all(teacherSpaceId, course.id),
    queryFn: () => sectionApi.list(teacherSpaceId, course.id),
    retry: false,
  })

  return (
    <div className="space-detail-card">
      <p className="eyebrow">Author Preview</p>
      <h1 id="course-preview-title">{course.title}</h1>
      <dl>
        <div>
          <dt>Status</dt>
          <dd>DRAFT</dd>
        </div>
      </dl>
      {sections.isPending && <LoadingState label="Loading Sections" />}
      {sections.isError && <ErrorState message={errorMessage(sections.error)} />}
      {sections.isSuccess && sections.data.length === 0 && (
        <div className="empty-state">
          <h2>No Sections yet</h2>
          <p>Add Sections before previewing the Course.</p>
        </div>
      )}
      {sections.isSuccess && sections.data.length > 0 && (
        <ol className="student-section-list">
          {sections.data.map((section) => (
            <SectionPreview
              courseId={course.id}
              key={section.id}
              section={section}
              teacherSpaceId={teacherSpaceId}
            />
          ))}
        </ol>
      )}
    </div>
  )
}

export const CoursePreviewPage = () => {
  const { teacherSpaceId, courseId } = useParams<{
    teacherSpaceId: string
    courseId: string
  }>()
  const scopeId = teacherSpaceId ?? ''
  const selectedCourseId = courseId ?? ''
  const course = useQuery({
    queryKey: courseKeys.detail(scopeId, selectedCourseId),
    queryFn: () => courseApi.get(scopeId, selectedCourseId),
    enabled: Boolean(scopeId && selectedCourseId),
    retry: false,
  })
  const courseNotFound = course.error instanceof ApiError && course.error.status === 404
  const coursePath = `/app/teacher-spaces/${scopeId}/environment/courses/${selectedCourseId}`

  return (
    <section className="course-preview-page" aria-label="Course Preview">
      <Link to={coursePath}>← Back to Course</Link>
      {course.isPending && <LoadingState label="Loading Course" />}
      {courseNotFound && <ErrorState message="Course not found." />}
      {course.isError && !courseNotFound && <ErrorState message={errorMessage(course.error)} />}
      {course.isSuccess && course.data.status !== 'draft' && (
        <ErrorState message="Course Preview is available only for DRAFT Courses." />
      )}
      {course.isSuccess && course.data.status === 'draft' && (
        <CoursePreviewContent course={course.data} teacherSpaceId={scopeId} />
      )}
    </section>
  )
}

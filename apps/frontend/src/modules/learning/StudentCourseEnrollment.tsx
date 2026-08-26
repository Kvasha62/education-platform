import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError } from '../../shared/api'
import { ErrorState, LoadingState } from '../../shared/ui'
import { enrollmentApi } from './enrollmentApi'
import type { EnrollmentList } from './enrollmentApi'
import { enrollmentKeys } from './enrollmentQueries'

const errorMessage = (error: unknown) =>
  error instanceof ApiError || error instanceof Error ? error.message : 'Request failed.'

export const StudentCourseEnrollment = ({ courseId }: { courseId: string }) => {
  const queryClient = useQueryClient()
  const enrollments = useQuery({
    queryKey: enrollmentKeys.all,
    queryFn: enrollmentApi.list,
    retry: false,
  })
  const enrollment = enrollments.data?.items.find((item) => item.course_id === courseId)
  const enroll = useMutation({
    mutationFn: () => enrollmentApi.enroll(courseId),
    onSuccess: (confirmed) => {
      queryClient.setQueryData<EnrollmentList>(enrollmentKeys.all, (current = { items: [] }) => ({
        items: current.items.some((item) => item.course_id === confirmed.course_id)
          ? current.items.map((item) =>
              item.course_id === confirmed.course_id ? confirmed : item,
            )
          : [...current.items, confirmed],
      }))
    },
  })

  return (
    <aside className="student-enrollment" aria-labelledby="course-enrollment-title">
      <h2 id="course-enrollment-title">Course enrollment</h2>
      {enrollments.isPending && <LoadingState label="Loading enrollment" />}
      {enrollments.isError && <ErrorState message={errorMessage(enrollments.error)} />}
      {enrollments.isSuccess && enrollment && (
        <p className="enrollment-status">Enrolled</p>
      )}
      {enrollments.isSuccess && !enrollment && (
        <button disabled={enroll.isPending} onClick={() => enroll.mutate()} type="button">
          {enroll.isPending ? 'Enrolling…' : 'Enroll in Course'}
        </button>
      )}
      {enroll.isError && <ErrorState message={errorMessage(enroll.error)} />}
    </aside>
  )
}

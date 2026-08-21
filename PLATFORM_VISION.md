# Education Platform — Platform Vision

**Status:** Product Vision Baseline v1.0

## 1. What we are building

Education Platform is a **constructor of educational environments** for learners approximately 6–17 years old.

The goal is not simply to host courses. The platform should allow educators to compose different learning experiences from reusable educational building blocks.

The platform should eventually support:

- Teacher Space;
- Student Space;
- Parent Space;
- future Mentor and Administrator spaces;
- courses;
- lessons;
- games;
- quests;
- videos;
- lectures;
- online activities;
- homework;
- homework review;
- quizzes and assessments;
- projects;
- interactive learning;
- commerce and payments;
- advertising for eligible free content;
- analytics;
- gamification;
- AI-assisted education.

These are future directions, not a requirement to implement everything immediately.

## 2. Constructor model

The central idea is:

```text
Educational Environment
        ↓
Course
        ↓
Sections
        ↓
Learning Units
        ↓
Activities
        ↓
Content / Assessment / Interaction
```

A teacher should eventually be able to construct a complete educational experience from these components without programming the platform itself.

## 3. Independent systems

The platform should be assembled from independent systems.

Initial system:

```text
Teacher Space
```

Future systems:

```text
Student Space
Parent Space
Mentor Space
Administrator Space
```

Independent domain engines will provide reusable capabilities such as education, content, learning, assessment, commerce, advertising, analytics and gamification.

Systems should be addable and, where practical, removable without rewriting unrelated parts of the platform.

## 4. Teacher experience

The teacher is the first platform user we optimize for.

A teacher should eventually be able to:

1. create an educational environment;
2. create a course;
3. define target age or audience;
4. create sections and learning units;
5. add different activity types;
6. attach educational content;
7. save drafts;
8. preview the course;
9. publish it;
10. define free or paid access;
11. configure supported payment methods;
12. manage the course after publication.

## 5. Course economics

A course may be free or paid.

For a free course, the platform may show advertising according to platform policy.

For a paid course, advertising should not be shown according to the platform's paid-content policy.

Payment providers must be replaceable and extensible.

## 6. Child-focused product philosophy

Because the platform targets children and teenagers, future development must prioritize:

- age-appropriate UX;
- safety;
- privacy;
- parental controls and visibility where appropriate;
- clear educational goals;
- accessibility;
- responsible monetization;
- protection from manipulative engagement patterns.

These principles should influence future product decisions without forcing premature implementation.

## 7. Development philosophy

The platform must be built through small vertical slices.

We do not attempt to build the entire ecosystem before validating the foundation.

Preferred sequence:

```text
Architecture
→ Technical Foundation
→ Identity
→ Teacher Space
→ Educational Environment
→ Course Builder
→ Content
→ Publication
→ Student Space
→ Learning
→ Assessment
→ Commerce
→ Advertising
→ Future Systems
```

## 8. Product principle

The platform should become more capable by **composition**, not by continually increasing the complexity of one giant application.

The long-term goal is:

> A flexible educational environment builder in which teachers can create different forms of learning while students and parents receive dedicated experiences around the same underlying educational model.

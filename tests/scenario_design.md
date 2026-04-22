# Manual Scenario Design (Stage 8)

## Preconditions

- Run base seed data and demo data first.
- Login accounts are ready (6 preset users).
- The app runs in single-session mode.

## Scenario 1: Normal Application Success

1. Agent creates and submits an application.
2. Reviewer approves the application.
3. School officer reserves the slot.
4. Expected:
   - Application status: `SCHOOL_RESERVED`
   - University and major quota both increase by 1
   - Operation and quota logs are written

## Scenario 2: Review Rejected

1. Agent creates and submits an application.
2. Reviewer rejects with required comment.
3. Expected:
   - Application status: `REVIEW_REJECTED`
   - `is_active_flow` becomes `False`
   - Review record exists

## Scenario 3: School Feedback Then Major Resubmission

1. Agent submits application.
2. Reviewer approves -> `SCHOOL_PENDING`.
3. School officer sends feedback with optional suggested major.
4. Agent performs `resubmit_with_new_major`.
5. Expected:
   - Old application status: `CLOSED`
   - New application status: `SUBMITTED`
   - New record references old one via `previous_application_id`

## Scenario 4: Quota Full

1. Prepare one `SCHOOL_PENDING` application.
2. Set target major quota to full.
3. School officer tries reserve action.
4. Expected:
   - Service raises business error
   - Application remains `SCHOOL_PENDING`
   - No quota/log partial update

## Scenario 5: No Reapply to Same University After Cancellation

1. Use student with a historical `CANCELLED` record in target university.
2. Agent tries creating a new application to the same university.
3. Expected:
   - Service raises business error
   - No new application is created

## Scenario 6: One Active Application Per Student

1. Use student with one active application (`SUBMITTED`/`SCHOOL_PENDING`/`SCHOOL_FEEDBACK`).
2. Agent tries creating another new application.
3. Expected:
   - Service raises business error
   - Existing active application remains unchanged


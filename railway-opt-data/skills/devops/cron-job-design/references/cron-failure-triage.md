# Cron failure triage

Use this when a cron job reports `exit code 1` or delivers a failure alert.

## Triage order

1. **Find the wrapper log** for the exact cron run.
2. **Read the first traceback / first nonzero failing step.** Do not start with the tail.
3. **Identify the exact script and interpreter** the cron wrapper used.
4. **Reproduce the failing step with the same command line** in the live environment.
5. **Fix the code path first** when the failure is deterministic.
6. **If the failure is in the runtime path**, make the job robust via a local fallback or shared helper instead of duplicating logic in each script.
7. **Re-run the same command once** to verify the fix before declaring success.

## Useful checks

- Did the wrapper stop before the digest/report render step?
- Did the failure come from an import at process start?
- Is the job using the same interpreter as the cron wrapper?
- Is there a cleaner shared helper the job should use instead of hand-rolled code?

## Goal

Turn the failing cron into one of:
- silent when healthy
- actionable when broken
- deterministic enough that the same class of failure is less likely to recur

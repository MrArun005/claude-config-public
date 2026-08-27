"""Alias-table ordering regression. Pure lookup: no browser, runs in ms.

Every case here is an ordering trap: a general rule that would answer a
specific question with the wrong value if it came first. Run via p3_test.py or
directly:  python tests/test_mapping.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apply.aliases import key_for          # noqa: E402
from apply.fields import FormField         # noqa: E402


def f(label, type="text", name="", options=None, required=False):
    return FormField(tag="select" if str(type).startswith("select") else "input",
                     type=type, name=name, id="", label=label,
                     required=required, options=options, idx=0)


CASES = [
    # (label, control type, expected key) — None means "must escalate to rung 2"
    ("How many years of React experience?",        "text", "years_react"),
    ("Years of Next.js experience",                "text", "years_nextjs"),
    ("Years of TypeScript",                        "text", "years_typescript"),
    ("Years of Node.js experience",                "text", "years_nodejs"),
    ("Total years of experience",                  "text", "years_experience"),
    ("Years of JavaScript experience",             "text", "years_javascript"),
    ("Years leading engineers",                    "text", "years_leadership"),

    ("Current CTC",                                "text", "current_ctc"),
    ("Current annual compensation",                "text", "current_ctc"),
    ("Expected CTC",                               "text", "salary_expectation"),
    ("Expected salary",                            "text", "salary_expectation"),
    ("Salary",                                     "text", "salary_expectation"),
    ("Expected hourly rate",                       "text", "hourly_rate"),

    ("Are you legally authorised to work in the United States?", "select", "authorised_us"),
    ("Are you authorized to work in the UK?",      "select", "authorised_uk_eu"),
    ("Do you require visa sponsorship?",           "select", "requires_sponsorship"),
    ("Work authorization",                         "text", "work_authorisation"),
    ("Citizenship",                                "text", "nationality"),
    ("Do you hold a security clearance?",          "select", "security_clearance"),

    ("Start date at your current employer",        "text", "current_start_date"),
    ("Earliest start date",                        "text", "earliest_start"),
    ("When can you start?",                        "text", "earliest_start"),
    ("Notice period",                              "text", "notice_period"),

    ("Cover letter",                               "file", "cover_letter_path"),
    ("Cover letter",                               "textarea", "why_this_company"),
    ("Resume/CV",                                  "file", "resume_path"),

    ("Background check consent",                   "select", "background_check"),
    ("I agree to the privacy policy",              "checkbox", "consent_privacy"),
    ("Gender",                                     "select", "gender"),
    ("Race / Ethnicity",                           "select", "ethnicity"),
    ("Veteran status",                             "select", "veteran_status"),
    ("Disability status",                          "select", "disability_status"),

    ("First Name",                                 "text", "first_name"),
    ("Last Name",                                  "text", "last_name"),
    ("Full legal name",                            "text", "full_name"),
    ("How did you hear about us?",                 "text", "referral_source"),
    ("Have you previously been employed by us?",   "select", "worked_here_before"),
    ("Are you related to a current employee?",     "select", "related_to_employee"),
    ("University",                                 "text", "university"),
    ("Year of graduation",                         "text", "graduation_year"),
    ("Highest degree",                             "text", "highest_degree"),
    ("English proficiency",                        "select", "english_level"),
    ("Timezone / overlap hours",                   "text", "timezone"),
    ("PIN code",                                   "text", "postal_code"),

    # Must NOT map to anything — proves the table stays honestly incomplete.
    ("What is your favourite Kubernetes operator?", "text", None),
]


def run() -> int:
    bad = []
    for label, type_, expected in CASES:
        got = key_for(f(label, type_))
        if got != expected:
            bad.append((label, type_, expected, got))
    for label, type_, expected, got in bad:
        print(f"  FAIL  {label!r} [{type_}] -> {got!r}, expected {expected!r}")
    print(f"mapping: {len(CASES)-len(bad)}/{len(CASES)} cases correct")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(run())

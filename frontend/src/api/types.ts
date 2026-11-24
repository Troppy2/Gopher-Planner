export type CourseStatus = "done" | "prog" | "plan" | "avail" | "block";
export type Season = "Fall" | "Spring" | "Summer";
export type Requirement =
  | "Major core"
  | "Math and stats"
  | "Elective"
  | "Liberal ed";

/** A term label such as "Fall 2026". "Completed" groups everything already finished. */
export type TermId = string;

export interface Course {
  code: string;
  title: string;
  credits: number;
  status: CourseStatus;
  requirement: Requirement;
  offered: Season[];
  prereqs: string[];
  concurrent: string[];
  professors: string[];
  term: TermId | null;
  lockReason?: string;
  slot?: string | null;
  slotCategories?: string[];
  /** Where title, credits and scheduling facts came from. */
  metadataSource?: "catalog" | "program";
  /** Full prerequisite tree; `prereqs` is a flat display list and never means "all required". */
  prerequisiteTree?: PrerequisiteExpression | null;
  metadataWarnings?: WarningCode[];
}

export type PrerequisiteExpression =
  | {
      type: "course";
      course_code: string;
    }
  | {
      type: "condition";
      text: string;
    }
  | {
      type: "any_of" | "all_of";
      requirements: PrerequisiteExpression[];
    }
  | {
      type: string;
      [key: string]: unknown;
    };

export interface CatalogPrerequisites {
  needs_review: boolean;
  source_text: string;
  status: string;
  requirements: PrerequisiteExpression | null;
}

export interface CatalogCourse {
  id: number;
  code: string;
  subject: string;
  number: string;
  title: string;
  campus: string;
  description: string;
  minimumCredits: number;
  maximumCredits: number;
  repeatable: string;
  maximumCompletions: string;
  maximumCreditsEarned: string;
  gradingBasis: string;
  requirements: string | null;
  typicallyOffered: string;
  offered: Season[];
  prerequisiteStatus: string;
  /** Liberal education designations, e.g. "Global Perspectives". */
  leAttributes?: string[];
  prerequisiteSourceText: string;
  prerequisites: CatalogPrerequisites | null;
  unresolvedPrerequisiteCourses: string[];
  resolvedPrerequisites?: {
    code: string;
    title: string;
  }[];
}

export interface CatalogCoursePage {
  courses: CatalogCourse[];
  total: number;
  limit: number;
  offset: number;
}

export interface Summary {
  gpa: number | null;
  gradedCredits: number;
  creditsCompleted: number;
  creditsTotal: number;
  percentComplete: number | null;
  program: string;
  source: string;
}

export interface Profile {
  name: string;
  major: string;
  standing: string;
  careerGoals: string;
  creditLoad: number;
  graduationTarget: string;
  onboarded: boolean;
}

export type WarningCode =
  | "program_requirements_unavailable"
  | "program_version_unavailable"
  | "program_version_unconfirmed"
  | "requirements_incomplete"
  | "requirements_need_review"
  | "course_metadata_unavailable"
  | "offered_terms_unverified"
  | "prerequisites_require_review"
  | "catalog_version_unverified"
  | "catalog_metadata_conflict"
  | "graduation_target_unreachable"
  | (string & {});

export type RequirementStatus = "satisfied" | "unsatisfied" | "needs_review";

export interface RequirementEvidence {
  matchedCodes: string[];
  missingCodes: string[];
  appliedAdjustments: string[];
  requiredCredits?: number;
  matchedCredits?: number;
  matchedCourses?: number;
  minCourses?: number;
  maxCourses?: number;
}

export interface RequirementProgress {
  options?: string[];
  id: string;
  label: string;
  parentId: string | null;
  type: string;
  category: Requirement | null;
  completedStatus: RequirementStatus;
  projectedStatus: RequirementStatus;
  completedEvidence: RequirementEvidence;
  projectedEvidence: RequirementEvidence;
  details: string[];
}

export interface Plan {
  /** Ordered: "Completed", current term, then every future term. */
  terms: TermId[];
  currentTerm: TermId;
  /** Credits earned before any course listed here (transfer, AP, older terms). */
  baseCredits: number;
  electiveCredits?: number;
  courses: Course[];
  /** The confirmed program catalog version, or null until the student selects one. */
  catalogTerm: TermId | null;
  availableCatalogTerms: TermId[];
  warnings: WarningCode[];
  requirementProgress: RequirementProgress[];
  /** Liberal education tracker; absent from older API responses. */
  liberalEd?: LiberalEd;
}

/** Codes by evidence kind: earned, in progress this term, or planned. */
export interface LeCodes {
  done: string[];
  prog: string[];
  plan: string[];
}

export type LeItemStatus = "done" | "in_progress" | "planned" | "needed" | "needs_review" | "not_required";
export type LeSectionStatus = "met" | "on_track" | "needs_review" | "short";

export interface LeCategory {
  id: string;
  label: string;
  /** Catalog designation names that satisfy it; the first is the current name. */
  designations: string[];
  status: LeItemStatus;
  /** "apas" when a parsed APAS audit marked it complete. */
  source: "catalog" | "apas";
  codes: LeCodes;
}

export interface WritingCounts {
  total: number;
  upper: number;
  upperInMajor: number;
}

export interface LiberalEd {
  source: "catalog" | "catalog+apas";
  core: { status: LeSectionStatus; items: LeCategory[] };
  themes: {
    status: LeSectionStatus;
    required: number;
    completed: number;
    projected: number;
    mandatory: string[];
    mandatoryMissing: string[];
    items: LeCategory[];
  };
  writing: {
    firstYear: { label: string; status: LeItemStatus; codes: LeCodes; acceptedCodes: string[] };
    intensive: {
      label: string;
      status: LeSectionStatus;
      required: WritingCounts;
      completed: WritingCounts;
      projected: WritingCounts;
      codes: LeCodes;
    };
  };
  /** Designation names a new course could still usefully cover. */
  remaining: string[];
  sources: Record<string, string>;
}

export interface DoubleDipperPage {
  remaining: string[];
  courses: (CatalogCourse & { covers: string[] })[];
  total: number;
  limit: number;
  offset: number;
}

export interface GenerateResult {
  jobId: string;
  status: "succeeded";
  warnings: WarningCode[];
  plan: Plan;
}

export interface CourseworkEntry {
  code: string;
  title: string;
  credits: number;
  status: "done" | "prog";
  term: TermId | null;
  grade: string | null;
  source?: "manual" | "transcript";
}

export interface Coursework {
  courses: CourseworkEntry[];
  skipped: boolean;
}

export interface ProgramSummary {
  name: string;
  officialName: string;
  catalogTerms: TermId[];
  reviewed: boolean;
}

export interface PlanChange {
  code: string;
  status: CourseStatus;
  term: TermId | null;
  slot?: string | null;
  credits?: number;
}

export interface Options {
  majors: string[];
  /** Majors whose requirements are machine-mapped and not yet hand-reviewed. */
  unverifiedMajors?: string[];
  standings: string[];
  graduationTargets: string[];
  subjects: string[];
  /** Career paths offered per major. */
  careers: Record<string, string[]>;
}

export interface CourseFilters {
  le?: string | string[];
  q?: string;
  subject?: string;
  level?: string;
  credits?: string;
  term?: string;
  requirement?: string;
  availability?: string;
  limit?: number;
  offset?: number;
}

export type TranscriptStatus = "parsing" | "parsed" | "no_text" | "failed";

export interface Transcript {
  id: string;
  fileName: string;
  status: TranscriptStatus;
  completed: number;
  inProgress: number;
  courses?: CourseworkEntry[];
  /** Codes found but not importable (transfer placeholders, unreadable codes). */
  notImported?: string[];
  errorCode?: string;
}
export type ReportTargetType = "course" | "requirement";
export type ReportReason = "prerequisites_wrong" | "offered_terms_wrong" | "details_wrong" | "missing_course" | "course_should_not_count" | "rule_wrong" | "other";
export type NewReport = (
  | { targetType: "course"; courseCode: string }
  | { targetType: "requirement"; requirementId: string }
) & { reason: ReportReason; note?: string };
export interface DataReport {
  id: number;
  targetType: ReportTargetType;
  courseCode: string | null;
  requirementId: string | null;
  reason: ReportReason;
  note: string | null;
  status: "open" | "resolved" | "dismissed";
  createdAt: string;
  updatedAt: string;
}


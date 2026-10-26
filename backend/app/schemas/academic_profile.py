"""Strict full-snapshot validation, independent of SQLAlchemy storage models."""

from dataclasses import dataclass
from decimal import Decimal
import re

SEASONS = {'Spring': 1, 'Summer': 2, 'Fall': 3}
SOURCES = {'institutional', 'IB', 'AP', 'transfer'}
GRADES = {'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'F', 'S', 'N'}


class ValidationError(Exception):
    def __init__(self, field, message, code='invalid'):
        self.details = [{'field': field, 'code': code, 'message': message}]
        super().__init__(message)


@dataclass(frozen=True)
class AcademicSnapshot:
    profile: dict
    courses: list[dict]
    extra: list[dict]


def object_fields(value, fields, path):
    if not isinstance(value, dict):
        raise ValidationError(path, 'Must be a JSON object.')
    missing, unknown = fields - value.keys(), value.keys() - fields
    if missing:
        raise ValidationError(path, 'Missing fields: ' + ', '.join(sorted(missing)), 'missing')
    if unknown:
        raise ValidationError(path, 'Unknown fields: ' + ', '.join(sorted(unknown)), 'unknown')


def label(value, path, maximum, nullable=False):
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > maximum:
        raise ValidationError(path, f'Must be nonempty trimmed text, at most {maximum} characters.')
    if any(ord(character) < 32 for character in value):
        raise ValidationError(path, 'Control characters are not allowed.')
    return value


def choice(value, choices, path, nullable=False):
    if value is None and nullable:
        return None
    if not isinstance(value, str) or value not in choices:
        raise ValidationError(path, 'Unsupported value.')
    return value


def credits(value, path, positive=False):
    # No strings, booleans, rounding, NaN, infinity, or inferred credits.
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValidationError(path, 'Must be a JSON number.')
    number = Decimal(str(value))
    if not number.is_finite() or not 0 <= number <= Decimal('9999.99'):
        raise ValidationError(path, 'Must be finite and between 0 and 9999.99.')
    if positive and number == 0:
        raise ValidationError(path, 'Must be greater than zero.')
    if number != number.quantize(Decimal('.01')):
        raise ValidationError(path, 'At most two decimal places are allowed.')
    return number


def term(value, path, nullable=False):
    if value is None and nullable:
        return None
    object_fields(value, {'year', 'season'}, path)
    if type(value['year']) is not int or not 1 <= value['year'] <= 9999:
        raise ValidationError(path + '.year', 'Must be an integer between 1 and 9999.')
    choice(value['season'], SEASONS, path + '.season')
    return dict(value)


def term_order(value):
    return value['year'], SEASONS[value['season']]


def unique(value, seen, path):
    if value in seen:
        raise ValidationError(path, 'Duplicate record or credit allocation.', 'duplicate')
    seen.add(value)


def validate_snapshot(payload) -> AcademicSnapshot:
    """Validate everything before opening a database transaction; fail explicitly."""
    object_fields(payload, {'profile', 'course_records', 'extra_credits'}, '$')
    profile = payload['profile']
    object_fields(profile, {'program', 'catalog_year', 'current_term',
                           'target_graduation_term', 'max_credits_per_term'}, 'profile')
    parsed_profile = dict(
        program=label(profile['program'], 'profile.program', 128),
        catalog_year=label(profile['catalog_year'], 'profile.catalog_year', 64),
        current_term=term(profile['current_term'], 'profile.current_term'),
        target_graduation_term=term(profile['target_graduation_term'], 'profile.target_graduation_term'),
        max_credits_per_term=credits(profile['max_credits_per_term'], 'profile.max_credits_per_term', True),
    )
    current = parsed_profile['current_term']
    if term_order(parsed_profile['target_graduation_term']) < term_order(current):
        raise ValidationError('profile.target_graduation_term', 'Cannot precede the current term.')

    for key in ('course_records', 'extra_credits'):
        if not isinstance(payload[key], list):
            raise ValidationError(key, 'Must be an array, including when empty.')
    courses, extra = [], []
    attempts, course_references, extra_references = set(), set(), set()
    course_fields = {'course_code', 'status', 'term', 'credits', 'earned_credits',
                     'grade', 'credit_source', 'grading_basis', 'credit_reference'}
    for index, row in enumerate(payload['course_records']):
        path = f'course_records[{index}]'
        # credit_reference was added as optional; omitted means an unknown identifier.
        if isinstance(row, dict) and 'credit_reference' not in row:
            row = row | {'credit_reference': None}
        object_fields(row, course_fields, path)
        record = dict(
            course_code=label(row['course_code'], path + '.course_code', 32),
            status=choice(row['status'], {'completed', 'in_progress'}, path + '.status'),
            term=term(row['term'], path + '.term', True),
            credits=credits(row['credits'], path + '.credits'),
            earned_credits=credits(row['earned_credits'], path + '.earned_credits'),
            grade=choice(row['grade'], GRADES, path + '.grade', True),
            credit_source=choice(row['credit_source'], SOURCES, path + '.credit_source'),
            grading_basis=choice(row['grading_basis'], {'AF', 'SN'}, path + '.grading_basis', True),
            credit_reference=label(row['credit_reference'], path + '.credit_reference', 128, True),
        )
        if not re.fullmatch(r'[A-Z][A-Z0-9]* [0-9]{4}[A-Z]?', record['course_code']):
            raise ValidationError(path + '.course_code', 'Use a canonical course code, for example CSCI 1133.')
        if record['earned_credits'] > record['credits']:
            raise ValidationError(path + '.earned_credits', 'Cannot exceed course credits.')
        if record['credit_source'] == 'institutional' and record['term'] is None:
            raise ValidationError(path + '.term', 'Institutional records require a term.')
        if record['status'] == 'in_progress':
            if record['earned_credits'] != 0:
                raise ValidationError(path + '.earned_credits', 'In-progress records must have zero earned credits.',
                                      'in_progress_requires_zero')
            if record['grade'] is not None or record['credit_source'] != 'institutional':
                raise ValidationError(path, 'In-progress records require institutional source and an unknown final grade.')
            if record['term'] != current:
                raise ValidationError(path + '.term', 'In-progress term must equal the current term.')
        elif record['term'] is not None and term_order(record['term']) > term_order(current):
            raise ValidationError(path + '.term', 'Completed term cannot follow the current term.')
        grade, basis = record['grade'], record['grading_basis']
        if grade is not None and basis is not None:
            if (basis == 'AF' and grade in {'S', 'N'}) or (basis == 'SN' and grade not in {'S', 'N'}):
                raise ValidationError(path + '.grade', 'Grade is incompatible with grading basis.')
        if grade in {'F', 'N'} and record['earned_credits'] != 0:
            raise ValidationError(path + '.earned_credits', 'F/N requires zero earned credits.')
        if record['credit_source'] in {'IB', 'AP'} and (grade is not None or basis is not None):
            raise ValidationError(path, 'IB/AP mapped credit must have unknown grade and grading basis.')
        attempt = (record['course_code'], None if record['term'] is None else term_order(record['term']))
        unique(attempt, attempts, path)
        if record['credit_reference'] is not None:
            unique(record['credit_reference'], course_references, path + '.credit_reference')
        courses.append(record)

    for index, row in enumerate(payload['extra_credits']):
        path = f'extra_credits[{index}]'
        object_fields(row, {'reference', 'source', 'earned_credits', 'usage_confirmed', 'confirmed_usage'}, path)
        record = dict(
            reference=label(row['reference'], path + '.reference', 128),
            source=choice(row['source'], SOURCES, path + '.source'),
            earned_credits=credits(row['earned_credits'], path + '.earned_credits', True),
            usage_confirmed=row['usage_confirmed'],
            confirmed_usage=label(row['confirmed_usage'], path + '.confirmed_usage', 500, True),
        )
        if type(record['usage_confirmed']) is not bool:
            raise ValidationError(path + '.usage_confirmed', 'Must be a JSON boolean.')
        if record['usage_confirmed'] != (record['confirmed_usage'] is not None):
            raise ValidationError(path, 'Confirmed usage requires true plus nonempty text; otherwise use false plus null.')
        unique(record['reference'], extra_references, path + '.reference')
        if record['reference'] in course_references:
            raise ValidationError(path + '.reference', 'Credit allocation already appears in course records.', 'duplicate')
        extra.append(record)
    return AcademicSnapshot(parsed_profile, courses, extra)

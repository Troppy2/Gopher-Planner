"""Input boundary tests require no database and never infer academic results."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from app.schemas.academic_profile import ValidationError, validate_snapshot


@pytest.fixture
def sample():
    return json.loads((Path(__file__).parent / 'fixtures/academic_profile.json').read_text())


@pytest.mark.parametrize(('path', 'value'), [
    (('profile', 'max_credits_per_term'), True),
    (('profile', 'max_credits_per_term'), '16'),
    (('profile', 'max_credits_per_term'), 16.001),
    (('profile', 'max_credits_per_term'), float('nan')),
    (('profile', 'max_credits_per_term'), float('inf')),
    (('profile', 'target_graduation_term'), {'year': 2026, 'season': 'Summer'}),
    (('profile', 'current_term'), {'year': True, 'season': 'Fall'}),
    (('course_records', 2, 'earned_credits'), 1),
    (('course_records', 2, 'grade'), 'A'),
    (('course_records', 2, 'term'), {'year': 2027, 'season': 'Spring'}),
    (('course_records', 0, 'term'), None),
    (('course_records', 0, 'term'), {'year': 2027, 'season': 'Fall'}),
    (('course_records', 0, 'grade'), 'W'),
    (('course_records', 0, 'grade'), 'I'),
    (('course_records', 0, 'grade'), 'T5'),
    (('course_records', 0, 'grade'), 'T6'),
    (('course_records', 0, 'grade'), 'AF'),
    (('course_records', 0, 'status'), 'done'),
    (('course_records', 0, 'grading_basis'), 'T5'),
    (('course_records', 0, 'credits'), -1),
    (('course_records', 0, 'credits'), 3),
    (('extra_credits', 0, 'usage_confirmed'), True),
    (('extra_credits', 0, 'usage_confirmed'), 'false'),
    (('extra_credits', 0, 'earned_credits'), 0),
    (('extra_credits', 0, 'confirmed_usage'), 'Elective'),
])
def test_invalid_values_are_rejected(sample, path, value):
    row = sample
    for key in path[:-1]:
        row = row[key]
    row[path[-1]] = value
    with pytest.raises(ValidationError):
        validate_snapshot(sample)


def test_no_input_mutation_or_unknown_grade_inference(sample):
    before = deepcopy(sample)
    result = validate_snapshot(sample)
    assert sample == before
    assert result.courses[1]['grade'] is None
    assert result.courses[1]['grading_basis'] is None


def test_unknown_identity_and_missing_array_rejected(sample):
    sample['student_id'] = 2
    with pytest.raises(ValidationError):
        validate_snapshot(sample)
    del sample['student_id'], sample['extra_credits']
    with pytest.raises(ValidationError):
        validate_snapshot(sample)


def test_duplicate_attempt_ignores_source(sample):
    sample['course_records'].append(sample['course_records'][0] | {'credit_source': 'transfer'})
    with pytest.raises(ValidationError):
        validate_snapshot(sample)


def test_null_term_duplicates_rejected_and_different_ib_mappings_allowed(sample):
    row = sample['course_records'][0] | dict(term=None, credit_source='IB', grade=None)
    sample['course_records'] = [row, row | {'course_code': 'MATH 1272'}]
    validate_snapshot(sample)
    sample['course_records'].append(dict(row))
    with pytest.raises(ValidationError):
        validate_snapshot(sample)


def test_different_term_retake_and_extra_usage_confirmation_allowed(sample):
    sample['course_records'].append(sample['course_records'][0] | {'term': {'year': 2026, 'season': 'Spring'}})
    sample['extra_credits'][0].update(usage_confirmed=True, confirmed_usage='Human-confirmed elective purpose')
    validate_snapshot(sample)


def test_cross_table_credit_reference_rejected(sample):
    sample['course_records'][0]['credit_reference'] = 'TEST-IB-001'
    with pytest.raises(ValidationError):
        validate_snapshot(sample)

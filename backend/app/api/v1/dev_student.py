"""Local development routes, registered only after explicit configuration opt-in."""

from decimal import Decimal
import json

from flask import Blueprint, current_app, request
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.schemas.academic_profile import ValidationError, validate_snapshot
from app.services.academic_profile import get_profile, save_profile

blueprint = Blueprint('dev_student', __name__, url_prefix='/api/v1/dev/student')


def error(code, message, status, details=None):
    payload = {'code': code, 'message': message}
    if details is not None:
        payload['details'] = details
    return {'error': payload}, status


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Repeated JSON object key.')
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError('Nonstandard JSON number.')


@blueprint.after_request
def no_cache(response):
    response.headers['Cache-Control'] = 'no-store'
    return response


@blueprint.errorhandler(413)
def too_large(_error):
    return error('validation', 'Request exceeds the 1 MiB limit.', 413)


@blueprint.route('/academic-profile', methods=['GET', 'PUT'])
def academic_profile():
    if request.args:
        return error('validation', 'Query parameters and client-selected identities are not supported.', 422)
    factory = current_app.extensions['database_session_factory']
    try:
        if request.method == 'GET':
            result = get_profile(factory)
            if result is None:
                return error('not_found', 'Development student academic profile does not exist.', 404)
            return result, 200
        if not request.is_json:
            return error('validation', 'Content-Type must be application/json.', 415)
        request.max_content_length = 1024 * 1024
        try:
            payload = json.loads(request.get_data(), parse_float=Decimal,
                                 parse_constant=invalid_constant, object_pairs_hook=strict_object)
        except (ValueError, UnicodeDecodeError, RecursionError):
            return error('validation', 'Malformed JSON, repeated object keys or nonstandard numbers.', 400)
        snapshot = validate_snapshot(payload)
        return save_profile(factory, snapshot), 200
    except ValidationError as exception:
        return error('validation', 'Academic profile validation failed.', 422, exception.details)
    except IntegrityError:
        return error('validation', 'Snapshot violates a database constraint; no changes were saved.', 422)
    except SQLAlchemyError:
        return error('server', 'Database operation failed; no changes were saved.', 503)

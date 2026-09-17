#!/usr/bin/env python3
"""Portable Tripo v3 client: Python 3.10+, standard library only."""
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import ssl
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from contextlib import contextmanager

BASE = 'https://openapi.tripo3d.ai'
ROUTES = {
    '/v3/generation/text-to-model', '/v3/generation/image-to-model',
    '/v3/generation/multiview-to-model', '/v3/generation/image-to-multiview',
    '/v3/models/texture', '/v3/models/convert', '/v3/models/import',
    '/v3/animations/rig-check', '/v3/animations/rig', '/v3/animations/retarget',
    '/v3/mesh/decimate',
}
TERMINAL_BAD = {'failed', 'cancelled', 'canceled', 'banned', 'expired', 'unknown'}
SECRET = ''


class TripoError(Exception):
    pass


class Rejected(TripoError):
    """Definite rejection; unlike an unknown POST outcome."""


def redact(value):
    if isinstance(value, dict):
        return {k: ('[REDACTED]' if k.lower() in ('authorization', 'api_key', 'user_api_key') else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        if SECRET:
            value = value.replace(SECRET, '[REDACTED]')
        return re.sub(r'tsk_[A-Za-z0-9]+', '[REDACTED]', value)
    return value


def emit(value):
    print(json.dumps(redact(value), ensure_ascii=False, indent=2), flush=True)


def save(path, value):
    """Private, atomic files, including job requests and expiring signed output URLs."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def credentials_path():
    if os.name == 'nt':
        return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'Tripo3D/credentials.json'
    return Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'tripo-3d/credentials.json'


def setup_guide():
    command = [sys.executable, str(Path(__file__).resolve()), 'configure']
    if os.name == 'nt':
        import subprocess
        configure_command = subprocess.list2cmdline(command)
    else:
        configure_command = shlex.join(command)
    return {
        'console_url': 'https://platform.tripo3d.ai',
        'steps': [
            '注册或登录 Tripo 开发者控制台，进入 API Keys，点击 Create Key。',
            '复制并妥善保存完整密钥；官方说明只在创建时展示一次。',
            '在自己的交互终端运行下面的 configure_command，粘贴密钥后按回车。输入不显示字符是正常的，无需发到聊天。',
            '显示 configured: true 表示验证并保存成功；随后运行 doctor --online 复核账户连接。验证不会生成模型。',
        ],
        'configure_command': configure_command,
        'help_file': str(Path(__file__).resolve().parent.parent / 'INSTALL.md'),
    }


def print_setup_guide():
    print(json.dumps(setup_guide(), ensure_ascii=False, indent=2), file=sys.stderr, flush=True)


def get_key():
    global SECRET
    key = os.environ.get('TRIPO_API_KEY', '').strip()
    if not key and credentials_path().exists():
        key = str(read(credentials_path()).get('api_key', '')).strip()
    if not key and sys.stdin.isatty():
        print_setup_guide()
        key = getpass.getpass('Tripo API key (hidden, not saved): ').strip()
    if not key:
        print_setup_guide()
        raise TripoError('No API key. Follow the setup guide above, or set TRIPO_API_KEY in your environment.')
    SECRET = key
    return key


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise TripoError('API redirect refused; verify the official endpoint. Credential was not forwarded.')


class Client:
    def __init__(self, key):
        self.key = key
        self.opener = urllib.request.build_opener(NoRedirect())

    def api(self, route, body=None, content_type='application/json'):
        if not route.startswith('/v3/') or '?' in route or '#' in route or '..' in route:
            raise TripoError('Expected an official /v3/ API path.')
        data = None if body is None else body if isinstance(body, bytes) else json.dumps(body).encode()
        req = urllib.request.Request(BASE + route, data=data, method='GET' if body is None else 'POST', headers={
            'Authorization': 'Bearer ' + self.key, 'Content-Type': content_type,
            'User-Agent': 'TripoPortableSkill/1.0',
        })
        attempts = 3 if body is None else 1
        for attempt in range(attempts):
            try:
                with self.opener.open(req, timeout=25) as response:
                    result = json.load(response)
                if not isinstance(result, dict) or result.get('code') != 0 or 'data' not in result:
                    # A nominal HTTP success with an API error is not assumed safe to resubmit.
                    raise TripoError('Tripo API response: ' + json.dumps(redact(result), ensure_ascii=False)[:600])
                return result['data']
            except urllib.error.HTTPError as error:
                if body is None and (error.code == 429 or error.code >= 500) and attempt + 1 < attempts:
                    time.sleep(2 ** attempt)
                    continue
                cls = Rejected if 400 <= error.code < 500 and error.code != 408 else TripoError
                raise cls(f'HTTP {error.code} from Tripo; inspect account/task state before retrying a submission.') from None
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                if attempt + 1 < attempts:
                    time.sleep(2 ** attempt)
                    continue
                raise TripoError(f'Connection failed ({type(error).__name__}); no POST was retried. Check TLS, proxy and saved job.') from None
            except (ValueError, UnicodeError):
                raise TripoError('Invalid Tripo response. Submission outcome may be unknown; do not resubmit blindly.') from None

    def task(self, task_id):
        if not re.fullmatch(r'[A-Za-z0-9_-]+', task_id):
            raise TripoError('Invalid task ID.')
        return self.api('/v3/tasks/' + task_id)


@contextmanager
def job_lock(job):
    job = Path(job)
    job.mkdir(parents=True, exist_ok=True)
    lock = job / '.submit.lock'
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise TripoError('Job is locked. If the recorded process ended, reconcile state before removing .submit.lock.') from None
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(str(os.getpid()))
        yield
    finally:
        lock.unlink(missing_ok=True)


def validate_request(request):
    if not isinstance(request, dict) or set(request) != {'endpoint', 'payload'}:
        raise TripoError('Request must contain exactly endpoint and payload.')
    route, payload = request['endpoint'], request['payload']
    if route not in ROUTES or not isinstance(payload, dict):
        raise TripoError('Unsupported endpoint or non-object payload; see references/api.md.')
    serialized = json.dumps(payload)
    if re.search(r'tsk_|api_key|authorization', serialized, re.I):
        raise TripoError('Do not put credentials in a request file.')
    if route.endswith('/text-to-model'):
        if not isinstance(payload.get('prompt'), str) or not 1 <= len(payload['prompt'].strip()) <= 1024:
            raise TripoError('Text generation requires a prompt of 1–1024 characters.')
    elif route.endswith('/multiview-to-model'):
        inputs = payload.get('inputs')
        if not isinstance(inputs, list) or not inputs:
            raise TripoError('Multiview requires nonempty inputs; use labeled views.')
        views = []
        for item in inputs:
            if not isinstance(item, dict) or len(item) != 1 or next(iter(item)) not in {'front','back','left','right','task_id'}:
                raise TripoError('Use one labeled view per object, or one task_id object. Do not mix schemas.')
            label, value = next(iter(item.items()))
            if not isinstance(value, str) or not value:
                raise TripoError('Each view requires an uploaded file token or HTTPS URL.')
            views.append(label)
        if len(views) != len(set(views)) or ('task_id' in views and len(views) != 1):
            raise TripoError('Duplicate views or mixed task/view input.')
    elif not isinstance(payload.get('input'), str) or not payload['input']:
        raise TripoError('This endpoint requires a nonempty input task ID, file token, or URL.')
    if route.endswith('/retarget'):
        if ('animation' in payload) == ('animations' in payload):
            raise TripoError('Use exactly one of animation or animations.')
        motions = payload.get('animations', [payload.get('animation')])
        if not isinstance(motions, list) or not motions or not all(isinstance(m, str) and m for m in motions):
            raise TripoError('Animations must be a nonempty list of preset IDs/file tokens.')
    return route, payload


def dependency_check(request, dependency):
    route, payload = validate_request(request)
    if route not in ('/v3/animations/rig', '/v3/animations/retarget'):
        return
    if not dependency:
        raise TripoError('Rig requires --source-job pointing to a successful rig-check; retarget requires a successful rig job.')
    source = read(Path(dependency) / 'job.json')
    result = source.get('result', {})
    if result.get('status') != 'success':
        raise TripoError('Source job has not completed successfully; run wait first.')
    if route.endswith('/rig'):
        if source['request']['endpoint'] != '/v3/animations/rig-check' or result.get('output', {}).get('riggable') is not True:
            raise TripoError('Source job must confirm riggable=true.')
        if payload['input'] != source['request']['payload']['input']:
            raise TripoError('Rig input must match the model checked, not the rig-check task ID.')
        recommended = result.get('output', {}).get('rig_type')
        if recommended and payload.get('rig_type') != recommended:
            raise TripoError('Rig type differs from rig-check recommendation; resolve before submitting.')
    elif source['request']['endpoint'] != '/v3/animations/rig' or payload['input'] != source.get('task_id'):
        raise TripoError('Retarget input must be the successful rig task ID, not the original model ID.')


def submit(client, request, job, source_job=None):
    route, payload = validate_request(request)
    dependency_check(request, source_job)
    path = Path(job) / 'job.json'
    with job_lock(job):
        if path.exists():
            record = read(path)
            if record.get('request') != request:
                raise TripoError('Job request changed. Use a new version directory; existing task was not resubmitted.')
            if record.get('task_id'):
                return record
            raise TripoError('Submission already attempted without a recorded task ID. Reconcile via account usage and recover; do not auto-resubmit.')
        balance = client.api('/v3/account/balance')
        record = {'request': request, 'submission': 'unknown', 'created_at': time.time(), 'balance_before': balance}
        # Persist uncertainty BEFORE the request. A crash/timeout must never cause a duplicate charge.
        save(path, redact(record))
        try:
            response = client.api(route, payload)
            if not isinstance(response, dict) or not response.get('task_id'):
                raise TripoError('Submission returned no task ID.')
            record.update(task_id=response['task_id'], submission='submitted')
        except Exception as error:
            record['submission'] = 'rejected' if isinstance(error, Rejected) else 'unknown'
            record['error'] = redact(str(error))
            save(path, redact(record))
            raise
        save(path, redact(record))
        return record


def wait_job(client, job, timeout=45, interval=5):
    path = Path(job) / 'job.json'
    deadline = time.monotonic() + timeout
    previous = None
    while True:
        record = read(path)
        if not record.get('task_id'):
            raise TripoError('No task ID saved. Reconcile the submission before polling.')
        result = client.task(record['task_id'])
        record['result'] = result
        save(path, redact(record))
        status = result.get('status')
        current = status, result.get('progress')
        if current != previous:
            emit({'task_id': record['task_id'], 'status': status, 'progress': current[1]})
            previous = current
        if status == 'success':
            try:
                record['balance_after'] = client.api('/v3/account/balance')
                save(path, redact(record))
            except TripoError:
                pass  # Successful generation is still usable if balance lookup is temporarily unavailable.
            return record
        if status in TERMINAL_BAD:
            raise TripoError('Task ended: ' + str(status) + '. Inspect job.json; no replacement was submitted.')
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        time.sleep(min(interval, remaining))


def upload(client, file, record_path):
    file, record_path = Path(file), Path(record_path)
    suffix = file.suffix.lower()
    limit = 20 if suffix in ('.png','.jpg','.jpeg') else 60
    if suffix not in ('.png','.jpg','.jpeg','.glb','.gltf','.fbx','.obj','.stl'):
        raise TripoError('Use PNG/JPEG or GLB/GLTF/FBX/OBJ/STL. See official docs for other formats.')
    if not 0 < file.stat().st_size <= limit * 1024 * 1024:
        raise TripoError(f'Multipart helper limit: {limit} MiB. For larger models use official files/presign; never forward API auth to storage.')
    data = file.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if record_path.exists():
        saved = read(record_path)
        if saved.get('sha256') != digest:
            raise TripoError('Upload input changed. Use a new record path.')
        if saved.get('file_token'):
            return saved
    boundary = 'TripoSkill' + uuid.uuid4().hex
    filename = 'input' + suffix  # Do not interpolate arbitrary filenames into multipart headers.
    mime = {'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg'}.get(suffix, 'application/octet-stream')
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: {mime}\r\n\r\n').encode() + data + f'\r\n--{boundary}--\r\n'.encode()
    result = client.api('/v3/files', body, 'multipart/form-data; boundary=' + boundary)
    if not result.get('file_token'):
        raise TripoError('Upload returned no file_token.')
    record = {'file_token': result['file_token'], 'sha256': digest, 'filename': file.name}
    save(record_path, record)
    return record


ASSET_EXTS = {'.glb','.gltf','.fbx','.obj','.stl','.usdz','.3mf','.zip','.png','.jpg','.jpeg','.webp','.bin','.mtl'}


def asset_urls(output):
    found, seen = [], set()
    def visit(value, trail='output'):
        if isinstance(value, dict):
            for k, v in value.items():
                visit(v, trail + '.' + str(k))
        elif isinstance(value, list):
            for i, v in enumerate(value):
                visit(v, trail + '.' + str(i))
        elif isinstance(value, str) and value.startswith('https://'):
            suffix = Path(urllib.parse.urlsplit(value).path).suffix.lower()
            if value not in seen and (suffix in ASSET_EXTS or re.search('model|animation|render|texture', trail, re.I)):
                found.append((trail, value))
                seen.add(value)
    visit(output)
    return found


class HTTPSRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).scheme != 'https':
            raise TripoError('Download redirect must stay HTTPS.')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_asset(url, target):
    if urllib.parse.urlsplit(url).scheme != 'https':
        raise TripoError('Artifact URL must use HTTPS.')
    req = urllib.request.Request(url, headers={'User-Agent': 'TripoPortableSkill/1.0'})
    # Separate opener: NO Bearer token, even when storage redirects to a CDN.
    opener = urllib.request.build_opener(HTTPSRedirect())
    temporary = Path(str(target) + '.part')
    digest, size = hashlib.sha256(), 0
    try:
        with opener.open(req, timeout=60) as response, temporary.open('wb') as stream:
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > 2 * 1024 ** 3:
                    raise TripoError('Artifact exceeds the helper 2 GiB limit.')
                digest.update(chunk)
                stream.write(chunk)
        if not size:
            raise TripoError('Empty artifact.')
        os.replace(temporary, target)
        return size, digest.hexdigest()
    finally:
        temporary.unlink(missing_ok=True)


def extract_zip(path, destination):
    """Validate all entries before extracting, with Windows traversal and symlink checks."""
    destination = Path(destination).resolve()
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) > 10000 or sum(i.file_size for i in infos) > 2 * 1024 ** 3:
            raise TripoError('Archive exceeds extraction limits.')
        seen = set()
        for item in infos:
            name = item.filename
            parts = PurePosixPath(name).parts
            if '\\' in name or ':' in name or name.startswith('/') or '..' in parts or (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise TripoError('Unsafe archive entry.')
            target = (destination / name).resolve()
            if not target.is_relative_to(destination) or str(target).casefold() in seen:
                raise TripoError('Unsafe or duplicate archive target.')
            seen.add(str(target).casefold())
            if target.exists() and not item.is_dir():
                raise TripoError('Extraction would overwrite a file; use a fresh extraction directory.')
        destination.mkdir(parents=True, exist_ok=True)
        archive.extractall(destination)


def download_job(client, job, extract=False):
    path = Path(job) / 'job.json'
    record = read(path)
    result = client.task(record['task_id'])  # Refresh expired signed URLs without generating again.
    record['result'] = result
    save(path, redact(record))
    if result.get('status') != 'success':
        raise TripoError('Download requires a successful task.')
    urls = asset_urls(result.get('output', {}))
    if not urls:
        raise TripoError('No downloadable artifacts; rig-check is metadata-only. Inspect saved output.')
    folder = Path(job) / 'assets'
    folder.mkdir(parents=True, exist_ok=True)
    manifest = []
    for index, (kind, url) in enumerate(urls):
        suffix = Path(urllib.parse.urlsplit(url).path).suffix.lower()
        if suffix not in ASSET_EXTS:
            suffix = '.bin'
        target = folder / (f'{index:02d}-' + re.sub(r'[^A-Za-z0-9_-]', '-', kind)[-80:] + suffix)
        size, digest = fetch_asset(url, target)
        with target.open('rb') as stream:
            magic = stream.read(4)
        actual = '.glb' if magic == b'glTF' else '.zip' if magic[:2] == b'PK' else suffix
        if actual != suffix:
            changed = target.with_suffix(actual)
            os.replace(target, changed)
            target = changed
        if actual == '.glb':
            from inspect_glb import inspect
            inspect(target)  # Reject corrupt GLB before publishing manifest.
        entry = {'kind': kind, 'file': target.relative_to(job).as_posix(), 'bytes': size, 'sha256': digest}
        if extract and actual == '.zip':
            destination = target.with_suffix('')
            if destination.exists():
                raise TripoError('Extraction directory exists; download without --extract or use a fresh job copy.')
            extract_zip(target, destination)
            entry['extracted'] = destination.relative_to(job).as_posix()
        manifest.append(entry)
        save(Path(job) / 'assets.json', {'task_id': record['task_id'], 'assets': manifest})
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    doctor = sub.add_parser('doctor', help='Offline environment check; --online verifies account without generating')
    doctor.add_argument('--online', action='store_true')
    sub.add_parser('configure', help='Hidden key prompt; verify and save in local user config, outside the skill')
    sub.add_parser('balance')
    sub.add_parser('usage', help='Read official account usage for task reconciliation')
    up = sub.add_parser('upload')
    up.add_argument('--file', required=True, type=Path)
    up.add_argument('--record', required=True, type=Path)
    su = sub.add_parser('submit')
    su.add_argument('--request', required=True, type=Path)
    su.add_argument('--job', required=True, type=Path)
    su.add_argument('--source-job', type=Path)
    su.add_argument('--dry-run', action='store_true')
    wa = sub.add_parser('wait')
    wa.add_argument('--job', required=True, type=Path)
    wa.add_argument('--timeout', type=float, default=45)
    wa.add_argument('--interval', type=float, default=5)
    status = sub.add_parser('status')
    status.add_argument('--task-id', required=True)
    recover = sub.add_parser('recover', help='Attach an existing task after reconciling an uncertain submission; never POSTs')
    recover.add_argument('--job', required=True, type=Path)
    recover.add_argument('--task-id', required=True)
    down = sub.add_parser('download')
    down.add_argument('--job', required=True, type=Path)
    down.add_argument('--extract', action='store_true')
    args = parser.parse_args(argv)
    if args.command == 'doctor':
        emit({'python': sys.version.split()[0], 'python_ok': sys.version_info >= (3,10), 'tls': ssl.OPENSSL_VERSION,
              'key_present': bool(os.environ.get('TRIPO_API_KEY')) or credentials_path().exists(),
              'credentials_file': str(credentials_path()), 'api_origin': BASE,
              'optional_blender': shutil.which('blender'), 'dependencies': 'Python standard library only'})
        if not os.environ.get('TRIPO_API_KEY', '').strip() and not credentials_path().exists():
            print_setup_guide()
        if not args.online:
            return 0
    if args.command == 'submit':
        request = read(args.request)
        validate_request(request)
        dependency_check(request, args.source_job)
        if args.dry_run:
            emit({'would_submit': request, 'job': str(args.job), 'network_requests': 0})
            return 0
    if args.command == 'configure':
        print_setup_guide()
        if not sys.stdin.isatty():
            raise TripoError('configure requires an interactive terminal to hide the key. Alternatively set TRIPO_API_KEY.')
        global SECRET
        SECRET = getpass.getpass('Tripo API key (hidden; saved only in local user config): ').strip()
        if not SECRET:
            raise TripoError('Empty API key.')
        balance = Client(SECRET).api('/v3/account/balance')
        save(credentials_path(), {'api_key': SECRET})
        emit({'configured': True, 'credentials_file': str(credentials_path()), 'balance': balance})
        return 0
    client = Client(get_key())
    if args.command in ('doctor','balance','usage'):
        emit(client.api('/v3/account/' + ('usage' if args.command == 'usage' else 'balance')))
    elif args.command == 'upload':
        emit(upload(client, args.file, args.record))
    elif args.command == 'submit':
        record = submit(client, request, args.job, args.source_job)
        emit({'task_id': record['task_id'], 'job': str(args.job), 'next': 'wait'})
    elif args.command == 'wait':
        if args.timeout < 0 or not 1 <= args.interval <= 60:
            raise TripoError('Use timeout >= 0 and interval between 1 and 60 seconds.')
        record = wait_job(client, args.job, args.timeout, args.interval)
        if record is None:
            emit({'pending': True, 'job': str(args.job), 'next': 'Run wait again; do not submit a replacement.'})
            return 3
        emit({'task_id': record['task_id'], 'status': 'success', 'credits_consumed': record['result'].get('credits_consumed')})
    elif args.command == 'status':
        emit(client.task(args.task_id))
    elif args.command == 'recover':
        with job_lock(args.job):
            path = args.job / 'job.json'
            record = read(path)
            if record.get('task_id') not in (None, args.task_id):
                raise TripoError('Job already belongs to a different task.')
            result = client.task(args.task_id)
            record.update(task_id=args.task_id, submission='recovered', result=result)
            save(path, redact(record))
            emit({'task_id': args.task_id, 'recovered': True})
    elif args.command == 'download':
        emit(download_job(client, args.job, args.extract))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (TripoError, OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        print('ERROR: ' + str(redact(str(error))), file=sys.stderr)
        sys.exit(1)

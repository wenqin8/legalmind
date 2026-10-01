"""Collect selected non-secret runtime evidence from a local Compose project."""
import argparse
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--docker', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    output = args.output.resolve()
    if not output.is_relative_to(root) or output.exists():
        raise SystemExit('Choose a new output inside the project.')
    env = {**os.environ, 'PATH': str(args.docker.parent) + os.pathsep + os.environ['PATH']}
    compose = ['compose', '--env-file', 'deployment/.env', '-f', 'compose.yml', '-p', args.project]
    def run(arguments):
        result = subprocess.run([str(args.docker), *arguments], cwd=root, env=env,
                                capture_output=True, text=True, encoding='utf-8', check=False)
        if result.returncode:
            raise RuntimeError('Docker evidence command failed: ' + arguments[0])
        return result.stdout.strip(), result.stderr.strip()
    run([*compose, 'config', '--quiet'])
    version, _ = run(['version', '--format', '{{json .}}'])
    compose_version, _ = run(['compose', 'version', '--short'])
    engine, _ = run(['info', '--format', '{{json .OperatingSystem}}'])
    rows, _ = run([*compose, 'ps', '--all', '--format', 'json'])
    services = []
    for line in rows.splitlines():
        row = json.loads(line)
        # The full inspect/config environment must never be written to evidence.
        image_id, _ = run(['inspect', '--format', '{{.Image}}', row['ID']])
        services.append({key: row.get(key) for key in ('Service', 'State', 'Health', 'ExitCode', 'Publishers')}
                        | {'image_id': image_id})
    volumes, _ = run(['volume', 'ls', '--filter', 'label=com.docker.compose.project=' + args.project,
                      '--format', '{{.Name}}'])
    _, nginx = run([*compose, 'exec', '-T', 'frontend', 'nginx', '-t'])
    pip_check, _ = run([*compose, 'exec', '-T', 'backend', 'python', '-m', 'pip', 'check'])
    runtime_code = (
        "import json,os,torch;from pathlib import Path;from sqlalchemy import select,func;"
        "from app.core.config import Settings;from app.db.session import Database;"
        "from app.db.models import Case,LegalProvision,KnowledgeChunk;"
        "db=Database(Settings().database_url.get_secret_value());"
        "manager=db.session();s=manager.__enter__();print(json.dumps({'uid':os.getuid(),'torch':torch.__version__,"
        "'cuda_available':torch.cuda.is_available(),'case_count':s.scalar(select(func.count()).select_from(Case)),"
        "'law_count':s.scalar(select(func.count()).select_from(LegalProvision)),"
        "'chunk_count':s.scalar(select(func.count()).select_from(KnowledgeChunk)),"
        "'env_files_in_app':[str(p) for p in Path('/app').rglob('.env')]}));manager.__exit__(None,None,None);db.dispose()"
    )
    runtime, _ = run([*compose, 'exec', '-T', 'backend', 'python', '-c', runtime_code])
    runtime = json.loads(runtime)
    published = [item for service in services for item in service.get('Publishers') or [] if item.get('PublishedPort')]
    checks = {
        'four_services_healthy': sum(s['Health'] == 'healthy' for s in services) == 4,
        'initialize_completed': any(s['Service'] == 'initialize' and s['ExitCode'] == 0 for s in services),
        'loopback_frontend_only': len(published) == 1 and published[0]['URL'] == '127.0.0.1' and published[0]['TargetPort'] == 80,
        'four_named_volumes': len(volumes.splitlines()) == 4,
        'nonroot_cpu_backend': runtime['uid'] == 10001 and not runtime['cuda_available'],
        'default_dataset_counts': (runtime['case_count'], runtime['law_count'], runtime['chunk_count']) == (16, 60, 64),
        'no_env_in_application_image': runtime['env_files_in_app'] == [],
        'pip_check': 'No broken requirements found.' in pip_check,
        'nginx_valid': 'test is successful' in nginx,
    }
    report = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'project': args.project,
              'host_windows_version': platform.win32_ver(), 'docker_version': json.loads(version),
              'compose_version': compose_version, 'engine_os': json.loads(engine), 'services': services,
              'volumes': volumes.splitlines(), 'runtime': runtime, 'nginx_test': nginx, 'pip_check': pip_check,
              'checks': checks, 'passed': all(checks.values()),
              'limitations': ['Runtime evidence complements clean-volume startup and browser restart reports.',
                              'No real model requests or secrets are included.']}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({'passed': report['passed'], 'checks': checks}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

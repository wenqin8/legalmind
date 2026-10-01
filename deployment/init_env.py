"""Create deployment secrets once; never print values or read the daily .env."""
import secrets
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    destination = root / '.env'
    if destination.exists():
        print('Deployment environment already exists; left unchanged.')
        return
    content = (root / '.env.example').read_text(encoding='utf-8')
    for key in ('LEGALMIND_POSTGRES_PASSWORD', 'LEGALMIND_REDIS_PASSWORD', 'LEGALMIND_JWT_SECRET_KEY'):
        content = content.replace(key + '=\n', key + '=' + secrets.token_urlsafe(48) + '\n')
    with destination.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(content)
    print('Created deployment/.env. Configure the model key locally before asking legal questions.')


if __name__ == '__main__': main()

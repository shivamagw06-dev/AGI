"""Atomically replace only the nightly valuation file over verified FTPS."""
import ftplib, ipaddress, os, socket, ssl, sys, uuid
from pathlib import Path

def tls_host(server):
    """Resolve legacy IP configuration to a verified Hostinger service hostname."""
    try:
        ipaddress.ip_address(server)
    except ValueError:
        return server
    try:
        candidates=[socket.gethostbyaddr(server)[0].rstrip('.').lower()]
    except socket.herror:
        # Inspect only the public certificate, before sending ANY credentials.
        # CA validation remains enabled; the eventual authenticated connection
        # always performs both CA and hostname validation with a default context.
        discovery=ssl.create_default_context()
        discovery.check_hostname=False
        with ftplib.FTP_TLS(context=discovery,timeout=30) as probe:
            probe.connect(server,21)
            probe.auth()
            candidates=[name.lower().rstrip('.') for kind,name in probe.sock.getpeercert().get('subjectAltName',[]) if kind=='DNS' and '*' not in name]
    for name in candidates:
        if not (name.endswith(('.main-hosting.eu','.hostinger.com')) or name=='agarwalglobalinvestments.com' or name.endswith('.agarwalglobalinvestments.com')):
            continue
        try:
            addresses={item[4][0] for item in socket.getaddrinfo(name,21,type=socket.SOCK_STREAM)}
        except socket.gaierror:
            continue
        if server in addresses:
            return name
    raise ValueError('No verified provider hostname resolves to the configured FTP IP; configure the Hostinger TLS hostname')

def publish(path):
    p=Path(path) if path != '--check' else None
    host=tls_host(os.environ['FTP_SERVER'])
    with ftplib.FTP_TLS(context=ssl.create_default_context(),timeout=120) as ftp:
        ftp.connect(host,21)
        ftp.login(os.environ['FTP_USERNAME'],os.environ['FTP_PASSWORD'])
        ftp.prot_p()
        if p is None:
            print('Verified Hostinger TLS connection and login')
            return
        try: ftp.cwd('investor-valuations')
        except ftplib.error_perm:
            ftp.mkd('investor-valuations'); ftp.cwd('investor-valuations')
        temporary='pending-'+uuid.uuid4().hex+'.json'
        with p.open('rb') as stream: ftp.storbinary('STOR '+temporary,stream)
        ftp.rename(temporary,'latest.json')
    print('Published nightly valuation snapshot')
if __name__=='__main__': publish(sys.argv[1])

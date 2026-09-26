"""Atomically replace only the nightly valuation file over verified FTPS."""
import ftplib, ipaddress, os, socket, ssl, sys, uuid
from pathlib import Path

def tls_host(server):
    """Resolve legacy IP configuration to a verified Hostinger service hostname."""
    try:
        ipaddress.ip_address(server)
    except ValueError:
        return server
    name=socket.gethostbyaddr(server)[0].rstrip('.').lower()
    # Only the configured hosting provider's domains are eligible, and forward
    # DNS must point back to the exact configured IP before any credentials move.
    if not name.endswith(('.main-hosting.eu','.hostinger.com')):
        raise ValueError('FTP IP needs its Hostinger TLS hostname configured')
    addresses={item[4][0] for item in socket.getaddrinfo(name,21,type=socket.SOCK_STREAM)}
    if server not in addresses:
        raise ValueError('FTP hostname does not resolve to the configured server')
    return name

def publish(path):
    p=Path(path)
    host=tls_host(os.environ['FTP_SERVER'])
    with ftplib.FTP_TLS(context=ssl.create_default_context(),timeout=120) as ftp:
        ftp.connect(host,21)
        ftp.login(os.environ['FTP_USERNAME'],os.environ['FTP_PASSWORD'])
        ftp.prot_p()
        try: ftp.cwd('investor-valuations')
        except ftplib.error_perm:
            ftp.mkd('investor-valuations'); ftp.cwd('investor-valuations')
        temporary='pending-'+uuid.uuid4().hex+'.json'
        with p.open('rb') as stream: ftp.storbinary('STOR '+temporary,stream)
        ftp.rename(temporary,'latest.json')
    print('Published nightly valuation snapshot')
if __name__=='__main__': publish(sys.argv[1])

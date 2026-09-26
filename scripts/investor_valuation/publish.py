"""Atomically replace only the nightly valuation file over verified FTPS."""
import ftplib, ipaddress, os, ssl, sys, uuid
from pathlib import Path

def tls_host(server):
    """Hostinger's shared FTP certificate covers hstgr.io, not server IPs.

    The TCP destination stays the configured server. This selects the expected
    TLS service identity; certificate chain AND hostname checks stay enabled.
    """
    try:
        ipaddress.ip_address(server)
    except ValueError:
        return server
    return 'hstgr.io'

def publish(path):
    p=Path(path) if path != '--check' else None
    server=os.environ['FTP_SERVER']
    host=tls_host(server)
    with ftplib.FTP_TLS(context=ssl.create_default_context(),timeout=120) as ftp:
        ftp.connect(server,21)
        ftp.host=host  # TLS SNI/identity only; the established TCP peer stays unchanged.
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

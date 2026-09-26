"""Atomically replace only the nightly valuation file over verified FTPS."""
import ftplib, os, ssl, sys, uuid
from pathlib import Path
p=Path(sys.argv[1])
with ftplib.FTP_TLS(context=ssl.create_default_context(),timeout=120) as ftp:
    ftp.connect(os.environ['FTP_SERVER'],21)
    ftp.login(os.environ['FTP_USERNAME'],os.environ['FTP_PASSWORD'])
    ftp.prot_p()
    try: ftp.cwd('investor-valuations')
    except ftplib.error_perm:
        ftp.mkd('investor-valuations'); ftp.cwd('investor-valuations')
    temporary='pending-'+uuid.uuid4().hex+'.json'
    with p.open('rb') as stream: ftp.storbinary('STOR '+temporary,stream)
    ftp.rename(temporary,'latest.json')
print('Published nightly valuation snapshot')

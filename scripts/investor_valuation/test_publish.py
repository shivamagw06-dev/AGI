import ssl, unittest
from unittest.mock import patch, MagicMock
from publish import tls_host, publish
class PublicationTests(unittest.TestCase):
    def test_dns_hostname_is_verified_directly(self):
        self.assertEqual(tls_host('example.hostinger.com'),'example.hostinger.com')
    def test_ip_uses_expected_hostinger_service_identity(self):
        self.assertEqual(tls_host('192.0.2.1'),'hstgr.io')
        self.assertEqual(tls_host('2001:db8::1'),'hstgr.io')
    @patch.dict('os.environ',{'FTP_SERVER':'192.0.2.1','FTP_USERNAME':'test','FTP_PASSWORD':'test'})
    @patch('publish.ftplib.FTP_TLS')
    def test_preflight_keeps_tcp_peer_and_full_certificate_verification(self,cls):
        ftp=cls.return_value.__enter__.return_value
        publish('--check')
        context=cls.call_args.kwargs['context']
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode,ssl.CERT_REQUIRED)
        ftp.connect.assert_called_once_with('192.0.2.1',21)
        self.assertEqual(ftp.host,'hstgr.io')
        ftp.login.assert_called_once_with('test','test')
        ftp.storbinary.assert_not_called()

import unittest
from unittest.mock import patch
from publish import tls_host
class PublicationTests(unittest.TestCase):
    def test_dns_hostname_is_verified_directly(self):
        self.assertEqual(tls_host('example.hostinger.com'),'example.hostinger.com')
    @patch('publish.socket.getaddrinfo',return_value=[(None,None,None,None,('192.0.2.1',21))])
    @patch('publish.socket.gethostbyaddr',return_value=('srv1.main-hosting.eu',[],['192.0.2.1']))
    def test_provider_hostname_must_point_to_original_ip(self,*_):
        self.assertEqual(tls_host('192.0.2.1'),'srv1.main-hosting.eu')
        with self.assertRaises(ValueError): tls_host('192.0.2.2')
    @patch('publish.socket.gethostbyaddr',return_value=('hostinger.com.attacker.example',[],['192.0.2.1']))
    def test_other_provider_hostname_rejected(self,*_):
        with self.assertRaises(ValueError): tls_host('192.0.2.1')
